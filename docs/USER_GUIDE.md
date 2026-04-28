# IVS Sessions Browser - User Guide

## Overview

The IVS Sessions Browser is a terminal-based user interface (TUI) for browsing, filtering, and managing IVS (International VLBI Service) session schedules. It provides a fast, keyboard-driven interface for exploring master and intensive session schedules from IVS Central Bureau, with powerful filtering capabilities, operator assignment features, and visual status indicators.

## Installation

### Prerequisites
- Python 3.10 or higher
- Linux/macOS terminal with curses support (Windows users: install `windows-curses`)
- Internet access to fetch schedules from ivscc.gsfc.nasa.gov

### Setup Steps

1. **Clone the repository:**
   ```bash
   git clone git@github.com:faksdal/ivs_sessions_browser.git
   cd ivs_sessions_browser
   ```

2. **Create and activate virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Optional - Editable install for console command:**
   ```bash
   pip install -e .
   ```
   This enables the `ivs-sessions-browser` command in your terminal.

## Quick Start

### Running the Application

Choose one of these methods:

**Method 1: Wrapper script (recommended)**
```bash
./run_browser
```

**Method 2: Direct with PYTHONPATH**
```bash
PYTHONPATH=src python3 scripts/run_sessions_browser.py
```

**Method 3: As a module**
```bash
PYTHONPATH=src python3 -m ivs_sessions_browser
```

**Method 4: Console script (after editable install)**
```bash
ivs-sessions-browser
```

### Command-Line Options

```bash
./run_browser --help
```

Available options:
- `--year YYYY` - Specify year (default: current year)
- `--scope {master|intensive|both}` - Session type (default: both)
- `--filters "expression"` - Initial filter expression
- `--mirrors` - Check mirror sites for most recent data, or in case master site is down
- `--output FILE` - Write output to file and exit (use `-` for stdout)
- `-p, --pretty-print [ALL|OP|TYPE|... ]` - Select output columns (pipe-delimited), default `ALL`
- `--verbose-fetch` - Show fetch/progress output even when using `--output`
- `--format {text|pdf}` - Output format flag (default: `text`)
- `--append` - Append to output file instead of overwriting
- `--version` - Show version and exit

### Examples

```bash
# Browse 2025 sessions
./run_browser --year 2025

# Only master sessions
./run_browser --year 2025 --scope master

# Start with a filter
./run_browser --filters "code: R1|R4; status: released"

# Check mirrors for latest data
./run_browser --mirrors

# Export to file and exit
./run_browser --year 2025 --output sessions.txt

# Export a colored PDF using the same pretty-printed lines
./run_browser --year 2025 --output sessions.pdf --format pdf

# Export selected columns to stdout
./run_browser --year 2025 --output - --pretty-print OP|TYPE|STATIONS

# Keep fetch progress visible while exporting
./run_browser --year 2025 --output sessions.txt --verbose-fetch
```

## Using the TUI

### Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Header Row (Column Titles)                                  │
│ ─────────────────────────────────────────────────────────── │
│ Op | Type | Code | Start | DOY | Dur | Stations | ...       │
│ ═════════════════════════════════════════════════════════   │
│ Session Row 1 (with color based on status/operator)         │
│ Session Row 2                                                │
│ Session Row 3 (selected - highlighted)                      │
│ ...                                                          │
│ Session Row N                                                │
│ ─────────────────────────────────────────────────────────── │
│ Status Bar: Row X/Y | Filter: ... | Help: ?                 │
└─────────────────────────────────────────────────────────────┘
```

### Navigation Basics

- **↑/↓ Arrow keys**: Move selection up/down one row
- **PgUp/PgDn**: Scroll one page at a time
- **Home**: Jump to first session
- **End**: Jump to last session
- **T**: Jump to today's session (or nearest future session)

### Viewing Session Details

Press **Enter** while a session is selected to open the full session page in your default web browser. This provides access to:
- Complete station list
- Schedule details
- Correlation status
- Analysis reports
- Download links for data files

### Statistics and Contribution Views

- Press **S** to open the statistics dialog.
- The statistics report includes:
   - Session and hour trends over years
   - Program mix and yearly observing hours
   - Network size proxies (active stations/session, baselines/session, baseline-hours)
   - Reliability proxies (cancelled share, non-cancelled share, reduced-network sessions)
- In the statistics dialog, use **↑/↓** or **PgUp/PgDn** to scroll, and **q** or **Enter** to close.

- Press **G** to generate a station contribution plot.
   - Repeated presses cycle the plotted metric between session share, hours, and weighted hours.

## Filtering Sessions

Filtering is one of the most powerful features of the IVS Sessions Browser. It allows you to quickly narrow down thousands of sessions to exactly what you need.

### Entering a Filter

1. Press `/` to enter filter mode
2. Type your filter expression
3. Press Enter to apply
4. Press `C` to clear all filters

### Filter Syntax Overview

**Basic format**: `field: value`

**Multiple criteria (AND)**: Separate with `;`
```
code: R1; status: released
```

**Multiple values (OR)**: Separate with `|`, space, `,`, or `+`
```
code: R1|R4|CRF
status: released processing
```

### Common Field Filters

**Session codes:**
```
code: R1|R4
```

**Status:**
```
status: released
status: processing|waiting
```

**Date range:**
```
start: 2025-02
```

**Correlator:**
```
correlator: BONN|WASH
```

### Station Filters

Station filters are special because they support explicit AND/OR logic:

**Both stations must be present (AND):**
```
stations: Nn&Ns
```

**Either station can be present (OR):**
```
stations: Nn|Ns
```

**Filter by removed stations:**
```
stations_removed: Ft|Ur
```

**Include both active and removed:**
```
stations_all: Ke
```

### Complex Filter Examples

**R1 or R4 sessions with both Nn and Ns:**
```
code: R1|R4; stations: Nn&Ns
```

**Released sessions in February 2025:**
```
status: released; start: 2025-02
```

**Any session with Onsala station, correlated at BONN:**
```
stations: Oe; correlator: BONN
```

**Processing sessions excluding cancelled:**
```
status: processing|waiting
```

See [FILTER_SYNTAX.md](FILTER_SYNTAX.md) for comprehensive documentation.

## Operator Assignment

Operator assignment allows you to tag sessions with operator names for tracking who is responsible for each session.

### Configuration

Edit `operators.json` in the project root:

```json
{
  "bindings": {
    "0": "",
    "1": "Alice",
    "2": "Bob",
    "3": "Charlie",
    "4": "",
    "5": ""
  },
  "colors": {
    "0": "white",
    "1": "green",
    "2": "blue",
    "3": "yellow",
    "4": "magenta",
    "5": "cyan"
  }
}
```

### Assigning Operators

1. Navigate to a session
2. Press a number key `0-5` to assign the corresponding operator
3. The session row will change color to match the operator's configured color
4. Assignments are saved to `operator_assignments.json`

### Filtering by Operator

```
op: Alice
```

Shows only sessions assigned to Alice.

```
op: Alice|Bob
```

Shows sessions assigned to either Alice or Bob.

## Understanding Color Codes

### Status Colors

| Color | Meaning |
|-------|---------|
| **Green** | Released - data available for download |
| **Yellow** | Processing or Waiting - data being processed |
| **Magenta** | Cancelled - session was cancelled |
| **White** | No status information available |

### Operator Colors

When operators are assigned, the row color reflects the operator's configured color (from `operators.json`), making it easy to visually identify who is responsible for each session.

### Removed Stations

Stations that were originally scheduled but later removed appear:
- In square brackets: `[Ft]`
- Often highlighted (depending on theme)
- Can be targeted via filters such as `stations:`, `stations_removed:`, and `stations_all:`

## Output to File

Instead of using the interactive TUI, you can export session data:

By default, `--output` runs in quiet mode (no fetch/progress chatter on stderr).
Use `--verbose-fetch` to re-enable progress/status output.

### Text Format
```bash
./run_browser --year 2025 --output sessions.txt
```

### PDF Format

```bash
./run_browser --year 2025 --output sessions.pdf --format pdf
```

PDF export reuses the same pretty-printed lines as text export and preserves the configured row colors in a monospaced layout. `--append` is not supported for PDF output.

### Append Mode
```bash
./run_browser --year 2025 --output sessions.txt --append
```

## Tips and Best Practices

### 1. Start with a Date Jump
Press `T` immediately after launching to jump to today's sessions, then filter from there.

### 2. Build Filters Incrementally
Start with broad filters and narrow down:
```
status: released          # First: only released
/code: R1|R4             # Then: specific codes
/stations: Nn&Ns         # Finally: required stations
```

### 3. Use Partial Date Matching
```
start: 2025-02    # All of February
start: 2025       # Entire year
```

### 4. Check Mirrors for Latest Data
Use `--mirrors` flag when you need the absolute latest schedule updates:
```bash
./run_browser --mirrors --year 2025
```

### 5. Keyboard Efficiency
- Master the navigation keys (especially `T`, `Home`, `End`)
- Use `C` frequently to clear filters and start fresh
- Remember `?` for quick help reference

### 6. Monitor Operations
- Set up operators with distinct colors for easy visual scanning
- Filter by `op:` to see your assigned sessions
- Review unassigned sessions (operator column empty)

### 7. Terminal Settings
For the best experience:
- Use a terminal with 256-color support
- Set `TERM=xterm-256color`
- Use a dark theme for better contrast
- Maximize terminal window to see all columns

## Troubleshooting

### Module Not Found Error
```
ModuleNotFoundError: No module named 'ivs_sessions_browser'
```

**Solution**: Set PYTHONPATH:
```bash
PYTHONPATH=src python3 scripts/run_sessions_browser.py
```

Or use the `run_browser` wrapper script.

### Windows Curses Error
```
ImportError: No module named '_curses'
```

**Solution**: Install windows-curses:
```bash
pip install windows-curses
```

### No Colors or Weird Characters
**Solutions**:
- Use a modern terminal (avoid very old terminal emulators)
- Check UTF-8 encoding support
- Set `TERM=xterm-256color` in your environment
- Try a different terminal emulator if issues persist

### Network Errors
- Check internet connection
- Try `--mirrors` flag to use alternative IVS sites
- Check firewall/proxy settings
- Set `IVS_CA_BUNDLE` environment variable if using custom certificates

### Performance Issues
- Filter sessions to reduce visible rows
- Use `--scope master` or `--scope intensive` instead of `both`
- Close other terminal applications
- Increase terminal buffer size

## Keyboard Reference

Press `?` anytime in the TUI for a complete keyboard reference.

Quick reference:
- **Navigation**: `↑↓` `PgUp` `PgDn` `Home` `End` `T`
- **Filtering**: `/` `C`
- **Actions**: `Enter` `0-5`
- **Help**: `?`
- **Quit**: `q` or `Q`

## Related Documentation

- [FILTER_SYNTAX.md](FILTER_SYNTAX.md) - Complete filter syntax reference
- [KEY_BINDINGS.md](KEY_BINDINGS.md) - All keyboard shortcuts
- [ARCHITECTURE.md](ARCHITECTURE.md) - Technical architecture overview
- [ROADMAP.md](ROADMAP.md) - Planned features and improvements

## Support and Contributing

For issues, questions, or contributions:
- Review the documentation in the `docs/` folder
- Check existing issues on the repository
- Follow coding standards when contributing
- Test changes thoroughly before submitting PRs

## License

MIT License - see [LICENSE](../LICENSE) for details.

## Acknowledgments

- IVS Central Bureau & NASA Goddard Space Flight Center for providing session schedules
- Contributors and operators at Ny-Ålesund and Brandal observatories
- The VLBI community for continued support and feedback
