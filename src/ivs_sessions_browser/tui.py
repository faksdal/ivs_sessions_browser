# flake8: noqa
# isort: skip_file

"""
Defined in tui.py.


"""

# ──────────────────────────────────────────────────────────────────────────────
# Import section
# ──────────────────────────────────────────────────────────────────────────────
# from ast import Dict
# from typing import Iterator, Optional
from bs4    import BeautifulSoup
import curses

# Project defined imports
# from .defs      import FIELD_INDEX, HEADERS, List, Row
from . import defs as D
from .operators import load_operator_bindings, load_operator_assignments #, save_operator_assignments
from .filter_and_sort import FilterAndSort
# ─── END OF Import section ────────────────────────────────────────────────────



class Tui:

    """
    SessionsTuiFormatter class definition.

    Scan raw HTML tags, producing formatted lines for the TUI.

    This class is responsible for a few tasks:
        - converting the raw HTML data into formatted lines for TUI display
        - handling sessions filtering
        - rendering the TUI
        - managing operator assignments
    """

    def __init__(self):

        """
        Defined in tui.py.
        Docstring for __init__
        """

        self.header_line = " | ".join([f"{title:<{w}}" for title, w in D.HEADERS])

        self.operator_bindings      = load_operator_bindings()
        self.operator_assignments   = load_operator_assignments()
        
        # Create reverse mapping: operator label -> operator key (for color lookup)
        self.operator_label_to_key  = {v: k for k, v in self.operator_bindings.items() if v}

        # Create an empty list to store parsed rows, we will .append() to this
        # in the build_list() method as we go along
        self.full_list: list[tuple[list[str], str | None, dict]] = []
        
        # Create filter and sort instance for filtering/sorting operations
        self.filter_sort = FilterAndSort()

    # ─── END OF __init__() ────────────────────────────────────────────────────



    def draw_header(self,
                    _stdscr,
                    _theme: TUITheme,
                    _state: UIState) -> None:
        """
        Draws up the header line on top of the terminal window using curses.
        Sets up the test to write, and the attributes for the text.
        Writes the header line and the dotted line underneath, at the top of the terminal

        :param _stdscr:
        :param _theme:
        :param _state:

        :return:    None
        """

        self._addstr_clip(_stdscr, 0, 0, "  " + D.HEADER_LINE, _theme.header)
        self._addstr_clip(_stdscr, 1, 0, "  " + "─" * len(D.HEADER_LINE))        
    # ─── END OF draw_header() ─────────────────────────────────────────────────



    def show_help(self, _stdscr, _theme) -> None:
        """
        Display centered, boxed help screen. Dismiss with any key.

        :param _stdscr: Curses screen object
        :param _theme: TUITheme for colors
        :return: None
        """
        h, w = _stdscr.getmaxyx()
        width = min(84, w - 4)
        height = min(len(D.HELP_TEXT) + 4, h - 4)
        y, x = (h - height) // 2, (w - width) // 2
        win = curses.newwin(height, width, y, x)
        win.box()

        for i, text in enumerate(D.HELP_TEXT, start=1):
            attr = 0
            if i == 1:  # title
                attr = curses.A_UNDERLINE | curses.A_BOLD
            elif "Green" in text:
                attr = _theme.released
            elif "Yellow" in text:
                attr = _theme.processing
            elif "Magenta" in text:
                attr = _theme.cancelled
            elif "White" in text:
                attr = _theme.none
            elif "Cyan" in text:
                attr = _theme.filtered

            win.addnstr(i, 2, text, width - 4, attr)

        win.refresh()
        win.getch()
    # ─── END OF show_help() ───────────────────────────────────────────────────



    def _addstr_clip(self, _stdscr, _y: int, _x: int, _text: str, _attr: int = 0) -> None:
        """
        Writes a string to curses _stdscr, clipping if necessary

        :param _stdscr:  Which screen to write to
        :param _y:       y co-ordinate
        :param _x:       x co-ordinate
        :param _text:    What to write
        :param _attr:    Text attributes

        :return:        None
        """

        max_y, max_x = _stdscr.getmaxyx()
        if _y >= max_y or _x >= max_x:
            return

        _stdscr.addstr(_y, _x, _text[: max_x - _x - 1], _attr)
    # ─── END OF _addstr_clip() ────────────────────────────────────────────────



    def draw_helpbar(self,
                     _stdscr,
                     _view_rows: list[D.Row],
                     _current_filter: str | None,
                     _theme,
                     _state) -> None:
        """
        Draws help bar at the bottom of the terminal with keyboard shortcuts,
        operator bindings, active filter, and row position information.

        :param _stdscr: Curses screen object
        :param _view_rows: Current visible/filtered rows
        :param _current_filter: Active filter string
        :param _theme: TUITheme object for colors
        :param _state: UIState object with current state
        :return: None
        """

        max_y, max_x = _stdscr.getmaxyx()
        
        # Main help text with keyboard shortcuts
        help_text = D.HELP_BAR_TEXT
        
        # Operator bindings (only show configured operators)
        ops_text = ""
        if self.operator_bindings:
            parts = []
            for k in sorted(self.operator_bindings.keys(), key=lambda s: int(s) if str(s).isdigit() else 99):
                v = (self.operator_bindings.get(k) or "").strip()
                if k == "0":
                    # Show 0 as "clear" it's mapped to empty string
                    if v == "":
                        parts.append("0:Clr")
                    else:
                        parts.append(f"0:{v}")
                else:
                    if v:
                        parts.append(f"{k}:{v}")
            if parts:
                ops_text = "  Op: " + " ".join(parts)

        # Row position indicator (current/total and remaining)
        right = f"row {min(_state.selected + 1, len(_view_rows))}/{len(_view_rows)}({len(_view_rows) - (min(_state.selected + 1, len(_view_rows)))})"

        # Construct full help bar text
        bar = (help_text
               + ops_text
               + (f" Filter: {_current_filter}" if _current_filter else "")
               + "  "
               + right)[: max_x - 1]
        
        bar_attr = _theme.help_bar if _state.has_colors else _theme.reversed
        self._addstr_clip(_stdscr, max_y - 1, 0, bar, bar_attr)
    # ─── END OF draw_helpbar() ────────────────────────────────────────────────



    def draw_rows(self,
                  _stdscr,
                  _rows:                list[D.Row],
                  _highlight_tokens:    list[str],
                  _theme,
                  _state) -> None:
        """
        Draws all the rows to terminal with proper formatting, colors, and highlighting.

        :param _stdscr: Curses screen object
        :param _rows: List of Row tuples to display
        :param _highlight_tokens: Station codes to highlight (from filter)
        :param _theme: TUITheme object for colors
        :param _state: UIState object with selection and view state
        :return: None
        """

        # Normalize state attributes if we're outside view boundaries
        if _state.selected < _state.offset:
            _state.offset = _state.selected
        elif _state.selected >= _state.offset + _state.view_height:
            _state.offset = _state.selected - _state.view_height + 1

        # Let the user know if we have nothing to show
        if not _rows:
            self._addstr_clip(_stdscr, 2, 0, "No sessions found.")
            return

        # Draw each visible row to terminal
        for i in range(_state.offset, min(len(_rows), _state.offset + _state.view_height)):
            row_vals, _, meta = _rows[i]

            # Copy, so we can override Stations column safely
            vals = list(row_vals)

            # If the user has chosen to hide removed stations, render only active in "stations" column
            if not _state.show_removed:
                active_only         = meta.get("active", "")
                field_index: int    = D.FIELD_INDEX.get("stations", -1)
                vals[field_index]   = f"{active_only:<{D.WIDTHS[field_index]}}"

            # Construct full line with a special rule for the "Type" column:
            # left-justify the type text in (width-3)
            # put "[I]" flush-right if meta["intensive"] is true
            parts       = []
            type_idx    = D.FIELD_INDEX.get("type", 0)
            for c, val in enumerate(vals):
                w = D.WIDTHS[c]
                if c == type_idx and meta.get("intensive"):
                    # reserve 3 chars for "[I]" at the right edge
                    base_w = max(0, w - 3)
                    parts.append(f"{val:<{base_w}}[I]")
                else:
                    parts.append(f"{val:<{w}}")

            y = i - _state.offset + 2

            # Get operator label from 'op' column and look up color
            op_label = vals[D.FIELD_INDEX.get("op", 0)].strip()
            op_key = self.operator_label_to_key.get(op_label, "0")  # Default to "0" (unassigned)
            
            # Determine row color based on operator
            if _state.has_colors and op_key in _theme.operator_colors:
                row_color = _theme.operator_colors[op_key]
            else:
                row_color = 0
            
            # Determine selection and basic flags; draw line first without A_REVERSE
            selected = (i == _state.selected)
            bold_flag = curses.A_BOLD if selected else 0

            # Marker and column attributes (no reverse yet)
            # marker = "► " if selected else "  "
            # marker = ""
            # marker_attr = row_color | bold_flag
            # self._addstr_clip(_stdscr, y, 0, marker, marker_attr)

            # Draw each column with operator color and white separators
            x_pos = 2   # The marker is gone, but to align with header which has
                        # 2 spaces padding, we keep x_pos starting at 2
            
            white_sep = curses.color_pair(1) if _state.has_colors else 0  # white

            for idx, part in enumerate(parts):
                # Draw column content with operator color (no reverse)
                col_attr = row_color | bold_flag
                self._addstr_clip(_stdscr, y, x_pos, part, col_attr)

                # Highlight intensive marker in Type column if present
                if idx == type_idx and "[I]" in part:
                    i_pos = part.find("[I]")
                    if i_pos != -1:
                        # Draw intensives in theme color; will be overridden by chgat when selected
                        # intensives_attr = _theme.intensivess if _state.has_colors else curses.A_BOLD
                        
                        # The [I] marker will be drawn in the current row color if
                        # colors are supported, otherwise it will be bold. When
                        # the row is selected, the entire row will be reversed, which
                        # will override the color but keep the bold.
                        intensives_attr = row_color if _state.has_colors else curses.A_BOLD
                        self._addstr_clip(_stdscr, y, x_pos + i_pos, "[I]", intensives_attr)

                x_pos += len(part)

                # Draw separator in white (except after last column)
                if idx < len(parts) - 1:
                    self._addstr_clip(_stdscr, y, x_pos, " | ", white_sep)
                    x_pos += 3

            # Station token highlighting (from stations:Xx filter)
            if vals[D.FIELD_INDEX.get("stations", -1)] and _highlight_tokens:
                # Padded field text as printed
                stations_text = vals[D.FIELD_INDEX.get("stations", -1)]

                # "stations" field index (add 2 for marker offset)
                col_x = self._col_start_x(D.FIELD_INDEX.get("stations", -1)) + 2

                # Station highlights override row colors (can't combine color pairs)
                hl_attr = (_theme.filtered | curses.A_BOLD) if _state.has_colors else (curses.A_BOLD | curses.A_UNDERLINE)
                for tok in _highlight_tokens:
                    start = 0
                    while True:
                        j = stations_text.find(tok, start)
                        if j == -1:
                            break
                        self._addstr_clip(_stdscr, y, col_x + j, tok, hl_attr)
                        start = j + len(tok)
            # If the row is selected, apply reverse (and bold) across the drawn line
            if selected:
                try:
                    max_y, max_x = _stdscr.getmaxyx()
                    # chgat length: cover from column 0 to the screen width
                    _stdscr.chgat(y, 0, max_x - 1, row_color | curses.A_REVERSE | curses.A_BOLD)
                except Exception:
                    # chgat may fail on some terminals; ignore errors and leave as-is
                    pass
    # ─── END OF draw_rows() ───────────────────────────────────────────────────



    def _col_start_x(self, _col_idx: int) -> int:
        """
        Computes the x offset where column _col_idx starts in the printed line.
        Each column is printed left-padded to WIDTHS[c], joined by " | " (3 chars).

        :param _col_idx: Column index
        :return: X offset position
        """
        sep = 3
        x   = 0
        for i in range(_col_idx):
            x += D.WIDTHS[i] + sep
        return x
    # ─── END OF _col_start_x() ────────────────────────────────────────────────



    def build_session_list(self,
                           _soup:             BeautifulSoup,
                           _num_of_headers:   int,
                           _is_intensive:     bool,
                           _filters:          str | None,
                           _url:              str | None = None,
                           ) -> None:
        """
        Defined in tui.py.

        build_list() parses the read HTML content, and add formatted rows, url
        and metadata like visible, is_intensive and code, to self.full_list.
        After its completion, self.full_list items can be rendered in the TUI.

        No filtering is done here, all rows are added to self.full_list.
        Filtering based on self.filters is done in the TUI renderer by turning
        the 'visible' flag on/off in the metadata dictionary for each row.

        :param self: Description
        :param _soup: Description
        :type _soup: BeautifulSoup
        :param _num_of_headers: Description
        :type _num_of_headers: int
        :param _is_intensive: Description
        :type _is_intensive: bool
        :param _filters: Description
        :type _filters: str | None
        :param _url: Description
        :type _url: str | None
        """

        soup            = _soup
        num_of_headers  = _num_of_headers
        is_intensive    = _is_intensive
        self.filters    = _filters
        url             = _url

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
            # Also returns active/removed strings for filtering
            # ──────────────────────────────────────────────────────────────────
            stations_str, active_str, removed_str = self._split_stations_active_removed(tds)
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
            # Prepare session detail URL
            # It will go into the metadata for this row
            # ──────────────────────────────────────────────────────────────────
            # Session detail URL from Code column if present
            code_link = values[2].lower()
            session_url = f"{url}/{code_link}" if url and code_link else None
            # ─── END OF Prepare session detail URL ────────────────────────────

            # ──────────────────────────────────────────────────────────────────
            # Prepare metadata dictionary for this row
            # Metadata dictionary for this row
            # Includes active/removed station strings for filtering
            # ──────────────────────────────────────────────────────────────────
            meta =  {
                     "intensive":    is_intensive,
                     "code":         session_code,
                     "active":       active_str,
                     "removed":      removed_str
                    }
            # ─── END OF Prepare metadata dictionary for this row ──────────────

            # ──────────────────────────────────────────────────────────────────
            # Append the parsed row to the full_list
            # ──────────────────────────────────────────────────────────────────
            self.full_list.append((values, session_url, meta))
            # ─── END OF Append the parsed row to the full_list ────────────────

        # ─── END OF 'for r in session_rows' ───────────────────────────────────
    # ─── END OF build_session_list() ──────────────────────────────────────────



    def apply_filters_and_sorting(self,
                                   _query: str | None = None,
                                   _show_removed: bool = True,
                                   _sort_key: str = "start",
                                   _ascending: bool = True) -> list[D.Row]:
        """
        Apply filters and sorting to self.full_list and return the filtered/sorted view.
        
        Uses the FilterAndSort class to apply complex filtering with OR/AND logic
        for stations and other fields, plus sorting by any column.
        
        :param _query: Filter query string (e.g., "code: r1|r4; stations: Nn&Ns")
        :param _show_removed: Whether to show stations marked as removed
        :param _sort_key: Field name to sort by (matches FIELD_INDEX keys)
        :param _ascending: Sort in ascending order if True, descending if False
        :return: Filtered and sorted list of Row tuples
        """
        
        return self.filter_sort.apply(
            self.full_list,
            _query or "",
            _show_removed=_show_removed,
            _sort_key=_sort_key,
            _ascending=_ascending
        )
    # ─── END OF apply_filters_and_sorting() ───────────────────────────────────



    def _match_stations_filter(self, _hay: str, _expr: str) -> bool:
        return True
    # ─── END OF _match_stations_filter() ──────────────────────────────────────



    def _split_stations_active_removed(self, _tds) -> tuple[str, str, str]:

        # ──────────────────────────────────────────────────────────────────
        # Differentiate active vs removed stations in the 'stations' column
        # Render as "Active [Removed]".
        # Find the current index of 'stations', and assign an attribute.
        # ──────────────────────────────────────────────────────────────────
        index = D.FIELD_INDEX.get("stations", -1)
        if index == -1:
            print("Index error on 'stations', exiting...")
            exit(-1)

        # This is the cell, or column, containing all the stations, and we
        # want to separate the active from the removed.
        # The reason for subtracting 1 is because we added 'op' at index 0,
        # but the website doesn't have that column, so all indices are shifted
        # by one.
        stations_column = _tds[index-1]

        # Two empty lists to hold active vs removed stations.
        active_ids  : D.List[str] = []
        removed_ids : D.List[str] = []

        # This is the logic, going through all list items in the
        # stations_column, extracting and sorting active and removed
        # stations separately.
        for li in stations_column.find_all("li", class_="station-id"):
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

        # Return display string plus active/removed for filtering
        return stations_str, active_str, removed_str
        # ─── END OF Differentiate active vs removed stations ──────────────
    # ─── END OF _split_stations_active_removed() ──────────────────────────────



    def recompute_header_widths(self) -> None:
        """
        Recompute width of each column in HEADERS based on the actual data in
        self.full_list, ensuring that all content fits properly.
        Also taking into account that 'Type' has room for a right-justified '[I]'
        if any intensive exists.

        This function scans all parsed rows to determine the actual maximum width
        needed for each column, taking into account:
        - Minimum width specified in D.HEADERS
        - Header title length
        - Observed data length across all rows in self.full_list
        """

        # Extract header titles and their minimum widths from D.HEADERS
        titles = [t for t, _ in D.HEADERS]
        mins   = [w for _, w in D.HEADERS]
        num    = len(titles)

        # Track observed maximum widths for each column
        obs             = [0] * num
        any_intensive   = False
        
        # Scan all rows in self.full_list to find maximum data widths
        for values, _url, meta in self.full_list:
            any_intensive = any_intensive or bool(meta.get("intensive"))
            for i in range(min(num, len(values))):
                obs[i] = max(obs[i], len(values[i]))

        # Calculate final widths: max of (minimum width, header title length, observed data length)
        name_lens = [len(t) for t in titles]
        widths = [max(mins[i], name_lens[i], obs[i]) for i in range(num)]

        # Add extra space for "[I]" marker in Type column if any intensive sessions exist
        type_idx = D.FIELD_INDEX.get("type", 1)
        if any_intensive:
            widths[type_idx] = max(widths[type_idx], name_lens[type_idx] + 3, mins[type_idx] + 3)

        # Update the global constants in defs module
        D.HEADERS = list(zip(titles, widths))
        D.HEADER_DICT = dict(D.HEADERS)
        D.WIDTHS = widths
        D.HEADER_LINE = " | ".join([f"{title:<{w}}" for title, w in D.HEADERS])
        
        # Update instance header_line to reflect the new computed widths
        self.header_line = D.HEADER_LINE
    # ─── END OF recompute_header_widths() ─────────────────────────────────────



    def clear_screen(self, _stdscr) -> None:
        """
        Clears the screen _stdscr

        :return: None
        """

        _stdscr.clear()
    # ─── END OF clear_screen() ────────────────────────────────────────────────
