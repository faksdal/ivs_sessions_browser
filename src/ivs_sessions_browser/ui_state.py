"""
Filename:   ui_state.py
Author:     jole
Created:    16.09.2025
Description:

Notes:
"""

from dataclasses import dataclass, field

@dataclass
class UIState:
    # # --- Define and initialize some more instance attributes ------------------------------------------------------
    # self.rows: List[Row] = []
    # self.view_rows: List[Row] = []
    # current_filter: str     = ""
    selected:       int     = 0     # the currently selected element in the list
    offset:         int     = 0     # the element currently at top of the view
    h_off:          int     = 0
    page_size:      int     = 20
    show_removed:   bool    = False
    has_colors:     bool    = False
# --- END OF class ITState ----------------------------------------------------------------------------------------



class Event: pass
class MoveUp(Event): pass
class MoveDown(Event): pass
class PageUp(Event): pass
class PageDown(Event): pass
class OpenSelected(Event): pass
class ApplyFilter(Event):
    def __init__(self, _text: str): self.text = _text
# --- END OF navigation classes ----------------------------------------------------------------------------------------