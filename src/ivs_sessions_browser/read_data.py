"""
Filename:       read_data.py
Author:         jole
Created:        15.09.2025

Description:

Notes:
"""

# --- Import section ---------------------------------------------------------------------------------------------------
import time
import requests
import logging

# import .defs

from bs4    import BeautifulSoup
from .defs import Row
from typing import Callable, Optional, List #, Tuple, Dict, Any

# from type_defs      import HEADERS, Row, FIELD_INDEX
# from session_parser import SessionParser
# --- END OF Import section --------------------------------------------------------------------------------------------



class ReadData:

    """
    Generic helper class to handle downloading from the web.
    This is called form the main, and has all the logic to download content, and give feedback to stdout
    """


    def __init__(self,
                 _urls:     List[str],
                 _year:     int,
                 _scope:    str,
                 _feedback: bool = True,
                 _stations_filter: Optional[str] = None
                 ) -> None:

        self.urls               = _urls
        self.year               = _year
        self.scope              = _scope
        self.feedback           = _feedback
        self.stations_filter    = _stations_filter

        print(f"{self.urls}-{self.year}-{self.scope}-{self.stations_filter}")
#   # --- END OF __init__() method, or constructor if you like ---------------------------------------------------------



    def fetch_all_urls(self) -> List[Row]:
        """
        todo: move the logic of ursl_for_scope in here.

            This function is the calling function from the outside, and the one to return ALL the downloaded content
        to the caller.

        :return str:    List containing the downloaded data (html)
        """

        rows: List[Row] = []
        # for url in self._urls_for_scope():
        #     rows.extend(self._fetch_one_url(url))

        # for r in rows:
        #     self.logger.debug(f"URLHelper.fetch_all_urls(): row: {r}")

        return rows
    # this is the end of _fetch_all_urls() -----------------------------------------------------------------------------
