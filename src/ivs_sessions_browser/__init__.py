# --- file: __init__.py

# ──────────────────────────────────────────────────────────────────────────────
# Import section
# ──────────────────────────────────────────────────────────────────────────────
import argparse
from datetime import datetime

# Project defined imports
from .defs import ARGUMENT_DESCRIPTION, ARGUMENT_EPILOG, ARGUMENT_FORMATTER_CLASS
from .sessions_browser import SessionsBrowser

# from .sessions_browser import SessionsBrowser
# ─── END OF Import section ────────────────────────────────────────────────────



# ──────────────────────────────────────────────────────────────────────────────
# Version (managed by setuptools-scm)
# ──────────────────────────────────────────────────────────────────────────────
try:
    from ._version import version as __version__
except ImportError:
    __version__ = "0.0.0"
# ─── END OF Version ───────────────────────────────────────────────────────────



# ──────────────────────────────────────────────────────────────────────────────
# main(); Main entry point (used by pyproject.toml [project.scripts])
# ──────────────────────────────────────────────────────────────────────────────
def main() -> None:
    """
    CLI entry point.

    Possible command line arguments:
        * --year        {the year you want to browse: xxxx}
        * --scope       {master, intensive, both}, defaults to both
        * --stations    {[station code: Xx]}, supports |(OR), &(AND), defaults to all stations
    """



    # Define an argument parser for the users command line args
    arg_parser = argparse.ArgumentParser(description        = ARGUMENT_DESCRIPTION,
                                         epilog             = ARGUMENT_EPILOG,
                                         formatter_class    = ARGUMENT_FORMATTER_CLASS)

    arg_parser.add_argument("--year",
                            type=int,
                            default=datetime.now().year,
                            help="Year (yyyy) (default: current year)"
    )
    arg_parser.add_argument("--scope",
                            choices=("master", "intensive", "both"),
                            default="both",
                            help="Which schedules to include (master, intensive, both) (default: both)"  # noqa: E501
    )
    arg_parser.add_argument("--filters",
                            type=str,
                            help="Initial filters (see help for syntax)")

    arg_parser.add_argument('-o', '--output', metavar='FILE',
                            help='write textual output to FILE (use - for stdout), and exit')
    arg_parser.add_argument('--format', choices=('text', 'json', 'csv'),
                            default='text', help='output format (default: text)')
    arg_parser.add_argument('-a', '--append', action='store_true',
                            help='append to output file instead of overwriting')

    # Provide a standard --version flag exposing package version
    arg_parser.add_argument('--version', action='version', version=__version__)

    args = arg_parser.parse_args()

    # Define the SessionsBrowser instance
    sb: SessionsBrowser = SessionsBrowser(_year     = args.year,
                                          _scope    = args.scope,
                                          _filters  = args.filters)

    # If user requested output to file/stdout, produce textual output and exit
    if args.output:
        # Only 'text' format implemented for now
        if args.format != 'text':
            print(f"Requested format '{args.format}' not implemented; only 'text' is supported.")
            raise SystemExit(2)

        # Generate textual output
        lines = sb.render_sessions_list()

        # Write to stdout
        if args.output == '-':
            import sys
            out = sys.stdout
            for ln in lines:
                print(ln, file=out)
            raise SystemExit(0)

        # Write to file: support append vs atomic overwrite
        import os
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
                with tempfile.NamedTemporaryFile('w', delete=False, dir=target_dir, encoding='utf-8') as tf:  # noqa: E501
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



    # No output - start TUI if available
    attr = getattr(sb, "run", None)
    if callable(attr):
        attr()
    else:
        print('TUI start not implemented; created SessionsBrowser instance.')

    #if hasattr(sb, 'run'):
    #    sb.run()    # callable() is also possible to use, for added safety
    #else:
    #    print('TUI start not implemented; created SessionsBrowser instance.')

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

