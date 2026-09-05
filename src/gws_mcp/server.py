"""Servidor MCP (stdio). Incremento 1: somente leitura.

Toda ferramenta recebe `profile`, o nome da conta configurada com
`gws-mcp accounts add <profile>`. Nenhuma ferramenta altera estado no Google.
"""

from __future__ import annotations

import functools
import logging
import sys

from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from . import auth, drive, gcal, gmail, store

logging.basicConfig(stream=sys.stderr, level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

mcp = MCPServer(
    name="gws-mcp",
    instructions=(
        "Google Workspace, somente leitura, multi-conta. Toda ferramenta exige `profile`, "
        "o nome de uma conta configurada. Use `accounts_list` para descobrir os perfis "
        "e a qual e-mail/empresa cada um corresponde. Datas em RFC3339 (ex.: 2026-09-04T00:00:00-03:00)."
    ),
)

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=True)


def safe(fn):
    """Converte excecoes em mensagens curtas, sem segredos."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except auth.GwsError as e:
            return {"error": str(e)}
        except RefreshError:
            prof = kwargs.get("profile") or (args[0] if args else "?")
            return {"error": f"Token do perfil '{prof}' invalido ou revogado. Rode: gws-mcp accounts add {prof}"}
        except HttpError as e:
            return {"error": f"Google API HTTP {e.status_code}: {e.reason}"}
        except Exception as e:  # noqa: BLE001
            logging.getLogger("gws-mcp").warning("erro inesperado: %s", type(e).__name__)
            return {"error": f"Erro inesperado: {type(e).__name__}"}

    return wrapper


# ---------- contas ----------


@mcp.tool(annotations=READ_ONLY)
@safe
def accounts_list() -> dict:
    """Lista os perfis (contas Google) configurados, com e-mail e escopos."""
    profiles = store.load_profiles()
    return {
        "profiles": [
            {"profile": name, "email": p.get("email"), "added": p.get("added"), "scopes": p.get("scopes")}
            for name, p in sorted(profiles.items())
        ]
    }


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True))
@safe
def accounts_add(profile: str) -> dict:
    """Adiciona uma conta Google: abre o navegador para consentimento (somente leitura) e guarda o token no Credential Manager.
    `profile` e um apelido curto, ex.: 'pessoal', 'trabalho', 'cliente'."""
    email = auth.add_profile(profile)
    return {"profile": profile, "email": email, "status": "adicionada"}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=False))
@safe
def accounts_remove(profile: str) -> dict:
    """Remove um perfil local e apaga o refresh token do Credential Manager. Nao altera nada no Google."""
    auth.validate_profile_name(profile)
    existed = store.remove_profile(profile)
    return {"profile": profile, "status": "removida" if existed else "nao existia"}


# ---------- gmail ----------


@mcp.tool(annotations=READ_ONLY)
@safe
def gmail_search(profile: str, query: str, max_results: int = 10) -> dict:
    """Busca mensagens com a sintaxe do Gmail (ex.: 'from:x@y.com newer_than:7d is:unread'). Devolve cabecalhos e snippet."""
    return {"messages": gmail.search(profile, query, max_results)}


@mcp.tool(annotations=READ_ONLY)
@safe
def gmail_get_message(profile: str, message_id: str, max_chars: int = 20000) -> dict:
    """Le uma mensagem pelo id: cabecalhos, corpo em texto e lista de anexos (nome/tamanho, sem conteudo)."""
    return gmail.get_message(profile, message_id, max_chars)


@mcp.tool(annotations=READ_ONLY)
@safe
def gmail_list_labels(profile: str) -> dict:
    """Lista os rotulos (labels) da conta."""
    return {"labels": gmail.list_labels(profile)}


# ---------- calendar ----------


@mcp.tool(annotations=READ_ONLY)
@safe
def calendar_list_events(
    profile: str,
    time_min: str | None = None,
    time_max: str | None = None,
    calendar_id: str = "primary",
    query: str | None = None,
    max_results: int = 25,
) -> dict:
    """Lista eventos entre time_min e time_max (RFC3339). Sem datas: proximos 7 dias. Recorrentes vem expandidos."""
    return {"events": gcal.list_events(profile, time_min, time_max, calendar_id, query, max_results)}


@mcp.tool(annotations=READ_ONLY)
@safe
def calendar_free_busy(
    profile: str,
    time_min: str | None = None,
    time_max: str | None = None,
    calendar_ids: list[str] | None = None,
) -> dict:
    """Blocos ocupados por calendario no intervalo (RFC3339). Sem datas: proximas 24h. Calendario padrao: 'primary'."""
    return gcal.free_busy(profile, time_min, time_max, calendar_ids)


# ---------- drive ----------


@mcp.tool(annotations=READ_ONLY)
@safe
def drive_search(profile: str, query: str | None = None, raw_q: str | None = None, max_results: int = 20) -> dict:
    """Busca arquivos. `query` procura no nome e no texto. `raw_q` aceita a sintaxe de busca do Drive (ex.: "mimeType='application/pdf'")."""
    return {"files": drive.search(profile, query, raw_q, max_results)}


@mcp.tool(annotations=READ_ONLY)
@safe
def drive_read_file(profile: str, file_id: str, max_chars: int = 50000) -> dict:
    """Le o conteudo de um arquivo como texto. Docs vira texto, Sheets vira CSV, Slides vira texto. Binarios devolvem so metadados."""
    return drive.read_file(profile, file_id, max_chars)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
