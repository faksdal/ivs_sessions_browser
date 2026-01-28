# isort: skip_file

"""SessionsTuiFormatter

Scan a BeautifulSoup `soup` and produce formatted lines for the TUI.

This module provides a small, dependency-light formatter that uses
heuristics to find session-like elements in the parsed HTML and
convert them into single-line strings suitable for a text UI.
"""

# ──────────────────────────────────────────────────────────────────────────────
# Import section
# ──────────────────────────────────────────────────────────────────────────────
# from ast import Dict
# from typing import Iterator, Optional
from bs4    import BeautifulSoup #, Tag

# Project defined imports
from .defs import FIELD_INDEX, HEADERS, List, Row
# ─── END OF Import section ────────────────────────────────────────────────────



class SessionsTuiFormatter:

    """
    Docstring for SessionsTuiFormatter
    """

    def __init__(self,
                 _soup:             BeautifulSoup,
                 _num_of_headers:   int,
                 _is_intensive:     bool,
                 _filters:          str,
                 #_operator_map:     Optional[Dict[str, str]] = None
                 ) -> None:
        
        """
        Docstring for __init__
        
        :param _soup:           The BeautifulSoup object containing the downloaded HTML.        
        :param _num_of_headers: The actual number of headers as expected in the session table.
        :param _is_intensive:   True/False indicating if the session is intensive.
                                This is used to add the [I] marker in the Type column.        
        :param _filters:        String containing filter criteria to apply to sessions.        
        """
        
        self.soup           = _soup
        self.num_of_headers = _num_of_headers
        self.is_intensive   = _is_intensive
        self.filters        = _filters
        #self.operator_map   = _operator_map or {}
        print("SessionsTuiFormatter initialized")

        self.header_line = " | ".join([f"{title:<{w}}" for title, w in HEADERS])
    # ─── END OF __init__() ────────────────────────────────────────────────────



    def run(self) -> None:
        # print(self.header_line)        
        # print("SessionsTuiFormatter run() method called.")

        # Create an empty list to store parsed rows, we will .append() to this as we go along
        parsed: List[Row] = []

        # Find all session rows in the HTML soup, they're the ones tagged <tr>
        session_rows = self.soup.select("table tr")
        

        for r in session_rows:            
            # Extract all <td> elements in the row, discard those that doesn't fit
            # the expected number of columns (headers)
            tds = r.find_all("td")
            if len(tds) < self.num_of_headers:
                continue

        # ──────────────────────────────────────────────────────────────────────
        # Differentiate active vs removed stations in the 'stations' column
        # ──────────────────────────────────────────────────────────────────────
            # Stations: differentiate between active and removed. Render as "Active [Removed]".
            # Find the current index of 'stations', and assign an attribute.
            index = FIELD_INDEX.get("stations", -1)
            if index == -1:
                print("Index error on 'stations', exiting...")
                exit(-1)

            # This is the cell, or column, containing all the stations, and we want to separate the
            # active from the removed.
            # The reason for subracting 1 is becasue we added 'op' as index 0, but the website
            # doesn't have that column, so all indices are shifted by one.
            stations_cell = tds[index-1]

            # Two empty lists to hold active vs removed stations.
            active_ids  : List[str] = []
            removed_ids : List[str] = []

            # This is the logic, going through all list items in the stations_cell column, extracting
            # and sorting active and removed stations separately.
            for li in stations_cell.find_all("li", class_="station-id"):
                classes = li.get("class", [])
                code    = li.get_text(strip=True)
                removed_ids.append(code) if "removed" in classes else active_ids.append(code)

            # And putting them into separate lists
            active_str  = "".join(active_ids)
            removed_str = "".join(removed_ids)

            # And now we're rendering the stations string, with the active and removed sessions
            # separated. They will be written as "active [removed]", with the removed in square brackets.
            if active_str and removed_str:
                stations_str = f"{active_str} [{removed_str}]"
            elif removed_str:
                stations_str = f"[{removed_str}]"
            else:
                stations_str = f"{active_str}"
                
            print(f"Stations parsed: {stations_str}")

        # ─── END OF Differentiate active vs removed stations ──────────────────

        # ─── END OF 'for r in session_rows' ───────────────────────────────────
            

    # ─── END OF run() ─────────────────────────────────────────────────────────



    def recompute_header_widths(rows: list[Row]) -> None:
        """
        Recompute HEADERS/HEADER_DICT/WIDTHS/HEADER_LINE from data.
        Ensures 'Type' has room for a right-justified '[I]' if any intensive exists.
        
        This function scans all parsed rows to determine the actual maximum width
        needed for each column, taking into account:
        - Minimum width specified in HEADERS
        - Header title length
        - Observed data length across all rows
        """

        global HEADERS, HEADER_DICT, WIDTHS, HEADER_LINE
        
        titles = [t for t, _ in HEADERS]
        mins   = [w for _, w in HEADERS]
        num    = len(titles)
        
        # --- Observed content lengths per column
        obs = [0] * num
        any_intensive = False
        for values, _url, meta in rows:
            any_intensive = any_intensive or bool(meta.get("intensive"))
            for i in range(min(num, len(values))):
                obs[i] = max(obs[i], len(values[i]))
        
        name_lens = [len(t) for t in titles]
        widths = [max(mins[i], name_lens[i], obs[i]) for i in range(num)]
        
        # --- Add some chars for "[I]" if any intensive is present
        type_idx = FIELD_INDEX.get("type", 1)
        if any_intensive:
            widths[type_idx] = max(widths[type_idx], name_lens[type_idx], mins[type_idx]) + 2
        
        HEADERS = list(zip(titles, widths))
        HEADER_DICT = dict(HEADERS)
        WIDTHS = widths
        HEADER_LINE = " | ".join([f"{title:<{w}}" for title, w in HEADERS])
    # ─── END OF recompute_header_widths() ─────────────────────────────────────