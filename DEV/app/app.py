"""
Aplicação Flask do UPA Transparente - Painel de Gestão e Transparência de Filas.
Projeto Integrador UNIVESP - Polo Jandira.
"""

import os
import secrets
import threading
import time
from datetime import datetime
from functools import wraps

import bcrypt
import mysql.connector
from flask import Flask, abort, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
_configured_secret = os.environ.get('FLASK_SECRET_KEY')
app.config.update(
    SECRET_KEY=_configured_secret or secrets.token_hex(32),
    SECRET_KEY_CONFIGURED=bool(_configured_secret),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE', '0') == '1',
    PERMANENT_SESSION_LIFETIME=3600,
)


@app.before_request
def protect_operator_routes():
    """Do not expose credentials or clinical writes over public plain HTTP.

    A loopback connection is allowed for an SSH tunnel to the DEV service.
    Behind Nginx, ProxyFix restores the original client address, so a public
    HTTP request does not qualify as loopback.
    """
    if not request.path.startswith('/operacao'):
        return None
    if not app.config['SECRET_KEY_CONFIGURED']:
        abort(503, description='Configure FLASK_SECRET_KEY para habilitar sessões operacionais.')
    if os.environ.get('OPERATIONS_REQUIRE_HTTPS', '0') != '1':
        return None
    loopback = request.remote_addr in ('127.0.0.1', '::1')
    if not request.is_secure and not loopback:
        abort(403, description='A área operacional requer HTTPS ou túnel SSH local.')

# Configuração de conexão ao MariaDB com suporte a variáveis de ambiente
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', '127.0.0.1'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER', ''),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'filago'),
    'charset': 'utf8mb4'
}

def get_db_connection():
    """Retorna uma nova conexão com o banco de dados MariaDB."""
    if not DB_CONFIG['user'] or not DB_CONFIG['password']:
        raise RuntimeError('DB_USER e DB_PASSWORD precisam estar configurados no ambiente.')
    return mysql.connector.connect(**DB_CONFIG)


