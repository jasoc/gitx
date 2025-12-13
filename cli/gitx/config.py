"""Configuration handling for gitx.

Configuration is stored as JSON in the XDG config directory, typically
"$HOME/.config/gitx/config.json".
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from rich.console import Console

console = Console()


CONFIG_DIR_NAME = "gitx"
CONFIG_FILE_NAME = "config.json"


VALID_PATHS = {
    "workspaces.baseDir",
    "workspaces.provider",
    "workspaces.editor"
}


@dataclass(slots=True)
class WorkspaceConfig:
    base_dir: Path
    provider: str
    editor: str


@dataclass(slots=True)
class AppConfig:
    workspaces: WorkspaceConfig


DEFAULT_CONFIG: Dict[str, Any] = {
    "workspaces": {
        "baseDir": "${HOME}/sources/workspaces",
        "provider": "github",
        "editor": "nano"
    }
}


def _expand_env(path_str: str) -> str:
    return os.path.expandvars(path_str)


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
            section = merged.setdefault(key, {})  # type: ignore[assignment]
            if isinstance(section, dict):
                section.update(value)
        else:
            merged[key] = value

    return merged


def parse_app_config(raw: Dict[str, Any]) -> AppConfig:
    workspaces_raw = raw.get("workspaces", {})
    base_dir_raw = str(workspaces_raw.get("baseDir", DEFAULT_CONFIG["workspaces"]["baseDir"]))
    provider = str(workspaces_raw.get("provider", DEFAULT_CONFIG["workspaces"]["provider"]))
    editor = str(workspaces_raw.get("editor", DEFAULT_CONFIG["workspaces"]["editor"]))

    expanded_base = _expand_env(base_dir_raw)
    base_path = Path(expanded_base).expanduser().resolve()
    base_path.mkdir(parents=True, exist_ok=True)

    workspace_cfg = WorkspaceConfig(base_dir=base_path, provider=provider, editor=editor)
    return AppConfig(workspaces=workspace_cfg)


def load_config() -> AppConfig:
    raw = load_raw_config()
    return parse_app_config(raw)


def save_config_value(path: str, value: str) -> None:
    """Set a configuration value and write it back to disk.

    Currently supports only "workspaces.baseDir" and "workspaces.provider".
    """

    if path not in VALID_PATHS:
        msg = f"Unsupported config key: {path}. Supported keys: {', '.join(sorted(VALID_PATHS))}"
        raise ValueError(msg)

    config_path = get_config_path()
    ensure_config_dir_exists(config_path)

    raw = load_raw_config()

    section_name, key = path.split(".", 1)
    section = raw.setdefault(section_name, {})
    if not isinstance(section, dict):
        raise ValueError(f"Invalid config structure at section '{section_name}'")

    section[key] = value

    config_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")


def show_config() -> Dict[str, Any]:
    """Return the current raw configuration for display purposes."""

    return load_raw_config()
