#! ../.venv/bin/python3

# --- This is a re-write of the ivs_sessions_browser.py script
#
# --- jole 2025

# --- Import section ---------------------------------------------------------------------------------------------------
import argparse
import curses
import webbrowser
import re
from typing             import Optional, List, Tuple, Dict, Any
from datetime           import datetime, date
from log_helper         import *
from url_helper         import URLHelper
from type_defs          import (Row,
                                FIELD_INDEX,
                                HEADERS,
                                HEADER_LINE,
                                WIDTHS,
                                ARGUMENT_DESCRIPTION,
                                ARGUMENT_EPILOG,
                                ARGUMENT_FORMATTER_CLASS,
                                NAVIGATION_KEYS
                               )
# --- END OF Import section --------------------------------------------------------------------------------------------



# --- Class definition -------------------------------------------------------------------------------------------------
class SessionBrowser:
    """
    Class SessionBrowser: Holds most of the functionality for navigating and filtering the list
    """

    def __init__(self,
                 _year: int,
                 _logger: logging.Logger,
                 _scope: str = "both",
                 _stations_filter: Optional[str] = None,
                 _sessions_filter: Optional[str] = None,
                 ) -> None:
        """

        :param _year:
        :param _logger:
        :param _scope:
        :param _stations_filter:
        :param _sessions_filter:
        """

        # --- Assigning all parameters to local instance attributes ----------------------------------------------------
        self.year               = _year
        self.logger             = _logger
        self.scope              = _scope
        self.stations_filter    = _stations_filter
        self.sessions_filter    = _sessions_filter

        # --- Define and initialize some more instance attributes ------------------------------------------------------
        self.rows:              List[Row]   = []
        self.view_rows:         List[Row]   = []
        self.current_filter:    str         = ""
        self.selected:          int         = 0
        self.offset:            int         = 0
        self.has_colors:        bool        = False

        # --- Flag for showing/hiding removed sessions in the list
        self.show_removed:      bool        = True

        # --- Tokens to highlight in the stations column when filtering
        self.highlight_tokens:  List[str]   = []
    # this is the end of __init__() ------------------------------------------------------------------------------------



    def _show_help(self, stdscr) -> None:
        """
        Map status text to a curses color pair.

            curses.init_pair(1, curses.COLOR_YELLOW, -1)                # removed stations, intensives
            curses.init_pair(2, curses.COLOR_CYAN, -1)                  # header
            curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE) # help bar
            curses.init_pair(4, curses.COLOR_GREEN, -1)                 # released
            curses.init_pair(5, curses.COLOR_YELLOW, -1)                # processing
            curses.init_pair(6, curses.COLOR_MAGENTA, -1)               # cancelled
            curses.init_pair(7, curses.COLOR_WHITE, -1)                 # none
            curses.init_pair(8, curses.COLOR_CYAN, -1)                  # station highlight in filter
        """
        help_text = [
            "IVS Session Browser Help",
            "",
            "Navigation:",
            "  ↑/↓ : Move selection",
            "  PgUp/PgDn : Page up/down",
            "  Home/End : Jump to first/last",
            "  T : Jump to today's session",
            "  Enter : Open session in browser",
            "",
            "Filtering:",
            "  / : Enter filter (field:value, supports AND/OR)",
            "  F : Clear filters",
            "  R : Toggle show/hide removed stations",
            "",
            "Other:",
            "  q or Q : Quit",
            "  ? : Show this help",
            "",
            "Color legend:",
            "  Green    = Released",
            "  Yellow   = Processing / Waiting",
            "  Magenta  = Cancelled",
            "  White    = No status",
            "  Cyan     = Active filters",
            "",
            "",
            "Hit any key to close this help",
            "",
            "Well, maybe not ANY key, keys like Ctrl, Shift and Alt usually doesn't work ;-)"
        ]
        h, w    = stdscr.getmaxyx()
        width   = min(84, w - 4)
        height  = min(len(help_text) + 4, h - 4)
        y, x    = (h - height)//2, (w - width)//2
        win     = curses.newwin(height, width, y, x)
        win.box()

        for i, text in enumerate(help_text, start=1):
            attr = 0
            if i == 1:  # title
                attr = curses.A_UNDERLINE | curses.A_BOLD
            elif "Green" in text:
                attr = curses.color_pair(4)
            elif "Yellow" in text:
                attr = curses.color_pair(1)
            elif "Magenta" in text:
                attr = curses.color_pair(6)
            # elif "White" in text:
            #     attr = curses.color_pair(4)
            elif "Cyan" in text:
                attr = curses.color_pair(8)

            win.addnstr(i, 2, text, width - 4, attr)

        win.refresh()
        win.getch()
    # --- END OF _show_help() ------------------------------------------------------------------------------------------



    def _col_start_x(self, _col_idx: int) -> int:
        """
        Computes the x offset where column _col_idx starts in the printed line.
        Each column is printed left-padded to WIDTHS[c], joined by " | " (3 chars).

        :param _col_idx:

        :return:
        """

        sep = 3
        x   = 0
        for i in range(_col_idx):
            x += WIDTHS[i] + sep
        return x
    # --- END OF _col_start_x() ----------------------------------------------------------------------------------------



    def sort_by_start(self, rows: List[Row]) -> List[Row]:
        """
        Sorts the list given by rows chronologically

        :param rows:    holds the list to be sorted
        :return rows:   the sorted list
        """

        def keyfunc(row: Row):
            """
            Nested function to set the sort key
            """

            start_str = row[0][2]
            try:
                return datetime.strptime(start_str, "%Y-%m-%d %H:%M")
            except ValueError:
                return datetime.min
        # --- END OF keyfunc() -----------------------------------------------------------------------------------------
        return sorted(rows, key=keyfunc)
    # --- END OF sort_by_start() ---------------------------------------------------------------------------------------



    def _index_on_or_after_today(self, rows: List[Row]) -> int:
        """
        Return index of first row whose Start date is today or later.
        If all are before today, return last index; if empty, return 0.
        """

        if not rows:
            return 0
        today_d: date = datetime.now().date()
        for i, r in enumerate(rows):
            start_str = r[0][2]
            try:
                d = datetime.strptime(start_str, "%Y-%m-%d %H:%M").date()
            except ValueError:
                continue
            if d >= today_d:
                return i
        return len(rows) - 1
    # --- END OF index_on_or_after_today() -----------------------------------------------------------------------------



    def _status_color(self, _has_colors: bool, _status_text: str) -> int:
        """
        Map status text to a curses color pair.

        curses.init_pair(1, curses.COLOR_YELLOW, -1)                # removed stations, intensives
        curses.init_pair(2, curses.COLOR_CYAN, -1)                  # header
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE) # help bar
        curses.init_pair(4, curses.COLOR_GREEN, -1)                 # released
        curses.init_pair(5, curses.COLOR_YELLOW, -1)                # processing
        curses.init_pair(6, curses.COLOR_MAGENTA, -1)               # cancelled
        curses.init_pair(7, curses.COLOR_WHITE, -1)                 # none
        curses.init_pair(8, curses.COLOR_CYAN, -1)                  # station highlight in filter
        """

        if not _has_colors:
            return 0
        st = _status_text.strip().lower()
        if "released" in st:
            return curses.color_pair(4)
        if any(k in st for k in ("waiting on media", "ready for processing", "cleaning up", "processing session")):
            return curses.color_pair(5)

        # --- Handle both spellings...
        if "cancelled" in st or "canceled" in st:
            return curses.color_pair(6)
        if st == "":
            return curses.color_pair(7)
        return 0
    # --- END OF _status_color() ---------------------------------------------------------------------------------------



    def _addstr_clip(self, stdscr, y: int, x: int, text: str, attr: int = 0) -> None:
        """
        Writes a string to terminal, clipping if necessary

        :param stdscr:  Which screen to write to
        :param y:       y co-ordinate
        :param x:       x co-ordinate
        :param text:    What to write
        :param attr:    Text attributes

        :return:        None
        """

        max_y, max_x = stdscr.getmaxyx()
        if y >= max_y or x >= max_x:
            return
        stdscr.addstr(y, x, text[: max_x -x - 1], attr)
    # --- END OF _addstr_clip() ----------------------------------------------------------------------------------------



    def _draw_header(self, stdscr) -> None:
        """
        Draws up the header line on top of the terminal window using curses.
        Sets up the test to write, and the attributes for the text.
        Writes the header line and the dotted line underneath, at the top of the terminal

        :param stdscr:  Which screen to draw on

        :return:        None
        """

        header_attributes = curses.A_BOLD | (curses.color_pair(2) if self.has_colors else 0)
        self._addstr_clip(stdscr, 0, 0, HEADER_LINE, header_attributes)
        self._addstr_clip(stdscr, 1, 0, "-" * len(HEADER_LINE))
    # --- END OF _draw_header() ----------------------------------------------------------------------------------------



    def _draw_rows(self, stdscr) -> None:
        """
        Draws all the rows to terminal

        :param stdscr:  Which screen to draw on
        :return:        None
        """

        max_y, _    = stdscr.getmaxyx()
        view_height = max(1, max_y - 3)

        if self.selected < self.offset:
            self.offset = self.selected
        elif self.selected >= self.offset + view_height:
            self.offset = self.selected - view_height + 1

        # --- Let the user know if we have nothing to show
        if not self.view_rows:
            self._addstr_clip(stdscr, 2, 0, "No sessions found.")
            return

        # --- Draw each visible row to terminal
        for i in range(self.offset, min(len(self.view_rows), self.offset + view_height)):

            row_vals, _, meta = self.view_rows[i]

            # --- Copy, so we can override Stations column safely
            vals = list(row_vals)

            # --- If the user has chosen to hide removed stations, render only active in column 5
            # --- Column 5 is best accessed as index = FIELD_INDEX.get("stations", -1)
            if not self.show_removed:
                active_only = meta.get("active", "")
                field_index: int = FIELD_INDEX.get("stations", -1)
                vals[field_index] = f"{active_only:<{WIDTHS[field_index]}}"

            # --- Construct full lines from parts
            parts       = [f"{val:<{WIDTHS[c]}}" for c, val in enumerate(vals)]
            full_line   = " | ".join(parts)
            y           = i - self.offset + 2
            row_attr    = curses.A_REVERSE if i == self.selected else 0

            row_color = self._status_color(self.has_colors, vals[FIELD_INDEX.get("status", -1)])
            self._addstr_clip(stdscr, y, 0, full_line, row_attr | row_color)

            # [REMOVED] --- Highlight "[...]" only if we are showing removed stations, after the active ones
            # --- This has changed: as a side effect, intensives that are also marked with [], will be
            # --- colored by the same color as removed stations (becasue of the []. This is for convenience; in later
            # --- versions intensives and removed should have separate colors.
            # if self.has_colors and self.show_removed and vals[FIELD_INDEX.get("stations", -1)]:
            if self.has_colors and vals[FIELD_INDEX.get("stations", -1)]:
                lbr = full_line.find("[")
                if lbr != -1:
                    rbr = full_line.find("]", lbr + 1)
                    if rbr != -1 and rbr > lbr:
                        self._addstr_clip(stdscr, y, lbr, full_line[lbr:rbr + 1], row_attr | curses.color_pair(1))

            # --- Station token highlighting (from stations:* filter)
            if vals[FIELD_INDEX.get("stations", -1)] and self.highlight_tokens:
                # --- Padded field text as printed
                stations_text = vals[FIELD_INDEX.get("stations", -1)]

                # --- "stations" field index
                col_x = self._col_start_x(FIELD_INDEX.get("stations", -1))

                # --- Fallback without colors: underline+bold (shows even on selected/reversed rows)
                hl_attr = (curses.color_pair(8) | curses.A_BOLD) if self.has_colors else (
                        curses.A_BOLD | curses.A_UNDERLINE)
                for tok in self.highlight_tokens:
                    start = 0
                    while True:
                        j = stations_text.find(tok, start)
                        if j == -1:
                            break
                        self._addstr_clip(stdscr, y, col_x + j, tok, row_attr | hl_attr)
                        start = j + len(tok)

        # --- END OF for i in range ------------------------------------------------------------------------------------
    # --- END OF _draw_rows() ------------------------------------------------------------------------------------------



    def _draw_helpbar(self, stdscr) -> None:
        """
        Draws up the help at the bottom of the terminal

        :param stdscr:  Where to write
        :return:        None
        """
        max_y, max_x = stdscr.getmaxyx()
        help_text = "↑↓-PgUp/PgDn-Home/End:Move Enter:Open /:Filter F:Clear filters ?:Help R:Hide/show removed q/Q:Quit"
        right = f"row {min(self.selected + 1, len(self.view_rows))}/{len(self.view_rows)}"
        bar = (help_text + (f" Filter: {self.current_filter}" if self.current_filter else "") + "  " + right)[
            : max_x - 1]
        bar_attr = curses.color_pair(3) if self.has_colors else curses.A_REVERSE
        self._addstr_clip(stdscr, max_y - 1, 0, bar, bar_attr)
    # --- END OF _draw_helpbar() ---------------------------------------------------------------------------------------



    def _navigate(self, key: int, stdscr) -> None:
        """
        Wrapper for main loop, _curses_main, to handle navigation in the session list.
        The idea is to keep a neater _curse_main.
        This wrapper handles navigation keys: up/down arrows, page up/down, home/end and the enter key
        to open the selected session in browser.

        :param key: The curse_KEY_ to handle

        :return:    None
        """

        match key:
            case curses.KEY_UP if self.selected > 0:
                self.selected -= 1
            case curses.KEY_DOWN if self.selected < len(self.view_rows) - 1:
                self.selected += 1
            case curses.KEY_NPAGE:
                max_y, _ = stdscr.getmaxyx()
                page = max(1, max_y - 3)
                self.selected = min(self.selected + page, len(self.view_rows) - 1)
            case curses.KEY_PPAGE:
                max_y, _ = stdscr.getmaxyx()
                page = max(1, max_y - 3)
                self.selected = max(self.selected - page, 0)
            case curses.KEY_HOME:
                self.selected = 0;
            case curses.KEY_END:
                self.selected = max(0, len(self.view_rows) - 1)
            case 10 | 13 | curses.KEY_ENTER:
                if self.view_rows:
                    _, url, _ = self.view_rows[self.selected]
                    if url:
                        webbrowser.open(url)
            case _:
                pass
    # --- END OF _navigate() -------------------------------------------------------------------------------------------



    def _jump_to_today(self) -> None:
        """
        Small helper to jump to today's date. If there are several sessions for a given date, this function stops
        at the first one, such that the rest are visible below the selected.

        If today's date is not in the list, it jumps to the next date.

        :return:    None
        """

        idx = self._index_on_or_after_today(self.view_rows)
        self.selected = idx
        self.offset = idx
    # --- END OF _jump_to_today() --------------------------------------------------------------------------------------



    def _get_input(self, stdscr, prompt: str, initial: str = "") -> str:
        """
        Get editable input from the user with an initial value pre-filled.

        :param stdscr:  Where to print
        :param prompt:  Prompt shown before the text
        :param initial: Initial text to prefill (e.g., current filter)

        :return:        The entered text
        """
        curses.curs_set(1)
        curses.noecho()

        # --- Important for KEY_* codes
        stdscr.keypad(True)

        max_y, max_x = stdscr.getmaxyx()

        # --- EDITABLE STATE

        # --- Prefill with current filter
        buffer: list[str] = list(initial)

        # --- Cursor index inside buffer
        cursor: int = len(buffer)

        # --- Horizontal scroll of the *text* (not including prompt)
        scroll: int = 0

        def _recalc_scroll():
            """Keep the cursor visible by adjusting horizontal scroll."""
            nonlocal scroll

            # --- How many cells we can draw
            visible_width = max_x - 1

            # --- Space available for the text after the prompt:
            text_space = visible_width - len(prompt)
            if text_space < 5:
                # --- If the prompt is huge, fallback to at least a few chars of input area
                text_space = 5

            # --- If cursor goes left of the window, scroll left
            if cursor < scroll:
                scroll = cursor
            # --- If cursor goes right of the window, scroll right
            elif cursor > scroll + text_space - 1:
                scroll = cursor - (text_space - 1)
            # --- Clamp scroll
            if scroll < 0:
                scroll = 0

        while True:
            _recalc_scroll()

            # --- Compose visible line
            text = "".join(buffer)
            visible_width = max_x - 1
            text_space = visible_width - len(prompt)
            if text_space < 5:
                text_space = 5

            # --- Take the slice of text that should be visible
            visible_text = text[scroll:scroll + text_space]
            line = (prompt + visible_text)[:visible_width]

            # --- Clear last line and draw prompt + visible text inverted
            stdscr.move(max_y - 1, 0)
            stdscr.clrtoeol()

            # [REMOVED]stdscr.addnstr(max_y - 1, 0, line, visible_width, curses.A_REVERSE)
            # --- Added filter color to filter input field
            stdscr.addnstr(max_y - 1, 0, line, visible_width, curses.A_REVERSE|curses.color_pair(8))

            # --- Compute on-screen cursor column
            cursor_col = len(prompt) + (cursor - scroll)
            cursor_col = max(0, min(cursor_col, visible_width - 1))
            stdscr.move(max_y - 1, cursor_col)

            ch = stdscr.getch()
            match ch:
                case 10 | 13 | curses.KEY_ENTER:
                    break

                case 27:
                    buffer = []
                    break

                case 8 | 127 | curses.KEY_BACKSPACE:
                    if cursor > 0:
                        cursor -= 1
                        buffer.pop(cursor)

                case curses.KEY_DC:
                    if cursor < len(buffer):
                        buffer.pop(cursor)

                case curses.KEY_LEFT:
                    if cursor > 0:
                        cursor -= 1
                case curses.KEY_RIGHT:
                    if cursor < len(buffer):
                        cursor += 1

                case curses.KEY_HOME:
                    cursor = 0
                case curses.KEY_END:
                    cursor = len(buffer)

                # Printable ASCII
                case c if 32 <= c <= 126:
                    buffer.insert(cursor, chr(c))
                    cursor += 1

                # Ignore everything else
                case _:
                    pass

        curses.curs_set(0)
        curses.echo()
        return "".join(buffer).strip()
    # --- END OF _get_input() ------------------------------------------------------------------------------------------



    def _split_tokens(self, val: str) -> List[str]:
        """

        :return:
        """
        return [t for t in re.split(r"[ ,+|]+", val) if t]
    # --- END OF _split_tokens() ---------------------------------------------------------------------------------------



    def _match_stations(self, hay: str, expr: str) -> bool:
        """

        :param expr:
        :return:
        """
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
    # --- END OF _match_stations() -------------------------------------------------------------------------------------



    def _match_text_ci(self, hay: str, expr: str) -> bool:
        """
        Case-insensitive matcher for NON-station fields.
        Supports '|' (OR) and '&' (AND) like _match_stations(),
        but comparisons are done case-insensitively.
        """

        text = expr.strip()
        if not text:
            return True

        H = hay.lower()

        def norm(s: str) -> str:
            return s.lower()

        has_or = '|' in text
        has_and = '&' in text
        if has_or or has_and:
            or_parts = [p.strip() for p in re.split(r"\s*\|{1,2}\s*", text) if p.strip()]
            for part in or_parts:
                and_chunks = [c.strip() for c in re.split(r"\s*&{1,2}\s*", part) if c.strip()]
                and_tokens: List[str] = []
                for chunk in and_chunks:
                    and_tokens.extend([t for t in re.split(r"[ ,+]+", chunk) if t])
                if and_tokens and all(norm(tok) in H for tok in and_tokens):
                    return True
                if not and_tokens and part and norm(part) in H:
                    return True1

            return False

        # --- No explicit | or &: treat split tokens as OR
        tokens = [t for t in re.split(r"[ ,+]+", text) if t]
        return any(norm(tok) in H for tok in tokens)
    # --- END OF _match_text_ci() --------------------------------------------------------------------------------------



    def _apply_filter(self, _query: str) -> List[Row]:
        """
        Applies filter from user input to the session list

        :param _query:  Filter string, for instance [stations: "Ns|Nn;type:IVS-R1]

        :return:    The session list with filters applied
        """

        if not _query:
            return self.rows

        clauses = [c.strip() for c in _query.split(';') if c.strip()]

        if not clauses:
            return self.rows

        return_value: List[Row] = []

        for r in self.rows:
            if all(self._clause_match(r, c) for c in clauses):
                return_value.append(r)

        return return_value
    # --- END OF _apply_filter() ---------------------------------------------------------------------------------------



    def _clause_match(self, _row: Row, _clause: str) -> bool:
        values, _, meta = _row

        if ':' in _clause:
            field, value = [p.strip() for p in _clause.split(':', 1)]

            fld = field.lower()

            idx = FIELD_INDEX.get(fld)
            if fld in ("stations", "stations_active", "stations-active"):
                return self._match_stations(meta["active"], value)
            if fld in ("stations_removed", "stations-removed"):
                return self._match_stations(meta["removed"], value)
            if fld in ("stations_all", "stations-all"):
                return self._match_stations(meta["active"] + " " + meta["removed"], value)
            if idx is None:
                return False

            hay = values[idx]

            # --- Non-station fields: case-insensitive, support | and &,
            # --- default to OR across tokens when neither is present.
            return self._match_text_ci(hay, value)

        return any(_clause in col for col in values)
    # --- END OF _clause_match() ---------------------------------------------------------------------------------------



    def _extract_station_tokens(self, _query: str) -> List[str]:
        """
        Highlight helper, pulls station codes from any station-related clause in the current filter.

        Whatever the user types, is passed as '_query', for instance '/ stations: "Ns|Nn"'

        :param _query:  The query passed by the caller, from which to extract station names (Nn, Ns, etc.)

        :return:        A list of strings
        """

        # --- If we're passed an empty query, return with nothing
        if not _query:
            return []

        # --- Empty list of strings
        tokens: List[str] = []

        # --- Splits _query by the ';', and
        clauses = [c.strip() for c in _query.split(';') if c.strip()]

        # --- Strips away any whitespace, storing what's left in 'clauses'
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

        # --- Deduplicate; longer-first to avoid partial-overwrite visuals (e.g., 'Ny' vs 'Nya')
        return sorted(set(tokens), key=lambda s: (-len(s), s))
    # --- END OF _extract_station_tokens() ---------------------------------------------------------------------------------------



    def _clear_filters(self) -> None:
        """
        Clears all active filters

        :return: None
        """
        self.current_filter = ""
        self.view_rows = self.rows
        self.highlight_tokens = []
        idx = self._index_on_or_after_today(self.view_rows)
        self.selected = idx
        self.offset = idx
    # --- END OF _clear_filters() ---------------------------------------------------------------------------------------



    def _curses_main(self, stdscr) -> None:
        """
        The scripts main loop.

        :param stdscr:  Which screen to write to

        :return: None
        """

        # --- Hide the cursor in the terminal
        curses.curs_set(0)

        # --- Clear the terminal window
        stdscr.clear()

        # --- Set up the colors, if any are available
        self.has_colors = curses.has_colors()
        if self.has_colors:
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_YELLOW, -1)                # removed stations, intensives
            curses.init_pair(2, curses.COLOR_CYAN, -1)                  # header
            curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE) # help bar
            curses.init_pair(4, curses.COLOR_GREEN, -1)                 # released
            curses.init_pair(5, curses.COLOR_YELLOW, -1)                # processing
            curses.init_pair(6, curses.COLOR_MAGENTA, -1)               # cancelled
            curses.init_pair(7, curses.COLOR_WHITE, -1)                 # none
            curses.init_pair(8, curses.COLOR_CYAN, -1)                  # station highlight in filter

        # --- Apply filters from command line, if any
        if self.stations_filter and not self.sessions_filter:
            # --- The difference between these two lines, made a big difference in the output from my filter logic!
            # --- Not having the "stations: " in front of my filter logic, made the list empty. Note to self!
            self.current_filter = "stations: " + self.stations_filter

        elif self.sessions_filter and not self.stations_filter:
            self.current_filter = "code: " + self.sessions_filter

        elif self.stations_filter and self.sessions_filter:
            self.current_filter = "stations: " + self.stations_filter + ";code: " + self.sessions_filter

        self.view_rows = self._apply_filter(self.current_filter)

        # --- Start the main loop
        quit = False
        while not quit:
            stdscr.clear()
            self._draw_header(stdscr)
            self._draw_rows(stdscr)
            self._draw_helpbar(stdscr)

            ch = stdscr.getch()
            match ch:

                # --- Handles all navigation keys, and enter
                case key if key in NAVIGATION_KEYS: self._navigate(ch, stdscr)

                # --- Jump to today's date (or the next if today is not in list)
                case c if c == ord('T'): self._jump_to_today()

                # --- Apply user filter
                case c if c == ord('/'):

                    prefill = self.current_filter or ""
                    q       = self._get_input(stdscr, "/ ", initial = prefill)

                    self.current_filter = q;
                    self.view_rows      = self._apply_filter(q)

                    self.highlight_tokens   = self._extract_station_tokens(self.current_filter)

                    idx             = self._index_on_or_after_today(self.view_rows)
                    self.selected   = idx
                    self.offset     = idx

                # --- Clear active filters
                case c if c == (ord('F')):  self._clear_filters()

                # --- Hide/show removed stations
                case c if c == (ord('R')):  self.show_removed = not self.show_removed

                # --- Show help
                case c if c == (ord('?')):   self._show_help(stdscr)

                # --- Quit the script and return to terminal
                case c if c in (ord('q'), ord('Q')):    quit = True

                # --- Any other key we'll just pass
                case _:                                 pass
            # --- END OF match ch --------------------------------------------------------------------------------------
        # --- END OF while not quit ------------------------------------------------------------------------------------
    # --- END OF _curses_main() ----------------------------------------------------------------------------------------



    def run(self) -> None:
        """
        run() starts the show.
        It first gets the data from web, sort them by date, updates indexing, then calls _curses_main

        :return: None
        """

        # --- Get data from web, and store in 'html', using functionality from 'URLHelper' class
        # --- We must differentiate between master and intensives, because we want to mark the intensives in the list

        # --- Fetch all items from web, based on year, scope, stations filter and sessions filter
        url_helper: URLHelper   = URLHelper(self.logger,
                                            self.year,
                                            self.scope,
                                            self.stations_filter,
                                            self.sessions_filter)
        self.rows  = url_helper.fetch_all_urls()

        # --- Items are mixed by default, since we've read from both master and intensives, potentially, thus a sort
        # --- in chronological order is needed.
        self.rows  = self.sort_by_start(self.rows)

        # --- Putting all rows into list form
        self.view_rows = list(self.rows)

        # --- Setting indexing to today's date
        idx             = self._index_on_or_after_today(self.view_rows)
        self.selected   = idx
        self.offset     = idx

        # --- Using curses to call on the main loop, self._curses.main()
        curses.wrapper(self._curses_main)
    # --- END OF run() -------------------------------------------------------------------------------------------------
