# flake8: noqa
# isort: skip_file

"""
Filename:    session_file_import.py
Description: Import local schedule files as manual sessions.
"""

from __future__ import annotations

import re

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from . import defs as D
from .manual_sessions import append_manual_session, validate_manual_session


@dataclass
class ImportResult:
    imported: list[str]
    skipped: list[str]
    errors: list[str]


def import_local_session_files(directory: Path, existing_codes: set[str]) -> ImportResult:
    imported: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []
    seen_codes = {code.strip().upper() for code in existing_codes if code.strip()}

    parsers = (
        ("*.vex", parse_vex_session),
        ("*.skd", parse_skd_session),
    )
    for pattern, parser in parsers:
        for path in sorted(directory.glob(pattern)):
            _import_session_file(path, parser, seen_codes, imported, skipped, errors)

    return ImportResult(imported=imported, skipped=skipped, errors=errors)


def _import_session_file(
    path: Path,
    parser: Any,
    seen_codes: set[str],
    imported: list[str],
    skipped: list[str],
    errors: list[str],
) -> None:
    try:
        session = parser(path)
    except ValueError as exc:
        errors.append(f"{path.name}: {exc}")
        return

    code = str(session.get("name", "")).strip().upper()
    if not code:
        errors.append(f"{path.name}: missing session code")
        return

    if code in seen_codes:
        skipped.append(code)
        return

    try:
        append_manual_session(session)
    except ValueError as exc:
        errors.append(f"{path.name}: {exc}")
        return

    seen_codes.add(code)
    imported.append(code)


