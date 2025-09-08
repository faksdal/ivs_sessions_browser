## Setting up the logger ###############################################################################################
# the log output file, should be /var/log/something or /tmp/something
#

import logging, sys
from pathlib import Path

def setup_logger(filename: str = "/var/log/ivs_browser.log",
                 *,
                 name: str = "plot_tics",
                 level: int = logging.DEBUG,
                 to_stdout: bool = True) -> logging.Logger:

    """Create a logger that writes to 'filename' and (optionally) stdout."""
    log = logging.getLogger(name)
    log.setLevel(level)

    # Make idempotent: if called again, don't stack handlers
    if log.handlers:
        log.handlers.clear()

    # Ensure the directory exists
    Path(filename).parent.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter("%(asctime)s-%(levelname)s: %(message)s", "%Y.%m.%d-%H:%M:%S")

    fh = logging.FileHandler(filename, mode="a", encoding="utf-8")
    fh.setFormatter(fmt)
    fh.setLevel(level)
    log.addHandler(fh)

    if to_stdout:
        sh = logging.StreamHandler(sys.stdout)  # stdout (default is stderr)
        sh.setFormatter(fmt)
        sh.setLevel(level)
        log.addHandler(sh)

    # Keep messages from propagating to the root logger (prevents dupes)
    log.propagate = False
    return log
########################################################################################################################
