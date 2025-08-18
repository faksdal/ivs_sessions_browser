
# File: README.md
# IVS Sessions TUI Browser

A terminal UI to browse IVS sessions by year, apply powerful filters, and open session detail pages in your browser.

> Still a work in progress — feedback and PRs are welcome!

## Features
- Scrollable, searchable TUI (curses)
- Whole-row coloring by status:
  - Green = Released
  - Yellow = Waiting/Processing/Cleaning/Processing session
  - Red = Cancelled or empty status
- Stations rendered as `Active [Removed]` with removed highlighted
- Case-sensitive filtering with AND/OR logic and multiple clauses
- Open selected session in browser (Enter)

## Install
```bash
python -m venv .venv
source .venv/bin/activate            # on Windows: .\.venv\Scripts\activate
pip install -r requirements.txt

