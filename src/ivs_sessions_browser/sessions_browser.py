"""
Filename:       sessions_browser.py
Author:         jole
Created:        15.09.2025

Description:    Holds class definitions for SessionBrowser along with attributes and methods.

Notes:
"""

# ──────────────────────────────────────────────────────────────────────────────
# Import section
# ──────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from .sb_render import SessionsBrowserRenderMixin  # for SessionsBrowser::render_sessions_list()
from .sb_run import SessionsBrowserRunMixin  # for SessionsBrowser::run()

# from typing import Optional

# ─── END OF Import section ────────────────────────────────────────────────────



class SessionsBrowser(SessionsBrowserRenderMixin, SessionsBrowserRunMixin):
    """
    Class representing the IVS Sessions Browser.
    """

    def __init__(self, _year: int, _scope: str, _filters: str | None = None) -> None:
        self.year = _year
        self.scope = _scope
        self.filters = _filters

        print(f"SessionsBrowser created for year = {self.year}, scope = {self.scope}, filters = {self.filters}")  # noqa: E501

        # --- Create and populate the list of url's we want to download from.
        #self.urls: List[str] = self._urls_for_scope()

        #self.state = UIState()
        #self.theme: TUITheme = None
        #self.draw: DrawTUI = DrawTUI()



        # --- self.rows contains all rosw read from web
        # --- self.view_rows contains the filtered list
        #self.rows: List[Row] = []  # populated in run()
        #self.view_rows: List[Row] = []

        # --- Tokens to highlight in the stations column when filtering
        #self.highlight_tokens: List[str] = []

        # --- Holds the current filter as input by user
        #self.current_filter: str = ""

        #self.fs = FilterAndSort()

        # self.operators = load_operators()
        #self.operator_bindings = load_operator_bindings()
        #self.operators = load_operators()

        # --- For debugging
        # print(self.operators)
        # exit(0)
    # ─── END OF __init__ ──────────────────────────────────────────────────────




# ─── END OF class SessionsBrowser ─────────────────────────────────────────────
