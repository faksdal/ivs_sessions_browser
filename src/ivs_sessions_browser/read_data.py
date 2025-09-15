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

from bs4    import BeautifulSoup
from typing import Callable, Optional, List #, Tuple, Dict, Any

# --- Project defined
from .defs                      import Row, HEADERS
from .ivs_session_parser import IvsSessionParser
# --- END OF Import section --------------------------------------------------------------------------------------------



class ReadData:

    """
    Generic helper class to handle downloading from the web.

        This is called from the main, and has all the logic to download content, and give feedback to stdout during
    download.
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
    # --- END OF __init__() method, or constructor if you like ---------------------------------------------------------



    def fetch_all_urls(self) -> List[Row]:
        """
            This function is the calling function from the outside, and the one to return ALL the downloaded content
        to the caller. The URL's to check, are in self.urls. This means the caller has the responsibility to setup
        the URL's.

        Calls on BeautifulSoup to create the html object (to return)

        :return str:    List containing the downloaded data (BeautifulSoup html)
        """

        html: List[Row] = []
        for url in self.urls:
            html.extend(self._fetch_one_url(url))

        return html
    # this is the end of _fetch_all_urls() -----------------------------------------------------------------------------



    def _fetch_one_url(self,
                       _url: str
                       ) -> List[Row]:
        """
        Fetch and parse the IVS sessions table URL into a list of rows (case-sensitive CLI filters)
        Data fetched from https://ivscc.gsfc.nasa.gov/.

            The data fetched must be sent through the parser before we return them. This is because the parser
        is responsible for putting square brackets around the intensives, amongst other things

        :return str:    List containing the downloaded and parsed data
        """

        try:
            is_intensive = "/intensive/" in _url

            html        = self._get_text_with_progress_retry(_url, _status_cb = self._status_inline)
            parsed_html = IvsSessionParser(BeautifulSoup(html, "html.parser"),
                                           len(HEADERS),
                                           is_intensive,
                                           self.stations_filter).parse()

            return parsed_html

        except requests.RequestException as exc:
            print(f"Error fetching {_url}: {exc}")
            print(f"ReadData._fetch_one_url(): Error fetching {_url}: {exc}")
            return []
    # this is the end of _fetch_one_url() ------------------------------------------------------------------------------



    def _status_inline(self, msg: str) -> None:
        """
        URLHelper._status_inline() - Used as callback function in URLHelper._get_text_with_progress_retry(), which is
                                     called from URLHelper._fetch_one_url(). It prints the download progress to stdout.

        :param msg: The message to print to stdout
        :return:    None
        """

        print(f"\r{msg}", end="", flush=True)
    # --- END OF _status_inline() --------------------------------------------------------------------------------------
#
#
#
    def _get_text_with_progress(self,
                                _url: str,
                                *, _timeout=(5, 20),
                                _status_cb: Optional[Callable[[str], None]] = None,
                                _chunk_size: int = 65536,
                                _min_update_interval: float = 0.10
                                ) -> str:
        """
            Download text content from a URL with progress reporting.

            This method streams the response in chunks, periodically invoking a
            callback with download status messages. Returns the entire response
            body decoded as text.

            :param _url:                    The URL to fetch.
            :param _timeout:                (connect_timeout, read_timeout) in seconds.
            :param _status_cb:              Optional callback taking a str; called with progress updates.
            :param _chunk_size:             Number of bytes to read per chunk (default 64 KB).
            :param _min_update_interval:    Minimum seconds between status callbacks (default 0.1).
            :return:                        The full response body as decoded text (usually HTML).
            :raises RuntimeError:           If the server responds with an HTTP error.
        """

        UA = "Mozilla/5.0 (compatible; IVSBrowser/1.0)"
        cb = _status_cb or (lambda _msg: None)

        with requests.get(_url, stream=True, timeout=_timeout, headers={"User-Agent": UA}) as r:
            try:
                # raise for 4xx/5xx errors
                r.raise_for_status()
            except requests.HTTPError as e:
                # give useful context
                raise RuntimeError(f"HTTP {r.status_code} {r.reason} for {r.url}") from e
            # content length, may be missing or non-numeric
            try:
                total = int(r.headers.get("Content-Length", ""))
            except ValueError:
                total = None

            got = 0
            chunks = []
            last_emit = 0.0

            for chunk in r.iter_content(chunk_size=_chunk_size):
                if not chunk:
                    continue
                chunks.append(chunk)
                got += len(chunk)

                now = time.monotonic()
                if now - last_emit >= _min_update_interval:
                    if total:
                        cb(f"Downloading… {got}/{total} bytes ({got / total * 100:.1f}%)")
                    else:
                        cb(f"Downloading… {got} bytes")
                    last_emit = now

            # final progress line
            if total:
                cb(f"Download complete: {got}/{total} bytes.")
                # self.logger.info(f"URLHelper._get_text_with_progress(): Download complete: {got}/{total} bytes.")
                # print a newline after it finishes to clean up user prompt
                print()
            else:
                cb(f"Download complete: {got} bytes.")
                # self.logger.info(f"URLHelper._get_text_with_progress(): Download complete: {got} bytes.")
                # print a newline after it finishes to clean up user prompt
                print()

            # Pick a sensible encoding
            enc = r.encoding or r.apparent_encoding or "utf-8"
            try:
                return b"".join(chunks).decode(enc, errors="replace")
            except LookupError:
                # Unknown codec name – fall back to utf-8
                return b"".join(chunks).decode("utf-8", errors="replace")
    # --- END OF _get_text_with_progress() -----------------------------------------------------------------------------



    def _get_text_with_progress_retry(self,
                                      _url: str,
                                      *,
                                      _retries: int = 2,
                                      _backoff: float = 0.5,
                                      _status_cb: Optional[Callable[[str],None]] = None,
                                      **_kwargs,
                                      ) -> str:
        """

        :param _url:
        :param _retries:
        :param _backoff:
        :param _status_cb:
        :param _kwargs:
        :return:
        """

        cb = _status_cb or (lambda _msg: None)
        for attempt in range(_retries + 1):
            try:
                return self._get_text_with_progress(_url, _status_cb = cb, **_kwargs)
            except (requests.Timeout, requests.ConnectionError) as e:
                if attempt < _retries:
                    self.logger.notice(f"URLHelper._get_text_with_progress(): {e.__class__.__name__}: {e}. Retrying in {_backoff:.1f}s…")
                    cb(f"{e.__class__.__name__}: {e}. Retrying in {_backoff:.1f}s…")
                    time.sleep(_backoff)
                    _backoff *= 2
                else:
                    raise
    # --- END OF _get_text_with_progress_retry() -----------------------------------------------------------------------
# --- END OF class ReadData --------------------------------------------------------------------------------------------