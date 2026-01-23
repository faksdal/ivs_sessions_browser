"""
Filename:       sessions_browser.py
Author:         jole
Created:        15.09.2025

Description:    Holds class definitions for SessionBrowser along with attributes and methods.

Notes:
"""

# --- Import section ---------------------------------------------------------------------------------------------------
import shutil
import subprocess
import sys
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import requests

# --- Project defined
from . import defs as D  # add this import near the top (recommended)
from .defs import (
    BASE_URL,
    FIELD_INDEX,
    HEADER_LINE,
    HEADERS,
    NAVIGATION_KEYS,
    WIDTHS,
    Row,
    recompute_header_widths,
)
from .draw_tui import DrawTUI
from .filter_and_sort import FilterAndSort
from .operators import load_operator_bindings, load_operators, save_operators
from .read_data import DataFetchFailedError, NoSessionsForYearError, ReadData
from .tui_state import *

# --- END OF Import section --------------------------------------------------------------------------------------------


class SessionsBrowser:
    """
    SessionBrowser holds the logic for the whole application, it keeps everything together!

    Application execution steps:
        - Get data from url's depending on the value in self.scope.
        - Display organized data as lines, supporting navigation with keyboard in terminal.
        - Run the loop, catching users input and act appropriately.
    """

    PRINT_COLUMNS = ["op", "type", "code", "start", "doy", "dur", "stations"]
    PRINT_WIDTH_OVERRIDES = {
        "stations": 48,  # pick what you like: 60, 80, 120...
    }

    def __init__(self, _year: int, _scope: str, _stations_filter: Optional[str] = None) -> None:
        self.year = _year
        self.scope = _scope
        self.stations_filter = _stations_filter
        self.state = UIState()
        self.theme: TUITheme = None
        self.draw: DrawTUI = DrawTUI()

        # --- Create and populate the list of url's we want to download from.
        self.urls: List[str] = self._urls_for_scope()

        # --- self.rows contains all rosw read from web
        # --- self.view_rows contains the filtered list
        self.rows: List[Row] = []  # populated in run()
        self.view_rows: List[Row] = []

        # --- Tokens to highlight in the stations column when filtering
        self.highlight_tokens: List[str] = []

        # --- Holds the current filter as input by user
        self.current_filter: str = ""

        self.fs = FilterAndSort()

        # self.operators = load_operators()
        self.operator_bindings = load_operator_bindings()
        self.operators = load_operators()

        # --- For debugging
        # print(self.operators)
        # exit(0)

    # --- END OF __init__() --------------------------------------------------------------------------------------------

    def _clip(self, s: str, w: int) -> str:
        """Clip string to width w (no ellipsis; matches screen-like hard clipping)."""
        s = s or ""
        return s[:w] if w > 0 else ""

    # --- END OF _clip() -----------------------------------------------------------------------------------------------

    # def _print_header_for_columns(self) -> str:
    #     parts = []
    #     for col in self.PRINT_COLUMNS:
    #         i = FIELD_INDEX.get(col, -1)
    #         if i < 0:
    #             continue
    #         name = HEADERS[i]
    #         w = WIDTHS[i]
    #         parts.append(f"{name:<{w}}")
    #     return " | ".join(parts)
    def _print_header_for_columns(self) -> str:
        parts = []
        for col in self.PRINT_COLUMNS:
            i = FIELD_INDEX.get(col, -1)
            if i < 0:
                continue

            h = HEADERS[i]
            # HEADERS[i] might be ("Op", "op") or similar; take the label part.
            name = h[0] if isinstance(h, (tuple, list)) else h

            w = self.PRINT_WIDTH_OVERRIDES.get(col, WIDTHS[i])
            parts.append(f"{str(name):<{int(w)}}")
        return " | ".join(parts)

    # --- END OF _print_header_for_columns() ---------------------------------------------------------------------------

    def _format_row_for_print(self, row: Row) -> str:
        values, _url, meta = row
        vals = list(values)

        # Match screen behavior: when hiding removed, show only "active" string
        if not self.state.show_removed:
            active_only = meta.get("active", "")
            stations_idx = FIELD_INDEX.get("stations", -1)
            if 0 <= stations_idx < len(vals):
                vals[stations_idx] = active_only

        type_idx = FIELD_INDEX.get("type", 0)

        parts = []
        for col in self.PRINT_COLUMNS:
            i = FIELD_INDEX.get(col, -1)
            if i < 0 or i >= len(vals):
                continue

            # w = WIDTHS[i]
            w = self.PRINT_WIDTH_OVERRIDES.get(col, WIDTHS[i])

            val = vals[i]

            # Match screen behavior for intensives: reserve 3 chars for "[I]"
            if i == type_idx and meta.get("intensive"):
                base_w = max(0, w - 3)
                left = self._clip(val, base_w)
                parts.append(f"{left:<{base_w}}[I]")
            else:
                clipped = self._clip(val, w)
                parts.append(f"{clipped:<{w}}")

        return " | ".join(parts)

    # --- END OF _format_row_for_print() -------------------------------------------------------------------------------

    def _print_visible_range(self) -> None:
        if not self.view_rows:
            return

        start = self.state.offset
        end = min(len(self.view_rows), self.state.offset + self.state.view_height)

        lines = []
        # lines.append(HEADER_LINE)
        # lines.append("-" * len(HEADER_LINE))
        hdr = self._print_header_for_columns()
        lines.append(hdr)
        lines.append("-" * len(hdr))

        for i in range(start, end):
            lines.append(self._format_row_for_print(self.view_rows[i]))

        # Write to a temp-ish file under ~/.cache so user can reprint/debug
        cache_dir = Path.home() / ".cache" / "ivs_sessions_browser"
        cache_dir.mkdir(parents=True, exist_ok=True)

        latest_path = cache_dir / "sessions_range_latest.txt"
        latest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        # Optional: keep history (set to False to disable)
        keep_history = False
        if keep_history:
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            hist_path = cache_dir / f"sessions_range_{ts}.txt"
            hist_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

            # Keep only the newest N history files
            keep_n = 5
            files = sorted(
                cache_dir.glob("sessions_range_*.txt"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            for old in files[keep_n:]:
                try:
                    old.unlink()
                except OSError:
                    pass

        # Print the latest file
        # out_path = latest_path

        # ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        # out_path = cache_dir / f"sessions_range_{ts}.txt"
        # out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        # Send to printer
        # if shutil.which("lp"):
        #     subprocess.run(["lp", str(out_path)], check=False)
        # elif shutil.which("lpr"):
        #     subprocess.run(["lpr", str(out_path)], check=False)
        # else:
        # No print tool available; at least leave the file behind
        # pass

    # --- END OF _print_visible_range() --------------------------------------------------------------------------------

    def _clear_filters(self) -> None:
        """
        Clears all active filters

        :return: None
        """
        self.current_filter = ""
        self.view_rows = self.fs.apply(
            self.rows,
            _query=self.current_filter,
            _show_removed=self.state.show_removed,
            _sort_key="start",
            _ascending=True,
        )
        self.highlight_tokens = []
        idx = self.fs.index_on_or_after_today(self.view_rows)
        self.state.selected = self.state.offset = idx

    # --- END OF _clear_filters() --------------------------------------------------------------------------------------

    def _get_input(self, _stdscr, _theme: TUITheme, _prompt: str, _initial: str = "") -> str:
        """
        Get editable input from the user with an initial value pre-filled.

        :param _stdscr:  Where to print
        :param _prompt:  Prompt shown before the text
        :param _initial: Initial text to prefill (e.g., current filter)

        :return:        The entered text
        """
        curses.curs_set(1)
        curses.noecho()

        # --- Important for KEY_* codes
        _stdscr.keypad(True)

        max_y, max_x = _stdscr.getmaxyx()

        # --- EDITABLE STATE

        # --- Prefill with current filter
        buffer: list[str] = list(_initial)

        # --- Cursor index inside buffer
        cursor: int = len(buffer)

        # --- Horizontal scroll of the *text* (not including prompt)
        scroll: int = 0

        def _recalc_scroll():
            """
            Keep the cursor visible by adjusting horizontal scroll.
            """

            nonlocal scroll

            # --- How many cells we can draw
            visible_width = max_x - 1

            # --- Space available for the text after the prompt:
            text_space = visible_width - len(_prompt)
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
            text_space = visible_width - len(_prompt)
            if text_space < 5:
                text_space = 5

            # --- Take the slice of text that should be visible
            visible_text = text[scroll : scroll + text_space]
            line = (_prompt + visible_text)[:visible_width]

            # --- Clear last line and draw prompt + visible text inverted
            _stdscr.move(max_y - 1, 0)
            _stdscr.clrtoeol()

            # --- Added filter color to filter-input-field
            _stdscr.addnstr(max_y - 1, 0, line, visible_width, _theme.reversed | _theme.filtered)

            # --- Compute on-screen cursor column
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

    def _navigate(self, _key: int, _stdscr) -> None:
        """
        Wrapper for main loop, _curses_main, to handle navigation in the session list.
        The idea is to keep a neater _curse_main.
        This wrapper handles navigation keys: up/down arrows, page up/down, home/end and the enter key
        to open the selected session in browser.

        :param _key:    The curses.KEY_xxx to handle
        :param _stdscr: The screen to write to (curses)

        :return:        None
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
                        webbrowser.open(url)
            case _:
                pass

    # --- END OF _navigate() -------------------------------------------------------------------------------------------

    def _apply_operator_assignment(self, _session_code: str, _operator_label: str) -> None:
        """
        Assign (or clear) an operator label for a given session code.

        Updates:
          - self.operators (persisted mapping)
          - the rendered row values in both self.rows and self.view_rows
        """

        session_code = (_session_code or "").strip()
        if not session_code:
            return

        op_label = (_operator_label or "").strip()

        # --- Update persistent mapping (in-memory; saving handled by caller)
        if op_label:
            self.operators[session_code] = op_label
        else:
            # treat empty label as "clear"
            self.operators.pop(session_code, None)

        code_idx = FIELD_INDEX.get("code", 2)
        op_idx = FIELD_INDEX.get("op", 0)

        def _update_rows(rows: List[Row]) -> None:
            for values, _url, _meta in rows:
                if len(values) > max(code_idx, op_idx) and values[code_idx] == session_code:
                    # values[op_idx] = op_label
                    values[op_idx] = f" {op_label}" if op_label else ""

        _update_rows(self.rows)
        _update_rows(self.view_rows)

    # --- END OF _apply_operator_assignment() -------------------------------------------------------------------------------------------

    def _curses_main(self, _stdscr) -> None:
        """
        This constitutes the main loop of the application.
        """

        self.theme = TUITheme.init_theme()  # <- use class, not instance

        # --- Set global has_colors in TUIState instance
        self.state.has_colors = curses.has_colors()

        # --- Start the main loop
        quit: bool = False
        while not quit:
            # --- Determine the view height of the current terminal screen
            max_y, _ = _stdscr.getmaxyx()
            self.state.view_height = max(1, max_y - 3)

            self.draw.clear_screen(_stdscr)
            self.draw.draw_header(_stdscr, self.theme, self.state)

            # --- We pass a filtered list to draw_rows. draw_rows stays "dumb", meaning it just prints whatever
            # --- we send it.
            self.draw.draw_rows(
                _stdscr, self.view_rows, self.highlight_tokens, self.theme, self.state
            )

            # --- Draw a help-bar at thw bottom of the screen
            self.draw.draw_helpbar(
                _stdscr,
                self.view_rows,
                self.current_filter,
                self.theme,
                self.state,
                self.operator_bindings,
            )

            # --- Parse user input
            key = _stdscr.getch()
            match key:
                case curses.KEY_LEFT:
                    pass
                    # self.h_off = max(0, self.h_off - 1)
                case curses.KEY_RIGHT:
                    pass
                    # self.h_off = self.h_off + 1

                # --- Handles all navigation keys, and [ENTER]
                case key if key in NAVIGATION_KEYS:
                    self._navigate(key, _stdscr)

                # -- Catches keystrokes 0-9, used to assign an operator to a session
                # --- Operator assignment: digit 0-9
                # ---  - translate digit -> operator label using operator_bindings
                # ---  - set session_code -> operator label in self.operators
                # ---  - persist immediately so it's available on next startup
                case c if ord("0") <= c <= ord("5"):
                    if self.view_rows and 0 <= self.state.selected < len(self.view_rows):
                        digit = chr(c)
                        operator_label = self.operator_bindings.get(digit, "")

                        values, _, _ = self.view_rows[self.state.selected]
                        code_idx = FIELD_INDEX.get("code", 2)
                        session_code = values[code_idx] if len(values) > code_idx else ""

                        if session_code:
                            self._apply_operator_assignment(session_code, operator_label)
                            save_operators(self.operators)

                            # Advance selection by one unless we're already on the last row
                            if self.state.selected < len(self.view_rows) - 1:
                                self._navigate(curses.KEY_DOWN, _stdscr)

                # --- Jump to today's date (or the next if today is not in list)
                case c if c == ord("T"):
                    idx = self.fs.index_on_or_after_today(self.view_rows)
                    self.state.selected = self.state.offset = idx
                #
                # --- Apply user filter
                case c if c == ord("/"):
                    # --- If we have a filter already, prefill prompt with it as a convenience to the user
                    prefill = self.current_filter or ""

                    # --- Get new filter from user
                    new_filter = self._get_input(_stdscr, self.theme, "/ ", _initial=prefill)

                    self.current_filter = new_filter
                    self.view_rows = self.fs.apply(
                        self.rows,
                        _query=self.current_filter,
                        _show_removed=self.state.show_removed,
                        _sort_key="start",
                        _ascending=True,
                    )

                    # --- Jump to today
                    idx = self.fs.index_on_or_after_today(self.view_rows)
                    self.state.selected = self.state.offset = idx

                    # --- Highlight stations when filtered
                    self.highlight_tokens = self.fs.extract_station_tokens(self.current_filter)

                # --- Clear active filters
                case c if c == (ord("C")):
                    self._clear_filters()

                # --- Hide/show removed stations
                case c if c == (ord("R")):
                    self.state.show_removed = not self.state.show_removed
                    self.view_rows = self.fs.apply(
                        self.rows,
                        _query=self.current_filter,
                        _show_removed=self.state.show_removed,
                        _sort_key="start",
                        _ascending=True,
                    )

                # --- Show help
                case c if c == (ord("?")):
                    self.draw.show_help(_stdscr, self.theme)

                # --- Print visible range (Ctrl+P)
                case 16:
                    self._print_visible_range()

                # --- Quit the script and return to terminal
                case c if c in (ord("q"), ord("Q")):
                    quit = True

                # --- Any other key we'll just pass
                case _:
                    pass
            # --- END OF match key -------------------------------------------------------------------------------------
        # --- END OF while not quit ------------------------------------------------------------------------------------

    # --- END OF _curses_main() ----------------------------------------------------------------------------------------

    def _urls_for_scope(self) -> List[str]:
        """
        Constructing the list of URL's to read from, based on the users input at terminal.
        This is being called from the SessionsBrowser __init__() function.

        :return List[str]:  List of url's from which we read our data. This will be 'master', and 'intensive' for
                            a given year. It defaults to the current year and both master and intensives
        """

        base_url = BASE_URL
        year = str(self.year)

        if self.scope == "master":
            return [f"{base_url}/{year}/"]
        if self.scope == "intensive":
            return [f"{base_url}/intensive/{year}/"]

        return [f"{base_url}/{year}/", f"{base_url}/intensive/{year}/"]

    # this is the end of _urls_for_scope() -----------------------------------------------------------------------------

    def run(self) -> None:
        """
        Starting point for the application.

        :return: None
        """

        try:
            # --- The return value from ReadData.fetch_all_urls is a List[Row], containing all the html from web.
            self.rows = ReadData(
                self.urls, self.year, self.scope, True, self.stations_filter, self.operators
            ).fetch_all_urls()
        except NoSessionsForYearError as e:
            print(f"No sessions found for year {e.year} (scope: {e.scope}).", file=sys.stderr)
            # Option A: return to shell without starting TUI
            return
            # Option B: if you prefer an interactive prompt here, you could
            # ask for a new year before continuing; but you said “immediately”
            # and “without rendering an empty list”, so we exit early.
        except DataFetchFailedError as e:
            print(e, file=sys.stderr)
            if e.errors:
                print("Errors:", file=sys.stderr)
                for line in e.errors:
                    print(f"  - {line}", file=sys.stderr)
            return
        except requests.RequestException as e:
            print(f"Network error while fetching sessions: {e}", file=sys.stderr)
            return

        # If we got here, we have rows — now start curses UI as usual.
        # ... existing curses setup & draw loop ...

        # --- This is the place to recompute HEADER widths
        # --- Compute dynamic column widths once, based on ALL fetched rows
        # --- Set final column widths based on all rows (adds 3 for '[I]' if present)
        # recompute_header_widths(self.rows)

        # --- Applying filter and sort to the list
        self.view_rows = self.fs.apply(
            self.rows,
            _query=self.current_filter,
            _show_removed=self.state.show_removed,
            _sort_key="start",
            _ascending=True,
        )
        recompute_header_widths(self.view_rows)
        # compute_headers(self.view_rows)

        # --- Update self.state, and jump to today
        self.state.selected = self.state.offset = self.fs.index_on_or_after_today(self.view_rows)

        # --- Using curses to call on the main loop, self._curses.main()
        curses.wrapper(self._curses_main)

        # exit(1)
        raise SystemExit(0)  # or: return

    # --- END OF run() -------------------------------------------------------------------------------------------------


# --- END OF class SessionsBrowser -------------------------------------------------------------------------------------
