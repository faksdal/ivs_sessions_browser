#! ../.venv/bin/python3

# --- This is a re-write of the ivs_sessions_browser.py script
#
# --- jole 2025



## Import section ######################################################################################################
""" import setup function for the logger """
from fileinput import filename

from bs4 import BeautifulSoup

# --- a little helper to setup the logger
from log_helper import setup_logger

# --- Optional for, well, obvious reasons
# --- I'm using Lists
from typing import Optional, List, Tuple, Dict, Any, Callable

# --- for regex
import re

# --- for requests
import requests

import time
## END OF Import section ###############################################################################################


Row = Tuple[List[str], Optional[str], Dict[str, Any]]

# --- class definition -------------------------------------------------------------------------------------------------
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

    # this is the end of __init__() ####################################################################################



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



    # --- downloads from web giving feedback to the user of the progress ###############################################
    def _get_text_with_progress(self,
                                _url: str,
                                *,_timeout = (5, 20),
                                _status_cb: Optional[Callable[[str], None]] = None,
                                _chunk_size: int = 65536,
                                _min_update_interval: float = 0.10
                           ) -> str:
        UA = "Mozilla/5.0 (compatible; IVSBrowser/1.0)"
        cb = _status_cb or (lambda _msg: None)

        with requests.get(_url, stream = True, timeout = _timeout, headers = {"User-Agent": UA}) as r:
            try:
                # raise for 4xx/5xx errors
                r.raise_for_status()
            except requests.HTTPError as e:
                # give useful context
                raise RuntimeError(f"HTTP {r.status_code} {r.reason} for {r.url}") from e
            # content length, may be missing or non-numeric
            try:
                total = int(r.headers.get("Content-Length", ""))
            except ValueError:
                total = None

            got         = 0
            chunks      = []
            last_emit   = 0.0

            for chunk in r.iter_content(chunk_size = _chunk_size):
                if not chunk:
                    continue
                chunks.append(chunk)
                got += len(chunk)

                now = time.monotonic()
                if now - last_emit >= _min_update_interval:
                    if total:
                        cb(f"Downloading… {got}/{total} bytes ({got / total * 100:.1f}%)")
                    else:
                        cb(f"Downloading… {got} bytes")
                    last_emit = now

            # final progress line
            if total:
                cb(f"Download complete: {got}/{total} bytes.")
            else:
                cb(f"Download complete: {got} bytes.")

            # Pick a sensible encoding
            enc = r.encoding or r.apparent_encoding or "utf-8"
            try:
                return b"".join(chunks).decode(enc, errors="replace")
            except LookupError:
                # Unknown codec name – fall back to utf-8
                return b"".join(chunks).decode("utf-8", errors="replace")



    def _set_status_line(self, msg: str) -> None:
        print(msg)



    # def _get_with_progress(_url, *, _timeout=(5, 20), _status_cb = print):
    #     with requests.get(_url, stream = True, timeout = _timeout, headers = {"User-Agent": "Mozilla/5.0"}) as r:
    #         r.raise_for_status()
    #         total = int(r.headers.get("Content-Length", 0))
    #         got = 0
    #         chunks = []
    #         for chunk in r.iter_content(chunk_size=8192):
    #             if not chunk:
    #                 continue
    #             chunks.append(chunk)
    #             got += len(chunk)
    #             if total:
    #                 _status_cb(f"Downloading… {got}/{total} bytes ({got / total * 100:.1f}%)")
    #             else:
    #                 _status_cb(f"Downloading… {got} bytes")
    #
    #         # Decode safely
    #         enc = r.encoding or r.apparent_encoding or "utf-8"
    #         text = b"".join(chunks).decode(enc, errors="replace")
    #         _status_cb("Download complete.")
    #         return text
    # this is the end of _get_with_progress()###########################################################################

    #############################################################################################
    def _get_text_with_progress_retry(self,
            _url: str,
            *,
            _retries: int = 2,
            _backoff: float = 0.5,
            _status_cb: Optional[Callable[[str], None]] = None,
            **_kwargs,
    ) -> str:
        cb = _status_cb or (lambda _msg: None)
        for attempt in range(_retries + 1):
            try:
                return self._get_text_with_progress(_url, _status_cb = cb, **_kwargs)
            except (requests.Timeout, requests.ConnectionError) as e:
                if attempt < _retries:
                    cb(f"{e.__class__.__name__}: {e}. Retrying in {_backoff:.1f}s…")
                    time.sleep(_backoff)
                    _backoff *= 2
                else:
                    raise
    #######################################



    # --- fetch and parse ONE IVS sessions table URL into rows (case-sensitive CLI filters)
    # --- data fetched from https://ivscc.gsfc.nasa.gov/
    #@staticmethod
    def _fetch_one(self, _url: str, _session_filter: Optional[str], _antenna_filter: Optional[str]) -> List[Row]:

        # --- reading data from web ####################################################################################
        print(f"Reading data from {_url}...")
        try:
            #response = requests.get(_url, timeout=20)
            html = self._get_text_with_progress_retry(_url, _status_cb = self._set_status_line)
            # response = SessionBrowser._get_with_progress(_url)
            #response = SessionBrowser._get_with_progress(_url, status_cb = self._set_status_line)
            #print(html)
            #response.raise_for_status()
        except requests.RequestException as exc:
            print(f"Error fetching {_url}: {exc}")
            return []
        # this is the end of reading data from web #####################################################################

        soup = BeautifulSoup(html, "html.parser")

        session_rows = soup.select("table tr")

        parsed: List[Row] = []

        # mark if intensives
        is_intensive = "/intensive" in _url

        for r in session_rows:
            tds = r.find_all("td")

            if len(tds) < len(SessionBrowser.HEADERS):
                continue
            #print(tds[5])
            #print("Jon")

            # --- regarding stations: split active vs. removed, render them as "Active [Removed]"
            # assign the stations_cell to the cells containing stations names, using the correct index from
            # FIELD_INDEX
            idx = SessionBrowser.FIELD_INDEX.get("stations")
            if idx is None or idx >= len(tds):
                continue  # or handle error/warn
            stations_cell = tds[idx]
            #stations_cell = tds[SessionBrowser.FIELD_INDEX["stations"]]

            # create a couple of local string list attributes to hold the active, and removed stations
            active_ids: List[str] = []
            removed_ids: List[str] = []






        # this is the end of 'for r in session_rows:' ##################################################################

    # this is the end of _fetch_one() ##################################################################################



# --- END OF class definition ------------------------------------------------------------------------------------------



def main():
    # create and setup the logger object. Disable printing to stdout
    logger = setup_logger(filename='../log/ivs_browser.log', to_stdout=False)
    logger.info("Script started")

    sb = SessionBrowser(2025)

    sb._fetch_one("https://ivscc.gsfc.nasa.gov/sessions/2025/", "", "")



if __name__ == "__main__":
    main()
