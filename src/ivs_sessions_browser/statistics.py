# flake8: noqa
# isort: skip_file

"""
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

from . import defs as D


START_FORMAT = "%Y-%m-%d %H:%M"
STATION_TOKEN_RE    = re.compile(r"[A-Z][a-z0-9]")


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



def _station_tokens(values: list[str], meta: dict) -> list[str]:
    active = (meta.get("active") or "").strip()
    removed = (meta.get("removed") or "").strip()

    # Prefer metadata if available since it separates active/removed reliably.
    source = f"{active} {removed}".strip()
    if not source:
        source = _safe_value(values, "stations")

    return STATION_TOKEN_RE.findall(source)



def summarize_rows(rows: list[D.Row]) -> SessionStatistics:
    by_year: Counter[int] = Counter()
    by_type: Counter[str] = Counter()
    by_ops_center: Counter[str] = Counter()
    by_correlator: Counter[str] = Counter()
    by_status: Counter[str] = Counter()
    by_operator: Counter[str] = Counter()
    by_station: Counter[str] = Counter()

    unique_codes: set[str] = set()
    rows_with_operator = 0
    intensive_count = 0
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

        if bool(meta.get("intensive")):
            intensive_count += 1

        start_dt = _parse_start(_safe_value(values, "start"))
        if start_dt is not None:
            start_values.append(start_dt)
            by_year[start_dt.year] += 1

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
    )



def _format_counter(counter: Counter, top_n: int) -> str:
    if not counter:
        return "-"

    parts: list[str] = []
    for key, count in counter.most_common(top_n):
        parts.append(f"{key}({count})")
    return ", ".join(parts)



def build_statistics_report(all_rows: list[D.Row], view_rows: list[D.Row], top_n: int = 8) -> list[str]:
    all_stats = summarize_rows(all_rows)
    view_stats = summarize_rows(view_rows)

    intensive_pct = 0.0
    if all_stats.row_count > 0:
        intensive_pct = 100.0 * all_stats.intensive_count / all_stats.row_count

    if all_stats.start_min and all_stats.start_max:
        span = f"{all_stats.start_min:%Y-%m-%d} .. {all_stats.start_max:%Y-%m-%d}"
    else:
        span = "-"

    lines = [
        "Session Statistics",
        f"Loaded rows: {all_stats.row_count}",
        f"Visible rows: {view_stats.row_count}",
        f"Unique session codes: {all_stats.unique_codes}",
        f"Intensive sessions: {all_stats.intensive_count} ({intensive_pct:.1f}%)",
        f"Rows with operator assignment: {all_stats.rows_with_operator}",
        f"Date span: {span}",
        f"Years: {_format_counter(all_stats.by_year, top_n)}",
        f"Top stations: {_format_counter(all_stats.by_station, top_n)}",
        f"Top correlators: {_format_counter(all_stats.by_correlator, top_n)}",
        f"Top ops centers: {_format_counter(all_stats.by_ops_center, top_n)}",
        f"Top types: {_format_counter(all_stats.by_type, top_n)}",
        f"Top statuses: {_format_counter(all_stats.by_status, top_n)}",
        f"Top operators: {_format_counter(all_stats.by_operator, top_n)}",
    ]

    return lines



def station_contribution_percentages(rows: list[D.Row], top_n: int | None = None) -> list[tuple[str, int, float]]:
    """
    Return station contribution percentages from the provided rows.

    Contribution is calculated as station-token share over all station tokens:
    percent = count / total_station_tokens * 100

    :param rows: Session rows to analyze.
    :param top_n: Optional cap on number of returned stations.
    :return: List of (station, count, percent), sorted descending by count.
    """

    stats = summarize_rows(rows)
    total = sum(stats.by_station.values())
    if total <= 0:
        return []

    items = stats.by_station.most_common(top_n)
    return [(station, count, (100.0 * count / total)) for station, count in items]



def write_station_contribution_plot(
    rows: list[D.Row],
    output_path: str | Path | None = None,
    top_n: int = 20,
) -> Path:
    """
    Create a horizontal bar chart of station contribution percentages.

    :param rows: Session rows to analyze.
    :param output_path: Output PNG path. If None, auto-generate in current dir.
    :param top_n: Number of stations to include (descending by contribution).
    :return: Path to saved PNG file.
    :raises ValueError: If no station tokens are available.
    """

    station_data = station_contribution_percentages(rows, top_n=top_n)
    if not station_data:
        raise ValueError("No station data available for plotting")

    # Lazy import so non-plot workflows do not require matplotlib at import time.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [item[0] for item in station_data][::-1]
    percentages = [item[2] for item in station_data][::-1]

    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = Path(f"station-contribution-{ts}.png")
    else:
        out = Path(output_path)

    fig_h = max(5.0, min(14.0, 1.2 + 0.42 * len(labels)))
    fig, ax = plt.subplots(figsize=(11.5, fig_h))

    bars = ax.barh(labels, percentages, color="#2f6c8f", alpha=0.9)
    ax.set_xlabel("Contribution (%)")
    ax.set_title("Station Contribution by Percentage")
    ax.set_xlim(0, max(percentages) * 1.12)
    ax.grid(axis="x", linestyle="--", alpha=0.35)

    for bar, pct in zip(bars, percentages):
        y = bar.get_y() + (bar.get_height() / 2.0)
        ax.text(
            bar.get_width() + 0.15,
            y,
            f"{pct:.1f}%",
            va="center",
            ha="left",
            fontsize=9,
        )

    fig.tight_layout()
    fig.savefig(out, dpi=160)
    plt.close(fig)
    return out
