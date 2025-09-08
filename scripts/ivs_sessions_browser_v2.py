#! ../.venv/bin/python3
# --- This is a re-write of the ivs_sessions_browser.py script
#
# --- jole 2025

## Import section ######################################################################################################
import argparse
import re
import requests
import logging
from bs4            import BeautifulSoup
from typing         import Optional, List, Tuple, Dict, Any
from datetime       import datetime, date
from log_helper     import setup_logger
from url_helper     import URLHelper
from session_parser import SessionParser
from type_defs      import (Row,
                            # FIELD_INDEX,
                            HEADERS,
                            # HEADER_LINE,
                            # WIDTHS,
                            ARGUMENT_DESCRIPTION,
                            ARGUMENT_EPILOG,
                            ARGUMENT_FORMATTER_CLASS
                            )
## END OF Import section ###############################################################################################



# --- class definition -------------------------------------------------------------------------------------------------
#class SessionBrowser(SessionParser):
class SessionBrowser:
    """
    Class SessionBrowser
    """

    # --- __init__() function, or constructor if you like since I come from c/c++ ----------------------------------------
    def __init__(self,
                 _year: int,
                 _logger: logging.Logger,
                 _scope: str = "both",
                 _session_filter: Optional[str] = None,
                 _antenna_filter: Optional[str] = None,
                 ) -> None:
        # assigning all parameters to local instance vars
        self.year           = _year
        self.logger         = _logger
        self.scope          = _scope
        self.session_filter = _session_filter
        self.antenna_filter = _antenna_filter

        # define and initialize some instance attributes ###############################################################
        self.rows:              List[Row]   = []
        self.view_rows:         List[Row]   = []
        self.current_filter:    str         = ""
        self.selected:          int         = 0
        self.offset:            int         = 0
        self.has_colors:        bool        = False
        self.show_removed:      bool        = False # --- flag for showing/hiding removed sessions in the list
        self.highlight_tokens:  List[str]   = []    # --- tokens to highlight in the stations column when filtering
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



    #def _fetch_one(self, _url: str, _session_filter: Optional[str], _antenna_filter: Optional[str]) -> List[Row]:
    def _fetch_one_url(self,
                       _url: str
                       ) -> List[Row]:
        """
        Fetch and parse the IVS sessions table URL into rows (case-sensitive CLI filters)
        Data fetched from https://ivscc.gsfc.nasa.gov/

        :return:    html (List[Row])
        """
        # --- reading data from web ####################################################################################
        print(f"Reading data from {_url}...")
        self.logger.info(f"Reading data from {_url}...")
        try:
            # --- this function is defined in subclass URLHelper. It fetches the content from the _url, giving feedback
            # --- to the user along the way through self._status_inline, which is also defined in URLHelper
            urlhelper = URLHelper(_url, self.logger)
            html = urlhelper.get_text_with_progress_retry(_url, _status_cb = urlhelper.status_inline)
            return html

        except requests.RequestException as exc:
            print(f"Error fetching {_url}: {exc}")
            self.logger.warning(f"Error fetching {_url}: {exc}")
            return []

    # this is the end of _fetch_one_url() ----------------------------------------------------------------------------------



    def fetch_all_urls(self) -> List[Row]:
        rows: List[Row] = []
        rows.extend(self._fetch_one_url())

        return rows



    def run(self) -> None:
        """
        This is what the user calls to run the loop.

        :return: None
        """
        # Get data from web, and store in 'html'
        html = self.fetch_all_urls()

        # Instantiate a SessionParser object, passing a soup object of the 'html', and the logger object
        # Store the return value in 'parsed'
        # We should be given a list of extracted columns from SessionParser,w hich in turn will be used to display
        # in the TUI.
        # parsed: List[Row] = SessionParser(BeautifulSoup(html, "html.parser"), self.logger, len(HEADERS)).parser()
        # print(len(SessionBrowser.HEADERS))

# --- END OF class SessionBrowser definition ------------------------------------------------------------------------------------------



def main() -> None:
    """
    Create and set up the logger object.

    :return:    None
    """

    # --- define an argument parser for the user's convenience
    arg_parser = argparse.ArgumentParser(description     = ARGUMENT_DESCRIPTION,
                                         epilog          = ARGUMENT_EPILOG,
                                         formatter_class = ARGUMENT_FORMATTER_CLASS)

    arg_parser.add_argument("--year",
                            type = int,
                            default = datetime.now().year,
                            help = "Year (default: current year)")

    arg_parser.add_argument("--scope",
                            choices = ("master", "intensive", "both"),
                            default = "both",
                            help = "Which schedules to include (default: both)")

    args = arg_parser.parse_args()

    from log_setup import log_filename
    logger = setup_logger(filename = log_filename, to_stdout = False)
    logger.info("Script started")

    sb = SessionBrowser(_year   = args.year,
                        _logger = logger,
                        _scope  = args.scope)
    # print(sb.__dict__)
    # sb.fetch_data_from_web()



if __name__ == "__main__":
    main()
