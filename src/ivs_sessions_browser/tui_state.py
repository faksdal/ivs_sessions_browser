"""
Filename:       ui_state.py
Author:         jole
Created:        16.09.2025
Description:

Notes:
"""

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
    show_removed:   bool    = False
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



class TUITheme:
    # self.has_colors = curses.has_colors()
    # if self.has_colors:
    #     curses.start_color()
    #     curses.use_default_colors()
    #     curses.init_pair(1, curses.COLOR_YELLOW, -1)  # removed stations, intensives
    #     curses.init_pair(2, curses.COLOR_CYAN, -1)  # header
    #     curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)  # help bar
    #     curses.init_pair(4, curses.COLOR_GREEN, -1)  # released
    #     curses.init_pair(5, curses.COLOR_YELLOW, -1)  # processing
    #     curses.init_pair(6, curses.COLOR_MAGENTA, -1)  # cancelled
    #     curses.init_pair(7, curses.COLOR_WHITE, -1)  # none
    #     curses.init_pair(8, curses.COLOR_CYAN, -1)  # station highlight in filter
    pass
# --- END OF class TUITheme --------------------------------------------------------------------------------------------

# --- END OF navigation classes ----------------------------------------------------------------------------------------