def csrf_token():
    token = session.get('_csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        session['_csrf_token'] = token
    return token


app.jinja_env.globals['csrf_token'] = csrf_token


def require_csrf():
    expected = session.get('_csrf_token', '')
    supplied = request.form.get('_csrf_token', '')
    if not expected or not secrets.compare_digest(expected, supplied):
        abort(400, description='Token de formulário inválido ou expirado.')


def operation_required(*profiles):
    def decorate(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user_id = session.get('operator_id')
            if not user_id:
                return redirect(url_for('operacao_login', next=request.path))
            if profiles and session.get('operator_profile') not in profiles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorate


def password_matches(password, stored_hash):
    if not stored_hash:
        return False
    if stored_hash.startswith(('$2a$', '$2b$', '$2y$')):
        try:
            normalized = stored_hash.replace('$2y$', '$2b$', 1).encode('ascii')
            return bcrypt.checkpw(password.encode('utf-8'), normalized)
        except (ValueError, TypeError):
            return False
    try:
        return check_password_hash(stored_hash, password)
    except (ValueError, TypeError):
        return False


def close_cursor_connection(cursor, connection):
    if cursor:
        cursor.close()
    if connection and connection.is_connected():
        connection.close()


def active_operator_roles():
    return ('ADMIN', 'RECEPCAO', 'TRIAGEM', 'MEDICO', 'GESTOR')


class LoginRateLimiter:
    """Controle progressivo de tentativas de login por chave (IP + login) e teto global de IP."""

    def __init__(self, failure_window=900, ip_global_threshold=20, ip_lock_time=900):
        self._lock = threading.Lock()
        self._window = failure_window  # 15 minutos sem novas falhas limpa o histórico
        self._ip_threshold = ip_global_threshold
        self._ip_lock_time = ip_lock_time
        self._user_attempts = {}  # (ip, login) -> {"failures": count, "locked_until": timestamp, "updated_at": timestamp}
        self._ip_attempts = {}    # ip -> {"failures": count, "locked_until": timestamp, "updated_at": timestamp}

    def _cleanup_unlocked(self, now: float):
        expired_users = [
            k for k, v in self._user_attempts.items()
            if now > v["locked_until"] and (now - v["updated_at"]) > self._window
        ]
        for k in expired_users:
            del self._user_attempts[k]

        expired_ips = [
            k for k, v in self._ip_attempts.items()
            if now > v["locked_until"] and (now - v["updated_at"]) > self._window
        ]
        for k in expired_ips:
            del self._ip_attempts[k]

    def check_lock(self, ip: str, login: str):
        now = time.time()
        key = (ip.strip(), login.strip().lower())
        with self._lock:
            self._cleanup_unlocked(now)

            ip_info = self._ip_attempts.get(ip)
            if ip_info and now < ip_info["locked_until"]:
                return True, max(1, int(ip_info["locked_until"] - now))

            user_info = self._user_attempts.get(key)
            if user_info and now < user_info["locked_until"]:
                return True, max(1, int(user_info["locked_until"] - now))

            return False, 0

    def record_failure(self, ip: str, login: str):
        now = time.time()
        key = (ip.strip(), login.strip().lower())
        with self._lock:
            ip_info = self._ip_attempts.setdefault(ip, {"failures": 0, "locked_until": 0.0, "updated_at": now})
            if now - ip_info["updated_at"] > self._window and now >= ip_info["locked_until"]:
                ip_info["failures"] = 0
            ip_info["failures"] += 1
            ip_info["updated_at"] = now
            if ip_info["failures"] >= self._ip_threshold:
                ip_info["locked_until"] = max(ip_info["locked_until"], now + self._ip_lock_time)
                return True, int(self._ip_lock_time)

            user_info = self._user_attempts.setdefault(key, {"failures": 0, "locked_until": 0.0, "updated_at": now})
            if now - user_info["updated_at"] > self._window and now >= user_info["locked_until"]:
                user_info["failures"] = 0
            user_info["failures"] += 1
            user_info["updated_at"] = now

            failures = user_info["failures"]
            lock_duration = 0
            if failures >= 11:
                lock_duration = 1800  # 30 minutos
            elif failures >= 8:
                lock_duration = 300   # 5 minutos
            elif failures >= 3:
                lock_duration = 30    # 30 segundos

            if lock_duration > 0:
                user_info["locked_until"] = now + lock_duration
                return True, lock_duration

            return False, 0

    def record_success(self, ip: str, login: str):
        key = (ip.strip(), login.strip().lower())
        with self._lock:
            if key in self._user_attempts:
                del self._user_attempts[key]
            if ip in self._ip_attempts and self._ip_attempts[ip]["failures"] < self._ip_threshold:
                del self._ip_attempts[ip]


login_limiter = LoginRateLimiter()


@app.route('/operacao/login', methods=['GET', 'POST'])
def operacao_login():
    if session.get('operator_id'):
        return redirect(url_for('operacao_home'))

    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.remote_addr
        or "127.0.0.1"
    )

    if request.method == 'POST':
        require_csrf()
        login = request.form.get('login', '').strip()
        password = request.form.get('password', '')

        is_locked, retry_after = login_limiter.check_lock(client_ip, login)
        if is_locked:
            flash(f'Muitas tentativas incorretas. Aguarde {retry_after} segundos para tentar novamente.', 'error')
            return render_template('operacao_login.html', lockout_seconds=retry_after), 429

        connection = cursor = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT id, nome, login, senha_hash, perfil, ativo "
                "FROM upa_usuarios WHERE login = %s LIMIT 1",
                (login,),
            )
            operator = cursor.fetchone()
            if (not operator or not operator['ativo'] or
                    operator['perfil'] not in active_operator_roles() or
                    not password_matches(password, operator['senha_hash'])):
                is_locked, retry_after = login_limiter.record_failure(client_ip, login)
                if is_locked:
                    flash(f'Muitas tentativas incorretas. Aguarde {retry_after} segundos para tentar novamente.', 'error')
                    return render_template('operacao_login.html', lockout_seconds=retry_after), 429
                flash('Login ou senha inválidos.', 'error')
                return render_template('operacao_login.html'), 401

            login_limiter.record_success(client_ip, login)
            session.clear()
            session.permanent = True
            session['operator_id'] = int(operator['id'])
            session['operator_name'] = operator['nome']
            session['operator_profile'] = operator['perfil']
            session['operator_login'] = operator['login']
            cursor.execute(
                "UPDATE upa_usuarios SET ultimo_acesso_em = CURRENT_TIMESTAMP WHERE id = %s",
                (operator['id'],),
            )
            connection.commit()
            csrf_token()
            target = request.args.get('next', '')
            target_routes = {
                '/operacao/cadastro': 'operacao_cadastro',
                '/operacao/fila': 'operacao_fila',
            }
            endpoint = target_routes.get(target, 'operacao_home')
            return redirect(url_for(endpoint))
        except Exception:
            app.logger.exception('Falha ao autenticar operador UPA')
            flash('Não foi possível validar o acesso agora.', 'error')
            return render_template('operacao_login.html'), 503
        finally:
            close_cursor_connection(cursor, connection)
    return render_template('operacao_login.html')


