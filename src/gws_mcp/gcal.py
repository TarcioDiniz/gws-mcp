"""Calendar, somente leitura."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from . import auth


def _svc(profile: str):
    return auth.service(profile, "calendar", "v3")


def _window(time_min: str | None, time_max: str | None, default_days: int) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    tmin = time_min or now.isoformat(timespec="seconds")
    tmax = time_max or (now + timedelta(days=default_days)).isoformat(timespec="seconds")
    return tmin, tmax


def list_events(
    profile: str,
    time_min: str | None = None,
    time_max: str | None = None,
    calendar_id: str = "primary",
    query: str | None = None,
    max_results: int = 25,
) -> list[dict]:
    tmin, tmax = _window(time_min, time_max, default_days=7)
    resp = (
        _svc(profile)
        .events()
        .list(
            calendarId=calendar_id,
            timeMin=tmin,
            timeMax=tmax,
            q=query,
            singleEvents=True,
            orderBy="startTime",
            maxResults=max(1, min(max_results, 100)),
        )
        .execute()
    )
    out = []
    for e in resp.get("items", []):
        out.append(
            {
                "id": e.get("id"),
                "summary": e.get("summary"),
                "start": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
                "end": e.get("end", {}).get("dateTime") or e.get("end", {}).get("date"),
                "location": e.get("location"),
                "status": e.get("status"),
                "organizer": (e.get("organizer") or {}).get("email"),
                "attendees": [a.get("email") for a in e.get("attendees", [])],
                "hangout_link": e.get("hangoutLink"),
                "description": (e.get("description") or "")[:1000],
            }
        )
    return out


def free_busy(
    profile: str,
    time_min: str | None = None,
    time_max: str | None = None,
    calendar_ids: list[str] | None = None,
) -> dict:
    tmin, tmax = _window(time_min, time_max, default_days=1)
    ids = calendar_ids or ["primary"]
    resp = (
        _svc(profile)
        .freebusy()
        .query(body={"timeMin": tmin, "timeMax": tmax, "items": [{"id": i} for i in ids]})
        .execute()
    )
    return {
        "time_min": tmin,
        "time_max": tmax,
        "calendars": {cid: cal.get("busy", []) for cid, cal in resp.get("calendars", {}).items()},
    }
