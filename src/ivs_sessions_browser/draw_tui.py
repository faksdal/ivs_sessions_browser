"""
Filename:       draw_tui.py
Author:         jole
Created:        15/09/2025

Description:

Notes:
"""

# --- Import section ---------------------------------------------------------------------------------------------------
import curses
import textwrap

from typing import List

#from repo.scripts.type_defs import WIDTHS
# --- Project defined
#  from .defs      import HEADER_LINE, WIDTHS, FIELD_INDEX, Row, HEADER_DICT, HELP_TEXT
from . import defs as D
from .tui_state import UIState, TUITheme
# --- END OF Import section --------------------------------------------------------------------------------------------



class DrawTUI():
    """
    This one is responsible for all the drawing to screen. By drawing I mean writing...
    """

    def show_help(self, _stdscr, _theme: TUITheme) -> None:
        """
        v2-style centered, boxed help screen. Dismiss with any key.
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

    # --- END OF show_help() ------------------------------------------------------------



    def draw_helpbar(self,
                     _stdscr,
                     _view_rows: D.List[D.Row],
                     _current_filter,
                     _theme,
                     _state
                     ) -> None:
        """
        Draws up the help at the bottom of the terminal

        :param stdscr:  Where to write
        :return:        None
        """

        max_y, max_x = _stdscr.getmaxyx()
        # help_text = "↑↓-PgUp/PgDn-Home/End:Move Enter:Open /:Filter F:Clear filters ?:Help R:Hide/show removed q/Q:Quit"
        help_text = "/:Filter C:Clear filters T: Jump to today R:Hide/show removed ?:Help q/Q:Quit"

        # --- Part of recomputing HEADER widths
        # right = f"row {min(_state.selected + 1, len(_view_rows))}/{len(_view_rows)}"
        right = f"row {min(_state.selected + 1, len(_view_rows))}/{len(_view_rows)}"

        bar = (help_text + (f" Filter: {_current_filter}" if _current_filter else "") + "  " + right)[
            : max_x - 1]
        bar_attr = _theme.help_bar if _state.has_colors else _theme.reversed
        self._addstr_clip(_stdscr, max_y - 1, 0, bar, bar_attr)
    # --- END OF _draw_helpbar() ---------------------------------------------------------------------------------------



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
            x += D.WIDTHS[i] + sep
        return x
    # --- END OF _col_start_x() ----------------------------------------------------------------------------------------



    def draw_rows(self,
                  _stdscr,
                  _rows:                D.List[D.Row],
                  _highlight_tokens:    List[str],
                  _theme:               TUITheme,
                  _state:               UIState
                  ) -> None:
        """
        Draws all the rows to terminal

        :param _stdscr:  Which screen to draw on
        :return:        None
        """

        # --- Normalize state attributes if we're outside view boundaries.
        if _state.selected < _state.offset:
            _state.offset = _state.selected
        elif _state.selected >= _state.offset + _state.view_height:
            _state.offset = _state.selected - _state.view_height + 1

        # --- Let the user know if we have nothing to show.
        if not _rows:
            self._addstr_clip(_stdscr, 2, 0, "No sessions found.")
            return

        # --- Draw each visible row to terminal
        for i in range(_state.offset, min(len(_rows), _state.offset + _state.view_height)):
            row_vals, _, meta = _rows[i]

            # --- Copy, so we can override Stations column safely
            vals = list(row_vals)

            # --- If the user has chosen to hide removed stations, render only active in "stations" column (5)
            if not _state.show_removed:
                active_only         = meta.get("active", "")
                field_index: int    = D.FIELD_INDEX.get("stations", -1)
                vals[field_index]   = f"{active_only:<{D.WIDTHS[field_index]}}"

            # --- Construct full lines from parts
            ### Changed some when I put in HEADER length recomputing
            ### The following lines are replaced
            # parts       = [f"{val:<{D.WIDTHS[c]}}" for c, val in enumerate(vals)]
            # full_line   = " | ".join(parts)

            ### By these:
            # --- Construct full line with a special rule for the "Type" column:
            # --- left-justify the type text in (width-3)
            # --- put "[I]" flush-right if meta["intensive"] is true
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

                # if c == D.FIELD_INDEX["type"] and meta.get("intensive"):
                #     base_width = D.WIDTHS[c] - 3  # room for [I]
                #     formatted = f"{val:<{base_width}} [I]"
                # else:
                #     formatted = f"{val:<{D.WIDTHS[c]}}"
                # parts.append(formatted)

            full_line = " | ".join(parts)

            y           = i - _state.offset + 2
            row_attr    = _theme.reversed if i == _state.selected else 0

            # --- We only color the rows if _state.has_colors are set to True. This is done by checking
            # --- curses if curses.has_colors() in SessionsBrowser._curses_main()
            row_color = self._status_color(_state.has_colors, vals[D.FIELD_INDEX.get("status", -1)], _theme)
            self._addstr_clip(_stdscr, y, 0, full_line, row_attr | row_color)

            # --- Highlight "[...]" in 'stations' column only if we are showing removed stations, after the active ones
            if _state.has_colors and vals[D.FIELD_INDEX.get("stations", -1)]:
                stations_offset = full_line.find(vals[D.FIELD_INDEX.get("stations", -1)])
                lbr = full_line.find("[", stations_offset)
                if lbr != -1:
                    rbr = full_line.find("]", lbr + 1)
                    if rbr != -1 and rbr > lbr:
                        self._addstr_clip(_stdscr, y, lbr, full_line[lbr:rbr + 1], row_attr | _theme.removed)

            # --- Highlight intensives. They are found in the "Type" column, which spans full_line[0:13]
            # --- Length of "Type" column can be determined with length = HEADER_DICT["Type"]
            search_length = D.HEADER_DICT["Type"]
            if _state.has_colors:
                lbr = full_line.find("[", 0, search_length)
                if lbr != -1:
                    rbr = full_line.find("]", lbr + 1)
                    if rbr != -1 and rbr > lbr:
                        self._addstr_clip(_stdscr, y, lbr, full_line[lbr:rbr + 1], row_attr | _theme.intensives)

            # --- Station token highlighting (from stations:Xx filter)
            if vals[D.FIELD_INDEX.get("stations", -1)] and _highlight_tokens:
                # --- Padded field text as printed
                stations_text = vals[D.FIELD_INDEX.get("stations", -1)]

                # --- "stations" field index
                col_x = self._col_start_x(D.FIELD_INDEX.get("stations", -1))

                # --- Fallback without colors: underline+bold (shows even on selected/reversed rows)
                hl_attr = (_theme.filtered | curses.A_BOLD) if _state.has_colors else (curses.A_BOLD | curses.A_UNDERLINE)
                for tok in _highlight_tokens:
                    start = 0
                    while True:
                        j = stations_text.find(tok, start)
                        if j == -1:
                            break
                        self._addstr_clip(_stdscr, y, col_x + j, tok, row_attr | hl_attr)
                        start = j + len(tok)
        # --- END OF for i in range ------------------------------------------------------------------------------------
    # --- END OF _draw_rows() ------------------------------------------------------------------------------------------



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

        self._addstr_clip(_stdscr, 0, 0, D.HEADER_LINE, _theme.header)
        self._addstr_clip(_stdscr, 1, 0, "-" * len(D.HEADER_LINE))

        # self._addstr_clip(_stdscr, 3, 0, "Jon Leithe", _theme.header)
    # --- END OF draw_header -------------------------------------------------------------------------------------------



    def _status_color(self, _has_colors: bool, _status_text: str, _theme: TUITheme) -> int:
        """
        Map status text to a curses color pair.
        """

        if not _has_colors:
            return _theme.none
        st = _status_text.strip().lower()
        if "released" in st:
            return _theme.released
            # return curses.color_pair(4)
        if any(k in st for k in ("waiting on media", "ready for processing", "cleaning up", "processing session")):
            return _theme.processing
            # return curses.color_pair(5)

        # --- Handle both spellings...
        if "cancelled" in st or "canceled" in st:
            # return curses.color_pair(6)
            return _theme.cancelled
        if st == "":
            # return curses.color_pair(7)
            return _theme.none
        return 0
    # --- END OF _status_color() ---------------------------------------------------------------------------------------



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
    # --- END OF _addstr_clip() ----------------------------------------------------------------------------------------



    def clear_screen(self, _stdscr) -> None:
        """
        Clears the screen _stdscr

        :return: None
        """

        _stdscr.clear()
    # --- END OF clear_screen ------------------------------------------------------------------------------------------

# --- END OF class DrawTUI ---------------------------------------------------------------------------------------------