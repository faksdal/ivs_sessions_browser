# flake8: noqa
# isort: skip_file

"""
Defined in statistics.py

Filename:       statistics.py
Author:         jole
Created:        19.04.2026

Description:    Compute compact session statistics from loaded IVS rows.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
from typing import Callable

from . import defs as D


START_FORMAT        = "%Y-%m-%d %H:%M"
STATION_TOKEN_RE    = re.compile(r"[A-Z][a-z0-9]")
REMOVED_BLOCK_RE    = re.compile(r"\[[^\]]*\]")
NUMERIC_RE          = re.compile(r"\d+(?:\.\d+)?")
PROGRAM_PREFIX_RE   = re.compile(r"^[A-Za-z]+\d*")

DEFAULT_TYPE_WEIGHTS: dict[str, float] = {
    "intensive": 1.5,
    "default": 1.0,
}

DEFAULT_STATUS_WEIGHTS: dict[str, float] = {
    "released": 1.0,
    "processing": 0.7,
    "waiting": 0.4,
    "cancelled": 0.0,
}


@dataclass
class SessionStatistics:
    row_count: int
    unique_codes: int
    intensive_count: int
    rows_with_operator: int
    start_min: datetime | None
    start_max: datetime | None
    by_year: Counter[int]
    by_type: Counter[str]
    by_ops_center: Counter[str]
    by_correlator: Counter[str]
    by_status: Counter[str]
    by_operator: Counter[str]
    by_station: Counter[str]
    by_program: Counter[str]
    by_year_hours: Counter[int]
    by_program_hours: Counter[str]
    stations_per_session: Counter[int]
    total_observed_hours: float
    total_active_station_mentions: int
    total_baselines: int
    total_baseline_hours: float
    cancelled_count: int
    non_cancelled_count: int
    reduced_network_count: int



def _safe_value(values: list[str], field: str) -> str:
    idx = D.FIELD_INDEX.get(field, -1)
    if idx < 0 or idx >= len(values):
        return ""
    return (values[idx] or "").strip()



def _parse_start(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None

    try:
        return datetime.strptime(text, START_FORMAT)
    except ValueError:
        return None



def _parse_duration_hours(value: str) -> float:
    """
    Parse a duration field into hours.

    Supports common schedule formats such as:
    - "24" (hours)
    - "12.5" (hours)
    - "12h"
    - "HH:MM" (e.g., "01:30" -> 1.5)
    """

    text = (value or "").strip().lower()
    if not text:
        return 0.0

    if ":" in text:
        hh, mm = text.split(":", 1)
        try:
            return max(float(hh), 0.0) + (max(float(mm), 0.0) / 60.0)
        except ValueError:
            return 0.0

    m = NUMERIC_RE.search(text)
    if not m:
        return 0.0

    try:
        return max(float(m.group(0)), 0.0)
    except ValueError:
        return 0.0



def _station_tokens(values: list[str], meta: dict, include_removed: bool = True) -> list[str]:
    active = (meta.get("active") or "").strip()
    removed = (meta.get("removed") or "").strip()

    # Prefer metadata if available since it separates active/removed reliably.
    if include_removed:
        source = f"{active} {removed}".strip()
    else:
        source = active

    if not source:
        source = _safe_value(values, "stations")

    # Fallback safety: if only active stations are requested but metadata is
    # unavailable, strip removed block(s) often rendered as "[HbMgSa]".
    if not include_removed and source:
        source = REMOVED_BLOCK_RE.sub("", source)

    return STATION_TOKEN_RE.findall(source)



def _program_bucket(values: list[str], meta: dict) -> str:
    """
    Build a coarse, stable program bucket from type/code metadata.
    """

    if bool(meta.get("intensive")):
        return "INT"

    type_text = _safe_value(values, "type").strip()
    code = _safe_value(values, "code").strip().upper()
    type_lower = type_text.lower()

    if "vgos" in type_lower or code.startswith("VG"):
        return "VGOS"
    if code.startswith("R1"):
        return "R1"
    if code.startswith("R4"):
        return "R4"

    if type_text:
        m = PROGRAM_PREFIX_RE.match(type_text)
        if m:
            return m.group(0).upper()
        return type_text.upper()

    if code:
        m = PROGRAM_PREFIX_RE.match(code)
        if m:
            return m.group(0).upper()

    return "UNKNOWN"



def _status_bucket(value: str) -> str:
    text = (value or "").strip().lower()
    if not text:
        return "unknown"
    if "cancel" in text:
        return "cancelled"
    if "release" in text:
        return "released"
    if "process" in text:
        return "processing"
    if "wait" in text:
        return "waiting"
    return text



def summarize_rows(rows: list[D.Row]) -> SessionStatistics:
    by_year: Counter[int] = Counter()
    by_type: Counter[str] = Counter()
    by_ops_center: Counter[str] = Counter()
    by_correlator: Counter[str] = Counter()
    by_status: Counter[str] = Counter()
    by_operator: Counter[str] = Counter()
    by_station: Counter[str] = Counter()
    by_program: Counter[str] = Counter()
    by_year_hours: Counter[int] = Counter()
    by_program_hours: Counter[str] = Counter()
    stations_per_session: Counter[int] = Counter()

    unique_codes: set[str] = set()
    rows_with_operator = 0
    intensive_count = 0
    total_observed_hours = 0.0
    total_active_station_mentions = 0
    total_baselines = 0
    total_baseline_hours = 0.0
    cancelled_count = 0
    non_cancelled_count = 0
    reduced_network_count = 0
    start_values: list[datetime] = []

    for values, _url, meta in rows:
        code = _safe_value(values, "code")
        if code:
            unique_codes.add(code)

        op = _safe_value(values, "op")
        if op:
            rows_with_operator += 1
            by_operator[op] += 1

        type_value = _safe_value(values, "type")
        if type_value:
            by_type[type_value] += 1

        ops_center = _safe_value(values, "ops")
        if ops_center:
            by_ops_center[ops_center] += 1

        correlator = _safe_value(values, "corr")
        if correlator:
            by_correlator[correlator] += 1

        status = _safe_value(values, "status")
        if status:
            by_status[status] += 1

        status_group = _status_bucket(status)
        if status_group == "cancelled":
            cancelled_count += 1
        else:
            non_cancelled_count += 1

        if bool(meta.get("intensive")):
            intensive_count += 1

        duration_hours = _parse_duration_hours(_safe_value(values, "dur"))
        total_observed_hours += duration_hours

        program = _program_bucket(values, meta)
        by_program[program] += 1
        by_program_hours[program] += duration_hours

        start_dt = _parse_start(_safe_value(values, "start"))
        if start_dt is not None:
            start_values.append(start_dt)
            by_year[start_dt.year] += 1
            by_year_hours[start_dt.year] += duration_hours

        active_stations = set(_station_tokens(values, meta, include_removed=False))
        n_stations = len(active_stations)
        stations_per_session[n_stations] += 1
        total_active_station_mentions += n_stations

        if 0 < n_stations < 3:
            reduced_network_count += 1

        baselines = (n_stations * (n_stations - 1)) // 2
        total_baselines += baselines
        total_baseline_hours += float(baselines) * duration_hours

        for token in _station_tokens(values, meta):
            by_station[token] += 1

    start_min = min(start_values) if start_values else None
    start_max = max(start_values) if start_values else None

    return SessionStatistics(
        row_count=len(rows),
        unique_codes=len(unique_codes),
        intensive_count=intensive_count,
        rows_with_operator=rows_with_operator,
        start_min=start_min,
        start_max=start_max,
        by_year=by_year,
        by_type=by_type,
        by_ops_center=by_ops_center,
        by_correlator=by_correlator,
        by_status=by_status,
        by_operator=by_operator,
        by_station=by_station,
        by_program=by_program,
        by_year_hours=by_year_hours,
        by_program_hours=by_program_hours,
        stations_per_session=stations_per_session,
        total_observed_hours=total_observed_hours,
        total_active_station_mentions=total_active_station_mentions,
        total_baselines=total_baselines,
        total_baseline_hours=total_baseline_hours,
        cancelled_count=cancelled_count,
        non_cancelled_count=non_cancelled_count,
        reduced_network_count=reduced_network_count,
    )



def _format_counter(counter: Counter, top_n: int) -> str:
    if not counter:
        return "-"

    def _fmt_count(value: float | int) -> str:
        if isinstance(value, float):
            return f"{value:.1f}" if not value.is_integer() else f"{int(value)}"
        return str(value)

    parts: list[str] = []
    for key, count in counter.most_common(top_n):
        parts.append(f"{key}({_fmt_count(count)})")
    return ", ".join(parts)



def _format_year_hours(counter: Counter[int], top_n: int) -> str:
    if not counter:
        return "-"

    parts: list[str] = []
    for year, value in sorted(counter.items(), key=lambda item: item[0], reverse=True)[:top_n]:
        parts.append(f"{year}({value:.1f}h)")
    return ", ".join(parts)



def _trend_text(counter: Counter[int], unit: str) -> str:
    """
    Return compact trend text from earliest to latest year.
    """

    if len(counter) < 2:
        return "-"

    years = sorted(counter.keys())
    first_year = years[0]
    last_year = years[-1]
    first_val = float(counter[first_year])
    last_val = float(counter[last_year])
    delta = last_val - first_val

    if first_val > 0:
        pct = (100.0 * delta / first_val)
        sign = "+" if delta >= 0 else ""
        return f"{first_year}->{last_year}: {first_val:.1f}{unit} to {last_val:.1f}{unit} ({sign}{pct:.1f}%)"

    sign = "+" if delta >= 0 else ""
    return f"{first_year}->{last_year}: {first_val:.1f}{unit} to {last_val:.1f}{unit} ({sign}{delta:.1f}{unit})"



def build_statistics_report(all_rows: list[D.Row], view_rows: list[D.Row], top_n: int = 8) -> list[str]:
    """
    Defined in statistics.py

    Build a list of human-readable statistics lines from the provided rows.
    """

    all_stats   = summarize_rows(all_rows)
    view_stats  = summarize_rows(view_rows)

    intensive_pct = 0.0
    if all_stats.row_count > 0:
        intensive_pct = 100.0 * all_stats.intensive_count / all_stats.row_count

    if all_stats.start_min and all_stats.start_max:
        span = f"{all_stats.start_min:%Y-%m-%d} .. {all_stats.start_max:%Y-%m-%d}"
    else:
        span = "-"

    visible_share = 0.0
    if all_stats.row_count > 0:
        visible_share = 100.0 * view_stats.row_count / all_stats.row_count

    avg_duration_hours = (all_stats.total_observed_hours / all_stats.row_count) if all_stats.row_count else 0.0
    avg_stations = (all_stats.total_active_station_mentions / all_stats.row_count) if all_stats.row_count else 0.0
    avg_baselines = (all_stats.total_baselines / all_stats.row_count) if all_stats.row_count else 0.0

    cancelled_pct = (100.0 * all_stats.cancelled_count / all_stats.row_count) if all_stats.row_count else 0.0
    non_cancelled_pct = (100.0 * all_stats.non_cancelled_count / all_stats.row_count) if all_stats.row_count else 0.0

    year_count = len(all_stats.by_year)
    sessions_per_year = (all_stats.row_count / year_count) if year_count else 0.0
    hours_per_year = (all_stats.total_observed_hours / year_count) if year_count else 0.0

    lines = [
        "Session Statistics",
        f"Loaded rows: {all_stats.row_count}",
        f"Visible rows: {view_stats.row_count} ({visible_share:.1f}%)",
        f"Unique session codes: {all_stats.unique_codes}",
        f"Intensive sessions: {all_stats.intensive_count} ({intensive_pct:.1f}%)",
        f"Rows with operator assignment: {all_stats.rows_with_operator}",
        f"Total scheduled hours: {all_stats.total_observed_hours:.1f}",
        f"Average session duration: {avg_duration_hours:.2f}h",
        f"Average active stations/session: {avg_stations:.2f}",
        f"Average baselines/session: {avg_baselines:.2f}",
        f"Total baseline-hours proxy: {all_stats.total_baseline_hours:.1f}",
        f"Cancelled sessions: {all_stats.cancelled_count} ({cancelled_pct:.1f}%)",
        f"Non-cancelled proxy success: {all_stats.non_cancelled_count} ({non_cancelled_pct:.1f}%)",
        f"Reduced-network sessions (<3 stations): {all_stats.reduced_network_count}",
        f"Date span: {span}",
        f"Sessions/year (avg): {sessions_per_year:.1f}",
        f"Hours/year (avg): {hours_per_year:.1f}",
        f"Session trend: {_trend_text(all_stats.by_year, '')}",
        f"Hours trend: {_trend_text(all_stats.by_year_hours, 'h')}",
        f"Years: {_format_counter(all_stats.by_year, top_n)}",
        f"Yearly hours: {_format_year_hours(all_stats.by_year_hours, top_n)}",
        f"Program mix: {_format_counter(all_stats.by_program, top_n)}",
        f"Program hours: {_format_counter(all_stats.by_program_hours, top_n)}",
        f"Top stations: {_format_counter(all_stats.by_station, top_n)}",
        f"Top correlators: {_format_counter(all_stats.by_correlator, top_n)}",
        f"Top ops centers: {_format_counter(all_stats.by_ops_center, top_n)}",
        f"Top types: {_format_counter(all_stats.by_type, top_n)}",
        f"Top statuses: {_format_counter(all_stats.by_status, top_n)}",
        f"Top operators: {_format_counter(all_stats.by_operator, top_n)}",
    ]

    station_lines = station_contribution_summary(all_rows, top_n=top_n)
    if station_lines:
        lines.append("Top station contribution (sessions % | hours | weighted):")
        lines.extend(station_lines)

    return lines



def station_contribution_percentages(rows: list[D.Row], top_n: int | None = None) -> list[tuple[str, int, float]]:
    """
    Defined in statistics.py

    Return station participation percentages from the provided rows.

    Participation is calculated as session share over all sessions:
    - each station is counted at most once per session
    - removed stations are excluded
    - percent = sessions_with_station / total_sessions * 100

    :param rows: Session rows to analyze.
    :param top_n: Optional cap on number of returned stations.
    :return: List of (station, session_count, percent), sorted descending.
    """

    total_sessions = len(rows)
    if total_sessions <= 0:
        return []

    sessions_by_station: Counter[str] = Counter()
    for values, _url, meta in rows:
        stations_in_session = set(_station_tokens(values, meta, include_removed=False))
        for station in stations_in_session:
            sessions_by_station[station] += 1

    items = sessions_by_station.most_common(top_n)
    return [
        (station, count, (100.0 * count / total_sessions))
        for station, count in items
    ]



def station_contribution_metrics(
    rows: list[D.Row],
    top_n: int | None = None,
    type_weights: dict[str, float] | None = None,
    status_weights: dict[str, float] | None = None,
) -> list[dict[str, float | int | str]]:
    """
    Compute station contribution metrics using session count, share, hours,
    and weighted hours.

    A station is counted at most once per session and removed stations are
    excluded.
    """

    total_sessions = len(rows)
    if total_sessions <= 0:
        return []

    type_w = {
        **DEFAULT_TYPE_WEIGHTS,
        **(type_weights or {}),
    }
    status_w = {
        **DEFAULT_STATUS_WEIGHTS,
        **(status_weights or {}),
    }

    session_count_by_station: Counter[str] = Counter()
    hours_by_station: Counter[str] = Counter()
    weighted_by_station: Counter[str] = Counter()

    for values, _url, meta in rows:
        stations_in_session = set(_station_tokens(values, meta, include_removed=False))
        if not stations_in_session:
            continue

        duration_hours = _parse_duration_hours(_safe_value(values, "dur"))

        session_type = ("intensive" if bool(meta.get("intensive")) else "default")
        type_factor = float(type_w.get(session_type, type_w.get("default", 1.0)))

        status = _safe_value(values, "status").lower()
        status_factor = float(status_w.get(status, 1.0))

        weighted_hours = duration_hours * type_factor * status_factor

        for station in stations_in_session:
            session_count_by_station[station] += 1
            hours_by_station[station] += duration_hours
            weighted_by_station[station] += weighted_hours

    def _sort_key(item: tuple[str, int]) -> tuple[float, int, str]:
        station, session_count = item
        return (
            weighted_by_station.get(station, 0.0),
            session_count,
            station,
        )

    sorted_stations = sorted(
        session_count_by_station.items(),
        key=_sort_key,
        reverse=True,
    )

    if top_n is not None:
        sorted_stations = sorted_stations[:top_n]

    results: list[dict[str, float | int | str]] = []
    for station, session_count in sorted_stations:
        session_share_pct = 100.0 * float(session_count) / float(total_sessions)
        hours = float(hours_by_station.get(station, 0.0))
        weighted = float(weighted_by_station.get(station, 0.0))

        results.append(
            {
                "station": station,
                "session_count": int(session_count),
                "session_share_pct": session_share_pct,
                "hours": hours,
                "weighted_hours": weighted,
            }
        )

    return results



def station_contribution_summary(rows: list[D.Row], top_n: int = 8) -> list[str]:
    """
    Build compact textual station contribution lines for stats UI.
    """

    metrics = station_contribution_metrics(rows, top_n=top_n)
    lines: list[str] = []
    for item in metrics:
        station = str(item["station"])
        session_count = int(item["session_count"])
        session_share_pct = float(item["session_share_pct"])
        hours = float(item["hours"])
        weighted_hours = float(item["weighted_hours"])
        lines.append(
            f"  {station}: {session_count} ({session_share_pct:.1f}%) | {hours:.1f}h | {weighted_hours:.1f}wh"
        )

    return lines



def write_station_contribution_plot(
    rows: list[D.Row],
    output_path: str | Path | None = None,
    top_n: int | None = None,
    chart_type: str = "barh",
    metric: str = "session_share_pct",
    aggregate_below_pct: float | None = None,
    others_label: str = "Others",
) -> Path:
    """
    Defined in statistics.py

    Called by the main loop, This is the main entry point
    for generating a station contribution plot. For now it is linked to the 'G'
    key.

    Create a station contribution plot.

    :param rows: Session rows to analyze.
    :param output_path: Output PNG path. If None, auto-generate in current dir.
    :param top_n: Number of stations to include (descending by participation).
                  If None, include all stations.
    :param chart_type: Plot style. Supported values are "barh" and "pie".
    :param aggregate_below_pct: If set to a positive value, stations with
                                participation percentage lower than this value
                                are grouped into a single "Others" entry.
    :param others_label: Label to use for the grouped "Others" entry.
    :return: Path to saved PNG file.
    :raises ValueError: If no station tokens are available.
    """

    metrics = station_contribution_metrics(rows, top_n=top_n)
    if not metrics:
        raise ValueError("No station data available for plotting")

    if metric not in {"session_share_pct", "hours", "weighted_hours"}:
        raise ValueError(f"Unsupported metric '{metric}'")

    station_data: list[tuple[str, int, float]] = []
    for item in metrics:
        station = str(item["station"])
        session_count = int(item["session_count"])
        metric_value = float(item[metric])
        station_data.append((station, session_count, metric_value))

    if aggregate_below_pct is not None and aggregate_below_pct > 0:
        kept: list[tuple[str, int, float]] = []
        others_count = 0
        others_pct = 0.0

        total_mentions = sum(count for _station, count, _pct in station_data)

        for station, count, pct in station_data:
            # For pie charts, users read percentages as slice share, so apply
            # threshold using that same denominator.
            if chart_type == "pie" and total_mentions > 0:
                compare_pct = 100.0 * count / total_mentions
            else:
                compare_pct = pct

            if compare_pct < aggregate_below_pct:
                others_count += count
                others_pct += pct
            else:
                kept.append((station, count, pct))

        if others_count > 0:
            kept.append((others_label, others_count, others_pct))

        station_data = kept

    # Lazy import so non-plot workflows do not require matplotlib at import time.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [item[0] for item in station_data]
    counts = [item[1] for item in station_data]
    values = [item[2] for item in station_data]

    if metric == "session_share_pct":
        x_label = "Sessions with station (%)"
        title   = "Station Participation by Session (%)"
        value_fmt: Callable[[float], str] = lambda val: f"{val:.1f}%"
        
    elif metric == "hours":
        x_label     = "Scheduled observing hours"
        title       = "Station Contribution by Scheduled Hours"
        value_fmt   = lambda val: f"{val:.1f}h"
    else:
        x_label = "Weighted contribution hours"
        title       = "Station Contribution by Weighted Hours"
        value_fmt   = lambda val: f"{val:.1f}wh"

    if output_path is None:
        ts  = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = Path(f"station-contribution-{ts}.png")
    else:
        out = Path(output_path)

    if chart_type == "pie":
        fig, ax = plt.subplots(figsize=(10.5, 8.5))

        # Pie slices use each station's share of all participation mentions.
        wedges, _texts, _autotexts = ax.pie(
            values,
            labels=labels,
            autopct="%1.1f%%",
            startangle=120,
            pctdistance=0.75,
            wedgeprops={"linewidth": 0.8, "edgecolor": "white"},
            textprops={"fontsize": 9},
        )
        ax.set_title(title)
        ax.axis("equal")

    else:
        labels = labels[::-1]
        values = values[::-1]

        fig_h = max(5.0, min(24.0, 1.2 + 0.42 * len(labels)))
        fig, ax = plt.subplots(figsize=(11.5, fig_h))

        bars = ax.barh(labels, values, color="#2f6c8f", alpha=0.9)
        ax.set_xlabel(x_label)
        ax.set_title(title)
        ax.set_xlim(0, max(values) * 1.12)
        ax.grid(axis="x", linestyle="--", alpha=0.35)

        for bar, value in zip(bars, values):
            y = bar.get_y() + (bar.get_height() / 2.0)
            ax.text(
                bar.get_width() + 0.15,
                y,
                value_fmt(value),
                va="center",
                ha="left",
                fontsize=9,
            )

    fig.tight_layout()
    fig.savefig(out, dpi=160)
    plt.close(fig)
    return out