# --- END OF class SessionBrowser definition ---------------------------------------------------------------------------



def main() -> None:
    """
    main()

    :return:    None
    """

    # --- Define an argument parser for the user's command line args
    arg_parser = argparse.ArgumentParser(description     = ARGUMENT_DESCRIPTION,
                                         epilog          = ARGUMENT_EPILOG,
                                         formatter_class = ARGUMENT_FORMATTER_CLASS)

    arg_parser.add_argument("--year",
                            type    = int,
                            default = datetime.now().year,
                            help    = "Year (default: current year)")

    arg_parser.add_argument("--scope",
                            choices = ("master", "intensive", "both"),
                            default = "both",
                            help    = "Which schedules to include (default: both)")
    arg_parser.add_argument("--stations",
                            type    = str,
                            help    ="Initial stations filter")
    # arg_parser.add_argument("--sessions",
    #                         type    = str,
    #                         help    = "Initial filter for sessions:")

    args = arg_parser.parse_args()

    from log_setup import log_filename
    logger = setup_logger(filename = log_filename)
    # logger.info("Script started.")

    SessionBrowser(_year                = args.year,
                   _logger              = logger,
                   _scope               = args.scope,
                   _stations_filter     = args.stations,
                   # _sessions_filter     = args.sessions,
                   ).run()
    # logger.info(f"Script ended.")
# --- END OF main() ----------------------------------------------------------------------------------------------------



if __name__ == "__main__":
    main()
