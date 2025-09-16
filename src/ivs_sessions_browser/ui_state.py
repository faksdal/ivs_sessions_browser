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
    # --- Assigning all parameters to local instance attributes ----------------------------------------------------
    # self.year = _year
    # self.logger = _logger
    # self.scope = _scope
    # self.stations_filter = _stations_filter
    # self.sessions_filter = _sessions_filter
    #
    # # --- Define and initialize some more instance attributes ------------------------------------------------------
    # self.rows: List[Row] = []
    # self.view_rows: List[Row] = []
    current_filter: str     = ""
    selected:       int     = 0
    offset:         int     = 0
    page:           int     = 0
    top:            int     = 0  # scroll offset
    page_size:      int     = 20
    show_removed:   bool    = False
    has_colors:     bool    = False

    # # --- Flag for showing/hiding removed sessions in the list
    # self.show_removed: bool = True
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