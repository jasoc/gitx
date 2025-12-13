"""Configuration handling for gitx.

Configuration is stored as JSON in the XDG config directory, typically
"$HOME/.config/gitx/config.json".
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar

from rich.console import Console

console = Console()


CONFIG_DIR_NAME = "gitx"
CONFIG_FILE_NAME = "config.json"


VALID_PATHS = {
    r"globals\.baseDir",
    r"globals\.defaultProvider",
    r"globals\.editor",
    r"workspaces\.[^.]+\.defaultBranch",
}


@dataclass(slots=True)
class GlobalsConfig:
    baseDir: Path
    defaultProvider: str
    editor: str


@dataclass(slots=True)
class WorkspaceConfig:
    name: str
    url: str
    lastBranch: str
    defaultBranch: str
    org: Optional[str] = None
    author: Optional[str] = None


@dataclass(slots=True)
class AppConfig:
    globals: GlobalsConfig
    workspaces: dict[str, WorkspaceConfig]


DEFAULT_CONFIG: Dict[str, Any] = {
    "globals": {
        "baseDir": "${HOME}/sources/workspaces",
        "defaultProvider": "github",
        "editor": "code",
    },
    "workspaces": {},
}


T = TypeVar("T")


def _expand_env(path_str: str) -> str:
    return os.path.expandvars(path_str)


def _dict_to_dataclass(data: Dict[str, Any], cls: Type[T]) -> T:
    """Dynamically map a dictionary to a dataclass instance.

    Nested dataclasses are supported when the target field type is a dataclass.
    Extra keys in the input dictionary are ignored so configuration can evolve
    without breaking older versions of the code.
    """

    if not is_dataclass(cls):  # type: ignore[arg-type]
        msg = f"Target {cls!r} is not a dataclass"
        raise TypeError(msg)

    kwargs: Dict[str, Any] = {}

    for f in fields(cls):  # type: ignore[arg-type]
        raw_key = f.name
        # Allow simple camelCase -> snake_case for JSON keys like baseDir
        json_key = raw_key
        if "_" in raw_key:
            parts = raw_key.split("_")
            json_key = parts[0] + "".join(p.capitalize() for p in parts[1:])

        if json_key not in data:
            continue

        value = data[json_key]

        # Support nested dataclasses
        if is_dataclass(f.type) and isinstance(value, dict):  # type: ignore[arg-type]
            kwargs[raw_key] = _dict_to_dataclass(value, f.type)  # type: ignore[arg-type]
            continue

        kwargs[raw_key] = value

    return cls(**kwargs)


def get_config_path() -> Path:
    """Return the path to the gitx config file.

    Uses XDG_CONFIG_HOME if set, otherwise falls back to ~/.config.
    """

    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg_config_home) if xdg_config_home else Path.home() / ".config"
    return base / CONFIG_DIR_NAME / CONFIG_FILE_NAME


def ensure_config_dir_exists(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_raw_config() -> Dict[str, Any]:
    """Load raw JSON configuration, falling back to defaults when missing."""

    config_path = get_config_path()
    if not config_path.exists():
        return DEFAULT_CONFIG.copy()

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        console.print(f"[red]Invalid JSON in config file:[/] {config_path} — using defaults")
        return DEFAULT_CONFIG.copy()

    merged: Dict[str, Any] = DEFAULT_CONFIG.copy()
    for key, value in data.items():
        if isinstance(value, dict):
            section = merged.setdefault(key, {})
            if isinstance(section, dict):
                section.update(value)
        else:
            merged[key] = value

    return merged


def parse_app_config(raw: Dict[str, Any]) -> AppConfig:
    """Parse a raw configuration dictionary into an AppConfig."""

    # --- globals section ---
    globals_raw = raw.get("globals", {})
    if not isinstance(globals_raw, dict):
        globals_raw = {}

    globals_cfg = _dict_to_dataclass(globals_raw, GlobalsConfig)

    expanded_base = _expand_env(str(globals_raw.get("baseDir", DEFAULT_CONFIG["globals"]["baseDir"])))
    base_path = Path(expanded_base).expanduser().resolve()
    base_path.mkdir(parents=True, exist_ok=True)
    globals_cfg.baseDir = base_path

    # workspaces section
    workspaces_raw = raw.get("workspaces", {})
    workspaces: dict[str, WorkspaceConfig] = {}
    if isinstance(workspaces_raw, dict):
        for ws_key, ws_val in workspaces_raw.items():
            if not isinstance(ws_val, dict):
                continue
            try:
                workspaces[ws_key] = _dict_to_dataclass(ws_val, WorkspaceConfig)
            except TypeError:
                # Ignore workspaces that do not match the expected shape to keep
                # parsing resilient to future schema changes.
                continue

    return AppConfig(globals=globals_cfg, workspaces=workspaces)


def load_config() -> AppConfig:
    raw = load_raw_config()
    return parse_app_config(raw)


def _is_valid_config_path(path: str) -> bool:
    """Return True if the given dot-path matches at least one VALID_PATH regex."""

    for pattern in VALID_PATHS:
        if re.fullmatch(pattern, path):
            return True
    return False


def save_config_value(path: str, value: str) -> None:
    """Set a configuration value and write it back to disk.

    The `path` is validated against the regex patterns in VALID_PATHS, so new
    keys can be authorised by simply adding an appropriate pattern.
    """

    if not _is_valid_config_path(path):
        msg = "Unsupported config key: {path}. Supported key patterns: {patterns}".format(
            path=path,
            patterns=", ".join(sorted(VALID_PATHS)),
        )
        raise ValueError(msg)

    config_path = get_config_path()
    ensure_config_dir_exists(config_path)

    raw = load_raw_config()

    # Support nested paths using dot-notation (e.g. "global.baseDir" or
    # "workspaces.myspace.defaultBranch").
    parts = path.split(".")
    section: Dict[str, Any] = raw
    for segment in parts[:-1]:
        next_section = section.setdefault(segment, {})
        if not isinstance(next_section, dict):
            raise ValueError(f"Invalid config structure at section '{segment}'")
        section = next_section

    section[parts[-1]] = value

    config_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")


def show_config() -> Dict[str, Any]:
    """Return the current raw configuration for display purposes."""

    return load_raw_config()
