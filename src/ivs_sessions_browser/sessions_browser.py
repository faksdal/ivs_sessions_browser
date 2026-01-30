# flake8: noqa
# isort: skip_file

"""
Filename:       sessions_browser.py
Author:         jole
Created:        15.09.2025

Description:    Holds class definitions for SessionBrowser along with attributes and methods.
Just some random text to increase the size of the description field.

Notes:
"""

# ──────────────────────────────────────────────────────────────────────────────
# Import section
# ──────────────────────────────────────────────────────────────────────────────
from __future__ import annotations
from bs4        import BeautifulSoup

import curses

# Project defined imports
from .defs                      import HEADERS, IVSCC_BASE_URLS
from .fetch_sessions            import FetchSessions
from .tui    import Tui
from .ivstypes                  import PageData
# ─── END OF Import section ────────────────────────────────────────────────────



class SessionsBrowser:
    """
    Class representing the IVS Sessions Browser.
    Defined in sessions_browser.py.

    """

    def __init__(self, _year: int, _scope: str, _mirrors: bool = False, _filters: str | None = None) -> None:

        # Store user input parameters
        self.year       = _year
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
        fs: FetchSessions = FetchSessions()

        # self.list_html_data_page contains the fetched HTML data for both master and intensive schedules
        self.list_html_data_page = fs.fetch_html_from_urls(self.url_list)
        # ─── END OF Fetch data from web ───────────────────────────────────────

        # ──────────────────────────────────────────────────────────────────────
        # Format and render session data
        # ──────────────────────────────────────────────────────────────────────
        # Create SessionsTuiFormatter instance to format the parsed HTML
        formatter = Tui()

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
            formatter.build_session_list(_soup              = soup,
                                 _num_of_headers    = len(HEADERS) - 1,  # <-- Op is local-only, not on the website
                                 _is_intensive      = is_intensive,
                                 _filters           = self.filters,
                                 _url               = url
                                 )

        print(f"Total sessions parsed: {len(formatter.full_list)}")
        # ─── END OF Format and render session data ────────────────────────────────

    # ─── END OF __init__() ────────────────────────────────────────────────────



    def _urls_for_scope(self, _mirrors: bool) -> list[str]:
        """
        Defined in sessions_browser.py.

        _urls_for_scope() builds the list of urls to download session data from,
        based on the year and scope provided by the user. The list contains both
        primary site, and any mirrors

        Primary and mirror sites are defined in IVSCC_BASE_URLS in defs.py.

        :return: list of string, containing the urls from which we read session data
        and compare last updated timestamps if __mirrors flag is set. We like to
        use the most recently updated data available.
        """

        base_url_list   : list[str] = IVSCC_BASE_URLS
        year            : int       = (int)(self.year)
        retval          : list[str] = []

        if not _mirrors:
            base_url_list = [base_url_list[0]]
            print(f"Using only primary IVSCC site for session data ({IVSCC_BASE_URLS[0]})")
        else:
            print("Reviewing primary and mirror IVSCC sites for the most recently updated session data.")

        if self.scope == "master":
            for base_url in base_url_list:
                retval.append(f"{base_url}/{year}")

        elif self.scope == "intensive":
            for base_url in base_url_list:
                retval.append(f"{base_url}/intensive/{year}")

        elif self.scope == "both":
            for base_url in base_url_list:
                retval.append(f"{base_url}/{year}")
                retval.append(f"{base_url}/intensive/{year}")

        return retval
    # ─── END OF _urls_for_scope() ─────────────────────────────────────────────



    def render_sessions_list(self) -> list[str]:
        """
        Defined in sessions_browser.py.
        Docstring for render_sessions_list

        :return: A list of strings representing the rendered sessions.
        :rtype: list[str]
        """

        lines: list[str] = []
        lines.append(f"IVS Sessions Browser — year={self.year}, scope={self.scope}")
        lines.append(f"Filters: {self.filters}")
        lines.append("Jon Leithe")
        lines.append("(No session rows available in this minimal implementation.)")
        return lines
    # ─── END OF render_sessions_list() ────────────────────────────────────────



    def _curses_main(self, _stdscr) -> None:
        """
        This constitutes the main loop of the application.
        """

        # self.theme              = TUITheme.init_theme() # <- use class, not instance

        # --- Set global has_colors in TUIState instance
        # self.state.has_colors   = curses.has_colors()

        _stdscr.keypad(True)
        curses.curs_set(1)  # --- Hide the cursor
        # curses.use_default_colors()
        # if self.state.has_colors:
            # curses.start_color()
        _stdscr.clear()
        _stdscr.addstr(0, 0, "IVS Sessions Browser - (Curses TUI not implemented in this minimal version)")
        _stdscr.addstr(2, 0, "Jon Leithe")
        _stdscr.addstr(4, 0, "Press any key to exit...")
        _stdscr.refresh()
        _stdscr.getch()

        # --- Start the main loop
        # quit: bool = False
        # while not quit:
            # --- Determine the view height of the current terminal screen
            # max_y, _ = _stdscr.getmaxyx()
            # self.state.view_height = max(1, max_y - 3)

            # self.draw.clear_screen(_stdscr)
            # self.draw.draw_header(_stdscr, self.theme, self.state)

            # --- We pass a filtered list to draw_rows. draw_rows stays "dumb", meaning it just prints whatever
            # --- we send it.
            # self.draw.draw_rows(_stdscr, self.view_rows, self.highlight_tokens, self.theme, self.state)

            # --- Draw a help-bar at thw bottom of the screen
            # self.draw.draw_helpbar(_stdscr, self.view_rows, self.current_filter, self.theme, self.state, self.operator_bindings)

            # --- Parse user input
            # key = _stdscr.getch()
            # match key:
                # case curses.KEY_LEFT:
                    # pass
                    # self.h_off = max(0, self.h_off - 1)
                # case curses.KEY_RIGHT:
                    # pass
                    # self.h_off = self.h_off + 1

                # --- Handles all navigation keys, and [ENTER]
                # case key if key in NAVIGATION_KEYS:
                    # self._navigate(key, _stdscr)

                # -- Catches keystrokes 0-9, used to assign an operator to a session
                # --- Operator assignment: digit 0-9
                # ---  - translate digit -> operator label using operator_bindings
                # ---  - set session_code -> operator label in self.operators
                # ---  - persist immediately so it's available on next startup
                # case c if ord('0') <= c <= ord('5'):
                    # if self.view_rows and 0 <= self.state.selected < len(self.view_rows):
                        # digit = chr(c)
                        # operator_label = self.operator_bindings.get(digit, "")

                        # values, _, _ = self.view_rows[self.state.selected]
                        # code_idx = FIELD_INDEX.get("code", 2)
                        # session_code = values[code_idx] if len(values) > code_idx else ""

                        # if session_code:
                            # self._apply_operator_assignment(session_code, operator_label)
                            # save_operators(self.operators)

                            # Advance selection by one unless we're already on the last row
                            # if self.state.selected < len(self.view_rows) - 1:
                                # self._navigate(curses.KEY_DOWN, _stdscr)

                # --- Jump to today's date (or the next if today is not in list)
                # case c if c == ord('T'):
                    # idx = self.fs.index_on_or_after_today(self.view_rows)
                    # self.state.selected = self.state.offset = idx
                #
                # --- Apply user filter
                # case c if c == ord('/'):
                    # --- If we have a filter already, prefill prompt with it as a convenience to the user
                    # prefill = self.current_filter or ""

                    # --- Get new filter from user
                    # new_filter = self._get_input(_stdscr, self.theme, "/ ", _initial = prefill)

                    # self.current_filter = new_filter
                    # self.view_rows      = self.fs.apply(self.rows,
                                                        # _query           = self.current_filter,
                                                        # _show_removed    = self.state.show_removed,
                                                        # _sort_key        = "start",
                                                        # _ascending       = True,
                                                        # )

                    # --- Jump to today
                    # idx = self.fs.index_on_or_after_today(self.view_rows)
                    # self.state.selected = self.state.offset = idx

                    # --- Highlight stations when filtered
                    # self.highlight_tokens = self.fs.extract_station_tokens(self.current_filter)

                # --- Clear active filters
                # case c if c == (ord('C')):
                    # self._clear_filters()

                # --- Hide/show removed stations
                # case c if c == (ord('R')):
                    # self.state.show_removed = not self.state.show_removed
                    # self.view_rows = self.fs.apply(self.rows,
                                                #    _query           = self.current_filter,
                                                #    _show_removed    = self.state.show_removed,
                                                #    _sort_key        = "start",
                                                #    _ascending       = True)


                # --- Show help
                # case c if c == (ord('?')):
                    # self.draw.show_help(_stdscr, self.theme)

                # --- Print visible range (Ctrl+P)
                # case 16:
                    # self._print_visible_range()

                # --- Quit the script and return to terminal
                # case c if c in (ord('q'), ord('Q')):
                    # quit = True

                # --- Any other key we'll just pass
                # case _:
                    # pass
            # --- END OF match key -------------------------------------------------------------------------------------
        # --- END OF while not quit ------------------------------------------------------------------------------------
    # ─── END OF _curses_main() ────────────────────────────────────────────────



    def run(self, _text: bool = True) -> None:
        """
        Placeholder run method provided by the mixin.
        """

        # --- Using curses to call on the main loop, self._curses.main()
        curses.wrapper(self._curses_main)
    # ─── END OF run() ─────────────────────────────────────────────────────────

# ─── END OF class SessionsBrowser ─────────────────────────────────────────────
