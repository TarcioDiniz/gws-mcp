# Política de privacidade — gws-mcp

Última atualização: 2026-09-04.

`gws-mcp` é um servidor MCP local, de uso pessoal, que dá a um agente de IA
rodando na **sua própria máquina** acesso de leitura às suas contas Google
(Gmail, Calendar, Drive).

## O que o app faz com seus dados

- Roda apenas no computador do usuário. Não há servidor remoto, backend nem
  banco de dados do projeto.
- Os dados lidos das APIs do Google são entregues ao cliente MCP local (por
  exemplo, o Claude Code) e não são armazenados pelo `gws-mcp`.
- Os tokens de acesso ficam no Credential Manager do Windows da própria
  máquina. Nenhum token é enviado a terceiros.
- Não há telemetria, analytics nem comunicação com domínios além de
  `googleapis.com` e `accounts.google.com`.

## Escopos pedidos

Somente leitura: `gmail.readonly`, `calendar.readonly`, `drive.readonly`.
O app não envia e-mails, não cria eventos e não altera arquivos.

## Como revogar

Em <https://myaccount.google.com/permissions>, remova o app `gws-mcp`. Na
máquina, `gws-mcp accounts remove <perfil>` apaga o token local.

## Uso da API do Google

O uso e a transferência de informações recebidas das APIs do Google por este
app seguem a [Política de dados do usuário dos serviços de API do Google](https://developers.google.com/terms/api-services-user-data-policy),
incluindo os requisitos de uso limitado.

## Contato

tarciodiniz0@gmail.com
