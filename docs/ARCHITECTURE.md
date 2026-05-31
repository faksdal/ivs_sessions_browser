# IVS Sessions Browser Architecture

## Purpose
This document explains how the CLI/TUI flow is wired together so contributors can follow execution from entry point through data fetching, parsing, filtering, and rendering. The goal is to provide a clear understanding of how all components interact to deliver an interactive terminal-based browser for IVS session schedules.

## High-level flow
1. User runs `ivs-sessions-browser`, `python -m ivs_sessions_browser`, or `./run_browser`.
2. The selected entry point calls `ivs_sessions_browser.main()` from `__init__.py`.
3. `main()` builds the CLI argument parser, parses arguments for `--year` (single, CSV, or range expression), `--scope`, `--filters`, `--mirrors`, output options, `--init-config`, `--man`, and `--version`.
4. Default user config files are initialized before network fetches; if `--init-config` was supplied, the program exits here.
5. `SessionsBrowser` is constructed with parsed arguments and computes the URL list for the chosen scope and mirror preferences.
6. `FetchSessions` retrieves HTML data from the most recently updated master/intensive pages (comparing timestamps when `--mirrors` is specified).
7. The HTML is parsed into row data, filtered, and sorted by `Tui` class using helper methods from `FilterAndSort`.
8. Either:
   - Interactive TUI is launched (default) via curses, or
   - Text, PDF, or XLSX output is written to file/stdout and the program exits.

## Detailed flow

### Entry points
- **Shell wrapper**: `run_browser` in project root sets `PYTHONPATH=src` and execs `.venv/bin/python3 scripts/run_sessions_browser.py`.
- **Module entry**: `src/ivs_sessions_browser/__main__.py` calls `main()` from `__init__.py`.
- **Console script** (after `pip install -e .`): `ivs-sessions-browser` command invokes `ivs_sessions_browser:main`.
- **CLI parser and dispatcher**: `src/ivs_sessions_browser/__init__.py` defines `main()` which:
  - Builds argument parser using constants from `defs.py`
  - Parses command-line arguments
  - Initializes default user config files, or exits immediately for `--init-config`
  - Applies `startup_defaults.json` for omitted startup options
  - Creates `SessionsBrowser` instance
  - Either launches TUI or produces text, PDF, or XLSX output

### Core components

#### `SessionsBrowser` (`sessions_browser.py`)
The main orchestrator class that:
- Stores user parameters: `year`, `scope`, `filters`
- Builds URL list via `_urls_for_scope(_mirrors)` using `IVSCC_BASE_URLS` from `defs.py`
- Creates `FetchSessions` instance to download HTML
- Parses HTML with BeautifulSoup to distinguish master vs intensive sessions
- Delegates to `Tui` class for building formatted session lists
- Manages TUI state (`UIState`) and theme (`TUITheme`)
- Loads operator configurations and session assignments
- Runs the main curses event loop in `_curses_main()`
- Shows bundled "what's new" notes once per installed version
- Handles navigation, filtering, operator assignment, and browser launching
- Handles in-TUI PDF/XLSX exports, statistics dialog, and station contribution plotting

**Key methods**:
- `_urls_for_scope(_mirrors)` - builds primary/mirror URL list for master/intensive/both
- `render_sessions_list()` - produces ANSI-colored text output for CLI mode
- `_curses_main(_stdscr)` - main TUI event loop handling keyboard input
- `_navigate(key, _stdscr)` - processes navigation keys and Enter for opening sessions
- `_show_statistics(_stdscr)` - displays scrollable session and station metrics
- `_plot_station_contributions(_stdscr)` - saves and opens station contribution plots while cycling metrics
- `run()` - launches the curses TUI wrapper

#### `FetchSessions` (`fetch_sessions.py`)
Handles all network operations:
- `fetch_html_from_urls(urls)` - fetches HTML from master/intensive URLs
- `_find_most_recent_page(urls)` - HEAD requests to compare `Last-Modified` timestamps, returns most recent
- `_fetch_latest_update_from_html(html)` - parses "Latest Update" timestamp from page footer
- `_get_ca_bundle_path()` - resolves CA bundle (env `IVS_CA_BUNDLE`, packaged PEM, or `certifi`)
- Implements retry logic with exponential backoff for network failures

#### `Tui` (`tui.py`)
Responsible for TUI rendering and session data formatting:
- `build_session_list(_soup, ...)` - parses BeautifulSoup HTML into structured row data
- `apply_filters_and_sorting(...)` - delegates to `FilterAndSort` for filtering/sorting
- `draw_header(_stdscr, _theme, _state)` - renders column headers
- `draw_rows(_stdscr, rows, highlight_tokens, _theme, _state)` - renders session rows with colors
- `draw_helpbar(_stdscr, ...)` - displays bottom status/help bar
- `show_help(_stdscr, _theme)` - shows centered help popup
- `recompute_header_widths()` - dynamically adjusts column widths based on content, starting from immutable base widths so repeated recomputes do not expand columns
- Uses operator configuration for row coloring based on assigned operators

