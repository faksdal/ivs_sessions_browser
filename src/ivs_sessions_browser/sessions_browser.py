"""
Filename:       sessions_browser.py
Author:         jole
Created:        15.09.2025

Description:    Holds class definitions for SessionBrowser along with attributes and methods.

Notes:
"""

# --- Import section ---------------------------------------------------------------------------------------------------
import curses

from typing     import Optional, List


# --- Project defined
from .draw_tui  import DrawTUI
from .defs      import BASE_URL, Row
from .read_data import ReadData
from .ui_state  import *
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
                 _year: int,
                 _scope: str,
                 _stations_filter: Optional[str] = None
                 ) -> None:
        self.year               = _year
        self.scope              = _scope
        self.stations_filter    = _stations_filter
        self.state              = UIState()

        # --- Create and populate the list of url's we want to download from.
        self.urls: List[str]    = self._urls_for_scope()

        # --- Create the list of html data that are actually read
        # self.data: ReadData     = ReadData(self.urls, self.year, self.scope, True, self.stations_filter)
        # print("SessionBrowser before read")
        self.rows: List[Row]    = [] # ReadData(self.urls, self.year, self.scope, True, self.stations_filter).fetch_all_urls()


        # --- Instance of DrawTui class to handle all the screen drawing. All drawing operations will be called using
        # --- this instance. This is done to have to code outside of the main loop (this class, SessionBrowser, is
        # --- considered the main loop). Other attributes related to drawing are also defined here.
        # self.tui: DrawTui   = DrawTui()
        # self.h_off: int     = 0
    # --- END OF __init__() --------------------------------------------------------------------------------------------



    def _curses_main(self, _stdscr) -> None:
        """
        This constitutes the main loop of the application.
        """

        # --- Hide the cursor in the terminal
        curses.curs_set(0)

        # --- Clear the terminal window
        _stdscr.clear()

        # --- Set up the colors, if any are available
        # self.has_colors = curses.has_colors()
        # if self.has_colors:
        #     self.tui.set_colors(curses)

        # --- Start the main loop
        quit: bool = False
        while not quit:
            DrawTUI.clear_screen(_stdscr)
            DrawTUI.draw_header(self,
                                _stdscr,
                                self.rows,
                                self.state)

            # self.tui.draw_header(curses, _stdscr)
            #
            # self.tui._draw_helpbar(curses, _stdscr)

            # bar_y = y + 1  # or your status line row
            # width = _stdscr.getmaxyx()[1] - x - 1
            # self.tui._draw_hscrollbar(_stdscr, bar_y, x, len(text), width, self.h_off)

            # self._draw_rows(stdscr)


            key = _stdscr.getch()
            match key:


                # elif ch in (curses.KEY_LEFT, ord('h')):
                #     self.h_off = max(0, self.h_off - 1)
                # elif ch in (curses.KEY_RIGHT, ord('l')):
                #     self.h_off = self.h_off + 1  # clamped after render

                case curses.KEY_LEFT:
                    pass
                    # self.h_off = max(0, self.h_off - 1)
                case curses.KEY_RIGHT:
                    pass
                    # self.h_off = self.h_off + 1

                # # --- Handles all navigation keys, and enter
                # case key if key in NAVIGATION_KEYS:
                #     self._navigate(key, stdscr)
                #
                # # --- Jump to today's date (or the next if today is not in list)
                # case c if c == ord('T'):
                #     self._jump_to_today()
                #
                # # --- Apply user filter
                # case c if c == ord('/'):
                #
                #     prefill = self.current_filter or ""
                #     q = self._get_input(stdscr, "/ ", initial=prefill)
                #
                #     self.current_filter = q;
                #     self.view_rows = self._apply_filter(q)
                #
                #     self.highlight_tokens = self._extract_station_tokens(self.current_filter)
                #
                #     idx = self._index_on_or_after_today(self.view_rows)
                #     self.selected = idx
                #     self.offset = idx
                #
                # # --- Clear active filters
                # case c if c == (ord('F')):
                #     self._clear_filters()
                #
                # # --- Hide/show removed stations
                # case c if c == (ord('R')):
                #     self.show_removed = not self.show_removed
                #
                # # --- Show help
                # case c if c == (ord('?')):
                #     self._show_help(stdscr)

                # --- Quit the script and return to terminal
                case c if c in (ord('q'), ord('Q')):
                    quit = True

                # --- Any other key we'll just pass
                case _:
                    pass
            # --- END OF match key -------------------------------------------------------------------------------------
        # --- END OF while not quit ------------------------------------------------------------------------------------
    # --- END OF _curses_main() ----------------------------------------------------------------------------------------



    def run(self) -> None:
        """
        Starting point for the application.

        :return: None
        """

        # --- The return value from fetch_all_urls is a List[Row], containing all the html from web.
        data = ReadData(self.urls, self.year, self.scope, True, self.stations_filter)
        self.rows = data.fetch_all_urls()


        # todo: list must be sorted

        # --- Using curses to call on the main loop, self._curses.main()
        curses.wrapper(self._curses_main)

        exit(1)
    # --- END OF run() -------------------------------------------------------------------------------------------------



    def _urls_for_scope(self) -> List[str]:
        """
        Constructing the list of URL's to read from, based on the users input at terminal.

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



    def _draw_hscrollbar(self,
                         _stdscr,
                         _y: int,
                         _x: int,
                         total_len: int,
                         width: int,
                         _h_off: int,
                         _track_attr = 0,
                         _thumb_attr = 0):
        """
        Draw a proportional scrollbar for one line of text.
        Put it on a status line or just below the scrolled text.
        """

        max_y, max_x = _stdscr.getmaxyx()
        if _y >= max_y or width <= 0 or total_len <= width:
            return

        # track
        try:
            _stdscr.hline(_y, _x, curses.ACS_HLINE, max(0, width))
        except Exception:
            _stdscr.addstr(_y, _x, "-" * max(0, width), _track_attr)

        # thumb size/pos
        thumb_len = max(1, (width * width) // max(1, total_len))
        max_thumb_pos = max(0, width - thumb_len)
        max_off = max(0, total_len - width)
        thumb_pos = (0 if max_off == 0 else (_h_off * max_thumb_pos) // max_off)

        # draw thumb as reversed spaces (easy to see)
        _stdscr.addstr(_y, _x + thumb_pos, " " * thumb_len,
                       _thumb_attr or curses.A_REVERSE)
        # --- END OF _draw_hscrollbar() --------------------------------------------------------------------------------
# --- END OF class SessionsBrowser -------------------------------------------------------------------------------------


