
import re
import logging

from typing     import List, Tuple, Optional, Dict, Any
from bs4        import BeautifulSoup
from type_defs  import Row, FIELD_INDEX, HEADERS, HEADER_LINE, WIDTHS



class SessionParser:
    """
    SessionParser takes care of parsing the BeautifulSoup object sent from the SessionBrowser object.
    It populates the instance attribute 'self.parsed' with the selected data
    The parsing takes place in the method 'parser', which returns the list to the sender

    Note: Should the parser be responsible for filtering?
    """

    def __init__(self,
                 _soup:             BeautifulSoup,
                 _logger:           logging.Logger,
                 _num_of_headers:   int,
                 _is_intensive:     bool,
                 _stations_filter: Optional[str] = None,
                 _sessions_filter: Optional[str] = None
                 ) -> None:
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
        self.num_of_headers     = _num_of_headers
        self.is_intensive       = _is_intensive
        self.stations_filter    = _stations_filter
        self.sessions_filter    = _sessions_filter

        # --- declare an empty list to be populated and returned
        self.parsed: List[Row]  = []

        # print(f"self.is_intensive: {self.is_intensive}")



    def parse(self) -> List[Row]:
        """
        """

        parsed: List[Row] = []
        session_rows = self.soup.select("table tr")
        # self.logger.debug(f"SessionParser.parse(): session_rows: {session_rows}")

        for r in session_rows:
            tds = r.find_all("td")
            if len(tds) < self.num_of_headers:
                continue

            # --- Stations: differentiate between active and removed. Render as "Active [Removed]"
            # --- Find the current index of 'stations', and assign an attribute
            index = FIELD_INDEX.get("stations", -1)
            if index == -1:
                self.logger.error("SessionParser.parse(): Index error on 'stations', exiting...")
                print("Index error on 'stations', exiting...")
                exit(-1)

            # this is the cell, or column, containing all the stations
            stations_cell           = tds[index]

            # --- two empty lists to hold active vs removed stations
            active_ids:     List[str]   = []
            removed_ids:    List[str]   = []

            for li in stations_cell.find_all("li", class_ = "station-id"):
                classes = li.get("class", [])
                code    = li.get_text(strip = True)
                removed_ids.append(code) if "removed" in classes else active_ids.append(code)

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

            # Tag intensives directly in Type column (right-align "[I]" in the Type field)
            if self.is_intensive:
                base_width = max(0, TYPE_WIDTH - 3)  # room for "[I]"
                values[0] = f"{values[0]:<{base_width}}[I]"
            else:
                values[0] = f"{values[0]:<{TYPE_WIDTH}}"

            # Session detail URL from Code column if present
            code_link   = tds[1].find("a")
            session_url = (f"https://ivscc.gsfc.nasa.gov{code_link['href']}"
                           if code_link and code_link.has_attr("href")
                           else None)

            # if stations_filter is set,and there is NO match between the active_str and the stations_filter,
            # continue the 'for r in session_rows loop'; e.g. we have no match
            if self.stations_filter and not self._match_stations(active_str, self.stations_filter):
                continue

            # if sessions_filter is set,and there is NO match between the values[1] and the sessions_filter,
            # continue the 'for r in session_rows loop'; e.g. we have no match
            # values[1] is the column for session name, e.g. R41223, and so on
            if self.sessions_filter and self.sessions_filter not in values[1]:
                continue

            # if we are here, we're good to append the current r in rows to the parsed List[Row]
            meta = {"active": active_str, "removed": removed_str}
            # self.logger.debug(f"values: {values}, session_url: {session_url}, meta: {meta}")
            parsed.append((values, session_url, meta))

        return parsed
    # --- END OF parse() -----------------------------------------------------------------------------------------------



    def _match_stations(self, hay: str, expr: str) -> bool:
        text = expr.strip()
        if not text:
            return True
        has_or = '|' in text
        has_and = '&' in text
        if has_or or has_and:
            or_parts = [p.strip() for p in re.split(r"\s*\|{1,2}\s*", text) if p.strip()]
            for part in or_parts:
                and_chunks = [c.strip() for c in re.split(r"\s*&{1,2}\s*", part) if c.strip()]
                and_tokens: List[str] = []
                for chunk in and_chunks:
                    and_tokens.extend([t for t in re.split(r"[ ,+]+", chunk) if t])
                if and_tokens and all(tok in hay for tok in and_tokens):
                    return True
                if not and_tokens and part and part in hay:
                    return True
            return False
        tokens = [t for t in re.split(r"[ ,+]+", text) if t]
        return all(tok in hay for tok in tokens)



    def _extract_station_tokens(self, _query: str) -> List[str]:
        """
        Highlight helper, to be called from within class, not from an instance outside
        Pull station codes from any station-related clause in the current filter
        Called from the 'while True:' in curses main loop when the user type '/' to apply filtering
        Whatever the user types, is passed as '_query', for instance '/ stations: "Ns|Nn"'
        :param _query:  The query passed by the caller, from which to extract station names (Nn, Ns, etc.)
        :return:        A list of strings
        """

        # if we're passed an empty query, return with nothing
        if not _query:
            return []

        # define and initialize some local instance attributes #########################################################
        tokens: List[str] = []  # empty list of strings
        clauses = [c.strip() for c in _query.split(';') if c.strip()]  # splits _query by the ';', and
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