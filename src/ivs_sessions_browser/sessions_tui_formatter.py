"""SessionsTuiFormatter

Scan a BeautifulSoup `soup` and produce formatted lines for the TUI.

This module provides a small, dependency-light formatter that uses
heuristics to find session-like elements in the parsed HTML and
convert them into single-line strings suitable for a text UI.
"""
from typing import Iterator

from bs4 import BeautifulSoup, Tag


class SessionsTuiFormatter:
    """
    Format parsed IVS session HTML into TUI-ready lines.

    The implementation uses simple heuristics (elements with class
    `session`, table rows, list items) to find candidate elements and
    converts them to readable, single-line strings. The behaviour is
    intentionally conservative so callers can replace or extend it.
    """

    def __init__(self,
                 _soup: BeautifulSoup,
                 _num_of_headers: int,
                 _is_intensive: bool,
                 _filters) -> None:

        self.soup = _soup
        self.num_of_headers = _num_of_headers
        self.is_intensive = _is_intensive
