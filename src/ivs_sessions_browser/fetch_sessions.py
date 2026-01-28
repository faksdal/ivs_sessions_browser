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
from .ivstypes          import PageData
from dateutil           import parser   as dparser
# ─── END OF Import section ────────────────────────────────────────────────────



class FetchSessions:
    """
    class FetchSessions defined in fetch_sessions.py.

    Methods:
        * fetch_html_from_urls(); Fetch HTML content for a list of URLs, comparing last-modified times to
          return the most recent content for master and intensive schedules.
        * _find_most_recent_page(); Find the most recent page from a list of URLs based on last-modified times.

    """

    def __init__(self) -> None:
        pass
        # Cache mapping: url -> { 'last_modified': datetime|None, 'etag': str|None }
        # Initialized here so other methods can rely on its presence.
        # self.url_meta: dict[str, dict] = {}
    # ─── END OF __init__() ────────────────────────────────────────────────────



    def fetch_html_from_urls(self, _urls: list[str], _timeout: int = 30) -> list[PageData]:
        """
        Defined in fetch_sessions.py.

        Fetch HTML content from a list of URLs, comparing last-modified times to
        return the most recent content for master and intensive schedules.

        Returns a list[PageData]: A list containing PageData for master and intensive schedules.
        """  # noqa: E501

        # Split URLs into master and intensive
        urls_master, urls_intensive = self._split_urls(_urls)

        # Declare PageData objects to hold results
        page_master     = PageData(html = "", last_modified = None)
        page_intensive  = PageData(html = "", last_modified = None)

        # Find most recent pages for master and intensive
        page_master     = self._find_most_recent_page(urls_master, _timeout)
        page_intensive  = self._find_most_recent_page(urls_intensive, _timeout)

        ############ DEBUGGING OUTPUT ############
        if page_master.url:
            print(f"Most recent master schedule URL: {page_master.url} - Last modified: {page_master.last_modified}")
        else:
            print("No master schedule URL fetched.")

        ############ DEBUGGING OUTPUT ############
        if page_intensive.url:
            print(f"Most recent intensive schedule URL: {page_intensive.url} - Last modified: {page_intensive.last_modified}")
        else:
            print("No intensive schedule URL fetched.")

        # return pager_master and page_intensive attributes as a list
        return [page_master, page_intensive]
    # ─── END OF fetch_html_from_urls() ─────────────────────────────────────────────



    def _find_most_recent_page(self, _urls: list[str], _timeout: int) -> PageData:

        page_data = PageData(html = "", last_modified = None)

        for url in _urls:
            # print(f"Please wait, fetching HTML content for URL: {url}")

            # Initialize variables
            html    = ""
            lm      = None

            # Fetch HTML content and last modified time
            html = self._fetch_one_url_html(url, _timeout = _timeout)



            if html:
                lm = self._fetch_latest_update_from_html(html)

            # print(f"Last modified: {lm} - fetched HTML content from URL: {url}")
            # Compare last modified time to pick most recent
            if page_data.last_modified is None or (lm is not None and lm > page_data.last_modified):
                page_data.html = html
                page_data.last_modified = lm
                page_data.url = url

            # print(f"Most recent last modified so far: {page_data.last_modified} from URL: {page_data.url}")

        return page_data
    # ─── END OF _find_most_recent_page() ──────────────────────────────────────



    def _fetch_latest_update_from_html(self, html: str) -> datetime | None:
        """
        Docstring for _fetch_latest_update_from_html

        :param self: Description
        :param html: Description
        :type html: str
        :return: Description
        :rtype: datetime | None
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
        Docstring for _fetch_one_url_html

        :param self: Description
        :param _url: Description
        :type _url: str
        :param _timeout: Description
        :type _timeout: int
        :return: Description
        :rtype: str
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
            print(f"SSL error fetching URL: {_url}")
            if "ivscc.oan.es" in _url:
                try:
                    resp = sessions.get(_url, timeout=_timeout, allow_redirects=True, verify=ca_bundle)
                    resp.raise_for_status()
                    return resp.text
                except requests.exceptions.RequestException as e:
                    print(f"Retry with CA bundle failed: {_url} - {e}")
                    return ""
            else:
                return ""

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            # Network-level failures: DNS failures, connection refused, timeouts
            print(f"Network error fetching URL: {_url} - {e}")
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
        """Return path to CA bundle: env override -> packaged PEM -> certifi."""
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
        s = requests.Session()
        retries = Retry(total=2, backoff_factor=0.3, status_forcelist=(500, 502, 503, 504))
        s.mount("https://", HTTPAdapter(max_retries=retries))
        s.mount("http://", HTTPAdapter(max_retries=retries))
        return s
    # ─── END OF _make_session() ───────────────────────────────────────────────



    # def fetch_urls_metadata(self, urls: list[str]) -> dict[str, dict]:
        # """
        # Fetch metadata for a list of URLs. What we're interested in are
        # Last-Modified and ETag headers.
#
        # Returns a mapping: { url: { 'last_modified': datetime|None, 'etag': str|None } }
        # """
#
        # meta: list[tuple[str, datetime]] = []
        # for u in urls:
            # print(f"Please wait, fetching metadata for URL: {u}")
            # lm = self.fetch_last_modified(u)
            # self.url_meta[u] = {'url': u, 'last_modified': lm}
#
        # for m in self.url_meta.items():
                # print(f"Last modified: {m[1].get('last_modified')} -> url: {m[0]}")
