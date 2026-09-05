"""CLI: gws-mcp setup | accounts add|list|remove | serve"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import auth, store


def cmd_setup(args: argparse.Namespace) -> int:
    if args.from_file:
        data = json.loads(Path(args.from_file).read_text(encoding="utf-8"))
        node = data.get("installed") or data.get("web") or {}
        client_id, client_secret = node.get("client_id"), node.get("client_secret")
        origem = f"arquivo {args.from_file}"
    else:
        client_id = os.environ.get("GWS_CLIENT_ID")
        client_secret = os.environ.get("GWS_CLIENT_SECRET")
        origem = "variaveis GWS_CLIENT_ID / GWS_CLIENT_SECRET"
    if not client_id or not client_secret:
        print(f"setup: client_id/client_secret nao encontrados em {origem}.", file=sys.stderr)
        return 2
    store.set_oauth_client(client_id, client_secret)
    print(f"OAuth client guardado no Credential Manager (origem: {origem}).")
    if args.from_file:
        print("Apague o arquivo JSON agora; ele nao e mais necessario.")
    return 0


def cmd_accounts_add(args: argparse.Namespace) -> int:
    try:
        email = auth.add_profile(args.profile)
    except auth.GwsError as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    print(f"Perfil '{args.profile}' adicionado: {email}")
    return 0


def cmd_accounts_list(_: argparse.Namespace) -> int:
    profiles = store.load_profiles()
    if not profiles:
        print("Nenhum perfil. Rode: gws-mcp accounts add <nome>")
        return 0
    for name, p in sorted(profiles.items()):
        tem_token = "ok" if store.get_refresh_token(name) else "SEM TOKEN"
        print(f"{name:<16} {p.get('email','?'):<40} {tem_token}")
    return 0


def cmd_accounts_remove(args: argparse.Namespace) -> int:
    existed = store.remove_profile(args.profile)
    print(f"Perfil '{args.profile}' {'removido' if existed else 'nao existia'}.")
    return 0


def cmd_serve(_: argparse.Namespace) -> int:
    from .server import main as serve

    serve()
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="gws-mcp", description="Servidor MCP local para Google Workspace, multi-conta.")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("setup", help="guarda o OAuth client (client_id/secret) no Credential Manager")
    s.add_argument("--from-file", help="JSON baixado do Google Cloud Console (apague depois)")
    s.set_defaults(fn=cmd_setup)

    a = sub.add_parser("accounts", help="gerencia perfis (contas)")
    asub = a.add_subparsers(dest="acmd", required=True)
    x = asub.add_parser("add", help="autoriza uma conta no navegador")
    x.add_argument("profile")
    x.set_defaults(fn=cmd_accounts_add)
    x = asub.add_parser("list")
    x.set_defaults(fn=cmd_accounts_list)
    x = asub.add_parser("remove")
    x.add_argument("profile")
    x.set_defaults(fn=cmd_accounts_remove)

    s = sub.add_parser("serve", help="inicia o servidor MCP (stdio)")
    s.set_defaults(fn=cmd_serve)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
