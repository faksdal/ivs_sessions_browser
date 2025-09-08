# log_helper.py

import logging
import sys
from typing import Optional

# --- Custom level: NOTICE (between INFO=20 and WARNING=30)
NOTICE = 25
logging.addLevelName(NOTICE, "NOTICE")

def notice(self: logging.Logger, message, *args, **kwargs):
    if self.isEnabledFor(NOTICE):
        self._log(NOTICE, message, args, **kwargs)

# Add as a real method on Logger
logging.Logger.notice = notice  # type: ignore[attr-defined]

# Default log file path (keep your existing default)
log_filename: str = '../log/ivs_browser.log'


def _has_file_handler(logger: logging.Logger, filename: str) -> bool:
    for h in logger.handlers:
        if isinstance(h, logging.FileHandler):
            # Compare underlying file names if available
            try:
                if getattr(h, 'baseFilename', None) == filename:
                    return True
            except Exception:
                pass
    return False


def _get_stream_handler(logger: logging.Logger) -> Optional[logging.Handler]:
    for h in logger.handlers:
        if isinstance(h, logging.StreamHandler) and getattr(h, "_is_ivsb_stdout", False):
            return h
    return None


def setup_logger(
    filename: str = log_filename,
    *,
    file_level: int = logging.DEBUG,
    stream_level: int = NOTICE
) -> logging.Logger:
    """
    Configure a logger that ALWAYS writes everything (file_level) to 'filename'
    and only emits NOTICE+ to stdout (stream_level).
    """
    logger = logging.getLogger("ivs_browser")
    logger.setLevel(min(file_level, stream_level, logging.DEBUG))

    # File handler: add once
    if not _has_file_handler(logger, filename):
        fh = logging.FileHandler(filename)
        fh.setLevel(file_level)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        ))
        logger.addHandler(fh)

    # Stream handler: add once
    if _get_stream_handler(logger) is None:
        sh = logging.StreamHandler(sys.stdout)
        sh.setLevel(stream_level)             # NOTICE and above to stdout
        sh.setFormatter(logging.Formatter("%(message)s"))
        # Mark so we can find it later
        setattr(sh, "_is_ivsb_stdout", True)
        logger.addHandler(sh)

    return logger


def set_stdout_threshold(logger: logging.Logger, level: int = NOTICE) -> None:
    """
    Change what goes to stdout at runtime, without touching file logging.
    """
    sh = _get_stream_handler(logger)
    if sh is not None:
        sh.setLevel(level)
