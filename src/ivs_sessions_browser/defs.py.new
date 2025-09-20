"""
Filename:   defs.py (refactor suggestion)
Author:     jole (proposed tidy by ChatGPT)
Created:    2025-09-20

Purpose:
  Centralize shared types and small, stable constants while avoiding mutable
  module‑level state. Header widths are computed on demand from data instead of
  mutating globals.

Drop‑in plan:
  - Replace your current defs.py with this file (or import the parts you want).
  - Update callers of `recompute_header_widths` to call `compute_headers(...)`
    and use the returned tuple instead of relying on mutated globals.
"""
# --- Import section ---------------------------------------------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any, Iterable
import argparse
import curses
# --- END OF Import section --------------------------------------------------------------------------------------------



# ──────────────────────────────────────────────────────────────────────────────
# Public types
# ──────────────────────────────────────────────────────────────────────────────
Row = Tuple[List[str], Optional[str], Dict[str, Any]]

# ──────────────────────────────────────────────────────────────────────────────
# CLI blurb + help
# ──────────────────────────────────────────────────────────────────────────────
ARGUMENT_DESCRIPTION = "IVS Sessions TUI Browser"
ARGUMENT_EPILOG = (
    "Filters:\n"
    "  Clauses separated by ';' are AND.\n"
    "  Non-stations fields: tokens split by space/comma/plus/pipe are OR "
    "(e.g. code: r1|r4, case-insensitive)\n"
    "  Stations active: stations: Nn&Ns  or  stations: Nn|Ns (case-sensitive)\n"
    "  Stations removed/any: stations_removed: Ft|Ur   stations_all: Hb|Ht "
    "(case-sensitive)\n\nCLI:\n"
)
ARGUMENT_FORMATTER_CLASS = argparse.RawDescriptionHelpFormatter

HELP_TEXT: List[str] = [
    "IVS Session Browser Help",
    "",
    "Navigation:",
    "  ↑/↓ : Move selection",
    "  PgUp/PgDn : Page up/down",
    "  Home/End : Jump to first/last",
    "  T : Jump to today's session",
    "  Enter : Open session in browser",
    "",
    "Filtering:",
    "  / : Enter filter (field:value, supports AND/OR)",
    "  C : Clear filters",
    "  R : Toggle show/hide removed stations",
    "",
    "Other:",
    "  q or Q : Quit",
    "  ? : Show this help",
    "",
    "Color legend:",
    "  Green    = Released",
    "  Yellow   = Processing / Waiting",
    "  Magenta  = Cancelled",
    "  White    = No status",
    "  Cyan     = Active filters",
    "",
    "",
    "Hit any key to close this help",
    "",
    "Well, maybe not ANY key—Ctrl/Shift/Alt usually won’t register ;-)",
]

HELPBAR_TEXT = (
    "↑↓-PgUp/PgDn-Home/End:Move Enter:Open /:Filter F:Clear filters ?:Help "
    "R:Hide/show removed q/Q:Quit"
)

BASE_URL    = "https://ivscc.gsfc.nasa.gov/sessions"
DATEFORMAT  = "%Y-%m-%d %H:%M"

# ──────────────────────────────────────────────────────────────────────────────
# Columns & headers
# ──────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Column:
    title: str
    min: int

# Base column set (minimum widths). Titles order defines field index mapping.
BASE_COLUMNS: List[Column] = [
    Column("Type", 14),  # allow space for right-justified "[I]" later
    Column("Code", 8),
    Column("Start", 16),
    Column("DOY", 3),
    Column("Dur", 5),
    Column("Stations", 10),
    Column("DB", 4),
    Column("Ops", 10),
    Column("Corr", 6),
    Column("Status", 10),
    Column("Analys", 10),
]

# Field name → index, including a few convenient aliases.
FIELD_INDEX: Dict[str, int] = {
    "type": 0,
    "code": 1,
    "start": 2,
    "doy": 3,
    "dur": 4,
    "stations": 5,
    "db code": 6,
    "db": 6,
    "ops center": 7,
    "ops": 7,
    "corr": 8,
    "status": 9,
    "analysis": 10,
}

# Keys that drive navigation (kept in a tuple to keep it hashable/iterable).
NAVIGATION_KEYS: Tuple[int, ...] = (
    curses.KEY_UP,
    curses.KEY_DOWN,
    curses.KEY_NPAGE,
    curses.KEY_PPAGE,
    curses.KEY_HOME,
    curses.KEY_END,
    curses.KEY_ENTER,
    10,  # LF
    13,  # CR
)

# ──────────────────────────────────────────────────────────────────────────────
# Header computation helpers (no global mutation!)
# ──────────────────────────────────────────────────────────────────────────────

def _observed_content_widths(rows: Iterable[Row], num_cols: int) -> List[int]:
    widths = [0] * num_cols
    for values, _url, _meta in rows:
        for i in range(min(num_cols, len(values))):
            w = len(values[i])
            if w > widths[i]:
                widths[i] = w
    return widths


def compute_widths(
    rows: Iterable[Row],
    base: List[Column] = BASE_COLUMNS,
    *,
    pad_type_for_intensive: bool = True,
) -> List[int]:
    """Return computed widths per column given *rows*.

    Never mutates module globals. Caller decides what to do with the result.
    """
    titles = [c.title for c in base]
    mins = [c.min for c in base]
    name_lens = [len(t) for t in titles]

    obs = _observed_content_widths(rows, len(base))
    widths = [max(mins[i], name_lens[i], obs[i]) for i in range(len(base))]

    if pad_type_for_intensive:
        # If any row is marked intensive in meta, add room for "[I]" at the end.
        any_intensive = any((meta.get("intensive", False)) for _vals, _u, meta in rows)
        if any_intensive:
            t_idx = FIELD_INDEX["type"]
            widths[t_idx] = max(widths[t_idx], mins[t_idx], name_lens[t_idx]) + 2

    return widths


def make_headers(widths: List[int], base: List[Column] = BASE_COLUMNS) -> List[Tuple[str, int]]:
    return [(base[i].title, widths[i]) for i in range(len(base))]


def header_line(headers: List[Tuple[str, int]]) -> str:
    return " | ".join(f"{title:<{w}}" for title, w in headers)


def header_dict(headers: List[Tuple[str, int]]) -> Dict[str, int]:
    return dict(headers)

# Convenience one‑shot: compute everything you need at once from rows.

def compute_headers(rows: Iterable[Row]) -> Tuple[
    List[Tuple[str, int]],  # headers
    Dict[str, int],         # header_dict
    List[int],              # widths
    str,                    # header_line
]:
    widths = compute_widths(rows)
    headers = make_headers(widths)
    hdict = header_dict(headers)
    hline = header_line(headers)
    return headers, hdict, widths, hline

# ──────────────────────────────────────────────────────────────────────────────
# Backwards compatibility shims (optional):
# If you want to keep old names around temporarily, uncomment below.
# ──────────────────────────────────────────────────────────────────────────────
HEADERS      = make_headers([c.min for c in BASE_COLUMNS])
HEADER_DICT  = header_dict(HEADERS)
WIDTHS       = [w for _t, w in HEADERS]
HEADER_LINE  = header_line(HEADERS)

