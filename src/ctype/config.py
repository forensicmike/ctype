"""Persisted user settings for ctype.

Stored as JSON at ~/.ctype/config.json (cross-platform). Anything not in
DEFAULT_SETTINGS is rejected so a stale config can't silently shadow a typo.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".ctype"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "theme": "monokai",
    "line_numbers": False,
    "background_color": None,
    "tab_size": 4,
    "word_wrap": False,
}

# A curated subset that ships with Pygments and renders well in a terminal.
AVAILABLE_THEMES: list[str] = [
    "monokai",
    "dracula",
    "nord",
    "github-dark",
    "one-dark",
    "solarized-dark",
    "solarized-light",
    "gruvbox-dark",
    "gruvbox-light",
    "fruity",
    "native",
    "vim",
    "vs",
    "default",
    "friendly",
    "colorful",
    "autumn",
    "rrt",
    "trac",
    "tango",
    "perldoc",
    "rainbow_dash",
    "lovelace",
    "inkpot",
    "zenburn",
    "paraiso-dark",
    "paraiso-light",
    "manni",
    "emacs",
    "abap",
]

_BOOL_KEYS = {"line_numbers", "word_wrap"}
_INT_KEYS = {"tab_size"}
_OPTIONAL_STR_KEYS = {"background_color"}


def load_settings() -> dict[str, Any]:
    """Load settings from disk, merged over DEFAULT_SETTINGS."""
    if not CONFIG_FILE.exists():
        return dict(DEFAULT_SETTINGS)
    try:
        stored = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_SETTINGS)
    if not isinstance(stored, dict):
        return dict(DEFAULT_SETTINGS)
    merged = dict(DEFAULT_SETTINGS)
    for key, value in stored.items():
        if key in DEFAULT_SETTINGS:
            merged[key] = value
    return merged


def save_settings(settings: dict[str, Any]) -> Path:
    """Persist settings to disk, returning the path written."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    payload = {k: settings.get(k, DEFAULT_SETTINGS[k]) for k in DEFAULT_SETTINGS}
    CONFIG_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return CONFIG_FILE


def coerce_value(key: str, raw: str) -> Any:
    """Convert a string value (from CLI / REPL) into the right type for ``key``."""
    if key not in DEFAULT_SETTINGS:
        msg = f"Unknown setting: {key!r}"
        raise KeyError(msg)
    if key in _BOOL_KEYS:
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    if key in _INT_KEYS:
        return int(raw)
    if key in _OPTIONAL_STR_KEYS and raw.strip().lower() in {"", "none", "null", "default"}:
        return None
    return raw
