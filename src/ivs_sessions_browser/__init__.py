# --- file: __init__.py

# --- Import section ---------------------------------------------------------------------------------------------------

from .defs import ARGUMENT_EPILOG, ARGUMENT_DESCRIPTION, ARGUMENT_FORMATTER_CLASS
import argparse
from datetime           import datetime
from .sessions_browser  import SessionsBrowser
# --- END OF Import section --------------------------------------------------------------------------------------------



# --- Version (managed by setuptools-scm)
try:
    from ._version import version as __version__
except ImportError:
    __version__ = "0.0.0"



# --- Main entry point (used by pyproject.toml [project.scripts])
def main() -> None:
    """
    CLI entry point.

    Possible command line arguments:
        * --year        {the year you want to browse: xxxx}
        * --scope       {master, intensive, both}, defaults to both
        * --stations    {[station code: Xx]}, supports |(OR), &(AND), defaults to all stations
    """

    # ARGUMENT_DESCRIPTION = "IVS Sessions TUI Browser"
    #
    # ARGUMENT_EPILOG = ("Filters (case-sensitive):\n"
    #                    "  Clauses separated by ';' are AND.\n"
    #                    "  Non-stations fields: tokens split by space/comma/plus/pipe are OR (e.g. code: R1|R4)\n"
    #                    "  Stations active: stations: Nn&Ns  or  stations: Nn|Ns\n"
    #                    "  Stations removed/any: stations_removed: Ft|Ur   stations_all: Hb|Ht\n"
    #                    "\nCLI:\n")
    #
    # ARGUMENT_FORMATTER_CLASS = argparse.RawDescriptionHelpFormatter

    # --- Define an argument parser for the user's command line args
    arg_parser = argparse.ArgumentParser(description=ARGUMENT_DESCRIPTION,
                                         epilog=ARGUMENT_EPILOG,
                                         formatter_class=ARGUMENT_FORMATTER_CLASS)

    arg_parser.add_argument("--year",
                            type=int,
                            default=datetime.now().year,
                            help="Year (default: current year)")

    arg_parser.add_argument("--scope",
                            choices=("master", "intensive", "both"),
                            default="both",
                            help="Which schedules to include (default: both)")
    arg_parser.add_argument("--stations",
                            type=str,
                            help="Initial stations filter (optional)")

    args = arg_parser.parse_args()

    sb: SessionsBrowser = SessionsBrowser(_year             = args.year,
                                          _scope            = args.scope,
                                          _stations_filter  = args.stations)
    sb.run()

    exit(0)

__all__ = [
    "__version__",
    "main",
    "SessionsBrowser",
    "ReadData"
]
