#! /usr/bin/python3

# File: ivs_sessions_browser.py

import argparse
import curses
import webbrowser
from datetime import datetime, date
from typing import List, Tuple, Optional, Dict, Any
import re

import requests
from bs4 import BeautifulSoup

# Row = ([columns...], session_url, meta)
Row = Tuple[List[str], Optional[str], Dict[str, Any]]


class SessionBrowser:
    # Column layout (preserve your widths)
    HEADERS = [
        ("Type", 14), ("Code", 8), ("Start", 18), ("DOY", 3), ("Dur", 5),
        ("Stations", 44), ("DB Code", 14), ("Ops Center", 10),
        ("Correlator", 10), ("Status", 20), ("Analysis", 10)
    ]
    HEADER_LINE = " | ".join([f"{title:<{w}}" for title, w in HEADERS])
    WIDTHS = [w for _, w in HEADERS]
    # FIELD_INDEX = {
    #     "type": 0,
    #     "code": 1,
    #     "start": 2,
    #     "doy": 3,
    #     "dur": 4,
    #     "stations": 5,
    #     "db code": 6,
    #     "db": 6,
    #     "ops center": 7,
    #     "ops": 7,
    #     "correlator": 8,
    #     "status": 9,
    #     "analysis": 10,
    # }

    def __init__(
        self,
        year: int,
        scope: str = "both",
        session_filter: Optional[str] = None,
        antenna_filter: Optional[str] = None,
    ) -> None:
        self.year = year
        self.scope = scope  # 'master' | 'intensive' | 'both'
        self.session_filter = session_filter
        self.antenna_filter = antenna_filter  # ACTIVE-only

        self.rows: List[Row] = []
        self.view_rows: List[Row] = []
        self.current_filter: str = ""
        self.selected: int = 0
        self.offset: int = 0

        self.has_colors: bool = False

        # flag for showing/hiding removed sessions in the list
        self.show_removed: bool = True
        # --- patch added by chatgpt 30/8-2025 --- #####################################################################

        # tokens to highlight in Stations column (from a stations:* filter)
        self.highlight_tokens: List[str] = []

        # ------------------ Highlight helpers ------------------

    def _extract_station_tokens(self, query: str) -> List[str]:
        """Pull station codes from any stations-related clause in the current filter."""
        if not query:
            return []

        tokens: List[str] = []
        clauses = [c.strip() for c in query.split(';') if c.strip()]

        for clause in clauses:
            if ':' not in clause:
                continue
            field, value = [p.strip() for p in clause.split(':', 1)]
            fld = field.lower()
            if fld in ("stations", "stations_active", "stations-active",
                       "stations_removed", "stations-removed",
                       "stations_all", "stations-all"):
                parts = re.split(r"[ ,+|&]+", value)
                tokens.extend([p for p in parts if p])

        # Deduplicate; longer-first to avoid partial-overwrite visuals (e.g., 'Ny' vs 'Nya')
        return sorted(set(tokens), key=lambda s: (-len(s), s))

    def _col_start_x(self, col_idx: int) -> int:
        """Compute the x offset where column col_idx starts in the printed line."""
        # Each column is printed left-padded to WIDTHS[c], joined by " | " (3 chars).
        sep = 3
        x = 0

        for i in range(col_idx):
            x += self.WIDTHS[i] + sep
        return x

    # --- END: patch added by chatgpt 30/8-2025 --- ################################################################

    # ------------------ Data ------------------

    @staticmethod
    def _fetch_one(url: str, session_filter: Optional[str], antenna_filter: Optional[str]) -> List[Row]:
        """Fetch and parse ONE IVSCC sessions table URL into rows (case-sensitive CLI filters)."""
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"Error fetching {url}: {exc}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        session_rows = soup.select("table tr")
        parsed: List[Row] = []

        is_intensive = "/intensive/" in url  # mark intensives

        for r in session_rows:
            tds = r.find_all("td")
            if len(tds) < 11:
                continue

            # Stations: split active vs removed, render as "Active [Removed]"
            stations_cell = tds[5]
            active_ids: List[str] = []
            removed_ids: List[str] = []
            for li in stations_cell.find_all("li", class_="station-id"):
                classes = li.get("class", [])
                code = li.get_text(strip=True)
                if "removed" in classes:
                    removed_ids.append(code)
                else:
                    active_ids.append(code)

            active_str = "".join(active_ids)
            removed_str = "".join(removed_ids)
            if active_str and removed_str:
                stations_str = f"{active_str} [{removed_str}]"
            elif removed_str:
                stations_str = f"[{removed_str}]"
            else:
                stations_str = active_str

            values = [
                tds[0].get_text(strip=True),  # Type
                tds[1].get_text(strip=True),  # Code
                tds[2].get_text(strip=True),  # Start
                tds[3].get_text(strip=True),  # DOY
                tds[4].get_text(strip=True),  # Dur
                stations_str.ljust(44),       # Stations (fixed width for alignment)
                tds[6].get_text(strip=True),  # DB Code
                tds[7].get_text(strip=True),  # Ops Center
                tds[8].get_text(strip=True),  # Correlator
                tds[9].get_text(strip=True),  # Status
                tds[10].get_text(strip=True), # Analysis
            ]

            # Column width for Type (class attribute, so prefix with the class)
            TYPE_WIDTH = next(w for title, w in SessionBrowser.HEADERS if title == "Type")
            # Tag intensives directly in Type column (right-align "[I]" in the Type field)
            if is_intensive:
                base_width = max(0, TYPE_WIDTH - 3)  # room for "[I]"
                values[0] = f"{values[0]:<{base_width}}[I]"
            else:
                values[0] = f"{values[0]:<{TYPE_WIDTH}}"

            # Session detail URL from Code column if present
            code_link = tds[1].find("a")
            session_url = f"https://ivscc.gsfc.nasa.gov{code_link['href']}" if code_link and code_link.has_attr("href") else None

            # --- patch added by chatgtp 30/8-2025 --- #################################################################
            # Initial CLI filters (case-sensitive for code; stations use same AND/OR grammar as TUI)
            if session_filter and session_filter not in values[1]:
                continue
            # chatgtp patch --- if antenna_filter and antenna_filter not in active_str:
            # Use the same stations grammar as the TUI (OR '|' and AND '&', space/',' '+' split),
            # applied to ACTIVE stations only for the CLI.
            if antenna_filter and not SessionBrowser._match_stations(active_str, antenna_filter):
                continue

            meta = {"active": active_str, "removed": removed_str}
            parsed.append((values, session_url, meta))

        return parsed

    def _urls_for_scope(self) -> List[str]:
        base = "https://ivscc.gsfc.nasa.gov/sessions"
        y = str(self.year)
        if self.scope == "master":
            return [f"{base}/{y}/"]
        if self.scope == "intensive":
            return [f"{base}/intensive/{y}/"]
        return [f"{base}/{y}/", f"{base}/intensive/{y}/"]

    def fetch_all(self) -> List[Row]:
        rows: List[Row] = []
        print(f"self._urls_for_scope(): {self._urls_for_scope()}")
        ch = input()
        for url in self._urls_for_scope():
            # print(f"url: {url}")
            rows.extend(self._fetch_one(url, self.session_filter, self.antenna_filter))
            # ch = input()
            # print(f"type(rows): {type(rows)}")
            # ch = input()
        return rows

    # ------------------ Filtering ------------------

    @staticmethod
    def _split_tokens(val: str) -> List[str]:
        return [t for t in re.split(r"[ ,+|]+", val) if t]

    @staticmethod
    def _match_stations(hay: str, expr: str) -> bool:
        text = expr.strip()
        if not text:
            return True
        has_or = '|' in text
        has_and = '&' in text
        if has_or or has_and:
            or_parts = [p.strip() for p in re.split(r"\s*\|{1,2}\s*", text) if p.strip()]
            for part in or_parts:
                and_chunks = [c.strip() for c in re.split(r"\s*&{1,2}\s*", part) if c.strip()]
                and_tokens: List[str] = []
                for chunk in and_chunks:
                    and_tokens.extend([t for t in re.split(r"[ ,+]+", chunk) if t])
                if and_tokens and all(tok in hay for tok in and_tokens):
                    return True
                if not and_tokens and part and part in hay:
                    return True
            return False
        tokens = [t for t in re.split(r"[ ,+]+", text) if t]
        return all(tok in hay for tok in tokens)

    def apply_filter(self, query: str) -> List[Row]:
        if not query:
            return self.rows
        clauses = [c.strip() for c in query.split(';') if c.strip()]
        if not clauses:
            return self.rows

        def clause_match(row: Row, clause: str) -> bool:
            values, _, meta = row
            if ':' in clause:
                field, value = [p.strip() for p in clause.split(':', 1)]
                fld = field.lower()
                idx = self.FIELD_INDEX.get(fld)
                if fld in ("stations", "stations_active", "stations-active"):
                    return self._match_stations(meta["active"], value)
                if fld in ("stations_removed", "stations-removed"):
                    return self._match_stations(meta["removed"], value)
                if fld in ("stations_all", "stations-all"):
                    return self._match_stations(meta["active"] + " " + meta["removed"], value)
                if idx is None:
                    return False
                hay = values[idx]
                tokens = self._split_tokens(value)
                return any(tok in hay for tok in tokens)
            return any(clause in col for col in values)

        return [r for r in self.rows if all(clause_match(r, c) for c in clauses)]

    # ------------------ Curses UI helpers ------------------

    @staticmethod
    def _addstr_clip(stdscr, y: int, x: int, text: str, attr: int = 0) -> None:
        max_y, max_x = stdscr.getmaxyx()
        if y >= max_y or x >= max_x:
            return
        stdscr.addstr(y, x, text[: max_x - x - 1], attr)

    @staticmethod
    def _get_input(stdscr, prompt: str) -> str:
        curses.curs_set(1)
        max_y, max_x = stdscr.getmaxyx()
        buf: List[str] = []
        while True:
            line = (prompt + "".join(buf))[: max_x - 1]
            SessionBrowser._addstr_clip(stdscr, max_y - 1, 0, " " * (max_x - 1))
            SessionBrowser._addstr_clip(stdscr, max_y - 1, 0, line, curses.A_REVERSE)
            stdscr.move(max_y - 1, min(len(line), max_x - 2))
            ch = stdscr.getch()
            if ch in (10, curses.KEY_ENTER):
                break
            if ch == 27:
                buf = []
                break
            if ch in (curses.KEY_BACKSPACE, 127, 8):
                if buf:
                    buf.pop()
                continue
            if 32 <= ch <= 126:
                buf.append(chr(ch))
        curses.curs_set(0)
        return "".join(buf).strip()

    @staticmethod
    def _status_color(has_colors: bool, status_text: str) -> int:
        """Map status text to a curses color pair.
        4=green(released), 5=yellow(processing/waiting), 6=magenta(cancelled), 7=red(none)."""
        if not has_colors:
            return 0
        st = status_text.strip().lower()
        if "released" in st:
            return curses.color_pair(4)
        if any(k in st for k in ("waiting on media", "ready for processing", "cleaning up", "processing session")):
            return curses.color_pair(5)
        if "cancelled" in st or "canceled" in st:  # handle both spellings
            return curses.color_pair(6)
        if st == "":
            return curses.color_pair(7)
        return 0



    # ------------------ Curses UI drawing ------------------

    def _draw_header(self, stdscr) -> None:
        header_attr = curses.A_BOLD | (curses.color_pair(2) if self.has_colors else 0)
        self._addstr_clip(stdscr, 0, 0, self.HEADER_LINE, header_attr)
        self._addstr_clip(stdscr, 1, 0, "-" * len(self.HEADER_LINE))

    # --- re-drawn to fix indentation errors
    #def _draw_rows(self, stdscr) -> None:
    #    max_y, _ = stdscr.getmaxyx()
    #    view_height = max(1, max_y - 3)

    #    if self.selected < self.offset:
    #        self.offset = self.selected
    #    elif self.selected >= self.offset + view_height:
    #        self.offset = self.selected - view_height + 1

    #    if not self.view_rows:
    #        self._addstr_clip(stdscr, 2, 0, "No sessions found.")
    #        return

    #    # --- patch added by chatgtp 30/8-2025 --- #####################################################################
    #    for i in range(self.offset, min(len(self.view_rows), self.offset + view_height)):
    #        row_vals, _, meta = self.view_rows[i]

    #        # COPY so we can override Stations column safely
    #        vals = list(row_vals)

    #        # If hiding removed stations, render active-only in col 5
    #        if not self.show_removed:
    #            active_only = meta.get("active", "")
    #            vals[5] = f"{active_only:<{self.WIDTHS[5]}}"

    #        parts = [f"{val:<{self.WIDTHS[c]}}" for c, val in enumerate(vals)]
    #        full_line = " | ".join(parts)
    #        y = i - self.offset + 2
    #        row_attr = curses.A_REVERSE if i == self.selected else 0

    #        row_color = self._status_color(self.has_colors, vals[9])
    #        self._addstr_clip(stdscr, y, 0, full_line, row_attr | row_color)

    #        # Highlight "[...]" only if we are showing removed stations
    #        if self.has_colors and self.show_removed and vals[5]:
    #            lbr = full_line.find("[")
    #            if lbr != -1:
    #                rbr = full_line.find("]", lbr + 1)
    #                if rbr != -1 and rbr > lbr:
    #                    self._addstr_clip(stdscr, y, lbr, full_line[lbr:rbr + 1], row_attr | curses.color_pair(1))

    #    #--- added by chatgtp 30/8-2025 ---#############################################################################
    #    # Station token highlighting (from stations:* filters)
    #    if vals[5] and self.highlight_tokens:
    #        stations_text = vals[5]  # padded field text as printed
    #        col_x = self._col_start_x(5)  # Stations column index is 5
    #        hl_attr = (curses.color_pair(8) | curses.A_BOLD) if self.has_colors else (curses.A_REVERSE | curses.A_BOLD)
    #        for tok in self.highlight_tokens:
    #            start = 0
    #            while True:
    #                j = stations_text.find(tok, start)
    #                if j == -1:
    #                    break
    #                self._addstr_clip(stdscr, y, col_x + j, tok, row_attr | hl_attr)
    #                start = j + len(tok)

    #    # --- END: added by chatgtp 30/8-2025 ---#######################################################################
    # --- END OF: re-drawn to fix indentation errors
    def _draw_rows(self, stdscr) -> None:
        max_y, _ = stdscr.getmaxyx()
        view_height = max(1, max_y - 3)

        if self.selected < self.offset:
            self.offset = self.selected
        elif self.selected >= self.offset + view_height:
            self.offset = self.selected - view_height + 1

        if not self.view_rows:
            self._addstr_clip(stdscr, 2, 0, "No sessions found.")
            return

        # draw each visible row
        for i in range(self.offset, min(len(self.view_rows), self.offset + view_height)):
            row_vals, _, meta = self.view_rows[i]

            # COPY so we can override Stations column safely
            vals = list(row_vals)

            # If hiding removed stations, render active-only in col 5
            if not self.show_removed:
                active_only = meta.get("active", "")
                vals[5] = f"{active_only:<{self.WIDTHS[5]}}"

            parts = [f"{val:<{self.WIDTHS[c]}}" for c, val in enumerate(vals)]
            full_line = " | ".join(parts)
            y = i - self.offset + 2
            row_attr = curses.A_REVERSE if i == self.selected else 0

            row_color = self._status_color(self.has_colors, vals[9])
            self._addstr_clip(stdscr, y, 0, full_line, row_attr | row_color)

            # Highlight "[...]" only if we are showing removed stations
            if self.has_colors and self.show_removed and vals[5]:
                lbr = full_line.find("[")
                if lbr != -1:
                    rbr = full_line.find("]", lbr + 1)
                    if rbr != -1 and rbr > lbr:
                        self._addstr_clip(stdscr, y, lbr, full_line[lbr:rbr + 1], row_attr | curses.color_pair(1))

            # Station token highlighting (from stations:* filters)
            if vals[5] and self.highlight_tokens:
                stations_text = vals[5]  # padded field text as printed
                col_x = self._col_start_x(5)  # Stations column index is 5
                # Fallback without colors: underline+bold (shows even on selected/reversed rows)
                hl_attr = (curses.color_pair(8) | curses.A_BOLD) if self.has_colors else (
                            curses.A_BOLD | curses.A_UNDERLINE)
                for tok in self.highlight_tokens:
                    start = 0
                    while True:
                        j = stations_text.find(tok, start)
                        if j == -1:
                            break
                        self._addstr_clip(stdscr, y, col_x + j, tok, row_attr | hl_attr)
                        start = j + len(tok)

    def _draw_helpbar(self, stdscr) -> None:
        max_y, max_x = stdscr.getmaxyx()
        help_text = "↑↓ Move  PgUp/PgDn  Home/End  Enter Open  '/' Filter  T Today  F ClearFilter R Show/hide removed  ? Help  q Quit  stations: AND(&) OR(|)  "
        right = f"row {min(self.selected + 1, len(self.view_rows))}/{len(self.view_rows)}"
        bar = (help_text + (f"filter: {self.current_filter}" if self.current_filter else "") + "  " + right)[: max_x - 1]
        bar_attr = curses.color_pair(3) if self.has_colors else curses.A_REVERSE
        self._addstr_clip(stdscr, max_y - 1, 0, bar, bar_attr)

    # ------------------ Help popup ------------------

    def _show_help(self, stdscr) -> None:
        lines = [
            "IVS Session Browser Help",
            "",
            "Navigation:",
            "  ↑/↓ : Move selection",
            "  PgUp/PgDn : Page up/down",
            "  Home/End : Jump to first/last",
            "  T : Jump to today's session",
            "  Enter : Open session in browser",
            "",
            "Filtering:",
            "  / : Enter filter (field:value, supports AND/OR)",
            "  F : Clear filters",
            "  R : Toggle show/hide removed stations",
            "",
            "Other:",
            "  q or ESC : Quit",
            "  ? : Show this help",
            "",
            "Color legend:",
            "  Green    = Released",
            "  Yellow   = Processing / Waiting",
            "  Magenta  = Cancelled",
            "  White    = No status",
            "  Cyan     = Active filters",
        ]
        h, w = stdscr.getmaxyx()
        width = min(84, w - 4)
        height = min(len(lines) + 4, h - 4)
        y, x = (h - height)//2, (w - width)//2
        win = curses.newwin(height, width, y, x)
        win.box()
        title_attr = curses.A_BOLD
        for i, text in enumerate(lines, start=1):
            attr = title_attr if i == 1 else 0
            win.addnstr(i, 2, text, width - 4, attr)
        win.refresh()
        win.getch()

    # ------------------ Main loop ------------------

    def _curses_main(self, stdscr) -> None:
        curses.curs_set(0)
        stdscr.clear()

        self.has_colors = curses.has_colors()
        if self.has_colors:
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_YELLOW, -1)                # removed stations
            curses.init_pair(2, curses.COLOR_CYAN, -1)                  # header
            curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE) # help bar
            curses.init_pair(4, curses.COLOR_GREEN, -1)                 # released
            curses.init_pair(5, curses.COLOR_YELLOW, -1)                # processing
            curses.init_pair(6, curses.COLOR_MAGENTA, -1)               # cancelled
            curses.init_pair(7, curses.COLOR_WHITE, -1)                  # none
            # --- added by chatgpt 30/8-2025 ---
            curses.init_pair(8, curses.COLOR_CYAN, -1)                   # station highlight

        while True:
            stdscr.clear()
            self._draw_header(stdscr)
            self._draw_rows(stdscr)
            self._draw_helpbar(stdscr)

            ch = stdscr.getch()
            if ch == curses.KEY_UP and self.selected > 0:
                self.selected -= 1
            elif ch == curses.KEY_DOWN and self.selected < len(self.view_rows) - 1:
                self.selected += 1
            elif ch == curses.KEY_NPAGE:
                max_y, _ = stdscr.getmaxyx()
                page = max(1, max_y - 3)
                self.selected = min(self.selected + page, len(self.view_rows) - 1)
            elif ch == curses.KEY_PPAGE:
                max_y, _ = stdscr.getmaxyx()
                page = max(1, max_y - 3)
                self.selected = max(self.selected - page, 0)
            elif ch == curses.KEY_HOME:
                self.selected = 0
            elif ch == curses.KEY_END:
                self.selected = max(0, len(self.view_rows) - 1)
            elif ch in (ord('t'), ord('T')):
                # Jump to today's date
                idx = index_on_or_after_today(self.view_rows)
                self.selected = idx
                self.offset = idx
            elif ch in (10, curses.KEY_ENTER):
                if self.view_rows:
                    _, url, _ = self.view_rows[self.selected]
                    if url:
                        webbrowser.open(url)
            elif ch == ord('/'):
                q = self._get_input(stdscr, "/ ")
                self.current_filter = q
                self.view_rows = self.apply_filter(q)
                # --- added by chatgpt 30/8-2025 ---
                self.highlight_tokens = self._extract_station_tokens(self.current_filter)

                #with open("out.txt", "a", encoding="utf-8") as f:
                #    print(self.highlight_tokens, file=f)  # adds newline automatically

                idx = index_on_or_after_today(self.view_rows)
                self.selected = idx
                self.offset = idx
            elif ch == ord('F'):
                self.current_filter = ""
                self.view_rows = self.rows
                # --- added by chatgpt 30/8-2025 ---
                self.highlight_tokens = []
                idx = index_on_or_after_today(self.view_rows)
                self.selected = idx
                self.offset = idx
            elif ch in (ord('r'), ord('R')):
                self.show_removed = not self.show_removed
            elif ch == ord('?'):
                self._show_help(stdscr)
            elif ch in (ord('q'), 27):
                break

    # ------------------ Public ------------------

    def load_data(self) -> None:
        self.rows = self.fetch_all()
        self.rows = sort_by_start(self.rows)  # chronological

        self.view_rows = list(self.rows)

        # Jump to first row on/after today
        idx = index_on_or_after_today(self.view_rows)
        self.selected = idx
        self.offset = idx  # makes it the first visible line

        # --- added by chatgpt 30/8-2025 --- ###########################################################################
        # If launched with --antenna, use it as an initial highlight hint
        #if self.antenna_filter:
        #    self.highlight_tokens = [self.antenna_filter]
        # If launched with --stations/--antenna, seed highlight tokens using the same split logic
        if self.antenna_filter:
            toks = [t for t in re.split(r"[ ,+|&]+", self.antenna_filter) if t]
            # longer-first avoids partial overwrites ('Ny' inside 'Nya')
            self.highlight_tokens = sorted(set(toks), key=lambda s: (-len(s), s))
        # --- END: added by chatgpt 30/8-2025 --- ######################################################################

    def run(self) -> None:
        self.load_data()
        curses.wrapper(self._curses_main)


