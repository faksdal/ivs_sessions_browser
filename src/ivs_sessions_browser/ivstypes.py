from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime  #, timezone
from typing import Any

# ──────────────────────────────────────────────────────────────────────────────
# Public types
# ──────────────────────────────────────────────────────────────────────────────
Row = tuple[list[str], str | None, dict[str, Any]]
# ─── END OF Public type ───────────────────────────────────────────────────────



# ──────────────────────────────────────────────────────────────────────────────
# Data classes and types
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class PageData:
    html            : str
    last_modified   : datetime | None
    url             : str | None = None
# ─── END OF Data classes and types ────────────────────────────────────────────
