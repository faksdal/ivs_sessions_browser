import requests
from bs4 import BeautifulSoup


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
    def __init__(self, _url: str):
        self.url_string: str    = _url
        self.site: str          = self._fetch_website()
        self.soup = BeautifulSoup(self.site, "html.parser")
    # --- END OF __init__() method, or constructor if you like ---------------------------------------------------------

    # --- url() method -------------------------------------------------------------------------------------------------
    # --- returns the url as string, to be called from outside
    def url(self) -> str:
        return '{}'.format(self.url_string)
    # --- END OF url() method ------------------------------------------------------------------------------------------

    # --- _fetch_website() method --------------------------------------------------------------------------------------
    # --- fetches the content of the website pointed to by the attribute self.url_string, and places it in
    # --- self.response, returning the text property of self.response, self.response.text
    def _fetch_website(self, timeout: float = 20) -> str:

        # Validate URL early (empty or whitespace-only)
        if not isinstance(self.url_string, str) or not self.url_string.strip():
            raise ValueError("url must be a non-empty string")

        self.response = None  # avoid stale response if this attempt fails

        try:
            # Tip: consider a (connect, read) tuple timeout, e.g., (5, 20)
            resp = requests.get(
                self.url_string,
                timeout=timeout,
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
            raise RuntimeError(f"Timeout fetching {self.url_string}") from exc
        except requests.HTTPError as exc:
            # Includes status code info in str(exc)
            raise RuntimeError(f"HTTP error fetching {self.url_string}: {exc}") from exc
        except requests.RequestException as exc:
            # ConnectionError, SSLError, InvalidURL, etc.
            raise RuntimeError(f"Request error fetching {self.url_string}: {exc}") from exc

    # --- END OF _fetch_website() method -------------------------------------------------------------------------------

    # --- soup_pretty() method -----------------------------------------------------------------------------------------
    # --- returns the prettified soup object from the instance
    def soup_pretty(self) -> str:
        #return self.soup.prettify()
        return '{}'.format(self.soup.prettify())
    # --- END OF soup_pretty() method ----------------------------------------------------------------------------------

    # --- _parse_soup() method -----------------------------------------------------------------------------------------
    # --- Intended use: parsing the soup based on user input.
    #def _parse_soup(self):
    #    print(f"{self.soup}")
    # --- END OF _parse_soup() method ----------------------------------------------------------------------------------
