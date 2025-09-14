
# File: README.md
# IVS Sessions Browser v3

A terminal-based TUI browser for [IVS session schedules](https://ivscc.gsfc.nasa.gov/sessions/).

Features:
- Browse and filter IVS master and intensive sessions
- Curses-based interface with keyboard navigation
- Color highlighting by session status
- Open selected session details in a web browser
- Filtering:
  - Clauses separated by `;` are **AND**
  - **Stations**: filters are **case-sensitive**
  - **Other fields**: filters are **case-insensitive**
  - Non-station fields: tokens split by space/comma/plus/pipe are **OR**
  - Examples:
    - `code:R1|R4` → sessions with codes matching R1 or R4
    - `stations:Nn&Ns` → sessions with both stations Nn and Ns
    - `stations_removed:Ft|Ur` → sessions with Ft or Ur removed
    - `stations_all: Hb|Ht` → sessions with Hb or Ht active or removed
  
- Best viewed in a dark theme

---

## Install

### Prerequisites
- Python 3.10+ recommended
- Linux/macOS: a terminal that supports curses
- Windows: also requires the [`windows-curses`](https://pypi.org/project/windows-curses/) package

### Setup

```bash
git clone https://github.com/faksdal/ivs_sessions_browser.git
cd ivs_sessions_browser
python -m venv .venv
source .venv/bin/activate              # Windows: .\.venv\Scripts\activate
pip install -r requirements.txt

## License
This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.
