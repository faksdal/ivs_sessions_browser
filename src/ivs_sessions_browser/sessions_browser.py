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
        self.filters    = _filters


        # Build the candidate URL list for the requested scope/mirrors
        self.url_list = self._urls_for_scope(_mirrors)

        # The raw HTML data fetched from the URL, in case of mirrors, the most recent
        # one is stored here.
        self.list_html_data: list[str] = []


        fs: FetchSessions = FetchSessions()

        # self.html_data contains the fetched HTML data for both master and intensive schedules
        self.list_html_data_page = fs.fetch_html_from_urls(self.url_list)

        for page_data in self.list_html_data_page:
            # print(f"Processing fetched HTML data of length: {len(page_data.html)} characters")
            soup = BeautifulSoup(page_data.html, "html.parser")
            h1 = soup.find('h1', class_='title')
            title_str = h1.get_text(strip=True) if h1 else None
            print(f"Fetched title: {title_str} from URL: {page_data.url}")

        # print the title of each downloaded page for debugging
        # soup = BeautifulSoup(html, "html.parser")
        # title_tag = soup.find("title")
        # title_text = title_tag.get_text() if title_tag else "No title found"
        # print(f"Fetched page title: {title_text} from URL: {url}")

        # h1 = soup.find('h1', class_='title')
        # title_str = h1.get_text(strip=True) if h1 else None
        # print(f"Fetched h1 title: {title_str} from URL: {url}")

        # soup = BeautifulSoup(html_data, "html.parser")
        # title_tag = soup.find("title")
        # title_text = title_tag.get_text() if title_tag else "No title found"
        # print(f"Fetched page title: {title_text}")

        # print(BeautifulSoup("".join(self.list_html_data), "html.parser").prettify())

        # print(f"Lenght of list element #1: {len(self.list_html_data[0])}")
        # print(f"Lenght of list element #2: {len(self.list_html_data[1])}")


        #soup = BeautifulSoup("".join(self.html_data), "html.parser")

        #from .sessions_tui_formatter import SessionsTuiFormatter

        #SessionsTuiFormatter(soup, self.filters)

        #session_lines = list(formatter.iter_lines())

        # print(f"Fetched {len(session_rows)} session rows from IVSCC sites.")

        # Next step is to organize and render the session data, applying filters if any.
        # session_rows = self.html_data.select("table tr")
        # print(session_rows)


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
            print("Using only primary IVSCC site for session data (https://ivscc.gsfc.nasa.gov)")
        else:
            print("Reviewing primary and mirror IVSCC sites for the most recently updated session data.")  # noqa: E501

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
    # ─── END OF render_sessions_list() ────────────────────────────────────────



    def run(self, _text: bool = True) -> None:
        """
        Placeholder run method provided by the mixin.
        """
    # ─── END OF run() ─────────────────────────────────────────────────────────

# ─── END OF class SessionsBrowser ─────────────────────────────────────────────
