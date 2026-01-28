# flake8: noqa
# isort: skip_file

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
from typing     import Any

import argparse
from pathlib import Path

# from dataclasses import dataclass

# import curses
# from dataclasses import dataclass
# from typing import Any, Dict, Iterable, List, Optional, Tuple
# ─── END OF Import section ────────────────────────────────────────────────────



# ──────────────────────────────────────────────────────────────────────────────
# CLI blurb + help
# ──────────────────────────────────────────────────────────────────────────────
ARGUMENT_DESCRIPTION        = "IVS Sessions TUI Browser; browse IVS session data in a terminal interface."
ARGUMENT_EPILOG             = ("Filters:\n"
                               "   ─ Added as key:value pair, several key:value pair are separated by ';'\n"
                               "   ─ Valid keys equals to the column headers (case-sensitive only for stations).\n"
                               "   ─ Non-stations fields: tokens split by space/comma/plus/pipe are OR (e.g. code: r1|r4)\n"
                               "   ─ Stations active: stations: Nn&Ns  or  stations: Nn|Ns\n"
                               "   ─ Filters must be escaped with \" or \'\n"
                               "   ─ | (pipe) means OR, & (ampersand) means AND\n"
                               "   Example: --filters \'code: r1|r4; stations: Nn&Ns\'\n\nCLI:\n"
                               )

ARGUMENT_FORMATTER_CLASS    = argparse.RawDescriptionHelpFormatter
# ─── END OF CLI blurb + help ──────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────────────
# IVSCC related constants
# ──────────────────────────────────────────────────────────────────────────────
IVSCC_BASE_URLS = [
  "https://ivscc.gsfc.nasa.gov/sessions",   # Primary site
  "https://ivscc.oan.es/sessions",
  "https://ivscc-vcc.org/sessions",
]
# ─── END OF IVSCC related constants and Protocol ──────────────────────────────



# Protocol describing the minimal attributes used by render mixins and other
# components that operate on a SessionsBrowser-like object. Place here so mixins
# can import a single shared Protocol and avoid repeating definitions.
#class SessionsBrowserLike(Protocol):
#    year:       int
#    scope:      str
#    filters:    str | None
#    url_list:   list[str]
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
# HEADERS: list[str] = []
HEADERS                     = [("Op", 5),
                               ("Type", 14),    # 16 in 2022
                               ("Code", 8),
                               ("Start", 16),
                               ("DOY", 3),
                               ("Dur", 5),
                               ("Stations", 10), # 56 in 2022
                               ("DB", 4),
                               ("Ops", 10),
                               ("Corr", 6),
                               ("Status", 10),
                               ("Analys", 10)
                              ]
# HEADER_LINE: str = ""
HEADER_LINE = " | ".join([f"{title:<{w}}" for title, w in HEADERS])

HEADER_DICT: dict[str, int] = dict(HEADERS)
WIDTHS: list[int] = [w for _, w in HEADERS]
FIELD_INDEX: dict[str, int] = {"op": 0,
                                "type": 1,
                                "code": 2,
                                "start": 3,
                                "doy": 4,
                                "dur": 5,
                                "stations": 6,
                                "db": 7,
                                "ops": 8,
                                "corr": 9,
                                "status": 10,
                                "analysis": 11
                                }

DATEFORMAT = "%Y-%m-%d"
BASE_URL = ""
NAVIGATION_KEYS: dict[str, str] = {}


# Configuration filenames and directory (shared constants)
# Use the user's config directory by default; tests or dev can override.
# Default config directory: current directory for development. Tests/dev can
# override by assigning a different value to `defs.CONFIG_DIR` at runtime.
CONFIG_DIR              = Path(".")
OPERATORS_FILENAME      = "operators.json"
ASSIGNMENTS_FILENAME    = "operator_assignments.json"
