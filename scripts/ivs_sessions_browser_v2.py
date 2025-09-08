#! ../.venv/bin/python3
# --- This is a re-write of the ivs_sessions_browser.py script
#
# --- jole 2025
import logging

## Import section ######################################################################################################
from bs4    import BeautifulSoup
from typing import Optional, List, Tuple, Dict, Any
import re
import requests

from log_helper     import setup_logger
from url_helper     import URLHelper
from session_parser import SessionParser

## END OF Import section ###############################################################################################



# --- class definition -------------------------------------------------------------------------------------------------
#class SessionBrowser(SessionParser):
class SessionBrowser:

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

    Row = Tuple[List[str], Optional[str], Dict[str, Any]]
    # --- END OF CLASS ATTRIBUTES --------------------------------------------------------------------------------------

    # --- __init__() function, or constructor if you like since I come from c/c++ ----------------------------------------
    def __init__(self,
                 _year: int,
                 _logger: logging.Logger,
                 _scope: str = "both",
                 _session_filter: Optional[str] = None,
                 _antenna_filter: Optional[str] = None,
                 _url: str = ""
                 ) -> None:
        # assigning all parameters to local instance vars
        self.year           = _year
        self.logger         = _logger
        self.scope          = _scope
        self.session_filter = _session_filter
        self.antenna_filter = _antenna_filter
        self.url            = _url

        # define and initialize some instance attributes ###############################################################
        self.rows: List[SessionBrowser.Row]         = []
        self.view_rows: List[SessionBrowser.Row]    = []
        self.current_filter: str                    = ""
        self.selected: int                          = 0
        self.offset: int                            = 0
        self.has_colors: bool                       = False
        self.show_removed: bool                     = False # --- flag for showing/hiding removed sessions in the list
        self.highlight_tokens: List[str]            = []    # --- tokens to highlight in the stations column when filtering
        ################################################################################################################
    # this is the end of __init__() ------------------------------------------------------------------------------------



    # todo: Decide where to put this. I'm not yet quite sure what is does.
    # --- computes the x offset where column _col_idx starts in the printed line
    # --- each column is printed left-padded to WIDTHS[c], joined by " | " (3 chars)
    def _col_start_x(self, _col_idx: int) -> int:
        sep = 3
        x   = 0
        for i in range(_col_idx):
            x += self.WIDTHS[i] + sep
        return x
    # this is the end of _col_start_x() ################################################################################



    # ---
    #def _fetch_one(self, _url: str, _session_filter: Optional[str], _antenna_filter: Optional[str]) -> List[Row]:
    def fetch_data_from_web(self) -> str:
        """
        Fetch and parse the IVS sessions table URL into rows (case-sensitive CLI filters)
        Data fetched from https://ivscc.gsfc.nasa.gov/
        :param:     self
        :return:    html (str)
        """
        # --- reading data from web ####################################################################################
        print(f"Reading data from {self.url}...")
        self.logger.info(f"Reading data from {self.url}...")
        try:
            # --- this function is defined in subclass URLHelper. It fetches the content from the _url, giving feedback
            # --- to the user along the way through self._status_inline, which is also defined in URLHelper
            urlhelper = URLHelper(self.url, self.logger)
            html = urlhelper.get_text_with_progress_retry(self.url, _status_cb = urlhelper.status_inline)
            return html

        except requests.RequestException as exc:
            print(f"Error fetching {self.url}: {exc}")
            self.logger.warning(f"Error fetching {self.url}: {exc}")
            return []
        # this is the end of reading data from web #####################################################################

        # start of parser ##############################################################################################
        # --- read the content into a soup object
        #soup = BeautifulSoup(html, "html.parser")
        #print(type(soup))

        # and extract table tags into session_rows
        #session_rows = soup.select("table tr")

        #parsed: List[Row] = []

        # attribute to mark if intensives
        # is_intensive = "/intensive" in self.url

        # for r in session_rows:
        #     tds = r.find_all("td")
        #
        #     if len(tds) < len(SessionBrowser.HEADERS):
        #         continue
        #     #print(tds[5])
        #
        #     # --- regarding stations: split active vs. removed, render them as "Active [Removed]"
        #     # assign the stations_cell to the cells containing stations names, using the correct index from
        #     # FIELD_INDEX
        #     idx = SessionBrowser.FIELD_INDEX.get("stations")
        #     if idx is None or idx >= len(tds):
        #         continue
        #     stations_cell = tds[idx]
        #     #stations_cell = tds[SessionBrowser.FIELD_INDEX["stations"]]
        #
        #     # create a couple of local string list attributes to hold the active, and removed stations
        #     active_ids: List[str] = []
        #     removed_ids: List[str] = []
        # return parsed
        # end of parser ##############################################################################################

        # this is the end of 'for r in session_rows:' ------------------------------------------------------------------
    # this is the end of _fetch_one() ----------------------------------------------------------------------------------

    def run(self) -> None:
        """
        This is what the user calls to run the loop.

        :return: None
        """
        # Get data from web, and store in 'html'
        html = self.fetch_data_from_web()

        # Instantiate a SessionParser object, passing a soup object of the 'html', and the logger object
        # Store the return value in 'parsed'
        # We should be given a list of extracted columns from SessionParser,w hich in turn will be used to display
        # in the TUI.
        parsed = SessionParser(BeautifulSoup(html, "html.parser"), self.logger)
        # print(parsed)
# --- END OF class SessionBrowser definition ------------------------------------------------------------------------------------------



def main() -> None:
    """
    Create and set up the logger object.

    :return:    None
    """

    # todo: May rename log_setup to general_setup(or something similar). Maybe there are other constants that can be
    # todo: set there as well!
    from log_setup import log_filename
    logger = setup_logger(filename = log_filename, to_stdout = False)
    logger.info("Script started")

    sb = SessionBrowser(2025, logger, _url = "https://ivscc.gsfc.nasa.gov/sessions/2025/").run()
    # sb.fetch_data_from_web()



if __name__ == "__main__":
    main()
