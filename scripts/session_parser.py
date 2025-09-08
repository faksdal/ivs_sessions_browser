
import logging

from typing     import List, Tuple, Optional, Dict, Any
from bs4        import BeautifulSoup
from type_defs  import Row, FIELD_INDEX, HEADERS, HEADER_LINE, WIDTHS



class SessionParser:
    """
    SessionParser takes care of parsing the BeautifulSoup object sent from the SessionBrowser object.
    It populates the instance attribute 'self.parsed' with the selected data
    The parsing takes place in the method 'parser', which returns the list to the sender
    """

    def __init__(self,
                 _soup:             BeautifulSoup,
                 _logger:           logging.Logger,
                 _num_of_headers:   int) -> None:
        """
        Initializer for SessionBrowser object. It takes a bs4 soup and logger object as parameters.
        The SessionParser is responsible for parsing the soup, generating a list (or tuplet) with the extracted data.

        :param _soup:           BeautifulSoup object from which we will extract our data
        :param _logger:         Logger object, we're logging to a file
        :param _num_of_headers: Integer value to hold the number of headers we want
        :return:                None
        """

        # --- Assign instance attributes from params
        self.soup               = _soup
        self.logger             = _logger
        self.num_of_headers    = _num_of_headers

        # --- declare an empty list to be populated and returned
        self.parsed: List[Row]  = []



    def parser(self) -> List[Row]:
        """
        Parses the instance attribute self.soup, populating self.parsed

        :return List[Row]:  Returns teh list self.parsed
        """

        session_rows = self.soup.select("table tr")

        for r in session_rows:
            tds = r.find_all("td")
            if len(tds) < self.num_of_headers:
                continue

            # --- Stations: differentiate between active and removed. Render as "Active [Removed]"
            # --- Find the current index of 'stations', and assign an attribute
            index = FIELD_INDEX.get("stations", -1)
            if index == -1:
                self.logger.error("Index error on 'stations', exiting...")
                print("Index error on 'stations', exiting...")
                exit(-1)

            # --- stations_cell; this is what it looks like
                # < li class ="station-id removed" >
                # < a href = "/sessions/stations/ur/" > Ur < / a >
                # < / li >
                # < li class ="station-id removed" >
                # < a href = "/sessions/stations/yg/" > Yg < / a >
                # < / li >
                # < / ul >
                # < / td >
            stations_cell           = tds[index]

            # --- two empty lists to hold active vs removed stations
            active_ids:     List[str]   = []
            removed_ids:    List[str]   = []

            # --- Small for-loop to iterate over stations_cell, populating classes and code with station codes and
            # --- whether they're active or removed. A ternary operator serves as a switch to populate the correct list.
                # classes: ['station-id', 'removed'], code: Yg
                # classes: ['station-id', 'removed'], code: Ww
                # classes: ['station-id', 'removed'], code: Ke
                # classes: ['station-id'], code: Yg
            for li in stations_cell.find_all("li", class_ = "station-id"):
                classes = li.get("class", [])
                code    = li.get_text(strip = True)
                removed_ids.append(code) if "removed" in classes else active_ids.append(code)
                # if "removed" in classes:
                #     removed_ids.append(code)
                # else:
                #     active_ids.append(code)

                # --- this is how the lists look at this point
                    # Removed stations: [], active stations: ['Ag', 'Ft', 'Hb', 'Ht', 'Is', 'Ke', 'Kv', 'Mc', 'Nn', 'On', 'Wz', 'Yg']
                    # Removed stations: [], active stations: ['Bd', 'Ht', 'Ma', 'Sv', 'Zc']
                    # Removed stations: ['Sh'], active stations: ['Ag', 'Ht', 'Kk', 'Kv', 'Ma', 'Nn', 'On', 'Wz']
            active_str  = "".join(active_ids)
            removed_str = "".join(removed_ids)

            if active_str and removed_str:
                stations_str = f"{active_str} [{removed_str}]"
            elif removed_str:
                stations_str = f"[{removed_str}]"
            else:
                stations_str = f"{active_str}"

            values = [
                tds[0].get_text(strip=True),  # Type
                tds[1].get_text(strip=True),  # Code
                tds[2].get_text(strip=True),  # Start
                tds[3].get_text(strip=True),  # DOY
                tds[4].get_text(strip=True),  # Dur
                stations_str.ljust(44),  # Stations (fixed width for alignment)
                tds[6].get_text(strip=True),  # DB Code
                tds[7].get_text(strip=True),  # Ops Center
                tds[8].get_text(strip=True),  # Correlator
                tds[9].get_text(strip=True),  # Status
                tds[10].get_text(strip=True),  # Analysis
            ]

            # Column width for Type (class attribute, so prefix with the class)
            TYPE_WIDTH = next(w for title, w in HEADERS if title == "Type")


            # print(f"TYPE_WIDTH: {TYPE_WIDTH}")
            # print(f"stations_str: {stations_str}")

        return self.parsed



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