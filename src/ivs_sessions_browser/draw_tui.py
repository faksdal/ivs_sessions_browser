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
from .defs import Row, HEADER_LINE, HELPBAR_TEXT
from .ui_state import UIState
# --- END OF Import section --------------------------------------------------------------------------------------------



class DrawTui(Protocol):
    """
    This one is responsible for all the drawing to screen. By drawing I mean writing...
    """

    # def draw(self, stdscr, rows: Sequence[str], state: UiState) -> None: ...

    # def read_event(self, stdscr) -> Optional[Event]: ...  # translate keys -> Event
    def draw_header(self,
                    _stdscr,
                    _rows: Sequence[str],
                    _state: UIState) -> None:
        """
        Draws up the header line on top of the terminal window using curses.
        Sets up the test to write, and the attributes for the text.
        Writes the header line and the dotted line underneath, at the top of the terminal

        :param stdscr:  Which screen to draw on

        :return:        None
        """

        header_attributes = curses.A_BOLD | (curses.color_pair(2) if _state.has_colors else 0)
        DrawTui._addstr_clip(_stdscr, 0, 0, HEADER_LINE, header_attributes)
        DrawTui._addstr_clip(stdscr, 1, 0, "-" * len(HEADER_LINE))
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
        _stdscr.addstr(y, x, _text[: max_x - x - 1], _attr)

    # --- END OF _addstr_clip() ----------------------------------------------------------------------------------------



    def clear_screen(_stdscr) -> None:
        """
        Clears the screen _stdscr

        :return: None
        """

        _stdscr.clear()
    # --- END OF clear_screen ------------------------------------------------------------------------------------------