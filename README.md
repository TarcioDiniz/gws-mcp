# gws-mcp

Servidor MCP local, em Python, para Google Workspace. Multi-conta por desenho:
cada conta Google é um **perfil nomeado** (`pessoal`, `trabalho`, `cliente`)
e toda ferramenta recebe qual perfil usar.

Feito porque os conectores oficiais do Google são por conta da Claude, não por
projeto, e os servidores de terceiros não têm massa crítica para receber acesso
a e-mail corporativo.

## Estado atual — incremento 1 (somente leitura)

| Serviço | Ferramentas | Testado com conta real |
|---|---|---|
| Contas | `accounts_list`, `accounts_add`, `accounts_remove` | sim, 2026-09-04, dois perfis (`accounts_remove` só em teste unitário) |
| Gmail | `gmail_search`, `gmail_get_message`, `gmail_list_labels` | sim, 2026-09-04 |
| Calendar | `calendar_list_events`, `calendar_free_busy` | sim, 2026-09-04 (agenda vazia no período) |
| Drive | `drive_search`, `drive_read_file` | sim, 2026-09-04 (Sheets exportado como CSV) |

Ainda não existe: Docs, Sheets, qualquer escrita (enviar e-mail, criar evento,
editar planilha). Os escopos OAuth pedidos são só `*.readonly`; o servidor não
tem como alterar nada no Google mesmo que uma ferramenta tentasse.

## Onde ficam os segredos

- **Refresh token** de cada perfil: Credential Manager do Windows, entrada
  `profile:<nome>@gws-mcp`.
- **OAuth client** (`client_id`/`client_secret`): Credential Manager, entrada
  `oauth-client@gws-mcp`.
- **Metadados sem segredo** (nome do perfil, e-mail, escopos, data):
  `%APPDATA%\gws-mcp\profiles.json`.

Nada de token em arquivo de texto, em log ou em mensagem de erro. Nenhuma
telemetria. O servidor só fala com `googleapis.com` e `accounts.google.com`.

## Estado do setup nesta máquina

Feito em 2026-09-04: projeto `gws-mcp-507701` na conta pessoal, três APIs
ativas, consentimento Externo **publicado (Em produção)**, cliente Desktop,
perfis `pessoal` e `trabalho` autorizados e testados. Registrado no Claude
Code com `--scope local` na pasta `robo`.

Para publicar, o Google exigiu página inicial e política de privacidade
públicas. Por isso o repositório ficou público e existe o `PRIVACY.md`;
`github.com` está nos domínios autorizados. Sem verificação do Google a tela
"app não verificado" aparece no consentimento, e é esperado.

Armadilha: o "Salvar" de usuários de teste no console só gravou na segunda
tentativa. Sem o e-mail na lista, em modo Testing, o consentimento devolve
`Erro 403: access_denied`. Em produção a lista deixa de importar.

## Setup (uma vez)

1. Criar o OAuth client no Google Cloud Console:
   - projeto novo (ou existente) na conta pessoal;
   - **APIs & Services → Library**: ativar *Gmail API*, *Google Calendar API*,
     *Google Drive API*;
   - **OAuth consent screen**: tipo *External*, adicionar os três e-mails como
     *test users* (enquanto o app estiver em "Testing", só eles conseguem
     autorizar; nessa fase o refresh token expira em 7 dias — ver abaixo);
   - **Credentials → Create → OAuth client ID → Desktop app**.
2. Guardar o client no Credential Manager. Ou por variáveis de ambiente:

   ```powershell
   $env:GWS_CLIENT_ID = "..."; $env:GWS_CLIENT_SECRET = "..."
   uv run gws-mcp setup
   Remove-Item Env:GWS_CLIENT_ID, Env:GWS_CLIENT_SECRET
   ```

   ou pelo JSON baixado do console (apague o arquivo depois):

   ```powershell
   uv run gws-mcp setup --from-file C:\caminho\client_secret_xxx.json
   ```

3. Adicionar contas. Abre o navegador para o consentimento:

   ```powershell
   uv run gws-mcp accounts add pessoal
   uv run gws-mcp accounts add trabalho
   uv run gws-mcp accounts list
   ```

4. Conectar no Claude Code, na pasta onde deve valer:

   ```powershell
   claude mcp add --scope local gws -- uv --directory C:\Users\Developer\Documents\Trabalho\Pessoal\gws-mcp run gws-mcp serve
   ```

### Sobre "Testing" vs "In production"

Com o consent screen em *Testing*, o Google expira o refresh token em 7 dias.
Para não repetir `accounts add` toda semana, publicar o app (*Publish app*).
Sem verificação do Google aparece a tela "app não verificado" no consentimento,
mas o token deixa de expirar. Como o client é seu e só você usa, é aceitável.

## Uso

Toda ferramenta exige `profile`. Comece por `accounts_list` para ver os perfis
e a qual e-mail cada um corresponde. Datas em RFC3339
(`2026-09-04T09:00:00-03:00`).

## Desenvolvimento

```powershell
uv sync
uv run gws-mcp --help
```

Estrutura em `src/gws_mcp/`:

| Arquivo | Papel |
|---|---|
| `store.py` | Credential Manager + `profiles.json` |
| `auth.py` | escopos, fluxo OAuth, credenciais por perfil |
| `gmail.py`, `gcal.py`, `drive.py` | chamadas à API, sem lógica de MCP |
| `server.py` | ferramentas MCP e tratamento de erro sem segredos |
| `cli.py` | `setup`, `accounts`, `serve` |

## Próximos incrementos

Um de cada vez, só depois de o anterior rodar em uso real por alguns dias:

1. Docs (leitura)
2. Sheets (leitura)
3. Escrita: enviar e-mail, criar evento, editar planilha. Exige novos escopos e
   novo consentimento em cada perfil.
