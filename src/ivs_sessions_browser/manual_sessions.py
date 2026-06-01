# flake8: noqa
# isort: skip_file

"""
Filename:    manual_sessions.py
Description: Load user-maintained manual sessions into the normal row format.
"""

from __future__ import annotations

import json
import re
import sys

from pathlib import Path
from typing import Any

from dateutil import parser as dparser

from . import defs as D
from .operators import load_operator_assignments


MANUAL_SESSIONS_TEMPLATE: dict[str, object] = {
    "sessions": [],
    "_example": {
        "start": "2026-06-01 12:00",
        "duration": "01:00",
        "name": "manual-example",
        "ops": "Ops Center",
        "correlator": "Correlator",
        "stations": ["Nn", "Wz"],
    },
}


def ensure_manual_sessions_file() -> None:
    path = D.CONFIG_DIR / D.MANUAL_SESSIONS_FILENAME
    if path.exists():
        return

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(MANUAL_SESSIONS_TEMPLATE, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def load_manual_session_rows(_years: list[int]) -> list[D.Row]:
    """
    Load manual sessions for the selected years.

    Accepted JSON shapes:
      - {"sessions": [{...}]}
      - [{...}]

    Required per session: start/start_date, duration/dur, name, ops,
    correlator/corr, stations. The old scheduler key is accepted as an alias.
    """

    ensure_manual_sessions_file()
    path = D.CONFIG_DIR / D.MANUAL_SESSIONS_FILENAME

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        print(f"Ignoring invalid {path}: {exc}", file=sys.stderr)
        return []

    if isinstance(raw, dict):
        sessions = raw.get("sessions", [])
    else:
        sessions = raw

    if not isinstance(sessions, list):
        print(f"Ignoring invalid {path}: expected a list or sessions list", file=sys.stderr)
        return []

    rows: list[D.Row] = []
    operator_assignments = load_operator_assignments()
    year_set = set(int(y) for y in _years)

    for idx, item in enumerate(sessions, start=1):
        if not isinstance(item, dict):
            _warn(path, idx, "expected an object")
            continue

        row = _manual_session_to_row(item, year_set, operator_assignments, path, idx)
        if row is not None:
            rows.append(row)

    return rows


def append_manual_session(item: dict[str, Any]) -> dict[str, Any]:
    """
    Append one validated manual session to manual_sessions.json.

    The returned dict is normalized for storage. This is intentionally reusable
    by importers that derive session data from .skd/.vex files.
    """

    ensure_manual_sessions_file()
    path = D.CONFIG_DIR / D.MANUAL_SESSIONS_FILENAME
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid {path}: {exc}") from exc
    except FileNotFoundError:
        raw = {"sessions": []}

    sessions: list[Any]
    if isinstance(raw, dict):
        sessions = raw.setdefault("sessions", [])
        if not isinstance(sessions, list):
            sessions = []
            raw["sessions"] = sessions
        data = raw
    elif isinstance(raw, list):
        sessions = raw
        data = {"sessions": sessions}
    else:
        sessions = []
        data = {"sessions": sessions}

    existing_names = {
        str(session.get("name", "")).strip().upper()
        for session in sessions
        if isinstance(session, dict)
    }
    normalized, errors = validate_manual_session(item, existing_names=existing_names)
    if errors or normalized is None:
        raise ValueError("; ".join(errors.values()) or "Invalid manual session")

    sessions.append(normalized)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return normalized


def delete_manual_session(name: str) -> bool:
    """
    Delete a manual session by name from manual_sessions.json.
    """

    session_name = str(name or "").strip().upper()
    if not session_name:
        return False

    ensure_manual_sessions_file()
    path = D.CONFIG_DIR / D.MANUAL_SESSIONS_FILENAME
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid {path}: {exc}") from exc
    except FileNotFoundError:
        return False

    if isinstance(raw, dict):
        sessions = raw.get("sessions", [])
        if not isinstance(sessions, list):
            return False
        data = raw
    elif isinstance(raw, list):
        sessions = raw
        data = {"sessions": sessions}
    else:
        return False

    kept = [
        session for session in sessions
        if not (isinstance(session, dict) and str(session.get("name", "")).strip().upper() == session_name)
    ]
    if len(kept) == len(sessions):
        return False

    data["sessions"] = kept
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return True


def validate_manual_session(
    item: dict[str, Any],
    *,
    existing_names: set[str] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, str]]:
    """
    Validate and normalize a manual session dict for storage.
    """

    existing_names = existing_names or set()
    errors: dict[str, str] = {}

    start_raw = item.get("start", item.get("start_date"))
    duration = item.get("duration", item.get("dur"))
    name = str(item.get("name", "")).strip().upper()
    ops = item.get("ops", item.get("scheduler"))
    correlator = item.get("correlator", item.get("corr"))
    stations_raw = item.get("stations")

    for key, value in (
        ("start", start_raw),
        ("duration", duration),
        ("name", name),
        ("ops", ops),
        ("correlator", correlator),
        ("stations", stations_raw),
    ):
        if value in (None, ""):
            errors[key] = f"{key} is required"

    start_dt = None
    if start_raw not in (None, ""):
        try:
            start_dt = dparser.parse(str(start_raw))
        except (ValueError, TypeError, OverflowError):
            errors["start"] = "start must be a valid date/time"

    stations, station_error = normalize_station_tokens(stations_raw)
    if station_error:
        errors["stations"] = station_error
    if stations_raw not in (None, "") and not stations:
        errors["stations"] = "stations must contain at least one station"

    if name and name in existing_names:
        errors["name"] = f"name '{name}' already exists"

    if errors or start_dt is None:
        return None, errors

    session_type = str(item.get("type", "Manual")).strip().upper() or "MANUAL"
    status = str(item.get("status", "Manual")).strip() or "Manual"

    return {
        "start": start_dt.strftime("%Y-%m-%d %H:%M"),
        "duration": str(duration).strip(),
        "name": name,
        "type": session_type,
        "ops": str(ops).strip().upper(),
        "correlator": str(correlator).strip().upper(),
        "stations": stations,
        "db": str(item.get("db", "")).strip(),
        "status": status,
        "analysis": str(item.get("analysis", "")).strip(),
    }, {}


