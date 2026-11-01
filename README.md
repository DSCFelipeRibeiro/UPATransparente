# UPA Transparente

Aplicação web do projeto integrador da UNIVESP para transparência do fluxo de atendimento em UPAs.

Este repositório publica o código-fonte da aplicação web em `DEV/app`, o schema acadêmico em `DEV/mariaDB` e os workflows de CI/CD. Não contém registros de atendimento, dumps de banco, configurações operacionais, segredos ou arquivos de produção.

## Fluxo de mudanças

- Pull requests para `dev` executam a verificação de sintaxe; commits em `dev` podem publicar em DEV quando os segredos e a variável de habilitação estiverem configurados.
- A promoção de `dev` para `main` é feita por pull request e revisão.
- PROD é publicado manualmente a partir de `main`, com aprovação do ambiente `production` e uma referência não sensível do backup verificado.

Consulte [CONTRIBUTING.md](CONTRIBUTING.md) para o fluxo e a configuração dos ambientes do GitHub Actions.

## Banco de desenvolvimento

O schema acadêmico com as definições das nove tabelas está em [`DEV/mariaDB/create_tables.sql`](DEV/mariaDB/create_tables.sql). Ele contém apenas `CREATE TABLE` e deve ser aplicado em um banco de desenvolvimento vazio.

