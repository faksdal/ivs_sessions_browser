# File: docs/USER_GUIDE.md
# User Guide

## Overview
This TUI fetches IVS session tables for a given year and lets you filter, scroll, and open details quickly.

## Quick Start
1. Create a venv and install requirements.
2. Run: `python ivs_sessions_browser.py --year 2025`
3. Use arrow keys to navigate, `/` to filter, `F` to clear filter, Enter to open.

## Filtering Examples
- `code: R1|R4`
- `status: released`
- `stations: Nn&Ns`
- `stations_removed: Ft|Ur`
- Combined: `code: R1|R4; stations: Nn&Ns`

## Tips
- Filters are case-sensitive.
- Columns are fixed-width; widen your terminal for best results.
- Removed stations appear in brackets and are highlighted.
