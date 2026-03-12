"""
Filename:       ui_state.py
Author:         jole
Created:        16.09.2025
Description:

Notes:
"""

import curses

from dataclasses import dataclass, field



@dataclass
class UIState:
    """
        Helper dataclass to hold all variables used for keeping tabs on the navigation in the list. Whenever the
    user moves around in the list, an instance of these variables are passed to the dra functions, from
    SessionsBrowser object. It's the SessionsBrowser object's responsibility to update the state of teh UI.
    """
    # # --- Define and initialize some instance attributes ------------------------------------------------------
    # self.rows: List[Row] = []
    # self.view_rows: List[Row] = []
    # current_filter: str     = ""
    selected:       int     = 0     # the currently selected element in the list
    offset:         int     = 0     # the element currently at top of the view
    h_off:          int     = 0
    page_size:      int     = 20
    view_height:    int     = 0
    show_removed:   bool    = True
    has_colors:     bool    = False
# --- END OF class UIState ----------------------------------------------------------------------------------------



class Event: pass
class MoveUp(Event): pass
class MoveDown(Event): pass
class PageUp(Event): pass
class PageDown(Event): pass
class OpenSelected(Event): pass
class ApplyFilter(Event):
    def __init__(self, _text: str): self.text = _text


@dataclass()
class TUITheme:
    intensives: int = 0
    header:     int = 0
    help_bar:   int = 0
    filtered:   int = 0
    reversed:   int = 0
    removed:    int = 0
    # (No legacy semantic aliases; use existing theme attributes)
    operator_colors:          dict[str, int] = field(default_factory=dict)
    operator_colors_selected: dict[str, int] = field(default_factory=dict)

    @staticmethod
    def init_theme(_operator_colors: dict[str, str]) -> "TUITheme":

        if not curses.has_colors():
            return TUITheme()

        curses.start_color()
        curses.use_default_colors()
        curses.curs_set(0)

        # Fixed color pairs for UI elements
        curses.init_pair(1, curses.COLOR_WHITE, -1)                     # intensives
        curses.init_pair(2, curses.COLOR_CYAN, -1)                      # header
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)     # help bar
        curses.init_pair(4, curses.COLOR_CYAN, -1)                      # filtered highlight
        curses.init_pair(5, curses.COLOR_YELLOW, -1)                    # removed

        # No additional semantic color pairs required

        # Map color names to curses color constants
        color_map = {
            "white":   curses.COLOR_WHITE,
            "green":   curses.COLOR_GREEN,
            "yellow":  curses.COLOR_YELLOW,
            "cyan":    curses.COLOR_CYAN,
            "magenta": curses.COLOR_MAGENTA,
            "blue":    curses.COLOR_BLUE,
            "red":     curses.COLOR_RED,
            "black":   curses.COLOR_BLACK,
        }

        # Create dynamic color pairs for operators (starting from pair 10)
        operator_colors = {}
        operator_colors_selected = {}
        pair_idx = 10

        for op_key, color_name in sorted(_operator_colors.items()):
            color_name_lower = color_name.lower()
            if color_name_lower in color_map:
                fg_color = color_map[color_name_lower]
                # Normal: color on default background
                curses.init_pair(pair_idx, fg_color, -1)
                operator_colors[op_key] = curses.color_pair(pair_idx)
                pair_idx += 1

                # Selected: same color on cyan background
                curses.init_pair(pair_idx, fg_color, curses.COLOR_CYAN)
                operator_colors_selected[op_key] = curses.color_pair(pair_idx)
                pair_idx += 1

        return TUITheme(
            intensives  = curses.color_pair(1),
            header      = curses.A_BOLD | curses.color_pair(2),
            help_bar    = curses.color_pair(3),
            filtered    = curses.color_pair(4),
            removed     = curses.color_pair(5),
            reversed    = curses.A_REVERSE,
            operator_colors = operator_colors,
            operator_colors_selected = operator_colors_selected
            )
    # --- END OF init_theme() ------------------------------------------------------------------------------------------
# --- END OF class TUITheme --------------------------------------------------------------------------------------------

# --- END OF navigation classes ----------------------------------------------------------------------------------------
