# flake8: noqa
# isort: skip_file

"""
Filename:   operators.py
Author:     jole
Created:    19.01.2026
Description:

Notes:
"""


import json
from importlib import resources
from pathlib import Path
from typing import Any
from . import defs as D

OPERATORS_PATH      = D.CONFIG_DIR / D.OPERATORS_FILENAME
ASSIGNMENTS_PATH    = D.CONFIG_DIR / D.ASSIGNMENTS_FILENAME



def _load_packaged_json(filename: str) -> Any:
    try:
        resource = resources.files("ivs_sessions_browser").joinpath(filename)
        return json.loads(resource.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, ModuleNotFoundError):
        return {}


def _ensure_packaged_default(path: Path, filename: str) -> None:
    if path.exists():
        return

    default_data = _load_packaged_json(filename)
    if not default_data:
        return

    try:
        _save_json(default_data, path)
    except OSError:
        pass


def _load_json(path: Path, *, fallback_package_file: str | None = None) -> Any:
    # dir = Path.cwd()
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        if fallback_package_file is not None:
            _ensure_packaged_default(path, fallback_package_file)
            if path.exists():
                try:
                    with path.open("r", encoding="utf-8") as f:
                        return json.load(f)
                except (FileNotFoundError, json.JSONDecodeError, OSError):
                    pass
            return _load_packaged_json(fallback_package_file)
        return {}


def _save_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def load_operator_bindings(path: Path = OPERATORS_PATH) -> dict[str, str]:
    """
    operators.json:
      { "bindings": { "1": "OP1", ... } }
    """
    fallback    = D.OPERATORS_FILENAME if path == OPERATORS_PATH else None
    raw         = _load_json(path, fallback_package_file=fallback)
    bindings    = raw.get("bindings", {}) if isinstance(raw, dict) else {}
    return {str(k): str(v) for k, v in bindings.items()}


def load_operator_colors(path: Path = OPERATORS_PATH) -> dict[str, str]:
    """
    operators.json:
      { "colors": { "1": "green", "2": "yellow", ... } }
    Returns dict mapping operator key to color name.
    """
    fallback = D.OPERATORS_FILENAME if path == OPERATORS_PATH else None
    raw     = _load_json(path, fallback_package_file=fallback)
    colors  = raw.get("colors", {}) if isinstance(raw, dict) else {}
    return {str(k): str(v) for k, v in colors.items()}


# def load_operator_assignments(path: Path = ASSIGNMENTS_PATH) -> Dict[str, str]:
    # """
    # operator_assignments.json:
    #   { "assignments": { "R41223": "OP1", ... } }
    # """
    # raw = _load_json(path)
    # assignments = raw.get("assignments", {}) if isinstance(raw, dict) else {}
    # return {str(k): str(v) for k, v in assignments.items()}


# def save_operator_assignments(data: dict[str, str], path: Path = ASSIGNMENTS_PATH) -> None:
    # _save_json({"assignments": data}, path)


# Backwards-compatible names used by the app
def load_operator_assignments(path: Path = ASSIGNMENTS_PATH) -> dict[str, str]:
    # return load_operator_assignments(path)
    """
    operator_assignments.json:
      { "assignments": { "R41223": "OP1", ... } }
    """
    raw         = _load_json(path)
    assignments = raw.get("assignments", {}) if isinstance(raw, dict) else {}

    return {str(k): str(v) for k, v in assignments.items()}


def save_operator_assignments(data: dict[str, str], path: Path = ASSIGNMENTS_PATH) -> None:
    # save_operator_assignments(data, path)
    _save_json({"assignments": data}, path)
