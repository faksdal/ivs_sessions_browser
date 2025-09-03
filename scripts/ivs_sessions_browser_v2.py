#! ../.venv/bin/python3

# --- This is a re-write of the ivs_sessions_browser.py script
#
# --- jole 2025



## Import section ######################################################################################################
""" import setup function for the logger """
from fileinput import filename

# --- a little helper to setup the logger
from log_helper import setup_logger

# --- Optional for, well, obvious reasons
# --- I'm using Lists
from typing import Optional, List


""" for data handling """
#import numpy as np

""" for sys.exit(n) """
#import sys

""" for differences in timestamps """
#from datetime import datetime, timezone
## END OF Import section ###############################################################################################



class SessionBrowser:

    # --- class attributes
    # Column layout, taking care to preserve the width
    HEADERS =   [
                ("Type", 14),
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
    HEADER_LINE = " | ".join([f"{title:<{w}}" for title, w in HEADERS])

    # By convention in Python, _ means “I don’t care about this value.”
    # You’re telling the reader: I know this variable exists, but I won’t use it.
    # So here, we’re ignoring the column names ("Type", "Code", …) and keeping only the widths.
    WIDTHS = [w for _, w in HEADERS]
    FIELD_INDEX = {"type": 0,
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
                   "analysis": 10}

    def __init__(self,
                 _year: int,
                 _scope: str = "both",
                 _session_filter: Optional[str] = None,
                 _antenna_filter: Optional[str] = None
                 ) -> None:
        self.year   = _year
        self.scope  = _scope
        self.session_filter = _session_filter
        self.antenna_filter = _antenna_filter

        # define and initialize some instance attributes ###############################################################
        self.rows: List[Row]                = []
        self.view_rows: List[Row]           = []
        self.current_filter: str            = ""
        self.selected: int                  = 0
        self.offset: int                    = 0
        self.has_colors: bool               = False
        self.show_removed: bool             = False # --- flag for showing/hiding removed sessions in the list
        self.highlight_tokens: List[str]    = []    # --- tokens to highlight in the stations column when filtering
        ################################################################################################################

    # this is the end of __init__ ######################################################################################



    # --- highlight helper, to be called from within class, not from an instance outside
    # --- Pull station codes from any station-related clause in the current filter
    # --- Called from the 'while True:' in curses main loop when the user type '/' to apply filtering
    # --- Whatever the user types, is passed as '_query', for instance '/ stations: "Ns|Nn"'
    def _extract_station_tokens(selfself, _query: str) -> List[str]:

        # if we're passed an empty query, return with nothing
        if not _query:
            return []

        # define and initialize some local instance attributes #########################################################
        tokens: List[str]   = []                                                    # empty list of strings
        clauses             = [c.strip() for c in _query.split(';') if c.strip()]   # splits _query by the ';', and
                                                                                    # strips away any whitespace, storing
                                                                                    # what's left in 'clauses'
        ################################################################################################################

        for clause in clauses:
            if ':' not in clause:
                continue
            field, value = [p.strip() for p in clause.split(':', 1)]
            fld = field.lower()

    # this is the end of _extract_station_tokens #######################################################################





def main():
    # create and setup the logger object. Disable printing to stdout
    logger = setup_logger(filename='../log/ivs_browser.log', to_stdout=False)
    logger.info("Script started")

    sb = SessionBrowser(2025)





if __name__ == "__main__":
    main()
