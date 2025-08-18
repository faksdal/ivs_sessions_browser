# File: ivs_sessions_browser.py

import argparse
import curses
import webbrowser
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
import re

import requests
from bs4 import BeautifulSoup

# Row = ([columns...], session_url, meta)
Row = Tuple[List[str], Optional[str], Dict[str, Any]]


class SessionBrowser:
    # Column layout (preserve your widths)
    HEADERS = [
        ("Type", 13), ("Code", 8), ("Start", 18), ("DOY", 3), ("Dur", 5),
        ("Stations", 44), ("DB Code", 14), ("Ops Center", 10),
        ("Correlator", 10), ("Status", 20), ("Analysis", 10)
    ]
    HEADER_LINE = " | ".join([f"{title:<{w}}" for title, w in HEADERS])
    WIDTHS = [w for _, w in HEADERS]
    FIELD_INDEX = {
        "type": 0,
        "code": 1,
        "start": 2,
        "doy": 3,
        "dur": 4,
        "stations": 5,          # display column string (Active [Removed])
        "db code": 6,
        "db": 6,
        "ops center": 7,
        "ops": 7,
        "correlator": 8,
        "status": 9,
        "analysis": 10,
    }

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
                stations_str.ljust(44),  # Stations (fixed width for alignment)
                tds[6].get_text(strip=True),  # DB Code
                tds[7].get_text(strip=True),  # Ops Center
                tds[8].get_text(strip=True),  # Correlator
                tds[9].get_text(strip=True),  # Status
                tds[10].get_text(strip=True),  # Analysis
            ]

            # Tag intensives directly in Type column (keeps alignment).
            if is_intensive:
                values[0] = f"{values[0]}[I]"

            # Session detail URL from Code column if present
            code_link = tds[1].find("a")
            session_url = f"https://ivscc.gsfc.nasa.gov{code_link['href']}" if code_link and code_link.has_attr(
                "href") else None

            # Initial CLI filters (case-sensitive)
            if session_filter and session_filter not in values[1]:
                continue
            if antenna_filter and antenna_filter not in active_str:
                continue

            meta = {"active": active_str, "removed": removed_str}
            parsed.append((values, session_url, meta))

        return parsed

    """
    def _fetch_one(self, url: str, session_filter: Optional[str], antenna_filter: Optional[str]) -> List[Row]:
    def _fetch_one(url: str, session_filter: Optional[str], antenna_filter: Optional[str]) -> List[Row]:
        # Fetch and parse ONE IVSCC sessions table URL into rows (case-sensitive CLI filters).
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"Error fetching {url}: {exc}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        session_rows = soup.select("table tr")
        parsed: List[Row] = []

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

            # Session detail URL from Code column if present
            code_link = tds[1].find("a")
            session_url = f"https://ivscc.gsfc.nasa.gov{code_link['href']}" if code_link and code_link.has_attr("href") else None

            # Initial CLI filters (case-sensitive)
            if session_filter and session_filter not in values[1]:
                continue
            if antenna_filter and antenna_filter not in active_str:
                # IMPORTANT: CLI antenna filter checks ACTIVE-ONLY
                continue

            meta = {"active": active_str, "removed": removed_str}
            parsed.append((values, session_url, meta))

        return parsed
        """

    def _urls_for_scope(self) -> List[str]:
        base = "https://ivscc.gsfc.nasa.gov/sessions"
        year = str(self.year)
        if self.scope == "master":
            return [f"{base}/{year}/"]
        if self.scope == "intensive":
            return [f"{base}/intensive/{year}/"]
        # both
        return [f"{base}/{year}/", f"{base}/intensive/{year}/"]

    def fetch_all(self) -> List[Row]:
        """Fetch and merge rows from selected scope."""
        rows: List[Row] = []
        for url in self._urls_for_scope():
            rows.extend(self._fetch_one(url, self.session_filter, self.antenna_filter))
        return rows

    # ------------------ Filtering ------------------

    @staticmethod
    def _split_tokens(val: str) -> List[str]:
        """Split on space/comma/plus/pipe for non-stations fields (OR semantics)."""
        return [t for t in re.split(r"[ ,+|]+", val) if t]

    @staticmethod
    def _match_stations(hay: str, expr: str) -> bool:
        """
        stations filter with AND/OR:
          - '|' or '||' separate OR-groups.
          - '&' or '&&' mean AND inside a group.
          - Within each AND group, space/comma/plus are also AND.
          - If no '&' or '|' present, default AND over space/comma/plus.
        Case-sensitive.
        """
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
        """
        Filtering (case-sensitive).
        Clauses: separated by ';' (AND across clauses).
        Fielded clause: "field: value".
          - stations / stations_active: ACTIVE-only, supports '&'/'&&' and '|'/'||'.
          - stations_removed: REMOVED-only, supports '&'/'&&' and '|'/'||'.
          - stations_all: active OR removed, supports '&'/'&&' and '|'/'||'.
          - other fields: tokens split by space/comma/plus/pipe are OR.
        Plain clause: searched in any column.
        """
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
                idx = self.FIELD_INDEX.get(fld)  # may be None for stations_* pseudo-fields

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
        if not has_colors:
            return 0
        st_lower = status_text.lower()
        if "released" in st_lower:
            return curses.color_pair(4)
        if any(k in st_lower for k in ("waiting on media", "ready for processing", "cleaning up", "processing session")):
            return curses.color_pair(5)
        if status_text.strip() == "" or "cancelled" in st_lower:
            return curses.color_pair(6)
        return 0

    # ------------------ Curses UI drawing ------------------

    def _draw_header(self, stdscr) -> None:
        header_attr = curses.A_BOLD | (curses.color_pair(2) if self.has_colors else 0)
        self._addstr_clip(stdscr, 0, 0, self.HEADER_LINE, header_attr)
        self._addstr_clip(stdscr, 1, 0, "-" * len(self.HEADER_LINE))

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

        for i in range(self.offset, min(len(self.view_rows), self.offset + view_height)):
            row_vals, _, _ = self.view_rows[i]
            parts = [f"{val:<{self.WIDTHS[c]}}" for c, val in enumerate(row_vals)]
            full_line = " | ".join(parts)
            y = i - self.offset + 2
            row_attr = curses.A_REVERSE if i == self.selected else 0

            row_color = self._status_color(self.has_colors, row_vals[9])
            self._addstr_clip(stdscr, y, 0, full_line, row_attr | row_color)

            # Highlight removed stations "[...]" inline (overrides row color)
            if self.has_colors and row_vals[5]:
                lbr = full_line.find("[")
                if lbr != -1:
                    rbr = full_line.find("]", lbr + 1)
                    if rbr != -1 and rbr > lbr:
                        self._addstr_clip(stdscr, y, lbr, full_line[lbr:rbr+1], row_attr | curses.color_pair(1))

    def _draw_helpbar(self, stdscr) -> None:
        max_y, max_x = stdscr.getmaxyx()
        help_text = "↑↓ Move  PgUp/PgDn  Home/End  Enter Open  '/' Filter  F ClearFilter  ? Help  q Quit  stations: AND(&) OR(|)  "
        right = f"row {min(self.selected + 1, len(self.view_rows))}/{len(self.view_rows)}"
        bar = (help_text + (f"filter: {self.current_filter}" if self.current_filter else "") + "  " + right)[: max_x - 1]
        bar_attr = curses.color_pair(3) if self.has_colors else curses.A_REVERSE
        self._addstr_clip(stdscr, max_y - 1, 0, bar, bar_attr)

    # ------------------ Help popup ------------------

    def _show_help(self, stdscr) -> None:
        lines = [
            "IVS Sessions TUI Browser — Help",
            "",
            "Keys:",
            "  ↑/↓ Move    PgUp/PgDn Page    Home/End Jump",
            "  Enter Open session URL",
            "  / Filter     F Clear Filter    ? Help   q/Esc Quit",
            "",
            "Filters (case-sensitive):",
            "  Clauses separated by ';' are AND between clauses.",
            "  Non-stations fields: tokens split by space/comma/plus/pipe are OR (e.g. code: R1|R4)",
            "  Stations (active-only): AND with '&' (or spaces), OR with '|'",
            "  Also: stations_removed: …   stations_all: …",
            "",
            "Press any key to close.",
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
            curses.init_pair(1, curses.COLOR_YELLOW, -1)  # removed stations
            curses.init_pair(2, curses.COLOR_CYAN, -1)    # header
            curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)  # help bar
            curses.init_pair(4, curses.COLOR_GREEN, -1)   # released
            curses.init_pair(5, curses.COLOR_YELLOW, -1)  # processing
            curses.init_pair(6, curses.COLOR_RED, -1)     # none/cancelled

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
            elif ch in (10, curses.KEY_ENTER):
                if self.view_rows:
                    _, url, _ = self.view_rows[self.selected]
                    if url:
                        webbrowser.open(url)
            elif ch == ord('/'):
                q = self._get_input(stdscr, "/ ")
                self.current_filter = q
                self.view_rows = self.apply_filter(q)
                self.selected = 0
                self.offset = 0
            elif ch == ord('F'):
                self.current_filter = ""
                self.view_rows = self.rows
                self.selected = 0
                self.offset = 0
            elif ch == ord('?'):
                self._show_help(stdscr)
            elif ch in (ord('q'), 27):
                break

    # ------------------ Public ------------------

    def load_data(self) -> None:
        self.rows = self.fetch_all()
        self.rows = sort_by_start(self.rows)  # added by jole, sorts the list by date

        self.view_rows = list(self.rows)

    def run(self) -> None:
        self.load_data()
        curses.wrapper(self._curses_main)



