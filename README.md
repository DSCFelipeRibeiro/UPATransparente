# UPA Transparente

Aplicação web do projeto integrador da UNIVESP para transparência do fluxo de atendimento em UPAs.

## Apresentação do projeto

[Assista ao vídeo de apresentação do UPA Transparente](https://youtu.be/7hIOg88dh14?is=tiGV1FhJzjUmX6nn).

## Contexto acadêmico e créditos

Projeto Integrador em Computação do Eixo de Computação da Universidade Virtual do Estado de São Paulo (UNIVESP), no primeiro semestre de 2026, vinculado ao Polo Jandira, na Zona Oeste da Região Metropolitana de São Paulo. O projeto foi desenvolvido por estudantes de Bacharelado em Tecnologia da Informação (BTI), Bacharelado em Ciência de Dados e Engenharia de Computação. É um projeto acadêmico, não um sistema operacional de atendimento médico.

**Facilitadora pedagógica:** Jessica de Oliveira Fernandes.

**Integrantes:**

- Daniele Hora Nogueira Santos
- Ednéia Rodrigues de Lima Silva
- Felipe Alex Ribeiro
- Jose Valdir Ribeiro
- Kélli do Prado Fernandes
- Matheus Pinheiro de Lima Rodrigues
- Mikael Josias Rodrigues
- Renan Santos Andrade

Este repositório publica o código-fonte da aplicação web em `DEV/app`, o schema acadêmico em `DEV/mariaDB` e os workflows de CI/CD. Não contém registros de atendimento, dumps de banco, configurações operacionais, segredos ou arquivos de produção.

## Fluxo de mudanças

- Pull requests para `dev` executam a verificação de sintaxe; commits em `dev` podem publicar em DEV quando os segredos e a variável de habilitação estiverem configurados.
- A promoção de `dev` para `main` é feita por pull request e revisão.
- PROD é publicado manualmente a partir de `main`, com aprovação do ambiente `production` e uma referência não sensível do backup verificado.

Consulte [CONTRIBUTING.md](CONTRIBUTING.md) para o fluxo e a configuração dos ambientes do GitHub Actions.

## Banco de desenvolvimento

O schema acadêmico com as definições das nove tabelas está em [`DEV/mariaDB/create_tables.sql`](DEV/mariaDB/create_tables.sql). Ele contém apenas `CREATE TABLE` e deve ser aplicado em um banco de desenvolvimento vazio.

