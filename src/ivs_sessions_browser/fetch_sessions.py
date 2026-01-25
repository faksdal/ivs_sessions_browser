
# ──────────────────────────────────────────────────────────────────────────────
# Import section
# ──────────────────────────────────────────────────────────────────────────────
#from urllib import response
import os                                       # noqa: I001
# from urllib import response
# import urllib.request
import certifi
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# from datetime import datetime, timezone
from datetime import datetime
# from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup
from dateutil import parser as dparser
import importlib.resources as pkg_resources
# ─── END OF Import section ────────────────────────────────────────────────────



class FetchSessions:
    """
    Docstring for FetchSessions

    :var mapping: Description
    :var implementation: Description
    :vartype implementation: it
    """



    def __init__(self) -> None:
        # Cache mapping: url -> { 'last_modified': datetime|None, 'etag': str|None }
        # Initialized here so other methods can rely on its presence.
        self.url_meta: dict[str, dict] = {}
    # ─── END OF __init__() ────────────────────────────────────────────────────



    def fetch_urls_html(self, _urls: list[str], _timeout: int = 30) -> dict[str, str]:
        """
        Fetch HTML content for a list of URLs.

        Returns a mapping: { url: html_content }
        """
        url_list = _urls

        self.url_meta: dict[str, dict] = {}
        self.url_meta.update(self.fetch_urls_metadata(url_list))

        # Here goes code to sort URLs by last modified date
        # Modifying the url_list, deleting the older ones
        # First need to differentiate between master and intensive schedules
        self.meta_master:       dict[str, datetime] = {}
        self.meta_intensive:    dict[str, datetime] = {}
        self.last_master:       str = ""
        self.last_intensive:    str = ""

        self.last_mod_master             = None
        self.last_mod_intensive          = None
        self.most_recent_mod_master      = None
        self.most_recent_mod_intensive   = None

        for m in self.url_meta.items():
            url         = m[0]

            if "intensive" not in url:  # master schedule
                #self.meta_master[url] = last_mod
                self.last_mod_master = m[1].get('last_modified')

                if self.most_recent_mod_master is None or self.most_recent_mod_master < self.last_mod_master:  # noqa: E501
                    self.most_recent_mod_master = self.last_mod_master
                    self.most_recent_url_master = url

            elif "intensive" in url:    # intensive schedule
                #self.meta_intensive[url] = last_mod
                self.last_mod_intensive = m[1].get('last_modified')

                if self.most_recent_mod_intensive is None or self.most_recent_mod_intensive < self.last_mod_intensive:  # noqa: E501
                    self.most_recent_mod_intensive = self.last_mod_intensive
                    self.most_recent_url_intensive = url

        html_map: dict[str, str] = {}
        ca_bundle   = self._get_ca_bundle_path()
        sess        = self._make_session()

        url_list.clear()
        url_list.append(self.most_recent_url_master)
        url_list.append(self.most_recent_url_intensive)
        print(url_list)


        for u in url_list:
            print(f"Please wait, fetching HTML for URL: {u}")

            try:
                resp = sess.get(u, timeout=_timeout, allow_redirects=True, verify=True)

                resp.raise_for_status()

                html_map[u] = resp.text

            except requests.exceptions.SSLError:
                    # SSL issues: if this relates to ivscc.oan.es, try again with our CA bundle
                    # Otherwise, just give up and return None
                    print(f"SSL error fetching URL: {u}")
                    print("Trying again with verify= ca_bundle")

                    if "ivscc.oan.es" in u:
                        resp = sess.get(u, timeout=_timeout, allow_redirects=True, verify=ca_bundle)
                        html_map[u] = resp.text
                    else:
                        html_map[u] = ""

            except requests.exceptions.RequestException:
                print(f"Error fetching URL: {u}")
                html_map[u] = ""

        return html_map

    # ─── END OF fetch_urls_html() ─────────────────────────────────────────────



    def fetch_urls_metadata(self, urls: list[str]) -> dict[str, dict]:
        """
        Fetch metadata for a list of URLs. What we're interested in are
        Last-Modified and ETag headers.

        Returns a mapping: { url: { 'last_modified': datetime|None, 'etag': str|None } }
        """

        # meta: list[tuple[str, datetime]] = []
        for u in urls:
            print(f"Please wait, fetching metadata for URL: {u}")
            lm = self.fetch_last_modified(u)
            self.url_meta[u] = {'url': u, 'last_modified': lm}

        for m in self.url_meta.items():
                print(f"Last modified: {m[1].get('last_modified')} -> url: {m[0]}")

        return self.url_meta
    # ─── END OF fetch_urls_metadata() ─────────────────────────────────────────



    #def fetch_last_modified(self, url: str, timeout: int = 10) -> tuple[datetime | None, str | None]:  # noqa: E501
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



    def fetch_last_modified(self, url: str, timeout: int = 10) -> datetime | None:
        """
        Perform a HEAD request (fallback to GET) and return (Last-Modified, ETag).

        Returns two values which may be None if the server doesn't provide the
        corresponding headers.
        """

        ca_bundle   = self._get_ca_bundle_path()
        sess        = self._make_session()
        lm          = None

        try:
            resp = sess.get(url, timeout=timeout, allow_redirects=True, verify=True)

            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            t = soup.find("time")
            if t and t.has_attr("datetime"):
                last_modified_string = str(t.get("datetime", "")).strip()
                try:
                    lm = dparser.parse(last_modified_string)
                except Exception:
                    lm = None
            else:
                lm = None

            return lm

        except requests.exceptions.SSLError:
            # SSL issues: if this relates to ivscc.oan.es, try again with our CA bundle
            # Otherwise, just give up and return None
            print(f"SSL error fetching URL: {url}")
            print("Trying again with verify= ca_bundle")

            if "ivscc.oan.es" in url:
                resp = sess.get(url, timeout=timeout, allow_redirects=True, verify=ca_bundle)

                soup = BeautifulSoup(resp.text, "html.parser")
                t = soup.find("time")
                if t and t.has_attr("datetime"):
                    last_modified_string = str(t.get("datetime", "")).strip()
                    try:
                        lm = dparser.parse(last_modified_string)
                    except Exception:
                        lm = None
                else:
                    lm = None
            else:
                lm = None

            return lm

        except requests.exceptions.RequestException:
            print(f"Error fetching URL: {url}")
            return (None)
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
