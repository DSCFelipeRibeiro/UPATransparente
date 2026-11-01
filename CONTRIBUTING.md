# Contribuição e publicação

## Branches

- Desenvolva em branches curtas e abra pull requests para `dev`.
- Pull requests e pushes em `dev` executam a verificação de sintaxe Python.
- Após revisão e validação em DEV, abra um pull request de `dev` para `main`.
- PROD não é publicado por push. Inicie manualmente `Promote to PROD` na branch `main`, informe uma referência não sensível dos backups verificados e aguarde aprovação do ambiente `production`.

## Configuração do GitHub Actions

Crie os ambientes `development` e `production` e configure os segredos por ambiente:

| Ambiente | Segredos |
|---|---|
| `development` | `DEV_HOST`, `DEV_USER`, `DEV_SSH_PRIVATE_KEY`, `DEV_SSH_KNOWN_HOSTS` |
| `production` | `PROD_HOST`, `PROD_USER`, `PROD_SSH_PRIVATE_KEY`, `PROD_SSH_KNOWN_HOSTS` |

No ambiente `development`, crie também a variável `DEV_DEPLOY_ENABLED=true` depois de verificar os quatro segredos. A branch `dev` deve ser permitida nesse ambiente. Restrinja a branch `main` ao ambiente `production` e configure revisores obrigatórios nesse ambiente.
A UPA e o BrincaEscola usam a mesma VM Oracle. Configure `DEV_HOST` e `PROD_HOST` com o mesmo endereço da VM e use `ubuntu` nos segredos `DEV_USER` e `PROD_USER`. As chaves de deploy precisam ser autorizadas nessa VM; podem ser cadastradas separadamente por ambiente. Os workflows da UPA atuam apenas em `/home/ubuntu/upatransparente-dev` e `/home/ubuntu/upatransparente-prod`, reiniciando apenas os serviços `upatransparente-dev.service` e `upatransparente-prod.service`.

Use uma chave de deploy dedicada e restrita. Verifique a identidade do host por canal confiável antes de cadastrar `*_SSH_KNOWN_HOSTS`. Nunca grave valores secretos no repositório ou em logs. Os workflows não recebem segredos em execuções de pull request.

## Limites de publicação

Os workflows enviam apenas `DEV/app` para `/home/ubuntu/upatransparente-dev` ou `/home/ubuntu/upatransparente-prod`. Arquivos `.env`, `venv`, bytecode e dados locais ficam excluídos. O deploy não aplica migrações, executa SQL, altera Nginx ou reinicia serviços de outros projetos.

Antes de PROD, faça e verifique os backups privados exigidos pelo procedimento operacional da UPA. As aplicações tratam dados de saúde: valide mudanças em DEV somente com registros sintéticos e não copie dados de pacientes para GitHub Actions.