def sort_by_start(rows: List[Row]) -> List[Row]:
    def keyfunc(row: Row):
        start_str = row[0][2]
        try:
            return datetime.strptime(start_str, "%Y-%m-%d %H:%M")
        except ValueError:
            return datetime.min
    return sorted(rows, key=keyfunc)


def index_on_or_after_today(rows: List[Row]) -> int:
    """Return index of first row whose Start date is today or later.
    If all are before today, return last index; if empty, return 0."""
    if not rows:
        return 0
    today_d: date = datetime.now().date()
    for i, r in enumerate(rows):
        start_str = r[0][2]
        try:
            d = datetime.strptime(start_str, "%Y-%m-%d %H:%M").date()
        except ValueError:
            continue
        if d >= today_d:
            return i
    return len(rows) - 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="IVS Sessions TUI Browser",
        epilog=(
            "Filters (case-sensitive):\n"
            "  Clauses separated by ';' are AND.\n"
            "  Non-stations fields: tokens split by space/comma/plus/pipe are OR (e.g. code: R1|R4)\n"
            "  Stations active: stations: Nn&Ns  or  stations: Nn|Ns\n"
            "  Stations removed/any: stations_removed: Ft|Ur   stations_all: Hb|Ht\n"
            "\nCLI:\n"
            "  --stations uses the same grammar as 'stations:' and applies to ACTIVE stations.\n"
            "  --antenna is deprecated and behaves like --stations.\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--year", type=int, default=datetime.now().year, help="Year (default: current year)")
    parser.add_argument("--scope", choices=("master", "intensive", "both"), default="both",
                        help="Which schedules to include (default: both)")
    parser.add_argument("--session", type=str, help="Initial filter: session code (case-sensitive)")
    parser.add_argument("--stations", type=str, help="Initial filter for ACTIVE stations (same grammar as 'stations:')")
    parser.add_argument("--antenna", type=str, help="(Deprecated) Same as --stations")
    #parser.add_argument("--session", type=str, help="Initial filter: session code (case-sensitive)")
    #parser.add_argument("--antenna", type=str, help="Initial filter: ACTIVE station/antenna (case-sensitive)")
    args = parser.parse_args()

    cli_stations = args.stations or args.antenna
    # print(f"year:           {args.year}")
    # print(f"scope:          {args.scope}")
    # print(f"session_filter: {args.session}")
    # print(f"cli_stations:   {cli_stations}")

    SessionBrowser(
        year=args.year,
        scope=args.scope,
        session_filter=args.session,
        antenna_filter=cli_stations
    ).run()


if __name__ == "__main__":
    main()