"""
Filename:   defs.py
Author:     jole
Created:    2026-01-23

Purpose:
  Centralize shared types and small, stable constants while avoiding mutable
  module‑level state. Header widths are computed on demand from data instead of
  mutating globals.
"""



# ──────────────────────────────────────────────────────────────────────────────
# Import section
# ──────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import argparse
from typing import Any, Protocol

# from dataclasses import dataclass

# import curses
# from dataclasses import dataclass
# from typing import Any, Dict, Iterable, List, Optional, Tuple
# ─── END OF Import section ────────────────────────────────────────────────────



# ──────────────────────────────────────────────────────────────────────────────
# CLI blurb + help
# ──────────────────────────────────────────────────────────────────────────────
ARGUMENT_DESCRIPTION        = "IVS Sessions TUI Browser"
ARGUMENT_EPILOG             = ("Filters:\n"
                               "  Clauses separated by ';' are AND.\n"
                               "  Non-stations fields: tokens split by space/comma/plus/pipe are OR "
                               "(e.g. code: r1|r4, case-insensitive)\n"
                               "  Stations active: stations: Nn&Ns  or  stations: Nn|Ns (case-sensitive)\n")  # noqa: E501
ARGUMENT_FORMATTER_CLASS    = argparse.RawDescriptionHelpFormatter
# ─── END OF CLI blurb + help ──────────────────────────────────────────────────



# Protocol describing the minimal attributes used by render mixins and other
# components that operate on a SessionsBrowser-like object. Place here so mixins
# can import a single shared Protocol and avoid repeating definitions.
class SessionsBrowserLike(Protocol):
    year:       int
    scope:      str
    filters:    str | None
# ─── END OF class SessionsBrowserLike() ───────────────────────────────────────


# Re-export commonly used typing aliases and placeholders so other modules can
# `from . import defs as D` and reference `D.List`, `D.Row`, etc. These are
# lightweight runtime aliases and placeholders; replace with concrete values
# as the codebase grows.
List = list
Dict = dict

# Row: (columns, optional stations string, metadata dict)
Row = tuple[list[str], str | None, dict[str, Any]]

# UI/layout placeholders
HELP_TEXT: list[str] = []
HEADERS: list[str] = []
HEADER_LINE: str = ""
HEADER_DICT: dict[str, int] = {}
WIDTHS: list[int] = []
FIELD_INDEX: dict[str, int] = {}

DATEFORMAT = "%Y-%m-%d"
BASE_URL = ""
NAVIGATION_KEYS: dict[str, str] = {}


def recompute_header_widths(rows: list[Row], headers: list[str]) -> None:
  """Placeholder recompute function; real implementation lives elsewhere."""
  return None
