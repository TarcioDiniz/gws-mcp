"""Gmail, somente leitura."""

from __future__ import annotations

import base64
import html
import re

from . import auth

_HEADERS = ("From", "To", "Cc", "Subject", "Date")


def _svc(profile: str):
    return auth.service(profile, "gmail", "v1")


def _headers(payload: dict) -> dict[str, str]:
    out = {}
    for h in payload.get("headers", []):
        if h["name"] in _HEADERS:
            out[h["name"].lower()] = h["value"]
    return out


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="replace")


def _strip_html(s: str) -> str:
    s = re.sub(r"(?is)<(script|style).*?</\1>", "", s)
    s = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def _walk(part: dict, texts: dict[str, list[str]], attachments: list[dict]) -> None:
    mime = part.get("mimeType", "")
    body = part.get("body", {})
    filename = part.get("filename")
    if filename:
        attachments.append({"filename": filename, "mime_type": mime, "size": body.get("size", 0)})
    elif body.get("data") and mime in ("text/plain", "text/html"):
        texts[mime].append(_decode(body["data"]))
    for sub in part.get("parts", []) or []:
        _walk(sub, texts, attachments)


def search(profile: str, query: str, max_results: int = 10) -> list[dict]:
    svc = _svc(profile)
    resp = svc.users().messages().list(userId="me", q=query, maxResults=max(1, min(max_results, 50))).execute()
    out = []
    for m in resp.get("messages", []):
        msg = (
            svc.users()
            .messages()
            .get(userId="me", id=m["id"], format="metadata", metadataHeaders=list(_HEADERS))
            .execute()
        )
        item = {"id": msg["id"], "thread_id": msg["threadId"], "snippet": msg.get("snippet", "")}
        item.update(_headers(msg.get("payload", {})))
        item["labels"] = msg.get("labelIds", [])
        out.append(item)
    return out


def get_message(profile: str, message_id: str, max_chars: int = 20000) -> dict:
    msg = _svc(profile).users().messages().get(userId="me", id=message_id, format="full").execute()
    payload = msg.get("payload", {})
    texts: dict[str, list[str]] = {"text/plain": [], "text/html": []}
    attachments: list[dict] = []
    _walk(payload, texts, attachments)
    body = "\n".join(texts["text/plain"]).strip() or _strip_html("\n".join(texts["text/html"]))
    out = {"id": msg["id"], "thread_id": msg["threadId"], "labels": msg.get("labelIds", [])}
    out.update(_headers(payload))
    out["body"] = body[:max_chars]
    out["truncated"] = len(body) > max_chars
    out["attachments"] = attachments
    return out


def list_labels(profile: str) -> list[dict]:
    resp = _svc(profile).users().labels().list(userId="me").execute()
    return [{"id": l["id"], "name": l["name"], "type": l.get("type")} for l in resp.get("labels", [])]
