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
import json
import os
import time
import webbrowser
from datetime import datetime
from importlib import resources
from urllib.parse import urlsplit, urlunsplit
from .pdf_export import write_ansi_lines_pdf
from .statistics import SessionStatistics, build_statistics_report, summarize_rows, write_station_contribution_plot
from .xlsx_export import write_sessions_xlsx

# Project defined imports
from .                          import defs as D

from .fetch_sessions    import FetchSessions
from .manual_sessions   import append_manual_session, build_manual_session_row, delete_manual_session, format_station_tokens, load_manual_session_rows, normalize_station_tokens, validate_manual_session
from .tui               import Tui
from .tui_state         import UIState, TUITheme
from .ivstypes          import PageData
from .operators         import load_operator_assignments, load_operator_bindings, load_operator_colors, save_operator_assignments
# ─── END OF Import section ────────────────────────────────────────────────────



def _load_pdf_default_columns() -> str | list[str]:
    try:
        pdf_columns_path = D.CONFIG_DIR / D.PDF_COLUMNS_FILENAME
        if not pdf_columns_path.exists():
            try:
                pdf_columns_path.parent.mkdir(parents=True, exist_ok=True)
                pdf_columns_path.write_text(D.PDF_COLUMNS_DEFAULT + "\n", encoding="utf-8")
            except Exception:
                pass

        raw = ""
        try:
            raw = (pdf_columns_path.read_text(encoding="utf-8") or "").strip()
        except Exception:
            raw = ""

        if not raw:
            return list(D.PDF_COLUMNS_DEFAULT_LIST)

        raw_up = raw.strip().upper()
        if raw_up == "ALL":
            return "ALL"

        cols = [c.strip().upper() for c in raw_up.split("|") if c.strip()]
        invalid = [c for c in cols if c not in D.PRETTY_PRINT_ALLOWED_COLUMNS]
        if invalid:
            return list(D.PDF_COLUMNS_DEFAULT_LIST)

        return cols
    except Exception:
        return list(D.PDF_COLUMNS_DEFAULT_LIST)


def _save_startup_default_filter(filter_text: str) -> None:
    path = D.CONFIG_DIR / D.STARTUP_DEFAULTS_FILENAME
    data: dict[str, object] = {
        "filters": "",
        "mirrors": False,
        "scope": "both",
        "year": None,
    }

    try:
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                data.update(raw)
    except (json.JSONDecodeError, OSError):
        pass

    data["filters"] = filter_text
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
# ─── END OF _save_startup_default_filter() ───────────────────────────────────


def _load_app_state() -> dict[str, object]:
    path = D.CONFIG_DIR / D.APP_STATE_FILENAME
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}

    return raw if isinstance(raw, dict) else {}


