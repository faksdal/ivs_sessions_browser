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

# from dataclasses import dataclass

# import curses
# from dataclasses import dataclass
# from typing import Any, Dict, Iterable, List, Optional, Tuple
# ─── END OF Import section ────────────────────────────────────────────────────



# ──────────────────────────────────────────────────────────────────────────────
# Public types
# ──────────────────────────────────────────────────────────────────────────────
Row = Tuple[List[str], Optional[str], Dict[str, Any]]
# ─── END OF Public type ───────────────────────────────────────────────────────



# ──────────────────────────────────────────────────────────────────────────────
# CLI blurb + help
# ──────────────────────────────────────────────────────────────────────────────
ARGUMENT_DESCRIPTION        = "IVS Sessions TUI Browser"
ARGUMENT_EPILOG             = ("Filters:\n"
                               "  Clauses separated by ';' are AND.\n"
                               "  Non-stations fields: tokens split by space/comma/plus/pipe are OR "
                               "(e.g. code: r1|r4, case-insensitive)\n"
                               "  Stations active: stations: Nn&Ns  or  stations: Nn|Ns (case-sensitive)\n")
ARGUMENT_FORMATTER_CLASS    = argparse.RawDescriptionHelpFormatter
# ─── END OF CLI blurb + help ──────────────────────────────────────────────────