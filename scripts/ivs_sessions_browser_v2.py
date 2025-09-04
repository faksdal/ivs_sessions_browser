#! ../.venv/bin/python3
# --- This is a re-write of the ivs_sessions_browser.py script
#
# --- jole 2025



## Import section ######################################################################################################
from bs4    import BeautifulSoup
from typing import Optional, List, Tuple, Dict, Any
import re
import requests

from log_helper     import setup_logger
from url_helper     import URLHelper
from session_parser import SessionParser

## END OF Import section ###############################################################################################



Row = Tuple[List[str], Optional[str], Dict[str, Any]]

# --- class definition -------------------------------------------------------------------------------------------------
class SessionBrowser(SessionParser):

    # --- CLASS ATTRIBUTES ---------------------------------------------------------------------------------------------

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

    # --- END OF CLASS ATTRIBUTES --------------------------------------------------------------------------------------

    # --- __init__ function, or constructor if you like since I come from c/c++ ----------------------------------------
    def __init__(self,
                 _year: int,
                 _scope: str = "both",
                 _session_filter: Optional[str] = None,
                 _antenna_filter: Optional[str] = None,
                 _url : str = ""
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
        # define url helper attribute, defined in url_helper.py
        self.urlhelper = URLHelper(_url)
        ################################################################################################################
    # this is the end of __init__() ------------------------------------------------------------------------------------



    # --- highlight helper, to be called from within class, not from an instance outside
    # --- Pull station codes from any station-related clause in the current filter
    # --- Called from the 'while True:' in curses main loop when the user type '/' to apply filtering
    # --- Whatever the user types, is passed as '_query', for instance '/ stations: "Ns|Nn"'
    def _extract_station_tokens(self, _query: str) -> List[str]:
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
            if fld in ("stations", "stations_active", "stations-active",
                       "stations_removed", "stations-removed",
                       "stations_all", "stations-all"):
                parts = re.split(r"[ ,+|&]+", value)
                tokens.extend([p for p in parts if p])

        # Deduplicate; longer-first to avoid partial-overwrite visuals (e.g., 'Ny' vs 'Nya')
        return sorted(set(tokens), key=lambda s: (-len(s), s))
    # this is the end of _extract_station_tokens() #####################################################################



    # --- computes the x offset where column _col_idx starts in the printed line
    # --- each column is printed left-padded to WIDTHS[c], joined by " | " (3 chars)
    def _col_start_x(self, _col_idx: int) -> int:
        sep = 3
        x   = 0
        for i in range(_col_idx):
            x += self.WIDTHS[i] + sep
        return x
    # this is the end of _col_start_x() ################################################################################



    # --- fetch and parse ONE IVS sessions table URL into rows (case-sensitive CLI filters)
    # --- data fetched from https://ivscc.gsfc.nasa.gov/
    def _fetch_one(self, _url: str, _session_filter: Optional[str], _antenna_filter: Optional[str]) -> List[Row]:

        # --- reading data from web ####################################################################################
        print(f"Reading data from {_url}...")
        try:
            # --- this function is defined in subclass URLHelper. It fetches the content from the _url, giving feedback
            # --- to the user along the way through self._status_inline, which is also defined in URLHelper
            html = self.urlhelper.get_text_with_progress_retry(_url, _status_cb = self.urlhelper.status_inline)
            # newline after it finishes
            print()
        except requests.RequestException as exc:
            print(f"Error fetching {_url}: {exc}")
            return []
        # this is the end of reading data from web #####################################################################

        # --- read the content into a soup object
        soup = BeautifulSoup(html, "html.parser")

        # and extract table tags into session_rows
        session_rows = soup.select("table tr")

        parsed: List[Row] = []

        # attribute to mark if intensives
        is_intensive = "/intensive" in _url

        for r in session_rows:
            tds = r.find_all("td")

            if len(tds) < len(SessionBrowser.HEADERS):
                continue
            #print(tds[5])

            # --- regarding stations: split active vs. removed, render them as "Active [Removed]"
            # assign the stations_cell to the cells containing stations names, using the correct index from
            # FIELD_INDEX
            idx = SessionBrowser.FIELD_INDEX.get("stations")
            if idx is None or idx >= len(tds):
                continue
            stations_cell = tds[idx]
            #stations_cell = tds[SessionBrowser.FIELD_INDEX["stations"]]

            # create a couple of local string list attributes to hold the active, and removed stations
            active_ids: List[str] = []
            removed_ids: List[str] = []
        return parsed

        # this is the end of 'for r in session_rows:' ------------------------------------------------------------------
    # this is the end of _fetch_one() ----------------------------------------------------------------------------------



# --- END OF class definition ------------------------------------------------------------------------------------------



def main():
    # create and set up the logger object. Disable printing to stdout
    logger = setup_logger(filename='../log/ivs_browser.log', to_stdout=False)
    logger.info("Script started")

    sb = SessionBrowser(2025, _url = "https://ivscc.gsfc.nasa.gov/sessions/2025/")
    #sb._fetch_one("https://ivscc.gsfc.nasa.gov/sessions/2025/", "", "")



if __name__ == "__main__":
    main()
