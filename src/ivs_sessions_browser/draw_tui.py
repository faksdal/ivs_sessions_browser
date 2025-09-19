"""
Filename:       draw_tui.py
Author:         jole
Created:        15/09/2025

Description:

Notes:
"""

# --- Import section ---------------------------------------------------------------------------------------------------
import curses

from typing import Protocol, Sequence

# --- Project defined
from .defs      import HEADER_LINE, HELPBAR_TEXT
from .tui_state import UIState, TUITheme
# --- END OF Import section --------------------------------------------------------------------------------------------



class DrawTUI(Protocol):
    """
    This one is responsible for all the drawing to screen. By drawing I mean writing...
    """

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



    def draw_rows(self,
                  _stdscr,
                  _rows:    Sequence[str],
                  _state:  UIState,
                  _theme:   TUITheme) -> None:
        """
        Draws all the rows to terminal

        :param _stdscr:  Which screen to draw on
        :return:        None
        """

        # --- Determine the view height of the current terminal screen
        max_y, _    = _stdscr.getmaxyx()
        view_height = max(1, max_y - 3)

        # --- Normalize state attributes if we're outside view boundaries.
        if _state.selected < _state.offset:
            _state.offset = _state.selected
        elif _state.selected >= _state.offset + view_height:
            _state.offset = _state.selected - view_height + 1

        # --- Let the user know if we have nothing to show.
        if not self.view_rows:
            self._addstr_clip(_stdscr, 2, 0, "No sessions found.")
            return

        # # --- Draw each visible row to terminal
        # for i in range(self.offset, min(len(self.view_rows), self.offset + view_height)):
        #
        #     row_vals, _, meta = self.view_rows[i]
        #
        #     # --- Copy, so we can override Stations column safely
        #     vals = list(row_vals)
        #
        #     # --- If the user has chosen to hide removed stations, render only active in column 5
        #     # --- Column 5 is best accessed as index = FIELD_INDEX.get("stations", -1)
        #     if not self.show_removed:
        #         active_only = meta.get("active", "")
        #         field_index: int = FIELD_INDEX.get("stations", -1)
        #         vals[field_index] = f"{active_only:<{WIDTHS[field_index]}}"
        #
        #     # --- Construct full lines from parts
        #     parts       = [f"{val:<{WIDTHS[c]}}" for c, val in enumerate(vals)]
        #     full_line   = " | ".join(parts)
        #     y           = i - self.offset + 2
        #     row_attr    = curses.A_REVERSE if i == self.selected else 0
        #
        #     row_color = self._status_color(self.has_colors, vals[FIELD_INDEX.get("status", -1)])
        #     self._addstr_clip(_stdscr, y, 0, full_line, row_attr | row_color)
        #
        #     # [REMOVED] --- Highlight "[...]" only if we are showing removed stations, after the active ones
        #     # --- This has changed: as a side effect, intensives that are also marked with [], will be
        #     # --- colored by the same color as removed stations (becasue of the []. This is for convenience; in later
        #     # --- versions intensives and removed should have separate colors.
        #     # if self.has_colors and self.show_removed and vals[FIELD_INDEX.get("stations", -1)]:
        #     if self.has_colors and vals[FIELD_INDEX.get("stations", -1)]:
        #         lbr = full_line.find("[")
        #         if lbr != -1:
        #             rbr = full_line.find("]", lbr + 1)
        #             if rbr != -1 and rbr > lbr:
        #                 self._addstr_clip(_stdscr, y, lbr, full_line[lbr:rbr + 1], row_attr | curses.color_pair(1))
        #
        #     # --- Station token highlighting (from stations:* filter)
        #     if vals[FIELD_INDEX.get("stations", -1)] and self.highlight_tokens:
        #         # --- Padded field text as printed
        #         stations_text = vals[FIELD_INDEX.get("stations", -1)]
        #
        #         # --- "stations" field index
        #         col_x = self._col_start_x(FIELD_INDEX.get("stations", -1))
        #
        #         # --- Fallback without colors: underline+bold (shows even on selected/reversed rows)
        #         hl_attr = (curses.color_pair(8) | curses.A_BOLD) if self.has_colors else (
        #                 curses.A_BOLD | curses.A_UNDERLINE)
        #         for tok in self.highlight_tokens:
        #             start = 0
        #             while True:
        #                 j = stations_text.find(tok, start)
        #                 if j == -1:
        #                     break
        #                 self._addstr_clip(_stdscr, y, col_x + j, tok, row_attr | hl_attr)
        #                 start = j + len(tok)

        # --- END OF for i in range ------------------------------------------------------------------------------------
    # --- END OF _draw_rows() ------------------------------------------------------------------------------------------



    def draw_header(_stdscr,
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

        DrawTUI._addstr_clip(_stdscr, 0, 0, HEADER_LINE, _theme.header)
        DrawTUI._addstr_clip(_stdscr, 1, 0, "-" * len(HEADER_LINE))
    # --- END OF draw_header -------------------------------------------------------------------------------------------



    def _addstr_clip(_stdscr, _y: int, _x: int, _text: str, _attr: int = 0) -> None:
        """
        Writes a string to terminal, clipping if necessary

        :param stdscr:  Which screen to write to
        :param y:       y co-ordinate
        :param x:       x co-ordinate
        :param text:    What to write
        :param attr:    Text attributes

        :return:        None
        """

        max_y, max_x = _stdscr.getmaxyx()
        if _y >= max_y or _x >= max_x:
            return

        _stdscr.addstr(_y, _x, _text[: max_x - _x - 1], _attr)
    # --- END OF _addstr_clip() ----------------------------------------------------------------------------------------



    def clear_screen(_stdscr) -> None:
        """
        Clears the screen _stdscr

        :return: None
        """

        _stdscr.clear()
    # --- END OF clear_screen ------------------------------------------------------------------------------------------

# --- END OF class DrawTUI ---------------------------------------------------------------------------------------------