@app.post('/operacao/logout')
@operation_required()
def operacao_logout():
    require_csrf()
    session.clear()
    return redirect(url_for('operacao_login'))


@app.route('/operacao')
@operation_required()
def operacao_home():
    return render_template('operacao_home.html', operator_name=session.get('operator_name'),
                           operator_profile=session.get('operator_profile'))


@app.route('/operacao/cadastro', methods=['GET', 'POST'])
@operation_required('ADMIN', 'RECEPCAO', 'TRIAGEM')
def operacao_cadastro():
    connection = cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, nome, codigo, cor FROM upa_classificacoes_risco "
            "WHERE ativo = 1 ORDER BY ordem_prioridade"
        )
        classificacoes = cursor.fetchall()
        if request.method == 'GET':
            return render_template('operacao_cadastro.html', classificacoes=classificacoes)

        require_csrf()
        nome = request.form.get('paciente_nome', '').strip()
        nascimento_txt = request.form.get('paciente_data_nascimento', '').strip()
        risco_id_txt = request.form.get('classificacao_risco_id', '').strip()
        if not nome or len(nome) > 180:
            flash('Informe o nome do paciente (até 180 caracteres).', 'error')
            return render_template('operacao_cadastro.html', classificacoes=classificacoes), 400
        try:
            nascimento = datetime.strptime(nascimento_txt, '%Y-%m-%d').date() if nascimento_txt else None
        except ValueError:
            flash('Data de nascimento inválida.', 'error')
            return render_template('operacao_cadastro.html', classificacoes=classificacoes), 400
        try:
            risco_id = int(risco_id_txt)
        except ValueError:
            flash('Selecione uma classificação de risco.', 'error')
            return render_template('operacao_cadastro.html', classificacoes=classificacoes), 400
        if risco_id not in {int(item['id']) for item in classificacoes}:
            abort(400)

        def optional_decimal(field, label, minimum, maximum):
            raw = request.form.get(field, '').strip().replace(',', '.')
            if not raw:
                return None
            try:
                value = float(raw)
            except ValueError:
                raise ValueError(f'{label}: valor inválido.')
            if value < minimum or value > maximum:
                raise ValueError(f'{label}: valor fora do intervalo permitido.')
            return value

        try:
            saturacao = optional_decimal('saturacao', 'Saturação', 0, 100)
            temperatura = optional_decimal('temperatura', 'Temperatura', 25, 45)
            peso = optional_decimal('peso', 'Peso', 0, 500)
            frequencia = optional_decimal('frequencia_cardiaca', 'Frequência cardíaca', 0, 300)
            dor_txt = request.form.get('nivel_dor', '').strip()
            nivel_dor = int(dor_txt) if dor_txt else None
            if nivel_dor is not None and not 0 <= nivel_dor <= 10:
                raise ValueError('Nível de dor deve ficar entre 0 e 10.')
        except ValueError as exc:
            flash(str(exc), 'error')
            return render_template('operacao_cadastro.html', classificacoes=classificacoes), 400

        arrival = datetime.now()
        protocolo = f"UPA1-{arrival.strftime('%Y%m%d%H%M%S%f')}"
        # Finalize the read transaction before beginning the atomic write.
        connection.commit()
        connection.start_transaction()
        # Create the daily counter row before locking it. The unique key makes
        # concurrent first arrivals serialize safely even when today's row is
        # not present yet.
        cursor.execute(
            "INSERT INTO upa_senhas_controle "
            "(unidade_id, data_referencia, tipo_senha, ultimo_numero) "
            "VALUES (1, %s, 'NORMAL', 0) "
            "ON DUPLICATE KEY UPDATE id = id",
            (arrival.date(),),
        )
        cursor.execute(
            "SELECT ultimo_numero FROM upa_senhas_controle "
            "WHERE unidade_id = 1 AND data_referencia = %s AND tipo_senha = 'NORMAL' FOR UPDATE",
            (arrival.date(),),
        )
        numero_senha = int(cursor.fetchone()['ultimo_numero']) + 1
        cursor.execute(
            "UPDATE upa_senhas_controle SET ultimo_numero = %s "
            "WHERE unidade_id = 1 AND data_referencia = %s AND tipo_senha = 'NORMAL'",
            (numero_senha, arrival.date()),
        )
        senha = f'P-{numero_senha:04d}'
        cursor.execute(
            "INSERT INTO upa_atendimentos "
            "(unidade_id, protocolo, senha, numero_senha, tipo_entrada, paciente_nome, paciente_data_nascimento, "
            "classificacao_risco_id, status_atual, prioridade_legal, criado_por) "
            "VALUES (1, %s, %s, %s, 'RECEPCAO', %s, %s, %s, 'EM_TRIAGEM', %s, %s)",
            (protocolo, senha, numero_senha, nome, nascimento, risco_id,
             1 if request.form.get('gestante') == '1' else 0, session['operator_id']),
        )
        atendimento_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO upa_triagem "
            "(atendimento_id, gestante, nivel_dor, saturacao, temperatura, pressao_arterial, peso, "
            "frequencia_cardiaca, alergias, queixa_observacao, hipertenso, diabetes, cancer, "
            "pneumopatia, tosse, outros_sintomas, prioridade_clinica) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (atendimento_id, 1 if request.form.get('gestante') == '1' else 0,
             nivel_dor, saturacao, temperatura, request.form.get('pressao_arterial', '').strip()[:20] or None,
             peso, frequencia, request.form.get('alergias', '').strip(),
             request.form.get('queixa_observacao', '').strip(),
             1 if request.form.get('hipertenso') == '1' else 0,
             1 if request.form.get('diabetes') == '1' else 0,
             1 if request.form.get('cancer') == '1' else 0,
             1 if request.form.get('pneumopatia') == '1' else 0,
             1 if request.form.get('tosse') == '1' else 0,
             1 if request.form.get('outros_sintomas') == '1' else 0,
             1 if request.form.get('prioridade_clinica') == '1' else 0),
        )
        cursor.execute(
            "INSERT INTO upa_atendimento_eventos "
            "(atendimento_id, unidade_id, usuario_id, tipo_evento, status_novo, observacao) "
            "VALUES (%s, 1, %s, 'CHEGADA_RECEPCAO', 'EM_TRIAGEM', %s)",
            (atendimento_id, session['operator_id'], f'Cadastro web por {session["operator_login"]}'),
        )
        connection.commit()
        return render_template('operacao_cadastro_sucesso.html', protocolo=protocolo, senha=senha)
    except mysql.connector.Error:
        if connection and connection.is_connected():
            connection.rollback()
        app.logger.exception('Falha ao cadastrar atendimento pela interface web')
        flash('Não foi possível salvar o atendimento. Confira os dados e tente novamente.', 'error')
        if request.method == 'POST':
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id, nome, codigo, cor FROM upa_classificacoes_risco WHERE ativo = 1 ORDER BY ordem_prioridade")
            return render_template('operacao_cadastro.html', classificacoes=cursor.fetchall()), 503
        raise
    finally:
        close_cursor_connection(cursor, connection)


