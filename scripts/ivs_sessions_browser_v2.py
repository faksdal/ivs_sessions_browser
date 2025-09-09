#! ../.venv/bin/python3
# --- This is a re-write of the ivs_sessions_browser.py script
#
# --- jole 2025

## Import section ######################################################################################################
import argparse
import curses
# import requests
# import logging
# from bs4                import BeautifulSoup
from typing             import Optional, List, Tuple, Dict, Any
from datetime           import datetime, date
from log_helper         import *
from url_helper         import URLHelper
# from session_parser     import SessionParser
from type_defs          import (Row,
                                FIELD_INDEX,
                                HEADERS,
                                HEADER_LINE,
                                WIDTHS,
                                ARGUMENT_DESCRIPTION,
                                ARGUMENT_EPILOG,
                                ARGUMENT_FORMATTER_CLASS
                               )
from sort_and_filter    import SortAndFilter
## END OF Import section ###############################################################################################



# --- class definition -------------------------------------------------------------------------------------------------
#class SessionBrowser(SessionParser):
class SessionBrowser:
    """
    Class SessionBrowser
    """

    # --- __init__() function, or constructor if you like since I come from c/c++ ----------------------------------------
    def __init__(self,
                 _year: int,
                 _logger: logging.Logger,
                 _scope: str = "both",
                 _stations_filter: Optional[str] = None,
                 _sessions_filter: Optional[str] = None,
                 ) -> None:
        # assigning all parameters to local instance vars
        self.year               = _year
        self.logger             = _logger
        self.scope              = _scope
        self.stations_filter    = _stations_filter
        self.sessions_filter    = _sessions_filter

        # define and initialize some instance attributes ###############################################################
        self.rows:              List[Row]   = []
        self.view_rows:         List[Row]   = []
        self.current_filter:    str         = ""
        self.selected:          int         = 0
        self.offset:            int         = 0
        self.has_colors:        bool        = False
        self.show_removed:      bool        = False # --- flag for showing/hiding removed sessions in the list
        self.highlight_tokens:  List[str]   = []    # --- tokens to highlight in the stations column when filtering
        ################################################################################################################
    # this is the end of __init__() ------------------------------------------------------------------------------------



    # todo: Decide where to put this. I'm not yet quite sure what is does.
    # --- computes the x offset where column _col_idx starts in the printed line
    # --- each column is printed left-padded to WIDTHS[c], joined by " | " (3 chars)
    def _col_start_x(self, _col_idx: int) -> int:
        sep = 3
        x   = 0
        for i in range(_col_idx):
            x += self.WIDTHS[i] + sep
        return x
    # this is the end of _col_start_x() ################################################################################



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
        4=green(released), 5=yellow(processing/waiting), 6=magenta(cancelled), 7=red(none).
        """

        if not _has_colors:
            return 0
        st = _status_text.strip().lower()
        if "released" in st:
            return curses.color_pair(4)
        if any(k in st for k in ("waiting on media", "ready for processing", "cleaning up", "processing session")):
            return curses.color_pair(5)
        if "cancelled" in st or "canceled" in st:  # handle both spellings
            return curses.color_pair(6)
        if st == "":
            return curses.color_pair(7)
        return 0
    # --- END OF _status_color() ----------------------------------------------------------------------------------------

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

        self.logger.debug(f"self.offset: {self.offset}")
        self.logger.debug(f"self.selected: {self.selected}")

        # --- Let the user know if we have nothing to show
        if not self.view_rows:
            self._addstr_clip(stdscr, 2, 0, "No sessions found.")
            return

        # --- Draw each visible row to terminal
        # self.logger.debug(f"self.offset: {self.offset}")
        # self.logger.debug(f"min(len(self.view_rows), self.offset + view_height): {min(len(self.view_rows), self.offset + view_height)}")
        # self.logger.debug(f"self.offset + view_height: {self.offset + view_height}")
        for i in range(self.offset, min(len(self.view_rows), self.offset + view_height)):

            row_vals, _, meta = self.view_rows[i]

            # --- Copy, so we can override Stations column safely
            vals = list(row_vals)

            # --- If the user has chosen to hide removed stations, render only active in column 5
            # --- Column 5 is best accessed as index = FIELD_INDEX.get("stations", -1)
            if not self.show_removed:
                active_only = meta.get("active", "")
                vals[FIELD_INDEX.get("stations", -1)] = f"{active_only:<{WIDTHS[FIELD_INDEX.get("stations", -1)]}}"

            # --- Construct full lines from parts
            parts       = [f"{val:<{WIDTHS[c]}}" for c, val in enumerate(vals)]
            full_line   = " | ".join(parts)
            y           = i - self.offset + 2
            row_attr    = curses.A_REVERSE if i == self.selected else 0

            row_color = self._status_color(self.has_colors, vals[FIELD_INDEX.get("status", -1)])
            self._addstr_clip(stdscr, y, 0, full_line, row_attr | row_color)

            # --- Highlight "[...]" only if we are showing removed stations, after the active ones
            if self.has_colors and self.show_removed and vals[FIELD_INDEX.get("stations", -1)]:
                lbr = full_line.find("[")
                if lbr != -1:
                    rbr = full_line.find("]", lbr + 1)
                    if rbr != -1 and rbr > lbr:
                        self._addstr_clip(stdscr, y, lbr, full_line[lbr:rbr + 1], row_attr | curses.color_pair(1))

            # --- Station token highlighting (from stations:* filter)
            if vals[FIELD_INDEX.get("stations", -1)] and self.highlight_tokens:
                stations_text = vals[FIELD_INDEX.get("stations", -1)]        # padded field text as printed
                col_x = self._col_start_x(FIELD_INDEX.get("stations", -1))  # "stations" field index

                # Fallback without colors: underline+bold (shows even on selected/reversed rows)
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
        help_text = "↑↓ Move  PgUp/PgDn  Home/End  Enter Open  '/' Filter  T Today  F ClearFilter R Show/hide removed  ? Help  q Quit  stations: AND(&) OR(|)  "
        right = f"row {min(self.selected + 1, len(self.view_rows))}/{len(self.view_rows)}"
        bar = (help_text + (f"filter: {self.current_filter}" if self.current_filter else "") + "  " + right)[
            : max_x - 1]
        bar_attr = curses.color_pair(3) if self.has_colors else curses.A_REVERSE
        self._addstr_clip(stdscr, max_y - 1, 0, bar, bar_attr)
    # --- END OF _draw_helpbar() ---------------------------------------------------------------------------------------

    def _curses_main(self, stdscr) -> None:

        # --- hide the cursor in the terminal
        curses.curs_set(0)

        # --- clear the terminal window
        stdscr.clear()

        # --- Set up the colors, if any are available
        self.has_colors = curses.has_colors()
        if self.has_colors:
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_YELLOW, -1)                # removed stations
            curses.init_pair(2, curses.COLOR_CYAN, -1)                  # header
            curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE) # help bar
            curses.init_pair(4, curses.COLOR_GREEN, -1)                 # released
            curses.init_pair(5, curses.COLOR_YELLOW, -1)                # processing
            curses.init_pair(6, curses.COLOR_MAGENTA, -1)               # cancelled
            curses.init_pair(7, curses.COLOR_WHITE, -1)                 # none
            curses.init_pair(8, curses.COLOR_CYAN, -1)                  # station highlight in filter

        # --- start the main loop
        quit = False
        while not quit:
            stdscr.clear()
            self._draw_header(stdscr)
            self._draw_rows(stdscr)
            self._draw_helpbar(stdscr)

            ch = stdscr.getch()
            match ch:
                case curses.KEY_UP if self.selected > 0:
                    self.selected -= 1
                case curses.KEY_DOWN if self.selected < len(self.view_rows) -1:
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

                case c if c in (ord('q'), ord('Q'), 27):
                    quit = True

                case _:
                    pass
            # --- END OF match ch --------------------------------------------------------------------------------------

        # --- END OF while not quit ----------------------------------------------------------------------------------------


    # --- END OF _curses_main() ----------------------------------------------------------------------------------------



    def run(self) -> None:
        """
        SessionBrowser.run() - This is what the user calls to run the loop.

        :return: None
        """

        # --- Create some local attributes to help us maintain the items list and TUI view
        saf:    SortAndFilter   = SortAndFilter(self.logger, self.stations_filter, self.sessions_filter)

        # Get data from web, and store in 'html', using functionality from 'URLHelper' class
        # We must differentiate between master and intensives, because we want to mark the intensives

        # --- fetch all items from web, based on year, scope, stations filter and sessions filter
        url_helper: URLHelper   = URLHelper(self.logger,
                                            self.year,
                                            self.scope,
                                            self.stations_filter,
                                            self.sessions_filter)
        self.rows  = url_helper.fetch_all_urls()
        # saf     = SortAndFilter(self.logger, self.stations_filter, self.sessions_filter)
        # --- items are mixed by default, since we've read from both master and intensives, potentially, thus a sort
        # --- in chronological order is needed
        self.rows  = saf.sort_by_start(self.rows)

        self.view_rows = list(self.rows)

        idx             = self._index_on_or_after_today(self.view_rows)
        self.selected   = idx;
        self.offset     = idx;

        # --- using curses to call on the main loop, self._curses.main()
        curses.wrapper(self._curses_main)

# --- END OF class SessionBrowser definition ------------------------------------------------------------------------------------------



def main() -> None:
    """
    main()

    :return:    None
    """

    # --- define an argument parser for the user's convenience
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
                            help    ="Initial filter for stations:")

    args = arg_parser.parse_args()

    from log_setup import log_filename
    # logger = setup_logger(filename = log_filename, to_stdout = False)
    logger = setup_logger(filename=log_filename)
    logger.info("Script started...")

    # sb = SessionBrowser(_year=args.year, _logger=logger, _scope=args.scope, _stations_filter=args.stations).run()
    SessionBrowser(_year=args.year, _logger=logger, _scope=args.scope, _stations_filter=args.stations).run()

    # print(sb.__dict__)
    # sb.fetch_data_from_web()



if __name__ == "__main__":
    main()