#
#
#
#     def _status_inline(self, msg: str) -> None:
#         """
#         URLHelper._status_inline() - Used as callback function in URLHelper._get_text_with_progress_retry(), which is
#                                      called from URLHelper._fetch_one_url(). It prints the download progress to stdout.
#
#         :param msg: The message to print to stdout
#         :return:    None
#         """
#
#         print(f"\r{msg}", end="", flush=True)
#     # --- END OF _status_inline() --------------------------------------------------------------------------------------
#
#
#
#     def _get_text_with_progress(self,
#                                 _url: str,
#                                 *, _timeout=(5, 20),
#                                 _status_cb: Optional[Callable[[str], None]] = None,
#                                 _chunk_size: int = 65536,
#                                 _min_update_interval: float = 0.10
#                                 ) -> str:
#         """
#             Download text content from a URL with progress reporting.
#
#             This method streams the response in chunks, periodically invoking a
#             callback with download status messages. Returns the entire response
#             body decoded as text.
#
#             :param _url:                    The URL to fetch.
#             :param _timeout:                (connect_timeout, read_timeout) in seconds.
#             :param _status_cb:              Optional callback taking a str; called with progress updates.
#             :param _chunk_size:             Number of bytes to read per chunk (default 64 KB).
#             :param _min_update_interval:    Minimum seconds between status callbacks (default 0.1).
#             :return:                        The full response body as decoded text (usually HTML).
#             :raises RuntimeError:           If the server responds with an HTTP error.
#         """
#
#         UA = "Mozilla/5.0 (compatible; IVSBrowser/1.0)"
#         cb = _status_cb or (lambda _msg: None)
#
#         with requests.get(_url, stream=True, timeout=_timeout, headers={"User-Agent": UA}) as r:
#             try:
#                 # raise for 4xx/5xx errors
#                 r.raise_for_status()
#             except requests.HTTPError as e:
#                 # give useful context
#                 raise RuntimeError(f"HTTP {r.status_code} {r.reason} for {r.url}") from e
#             # content length, may be missing or non-numeric
#             try:
#                 total = int(r.headers.get("Content-Length", ""))
#             except ValueError:
#                 total = None
#
#             got = 0
#             chunks = []
#             last_emit = 0.0
#
#             for chunk in r.iter_content(chunk_size=_chunk_size):
#                 if not chunk:
#                     continue
#                 chunks.append(chunk)
#                 got += len(chunk)
#
#                 now = time.monotonic()
#                 if now - last_emit >= _min_update_interval:
#                     if total:
#                         cb(f"Downloading… {got}/{total} bytes ({got / total * 100:.1f}%)")
#                     else:
#                         cb(f"Downloading… {got} bytes")
#                     last_emit = now
#
#             # final progress line
#             if total:
#                 cb(f"Download complete: {got}/{total} bytes.")
#                 self.logger.info(f"URLHelper._get_text_with_progress(): Download complete: {got}/{total} bytes.")
#                 # print a newline after it finishes to clean up user prompt
#                 print()
#             else:
#                 cb(f"Download complete: {got} bytes.")
#                 self.logger.info(f"URLHelper._get_text_with_progress(): Download complete: {got} bytes.")
#                 # print a newline after it finishes to clean up user prompt
#                 print()
#
#             # Pick a sensible encoding
#             enc = r.encoding or r.apparent_encoding or "utf-8"
#             try:
#                 return b"".join(chunks).decode(enc, errors="replace")
#             except LookupError:
#                 # Unknown codec name – fall back to utf-8
#                 return b"".join(chunks).decode("utf-8", errors="replace")
#     # --- END OF _get_text_with_progress() -----------------------------------------------------------------------------
#
#
#
#     # --- downloads from web giving feedback to the user of the progress ###############################################
#     def _get_text_with_progress_retry(self,
#                                       _url: str,
#                                       *,
#                                       _retries: int = 2,
#                                       _backoff: float = 0.5,
#                                       _status_cb: Optional[Callable[[str],None]] = None,
#                                       **_kwargs,
#                                       ) -> str:
#         """
#
#         :param _url:
#         :param _retries:
#         :param _backoff:
#         :param _status_cb:
#         :param _kwargs:
#         :return:
#         """
#
#         cb = _status_cb or (lambda _msg: None)
#         for attempt in range(_retries + 1):
#             try:
#                 return self._get_text_with_progress(_url, _status_cb = cb, **_kwargs)
#             except (requests.Timeout, requests.ConnectionError) as e:
#                 if attempt < _retries:
#                     self.logger.notice(f"URLHelper._get_text_with_progress(): {e.__class__.__name__}: {e}. Retrying in {_backoff:.1f}s…")
#                     cb(f"{e.__class__.__name__}: {e}. Retrying in {_backoff:.1f}s…")
#                     time.sleep(_backoff)
#                     _backoff *= 2
#                 else:
#                     raise
#
#     # --- END OF _get_text_with_progress_retry() -----------------------------------------------------------------------
#
#
#
#     def _fetch_one_url(self,
#                       _url: str
#                       ) -> List[Row]:
#         """
#         Fetch and parse the IVS sessions table URL into rows (case-sensitive CLI filters)
#         Data fetched from https://ivscc.gsfc.nasa.gov/
#
#         :return str:    List containing the downloaded and parsed data
#         """
#
#         # --- reading data from web ####################################################################################
#         # print(f"Reading data from {_url}...")
#         self.logger.notice(f"URLHelper._fetch_one_url(): Reading data from {_url}")
#         # self.logger.debug(f"URLHelper._fetch_one_url()")
#         try:
#             # --- this function is defined in subclass URLHelper. It fetches the content from the _url, giving feedback
#             # --- to the user along the way through self._status_inline, which is also defined in URLHelper
#             # urlhelper = URLHelper(_url, self.logger)
#             is_intensive = "/intensive/" in _url
#
#             html    = self._get_text_with_progress_retry(_url, _status_cb = self._status_inline)
#             parsed  = SessionParser(BeautifulSoup(html, "html.parser"),
#                                     self.logger,
#                                     len(HEADERS),
#                                     is_intensive,
#                                     self.stations_filter,
#                                     self.sessions_filter).parse()
#             return parsed
#
#         except requests.RequestException as exc:
#             print(f"Error fetching {_url}: {exc}")
#             self.logger.warning(f"URLHelper._fetch_one_url(): Error fetching {_url}: {exc}")
#             return []
#     # this is the end of _fetch_one_url() ------------------------------------------------------------------------------
#
#
#

#
#
#
#     def _urls_for_scope(self) -> List[str]:
#         """
#         Constructing the url's to read from
#
#         :return List[str]:  List of url's from which we read our data. This will be 'master', and 'intensive' for
#                             a given year. It defaults to the current year and both master and intensives
#         """
#
#         base_url = "https://ivscc.gsfc.nasa.gov/sessions"
#         year = str(self.year)
#         if self.scope == "master":
#             return [f"{base_url}/{year}/"]
#         if self.scope == "intensive":
#             return [f"{base_url}/intensive/{year}/"]
#         return [f"{base_url}/{year}/", f"{base_url}/intensive/{year}/"]
#     # this is the end of _urls_for_scope() -----------------------------------------------------------------------------
#
# --- END OF class ReadData --------------------------------------------------------------------------------------------