QUEUE_DESTINATIONS = {
    'RECEPCAO': ('AGUARDANDO_RECEPCAO', None, 'RECEPCAO_CHAMADO'),
    'CLASSIFICACAO': ('EM_TRIAGEM', None, 'TRIAGEM_INICIADA'),
    'CLINICO': ('AGUARDANDO_ATENDIMENTO', 'Clínico Geral', 'CONSULTA_CHAMADO'),
    'PEDIATRIA': ('AGUARDANDO_ATENDIMENTO', 'Pediatria', 'CONSULTA_CHAMADO'),
    'ORTOPEDIA': ('AGUARDANDO_ATENDIMENTO', 'Ortopedia', 'CONSULTA_CHAMADO'),
    'ODONTOLOGIA': ('AGUARDANDO_ATENDIMENTO', 'Odontologia', 'CONSULTA_CHAMADO'),
    'MEDICACAO': ('AGUARDANDO_MEDICACAO', None, 'MEDICACAO_ENCAMINHADO'),
}


@app.route('/operacao/fila', methods=['GET', 'POST'])
@operation_required('ADMIN', 'TRIAGEM', 'MEDICO', 'GESTOR')
def operacao_fila():
    connection = cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        if request.method == 'POST':
            require_csrf()
            atendimento_id = request.form.get('atendimento_id', type=int)
            action = request.form.get('action', '')
            destination = request.form.get('destination', '')
            if not atendimento_id:
                abort(400)
            connection.start_transaction()
            cursor.execute(
                "SELECT id, status_atual, especialidade FROM upa_atendimentos "
                "WHERE id = %s AND status_atual NOT IN ('FINALIZADO','EVASAO','CANCELADO','TRANSFERIDO') FOR UPDATE",
                (atendimento_id,),
            )
            patient = cursor.fetchone()
            if not patient:
                flash('Atendimento não encontrado ou já encerrado.', 'error')
                return redirect(url_for('operacao_fila'))
            if action == 'finish':
                if session.get('operator_profile') not in ('ADMIN', 'MEDICO', 'GESTOR'):
                    abort(403)
                status_novo, especialidade, tipo_evento = 'FINALIZADO', patient['especialidade'], 'ALTA'
                sql = "UPDATE upa_atendimentos SET status_atual = %s, atendimento_fim_em = COALESCE(atendimento_fim_em, CURRENT_TIMESTAMP), finalizado_em = CURRENT_TIMESTAMP, atualizado_por = %s WHERE id = %s"
                params = (status_novo, session['operator_id'], atendimento_id)
            elif destination in QUEUE_DESTINATIONS:
                if session.get('operator_profile') not in ('ADMIN', 'TRIAGEM', 'GESTOR'):
                    abort(403)
                status_novo, especialidade, tipo_evento = QUEUE_DESTINATIONS[destination]
                if destination == 'CLASSIFICACAO':
                    sql = "UPDATE upa_atendimentos SET status_atual = %s, triagem_inicio_em = COALESCE(triagem_inicio_em, CURRENT_TIMESTAMP), atualizado_por = %s WHERE id = %s"
                    params = (status_novo, session['operator_id'], atendimento_id)
                elif destination in ('CLINICO', 'PEDIATRIA', 'ORTOPEDIA', 'ODONTOLOGIA'):
                    sql = "UPDATE upa_atendimentos SET status_atual = %s, especialidade = %s, triagem_fim_em = COALESCE(triagem_fim_em, CURRENT_TIMESTAMP), atualizado_por = %s WHERE id = %s"
                    params = (status_novo, especialidade, session['operator_id'], atendimento_id)
                else:
                    sql = "UPDATE upa_atendimentos SET status_atual = %s, especialidade = %s, atualizado_por = %s WHERE id = %s"
                    params = (status_novo, especialidade, session['operator_id'], atendimento_id)
            else:
                abort(400)
            cursor.execute(sql, params)
            cursor.execute(
                "INSERT INTO upa_atendimento_eventos "
                "(atendimento_id, unidade_id, usuario_id, tipo_evento, status_anterior, status_novo, observacao) "
                "VALUES (%s, 1, %s, %s, %s, %s, %s)",
                (atendimento_id, session['operator_id'], tipo_evento, patient['status_atual'], status_novo,
                 f'Atualização web por {session["operator_login"]}'),
            )
            connection.commit()
            flash('Atendimento atualizado.', 'success')
            return redirect(url_for('operacao_fila'))

        term = request.args.get('q', '').strip()
        if term:
            cursor.execute(
                "SELECT a.id, a.protocolo, a.senha, a.paciente_nome, a.status_atual, a.especialidade, "
                "a.chegada_em, cr.nome AS classificacao_nome "
                "FROM upa_atendimentos a LEFT JOIN upa_classificacoes_risco cr "
                "ON cr.id = a.classificacao_risco_id "
                "WHERE a.status_atual NOT IN ('FINALIZADO','EVASAO','CANCELADO','TRANSFERIDO') "
                "AND (a.paciente_nome LIKE %s OR a.protocolo LIKE %s OR a.senha LIKE %s) "
                "ORDER BY a.chegada_em ASC LIMIT 100",
                (f'%{term}%', f'%{term}%', f'%{term}%'),
            )
        else:
            cursor.execute(
                "SELECT a.id, a.protocolo, a.senha, a.paciente_nome, a.status_atual, a.especialidade, "
                "a.chegada_em, cr.nome AS classificacao_nome "
                "FROM upa_atendimentos a LEFT JOIN upa_classificacoes_risco cr "
                "ON cr.id = a.classificacao_risco_id "
                "WHERE a.status_atual NOT IN ('FINALIZADO','EVASAO','CANCELADO','TRANSFERIDO') "
                "ORDER BY a.chegada_em ASC LIMIT 100"
            )
        return render_template('operacao_fila.html', atendimentos=cursor.fetchall(), term=term,
                               destinations=QUEUE_DESTINATIONS)
    except mysql.connector.Error:
        if connection and connection.is_connected():
            connection.rollback()
        app.logger.exception('Falha ao consultar ou movimentar fila pela interface web')
        flash('Não foi possível acessar a fila neste momento.', 'error')
        return render_template('operacao_fila.html', atendimentos=[], term=request.args.get('q', ''),
                               destinations=QUEUE_DESTINATIONS), 503
    finally:
        close_cursor_connection(cursor, connection)

