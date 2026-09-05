"""OAuth com as bibliotecas oficiais do Google. Nada de segredo em log."""

from __future__ import annotations

import re

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from . import store

# Incremento 1: somente leitura. Nenhum escopo de escrita.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

TOKEN_URI = "https://oauth2.googleapis.com/token"
PROFILE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")


class GwsError(Exception):
    """Erro seguro para mostrar ao usuario (sem segredos)."""


def validate_profile_name(name: str) -> str:
    if not PROFILE_RE.match(name):
        raise GwsError("Nome de perfil invalido. Use letras minusculas, numeros, '-' ou '_' (max 32).")
    return name


def _client() -> dict[str, str]:
    client = store.get_oauth_client()
    if not client:
        raise GwsError("OAuth client nao configurado. Rode: gws-mcp setup")
    return client


def add_profile(name: str) -> str:
    """Abre o navegador, faz o consentimento e guarda o refresh token. Devolve o e-mail."""
    validate_profile_name(name)
    client = _client()
    config = {
        "installed": {
            "client_id": client["client_id"],
            "client_secret": client["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": TOKEN_URI,
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(config, SCOPES)
    # authorization_prompt_message="" evita print no stdout (que e o canal do MCP).
    creds = flow.run_local_server(
        port=0,
        authorization_prompt_message="",
        success_message="gws-mcp: conta autorizada. Pode fechar esta aba.",
        # prompt=consent garante refresh_token mesmo se ja houve consentimento antes.
        prompt="consent",
    )
    if not creds.refresh_token:
        raise GwsError("Google nao devolveu refresh token. Revogue o acesso em myaccount.google.com/permissions e tente de novo.")
    email = build("gmail", "v1", credentials=creds, cache_discovery=False).users().getProfile(userId="me").execute()["emailAddress"]
    store.set_refresh_token(name, creds.refresh_token)
    store.upsert_profile(name, email, SCOPES)
    return email


def credentials_for(profile: str) -> Credentials:
    profiles = store.load_profiles()
    if profile not in profiles:
        known = ", ".join(sorted(profiles)) or "(nenhum)"
        raise GwsError(f"Perfil '{profile}' nao existe. Perfis conhecidos: {known}")
    token = store.get_refresh_token(profile)
    if not token:
        raise GwsError(f"Perfil '{profile}' sem refresh token no Credential Manager. Rode: gws-mcp accounts add {profile}")
    client = _client()
    return Credentials(
        token=None,
        refresh_token=token,
        token_uri=TOKEN_URI,
        client_id=client["client_id"],
        client_secret=client["client_secret"],
        scopes=profiles[profile].get("scopes", SCOPES),
    )


def service(profile: str, api: str, version: str):
    return build(api, version, credentials=credentials_for(profile), cache_discovery=False)