#### `FilterAndSort` (`filter_and_sort.py`)
Implements filtering and sorting logic:
- `apply_filters(_rows, _query, _show_removed)` - parses filter query and applies field/station filters
- `apply_sorting(_rows, _sort_key, _ascending)` - sorts by specified column
- `extract_station_tokens(_query)` - extracts station codes for highlighting
- `index_on_or_after_today(_rows)` - finds row index matching or after current date
- Supports complex filter expressions with AND (`;`), OR (`|`), and station-specific logic

#### `operators.py`
Manages operator configuration and session assignments:
- `load_operator_bindings()` - loads key-to-label mappings from `~/.config/ivs-sessions-browser/operators.json`
- `load_operator_colors()` - loads color assignments for each operator
- `load_operator_assignments()` - loads session-to-operator mappings from `~/.config/ivs-sessions-browser/operator_assignments.json`
- `save_operator_assignments(data)` - persists session assignments to JSON
- Configuration files are stored in `~/.config/ivs-sessions-browser/` by default (or configurable via `defs.CONFIG_DIR`)

#### `tui_state.py` and `TUITheme`
- `UIState` - dataclass holding TUI state: selected row, offset, view height, colors availability
- `TUITheme` - manages curses color pairs for different statuses (released, processing, cancelled, etc.) and operators

#### `defs.py`
Centralized constants and configuration:
- `HEADERS` - column definitions with widths
- `FIELD_INDEX` - mapping of field names to column indices
- `IVSCC_BASE_URLS` - primary and mirror IVS session URLs
- `HELP_TEXT` - multiline help screen text
- CLI argument descriptions and formatter classes

#### `ivstypes.py`
Type definitions and data classes:
- `PageData` - holds URL and HTML content for a fetched page

## CLI surface (current)
- `--year` (year expression, default: current year)
  - Accepted forms: `2025`, `2022,2023`, `2022-2025`, `2022,2024-2026`
- `--scope` (master|intensive|both; default: both)
- `--filters` (string filter expression following documented syntax)
- `--mirrors` / `--no-mirrors` (compare timestamps across mirror sites, select most recent; `--no-mirrors` overrides startup defaults)
- Output controls:
  - `--output FILE` - write to file (use `-` for stdout) and exit
  - `--pretty-print [ALL|OP|TYPE|...]` - select output columns for textual rendering
  - `--verbose-fetch` - keep fetch/progress messages visible when using `--output`
  - `--format` (text|pdf|xlsx; default: text)
  - `--append` - append to output file instead of overwriting
- `--version` - reports package version from setuptools-scm
- `--init-config` - creates default config files in `~/.config/ivs-sessions-browser/` and exits before fetching session data
- `--man` - renders the bundled manual page and exits

## Data sources
- Base URLs: `defs.IVSCC_BASE_URLS` lists primary (gsfc.nasa.gov) and mirror IVS session roots (oan.es, ivscc-vcc.org).
- For each scope (master/intensive/both), the most recently updated URL is selected before HTML fetch when `--mirrors` is enabled.
- HTML pages are parsed for `<table>` elements containing session data.

## Versioning
- Managed by setuptools-scm (configured in `pyproject.toml`).
- `src/ivs_sessions_browser/version.py` is auto-generated on `pip install -e .` based on git tags/commits.
- `--version` flag reads `__version__` from the generated file.

## TUI Features
- **Navigation**: Arrow keys, PgUp/PgDn, Home/End, jump to today with `T`
- **Filtering**: `/` to enter filter, `C` to clear, `D` to save the current filter as the startup default (including station filters: `stations`, `stations_removed`, `stations_all`)
- **Operator assignment**: `0-5` keys assign configured operators to sessions
- **Dynamic Op width**: the operator column expands to fit saved assignment labels from `operator_assignments.json`
- **Colors**: Status-based colors (green=released, yellow=processing/waiting, magenta=cancelled) and operator-specific colors
- **Help**: `?` displays inline help with key bindings and examples
- **Browser integration**: Enter opens selected session in default web browser
- **Exports**: `P` saves visible rows to PDF; `X` saves visible rows to XLSX
- **Statistics**: `S` opens a scrollable statistics popup; `G` saves station contribution plots for session share, hours, and weighted hours

## Configuration files
- `~/.config/ivs-sessions-browser/operators.json` - operator bindings (key → label) and colors; created from the packaged default when missing
- `~/.config/ivs-sessions-browser/operator_assignments.json` - session code → operator label mappings
- `~/.config/ivs-sessions-browser/pdf_columns` - default PDF export columns; created as `op|start|code|stations|corr` when missing
- `~/.config/ivs-sessions-browser/startup_defaults.json` - optional defaults for omitted `--year`, `--scope`, `--filters`, and `--mirrors`
- `~/.config/ivs-sessions-browser/app_state.json` - internal UI state, including the last version whose "what's new" notes were shown

## Future enhancements
- Additional output formats (full JSON structure, richer CSV)
- More sophisticated filter grammar (parentheses, nested expressions)
- Mouse support for clicking rows
- Configuration file for theme customization
- Multi-year view and quick year switching
- Persistent filter storage between runs
