# flake8: noqa
# isort: skip_file
"""
Filename:       sessions_browser.py
Author:         jole
Created:        15.09.2025

Description:    Holds class definitions for SessionBrowser along with attributes and methods.
"""

# ──────────────────────────────────────────────────────────────────────────────
# Import section
# ──────────────────────────────────────────────────────────────────────────────
from __future__ import annotations
from bs4        import BeautifulSoup

import curses
import os
import time
import webbrowser
from urllib.parse import urlsplit, urlunsplit
from .pdf_export import write_ansi_lines_pdf

# Project defined imports
from .                          import defs as D

from .fetch_sessions    import FetchSessions
from .tui               import Tui
from .tui_state         import UIState, TUITheme
from .ivstypes          import PageData
from .operators         import load_operator_assignments, load_operator_bindings, load_operator_colors, save_operator_assignments
# ─── END OF Import section ────────────────────────────────────────────────────



class SessionsBrowser:
    """
    Class representing the IVS Sessions Browser object.
    Defined in sessions_browser.py.

    """

    PDF_STATUS_MESSAGE_DELAY_SECONDS = 1.9

    def __init__(self, _year: int | list[int], _scope: str, _mirrors: bool = False, _filters: str | None = None) -> None:
        """
        Docstring for __init__

        :param _year:       Which year(s) to fetch sessions for (e.g., 2025 or [2022, 2023])
        :type _year:        int | list[int]
        :param _scope:      Which schedules to include (master, intensive, both)
        :type _scope:       str
        :param _mirrors:    Whether to check mirror websites for the latest update
                            and use the most recent one
        :type _mirrors:     bool
        :param _filters:    Initial filters (see help for syntax)
        :type _filters:     str | None
        """

        # Store user input parameters
        if isinstance(_year, int):
            self.years = [_year]
        else:
            self.years = list(dict.fromkeys(int(y) for y in _year))
        self.year       = self.years[0]
        self.scope      = _scope
        self.filters    = _filters

        # Build the candidate URL list for the requested scope/mirrors
        self.url_list = self._urls_for_scope(_mirrors)

        # Creating attribute to store the raw HTML data fetched from the URL, in
        # case the --mirrors flag is set, the most recent one is stored here.
        self.list_html_data_page: list[PageData] = []

        # ──────────────────────────────────────────────────────────────────────
        # Fetch data from web
        # ──────────────────────────────────────────────────────────────────────
        # Create FetchSessions instance to download HTML data from the URLs
        fs: FetchSessions = FetchSessions(_mirrors)

        # self.list_html_data_page contains the fetched HTML data for both master
        # and intensive schedules
        self.list_html_data_page = fs.fetch_html_from_urls(self.url_list)
        # ─── END OF Fetch data from web ───────────────────────────────────────

        # ──────────────────────────────────────────────────────────────────────
        # Format and render session data
        # ──────────────────────────────────────────────────────────────────────
        # Create SessionsTuiFormatter instance to format the parsed HTML
        self.formatter = Tui()

        # Scan fetched HTML data and produce formatted lines
        for page_data in self.list_html_data_page:
            soup    = BeautifulSoup(page_data.html, "html.parser")
            url     = page_data.url

            # Determine if this is a master or an intensive session, and set
            # the is_intensive flag accordingly
            h1          = soup.find('h1', class_='title')
            title_str   = h1.get_text(strip = True) if h1 else None
            if title_str and "intensive" in title_str.lower():
                is_intensive = True
            else:
                is_intensive = False

            # Build the formatted session list from the downloaded HTML soup
            self.formatter.build_session_list(_soup              = soup,
                                 _num_of_headers    = len(D.HEADERS) - 1,  # <-- Op is local-only, not on the website
                                 _is_intensive      = is_intensive,
                                 _filters           = self.filters,
                                 _url               = url
                                 )

        # Applying filters and sorting to the full list of sessions, which is
        # stored in self.formatter.full_list. The filtered and sorted list is
        # stored in self.view_rows, which is what we render in the TUI.
        self.view_rows = self.formatter.apply_filters_and_sorting(_query        = self.filters,
                                                                  _show_removed = True,
                                                                  _sort_key     = "start",
                                                                  _ascending    = True)

        # Extract station tokens for highlighting
        self.highlight_tokens = self.formatter.filter_sort.extract_station_tokens(self.filters or "")

        # After building the session list(s), recompute header widths to fit content
        self.formatter.recompute_header_widths()

        # Create the TUIState and TUITheme instances to hold the state of the
        # UI, such as selected session, applied filters, etc., and the theme (colors, styles, etc.)
        self.state              = UIState()
        self.theme: TUITheme    = None  # <- initialized in self._curses_main()

        # self.operators = load_operators()
        self.operator_bindings      = load_operator_bindings()
        self.operator_assignments   = load_operator_assignments()
        self.operator_colors        = load_operator_colors()
        # Read default PDF columns from user-editable file in CONFIG_DIR
        try:
            pdf_columns_path = D.CONFIG_DIR / "pdf_columns"
            if not pdf_columns_path.exists():
                try:
                    pdf_columns_path.write_text("ALL", encoding="utf-8")
                except Exception:
                    pass

            raw = ""
            try:
                raw = (pdf_columns_path.read_text(encoding="utf-8") or "").strip()
            except Exception:
                raw = ""

            if not raw:
                self.pdf_default_columns = "ALL"
            else:
                raw_up = raw.strip().upper()
                if raw_up == "ALL":
                    self.pdf_default_columns = "ALL"
                else:
                    cols = [c.strip().upper() for c in raw_up.split("|") if c.strip()]
                    invalid = [c for c in cols if c not in D.PRETTY_PRINT_ALLOWED_COLUMNS]
                    if invalid:
                        self.pdf_default_columns = "ALL"
                    else:
                        # store as list for later use
                        self.pdf_default_columns = cols
        except Exception:
            self.pdf_default_columns = "ALL"
        # ─── END OF Format and render session data ────────────────────────────
    # ─── END OF __init__() ────────────────────────────────────────────────────



    def _urls_for_scope(self, _mirrors: bool) -> list[str]:
        """
        Defined in sessions_browser.py.

        _urls_for_scope() builds the list of urls to download session data from,
        based on the year(s) and scope provided by the user. The list contains both
        primary site, and any mirrors

        Primary and mirror sites are defined in IVSCC_BASE_URLS in defs.py.

        :return: list of string, containing the urls from which we read session data
        and compare last updated timestamps if __mirrors flag is set. We like to
        use the most recently updated data available.
        """

        base_url_list   : list[str] = D.IVSCC_BASE_URLS
        retval          : list[str] = []
        quiet = os.getenv("IVS_SESSIONS_QUIET") == "1"

        if not _mirrors:
            base_url_list = [base_url_list[0]]
            if not quiet:
                print(f"► Using only primary IVSCC site for session data ({D.IVSCC_BASE_URLS[0]})")
        else:
            if not quiet:
                print("►► Reviewing primary and mirror IVSCC sites for the most recently updated session data.")

        if self.scope == "master":
            for base_url in base_url_list:
                for year in self.years:
                    retval.append(f"{base_url}/{year}")

        elif self.scope == "intensive":
            for base_url in base_url_list:
                for year in self.years:
                    retval.append(f"{base_url}/intensive/{year}")

        elif self.scope == "both":
            for base_url in base_url_list:
                for year in self.years:
                    retval.append(f"{base_url}/{year}")
                    retval.append(f"{base_url}/intensive/{year}")

        return retval
    # ─── END OF _urls_for_scope() ─────────────────────────────────────────────



    def render_sessions_list(self, pretty_print: str | list[str] = "ALL") -> list[str]:
        """
        Defined in sessions_browser.py.

        This method is responsible for rendering the session list as formatted
        text output with ANSI colors, suitable for printing to console or web display.

        Returns formatted lines matching TUI appearance:
        - Operator colors applied to each row
        - Proper column widths and padding
        - [I] markers for intensive sessions
        - Header and separator lines

        :return: List of formatted strings with ANSI color codes
        :rtype: list[str]
        """

        # ANSI color codes
        ANSI_COLORS = {
            "white"     : "\033[97m",
            "green"     : "\033[92m",
            "yellow"    : "\033[93m",
            "cyan"      : "\033[96m",
            "magenta"   : "\033[95m",
            "blue"      : "\033[94m",
            "red"       : "\033[91m",
            "black"     : "\033[30m",
        }
        ANSI_RESET = "\033[0m"
        ANSI_BOLD = "\033[1m"

        if pretty_print == "ALL":
            selected_indices = list(range(len(D.HEADERS)))
        else:
            selected_indices = [
                D.FIELD_INDEX[D.PRETTY_PRINT_COLUMN_TO_FIELD[col_name]]
                for col_name in pretty_print
                if col_name in D.PRETTY_PRINT_COLUMN_TO_FIELD
            ]

        if not selected_indices:
            selected_indices = list(range(len(D.HEADERS)))

        # Map operator labels to colors
        operator_label_to_color = {}
        for op_key, op_label in self.operator_bindings.items():
            if op_label and op_key in self.operator_colors:
                color_name = self.operator_colors[op_key].lower()
                operator_label_to_color[op_label] = ANSI_COLORS.get(color_name, "")

        # Build output lines
        lines = []

        # Header
        header = " | ".join([f"{D.HEADERS[i][0]:<{D.HEADERS[i][1]}}" for i in selected_indices])

        lines.append(f"{ANSI_BOLD}{ANSI_COLORS['cyan']}{header}{ANSI_RESET}")
        lines.append("─" * len(header))

        # Data rows
        for values, _url, meta in self.view_rows:
            # Get operator color
            op_label = values[D.FIELD_INDEX.get("op", 0)].strip()
            color_code = operator_label_to_color.get(op_label, "")

            # Build formatted parts with proper widths
            parts = []
            type_idx = D.FIELD_INDEX.get("type", 1)
            for c in selected_indices:
                val = values[c]
                w = D.WIDTHS[c]
                if c == type_idx and meta.get("intensive"):
                    # Reserve 3 chars for "[I]" at right edge
                    base_w = max(0, w - 3)
                    parts.append(f"{val:<{base_w}}[I]")
                else:
                    parts.append(f"{val:<{w}}")

            # Build line with white separators and colored cells
            line_parts = []
            for i, part in enumerate(parts):
                if color_code:
                    line_parts.append(f"{color_code}{part}{ANSI_RESET}")
                else:
                    line_parts.append(part)

            # Join with white pipe separators
            full_line = f"{ANSI_COLORS['white']} | {ANSI_RESET}".join(line_parts)
            lines.append(full_line)

        return lines
    # ─── END OF render_sessions_list() ────────────────────────────────────────



    def _curses_main(self, _stdscr) -> None:
        """
        Defined in sessions_browser.py       

        This method is the main loop of the TUI, responsible for rendering the
        interface, handling user input, and updating the display accordingly.
        
        It is called by curses.wrapper() in the run() method, which sets up the
        curses environment and passes the standard screen (_stdscr) to this        
        """
    
        # Use class, not instance
        self.theme = TUITheme.init_theme(self.operator_colors)

        # Set global has_colors in TUIState instance
        self.state.has_colors = curses.has_colors()

        _stdscr.keypad(True)
        # Hide the cursor in the TUI
        curses.curs_set(0)  
        curses.use_default_colors()
        if self.state.has_colors:
            # Initialize color support
            curses.start_color()
        _stdscr.clear()

        # Jump to today's session on startup
        idx = self.formatter.filter_sort.index_on_or_after_today(self.view_rows)
        if idx != -1:
            # self.state.selected = idx
            self.state.selected = self.state.offset = idx

        # Start the main loop
        quit: bool = False
        while not quit:
            # Determine the view height of the current terminal screen
            max_y, _                = _stdscr.getmaxyx()
            self.state.view_height  = max(1, max_y - 3)

            self.formatter.clear_screen(_stdscr)
            self.formatter.draw_header(_stdscr, self.theme, self.state)

            # We pass a filtered list to draw_rows. draw_rows stays "dumb", meaning it just prints whatever
            # we send it.
            self.formatter.draw_rows(_stdscr, self.view_rows, self.highlight_tokens, self.theme, self.state)

            # Draw a help-bar at the bottom of the screen
            self.formatter.draw_helpbar(_stdscr, self.view_rows, self.filters, self.theme, self.state)

            # Get and parse user input
            key = _stdscr.getch()
            match key:
                # Navigation keys and Enter
                case key if key in (curses.KEY_UP, curses.KEY_DOWN, curses.KEY_PPAGE, curses.KEY_NPAGE,
                                   curses.KEY_HOME, curses.KEY_END, 10, 13, curses.KEY_ENTER):
                    self._navigate(key, _stdscr)

                # Operator assignment: digit 0-5
                case c if ord('0') <= c <= ord('5'):
                    if self.view_rows and 0 <= self.state.selected < len(self.view_rows):
                        digit = chr(c)
                        operator_label = self.operator_bindings.get(digit, "")

                        values, _, _ = self.view_rows[self.state.selected]
                        code_idx = D.FIELD_INDEX.get("code", 2)
                        session_code = values[code_idx] if len(values) > code_idx else ""

                        if session_code:
                            self._apply_operator_assignment(session_code, operator_label)
                            save_operator_assignments(self.operator_assignments)

                            # Advance selection by one unless we're already on the last row
                            if self.state.selected < len(self.view_rows) - 1:
                                self._navigate(curses.KEY_DOWN, _stdscr)

                # Jump to today's date
                case c if c == ord('T'):
                    idx = self.formatter.filter_sort.index_on_or_after_today(self.view_rows)
                    self.state.selected = self.state.offset = idx

                # Apply user filter
                case c if c == ord('/'):
                    # Prefill prompt with current filter
                    prefill = self.filters or ""

                    # Get new filter from user
                    new_filter = self._get_input(_stdscr, self.theme, "/ ", _initial=prefill)

                    self.filters = new_filter
                    self.view_rows = self.formatter.apply_filters_and_sorting(
                        _query=self.filters,
                        _show_removed=self.state.show_removed,
                        _sort_key="start",
                        _ascending=True
                    )

                    # Jump to today
                    idx = self.formatter.filter_sort.index_on_or_after_today(self.view_rows)
                    self.state.selected = self.state.offset = idx

                    # Highlight stations when filtered
                    self.highlight_tokens = self.formatter.filter_sort.extract_station_tokens(self.filters)

                # Clear active filters
                case c if c == ord('C'):
                    self._clear_filters()
                    # Jump to today after clearing
                    idx = self.formatter.filter_sort.index_on_or_after_today(self.view_rows)
                    self.state.selected = self.state.offset = idx

                # Hide/show removed stations
                # case c if c == ord('R'):
                    # self.state.show_removed = not self.state.show_removed
                    # self.view_rows = self.formatter.apply_filters_and_sorting(
                        # _query=self.filters,
                        # _show_removed=self.state.show_removed,
                        # _sort_key="start",
                        # _ascending=True
                    # )

                # Save to PDF
                case c if c == ord('P'):
                    # Prompt user for which columns to include (ALL or
                    # pipe-separated list)
                    prompt = "PDF columns (ALL or pipe-separated, e.g. OP|TYPE|STATIONS): "
                    # Use configured default (string 'ALL' or list of cols)
                    if isinstance(getattr(self, 'pdf_default_columns', None), list):
                        prefill = "|".join(self.pdf_default_columns)
                    else:
                        prefill = str(getattr(self, 'pdf_default_columns', 'ALL'))
                    cols_input = self._get_input(_stdscr, self.theme, prompt, _initial=prefill)
                    if not cols_input:
                        cols_input = "ALL"

                    # Parse and validate input
                    pretty: str | list[str]
                    text = cols_input.strip().upper()
                    if text == "ALL":
                        pretty = "ALL"
                    else:
                        cols = [col.strip().upper() for col in text.split("|") if col.strip()]
                        invalid = [col for col in cols if col not in D.PRETTY_PRINT_ALLOWED_COLUMNS]
                        if invalid:
                            max_y, max_x = _stdscr.getmaxyx()
                            err = f"Unknown column(s): {','.join(invalid)}"
                            attr = self.theme.help_bar if self.state.has_colors else 0
                            self.formatter._addstr_clip(_stdscr, max_y - 2, 0, err[: max_x - 1], attr)
                            _stdscr.refresh()
                            time.sleep(self.PDF_STATUS_MESSAGE_DELAY_SECONDS)
                            break
                        # De-duplicate while preserving order
                        pretty = list(dict.fromkeys(cols))

                    try:
                        max_y, max_x = _stdscr.getmaxyx()
                        filename = f"sessions-{time.strftime('%Y%m%d-%H%M%S')}.pdf"
                        out_path = os.path.join(os.getcwd(), filename)

                        # Build ANSI-coloured lines and write PDF
                        lines = self.render_sessions_list(pretty)
                        with open(out_path, "wb") as f:
                            write_ansi_lines_pdf(lines, f)

                        # Show short confirmation message above helpbar
                        msg = f"Saved PDF: {out_path}"
                        attr = self.theme.help_bar if self.state.has_colors else 0
                        self.formatter._addstr_clip(_stdscr, max_y - 2, 0, msg[: max_x - 1], attr)
                        _stdscr.refresh()
                        time.sleep(self.PDF_STATUS_MESSAGE_DELAY_SECONDS)

                        # Try to open the saved file in the system viewer
                        try:
                            webbrowser.open(f"file://{out_path}")
                        except Exception:
                            pass
                    except Exception as e:
                        max_y, max_x = _stdscr.getmaxyx()
                        err = f"Error saving PDF: {e}"
                        attr = self.theme.help_bar if self.state.has_colors else 0
                        self.formatter._addstr_clip(_stdscr, max_y - 2, 0, err[: max_x - 1], attr)
                        _stdscr.refresh()
                        time.sleep(self.PDF_STATUS_MESSAGE_DELAY_SECONDS)

                # Show help
                case c if c == ord('?'):
                    self.formatter.show_help(_stdscr, self.theme)

                # Quit the script and return to terminal
                case c if c in (ord('q'), ord('Q')):
                    quit = True

                # Any other key we'll just pass
                case _:
                    pass
            # ───END OF match key ─────────────────────────────────────────────
        # ─── END OF while not quit ────────────────────────────────────────────
    # ─── END OF _curses_main() ────────────────────────────────────────────────



    def _navigate(self, _key: int, _stdscr) -> None:
        """
        Defined in sessions_browser.py.

        Handle navigation keys: up/down arrows, page up/down, home/end and the enter key
        to open the selected session in browser.

        :param _key: The curses.KEY_xxx to handle
        :param _stdscr: The screen to write to (curses)
        :return: None
        """
        match _key:
            case curses.KEY_UP if self.state.selected > 0:
                self.state.selected -= 1
            case curses.KEY_DOWN if self.state.selected < len(self.view_rows) - 1:
                self.state.selected += 1
            case curses.KEY_NPAGE:
                max_y, _ = _stdscr.getmaxyx()
                page = max(1, max_y - 3)
                self.state.selected = min(self.state.selected + page, len(self.view_rows) - 1)
            case curses.KEY_PPAGE:
                max_y, _ = _stdscr.getmaxyx()
                page = max(1, max_y - 3)
                self.state.selected = max(self.state.selected - page, 0)
            case curses.KEY_HOME:
                self.state.selected = 0
            case curses.KEY_END:
                self.state.selected = max(0, len(self.view_rows) - 1)
            case 10 | 13 | curses.KEY_ENTER:
                if self.view_rows:
                    _, url, _ = self.view_rows[self.state.selected]
                    if url:
                        webbrowser.open(self._trim_intensive_from_url(url))
            case _:
                pass
    # ─── END OF _navigate() ───────────────────────────────────────────────────



    def _trim_intensive_from_url(self, _url: str) -> str:
        """
        Defined in sessions_browser.py.

        Remove '/intensive' from the URL path if present.

        Example:
        https://ivscc.gsfc.nasa.gov/sessions/intensive/2026/r1234
        ->
        https://ivscc.gsfc.nasa.gov/sessions/2026/r1234
        """
        parts       = urlsplit(_url)
        new_path    = parts.path.replace("/intensive/", "/", 1)
        new_path    = new_path.replace("/intensive", "", 1)
        
        return urlunsplit((parts.scheme, parts.netloc, new_path, parts.query, parts.fragment))
    # ─── END OF _trim_intensive_from_url() ────────────────────────────────────



    def _get_input(self, _stdscr, _theme, _prompt: str, _initial: str = "") -> str:
        """
        Defined in sessions_browser.py.

        Get editable input from the user with an initial value pre-filled.

        :param _stdscr: Where to print
        :param _theme: TUITheme for colors
        :param _prompt: Prompt shown before the text
        :param _initial: Initial text to prefill (e.g., current filter)
        :return: The entered text
        """
        curses.curs_set(1)
        curses.noecho()
        _stdscr.keypad(True)

        max_y, max_x = _stdscr.getmaxyx()

        # Prefill with current filter
        buffer: list[str] = list(_initial)
        cursor: int = len(buffer)
        scroll: int = 0

        def _recalc_scroll():
            """
            Defined in sessions_browser.py.

            Keep the cursor visible by adjusting horizontal scroll.
            This is called after any change to cursor position or buffer content.
            """

            nonlocal scroll
            visible_width = max_x - 1
            text_space = visible_width - len(_prompt)
            if text_space < 5:
                text_space = 5

            if cursor < scroll:
                scroll = cursor
            elif cursor > scroll + text_space - 1:
                scroll = cursor - (text_space - 1)
            if scroll < 0:
                scroll = 0

        while True:
            _recalc_scroll()

            text = "".join(buffer)
            visible_width = max_x - 1
            text_space = visible_width - len(_prompt)
            if text_space < 5:
                text_space = 5

            visible_text = text[scroll:scroll + text_space]
            line = (_prompt + visible_text)[:visible_width]

            _stdscr.move(max_y - 1, 0)
            _stdscr.clrtoeol()
            _stdscr.addnstr(max_y - 1, 0, line, visible_width, _theme.reversed | _theme.filtered)

            cursor_col = len(_prompt) + (cursor - scroll)
            cursor_col = max(0, min(cursor_col, visible_width - 1))
            _stdscr.move(max_y - 1, cursor_col)

            ch = _stdscr.getch()
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
                case c if 32 <= c <= 126:
                    buffer.insert(cursor, chr(c))
                    cursor += 1
                case _:
                    pass

        curses.curs_set(0)
        curses.echo()
        return "".join(buffer).strip()
    # ─── END OF _get_input() ──────────────────────────────────────────────────



    def _clear_filters(self) -> None:
        """
        Defined in sessions_browser.py.

        Clear all active filters and reset view.
        """

        self.filters = ""
        self.view_rows = self.formatter.apply_filters_and_sorting(
            _query=self.filters,
            _show_removed=self.state.show_removed,
            _sort_key="start",
            _ascending=True
        )
        self.highlight_tokens = []
    # ─── END OF _clear_filters() ──────────────────────────────────────────────



    def _apply_operator_assignment(self, _session_code: str, _operator_label: str) -> None:
        """
        Defined in sessions_browser.py.

        Assign (or clear) an operator label for a given session code.
        Updates the rendered row values in view_rows.

        :param _session_code: Session code to assign operator to
        :param _operator_label: Operator label (empty string clears)
        """

        session_code = (_session_code or "").strip()
        if not session_code:
            return

        op_label = (_operator_label or "").strip()

        # Update persistent mapping
        if op_label:
            self.operator_assignments[session_code] = op_label
        else:
            self.operator_assignments.pop(session_code, None)

        code_idx = D.FIELD_INDEX.get("code", 2)
        op_idx = D.FIELD_INDEX.get("op", 0)

        # Update view_rows
        for values, _url, _meta in self.view_rows:
            if len(values) > max(code_idx, op_idx) and values[code_idx] == session_code:
                values[op_idx] = f"{op_label}" if op_label else ""
    # ─── END OF _apply_operator_assignment() ──────────────────────────────────



    def run(self, _text: bool = True) -> None:
        """
        Defined in sessions_browser.py.
        
        Run the TUI application. This method initializes the curses environment
        and starts the main loop defined in _curses_main().
        
        When the user exits the TUI, it prints an exit message.                 
        """

        # Using curses to call on the main loop, self._curses.main()
        curses.wrapper(self._curses_main)

        # Print exit message after exiting curses mode
        print(D.EXIT_MESSAGE)

    # ─── END OF run() ─────────────────────────────────────────────────────────
# ─── END OF class SessionsBrowser ─────────────────────────────────────────────