@app.route('/')
def index():
    """Renderiza o painel web responsivo (TV da UPA e visualização mobile do paciente)."""
    return render_template('index.html')


@app.route('/creditos')
def creditos():
    """Exibe os créditos acadêmicos do projeto."""
    return render_template('creditos.html')

@app.route('/api/dados')
def api_dados():
    """
    Retorna o payload JSON atualizado da fila em tempo real.
    - Se informado o parâmetro 'protocolo', calcula a posição individual do paciente
      aplicando a regra de ordenação: Protocolo de Manchester > Prioridade Legal > Chegada.
    - Retorna a contagem agregada de pacientes por setor e por classificação de risco.
    """
    protocolo = request.args.get('protocolo')
    
    dados = {
        "paciente": None,
        "posicao": None,       
        "total_setor": None,   
        "tempo_estimado": None,
        "risco": {
            "emergencia": {"qtd": 0, "tempo": ""},
            "muitoUrgente": {"qtd": 0, "tempo": ""},
            "urgente": {"qtd": 0, "tempo": ""},
            "poucoUrgente": {"qtd": 0, "tempo": ""},
            "naoUrgente": {"qtd": 0, "tempo": ""}
        },
        "setores": {
            "recepcao": {"qtd": 0, "tempo": ""},
            "classificacao": {"qtd": 0, "tempo": ""},
            "clinico": {"qtd": 0, "tempo": ""},
            "pediatra": {"qtd": 0, "tempo": ""},
            "ortopedia": {"qtd": 0, "tempo": ""},
            "odonto": {"qtd": 0, "tempo": ""},
            "medicacao": {"qtd": 0, "tempo": ""}
        }
    }

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 1. Puxa os dados do paciente com campos necessários para a regra de negócio
        pac = None
        if protocolo:
            query_paciente = """
                SELECT a.id, a.paciente_nome, a.status_atual, a.especialidade, a.chegada_em, 
                       cr.nome as classificacao_nome, cr.ordem_prioridade, a.prioridade_legal
                FROM upa_atendimentos a 
                LEFT JOIN upa_classificacoes_risco cr ON a.classificacao_risco_id = cr.id 
                WHERE a.protocolo = %s
            """
            cursor.execute(query_paciente, (protocolo,))
            pac = cursor.fetchone()
            
            if pac:
                ordem_p = pac.get("ordem_prioridade") or 99
                prioridade_leg = pac.get("prioridade_legal") or 0
                
                # Regra de ordenação: Manchester > Prioridade Legal > Horário de Chegada
                query_posicao = """
                    SELECT COUNT(*) as pos 
                    FROM upa_atendimentos a2
                    LEFT JOIN upa_classificacoes_risco cr2 ON a2.classificacao_risco_id = cr2.id
                    WHERE a2.status_atual = %s 
                      AND a2.id != %s
                      AND (
                          (COALESCE(cr2.ordem_prioridade, 99) < %s) OR
                          (COALESCE(cr2.ordem_prioridade, 99) = %s AND a2.prioridade_legal > %s) OR
                          (COALESCE(cr2.ordem_prioridade, 99) = %s AND a2.prioridade_legal = %s AND a2.chegada_em < %s)
                      )
                """
                cursor.execute(query_posicao, (
                    pac["status_atual"], pac["id"], 
                    ordem_p, 
                    ordem_p, prioridade_leg, 
                    ordem_p, prioridade_leg, pac["chegada_em"]
                ))
                res_pos = cursor.fetchone()
                pessoas_na_frente = res_pos['pos'] if res_pos else 0
                
                dados["paciente"] = {
                    "paciente_nome": pac.get("paciente_nome", ""),
                    "status_atual": pac.get("status_atual", ""),
                    "especialidade": pac.get("especialidade", ""),
                    "classificacao_nome": pac.get("classificacao_nome") or "Aguardando Classificação"
                }
                dados["posicao"] = pessoas_na_frente + 1
                dados["tempo_estimado"] = pessoas_na_frente * 5

        # 2. Puxa TODOS os pacientes para preencher os cards da visão geral
        query_todos = """
            SELECT a.status_atual, a.especialidade, cr.nome as classificacao_nome 
            FROM upa_atendimentos a 
            LEFT JOIN upa_classificacoes_risco cr ON a.classificacao_risco_id = cr.id 
            WHERE a.status_atual NOT IN ('FINALIZADO', 'EVASAO', 'CANCELADO')
        """
        cursor.execute(query_todos)
        todos = cursor.fetchall()
        
        for p in todos:
            status = p.get('status_atual', '')
            espec = p.get('especialidade', '')
            risco = str(p.get('classificacao_nome', '')).lower()
            
            # Contagem de Setores
            if status == 'AGUARDANDO_RECEPCAO': 
                dados['setores']['recepcao']['qtd'] += 1
            elif status == 'EM_TRIAGEM': 
                dados['setores']['classificacao']['qtd'] += 1
            elif status in ['AGUARDANDO_ATENDIMENTO', 'EM_ATENDIMENTO']:
                if espec == 'Clínico Geral': dados['setores']['clinico']['qtd'] += 1
                elif espec == 'Pediatria': dados['setores']['pediatra']['qtd'] += 1
                elif espec == 'Ortopedia': dados['setores']['ortopedia']['qtd'] += 1
                elif espec == 'Odontologia': dados['setores']['odonto']['qtd'] += 1
            elif status == 'AGUARDANDO_MEDICACAO': 
                dados['setores']['medicacao']['qtd'] += 1

            # Conta Riscos (Manchester)
            if 'emerg' in risco: dados['risco']['emergencia']['qtd'] += 1
            elif 'muito urgente' in risco: dados['risco']['muitoUrgente']['qtd'] += 1
            elif 'pouco urgente' in risco: dados['risco']['poucoUrgente']['qtd'] += 1
            elif 'urgente' in risco: dados['risco']['urgente']['qtd'] += 1
            elif 'nao' in risco or 'não' in risco: dados['risco']['naoUrgente']['qtd'] += 1

        # 3. Define total_setor do paciente lido
        if protocolo and pac:
            s_pac = pac.get("status_atual", "")
            e_pac = pac.get("especialidade", "")
            if s_pac == 'AGUARDANDO_RECEPCAO': dados["total_setor"] = dados['setores']['recepcao']['qtd']
            elif s_pac == 'EM_TRIAGEM': dados["total_setor"] = dados['setores']['classificacao']['qtd']
            elif s_pac in ['AGUARDANDO_ATENDIMENTO', 'EM_ATENDIMENTO']:
                if e_pac == 'Clínico Geral': dados["total_setor"] = dados['setores']['clinico']['qtd']
                elif e_pac == 'Pediatria': dados["total_setor"] = dados['setores']['pediatra']['qtd']
                elif e_pac == 'Ortopedia': dados["total_setor"] = dados['setores']['ortopedia']['qtd']
                elif e_pac == 'Odontologia': dados["total_setor"] = dados['setores']['odonto']['qtd']
            elif s_pac == 'AGUARDANDO_MEDICACAO': dados["total_setor"] = dados['setores']['medicacao']['qtd']

        cursor.close()
        conn.close()
    except Exception as e:
        print("Erro no banco:", e)

    return jsonify(dados)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(host=host, port=port, debug=debug)
