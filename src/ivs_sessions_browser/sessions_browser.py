"""
Filename:       sessions_browser.py
Author:         jole
Created:        15.09.2025

Description:    Holds class definitions for SessionBrowser along with attributes and methods.

Notes:
"""

# --- Import section ---------------------------------------------------------------------------------------------------
from typing import Optional

from .read_data import ReadData
# --- END OF Import section --------------------------------------------------------------------------------------------



class SessionsBrowser:
    """
    SessionBrowser holds the logic for the whole application, it keeps everything together!

    Application execution steps:
        - Get data from url's depending on the value in self.scope.
        - Display organized data as lines, supporting navigation with keyboard in terminal.
        - Run the loop, catching users input and act appropriately.
    """

    def __init__(self,
                 _year: int,
                 _scope: str,
                 _stations_filter: Optional[str] = None
                 ) -> None:
        self.year               = _year
        self.scope              = _scope
        self.stations_filter    = _stations_filter

        self.data: ReadData = ReadData(self.year, self.scope, True, self.stations_filter)
    # --- END OF __init__() --------------------------------------------------------------------------------------------



    def run(self) -> None:
        """
        Starting point for the application.

        :return: None
        """
        exit(1)
    # --- END OF run() -------------------------------------------------------------------------------------------------
# --- END OF class SessionsBrowser -------------------------------------------------------------------------------------


