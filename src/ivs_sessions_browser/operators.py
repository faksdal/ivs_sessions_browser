"""
Filename:   operators.py
Author:     jole
Created:    19.01.2026
Description:

Notes:
"""

# operators.py
import json
from pathlib import Path
from typing import Dict

DEFAULT_PATH = Path.home() / ".config" / "ivs_session_browser" / "operators.json"


def load_operators(path: Path = DEFAULT_PATH) -> Dict[str, str]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_operators(data: Dict[str, str], path: Path = DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)

