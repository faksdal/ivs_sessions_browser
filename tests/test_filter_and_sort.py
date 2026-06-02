from __future__ import annotations

from ivs_sessions_browser.filter_and_sort import FilterAndSort


def _row(code: str, start: str):
    return (
        ["", "", code, start, "", "", "", "", "", "", "", ""],
        None,
        {},
    )


def test_start_filter_accepts_month_names_and_abbreviations() -> None:
    filter_sort = FilterAndSort()
    rows = [
        _row("JAN", "2026-01-10 00:00"),
        _row("JUN", "2026-06-10 00:00"),
        _row("JUL", "2026-07-10 00:00"),
    ]

    assert [row[0][2] for row in filter_sort.apply(rows, "start: jun")] == ["JUN"]
    assert [row[0][2] for row in filter_sort.apply(rows, "start: june")] == ["JUN"]
    assert [row[0][2] for row in filter_sort.apply(rows, "start: 2026-06")] == ["JUN"]


def test_start_month_toggle_preserves_other_filter_clauses() -> None:
    filter_sort = FilterAndSort()

    assert (
        filter_sort.toggle_start_month_filter("code: r1; stations: Nn", 6)
        == "code: r1; stations: Nn; start: jun"
    )
    assert (
        filter_sort.toggle_start_month_filter("code: r1; start: may; stations: Nn", 6)
        == "code: r1; start: jun; stations: Nn"
    )
    assert (
        filter_sort.toggle_start_month_filter("code: r1; start: jun; stations: Nn", 6)
        == "code: r1; stations: Nn"
    )