def sort_by_start(rows: List[Row]) -> List[Row]:
    def keyfunc(row: Row):
        start_str = row[0][2]  # "Start" column
        try:
            return datetime.strptime(start_str, "%Y-%m-%d %H:%M")
        except ValueError:
            return datetime.min
    return sorted(rows, key=keyfunc)



def main() -> None:
    parser = argparse.ArgumentParser(
        description="IVS Sessions TUI Browser",
        epilog=(
            "Filters (case-sensitive):\n"
            "  Clauses separated by ';' are AND.\n"
            "  Non-stations fields: tokens split by space/comma/plus/pipe are OR (e.g. code: R1|R4)\n"
            "  Stations active: stations: Nn&Ns  or  stations: Nn|Ns\n"
            "  Stations removed/any: stations_removed: Ft|Ur   stations_all: Hb|Ht\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--year", type=int, default=datetime.now().year, help="Year (default: current year)")
    parser.add_argument("--scope", choices=("master", "intensive", "both"), default="both",
                        help="Which schedules to include (default: both)")
    parser.add_argument("--session", type=str, help="Initial filter: session code (case-sensitive)")
    parser.add_argument("--antenna", type=str, help="Initial filter: ACTIVE station/antenna (case-sensitive)")
    args = parser.parse_args()

    SessionBrowser(
        year=args.year,
        scope=args.scope,
        session_filter=args.session,
        antenna_filter=args.antenna
    ).run()


if __name__ == "__main__":
    main()
