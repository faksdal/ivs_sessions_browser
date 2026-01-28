# flake8: noqa
# isort: skip_file

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
from bs4        import BeautifulSoup

# Project defined imports
from .defs                      import HEADERS, IVSCC_BASE_URLS
from .fetch_sessions            import FetchSessions
from .sessions_tui_formatter    import SessionsTuiFormatter
from .ivstypes                  import PageData
# ─── END OF Import section ────────────────────────────────────────────────────



class SessionsBrowser:
    """
    Class representing the IVS Sessions Browser.
    Defined in sessions_browser.py.

    """

    def __init__(self, _year: int, _scope: str, _mirrors: bool = False, _filters: str | None = None) -> None:

        # Store user input parameters
        self.year       = _year
        self.scope      = _scope
        self.filters    = _filters

        # Build the candidate URL list for the requested scope/mirrors
        self.url_list = self._urls_for_scope(_mirrors)

        # Creating attribute to store the raw HTML data fetched from the URL, in
        # case the --mirrors flag is set, the most recent one is stored here.
        self.list_html_data_page: list[PageData] = []

        # ──────────────────────────────────────────────────────────────────────
        # Fetch data from web
        # ──────────────────────────────────────────────────────────────────────
        # Create FetchSessions instance to download HTML data from the URLs
        fs: FetchSessions = FetchSessions()

        # self.list_html_data_page contains the fetched HTML data for both master and intensive schedules
        self.list_html_data_page = fs.fetch_html_from_urls(self.url_list)
        # ─── END OF Fetch data from web ───────────────────────────────────────

        # ──────────────────────────────────────────────────────────────────────
        # Format and render session data
        # ──────────────────────────────────────────────────────────────────────
        # Create SessionsTuiFormatter instance to format the parsed HTML
        formatter = SessionsTuiFormatter()

        # Scan fetched HTML data and produce formatted lines
        for page_data in self.list_html_data_page:
            soup    = BeautifulSoup(page_data.html, "html.parser")
            url     = page_data.url

            # Determine if this is a master or an intensive session, and set
            # the is_intensive flag accordingly
            h1          = soup.find('h1', class_='title')
            title_str   = h1.get_text(strip = True) if h1 else None
            if title_str and "intensive" in title_str.lower():
                is_intensive = True
            else:
                is_intensive = False

            # Build the formatted session list from the downloaded HTML soup
            formatter.build_list(_soup              = soup,
                                 _num_of_headers    = len(HEADERS) - 1,  # <-- Op is local-only, not on the website
                                 _is_intensive      = is_intensive,
                                 _filters           = self.filters,
                                 _url               = url
                                 )

        print(f"Total sessions parsed: {len(formatter.full_list)}")
        # ─── END OF Format and render session data ────────────────────────────────

    # ─── END OF __init__() ────────────────────────────────────────────────────



    def _urls_for_scope(self, _mirrors: bool) -> list[str]:
        """
        Defined in sessions_browser.py.

        _urls_for_scope() builds the list of urls to download session data from,
        based on the year and scope provided by the user. The list contains both
        primary site, and any mirrors

        Primary and mirror sites are defined in IVSCC_BASE_URLS in defs.py.

        :return: list of string, containing the urls from which we read session data
        and compare last updated timestamps if __mirrors flag is set. We like to
        use the most recently updated data available.
        """

        base_url_list   : list[str] = IVSCC_BASE_URLS
        year            : int       = (int)(self.year)
        retval          : list[str] = []

        if not _mirrors:
            base_url_list = [base_url_list[0]]
            print(f"Using only primary IVSCC site for session data ({IVSCC_BASE_URLS[0]})")
        else:
            print("Reviewing primary and mirror IVSCC sites for the most recently updated session data.")

        if self.scope == "master":
            for base_url in base_url_list:
                retval.append(f"{base_url}/{year}")

        elif self.scope == "intensive":
            for base_url in base_url_list:
                retval.append(f"{base_url}/intensive/{year}")

        elif self.scope == "both":
            for base_url in base_url_list:
                retval.append(f"{base_url}/{year}")
                retval.append(f"{base_url}/intensive/{year}")

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
