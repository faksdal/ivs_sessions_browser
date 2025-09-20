"""
Filename:       sessions_browser.py
Author:         jole
Created:        15.09.2025

Description:    Holds class definitions for SessionBrowser along with attributes and methods.

Notes:
"""

# --- Import section ---------------------------------------------------------------------------------------------------
import sys
import requests

from typing     import Optional, List
# from datetime   import datetime


# --- Project defined
from .draw_tui          import DrawTUI
from .defs              import BASE_URL, Row, NAVIGATION_KEYS, recompute_header_widths
from .read_data         import ReadData, NoSessionsForYearError, DataFetchFailedError
from .tui_state         import *
from .filter_and_sort   import FilterAndSort
# --- END OF Import section --------------------------------------------------------------------------------------------



class SessionsBrowser:
    """
    SessionBrowser holds the logic for the whole application, it keeps everything together!

    Application execution steps:
        - Get data from url's depending on the value in self.scope.
        - Display organized data as lines, supporting navigation with keyboard in terminal.
        - Run the loop, catching users input and act appropriately.
    """

    def __init__(self,
                 _year:             int,
                 _scope:            str,
                 _stations_filter:  Optional[str] = None
                 ) -> None:
        self.year               = _year
        self.scope              = _scope
        self.stations_filter    = _stations_filter
        self.state              = UIState()
        self.theme: TUITheme    = None
        self.draw: DrawTUI      = DrawTUI()

        # --- Create and populate the list of url's we want to download from.
        self.urls: List[str]    = self._urls_for_scope()

        # --- self.rows contains all rosw read from web
        # --- self.view_rows contains the filtered list
        self.rows:      List[Row]   = []    # populated in run()
        self.view_rows: List[Row]   = []

        # --- Tokens to highlight in the stations column when filtering
        self.highlight_tokens: List[str] = []

        # --- Holds the current filter as input by user
        self.current_filter: str = ""

        self.fs = FilterAndSort()
    # --- END OF __init__() --------------------------------------------------------------------------------------------



    def _clear_filters(self) -> None:
        """
        Clears all active filters

        :return: None
        """
        self.current_filter = ""
        self.view_rows = self.rows
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
            visible_text = text[scroll:scroll + text_space]
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
                self.state.selected = 0;
            case curses.KEY_END:
                self.state.selected = max(0, len(self.view_rows) - 1)
            # case 10 | 13 | curses.KEY_ENTER:
            #     if self.view_rows:
            #         _, url, _ = self.view_rows[self.state.selected]
            #         if url:
            #             webbrowser.open(url)
            case _:
                pass
    # --- END OF _navigate() -------------------------------------------------------------------------------------------



    def _curses_main(self, _stdscr) -> None:
        """
        This constitutes the main loop of the application.
        """

        self.theme              = TUITheme.init_theme() # <- use class, not instance

        # --- Set global has_colors in TUIState instance
        self.state.has_colors   = curses.has_colors()

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
            self.draw.draw_rows(_stdscr, self.view_rows, self.highlight_tokens, self.theme, self.state)

            # --- Draw a help-bar at thw bottom of the screen
            self.draw.draw_helpbar(_stdscr, self.view_rows, self.current_filter, self.theme, self.state)

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

                # --- Jump to today's date (or the next if today is not in list)
                case c if c == ord('T'):
                    idx = self.fs.index_on_or_after_today(self.view_rows)
                    self.state.selected = self.state.offset = idx
                #
                # --- Apply user filter
                case c if c == ord('/'):

                    # --- If we have a filter already, prefill prompt with it as a convenience to the user
                    prefill = self.current_filter or ""

                    # --- Get new filter from user
                    new_filter = self._get_input(_stdscr, self.theme, "/ ", _initial = prefill)

                    self.current_filter = new_filter
                    self.view_rows      = self.fs.apply(self.rows,
                                                        _query           = self.current_filter,
                                                        _show_removed    = self.state.show_removed,
                                                        _sort_key        = "start",
                                                        _ascending       = True,
                                                        )

                    # --- Jump to today
                    idx = self.fs.index_on_or_after_today(self.view_rows)
                    self.state.selected = self.state.offset = idx

                    # --- Highlight stations when filtered
                    self.highlight_tokens = self.fs.extract_station_tokens(self.current_filter)

                # --- Clear active filters
                case c if c == (ord('C')):
                    self._clear_filters()

                # --- Hide/show removed stations
                case c if c == (ord('R')):
                    self.state.show_removed = not self.state.show_removed
                    self.view_rows = self.fs.apply(self.rows,
                                                   _query           = self.current_filter,
                                                   _show_removed    = self.state.show_removed,
                                                   _sort_key        = "start",
                                                   _ascending       = True)


                # --- Show help
                case c if c == (ord('?')):
                    self.draw.show_help(_stdscr, self.theme)

                # --- Quit the script and return to terminal
                case c if c in (ord('q'), ord('Q')):
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

        base_url    = BASE_URL
        year        = str(self.year)

        if self.scope == "master":      return [f"{base_url}/{year}/"]
        if self.scope == "intensive":   return [f"{base_url}/intensive/{year}/"]

        return [f"{base_url}/{year}/", f"{base_url}/intensive/{year}/"]
    # this is the end of _urls_for_scope() -----------------------------------------------------------------------------



    def run(self) -> None:
        """
        Starting point for the application.

        :return: None
        """

        try:
            # --- The return value from ReadData.fetch_all_urls is a List[Row], containing all the html from web.
            self.rows = ReadData(self.urls, self.year, self.scope, True, self.stations_filter).fetch_all_urls()
        except NoSessionsForYearError as e:
            print(f"No sessions found for year {e.year} (scope: {e.scope}).", file=sys.stderr)
            # Option A: return to shell without starting TUI
            return
            # Option B: if you prefer an interactive prompt here, you could
            # ask for a new year before continuing; but you said “immediately”
            # and “without rendering an empty list”, so we exit early.
        except DataFetchFailedError as e:
            print(e, file = sys.stderr)
            if e.errors:
                print("Errors:", file = sys.stderr)
                for line in e.errors:
                    print(f"  - {line}", file = sys.stderr)
            return
        except requests.RequestException as e:
            print(f"Network error while fetching sessions: {e}", file = sys.stderr)
            return

        # If we got here, we have rows — now start curses UI as usual.
        # ... existing curses setup & draw loop ...

        # --- This is the place to recompute HEADER widths
        # --- Compute dynamic column widths once, based on ALL fetched rows
        # --- Set final column widths based on all rows (adds 3 for '[I]' if present)
        # recompute_header_widths(self.rows)

        # --- Applying filter and sort to the list
        self.view_rows = self.fs.apply(self.rows,
                                       _query           = self.current_filter,
                                       _show_removed    = self.state.show_removed,
                                       _sort_key        = "start",
                                       _ascending       = True)
        recompute_header_widths(self.view_rows)

        # --- Update self.state, and jump to today
        self.state.selected = self.state.offset = self.fs.index_on_or_after_today(self.view_rows)

        # --- Using curses to call on the main loop, self._curses.main()
        curses.wrapper(self._curses_main)

        exit(1)
    # --- END OF run() -------------------------------------------------------------------------------------------------

# --- END OF class SessionsBrowser -------------------------------------------------------------------------------------