def build_manual_session_row(item: dict[str, Any], operator_assignments: dict[str, str] | None = None) -> D.Row | None:
    """
    Convert one validated manual session dict into the normal row format.
    """

    normalized, errors = validate_manual_session(item)
    if errors or normalized is None:
        return None

    return _manual_session_to_row(
        normalized,
        {dparser.parse(str(normalized["start"])).year},
        operator_assignments or load_operator_assignments(),
        D.CONFIG_DIR / D.MANUAL_SESSIONS_FILENAME,
        1,
    )


def _manual_session_to_row(
    item: dict[str, Any],
    year_set: set[int],
    operator_assignments: dict[str, str],
    path: Path,
    idx: int,
) -> D.Row | None:
    normalized, errors = validate_manual_session(item)
    if errors or normalized is None:
        _warn(path, idx, "; ".join(errors.values()) or "invalid session")
        return None

    try:
        start_dt = dparser.parse(str(normalized["start"]))
    except (ValueError, TypeError, OverflowError) as exc:
        _warn(path, idx, f"invalid start date: {exc}")
        return None

    if start_dt.year not in year_set:
        return None

    stations = _normalize_stations(normalized["stations"])
    if not stations:
        _warn(path, idx, "stations must be a non-empty string or list")
        return None

    code = str(normalized["name"]).strip()
    op = operator_assignments.get(code, "")
    session_type = str(normalized.get("type", "Manual")).strip() or "Manual"

    values = [
        op,
        session_type,
        code,
        start_dt.strftime("%Y-%m-%d %H:%M"),
        f"{start_dt.timetuple().tm_yday:03d}",
        str(normalized["duration"]).strip(),
        stations,
        str(normalized.get("db", "")).strip(),
        str(normalized["ops"]).strip(),
        str(normalized["correlator"]).strip(),
        str(normalized.get("status", "Manual")).strip() or "Manual",
        str(normalized.get("analysis", "")).strip(),
    ]

    meta = {
        "intensive": False,
        "code": code,
        "active": stations,
        "removed": "",
        "manual": True,
    }

    return (values, None, meta)


def _normalize_stations(value: Any) -> str:
    if isinstance(value, str):
        return "".join(value.replace(",", " ").split())

    if isinstance(value, list):
        parts = [str(part).strip() for part in value if str(part).strip()]
        return "".join(parts)

    return ""


def normalize_station_tokens(value: Any) -> tuple[list[str], str | None]:
    """
    Normalize station input.

    Accepted text forms:
      Ns, Nn
      Ns Nn
      Ns|Nn
      NsNn
    """

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return [], None

        if re.search(r"[\s,|]+", text):
            parts = [part for part in re.split(r"[\s,|]+", text) if part]
        else:
            if len(text) % 2 != 0:
                return [], "stations must be 2-character codes, e.g. Ns,Nn or NsNn"
            parts = [text[i:i + 2] for i in range(0, len(text), 2)]

        return _validate_station_parts(parts)

    if isinstance(value, list):
        parts = [str(part).strip() for part in value if str(part).strip()]
        return _validate_station_parts(parts)

    return [], None


def format_station_tokens(value: Any) -> str:
    stations, error = normalize_station_tokens(value)
    if error or not stations:
        return str(value or "")
    return ", ".join(stations)


def _validate_station_parts(parts: list[str]) -> tuple[list[str], str | None]:
    invalid = [part for part in parts if len(part) != 2 or not part.isalnum()]
    if invalid:
        return [], "stations must be 2-character codes, e.g. Ns,Nn or NsNn"
    return parts, None




def _warn(path: Path, idx: int, message: str) -> None:
    print(f"Ignoring manual session #{idx} in {path}: {message}", file=sys.stderr)
