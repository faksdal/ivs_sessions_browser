# flake8: noqa
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
from bs4    import BeautifulSoup

# Project defined imports
from .defs      import FIELD_INDEX, HEADERS, List, Row
from .operators import load_operator_bindings, load_operator_assignments, save_operator_assignments
# ─── END OF Import section ────────────────────────────────────────────────────



class SessionsTuiFormatter:

    """
    Docstring for SessionsTuiFormatter
    """

    def __init__(self):#,
                 #_soup:             BeautifulSoup,
                 #_num_of_headers:   int,
                 #_is_intensive:     bool,
                 #_filters:          str | None,
                 #_url:              str | None = None,
                 #) -> None:

        """
        Docstring for __init__

        :param _soup:           The BeautifulSoup object containing the downloaded HTML.
        :param _num_of_headers: The actual number of headers as expected in the session table.
        :param _is_intensive:   True/False indicating if the session is intensive.
                                This is used to add the [I] marker in the Type column.
        :param _filters:        String containing filter criteria to apply to sessions.
        """

        self.header_line = " | ".join([f"{title:<{w}}" for title, w in HEADERS])

        self.operator_bindings      = load_operator_bindings()
        self.operator_assignments   = load_operator_assignments()

        # Create an empty list to store parsed rows, we will .append() to this
        # in the build_list() method as we go along
        self.full_list: list[tuple[list[str], str | None, dict]] = []

    # ─── END OF __init__() ────────────────────────────────────────────────────



    def build_list(self,
                   _soup:             BeautifulSoup,
                   _num_of_headers:   int,
                   _is_intensive:     bool,
                   _filters:          str | None,
                   _url:              str | None = None,
                   ) -> None:

        soup           = _soup
        num_of_headers = _num_of_headers
        is_intensive   = _is_intensive
        filters        = _filters
        url            = _url

        # Find all session rows in the HTML soup
        session_rows = soup.select("table tr")
        for r in session_rows:
            # Extract all <td> elements in the row, discard those that doesn't fit
            # the expected number of columns (headers)
            tds = r.find_all("td")
            if len(tds) < num_of_headers:
                continue

            # ──────────────────────────────────────────────────────────────────
            # Differentiate active vs removed stations in the 'stations' column
            # _split_stations_active_removed() render them as "Active [Removed]"
            # ──────────────────────────────────────────────────────────────────
            stations_str = self._split_stations_active_removed(tds)
            # ─── END OF Differentiate active vs removed stations ──────────────

            # ──────────────────────────────────────────────────────────────────
            # Add header for operator assignments
            # Operator, or 'op', gets added at index 0, shifting all other indices by 1
            # ──────────────────────────────────────────────────────────────────
            session_code = tds[1].get_text(strip=True) # values[1]
            op = self.operator_assignments.get(session_code, "")
            # ─── END OF Add header for operator assignments ───────────────────

            # ──────────────────────────────────────────────────────────────────
            # Assigning each column's value in 'values' list
            # ──────────────────────────────────────────────────────────────────
            values = [
                f"{op}" if op else "",
                tds[0].get_text(strip=True),    # Type
                tds[1].get_text(strip=True),    # Code
                tds[2].get_text(strip=True),    # Start
                tds[3].get_text(strip=True),    # DOY
                tds[4].get_text(strip=True),    # Dur
                # stations_str.ljust(44),       # Stations (fixed width for alignment)
                stations_str,                   # Stations (no padding; renderer will align)
                tds[6].get_text(strip=True),    # DB Code
                tds[7].get_text(strip=True),    # Ops Center
                tds[8].get_text(strip=True),    # Correlator
                tds[9].get_text(strip=True),    # Status
                tds[10].get_text(strip=True),   # Analysis
            ]
            # ─── END OF Assigning each column's value in 'values' list ────────

            # ──────────────────────────────────────────────────────────────────
            # Visualise intensive sessions
            # This is done by adding '[I]' to the Type column
            # Tag intensives directly, no padding here; alignment happens in the renderer
            # ──────────────────────────────────────────────────────────────────
            if is_intensive:
                # values[1] = f"{values[1]}[I]"
                values[1] += f"[I]"
            # ─── END OF Visualise intensive sessions ──────────────────────────

            # ──────────────────────────────────────────────────────────────────
            # Prepare session detail URL
            # It will go into the metadata for this row
            # ──────────────────────────────────────────────────────────────────
            # Session detail URL from Code column if present
            code_link = values[2].lower()
            session_url = f"{url}/{code_link}" if url and code_link else None
            # ─── END OF Prepare session detail URL ────────────────────────────

            # ──────────────────────────────────────────────────────────────────
            # Prepare metadata dictionary for this row
            # Metadata dictionary for this row, all rows are visible by default
            # Filtering the list based on stations_filter happens in the TUI renderer
            # by turning the 'visible' flag on/off
            # ──────────────────────────────────────────────────────────────────
            meta =  {"visible":      True,
                     "intensive":    is_intensive,
                     "code":         session_code
                    }
            # ─── END OF Prepare metadata dictionary for this row ──────────────

            # ──────────────────────────────────────────────────────────────────
            # Append the parsed row to the full_list
            # ──────────────────────────────────────────────────────────────────
            self.full_list.append((values, session_url, meta))
            # ─── END OF Append the parsed row to the full_list ────────────────

        # ─── END OF 'for r in session_rows' ───────────────────────────────────
    # ─── END OF run() ─────────────────────────────────────────────────────────



    def _match_stations_filter(self, _hay: str, _expr: str) -> bool:
        return True
    # ─── END OF _match_stations_filter() ──────────────────────────────────────



    def _split_stations_active_removed(self, _tds) -> str:

        # ──────────────────────────────────────────────────────────────────
        # Differentiate active vs removed stations in the 'stations' column
        # Render as "Active [Removed]".
        # Find the current index of 'stations', and assign an attribute.
        # ──────────────────────────────────────────────────────────────────
        index = FIELD_INDEX.get("stations", -1)
        if index == -1:
            print("Index error on 'stations', exiting...")
            exit(-1)

        # This is the cell, or column, containing all the stations, and we
        # want to separate the active from the removed.
        # The reason for subtracting 1 is because we added 'op' as index 0,
        # but the website doesn't have that column, so all indices are shifted
        # by one.
        stations_cell = _tds[index-1]

        # Two empty lists to hold active vs removed stations.
        active_ids  : List[str] = []
        removed_ids : List[str] = []

        # This is the logic, going through all list items in the
        # stations_cell column, extracting and sorting active and removed
        # stations separately.
        for li in stations_cell.find_all("li", class_="station-id"):
            classes = li.get("class", [])
            code    = li.get_text(strip=True)
            removed_ids.append(code) if "removed" in classes else active_ids.append(code)

        # And putting them into separate lists
        active_str  = "".join(active_ids)
        removed_str = "".join(removed_ids)

        # And now we're rendering the stations string, with the active and
        # removed sessions separated. They will be written as
        # "active [removed]", with the removed in square brackets.
        if active_str and removed_str:
            stations_str = f"{active_str} [{removed_str}]"
        elif removed_str:
            stations_str = f"[{removed_str}]"
        else:
            stations_str = f"{active_str}"

        return stations_str
        # ─── END OF Differentiate active vs removed stations ──────────────
    # ─── END OF _split_stations_active_removed() ──────────────────────────────



    def recompute_header_widths(self, rows: list[Row]) -> None:
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