def parse_skd_session(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")

    name = _find_skd_experiment_name(text) or path.stem
    scheduler, correlator, start_raw, stop_raw = _find_skd_param_metadata(text)
    if not start_raw:
        raise ValueError("missing START in $PARAM")

    start_dt = _parse_skd_datetime(start_raw)
    if start_dt is None:
        raise ValueError("invalid START in $PARAM")

    stop_dt = _parse_skd_datetime(stop_raw) if stop_raw else None
    duration = _format_duration(start_dt, stop_dt)
    stations = _skd_station_codes(text)
    if not stations:
        raise ValueError("no stations found")

    session = {
        "type": "SKD",
        "name": name,
        "start": start_dt.strftime("%Y-%m-%d %H:%M"),
        "duration": duration,
        "ops": scheduler or "UNKNOWN",
        "correlator": correlator or "UNKNOWN",
        "stations": stations,
    }
    normalized, errors = validate_manual_session(session)
    if errors or normalized is None:
        raise ValueError("; ".join(errors.values()) or "invalid SKD session")
    return normalized


def parse_vex_session(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    uncommented = _strip_vex_comments(text)

    name = _find_first_value(uncommented, "exper_name")
    if not name:
        name = _find_global_experiment_ref(uncommented)
    if not name:
        name = path.stem

    start_raw = _find_first_value(uncommented, "exper_nominal_start")
    stop_raw = _find_first_value(uncommented, "exper_nominal_stop")
    start_dt = _parse_vex_datetime(start_raw) if start_raw else None
    stop_dt = _parse_vex_datetime(stop_raw) if stop_raw else None
    if start_dt is None:
        raise ValueError("missing or invalid exper_nominal_start")

    duration = _format_duration(start_dt, stop_dt)
    ops = _clean_vex_value(_find_first_value(uncommented, "scheduler_name") or "UNKNOWN")
    correlator = _clean_vex_value(_find_first_value(uncommented, "target_correlator") or "UNKNOWN")
    stations = _scheduled_stations(uncommented)
    if not stations:
        stations = _defined_stations(uncommented)
    if not stations:
        raise ValueError("no stations found")

    session = {
        "type": "VEX",
        "name": _clean_vex_value(name),
        "start": start_dt.strftime("%Y-%m-%d %H:%M"),
        "duration": duration,
        "ops": ops,
        "correlator": correlator,
        "stations": stations,
    }
    normalized, errors = validate_manual_session(session)
    if errors or normalized is None:
        raise ValueError("; ".join(errors.values()) or "invalid VEX session")
    return normalized


def existing_session_codes(rows: list[D.Row]) -> set[str]:
    code_idx = D.FIELD_INDEX.get("code", 2)
    return {
        values[code_idx].strip().upper()
        for values, _url, _meta in rows
        if len(values) > code_idx and values[code_idx].strip()
    }


def _find_skd_experiment_name(text: str) -> str | None:
    match = re.search(r"^\s*\$EXPER\s+(\S+)", text, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip()


def _find_skd_param_metadata(text: str) -> tuple[str | None, str | None, str | None, str | None]:
    match = re.search(
        r"^\s*SCHEDULER\s+(?P<scheduler>.*?)\s+CORRELATOR\s+(?P<correlator>\S+)"
        r"\s+START\s+(?P<start>\d+)(?:\s+END\s+(?P<end>\d+))?",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if not match:
        return None, None, None, None
    return (
        match.group("scheduler").strip(),
        match.group("correlator").strip(),
        match.group("start").strip(),
        (match.group("end") or "").strip() or None,
    )


def _parse_skd_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None

    match = re.fullmatch(r"(\d{2})(\d{3})(\d{2})(\d{2})(\d{2})", str(value).strip())
    if not match:
        return None

    year_2, doy, hour, minute, second = (int(part) for part in match.groups())
    year = 2000 + year_2 if year_2 < 70 else 1900 + year_2
    try:
        base = datetime.strptime(f"{year} {doy:03d}", "%Y %j")
        return base.replace(hour=hour, minute=minute, second=second)
    except ValueError:
        return None


def _skd_station_codes(text: str) -> list[str]:
    station_block = _find_skd_block(text, "STATIONS")
    if not station_block:
        return []

    stations: list[str] = []
    for line in station_block.splitlines():
        if line.lstrip().startswith("*"):
            continue
        match = re.match(r"^\s*A\s+\S+\s+\S+.*?\s+([A-Za-z0-9]{2})\s+[A-Za-z0-9-]{2}\s+[A-Za-z0-9-]{2}\s*$", line)
        if not match:
            continue
        station = match.group(1)
        if station not in stations:
            stations.append(station)

    if stations:
        return stations

    for line in station_block.splitlines():
        if line.lstrip().startswith("*"):
            continue
        match = re.match(r"^\s*T\s+([A-Za-z0-9]{2})\b", line)
        if not match:
            continue
        station = match.group(1)
        if station not in stations:
            stations.append(station)

    return stations


def _find_skd_block(text: str, name: str) -> str | None:
    match = re.search(
        rf"^\s*\${re.escape(name)}\s*$\n(.*?)(?=^\s*\$|\Z)",
        text,
        flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    if not match:
        return None
    return match.group(1)


def _strip_vex_comments(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.lstrip().startswith("*"):
            continue
        if "*" in line:
            line = line.split("*", 1)[0]
        lines.append(line)
    return "\n".join(lines)


def _find_first_value(text: str, key: str) -> str | None:
    match = re.search(rf"\b{re.escape(key)}\s*=\s*([^;]+);", text, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip()


def _find_global_experiment_ref(text: str) -> str | None:
    match = re.search(r"ref\s+\$EXPER\s*=\s*([^;]+);", text, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip()


def _clean_vex_value(value: str) -> str:
    text = str(value or "").strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        text = text[1:-1]
    return text.strip()


def _parse_vex_datetime(value: str) -> datetime | None:
    text = _clean_vex_value(value)
    match = re.fullmatch(r"(\d{4})y(\d{1,3})d(\d{1,2})h(\d{1,2})m(\d{1,2})s", text, flags=re.IGNORECASE)
    if not match:
        return None
    year, doy, hour, minute, second = (int(part) for part in match.groups())
    base = datetime.strptime(f"{year} {doy:03d}", "%Y %j")
    return base.replace(hour=hour, minute=minute, second=second)


def _format_duration(start_dt: datetime, stop_dt: datetime | None) -> str:
    if stop_dt is None:
        return "24:00"
    if stop_dt < start_dt:
        stop_dt = stop_dt + timedelta(days=1)

    total_minutes = max(0, round((stop_dt - start_dt).total_seconds() / 60))
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}:{minutes:02d}"


def _scheduled_stations(text: str) -> list[str]:
    stations: list[str] = []
    for match in re.finditer(r"^\s*station\s*=\s*([A-Za-z0-9]{2})\s*:", text, flags=re.IGNORECASE | re.MULTILINE):
        station = match.group(1)
        if station not in stations:
            stations.append(station)
    return stations


def _defined_stations(text: str) -> list[str]:
    station_block = re.search(r"\$STATION;(.*?)(?:^\$|\Z)", text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
    if not station_block:
        return []
    stations: list[str] = []
    for match in re.finditer(r"^\s*def\s+([A-Za-z0-9]{2})\s*;", station_block.group(1), flags=re.IGNORECASE | re.MULTILINE):
        station = match.group(1)
        if station not in stations:
            stations.append(station)
    return stations

