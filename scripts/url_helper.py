########################################################################################################################
#   file:       url_helper.py
#   author:     jole 2025
#   content:    something
########################################################################################################################

# --- todo section -----------------------------------------------------------------------------------------------------
# --- todo:
# --- END OF todo section ----------------------------------------------------------------------------------------------

## Import section ######################################################################################################
import time
import requests
import logging

from bs4    import BeautifulSoup
from typing import Callable, Optional, List, Tuple, Dict, Any
## END OF Import section ###############################################################################################


# --- Classes in Python has methods and attributes ---------------------------------------------------------------------
# --- and there's a difference between instance methods and attributes, and class methods and attributes ---------------
# --- Perhaps this class should just retrieve the data, and I make a different class, more specific to the transfers and
# --- what I'd like to get out of that...
class URLHelper:
    # --- __init__() method, or constructor if you like ----------------------------------------------------------------
    # --- It initialises the string 'url_string' with the string from the parameter '_url'
    # --- It initialises the string 'site' with the result from calling the instance method _fetch_website(), this
    # --- method uses the instance variable url_string to look up and return the contents of the site
    # --- It then runs the site content through BeautifulSoup, putting the result in soup attribute
    # --- Then the site content is parsed, using BeautifulSoup package in the instance method _parse_soup()
    def __init__(self,
                 _url: str,
                 _logger: logging.Logger
                 ):
        self.url_string: str    = _url
        self.logger             = _logger

        self.site: str          = self._fetch_website()
        # self.soup = BeautifulSoup(self.site, "html.parser")
    # --- END OF __init__() method, or constructor if you like ---------------------------------------------------------

    # --- url() method -------------------------------------------------------------------------------------------------
    # --- returns the url as string, to be called from outside
    def url(self) -> str:
        return '{}'.format(self.url_string)
    # --- END OF url() method ------------------------------------------------------------------------------------------



    ####################################################################################################################
    ### TEXT HELPERS ###################################################################################################
    ####################################################################################################################
    # --- helper to print feedback to the user. This one prints feedback on a new line - not in use....-----------------
    def _set_status_line(self, msg: str) -> None:
        print(msg)
    # --- END OF _set_status_line() ------------------------------------------------------------------------------------

    # --- helper to print feedback to the user. This one prints on the same line, clearing it between feedbacks --------
    # --- at the end, it prints a message telling the user download is done! -------------------------------------------
    def status_inline(self, msg: str) -> None:
        #self.logger.info(f"\r{msg}")
        print(f"\r{msg}", end="", flush=True)
    # --- END OF _status_inline() --------------------------------------------------------------------------------------



    ####################################################################################################################
    ### FETCHING THE DATA ##############################################################################################
    ####################################################################################################################
    # --- downloads from web giving feedback to the user of the progress ###############################################
    def _get_text_with_progress(self,
                                _url: str,
                                *, _timeout=(5, 20),
                                _status_cb: Optional[Callable[[str], None]] = None,
                                _chunk_size: int = 65536,
                                _min_update_interval: float = 0.10
                                ) -> str:
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
                self.logger.notice(f"Download complete: {got}/{total} bytes.")
                # print a newline after it finishes to clean up user prompt
                print()
            else:
                cb(f"Download complete: {got} bytes.")
                self.logger.notice(f"Download complete: {got} bytes.")
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



    # --- downloads from web giving feedback to the user of the progress ###############################################
    def get_text_with_progress_retry(self,
                                      _url: str,
                                      *,
                                      _retries: int = 2,
                                      _backoff: float = 0.5,
                                      _status_cb: Optional[Callable[[str],None]] = None,
                                      **_kwargs,
                                      ) -> str:

        cb = _status_cb or (lambda _msg: None)
        for attempt in range(_retries + 1):
            try:
                return self._get_text_with_progress(_url, _status_cb = cb, **_kwargs)
            except (requests.Timeout, requests.ConnectionError) as e:
                if attempt < _retries:
                    self.logger.notice(f"{e.__class__.__name__}: {e}. Retrying in {_backoff:.1f}s…")
                    cb(f"{e.__class__.__name__}: {e}. Retrying in {_backoff:.1f}s…")
                    time.sleep(_backoff)
                    _backoff *= 2
                else:
                    raise

    # --- END OF _get_text_with_progress_retry() -----------------------------------------------------------------------



    # --- _fetch_website() method --------------------------------------------------------------------------------------
    # --- fetches the content of the website pointed to by the attribute self.url_string, and places it in
    # --- self.response, returning the text property of self.response, self.response.text
    def _fetch_website(self, _timeout: float = 20) -> str:

        # Validate URL early (empty or whitespace-only)
        if not isinstance(self.url_string, str) or not self.url_string.strip():
            self.logger.warning("url must be a non-empty string")
            raise ValueError("url must be a non-empty string")

        # avoid stale response if this attempt fails
        self.response = None

        try:
            # Tip: consider a (connect, read) tuple timeout, e.g., (5, 20)
            resp = requests.get(
                self.url_string,
                timeout=_timeout,
                headers={"User-Agent": "Mozilla/5.0 (compatible; TransferStatus/1.0)"},
            )
            resp.raise_for_status()

            # Respect server-provided encoding; fall back to detection if missing
            if not resp.encoding:
                resp.encoding = resp.apparent_encoding

            self.response = resp  # only set after success
            return self.response.text

        except requests.Timeout as exc:
            # Specific message for common case
            self.logger.warning(f"Timeout fetching {self.url_string}")
            raise RuntimeError(f"Timeout fetching {self.url_string}") from exc
        except requests.HTTPError as exc:
            # Includes status code info in str(exc)
            self.logger.warning(f"HTTP error fetching {self.url_string}: {exc}")
            raise RuntimeError(f"HTTP error fetching {self.url_string}: {exc}") from exc
        except requests.RequestException as exc:
            # ConnectionError, SSLError, InvalidURL, etc.
            self.logger.warning(f"Request error fetching {self.url_string}: {exc}")
            raise RuntimeError(f"Request error fetching {self.url_string}: {exc}") from exc
    # --- END OF _fetch_website() method -------------------------------------------------------------------------------



    # # --- soup_pretty() method -----------------------------------------------------------------------------------------
    # # --- returns the prettified soup object from the instance
    # def soup_pretty(self) -> str:
    #     #return self.soup.prettify()
    #     return '{}'.format(self.soup.prettify())
    # # --- END OF soup_pretty() method ----------------------------------------------------------------------------------
# --- END OF class URLHelper -------------------------------------------------------------------------------------------