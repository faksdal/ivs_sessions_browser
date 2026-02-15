# flake8: noqa
# isort: skip_file

"""
Filename:    fetch_sessions.py
Author:      Jon Leithe
Created:     2026-01-27
Description: Fetch and choose most-recent IVS session HTML pages.
"""

# ──────────────────────────────────────────────────────────────────────────────
# Import section
# ──────────────────────────────────────────────────────────────────────────────
import os
import certifi
import requests
import importlib.resources as pkg_resources

from requests.adapters  import HTTPAdapter
from urllib3.util.retry import Retry
from datetime           import datetime
from bs4                import BeautifulSoup

from dateutil           import parser   as dparser

# Project defined imports
from .ivstypes          import PageData
# ─── END OF Import section ────────────────────────────────────────────────────



class FetchSessions:
    """
    class FetchSessions defined in fetch_sessions.py.

    Methods:
        * fetch_html_from_urls(); Fetch HTML content for a list of URLs, comparing last-modified times to
          return the most recent content for master and intensive schedules.
        * _find_most_recent_page(); Find the most recent page from a list of URLs based on last-modified times.

    """

    def __init__(self, _mirrors: bool) -> None:
        self.mirrors = _mirrors        
    # ─── END OF __init__() ────────────────────────────────────────────────────



    def fetch_html_from_urls(self, _urls: list[str], _timeout: int = 30) -> list[PageData]:
        """
        Defined in fetch_sessions.py.

        Fetch HTML content from a list of URLs, comparing last-modified times to
        return the most recent content for master and intensive schedules.

        Returns a list[PageData]: A list containing PageData for master and intensive
        schedules.
        """ 

        # Split URLs into master and intensive
        urls_master, urls_intensive = self._split_urls(_urls)

        # Declare PageData objects to hold results
        page_master     = PageData(html = "", last_modified = None)
        page_intensive  = PageData(html = "", last_modified = None)

        # Find most recent pages for master and intensive, and store results in
        # page_master and page_intensive
        page_master     = self._find_most_recent_page(urls_master, _timeout)
        page_intensive  = self._find_most_recent_page(urls_intensive, _timeout)

        if self.mirrors:
            if page_master.url:
                print(f"Most recent master schedule URL: {page_master.url} - Last modified: {page_master.last_modified}")
            else:
                print("No master schedule URL fetched.")

            if page_intensive.url:
                print(f"Most recent intensive schedule URL: {page_intensive.url} - Last modified: {page_intensive.last_modified}")
            else:
                print("No intensive schedule URL fetched.")

        # return pager_master and page_intensive attributes as a list
        return [page_master, page_intensive]
    # ─── END OF fetch_html_from_urls() ─────────────────────────────────────────────



    def _find_most_recent_page(self, _urls: list[str], _timeout: int) -> PageData:
        """
        Defined in fetch_sessions.py.
        
        :param _urls    : List of URLs to fetch HTML content from
        :type _urls     : list[str]
        :param _timeout : Timeout for the request in seconds
        :type _timeout  : int
        :return         : PageData object containing the most recent page's HTML
                          and last modified time
        :rtype          : PageData
        """

        page_data = PageData(html = "", last_modified = None)

        for url in _urls:
            # Initialize variables
            html    = ""
            lm      = None

            
            # Give the user some outputbased on whether we're checking mirrors
            # or just fetching HTML content
            if(self.mirrors):
                print(f"Please wait, checking last update on {url}")
            else:
                print(f"Please wait, fetching HTML content for URL: {url}")

            # Fetch HTML content and last modified time from the URL
            html = self._fetch_one_url_html(url, _timeout = _timeout)

            if html:
                lm = self._fetch_latest_update_from_html(html)

            # Compare last modified time to pick most recent, setting page_data
            # attributes if this page is more recent than the current most recent
            if page_data.last_modified is None or (lm is not None and lm > page_data.last_modified):
                page_data.html          = html
                page_data.last_modified = lm
                page_data.url           = url

        return page_data
    # ─── END OF _find_most_recent_page() ──────────────────────────────────────



    def _fetch_latest_update_from_html(self, html: str) -> datetime | None:
        """
        Defined in fetch_sessions.py.
        Extract the latest update time from HTML content.

        :param html : HTML content to parse for the latest update time
        :type html  : str
        :return     : The latest update time as a datetime object, or None if not found
        :rtype      : datetime | None
        """

        try:
            soup = BeautifulSoup(html, "html.parser")
            t = soup.find("time")
            if t and t.has_attr("datetime"):
                last_modified_string = str(t.get("datetime", "")).strip()
                try:
                    lm = dparser.parse(last_modified_string)
                    return lm
                except Exception:
                    return None
            else:
                return None

        except Exception:
            return None
    # ─── END OF _fetch_latest_update_from_html() ──────────────────────────────



    def _fetch_one_url_html(self, _url: str, _timeout: int = 30) -> str:
        """
        Defined in fetch_sessions.py.

        :param _url     : URL to fetch HTML content from
        :type _url      : str
        :param _timeout : Timeout for the request in seconds
        :type _timeout  : int
        :return         : HTML content as a string
        :rtype          : str
        """

        ca_bundle   = self._get_ca_bundle_path()
        sessions    = self._make_session()

        try:
            resp = sessions.get(_url, timeout=_timeout, allow_redirects=True, verify=True)

            resp.raise_for_status()

            return resp.text

        except requests.exceptions.SSLError:
            # SSL issues: try with packaged CA bundle only for known host, otherwise
            # treat as non-fatal and return empty content so caller can continue.
            # print(f"SSL error fetching URL: {_url}")
            if "ivscc.oan.es" in _url:
                try:
                    resp = sessions.get(_url, timeout=_timeout, allow_redirects=True, verify=ca_bundle)
                    # print(f"Please wait, reading from {_url}")
                    resp.raise_for_status()
                    return resp.text
                except requests.exceptions.RequestException as e:
                    # print(f"Retry with CA bundle failed: {_url} - {e}")
                    return ""
            else:
                return ""

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            # Network-level failures: DNS failures, connection refused, timeouts
            # print(f"Network error fetching URL: {_url} - {e}")
            return ""

        except requests.exceptions.RequestException as e:
            # HTTP errors (4xx/5xx) and other request exceptions
            print(f"Error fetching URL: {_url} - {e}")
            return ""
    # ─── END OF _fetch_one_url_html() ─────────────────────────────────────────



    def _split_urls(self, _urls: list[str]) -> tuple[list[str], list[str]]:
        """
        Defined in fetch_sessions.py.

        Split a list of URLs into master and intensive lists.

        :param _urls: List of urls to split between master and intensive
        :type _urls: list[str]
        :return: Returns a tuple: (urls_master, urls_intensive)
        :rtype: tuple[list[str], list[str]]
        """

        urls_master     : list[str]  = []
        urls_intensive  : list[str]  = []

        for u in _urls:
            if "intensive" not in u:
                urls_master.append(u)
            elif "intensive" in u:
                urls_intensive.append(u)

        return (urls_master, urls_intensive)
    # ─── END OF _split_urls() ─────────────────────────────────────────────────



    #def fetch_last_modified(self, url: str, timeout: int = 10) -> tuple[datetime | None, str | None]:
    def _get_ca_bundle_path(self) -> str:
        """
        Defined in fetch_sessions.py.

        Return path to CA bundle: env override -> packaged PEM -> certifi.
        """
        
        env = os.getenv("IVS_CA_BUNDLE")
        if env:
            return env

        try:
            pkg_file = pkg_resources.files("ivs_sessions_browser").joinpath("certs/ivscc_chain.pem")
            # Use as_file to get a filesystem Path which supports exists()
            try:
                with pkg_resources.as_file(pkg_file) as p:
                    if p.exists():
                        return str(p)
            except Exception:
                # as_file may fail for non-existent resources; fall through
                pass
        except Exception:
            pass

        return certifi.where()
    # ─── END OF _get_ca_bundle_path() ─────────────────────────────────────────



    def _make_session(self) -> requests.Session:
        """
        Defined in fetch_sessions.py.

        Create a requests Session with retry logic for transient errors.
        """
        s = requests.Session()
        retries = Retry(total=2, backoff_factor=0.3, status_forcelist=(500, 502, 503, 504))
        s.mount("https://", HTTPAdapter(max_retries=retries))
        s.mount("http://", HTTPAdapter(max_retries=retries))
        return s
    # ─── END OF _make_session() ───────────────────────────────────────────────