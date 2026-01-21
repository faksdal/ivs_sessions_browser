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
from typing import Dict, Any

CONFIG_DIR = Path.home() / ".config" / "ivs_sessions_browser"
OPERATORS_PATH = CONFIG_DIR / "operators.json"
ASSIGNMENTS_PATH = CONFIG_DIR / "operator_assignments.json"


def _load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _save_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def load_operator_bindings(path: Path = OPERATORS_PATH) -> Dict[str, str]:
    """
    operators.json:
      { "bindings": { "1": "OP1", ... } }
    """
    raw = _load_json(path)
    bindings = raw.get("bindings", {}) if isinstance(raw, dict) else {}
    return {str(k): str(v) for k, v in bindings.items()}


def load_operator_assignments(path: Path = ASSIGNMENTS_PATH) -> Dict[str, str]:
    """
    operator_assignments.json:
      { "assignments": { "R41223": "OP1", ... } }
    """
    raw = _load_json(path)
    assignments = raw.get("assignments", {}) if isinstance(raw, dict) else {}
    return {str(k): str(v) for k, v in assignments.items()}


def save_operator_assignments(data: Dict[str, str], path: Path = ASSIGNMENTS_PATH) -> None:
    _save_json({"assignments": data}, path)


# Backwards-compatible names used by the app
def load_operators(path: Path = ASSIGNMENTS_PATH) -> Dict[str, str]:
    return load_operator_assignments(path)


def save_operators(data: Dict[str, str], path: Path = ASSIGNMENTS_PATH) -> None:
    save_operator_assignments(data, path)
