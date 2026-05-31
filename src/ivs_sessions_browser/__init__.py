# flake8: noqa
# isort: skip_file

"""
Filename:       __init__.py
Author:         jole
Created:        26.01.2026

Description:    Entry point for ivs_sessions_browser package. Defines the main()
                function which serves as the CLI entry point, and imports necessary
                components from other modules.
                It also handles command line arguments, creates a SessionsBrowser
                instance, and either runs a TUI or outputs textual data based on
                user input.
"""

# ──────────────────────────────────────────────────────────────────────────────
# Import section
# ──────────────────────────────────────────────────────────────────────────────
import argparse
import json
import os
import shutil
import subprocess
import sys

from datetime import datetime
from importlib import resources

# Project defined imports
from .defs              import (
    ARGUMENT_DESCRIPTION,
    ARGUMENT_EPILOG,
    ARGUMENT_FORMATTER_CLASS,
    CONFIG_DIR,
    PRETTY_PRINT_ALLOWED_COLUMNS,
    STARTUP_DEFAULTS_FILENAME,
)
from .operators         import load_operator_bindings, load_operator_colors
from .pdf_export        import write_ansi_lines_pdf
from .sessions_browser  import SessionsBrowser, _load_pdf_default_columns
from .xlsx_export       import write_sessions_xlsx
# ─── END OF Import section ────────────────────────────────────────────────────



def _parse_pretty_columns(value: str) -> str | list[str]:
    text = value.strip().upper()
    if text == "ALL":
        return "ALL"

    cols = [col.strip().upper() for col in value.split("|") if col.strip()]
    if not cols:
        raise argparse.ArgumentTypeError(
            "Use ALL or a pipe-delimited list, e.g. OP|TYPE|STATIONS"
        )

    invalid = [col for col in cols if col not in PRETTY_PRINT_ALLOWED_COLUMNS]
    if invalid:
        valid = "|".join(PRETTY_PRINT_ALLOWED_COLUMNS)
        bad = "|".join(invalid)
        raise argparse.ArgumentTypeError(
            f"Unknown column(s): {bad}. Valid values: {valid}"
        )

    # De-duplicate while preserving order
    deduped_cols: list[str] = list(dict.fromkeys(cols))
    return deduped_cols
# ─── END OF _parse_pretty_columns() ───────────────────────────────────────────



def _parse_years(value: str) -> list[int]:
    """
    Parse year expression into a de-duplicated ordered list of years.

    Accepted forms:
      - "2025"
      - "2022,2023"
      - "2022-2025"
      - "2022,2024-2026"
    """

    text = value.strip()
    if not text:
        raise argparse.ArgumentTypeError("Year expression cannot be empty")

    years: list[int] = []

    for token in [part.strip() for part in text.split(",") if part.strip()]:
        if "-" in token:
            bounds = [p.strip() for p in token.split("-", 1)]
            if len(bounds) != 2:
                raise argparse.ArgumentTypeError(
                    f"Invalid year range '{token}'. Use YYYY-YYYY"
                )
            try:
                start = int(bounds[0])
                end = int(bounds[1])
            except ValueError as exc:
                raise argparse.ArgumentTypeError(
                    f"Invalid year range '{token}'. Use numeric years"
                ) from exc

            if start > end:
                raise argparse.ArgumentTypeError(
                    f"Invalid year range '{token}'. Start year must be <= end year"
                )

            years.extend(range(start, end + 1))
        else:
            try:
                years.append(int(token))
            except ValueError as exc:
                raise argparse.ArgumentTypeError(
                    f"Invalid year '{token}'. Use YYYY, YYYY,YYYY, or YYYY-YYYY"
                ) from exc

    if not years:
        raise argparse.ArgumentTypeError("No valid years found")

    for y in years:
        if y < 1979:
            raise argparse.ArgumentTypeError(
                f"Year '{y}' is out of range. Earliest supported year is 1979"
            )

    # De-duplicate while preserving order
    return list(dict.fromkeys(years))
# ─── END OF _parse_years() ────────────────────────────────────────────────────


STARTUP_DEFAULTS_PATH = CONFIG_DIR / STARTUP_DEFAULTS_FILENAME
STARTUP_DEFAULTS_TEMPLATE: dict[str, object] = {
    "year": None,
    "scope": "both",
    "filters": "",
    "mirrors": False,
}


def _ensure_startup_defaults_file() -> None:
    if STARTUP_DEFAULTS_PATH.exists():
        return

    try:
        STARTUP_DEFAULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with STARTUP_DEFAULTS_PATH.open("w", encoding="utf-8") as f:
            json.dump(STARTUP_DEFAULTS_TEMPLATE, f, indent=2, sort_keys=True)
            f.write("\n")
    except OSError:
        pass


