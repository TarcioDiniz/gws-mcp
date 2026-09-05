"""Drive, somente leitura."""

from __future__ import annotations

import io

from googleapiclient.http import MediaIoBaseDownload

from . import auth

_FIELDS = "id,name,mimeType,modifiedTime,size,webViewLink,owners(emailAddress)"
_EXPORT = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}
_TEXT_PREFIXES = ("text/", "application/json", "application/xml", "application/x-yaml")


def _svc(profile: str):
    return auth.service(profile, "drive", "v3")


def _slim(f: dict) -> dict:
    return {
        "id": f.get("id"),
        "name": f.get("name"),
        "mime_type": f.get("mimeType"),
        "modified": f.get("modifiedTime"),
        "size": int(f["size"]) if f.get("size") else None,
        "link": f.get("webViewLink"),
        "owner": (f.get("owners") or [{}])[0].get("emailAddress"),
    }


def search(profile: str, query: str | None = None, raw_q: str | None = None, max_results: int = 20) -> list[dict]:
    if raw_q:
        q = raw_q
    elif query:
        safe = query.replace("\\", "\\\\").replace("'", "\\'")
        q = f"(name contains '{safe}' or fullText contains '{safe}') and trashed = false"
    else:
        q = "trashed = false"
    resp = (
        _svc(profile)
        .files()
        .list(
            q=q,
            pageSize=max(1, min(max_results, 100)),
            fields=f"files({_FIELDS})",
            orderBy="modifiedTime desc",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        .execute()
    )
    return [_slim(f) for f in resp.get("files", [])]


def read_file(profile: str, file_id: str, max_chars: int = 50000) -> dict:
    svc = _svc(profile)
    meta = svc.files().get(fileId=file_id, fields=_FIELDS, supportsAllDrives=True).execute()
    mime = meta.get("mimeType", "")
    out = _slim(meta)
    if mime in _EXPORT:
        req = svc.files().export_media(fileId=file_id, mimeType=_EXPORT[mime])
    elif mime.startswith(_TEXT_PREFIXES):
        req = svc.files().get_media(fileId=file_id, supportsAllDrives=True)
    else:
        out["content"] = None
        out["note"] = f"Tipo {mime} nao e texto; so metadados devolvidos."
        return out
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    text = buf.getvalue().decode("utf-8", errors="replace")
    out["content"] = text[:max_chars]
    out["truncated"] = len(text) > max_chars
    return out
