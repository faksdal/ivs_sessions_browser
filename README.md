
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
- Supports both regular and intensive schedules
  - Intensive sessions are tagged with `[I]` in the `Type` column
- Sessions are always shown in chronological order (by `Start`)
- Filter bar (`/`) supports multiple clauses and AND/OR in stations
- Press `F` to clear filters


## Install
```bash
python -m venv .venv
source .venv/bin/activate            # on Windows: .\.venv\Scripts\activate
pip install -r requirements.txt
```

## License
This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.