def _coerce_startup_year(value: object) -> list[int] | None:
    if value in (None, ""):
        return None

    if isinstance(value, int):
        return _parse_years(str(value))

    if isinstance(value, str):
        return _parse_years(value)

    if isinstance(value, list):
        year_tokens: list[str] = []
        for item in value:
            if not isinstance(item, int):
                raise ValueError("year list must contain only numeric years")
            year_tokens.append(str(item))
        return _parse_years(",".join(year_tokens))

    raise ValueError("year must be a number, string, list of numbers, or null")


def _load_startup_defaults() -> dict[str, object]:
    _ensure_startup_defaults_file()

    try:
        with STARTUP_DEFAULTS_PATH.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Ignoring invalid {STARTUP_DEFAULTS_PATH}: {exc}", file=sys.stderr)
        return {}

    if not isinstance(raw, dict):
        print(f"Ignoring invalid {STARTUP_DEFAULTS_PATH}: expected a JSON object", file=sys.stderr)
        return {}

    defaults: dict[str, object] = {}

    try:
        year = _coerce_startup_year(raw.get("year"))
    except (argparse.ArgumentTypeError, ValueError) as exc:
        print(f"Ignoring invalid startup default year: {exc}", file=sys.stderr)
        year = None
    if year is not None:
        defaults["year"] = year

    scope = raw.get("scope")
    if scope in ("master", "intensive", "both"):
        defaults["scope"] = scope
    elif scope not in (None, ""):
        print("Ignoring invalid startup default scope: use master, intensive, or both", file=sys.stderr)

    filters = raw.get("filters")
    if isinstance(filters, str) and filters.strip():
        defaults["filters"] = filters
    elif filters not in (None, ""):
        print("Ignoring invalid startup default filters: use a string", file=sys.stderr)

    mirrors = raw.get("mirrors")
    if isinstance(mirrors, bool):
        defaults["mirrors"] = mirrors
    elif mirrors not in (None, ""):
        print("Ignoring invalid startup default mirrors: use true or false", file=sys.stderr)

    return defaults


def _apply_startup_defaults(args: argparse.Namespace) -> None:
    defaults = _load_startup_defaults()

    if args.year is None:
        args.year = defaults.get("year", [datetime.now().year])

    if args.scope is None:
        args.scope = defaults.get("scope", "both")

    if args.filters is None:
        args.filters = defaults.get("filters")

    if args.mirrors is None:
        args.mirrors = defaults.get("mirrors", False)
# ─── END OF startup defaults helpers ──────────────────────────────────────────



# ──────────────────────────────────────────────────────────────────────────────
# Version (managed by setuptools-scm)
# ──────────────────────────────────────────────────────────────────────────────
try:
    from .version import version as __version__
except ImportError:
    __version__ = "0.0.0"
# ─── END OF Version ───────────────────────────────────────────────────────────


def _ensure_user_config_files() -> None:
    # pip/pipx install cannot write user config into $HOME; the app creates
    # editable defaults when explicitly requested or before a normal run.
    load_operator_bindings()
    load_operator_colors()
    _load_pdf_default_columns()
    _ensure_startup_defaults_file()


def _show_man_page() -> None:
    resource = resources.files("ivs_sessions_browser").joinpath("man/ivs-sessions-browser.1")

    try:
        with resources.as_file(resource) as man_path:
            man_cmd = shutil.which("man")
            if man_cmd:
                raise SystemExit(subprocess.run([man_cmd, str(man_path)], check=False).returncode)

            groff_cmd = shutil.which("groff")
            if groff_cmd:
                result = subprocess.run(
                    [groff_cmd, "-Tutf8", "-man", str(man_path)],
                    check=False,
                    text=True,
                    capture_output=True,
                )
                if result.stdout:
                    print(result.stdout, end="")
                    raise SystemExit(result.returncode)

            print(man_path.read_text(encoding="utf-8"), end="")
    except FileNotFoundError:
        print("Manual page is not available in this installation.")
        raise SystemExit(1)



