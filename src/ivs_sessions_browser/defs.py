"""
Filename:   defs.py
Author:     jole
Created:    15.09.2025

Description:    Hold various constants, or other definitions, for use across the project.

Notes:
"""

# --- Import section ---------------------------------------------------------------------------------------------------
import curses
import argparse

from typing import List, Tuple, Optional, Dict, Any
# --- END OF Import section --------------------------------------------------------------------------------------------



ARGUMENT_DESCRIPTION = "IVS Sessions TUI Browser"

ARGUMENT_EPILOG =   ("Filters:\n"
                     "  Clauses separated by ';' are AND.\n"
                     "  Non-stations fields: tokens split by space/comma/plus/pipe are OR "
                     "(e.g. code: r1|r4, case-insensitive)\n"
                     "  Stations active: stations: Nn&Ns  or  stations: Nn|Ns (case-sensitive)\n"
                     "  Stations removed/any: stations_removed: Ft|Ur   stations_all: Hb|Ht "
                     "(case-sensitive)\n"
                     "\nCLI:\n"
                    )

HELP_TEXT = [
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
            "Well, maybe not ANY key—Ctrl/Shift/Alt usually won’t register ;-)"
        ]

ARGUMENT_FORMATTER_CLASS = argparse.RawDescriptionHelpFormatter

Row         = Tuple[List[str], Optional[str], Dict[str, Any]]

BASE_URL    = "https://ivscc.gsfc.nasa.gov/sessions"

FIELD_INDEX                 = {"type": 0,
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
                               "analysis": 10
                               }

HEADERS                     = [("Type", 14),    # 16 in 2022
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
HEADER_DICT = dict(HEADERS)

HELPBAR_TEXT = "↑↓-PgUp/PgDn-Home/End:Move Enter:Open /:Filter F:Clear filters ?:Help R:Hide/show removed q/Q:Quit"

HEADER_LINE = " | ".join([f"{title:<{w}}" for title, w in HEADERS])

WIDTHS = [w for _, w in HEADERS]

NAVIGATION_KEYS = {curses.KEY_UP,
                   curses.KEY_DOWN,
                   curses.KEY_NPAGE,
                   curses.KEY_PPAGE,
                   curses.KEY_HOME,
                   curses.KEY_END,
                   curses.KEY_ENTER,
                   10, 13}

DATEFORMAT = "%Y-%m-%d %H:%M"



# --- Dynamic width recompute ---------------------------------------------------
def recompute_header_widths(rows: List[Row]) -> None:
    """
    Recompute HEADERS/HEADER_DICT/WIDTHS/HEADER_LINE from data.
    Ensures 'Type' has room for a right-justified '[I]' if any intensive exists.
    """
    global HEADERS, HEADER_DICT, WIDTHS, HEADER_LINE

    titles = [t for t, _ in HEADERS]
    mins   = [w for _, w in HEADERS]
    num    = len(titles)

    # --- Observed content lengths per column
    obs = [0]*num
    any_intensive = False
    for values, _url, meta in rows:
        any_intensive = any_intensive or bool(meta.get("intensive"))
        for i in range(min(num, len(values))):
            obs[i] = max(obs[i], len(values[i]))

    name_lens = [len(t) for t in titles]
    widths = [max(mins[i], name_lens[i], obs[i]) for i in range(num)]

    # --- Add some chars for "[I]" if any intensive is present
    type_idx = FIELD_INDEX.get("type", 0)
    if any_intensive:
        widths[type_idx] = max(widths[type_idx], name_lens[type_idx], mins[type_idx]) + 2

    HEADERS = list(zip(titles, widths))
    HEADER_DICT = dict(HEADERS)
    WIDTHS = widths
    HEADER_LINE = " | ".join([f"{title:<{w}}" for title, w in HEADERS])
# --- END OF recompute_header_widths() ---------------------------------------------------------------------------------