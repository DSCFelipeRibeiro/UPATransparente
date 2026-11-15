# Schema de desenvolvimento

`create_tables.sql` define as nove tabelas da aplicação acadêmica. O arquivo contém somente instruções `CREATE TABLE`; não apaga tabelas existentes nem insere registros.

Use em um banco local/de desenvolvimento vazio. Não aplique sobre uma base que contenha dados que você queira preservar. Os dados de teste devem ser fictícios.

Exemplo, depois de criar o banco vazio e configurar o acesso local:

```sh
mariadb -u <usuario> -p <nome_do_banco_dev> < DEV/mariaDB/create_tables.sql
```

Depois, carregue os registros de referência necessários à aplicação:

```sh
mariadb -u <usuario> -p <nome_do_banco_dev> < DEV/mariaDB/seed_reference_data.sql
```

O seed contém somente a unidade, seus setores e classificações de risco. Foi extraído de um snapshot local legado de 2026-04-30; não contém usuários, credenciais, atendimentos nem dados de pacientes. Confirme os valores com a equipe antes de uso operacional.
