
import logging

from typing import List
from bs4 import BeautifulSoup



class SessionParser:

    def __init__(self,
                 _soup:     BeautifulSoup,
                 _logger:   logging.Logger) -> None:
        """
        Initializer for SessionBrowser object. It takes a bs4 soup and logger object as parameters.
        The SessionParser is responsible for parsing the soup, generating a list (or tuplet) with the extracted data.

        :param _soup:   BeautifulSoup object from which we will extract our data
        :param _logger: Logger object, we're logging to a file
        :return:        None
        """
        self.soup   = _soup
        self.logger = _logger



    def _extract_station_tokens(self, _query: str) -> List[str]:
        """
        Highlight helper, to be called from within class, not from an instance outside
        Pull station codes from any station-related clause in the current filter
        Called from the 'while True:' in curses main loop when the user type '/' to apply filtering
        Whatever the user types, is passed as '_query', for instance '/ stations: "Ns|Nn"'
        :param _query:  The query passed by the caller, from which to extract station names (Nn, Ns, etc.)
        :return:        A list of strings
        """
        print("Inside _extract_station_tokens()")
        # # if we're passed an empty query, return with nothing
        # if not _query:
        #     return []
        #
        # # define and initialize some local instance attributes #########################################################
        # tokens: List[str] = []  # empty list of strings
        # clauses = [c.strip() for c in _query.split(';') if c.strip()]  # splits _query by the ';', and
        # # strips away any whitespace, storing
        # # what's left in 'clauses'
        # ################################################################################################################
        # for clause in clauses:
        #     if ':' not in clause:
        #         continue
        #     field, value = [p.strip() for p in clause.split(':', 1)]
        #     fld = field.lower()
        #     if fld in ("stations", "stations_active", "stations-active",
        #                "stations_removed", "stations-removed",
        #                "stations_all", "stations-all"):
        #         parts = re.split(r"[ ,+|&]+", value)
        #         tokens.extend([p for p in parts if p])
        #
        # # Deduplicate; longer-first to avoid partial-overwrite visuals (e.g., 'Ny' vs 'Nya')
        # return sorted(set(tokens), key=lambda s: (-len(s), s))
    # this is the end of _extract_station_tokens() #####################################################################