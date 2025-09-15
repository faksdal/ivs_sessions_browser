"""
Filename:   defs.py
Author:     jole
Created:    15.09.2025

Description:    Hold various constants, or other definitions, for use across the project.

Notes:
"""

# --- Import section ---------------------------------------------------------------------------------------------------
import argparse

from typing import List, Tuple, Optional, Dict, Any
# --- END OF Import section --------------------------------------------------------------------------------------------



ARGUMENT_DESCRIPTION = "IVS Sessions TUI Browser"

ARGUMENT_EPILOG = ("Filters (case-sensitive):\n"
                   "  Clauses separated by ';' are AND.\n"
                   "  Non-stations fields: tokens split by space/comma/plus/pipe are OR (e.g. code: R1|R4)\n"
                   "  Stations active: stations: Nn&Ns  or  stations: Nn|Ns\n"
                   "  Stations removed/any: stations_removed: Ft|Ur   stations_all: Hb|Ht\n"
                   "\nCLI:\n")

ARGUMENT_FORMATTER_CLASS = argparse.RawDescriptionHelpFormatter

Row = Tuple[List[str], Optional[str], Dict[str, Any]]