# ──────────────────────────────────────────────────────────────────────────────
# main(); Main entry point (used by pyproject.toml [project.scripts])
# ──────────────────────────────────────────────────────────────────────────────
def main() -> None:
    """
    CLI entry point. Parses command line arguments, creates a SessionsBrowser
    instance, and either runs a TUI or outputs textual data based on user input.
    """

    # Define an argument parser for the users command line args
    arg_parser = argparse.ArgumentParser(description        = ARGUMENT_DESCRIPTION,
                                         epilog             = ARGUMENT_EPILOG,
                                         formatter_class    = ARGUMENT_FORMATTER_CLASS)

    arg_parser.add_argument("--year",
                            type=_parse_years,
                            default=None,
                            help="Year expression (default: startup_defaults.json year, or current year). Examples: 2025, 2022,2023, 2022-2025, 2022,2024-2026"
    )
    arg_parser.add_argument("--scope",
                            choices=("master", "intensive", "both"),
                            default=None,
                            help="Which schedules to include (master, intensive, both) (default: startup_defaults.json scope, or both)"
    )
    arg_parser.add_argument("--filters",
                            type=str,
                            help="Initial filters (see help for syntax)")

    arg_parser.add_argument('-o', '--output', metavar='FILE',
                            help='write output to FILE (use - for stdout), and exit')

    #arg_parser.add_argument('-p', '--pretty-print', action='store_true',
    #                        help='pretty print the output')
    arg_parser.add_argument('-p', '--pretty-print',
                            nargs='?',
                            const='ALL',
                            default='ALL',
                            type=_parse_pretty_columns,
                            metavar='ALL|OP|TYPE|CODE|START|DOY|DUR|STATIONS|DB|OPS|CORR|STATUS|ANALYS',
                            help='pretty print columns; use ALL (default) or pipe-delimited names (e.g. OP|TYPE|STATIONS). ANALYSIS is accepted as alias for ANALYS.')

    arg_parser.add_argument('--format', choices=('text', 'pdf', 'xlsx'),
                            default='text', help='output format (default: text); pdf preserves row colors, xlsx writes spreadsheet cells')

    arg_parser.add_argument('-a', '--append', action='store_true',
                            help='append to output file instead of overwriting')

    mirror_group = arg_parser.add_mutually_exclusive_group()
    mirror_group.add_argument('-m', '--mirrors', dest='mirrors', action='store_true',
                              default=None,
                              help='check mirror websites for last update; default is use only primary IVSCC site (https://ivscc.gsfc.nasa.gov)')
    mirror_group.add_argument('--no-mirrors', dest='mirrors', action='store_false',
                              help='disable mirror checking even if startup_defaults.json enables it')

    arg_parser.add_argument('--verbose-fetch', action='store_true',
                            help='show fetch progress and source-status messages even when using --output')

    arg_parser.add_argument('--init-config', action='store_true',
                            help='create default user config files in ~/.config/ivs-sessions-browser and exit')

    arg_parser.add_argument('--man', action='store_true',
                            help='show the bundled manual page and exit')

    # Provide a standard --version flag exposing package version
    # Note: setuptools-scm will automatically update the __version__ variable
    # during build, so this will always reflect the current package version.
    arg_parser.add_argument('--version', action='version', version=__version__)

    args = arg_parser.parse_args()

    if args.man:
        _show_man_page()

    if args.init_config:
        _ensure_user_config_files()
        print("Config initialized in ~/.config/ivs-sessions-browser")
        raise SystemExit(0)

    _apply_startup_defaults(args)

    # Script-friendly mode: suppress progress/status chatter when user requested
    # textual output (stdout/file) via -o/--output.
    if args.output and not args.verbose_fetch:
        os.environ["IVS_SESSIONS_QUIET"] = "1"
    else:
        os.environ.pop("IVS_SESSIONS_QUIET", None)

    # Ensure first-run user-editable config files exist before network fetches
    # or TUI setup.
    _ensure_user_config_files()

    # Define the SessionsBrowser instance, and read html data from web
    # After a successful creation, sb.list_html_data_page contains the fetched HTML data
    sb: SessionsBrowser = SessionsBrowser(_year     = args.year,
                                          _scope    = args.scope,
                                          _mirrors  = args.mirrors,
                                          _filters  = args.filters,
                                          _app_version = __version__)
    # ─── END OF SessionsBrowser creation ──────────────────────────────────────


    # If user requested output to file/stdout, produce textual output and exit
    if args.output:
        if args.format == 'pdf':
            if args.append:
                print("PDF export does not support --append; write a new file instead.")
                raise SystemExit(2)

            # PDF export reuses the same ANSI-colored lines as text output.
            lines = sb.render_sessions_list(args.pretty_print)

            if args.output == '-':
                import sys
                out = sys.stdout.buffer
                try:
                    write_ansi_lines_pdf(lines, out)
                except BrokenPipeError:
                    devnull_fd = os.open(os.devnull, os.O_WRONLY)
                    os.dup2(devnull_fd, sys.stdout.fileno())
                    raise SystemExit(0)
                raise SystemExit(0)

            import tempfile

            target_dir = os.path.dirname(args.output) or '.'
            tmp_name = None
            try:
                with tempfile.NamedTemporaryFile('wb', delete=False, dir=target_dir) as tf:
                    tmp_name = tf.name
                    write_ansi_lines_pdf(lines, tf)
                if tmp_name is not None:
                    os.replace(tmp_name, args.output)
            except OSError as exc:
                print(f"Failed to write PDF output file: {exc}")
                try:
                    if tmp_name and os.path.exists(tmp_name):
                        os.remove(tmp_name)
                except Exception:
                    pass
                raise SystemExit(2) from exc

            raise SystemExit(0)

        if args.format == 'xlsx':
            if args.append:
                print("XLSX export does not support --append; write a new file instead.")
                raise SystemExit(2)

            if args.output == '-':
                import sys
                out = sys.stdout.buffer
                try:
                    write_sessions_xlsx(
                        sb.view_rows,
                        args.pretty_print,
                        sb.operator_bindings,
                        sb.operator_colors,
                        out,
                    )
                except BrokenPipeError:
                    devnull_fd = os.open(os.devnull, os.O_WRONLY)
                    os.dup2(devnull_fd, sys.stdout.fileno())
                    raise SystemExit(0)
                raise SystemExit(0)

            import tempfile

            target_dir = os.path.dirname(args.output) or '.'
            tmp_name = None
            try:
                with tempfile.NamedTemporaryFile('wb', delete=False, dir=target_dir) as tf:
                    tmp_name = tf.name
                    write_sessions_xlsx(
                        sb.view_rows,
                        args.pretty_print,
                        sb.operator_bindings,
                        sb.operator_colors,
                        tf,
                    )
                if tmp_name is not None:
                    os.replace(tmp_name, args.output)
            except OSError as exc:
                print(f"Failed to write XLSX output file: {exc}")
                try:
                    if tmp_name and os.path.exists(tmp_name):
                        os.remove(tmp_name)
                except Exception:
                    pass
                raise SystemExit(2) from exc

            raise SystemExit(0)

        lines = sb.render_sessions_list(args.pretty_print)

        # Write to stdout
        if args.output == '-':
            import sys
            out = sys.stdout
            try:
                for ln in lines:
                    print(ln, file=out)
            except BrokenPipeError:
                # Downstream consumer closed stdout early (e.g. pipe/head or debugger transport).
                # Exit cleanly instead of showing a traceback/non-zero status.
                devnull_fd = os.open(os.devnull, os.O_WRONLY)
                os.dup2(devnull_fd, sys.stdout.fileno())
                raise SystemExit(0)
            raise SystemExit(0)

        # Write to file: support append vs atomic overwrite
        import tempfile

        if args.append:
            # Append directly
            try:
                with open(args.output, 'a', encoding='utf-8') as fh:
                    for ln in lines:
                        fh.write(ln + "\n")
            except OSError as exc:
                print(f"Failed to write output file: {exc}")
                raise SystemExit(2) from exc
        else:
            # Atomic write: write to temp file in same dir then replace
            target_dir = os.path.dirname(args.output) or '.'
            tmp_name = None
            try:
                with tempfile.NamedTemporaryFile('w', delete=False, dir=target_dir, encoding='utf-8') as tf:
                    tmp_name = tf.name
                    for ln in lines:
                        tf.write(ln + "\n")
                if tmp_name is not None:
                    os.replace(tmp_name, args.output)
            except OSError as exc:
                print(f"Failed to write output file: {exc}")
                # Attempt cleanup
                try:
                    if tmp_name and os.path.exists(tmp_name):
                        os.remove(tmp_name)
                except Exception:
                    pass
                raise SystemExit(2) from exc

        raise SystemExit(0)
    # ─── END OF textual output logic ──────────────────────────────────────────



    # No output - start TUI if available using the sb.run() method
    attr = getattr(sb, "run", None)
    if callable(attr):
        attr(False)
    else:
        print('TUI start not implemented; created SessionsBrowser instance.')

    # Exit normally after TUI exits or if TUI not implemented
    raise SystemExit(0)
# ─── END OF main() ────────────────────────────────────────────────────────────


#__all__ = [
#    "__version__",
#    "main",
#    "UIState",
#    "SessionsBrowser",
#    "ReadData",
#    "IvsSessionParser",
#    "DrawTUI",
#]
