"""
    types.py

    Contains user defined types for use around the different project classes

    2025 jole
"""
import argparse
import curses

from typing import List, Tuple, Optional, Dict, Any



Row = Tuple[List[str], Optional[str], Dict[str, Any]]

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
                               "correlator": 8,
                               "status": 9,
                               "analysis": 10
                               }

HEADERS                     = [("Type", 14),
                               ("Code", 8),
                               ("Start", 18),
                               ("DOY", 3),
                               ("Dur", 5),
                               ("Stations", 44),
                               ("DB Code", 14),
                               ("Ops Center", 10),
                               ("Correlator", 10),
                               ("Status", 20),
                               ("Analysis", 10)
                              ]

HEADER_LINE                 = " | ".join([f"{title:<{w}}" for title, w in HEADERS])

WIDTHS                      = [w for _, w in HEADERS]

ARGUMENT_DESCRIPTION        = "IVS Sessions TUI Browser"

ARGUMENT_EPILOG             = ("Filters (case-sensitive):\n"
                               "  Clauses separated by ';' are AND.\n"
                               "  Non-stations fields: tokens split by space/comma/plus/pipe are OR (e.g. code: R1|R4)\n"
                               "  Stations active: stations: Nn&Ns  or  stations: Nn|Ns\n"
                               "  Stations removed/any: stations_removed: Ft|Ur   stations_all: Hb|Ht\n"
                               "\nCLI:\n"
                               "  --stations uses the same grammar as 'stations:' and applies to ACTIVE stations.\n")

ARGUMENT_FORMATTER_CLASS    = argparse.RawDescriptionHelpFormatter
NAVIGATION_KEYS = {curses.KEY_UP, curses.KEY_DOWN, curses.KEY_NPAGE, curses.KEY_PPAGE, curses.KEY_HOME,
                           curses.KEY_END, curses.KEY_ENTER, 10, 13}