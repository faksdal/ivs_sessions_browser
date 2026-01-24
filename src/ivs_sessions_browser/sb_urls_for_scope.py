


from __future__ import annotations

from .defs import IVSCC_BASE_URLS, SessionsBrowserLike


class SessionsBrowserUrlsForScopeMixin:
    def _urls_for_scope(self: SessionsBrowserLike) -> list[str]:
        """
        Defined in sb_urls_for_scope.py.
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
# ─── END OF _urls_for_scope() ─────────────────────────────────────────────────
