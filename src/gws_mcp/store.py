"""Onde as coisas ficam guardadas.

Segredos (client OAuth e refresh tokens) vao para o Credential Manager do
Windows, via `keyring`. Metadados nao sigilosos (nome do perfil, e-mail, data)
vao para um JSON em %APPDATA%/gws-mcp/profiles.json.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import keyring

SERVICE = "gws-mcp"
CLIENT_KEY = "oauth-client"


def _profile_key(name: str) -> str:
    return f"profile:{name}"


# ---------- segredos (Credential Manager) ----------


def set_oauth_client(client_id: str, client_secret: str) -> None:
    keyring.set_password(SERVICE, CLIENT_KEY, json.dumps({"client_id": client_id, "client_secret": client_secret}))


def get_oauth_client() -> dict[str, str] | None:
    raw = keyring.get_password(SERVICE, CLIENT_KEY)
    return json.loads(raw) if raw else None


def set_refresh_token(profile: str, refresh_token: str) -> None:
    keyring.set_password(SERVICE, _profile_key(profile), refresh_token)


def get_refresh_token(profile: str) -> str | None:
    return keyring.get_password(SERVICE, _profile_key(profile))


def delete_refresh_token(profile: str) -> None:
    try:
        keyring.delete_password(SERVICE, _profile_key(profile))
    except keyring.errors.PasswordDeleteError:
        pass


# ---------- metadados (arquivo, sem segredos) ----------


def _profiles_path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "gws-mcp" / "profiles.json"


def load_profiles() -> dict[str, dict]:
    p = _profiles_path()
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _save_profiles(profiles: dict[str, dict]) -> None:
    p = _profiles_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(profiles, indent=2, ensure_ascii=False), encoding="utf-8")


def upsert_profile(name: str, email: str, scopes: list[str]) -> None:
    profiles = load_profiles()
    profiles[name] = {
        "email": email,
        "scopes": scopes,
        "added": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    _save_profiles(profiles)


def remove_profile(name: str) -> bool:
    profiles = load_profiles()
    existed = profiles.pop(name, None) is not None
    _save_profiles(profiles)
    delete_refresh_token(name)
    return existed
