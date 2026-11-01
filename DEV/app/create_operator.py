"""Create an initial UPA operator account using a privileged DB connection.

Run this only from the server's trusted shell, with DB_* variables set to a
MariaDB account that can INSERT into upa_usuarios. Never expose that account to
the Flask service or store the operator password in a file or command line.
"""

import argparse
import getpass
import os
import re

import bcrypt
import mysql.connector


PROFILES = {'ADMIN', 'RECEPCAO', 'TRIAGEM', 'MEDICO', 'GESTOR'}


def main():
    parser = argparse.ArgumentParser(description='Cria um usuário operacional da UPA.')
    parser.add_argument(
        '--sql-only', action='store_true',
        help='imprime um INSERT para enviar diretamente ao cliente MariaDB administrativo',
    )
    args = parser.parse_args()
    login = input('Login (até 80 caracteres): ').strip()
    name = input('Nome do operador: ').strip()
    profile = input('Perfil (ADMIN/RECEPCAO/TRIAGEM/MEDICO/GESTOR): ').strip().upper()
    if not re.fullmatch(r'[A-Za-z0-9._-]{3,80}', login):
        raise SystemExit('Login inválido; use 3 a 80 letras, números, ponto, hífen ou sublinhado.')
    if not name or len(name) > 180:
        raise SystemExit('Informe um nome de até 180 caracteres.')
    if profile not in PROFILES:
        raise SystemExit('Perfil inválido.')
    password = getpass.getpass('Senha: ')
    confirmation = getpass.getpass('Confirme a senha: ')
    if not password or password != confirmation:
        raise SystemExit('As senhas devem coincidir e não podem ser vazias.')

    digest = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('ascii')
    if args.sql_only:
        # Hex literals avoid quoting user input into SQL. Pipe stdout directly
        # to the MariaDB CLI; do not save the statement in a file or shell log.
        name_hex = name.encode('utf-8').hex()
        login_hex = login.encode('utf-8').hex()
        hash_hex = digest.encode('ascii').hex()
        print(
            'INSERT INTO upa_usuarios (nome, login, senha_hash, perfil, unidade_id, ativo) '
            f"VALUES (CONVERT(0x{name_hex} USING utf8mb4), "
            f"CONVERT(0x{login_hex} USING utf8mb4), "
            f"CONVERT(0x{hash_hex} USING ascii), '{profile}', 1, 1);"
        )
        return

    config = {
        'host': os.environ.get('DB_HOST', '127.0.0.1'),
        'port': int(os.environ.get('DB_PORT', 3306)),
        'user': os.environ.get('DB_USER', ''),
        'password': os.environ.get('DB_PASSWORD', ''),
        'database': os.environ.get('DB_NAME', 'filago_dev'),
        'charset': 'utf8mb4',
    }
    if not config['user'] or not config['password']:
        raise SystemExit('Configure DB_USER e DB_PASSWORD para uma conta administrativa confiável.')

    connection = mysql.connector.connect(**config)
    try:
        cursor = connection.cursor()
        cursor.execute(
            'INSERT INTO upa_usuarios (nome, login, senha_hash, perfil, unidade_id, ativo) '
            'VALUES (%s, %s, %s, %s, 1, 1)',
            (name, login, digest, profile),
        )
        connection.commit()
        print(f'Operador {login!r} criado no banco {config["database"]} com perfil {profile}.')
    finally:
        connection.close()


if __name__ == '__main__':
    main()
