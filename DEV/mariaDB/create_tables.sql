-- UPA Transparente — academic development schema
-- Contains table definitions only: no DROP, INSERT, patient records, or credentials.
-- Apply only to a new, empty development database.
CREATE TABLE `upa_atendimento_eventos` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `atendimento_id` bigint(20) unsigned NOT NULL,
  `unidade_id` bigint(20) unsigned NOT NULL,
  `setor_id` bigint(20) unsigned DEFAULT NULL,
  `usuario_id` bigint(20) unsigned DEFAULT NULL,
  `tipo_evento` enum('CHEGADA_QR','CHEGADA_TOTEM','CHEGADA_RECEPCAO','RECEPCAO_CHAMADO','RECEPCAO_INICIADA','RECEPCAO_FINALIZADA','TRIAGEM_CHAMADO','TRIAGEM_INICIADA','TRIAGEM_FINALIZADA','CLASSIFICACAO_DEFINIDA','CONSULTA_CHAMADO','CONSULTA_INICIADA','CONSULTA_FINALIZADA','MEDICACAO_ENCAMINHADO','OBSERVACAO_INICIADA','OBSERVACAO_FINALIZADA','ALTA','EVASAO','TRANSFERENCIA','CANCELAMENTO','REABERTURA') NOT NULL,
  `status_anterior` varchar(60) DEFAULT NULL,
  `status_novo` varchar(60) DEFAULT NULL,
  `observacao` text DEFAULT NULL,
  `criado_em` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_upa_eventos_atendimento` (`atendimento_id`),
  KEY `idx_upa_eventos_unidade_tipo` (`unidade_id`,`tipo_evento`),
  KEY `idx_upa_eventos_criado_em` (`criado_em`),
  KEY `fk_upa_eventos_setor` (`setor_id`),
  KEY `fk_upa_eventos_usuario` (`usuario_id`),
  CONSTRAINT `fk_upa_eventos_atendimento` FOREIGN KEY (`atendimento_id`) REFERENCES `upa_atendimentos` (`id`),
  CONSTRAINT `fk_upa_eventos_setor` FOREIGN KEY (`setor_id`) REFERENCES `upa_setores` (`id`),
  CONSTRAINT `fk_upa_eventos_unidade` FOREIGN KEY (`unidade_id`) REFERENCES `upa_unidades` (`id`),
  CONSTRAINT `fk_upa_eventos_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `upa_usuarios` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `upa_atendimentos` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `unidade_id` bigint(20) unsigned NOT NULL,
  `protocolo` varchar(40) NOT NULL,
  `senha` varchar(20) NOT NULL,
  `numero_senha` int(11) NOT NULL,
  `paciente_nome` varchar(180) DEFAULT NULL,
  `paciente_cpf` varchar(14) DEFAULT NULL,
  `paciente_cns` varchar(20) DEFAULT NULL,
  `paciente_data_nascimento` date DEFAULT NULL,
  `paciente_nome_mae` varchar(180) DEFAULT NULL,
  `paciente_telefone` varchar(30) DEFAULT NULL,
  `tipo_entrada` enum('QR','TOTEM','RECEPCAO') NOT NULL DEFAULT 'QR',
  `status_atual` enum('AGUARDANDO_RECEPCAO','EM_RECEPCAO','AGUARDANDO_TRIAGEM','EM_TRIAGEM','AGUARDANDO_ATENDIMENTO','EM_ATENDIMENTO','AGUARDANDO_MEDICACAO','EM_OBSERVACAO','FINALIZADO','CANCELADO','EVASAO','TRANSFERIDO') NOT NULL DEFAULT 'AGUARDANDO_RECEPCAO',
  `classificacao_risco_id` bigint(20) unsigned DEFAULT NULL,
  `especialidade` varchar(100) DEFAULT 'Clínico Geral',
  `prioridade_legal` tinyint(1) NOT NULL DEFAULT 0,
  `prioridade_descricao` varchar(120) DEFAULT NULL,
  `chegada_em` datetime NOT NULL DEFAULT current_timestamp(),
  `recepcao_inicio_em` datetime DEFAULT NULL,
  `recepcao_fim_em` datetime DEFAULT NULL,
  `triagem_inicio_em` datetime DEFAULT NULL,
  `triagem_fim_em` datetime DEFAULT NULL,
  `atendimento_inicio_em` datetime DEFAULT NULL,
  `atendimento_fim_em` datetime DEFAULT NULL,
  `finalizado_em` datetime DEFAULT NULL,
  `cancelado_em` datetime DEFAULT NULL,
  `criado_por` bigint(20) unsigned DEFAULT NULL,
  `atualizado_por` bigint(20) unsigned DEFAULT NULL,
  `criado_em` datetime NOT NULL DEFAULT current_timestamp(),
  `atualizado_em` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_upa_atendimentos_protocolo` (`protocolo`),
  KEY `idx_upa_atendimentos_unidade_status` (`unidade_id`,`status_atual`),
  KEY `idx_upa_atendimentos_chegada` (`chegada_em`),
  KEY `idx_upa_atendimentos_senha` (`senha`),
  KEY `idx_upa_atendimentos_classificacao` (`classificacao_risco_id`),
  KEY `fk_upa_atendimentos_criado_por` (`criado_por`),
  KEY `fk_upa_atendimentos_atualizado_por` (`atualizado_por`),
  CONSTRAINT `fk_upa_atendimentos_atualizado_por` FOREIGN KEY (`atualizado_por`) REFERENCES `upa_usuarios` (`id`),
  CONSTRAINT `fk_upa_atendimentos_classificacao` FOREIGN KEY (`classificacao_risco_id`) REFERENCES `upa_classificacoes_risco` (`id`),
  CONSTRAINT `fk_upa_atendimentos_criado_por` FOREIGN KEY (`criado_por`) REFERENCES `upa_usuarios` (`id`),
  CONSTRAINT `fk_upa_atendimentos_unidade` FOREIGN KEY (`unidade_id`) REFERENCES `upa_unidades` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `upa_chamadas` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `atendimento_id` bigint(20) unsigned NOT NULL,
  `unidade_id` bigint(20) unsigned NOT NULL,
  `setor_id` bigint(20) unsigned DEFAULT NULL,
  `usuario_id` bigint(20) unsigned DEFAULT NULL,
  `senha` varchar(20) NOT NULL,
  `local_chamada` varchar(120) NOT NULL,
  `tipo_chamada` enum('RECEPCAO','TRIAGEM','CONSULTORIO','MEDICACAO','OBSERVACAO') NOT NULL,
  `chamada_ativa` tinyint(1) NOT NULL DEFAULT 1,
  `chamado_em` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_upa_chamadas_unidade_ativa` (`unidade_id`,`chamada_ativa`),
  KEY `idx_upa_chamadas_chamado_em` (`chamado_em`),
  KEY `fk_upa_chamadas_atendimento` (`atendimento_id`),
  KEY `fk_upa_chamadas_setor` (`setor_id`),
  KEY `fk_upa_chamadas_usuario` (`usuario_id`),
  CONSTRAINT `fk_upa_chamadas_atendimento` FOREIGN KEY (`atendimento_id`) REFERENCES `upa_atendimentos` (`id`),
  CONSTRAINT `fk_upa_chamadas_setor` FOREIGN KEY (`setor_id`) REFERENCES `upa_setores` (`id`),
  CONSTRAINT `fk_upa_chamadas_unidade` FOREIGN KEY (`unidade_id`) REFERENCES `upa_unidades` (`id`),
  CONSTRAINT `fk_upa_chamadas_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `upa_usuarios` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `upa_classificacoes_risco` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `nome` varchar(80) NOT NULL,
  `codigo` varchar(30) NOT NULL,
  `cor` varchar(30) NOT NULL,
  `ordem_prioridade` int(11) NOT NULL,
  `tempo_alvo_minutos` int(11) NOT NULL,
  `ativo` tinyint(1) NOT NULL DEFAULT 1,
  `criado_em` datetime NOT NULL DEFAULT current_timestamp(),
  `atualizado_em` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_upa_classificacoes_codigo` (`codigo`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `upa_senhas_controle` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `unidade_id` bigint(20) unsigned NOT NULL,
  `data_referencia` date NOT NULL,
  `tipo_senha` enum('NORMAL','PRIORITARIA') NOT NULL DEFAULT 'NORMAL',
  `ultimo_numero` int(11) NOT NULL DEFAULT 0,
  `atualizado_em` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_upa_senhas_unidade_data_tipo` (`unidade_id`,`data_referencia`,`tipo_senha`),
  CONSTRAINT `fk_upa_senhas_unidade` FOREIGN KEY (`unidade_id`) REFERENCES `upa_unidades` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `upa_setores` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `unidade_id` bigint(20) unsigned NOT NULL,
  `nome` varchar(120) NOT NULL,
  `codigo` varchar(60) NOT NULL,
  `tipo` enum('RECEPCAO','TRIAGEM','CONSULTORIO','MEDICACAO','OBSERVACAO','ADMINISTRATIVO') NOT NULL,
  `ativo` tinyint(1) NOT NULL DEFAULT 1,
  `criado_em` datetime NOT NULL DEFAULT current_timestamp(),
  `atualizado_em` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_upa_setores_unidade_codigo` (`unidade_id`,`codigo`),
  KEY `idx_upa_setores_unidade` (`unidade_id`),
  CONSTRAINT `fk_upa_setores_unidade` FOREIGN KEY (`unidade_id`) REFERENCES `upa_unidades` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `upa_triagem` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `atendimento_id` bigint(20) unsigned NOT NULL,
  `gestante` tinyint(1) DEFAULT 0,
  `nivel_dor` int(11) DEFAULT NULL,
  `saturacao` decimal(5,2) DEFAULT NULL,
  `temperatura` decimal(5,2) DEFAULT NULL,
  `pressao_arterial` varchar(20) DEFAULT NULL,
  `peso` decimal(5,2) DEFAULT NULL,
  `frequencia_cardiaca` decimal(5,2) DEFAULT NULL,
  `alergias` text DEFAULT NULL,
  `queixa_observacao` text DEFAULT NULL,
  `hipertenso` tinyint(1) DEFAULT 0,
  `diabetes` tinyint(1) DEFAULT 0,
  `cancer` tinyint(1) DEFAULT 0,
  `pneumopatia` tinyint(1) DEFAULT 0,
  `tosse` tinyint(1) DEFAULT 0,
  `outros_sintomas` tinyint(1) DEFAULT 0,
  `prioridade_clinica` tinyint(1) DEFAULT 0,
  `criado_em` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_triagem_atendimento` (`atendimento_id`),
  CONSTRAINT `fk_triagem_atendimento` FOREIGN KEY (`atendimento_id`) REFERENCES `upa_atendimentos` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `upa_unidades` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `nome` varchar(180) NOT NULL,
  `codigo` varchar(50) NOT NULL,
  `endereco` varchar(255) DEFAULT NULL,
  `telefone` varchar(30) DEFAULT NULL,
  `ativo` tinyint(1) NOT NULL DEFAULT 1,
  `criado_em` datetime NOT NULL DEFAULT current_timestamp(),
  `atualizado_em` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_upa_unidades_codigo` (`codigo`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `upa_usuarios` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `nome` varchar(180) NOT NULL,
  `login` varchar(80) NOT NULL,
  `email` varchar(180) DEFAULT NULL,
  `senha_hash` varchar(255) NOT NULL,
  `perfil` enum('ADMIN','RECEPCAO','TRIAGEM','MEDICO','GESTOR','PAINEL') NOT NULL,
  `unidade_id` bigint(20) unsigned DEFAULT NULL,
  `ativo` tinyint(1) NOT NULL DEFAULT 1,
  `ultimo_acesso_em` datetime DEFAULT NULL,
  `criado_em` datetime NOT NULL DEFAULT current_timestamp(),
  `atualizado_em` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_upa_usuarios_login` (`login`),
  KEY `idx_upa_usuarios_unidade` (`unidade_id`),
  CONSTRAINT `fk_upa_usuarios_unidade` FOREIGN KEY (`unidade_id`) REFERENCES `upa_unidades` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

