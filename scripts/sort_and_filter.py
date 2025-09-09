"""
Filename:   sort_and_filter.py
Author:     jole
Created:    2025-09-09
Description:
    Provides mechanisms for sorting and filtering the list of sessions. Most of these will be called from
    SessionBrowser.run()

Notes:
    - Requires logger library.
    - Requires datetime
    - Requires Optional and List from typing
    - Requires Row from type_defs (local defines for this project)
"""

# --- import section ---------------------------------------------------------------------------------------------------
import logging

from datetime   import datetime
from typing     import List, Optional # Tuple, Dict, Any
from type_defs  import Row #, FIELD_INDEX, HEADERS, HEADER_LINE, WIDTHS
# --- END OF import section --------------------------------------------------------------------------------------------



class SortAndFilter:
    """
    Handles all sorting and filtering on the list of sessions
    """

    def __init__(self,
                 _logger:           logging.Logger,
                 _stations_filter: Optional[str] = None,
                 _sessions_filter: Optional[str] = None
                 ) -> None:
        """

        :param _logger:             the logger object
        :param _stations_filter:    any station filters applied
        :param _sessions_filter:    any session filters applied
        """

        self.logger             = _logger
        self.stations_filter    = _stations_filter
        self.sessions_filter    = _sessions_filter
    # --- END OF __init__() --------------------------------------------------------------------------------------------



    def sort_by_start(self, rows: List[Row]) -> List[Row]:
        """
        Sorts the list given by rows chronologically

        :param rows:    holds the list to be sorted
        :return rows:   the sorted list
        """

        def keyfunc(row: Row):
            """
            Nested function to set the sort key
            """
            start_str = row[0][2]
            try:
                return datetime.strptime(start_str, "%Y-%m-%d %H:%M")
            except ValueError:
                return datetime.min
        # --- END OF keyfunc() -----------------------------------------------------------------------------------------
        return sorted(rows, key=keyfunc)
    # --- END OF sort_by_start() ---------------------------------------------------------------------------------------