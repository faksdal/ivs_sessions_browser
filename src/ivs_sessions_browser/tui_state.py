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
    pass
# --- END OF class TUITheme --------------------------------------------------------------------------------------------

# --- END OF navigation classes ----------------------------------------------------------------------------------------
