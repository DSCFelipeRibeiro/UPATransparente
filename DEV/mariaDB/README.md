# Schema de desenvolvimento

`create_tables.sql` define as nove tabelas da aplicação acadêmica. O arquivo contém somente instruções `CREATE TABLE`; não apaga tabelas existentes nem insere registros.

Use em um banco local/de desenvolvimento vazio. Não aplique sobre uma base que contenha dados que você queira preservar. Os dados de teste devem ser fictícios.

Exemplo, depois de criar o banco vazio e configurar o acesso local:

```sh
mariadb -u <usuario> -p <nome_do_banco_dev> < DEV/mariaDB/create_tables.sql
```
