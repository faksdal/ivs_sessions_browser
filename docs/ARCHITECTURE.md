# IVS Sessions Browser Architecture

## Purpose
- Explain how the CLI/TUI flow is wired together so contributors can follow execution from entry point to data fetch and rendering.
- Scope: current minimal implementation that fetches session pages, chooses freshest master/intensive URLs, and prints a text summary.

## High-level flow
1. User runs `run_browser` or `python -m ivs_sessions_browser`.
2. `__main__.py` calls `ivs_sessions_browser.main()`.
3. `main()` (argument parsing) builds the CLI parser, adds `--year`, `--scope`, `--filters`, `--mirrors`, output options, and `--version`, then parses args.
4. `SessionsBrowser` is constructed with parsed args and computes the URL list for the chosen scope and mirrors.
5. `FetchSessions` retrieves metadata for those URLs, picks the most recently updated master and intensive pages, then fetches their HTML.
6. `SessionsBrowser.render_sessions_list()` produces text lines (placeholder for now) and either prints or writes them based on CLI options.

## Detailed flow
- CLI arguments are being processed in `__init__.py`.
- SessionsBrowser object are created in `__init__.py` as `sb`. This calls upon SessionsBrowser's `__init__()` method.
    `SessionsBrowser::__init__()` This initializes the local attributes: `year`, `scope`, `mirrors` and `filters`.
    `SessionsBrowser::__init__()` continues to call `self._urls_for_scope(_mirrors)` to build the list of URLs to
    get session data from.

## Entry points
- Shell wrapper: `run_browser` in project root sets `PYTHONPATH=src` and execs `.venv/bin/python3 scripts/run_sessions_browser.py`.
- Module entry: `src/ivs_sessions_browser/__main__.py` calls `main()`.
- CLI parser and dispatcher: `src/ivs_sessions_browser/__init__.py` defines `main()` and registers `--version` using `__version__` from setuptools-scm.

## Core components
- `SessionsBrowser` (`src/ivs_sessions_browser/sessions_browser.py`)
  - `_urls_for_scope(_mirrors)` builds primary/mirror URL list for master/intensive/both using `IVSCC_BASE_URLS`.
  - `render_sessions_list()` currently returns a placeholder list of lines; future work: parse fetched HTML into rows, filter, and format.
- `FetchSessions` (`src/ivs_sessions_browser/fetch_sessions.py`)
  - `fetch_urls_metadata(urls)` HEAD/GET to gather `Last-Modified` timestamps.
  - Chooses most recent master and intensive URLs, then `fetch_urls_html()` downloads HTML with retry and CA-bundle handling.
  - `_get_ca_bundle_path()` picks CA bundle (env `IVS_CA_BUNDLE`, packaged PEM, or `certifi`).

## CLI surface (current)
- `--year` (int, default: current year)
- `--scope` (master|intensive|both; default both)
- `--filters` (string filter expression; placeholder usage)
- `--mirrors` (include mirror sites when picking freshest data)
- Output controls: `--output`, `--format`, `--append`
- `--version` (reports package version from setuptools-scm)

## Data sources
- Base URLs: `defs.IVSCC_BASE_URLS` lists primary and mirror IVS session roots.
- For each scope, the most recently updated URL is selected before HTML fetch.

## Versioning
- Managed by setuptools-scm (configured in `pyproject.toml`).
- `src/ivs_sessions_browser/version.py` is generated on `pip install -e .` based on git tags/commits.
- `--version` reads `__version__` from that generated file.

## Future work / gaps
- Parse fetched HTML into structured rows; implement filtering and sorting.
- Replace placeholder rendering with real tabular/text (and optional JSON/CSV) output.
- Add error handling around fetch and parsing for offline/SSL/timeouts.
- Extend tests for URL selection, parsing, and CLI behaviors.
