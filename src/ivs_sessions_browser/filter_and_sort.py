# flake8: noqa
# isort: skip_file

"""
Filename:       filter_and_sort.py
Author:         jole
Created:        20/09/2025

Description:    Filter and sort session data based on user queries.
                Supports complex filtering with OR/AND logic for stations and other fields.

Notes:          Adapted from v3 codebase to work with current project structure.
"""

# ──────────────────────────────────────────────────────────────────────────────
# Import section
# ──────────────────────────────────────────────────────────────────────────────
from __future__ import annotations
from datetime import datetime
from typing import Callable, Any
import re

# Project defined imports
from . import defs as D
# ─── END OF Import section ────────────────────────────────────────────────────



class FilterAndSort:
    """
    Single place for:
      - parsing a user query into predicates
      - applying those predicates to rows
      - common sorts (e.g., by 'start')
      - helpers like 'index_on_or_after_today'
    """

    MONTH_ABBRS: tuple[str, ...] = (
        "jan", "feb", "mar", "apr", "may", "jun",
        "jul", "aug", "sep", "oct", "nov", "dec",
    )
    MONTH_NAMES: dict[str, int] = {
        "jan": 1, "january": 1,
        "feb": 2, "february": 2,
        "mar": 3, "march": 3,
        "apr": 4, "april": 4,
        "may": 5,
        "jun": 6, "june": 6,
        "jul": 7, "july": 7,
        "aug": 8, "august": 8,
        "sep": 9, "sept": 9, "september": 9,
        "oct": 10, "october": 10,
        "nov": 11, "november": 11,
        "dec": 12, "december": 12,
    }

    def start_month_label(self, _month: int) -> str:
        if not 1 <= _month <= 12:
            raise ValueError(f"month must be 1-12, got {_month}")
        return self.MONTH_ABBRS[_month - 1]
    # ─── END OF start_month_label() ──────────────────────────────────────────



    def toggle_start_month_filter(self, _query: str, _month: int) -> str:
        """
        Add, replace, or remove a start-month clause.

        F-key shortcuts use this so month filtering stays compatible with the
        normal filter language: e.g. `code:R1; start: jun`.
        """

        label = self.start_month_label(_month)
        clauses = self._split_clauses(_query or "")
        new_clauses: list[str] = []
        found_start = False

        for clause in clauses:
            if ":" not in clause:
                new_clauses.append(clause)
                continue

            field, value = [p.strip() for p in clause.split(":", 1)]
            if field.lower() != "start":
                new_clauses.append(clause)
                continue

            if found_start:
                continue

            found_start = True
            if self._is_exact_start_month(value, _month):
                continue
            new_clauses.append(f"start: {label}")

        if not found_start:
            new_clauses.append(f"start: {label}")

        return "; ".join(new_clauses)
    # ─── END OF toggle_start_month_filter() ──────────────────────────────────



    def has_exact_start_month_filter(self, _query: str, _month: int) -> bool:
        for clause in self._split_clauses(_query or ""):
            if ":" not in clause:
                continue

            field, value = [p.strip() for p in clause.split(":", 1)]
            if field.lower() == "start" and self._is_exact_start_month(value, _month):
                return True
        return False
    # ─── END OF has_exact_start_month_filter() ───────────────────────────────

    def apply(self,
              _rows: list[D.Row],
              _query: str           = "",
              *,
              _show_removed: bool   = True,
              _sort_key: str        = "start",
              _ascending: bool      = True,
              ) -> list[D.Row]:

        preds       = self._predicates_from_query(_query)
        filtered    = [r for r in _rows if all(p(r) for p in preds)]

        # --- optional post-filter projection when hiding removed stations
        if not _show_removed:
            filtered = [self._with_active_only(r) for r in filtered]
        return self.sort(filtered, _sort_key = _sort_key, _ascending = _ascending)
    # ─── END OF apply() ───────────────────────────────────────────────────────



    def sort(self, _rows: list[D.Row], *, _sort_key: str = "start", _ascending: bool = True) -> list[D.Row]:
        keyfunc = self._keyfunc(_sort_key)
        return sorted(_rows, key = keyfunc, reverse = not _ascending)
    # ─── END OF sort() ────────────────────────────────────────────────────────



    def index_on_or_after_today(self, _rows: list[D.Row], _now: datetime | None = None) -> int:
        _now = _now or datetime.now()
        for i, r in enumerate(_rows):
            dt = self._parse_start(r)
            if dt and dt >= _now:
                return i
        return max(0, len(_rows) - 1)
    # ─── END OF index_on_or_after_today() ─────────────────────────────────────



    def extract_station_tokens(self, _query: str) -> list[str]:
        """Return station tokens for highlighting (dedup, longer-first)."""
        if not _query:
            return []
        tokens: list[str] = []
        for clause in self._split_clauses(_query):
            if ":" not in clause:
                continue
            field, value = [p.strip() for p in clause.split(":", 1)]
            fld = field.lower()
            if fld in ("stations", "stations_active", "stations-active",
                       "stations_removed", "stations-removed",
                       "stations_all", "stations-all"):
                parts = re.split(r"[ ,+|&]+", value)
                tokens.extend([p for p in parts if p])
        return sorted(set(tokens), key=lambda s: (-len(s), s))
    # ─── END OF extract_station_tokens() ──────────────────────────────────────



    def _predicates_from_query(self, _query: str) -> list[Callable[[D.Row], bool]]:
        """
        Grammar (from ARGUMENT_EPILOG):
          - Clauses separated by ';' are AND across the whole query
          - Non-stations fields: tokens split by space/comma/plus/pipe are OR
          - Stations active (default): stations: Nn&Ns  or  stations: Nn|Ns
          - Stations removed/any: stations_removed: Ft|Ur   stations_all: Hb|Ht
        """
        _query = (_query or "").strip()
        if not _query:
            return [lambda _r: True]

        preds: list[Callable[[D.Row], bool]] = []
        for clause in self._split_clauses(_query):
            if ":" not in clause:
                # Free-text (fallback OR over all columns)
                val = clause
                preds.append(self._predicate_any_field_contains(val))
                continue

            field, value = [p.strip() for p in clause.split(":", 1)]
            fld = field.lower()

            if fld in ("stations", "stations_active", "stations-active"):
                preds.append(self._predicate_stations_active(value))
            elif fld in ("stations_removed", "stations-removed"):
                preds.append(self._predicate_stations_removed(value))
            elif fld in ("stations_all", "stations-all"):
                preds.append(self._predicate_stations_all(value))
            else:
                preds.append(self._predicate_field_tokens_or(fld, value))
        return preds
    # ─── END OF _predicates_from_query() ──────────────────────────────────────



    def _split_clauses(self, _query: str) -> list[str]:
        return [c.strip() for c in _query.split(";") if c.strip()]
    # ─── END OF _split_clauses() ──────────────────────────────────────────────


    
    def _predicate_any_field_contains(self, _needle: str) -> Callable[[D.Row], bool]:
        n = _needle.lower()
        return lambda r: any(n in v.lower() for v in r[0])
    # ─── END OF _predicate_any_field_contains() ───────────────────────────────



    def _predicate_field_tokens_or(self, _fld: str, _value: str) -> Callable[[D.Row], bool]:
        idx = D.FIELD_INDEX.get(_fld, None)
        if idx is None or idx < 0:
            # unknown field: match nothing (alternatively: any_field_contains)
            return lambda _r: False
        # tokens separated by space/comma/plus/pipe are OR
        tokens = [t.lower() for t in re.split(r"[ ,+|]+", _value) if t]
        if _fld == "start":
            return self._predicate_start_tokens_or(tokens)
        return lambda r: any(tok in r[0][idx].lower() for tok in tokens)
    # ─── END OF _predicate_field_tokens_or() ──────────────────────────────────



    def _predicate_start_tokens_or(self, _tokens: list[str]) -> Callable[[D.Row], bool]:
        idx = D.FIELD_INDEX["start"]
        month_tokens = [self.MONTH_NAMES[tok] for tok in _tokens if tok in self.MONTH_NAMES]
        text_tokens = [tok for tok in _tokens if tok not in self.MONTH_NAMES]

        def pred(_r: D.Row) -> bool:
            start_text = _r[0][idx].lower()
            if any(tok in start_text for tok in text_tokens):
                return True

            if month_tokens:
                start_dt = self._parse_start(_r)
                if start_dt != datetime.min and start_dt.month in month_tokens:
                    return True

            return False

        return pred
    # ─── END OF _predicate_start_tokens_or() ─────────────────────────────────



    def _is_exact_start_month(self, _value: str, _month: int) -> bool:
        tokens = [t.lower() for t in re.split(r"[ ,+|]+", _value) if t]
        return len(tokens) == 1 and self.MONTH_NAMES.get(tokens[0]) == _month
    # ─── END OF _is_exact_start_month() ──────────────────────────────────────



    def _predicate_stations_active(self, _expr: str) -> Callable[[D.Row], bool]:

        def match_and_or(_hay: str, _text: str) -> bool:
            has_or = '|' in _text
            has_and = '&' in _text
            if has_or or has_and:
                or_parts = [p.strip() for p in re.split(r"\s*\|{1,2}\s*", _text) if p.strip()]
                for part in or_parts:
                    and_chunks = [c.strip() for c in re.split(r"\s*&{1,2}\s*", part) if c.strip()]
                    and_tokens: list[str] = []
                    for chunk in and_chunks:
                        and_tokens.extend([t for t in re.split(r"[ ,+]+", chunk) if t])
                    if and_tokens and all(tok in _hay for tok in and_tokens):
                        return True
                    if not and_tokens and part and part in _hay:
                        return True
                return False
            tokens = [t for t in re.split(r"[ ,+]+", _text) if t]
            return all(tok in _hay for tok in tokens)
        # ─── END OF match_and_or() ────────────────────────────────────────────
        return lambda r: match_and_or(r[2].get("active", ""), _expr)
    # ─── END OF _predicate_stations_active() ──────────────────────────────────



    def _predicate_stations_removed(self, _expr: str) -> Callable[[D.Row], bool]:
        return self._predicate_stations_side(_expr, _side = "removed")
    # ─── END OF _predicate_stations_removed() ─────────────────────────────────



    def _predicate_stations_all(self, _expr: str) -> Callable[[D.Row], bool]:
        return self._predicate_stations_side(_expr, _side = "all")
    # ─── END OF _predicate_stations_all() ─────────────────────────────────────


    def _predicate_stations_side(self, _expr: str, *, _side: str) -> Callable[[D.Row], bool]:

        def normalize(meta: dict[str, Any]) -> str:
            active = meta.get("active", "")
            removed = meta.get("removed", "")
            if _side == "removed":
                return removed
            if _side == "all":
                return active + removed
            return active
        # ─── END OF normalize() ───────────────────────────────────────────────

        # reuse active predicate logic on chosen haystack
        def pred(_r: D.Row) -> bool:
            hay = normalize(_r[2])
            dummy_row: D.Row = (_r[0], _r[1], {"active": hay, "removed": ""})
            return self._predicate_stations_active(_expr)(dummy_row)

        # ─── END OF pred() ────────────────────────────────────────────────────
        return pred
    # ─── END OF _predicate_stations_side() ────────────────────────────────────



    def _with_active_only(self, _r: D.Row) -> D.Row:
        values, url, meta = _r
        idx = D.FIELD_INDEX.get("stations", -1)
        if idx >= 0 and meta.get("active"):
            new_vals = list(values)
            # left-justify to keep column alignment consistent with your renderer
            new_vals[idx] = meta["active"].ljust(len(values[idx]))
            return (new_vals, url, meta)
        return _r
    # ─── END OF _with_active_only() ───────────────────────────────────────────



    def _keyfunc(self, _sort_key: str) -> Callable[[D.Row], Any]:
        sk = (_sort_key or "").lower()
        if sk == "start":
            return self._parse_start
        # fallback: column name in FIELD_INDEX or no-op
        idx = D.FIELD_INDEX.get(sk, None)
        if idx is None:
            return lambda r: 0
        return lambda r: r[0][idx]
    # ─── END OF _keyfunc() ────────────────────────────────────────────────────



    def _parse_start(self, _r: D.Row):
        start_str = _r[0][D.FIELD_INDEX["start"]]
        try:
            # Try parsing with time first (format: "2026-01-05 17:00")
            return datetime.strptime(start_str, "%Y-%m-%d %H:%M")
        except Exception:
            try:
                # Fallback to date-only format
                return datetime.strptime(start_str, D.DATEFORMAT)
            except Exception:
                return datetime.min
    # ─── END OF _parse_start() ────────────────────────────────────────────────

# ─── END OF class FilterAndSort ───────────────────────────────────────────────
