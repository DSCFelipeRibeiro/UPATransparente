-- Dados de referência para desenvolvimento local.
-- Recorte apenas das tabelas de unidade, setores e classificações de risco
-- do dump local legado de filago_schema.sql (snapshot de 2026-04-30).
-- Não contém usuários, credenciais, atendimentos ou dados de pacientes.
-- Aplicar depois de create_tables.sql, em um banco de desenvolvimento vazio.

INSERT INTO `upa_unidades`
  (`id`, `nome`, `codigo`, `endereco`, `telefone`, `ativo`)
VALUES
  (1, 'UPA Central', 'UPA-CENTRAL', NULL, NULL, 1)
ON DUPLICATE KEY UPDATE
  `nome` = VALUES(`nome`),
  `endereco` = VALUES(`endereco`),
  `telefone` = VALUES(`telefone`),
  `ativo` = VALUES(`ativo`);

INSERT INTO `upa_classificacoes_risco`
  (`id`, `nome`, `codigo`, `cor`, `ordem_prioridade`, `tempo_alvo_minutos`, `ativo`)
VALUES
  (1, 'Emergência', 'VERMELHO', '#dc3545', 1, 0, 1),
  (2, 'Muito Urgente', 'LARANJA', '#fd7e14', 2, 10, 1),
  (3, 'Urgente', 'AMARELO', '#ffc107', 3, 60, 1),
  (4, 'Pouco Urgente', 'VERDE', '#28a745', 4, 120, 1),
  (5, 'Não Urgente', 'AZUL', '#0d6efd', 5, 240, 1)
ON DUPLICATE KEY UPDATE
  `nome` = VALUES(`nome`),
  `cor` = VALUES(`cor`),
  `ordem_prioridade` = VALUES(`ordem_prioridade`),
  `tempo_alvo_minutos` = VALUES(`tempo_alvo_minutos`),
  `ativo` = VALUES(`ativo`);

INSERT INTO `upa_setores`
  (`id`, `unidade_id`, `nome`, `codigo`, `tipo`, `ativo`)
VALUES
  (1, 1, 'Recepção 1', 'RECEPCAO-01', 'RECEPCAO', 1),
  (2, 1, 'Triagem 1', 'TRIAGEM-01', 'TRIAGEM', 1),
  (3, 1, 'Consultório 1', 'CONSULTORIO-01', 'CONSULTORIO', 1),
  (4, 1, 'Consultório 2', 'CONSULTORIO-02', 'CONSULTORIO', 1),
  (5, 1, 'Medicação', 'MEDICACAO-01', 'MEDICACAO', 1),
  (6, 1, 'Observação', 'OBSERVACAO-01', 'OBSERVACAO', 1)
ON DUPLICATE KEY UPDATE
  `nome` = VALUES(`nome`),
  `tipo` = VALUES(`tipo`),
  `ativo` = VALUES(`ativo`);
