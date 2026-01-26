"""
Filename:       sessions_browser.py
Author:         jole
Created:        15.09.2025

Description:    Holds class definitions for SessionBrowser along with attributes and methods.
Just some random text to increase the size of the description field.

Notes:
"""

# ──────────────────────────────────────────────────────────────────────────────
# Import section
# ──────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from bs4 import BeautifulSoup  # noqa: I001

from .defs import IVSCC_BASE_URLS
from .fetch_sessions import FetchSessions

# ─── END OF Import section ────────────────────────────────────────────────────



class SessionsBrowser:

    """
    Class representing the IVS Sessions Browser.

    Defined in sessions_browser.py.

    """

    def __init__(self, _year: int, _scope: str, _mirrors: bool = False, _filters: str | None = None) -> None:  # noqa: E501
        # Store user input parameters
        self.year       = _year
        self.scope      = _scope
        #self.mirrors    = _mirrors
        self.filters    = _filters


        # Build the candidate URL list for the requested scope/mirrors
        self.url_list = self._urls_for_scope(_mirrors)

        #for url in self.url_list:
        #    print(f"url: {url}")

        # Container for fetched HTML (url -> html string) and parsed rows.
        # `FetchSessions.fetch_urls_html()` is responsible for probing mirrors
        # and returning the most-recent master/intensive pages when possible.
        #self.url_meta: dict[str, dict] = {}
        #self.html_map: dict[str, str] = {}

        # The raw HTML data fetched from the URL, in case of mirrors, the most recent
        # one is stored here.
        self.html_data: list[str] = []

        fs: FetchSessions = FetchSessions()

        self.html_data = fs.fetch_urls_html(self.url_list)
        print(f"Fetched HTML data for {BeautifulSoup(''.join(self.html_data), 'html.parser')} URLs.")  # noqa: E501
    # ─── END OF __init__() ────────────────────────────────────────────────────



    def _urls_for_scope(self, _mirrors: bool) -> list[str]:
        """
        Defined in sessions_browser.py.
        _urls_for_scope() builds the list of urls to download session data from,
        based on the year and scope provided by the user. The list contains both
        primary site, and any mirrors

        Primary and mirror sites are defined in IVSCC_BASE_URLS in defs.py.

        :return: list of string, containing the urls from which we read session data
        and compare last updated timestamps. We like to use the most recently updated
        data available.
        """

        base_url_list   : list[str] = IVSCC_BASE_URLS
        year            : int       = (int)(self.year)
        retval          : list[str] = []

        if not _mirrors:
            base_url_list = [base_url_list[0]]
            print("Using only primary IVSCC site for session data.")
        else:
            print("Using most recent of primary and mirror IVSCC sites for session data.")

        if self.scope == "master":
            for base_url in base_url_list:
                retval.append(f"{base_url}/{year}/")

        elif self.scope == "intensive":
            for base_url in base_url_list:
                retval.append(f"{base_url}/intensive/{year}/")

        elif self.scope == "both":
            for base_url in base_url_list:
                retval.append(f"{base_url}/{year}/")
                retval.append(f"{base_url}/intensive/{year}/")

        return retval
    # ─── END OF _urls_for_scope() ─────────────────────────────────────────────



    def render_sessions_list(self) -> list[str]:
        """
        Defined in sessions_browser.py.
        Docstring for render_sessions_list

        :return: A list of strings representing the rendered sessions.
        :rtype: list[str]
        """

        lines: list[str] = []
        lines.append(f"IVS Sessions Browser — year={self.year}, scope={self.scope}")
        lines.append(f"Filters: {self.filters}")
        lines.append("Jon Leithe")
        lines.append("(No session rows available in this minimal implementation.)")
        return lines
# ─── END OF render_sessions_list() ────────────────────────────────────────────



    def run(self, _text: bool = True) -> None:
        """
        Placeholder run method provided by the mixin.
        """
        print(f"{_text}")

    # ─── END OF run() ─────────────────────────────────────────────────────────

# ─── END OF class SessionsBrowser ─────────────────────────────────────────────