def _save_app_state(state: dict[str, object]) -> None:
    path = D.CONFIG_DIR / D.APP_STATE_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_whats_new_lines(app_version: str) -> list[str]:
    try:
        resource = resources.files("ivs_sessions_browser").joinpath("WHATS_NEW.md")
        raw = resource.read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError, OSError):
        return []

    lines = [line.rstrip() for line in raw.splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()

    if not lines:
        return []

    title = f"What's new in version {app_version}"
    if lines[0].lstrip("# ").strip().lower().startswith("what's new"):
        lines[0] = title
    else:
        lines.insert(0, "")
        lines.insert(0, title)

    return lines


class SessionsBrowser:
    """
    Class representing the IVS Sessions Browser object.
    Defined in sessions_browser.py.

    """

    PDF_STATUS_MESSAGE_DELAY_SECONDS    = 1.9
    STATS_TOP_N                         = 8
    STATION_PLOT_TOP_N                  = None
    # STATION_PLOT_CHART_TYPE             = "pie"
    STATION_PLOT_CHART_TYPE             = "barh"
    STATION_PLOT_METRIC                 = "session_share_pct"   # initial / fallback
    _STATION_PLOT_METRICS               = ("session_share_pct", "hours", "weighted_hours")
    STATION_PLOT_OTHERS_BELOW_PCT       = 3.0
    MANUAL_ADD_STATUS_SECONDS            = 2.5
    MANUAL_ADD_FIELDS                    = (
        ("type", "type", "Type"),
        ("name", "code", "Code"),
        ("start", "start", "Start"),
        ("duration", "dur", "Dur"),
        ("stations", "stations", "Stations"),
        ("ops", "ops", "Ops"),
        ("correlator", "corr", "Corr"),
    )

    def __init__(self, _year: int | list[int], _scope: str, _mirrors: bool = False, _filters: str | None = None, _app_version: str = "0.0.0") -> None:
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
        self.app_version = _app_version

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

        self.formatter.full_list.extend(load_manual_session_rows(self.years))

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
        self._station_plot_metric_idx: int = 0  # index into _STATION_PLOT_METRICS
        self._manual_add_active = False
        self._manual_add_values: dict[str, str] = {}
        self._manual_add_cursors: dict[str, int] = {}
        self._manual_add_field_idx = 0
        self._manual_add_touched: set[str] = set()
        self._manual_add_message = ""
        self._manual_add_message_expires_at: float | None = None
        self._manual_add_previous_selected = 0
        self._manual_add_previous_offset = 0

        # self.operators = load_operators()
        self.operator_bindings      = load_operator_bindings()
        self.operator_assignments   = load_operator_assignments()
        self.operator_colors        = load_operator_colors()
        # Read default PDF columns from user-editable file in CONFIG_DIR
        self.pdf_default_columns = _load_pdf_default_columns()
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
                marker = Tui.type_marker(meta) if c == type_idx else ""
                if marker:
                    base_w = max(0, w - len(marker))
                    parts.append(f"{val:<{base_w}}{marker}")
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

        self._show_whats_new_if_needed(_stdscr)

        # Start the main loop
        quit: bool = False
        while not quit:
            # Determine the view height of the current terminal screen
            self._expire_manual_add_message()
            max_y, _                = _stdscr.getmaxyx()
            reserved_status_lines = 1 if self._manual_add_active or self._manual_add_message else 0
            self.state.view_height  = max(1, max_y - 3 - reserved_status_lines)

            self.formatter.clear_screen(_stdscr)
            self.formatter.draw_header(_stdscr, self.theme, self.state)

            # We pass a filtered list to draw_rows. draw_rows stays "dumb", meaning it just prints whatever
            # we send it.
            self.formatter.draw_rows(_stdscr, self.view_rows, self.highlight_tokens, self.theme, self.state)

            # Draw a help-bar at the bottom of the screen
            self.formatter.draw_helpbar(_stdscr, self.view_rows, self.filters, self.theme, self.state)
            self._draw_manual_add_overlay(_stdscr)

            # Get and parse user input
            if self._manual_add_message and self._manual_add_message_expires_at is not None:
                _stdscr.timeout(250)
            else:
                _stdscr.timeout(-1)
            key = _stdscr.getch()
            if key == -1:
                continue
            if self._manual_add_active:
                self._handle_manual_add_key(key)
                continue
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
                            self.formatter.recompute_header_widths()

                            # Advance selection by one unless we're already on the last row
                            if self.state.selected < len(self.view_rows) - 1:
                                self._navigate(curses.KEY_DOWN, _stdscr)

                # Jump to today's date
                case c if c == ord('T'):
                    idx = self.formatter.filter_sort.index_on_or_after_today(self.view_rows)
                    self.state.selected = self.state.offset = idx

                # Quick month filters: F1-F12 map to Jan-Dec
                case c if self._function_key_month(c) is not None:
                    month = self._function_key_month(c)
                    if month is not None:
                        self._toggle_start_month_filter(month)

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

                # Save current filter as startup default
                case c if c == ord('D'):
                    max_y, max_x = _stdscr.getmaxyx()
                    attr = self.theme.help_bar if self.state.has_colors else 0
                    try:
                        _save_startup_default_filter(self.filters or "")
                        if self.filters:
                            msg = "Saved current filter as startup default"
                        else:
                            msg = "Cleared startup default filter"
                    except OSError as e:
                        msg = f"Error saving startup default filter: {e}"
                    self.formatter._addstr_clip(_stdscr, max_y - 2, 0, msg[: max_x - 1], attr)
                    _stdscr.refresh()
                    time.sleep(self.PDF_STATUS_MESSAGE_DELAY_SECONDS)

                # Add manual session inline
                case c if c in (ord('A'), ord('+')):
                    self._start_manual_add()

                # Delete selected manual session
                case curses.KEY_DC:
                    self._delete_selected_manual_session()

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

                # Save to XLSX
                case c if c == ord('X'):
                    prompt = "XLSX columns (ALL or pipe-separated, e.g. OP|TYPE|STATIONS): "
                    if isinstance(getattr(self, 'pdf_default_columns', None), list):
                        prefill = "|".join(self.pdf_default_columns)
                    else:
                        prefill = str(getattr(self, 'pdf_default_columns', 'ALL'))
                    cols_input = self._get_input(_stdscr, self.theme, prompt, _initial=prefill)
                    if not cols_input:
                        cols_input = "ALL"

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
                        pretty = list(dict.fromkeys(cols))

                    try:
                        max_y, max_x = _stdscr.getmaxyx()
                        filename = f"sessions-{time.strftime('%Y%m%d-%H%M%S')}.xlsx"
                        out_path = os.path.join(os.getcwd(), filename)

                        with open(out_path, "wb") as f:
                            write_sessions_xlsx(
                                self.view_rows,
                                pretty,
                                self.operator_bindings,
                                self.operator_colors,
                                f,
                            )

                        msg = f"Saved XLSX: {out_path}"
                        attr = self.theme.help_bar if self.state.has_colors else 0
                        self.formatter._addstr_clip(_stdscr, max_y - 2, 0, msg[: max_x - 1], attr)
                        _stdscr.refresh()
                        time.sleep(self.PDF_STATUS_MESSAGE_DELAY_SECONDS)

                        try:
                            webbrowser.open(f"file://{out_path}")
                        except Exception:
                            pass
                    except Exception as e:
                        max_y, max_x = _stdscr.getmaxyx()
                        err = f"Error saving XLSX: {e}"
                        attr = self.theme.help_bar if self.state.has_colors else 0
                        self.formatter._addstr_clip(_stdscr, max_y - 2, 0, err[: max_x - 1], attr)
                        _stdscr.refresh()
                        time.sleep(self.PDF_STATUS_MESSAGE_DELAY_SECONDS)

                # Show help
                case c if c == ord('?'):
                    self.formatter.show_help(_stdscr, self.theme)

                # Show statistics
                # case c if c in (ord('S'), ord('s')):
                case c if c == ord('S'):
                    self._show_statistics(_stdscr)

                # Plot station contribution percentages
                case c if c == ord('G'):
                    self._plot_station_contributions(_stdscr)

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



    def _start_manual_add(self) -> None:
        if self._manual_add_active:
            return

        self._manual_add_previous_selected = self.state.selected
        self._manual_add_previous_offset = self.state.offset
        self._manual_add_active = True
        today_start = datetime.now().strftime("%Y-%m-%d 00:00")
        self._manual_add_values = {
            "type": "",
            "name": "",
            "start": today_start,
            "duration": "24:00",
            "stations": "",
            "ops": "",
            "correlator": "",
        }
        self._manual_add_cursors = {
            field_key: len(self._manual_add_values.get(field_key, ""))
            for field_key, _field_name, _label in self.MANUAL_ADD_FIELDS
        }
        self._manual_add_field_idx = 0
        self._manual_add_touched = set()
        self._set_manual_add_message("Add: fill row, Enter saves")
        setattr(self.state, "manual_add_active", True)

        self.view_rows.append(self._manual_add_draft_row())
        self.state.selected = len(self.view_rows) - 1
        self.state.offset = max(0, len(self.view_rows) - max(1, self.state.view_height))
    # ─── END OF _start_manual_add() ──────────────────────────────────────────



    def _handle_manual_add_key(self, _key: int) -> None:
        field_key, _field_name, _label = self.MANUAL_ADD_FIELDS[self._manual_add_field_idx]

        match _key:
            case 27:
                self._cancel_manual_add()
                return
            case 9:
                self._move_manual_add_field(1)
            case curses.KEY_BTAB:
                self._move_manual_add_field(-1)
            case 10 | 13 | curses.KEY_ENTER:
                self._finish_manual_add()
                return
            case curses.KEY_LEFT:
                self._move_manual_add_cursor(field_key, -1)
            case curses.KEY_RIGHT:
                self._move_manual_add_cursor(field_key, 1)
            case curses.KEY_HOME:
                self._manual_add_cursors[field_key] = 0
            case curses.KEY_END:
                self._manual_add_cursors[field_key] = len(self._manual_add_values.get(field_key, ""))
            case 8 | 127 | curses.KEY_BACKSPACE:
                current = self._manual_add_values.get(field_key, "")
                cursor = self._manual_add_cursor(field_key)
                if cursor > 0:
                    self._manual_add_values[field_key] = current[:cursor - 1] + current[cursor:]
                    self._manual_add_cursors[field_key] = cursor - 1
                    self._manual_add_touched.add(field_key)
            case curses.KEY_DC:
                current = self._manual_add_values.get(field_key, "")
                cursor = self._manual_add_cursor(field_key)
                if cursor < len(current):
                    self._manual_add_values[field_key] = current[:cursor] + current[cursor + 1:]
                    self._manual_add_touched.add(field_key)
            case c if 32 <= c <= 126:
                current = self._manual_add_values.get(field_key, "")
                cursor = self._manual_add_cursor(field_key)
                char = chr(c)
                self._manual_add_values[field_key] = current[:cursor] + char + current[cursor:]
                self._manual_add_cursors[field_key] = cursor + 1
                self._manual_add_touched.add(field_key)
            case _:
                pass

        _field_key, _field_name, current_label = self.MANUAL_ADD_FIELDS[self._manual_add_field_idx]
        self._set_manual_add_message(f"Edit {current_label}")
        self._replace_manual_add_draft_row()
    # ─── END OF _handle_manual_add_key() ─────────────────────────────────────



    def _move_manual_add_field(self, _delta: int) -> None:
        self._normalize_manual_add_field_on_exit()
        count = len(self.MANUAL_ADD_FIELDS)
        self._manual_add_field_idx = (self._manual_add_field_idx + _delta) % count
        self._clamp_manual_add_cursor(self.MANUAL_ADD_FIELDS[self._manual_add_field_idx][0])
    # ─── END OF _move_manual_add_field() ─────────────────────────────────────



    def _manual_add_cursor(self, _field_key: str) -> int:
        value = self._manual_add_values.get(_field_key, "")
        cursor = self._manual_add_cursors.get(_field_key, len(value))
        cursor = max(0, min(cursor, len(value)))
        self._manual_add_cursors[_field_key] = cursor
        return cursor
    # ─── END OF _manual_add_cursor() ─────────────────────────────────────────



    def _move_manual_add_cursor(self, _field_key: str, _delta: int) -> None:
        self._manual_add_cursors[_field_key] = self._manual_add_cursor(_field_key) + _delta
        self._clamp_manual_add_cursor(_field_key)
    # ─── END OF _move_manual_add_cursor() ────────────────────────────────────



    def _clamp_manual_add_cursor(self, _field_key: str) -> None:
        value = self._manual_add_values.get(_field_key, "")
        self._manual_add_cursors[_field_key] = max(0, min(self._manual_add_cursors.get(_field_key, len(value)), len(value)))
    # ─── END OF _clamp_manual_add_cursor() ───────────────────────────────────



    def _normalize_manual_add_field_on_exit(self) -> None:
        field_key, _field_name, _label = self.MANUAL_ADD_FIELDS[self._manual_add_field_idx]
        if field_key in ("type", "name", "ops", "correlator"):
            self._manual_add_values[field_key] = self._manual_add_values.get(field_key, "").strip().upper()
            self._manual_add_cursors[field_key] = len(self._manual_add_values[field_key])
            return

        if field_key != "stations":
            return

        raw = self._manual_add_values.get("stations", "")
        if not raw.strip():
            return

        stations, error = normalize_station_tokens(raw)
        if error:
            self._set_manual_add_message(error)
            return

        self._manual_add_values["stations"] = ", ".join(stations)
        self._manual_add_cursors["stations"] = len(self._manual_add_values["stations"])
        self._set_manual_add_message("Stations OK")
    # ─── END OF _normalize_manual_add_field_on_exit() ────────────────────────



    def _finish_manual_add(self) -> None:
        existing_names = {
            values[D.FIELD_INDEX.get("code", 2)].strip()
            for values, _url, meta in self.formatter.full_list
            if values and not meta.get("draft")
        }
        normalized, errors = validate_manual_session(
            self._manual_add_values,
            existing_names=existing_names,
        )

        if errors or normalized is None:
            first_key, message = next(iter(errors.items()))
            self._focus_manual_add_field(first_key)
            self._set_manual_add_message(message)
            self._replace_manual_add_draft_row()
            return

        try:
            stored = append_manual_session(normalized)
        except ValueError as exc:
            self._set_manual_add_message(str(exc))
            self._replace_manual_add_draft_row()
            return
        except OSError as exc:
            self._set_manual_add_message(f"Could not save manual session: {exc}")
            self._replace_manual_add_draft_row()
            return

        row = build_manual_session_row(stored, self.operator_assignments)
        if row is not None:
            self.formatter.full_list.append(row)

        saved_name = stored["name"]
        self._manual_add_active = False
        setattr(self.state, "manual_add_active", False)
        self._set_manual_add_message(f"Saved manual session {saved_name}", _temporary=True)
        self._refresh_view_after_manual_add(saved_name)
    # ─── END OF _finish_manual_add() ─────────────────────────────────────────



    def _cancel_manual_add(self) -> None:
        self._manual_add_active = False
        setattr(self.state, "manual_add_active", False)
        self._manual_add_values = {}
        self._manual_add_cursors = {}
        self._set_manual_add_message("Manual session add cancelled", _temporary=True)
        self._refresh_view_after_manual_add(None, _restore_previous=True)
    # ─── END OF _cancel_manual_add() ─────────────────────────────────────────



    def _delete_selected_manual_session(self) -> None:
        if not self.view_rows or not (0 <= self.state.selected < len(self.view_rows)):
            return

        values, _url, meta = self.view_rows[self.state.selected]
        if not meta.get("manual"):
            self._set_manual_add_message("Del only removes manual sessions", _temporary=True)
            return

        code_idx = D.FIELD_INDEX.get("code", 2)
        session_code = values[code_idx].strip() if len(values) > code_idx else ""
        if not session_code:
            self._set_manual_add_message("Manual session has no code", _temporary=True)
            return

        try:
            deleted = delete_manual_session(session_code)
        except ValueError as exc:
            self._set_manual_add_message(str(exc), _temporary=True)
            return
        except OSError as exc:
            self._set_manual_add_message(f"Could not delete manual session: {exc}", _temporary=True)
            return

        if not deleted:
            self._set_manual_add_message(f"Manual session not found: {session_code}", _temporary=True)
            return

        selected_before = self.state.selected
        self.formatter.full_list = [
            row for row in self.formatter.full_list
            if not (row[2].get("manual") and row[0][code_idx].strip() == session_code)
        ]
        self.view_rows = self.formatter.apply_filters_and_sorting(
            _query=self.filters,
            _show_removed=self.state.show_removed,
            _sort_key="start",
            _ascending=True
        )
        self.highlight_tokens = self.formatter.filter_sort.extract_station_tokens(self.filters or "")
        self.formatter.recompute_header_widths()
        self.state.selected = min(selected_before, max(0, len(self.view_rows) - 1))
        self.state.offset = min(self.state.offset, max(0, len(self.view_rows) - 1))
        self._set_manual_add_message(f"Deleted manual session {session_code}", _temporary=True)
    # ─── END OF _delete_selected_manual_session() ────────────────────────────



    def _refresh_view_after_manual_add(self, _select_code: str | None, *, _restore_previous: bool = False) -> None:
        self.view_rows = self.formatter.apply_filters_and_sorting(
            _query=self.filters,
            _show_removed=self.state.show_removed,
            _sort_key="start",
            _ascending=True
        )
        self.highlight_tokens = self.formatter.filter_sort.extract_station_tokens(self.filters or "")
        self.formatter.recompute_header_widths()

        if _restore_previous:
            self.state.selected = min(self._manual_add_previous_selected, max(0, len(self.view_rows) - 1))
            self.state.offset = min(self._manual_add_previous_offset, max(0, len(self.view_rows) - 1))
            return

        if _select_code:
            code_idx = D.FIELD_INDEX.get("code", 2)
            for i, (values, _url, _meta) in enumerate(self.view_rows):
                if len(values) > code_idx and values[code_idx] == _select_code:
                    self.state.selected = i
                    self.state.offset = max(0, i - max(0, self.state.view_height - 1))
                    return

        self.state.selected = min(self.state.selected, max(0, len(self.view_rows) - 1))
        self.state.offset = min(self.state.offset, max(0, len(self.view_rows) - 1))
    # ─── END OF _refresh_view_after_manual_add() ─────────────────────────────



    def _set_manual_add_message(self, _message: str, *, _temporary: bool = False) -> None:
        self._manual_add_message = _message
        if _temporary:
            self._manual_add_message_expires_at = time.monotonic() + self.MANUAL_ADD_STATUS_SECONDS
        else:
            self._manual_add_message_expires_at = None
    # ─── END OF _set_manual_add_message() ────────────────────────────────────



    def _expire_manual_add_message(self) -> None:
        if self._manual_add_active:
            return
        if self._manual_add_message_expires_at is None:
            return
        if time.monotonic() < self._manual_add_message_expires_at:
            return

        self._manual_add_message = ""
        self._manual_add_message_expires_at = None
    # ─── END OF _expire_manual_add_message() ─────────────────────────────────



    def _focus_manual_add_field(self, _key: str) -> None:
        aliases = {"duration": "duration", "dur": "duration", "corr": "correlator"}
        wanted = aliases.get(_key, _key)
        for i, (field_key, _field_name, _label) in enumerate(self.MANUAL_ADD_FIELDS):
            if field_key == wanted:
                self._manual_add_field_idx = i
                self._clamp_manual_add_cursor(field_key)
                return
    # ─── END OF _focus_manual_add_field() ────────────────────────────────────



    def _replace_manual_add_draft_row(self) -> None:
        if not self.view_rows:
            self.view_rows.append(self._manual_add_draft_row())
            self.state.selected = 0
            return

        if self.state.selected < 0 or self.state.selected >= len(self.view_rows):
            self.state.selected = len(self.view_rows) - 1

        self.view_rows[self.state.selected] = self._manual_add_draft_row()
    # ─── END OF _replace_manual_add_draft_row() ──────────────────────────────



    def _manual_add_draft_row(self) -> D.Row:
        values = [""] * len(D.HEADERS)
        values[D.FIELD_INDEX["type"]] = self._manual_add_values.get("type", "Manual")
        values[D.FIELD_INDEX["code"]] = self._manual_add_values.get("name", "")
        values[D.FIELD_INDEX["start"]] = self._manual_add_values.get("start", "")
        values[D.FIELD_INDEX["dur"]] = self._manual_add_values.get("duration", "")
        values[D.FIELD_INDEX["stations"]] = self._manual_add_station_display_value()
        values[D.FIELD_INDEX["ops"]] = self._manual_add_values.get("ops", "")
        values[D.FIELD_INDEX["corr"]] = self._manual_add_values.get("correlator", "")
        values[D.FIELD_INDEX["status"]] = "Manual"

        stations = "".join(normalize_station_tokens(self._manual_add_values.get("stations", ""))[0])
        meta = {
            "intensive": False,
            "manual": True,
            "draft": True,
            "code": self._manual_add_values.get("name", ""),
            "active": stations,
            "removed": "",
        }
        return (values, None, meta)
    # ─── END OF _manual_add_draft_row() ──────────────────────────────────────



    def _manual_add_station_display_value(self) -> str:
        value = self._manual_add_values.get("stations", "")
        if not self._manual_add_active:
            return format_station_tokens(value)

        field_key, _field_name, _label = self.MANUAL_ADD_FIELDS[self._manual_add_field_idx]
        if field_key == "stations":
            return value

        return format_station_tokens(value)
    # ─── END OF _manual_add_station_display_value() ─────────────────────────



    def _draw_manual_add_overlay(self, _stdscr) -> None:
        if not self._manual_add_active:
            try:
                curses.curs_set(0)
            except Exception:
                pass
            if self._manual_add_message:
                max_y, max_x = _stdscr.getmaxyx()
                attr = self.theme.help_bar if self.state.has_colors else 0
                self.formatter._addstr_clip(_stdscr, max_y - 2, 0, self._manual_add_message[: max_x - 1], attr)
            return

        max_y, max_x = _stdscr.getmaxyx()
        if self._manual_add_message:
            attr = self.theme.help_bar if self.state.has_colors else 0
            self.formatter._addstr_clip(_stdscr, max_y - 2, 0, self._manual_add_message[: max_x - 1], attr)

        if self.state.selected < self.state.offset:
            return
        if self.state.selected >= self.state.offset + self.state.view_height:
            return

        field_key, field_name, _label = self.MANUAL_ADD_FIELDS[self._manual_add_field_idx]
        col_idx = D.FIELD_INDEX[field_name]
        y = self.state.selected - self.state.offset + 2
        x = self.formatter._col_start_x(col_idx) + 2
        width = D.WIDTHS[col_idx]
        value = self.view_rows[self.state.selected][0][col_idx]
        text = f"{value:<{width}}"
        attr = (self.theme.filtered | curses.A_REVERSE) if self.state.has_colors else curses.A_REVERSE
        self.formatter._addstr_clip(_stdscr, y, x, text[: max(0, max_x - x - 1)], attr)
        try:
            cursor_x = min(x + self._manual_add_cursor(field_key), x + max(0, width - 1), max_x - 2)
            _stdscr.move(y, max(0, cursor_x))
            curses.curs_set(1)
        except Exception:
            pass
    # ─── END OF _draw_manual_add_overlay() ───────────────────────────────────



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



    def get_statistics(self, _visible_only: bool = False) -> SessionStatistics:
        """
        Defined in sessions_browser.py.

        Compute statistics from loaded rows.

        :param _visible_only: If True, summarize only currently filtered rows.
        :return: SessionStatistics dataclass instance.
        """

        rows = self.view_rows if _visible_only else self.formatter.full_list
        return summarize_rows(rows)
    # ─── END OF get_statistics() ──────────────────────────────────────────────



    def _show_statistics(self, _stdscr) -> None:
        """
        Defined in sessions_browser.py.

        Show a compact statistics window for loaded and visible sessions.
        """

        lines = build_statistics_report(
            self.formatter.full_list,
            self.view_rows,
            top_n=self.STATS_TOP_N,
        )

        max_y, max_x = _stdscr.getmaxyx()
        footer = "Up/Down scroll, q/Enter close"
        display_lines = lines + ["", footer]

        width = min(max(len(line) for line in display_lines) + 4, max_x - 4)
        height = min(max_y - 4, max(8, min(len(display_lines) + 2, max_y - 4)))

        if width < 20 or height < 8:
            return

        top = (max_y - height) // 2
        left = (max_x - width) // 2
        win = curses.newwin(height, width, top, left)
        win.keypad(True)

        max_visible = height - 2
        scroll = 0
        max_scroll = max(0, len(display_lines) - max_visible)

        while True:
            win.erase()
            win.box()

            visible = display_lines[scroll: scroll + max_visible]
            for i, line in enumerate(visible):
                absolute_idx = scroll + i
                if absolute_idx == 0 and self.state.has_colors:
                    attr = self.theme.header
                elif absolute_idx == len(display_lines) - 1 and self.state.has_colors:
                    attr = self.theme.help_bar
                else:
                    attr = 0
                win.addnstr(i + 1, 2, line, width - 4, attr)

            win.refresh()
            key = win.getch()

            if key in (ord("q"), ord("Q"), 10, 13, curses.KEY_ENTER, 27):
                break
            if key in (curses.KEY_DOWN, ord("j")):
                scroll = min(max_scroll, scroll + 1)
            elif key in (curses.KEY_UP, ord("k")):
                scroll = max(0, scroll - 1)
            elif key == curses.KEY_NPAGE:
                scroll = min(max_scroll, scroll + max_visible)
            elif key == curses.KEY_PPAGE:
                scroll = max(0, scroll - max_visible)
    # ─── END OF _show_statistics() ───────────────────────────────────────────


    def _show_whats_new_if_needed(self, _stdscr) -> None:
        """
        Show the bundled "what's new" notes once per installed version.
        """

        state = _load_app_state()
        if state.get("whats_new_seen_version") == self.app_version:
            return

        lines = _load_whats_new_lines(self.app_version)
        if not lines:
            return

        self._show_scrollable_text_window(
            _stdscr,
            lines,
            footer="Up/Down scroll, q/Enter close",
        )

        state["whats_new_seen_version"] = self.app_version
        try:
            _save_app_state(state)
        except OSError:
            pass
    # ─── END OF _show_whats_new_if_needed() ──────────────────────────────────



    def _show_scrollable_text_window(self, _stdscr, lines: list[str], footer: str) -> None:
        """
        Display text in a centered, scrollable popup.
        """

        display_lines = lines + ["", footer]
        max_y, max_x = _stdscr.getmaxyx()
        width = min(max(len(line) for line in display_lines) + 4, max_x - 4)
        height = min(max_y - 4, max(8, min(len(display_lines) + 2, max_y - 4)))

        if width < 20 or height < 8:
            return

        top = (max_y - height) // 2
        left = (max_x - width) // 2
        win = curses.newwin(height, width, top, left)
        win.keypad(True)

        max_visible = height - 2
        scroll = 0
        max_scroll = max(0, len(display_lines) - max_visible)

        while True:
            win.erase()
            win.box()

            visible = display_lines[scroll: scroll + max_visible]
            for i, line in enumerate(visible):
                absolute_idx = scroll + i
                if absolute_idx == 0 and self.state.has_colors:
                    attr = self.theme.header
                elif absolute_idx == len(display_lines) - 1 and self.state.has_colors:
                    attr = self.theme.help_bar
                else:
                    attr = 0
                win.addnstr(i + 1, 2, line, width - 4, attr)

            win.refresh()
            key = win.getch()

            if key in (ord("q"), ord("Q"), 10, 13, curses.KEY_ENTER, 27):
                break
            if key in (curses.KEY_DOWN, ord("j")):
                scroll = min(max_scroll, scroll + 1)
            elif key in (curses.KEY_UP, ord("k")):
                scroll = max(0, scroll - 1)
            elif key == curses.KEY_NPAGE:
                scroll = min(max_scroll, scroll + max_visible)
            elif key == curses.KEY_PPAGE:
                scroll = max(0, scroll - max_visible)
    # ─── END OF _show_scrollable_text_window() ────────────────────────────────



    def _plot_station_contributions(self, _stdscr) -> None:
        """
        Defined in sessions_browser.py.

        Create and open a plot of station contribution percentages.
        """

        max_y, max_x    = _stdscr.getmaxyx()
        attr            = self.theme.help_bar if self.state.has_colors else 0

        # Advance to the next metric in the cycle before plotting
        self._station_plot_metric_idx = (
            self._station_plot_metric_idx + 1
        ) % len(self._STATION_PLOT_METRICS)
        current_metric = self._STATION_PLOT_METRICS[self._station_plot_metric_idx]

        try:
            filename = f"station-contribution-{time.strftime('%Y%m%d-%H%M%S')}.png"
            out_path = os.path.join(os.getcwd(), filename)

            # Call the plotting function from statistics.py, which returns the
            # path to the saved PNG file
            write_station_contribution_plot(
                self.formatter.full_list,
                output_path         = out_path,
                top_n               = self.STATION_PLOT_TOP_N,
                chart_type          = self.STATION_PLOT_CHART_TYPE,
                metric              = current_metric,
                aggregate_below_pct = self.STATION_PLOT_OTHERS_BELOW_PCT,
            )

            metric_labels = {
                "session_share_pct": "session %",
                "hours":             "hours",
                "weighted_hours":    "weighted hours",
            }
            msg = f"[{metric_labels[current_metric]}] Saved station plot: {out_path}"
            self.formatter._addstr_clip(_stdscr, max_y - 2, 0, msg[: max_x - 1], attr)
            _stdscr.refresh()
            time.sleep(self.PDF_STATUS_MESSAGE_DELAY_SECONDS)

            try:
                webbrowser.open(f"file://{out_path}")
            except Exception:
                pass

        except Exception as e:
            err = f"Error creating station plot: {e}"
            self.formatter._addstr_clip(_stdscr, max_y - 2, 0, err[: max_x - 1], attr)
            _stdscr.refresh()
            time.sleep(self.PDF_STATUS_MESSAGE_DELAY_SECONDS)
    # ─── END OF _plot_station_contributions() ────────────────────────────────



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
        _stdscr.timeout(-1)

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



    def _function_key_month(self, _key: int) -> int | None:
        key_f = getattr(curses, "KEY_F", None)
        if callable(key_f):
            for month in range(1, 13):
                if _key == key_f(month):
                    return month

        key_f0 = getattr(curses, "KEY_F0", None)
        if key_f0 is not None and key_f0 < _key <= key_f0 + 12:
            return _key - key_f0

        for month in range(1, 13):
            if _key == getattr(curses, f"KEY_F{month}", None):
                return month
        return None
    # ─── END OF _function_key_month() ────────────────────────────────────────



    def _toggle_start_month_filter(self, _month: int) -> None:
        previous_filters = self.filters or ""
        month_was_active = self.formatter.filter_sort.has_exact_start_month_filter(previous_filters, _month)

        self.filters = self.formatter.filter_sort.toggle_start_month_filter(previous_filters, _month)
        self.view_rows = self.formatter.apply_filters_and_sorting(
            _query=self.filters,
            _show_removed=self.state.show_removed,
            _sort_key="start",
            _ascending=True
        )
        self.highlight_tokens = self.formatter.filter_sort.extract_station_tokens(self.filters or "")

        if month_was_active:
            idx = self.formatter.filter_sort.index_on_or_after_today(self.view_rows)
            self.state.selected = self.state.offset = idx
        else:
            self.state.selected = 0
            self.state.offset = 0
    # ─── END OF _toggle_start_month_filter() ─────────────────────────────────



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