#
        # return self.url_meta
    # ─── END OF fetch_urls_metadata() ─────────────────────────────────────────



    # def fetch_last_modified(self, url: str, timeout: int = 10) -> datetime | None:
        # """
        # Perform a HEAD request (fallback to GET) and return (Last-Modified, ETag).
#
        # Returns two values which may be None if the server doesn't provide the
        # corresponding headers.
        # """

        # ca_bundle   = self._get_ca_bundle_path()
        # sess        = self._make_session()
        # lm          = None

        # try:
            # resp = sess.get(url, timeout=timeout, allow_redirects=True, verify=True)

            # resp.raise_for_status()

            # soup = BeautifulSoup(resp.text, "html.parser")
            # t = soup.find("time")
            # if t and t.has_attr("datetime"):
                # last_modified_string = str(t.get("datetime", "")).strip()
                # try:
                    # lm = dparser.parse(last_modified_string)
                # except Exception:
                    # lm = None
            # else:
                # lm = None

            # return lm

        # except requests.exceptions.SSLError:
            # SSL issues: if this relates to ivscc.oan.es, try again with our CA bundle
            # Otherwise, just give up and return None
            # print(f"SSL error fetching URL: {url}")
            # print("Trying again with verify= ca_bundle")

            # if "ivscc.oan.es" in url:
                # resp = sess.get(url, timeout=timeout, allow_redirects=True, verify=ca_bundle)
#
                # soup = BeautifulSoup(resp.text, "html.parser")
                # t = soup.find("time")
                # if t and t.has_attr("datetime"):
                    # last_modified_string = str(t.get("datetime", "")).strip()
                    # try:
                        # lm = dparser.parse(last_modified_string)
                    # except Exception:
                        # lm = None
                # else:
                    # lm = None
            # else:
                # lm = None
#
            # return lm
#
        # except requests.exceptions.RequestException:
            # print(f"Error fetching URL: {url}")
            # return (None)
    # ─── END OF fetch_last_modified() ─────────────────────────────────────────



    #def _parse_last_modified(self, header_value: str) -> datetime | None:
    #    try:
    #        return parsedate_to_datetime(header_value)
    #    except Exception:
    #        return None
    # ─── END OF _parse_last_modified() ────────────────────────────────────────



    #def _extract_html_time(self, html: str) -> datetime | None:
    #    """Extract a datetime from a <time datetime="..."> or visible timestamp.

    #    Returns a timezone-aware UTC `datetime` when possible.
    #    """
    #    # Use BeautifulSoup to robustly extract footer/time
    #    try:
    #        soup = BeautifulSoup(html, "html.parser")
    #    except Exception:
    #        return None

    #    footer = soup.find("footer")
    #    if not footer:
    #        # fallback to searching whole document
    #        container = soup
    #    else:
    #        container = footer

    #    # Prefer explicit <time datetime="..."> attribute
    #    t = container.find("time")
    #    if t and t.has_attr("datetime"):
    #        s = str(t.get("datetime", "")).strip()
    #        try:
    #            dt = dparser.parse(s)
    #            if dt.tzinfo is None:
    #                dt = dt.replace(tzinfo=timezone.utc)
    #            return dt
    #        except Exception:
    #            pass

    #    # Fallback: search visible text for a recognizable date/time
    #    text = container.get_text(" ", strip=True)
    #    try:
    #        dt = dparser.parse(text, fuzzy=True)
    #        if dt.tzinfo is None:
    #            dt = dt.replace(tzinfo=timezone.utc)
    #        return dt
    #    except Exception:
    #        return None
    # ─── END OF _extract_html_time() ──────────────────────────────────────────



    #def read_and_process_url(self, url: str, timeout: int = 30) -> bool:
    #    """Perform a GET for the URL and process its contents.

    #    This is a minimal implementation: it reads the response body and returns
    #    True on success. Replace processing with your parser/loader.
    #    """
    #    try:
    #        with urllib.request.urlopen(url, timeout=timeout) as resp:
    #            _ = resp.read()
    #        return True
    #    except Exception:
    #        return False
    # ─── END OF read_and_process_url() ────────────────────────────────────────



    #def read_if_updated(self, urls: list[str]) -> None:
    #    """Read only those URLs that are new or updated compared to `self.url_meta`.

    #    `self.url_meta` is an instance-level cache mapping url -> metadata dict.
    #    After a successful read the metadata for the URL is updated.
    #    """
    #    if not hasattr(self, 'url_meta') or not isinstance(self.url_meta, dict):
    #        self.url_meta = {}

    #    for u in urls:
    #        remote_lm, remote_etag = self.fetch_last_modified(u)
    #        prev = self.url_meta.get(u, {})
    #        prev_lm = prev.get('last_modified')
    #        prev_etag = prev.get('etag')

    #        should_fetch = False
    #        if prev_lm is None and prev_etag is None:
    #            should_fetch = True
    #        elif remote_etag and prev_etag != remote_etag:
    #            should_fetch = True
    #        elif remote_lm and (prev_lm is None or remote_lm > prev_lm):
    #            should_fetch = True

    #        if should_fetch:
    #            ok = self.read_and_process_url(u)
    #            if ok:
    #                self.url_meta[u] = {'last_modified': remote_lm, 'etag': remote_etag}
    # ─── END OF read_if_updated() ─────────────────────────────────────────────
