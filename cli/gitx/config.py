import json
import os
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, Type, TypeVar, Optional, get_origin, get_args

from rich.console import Console

console = Console()

CONFIG_DIR_NAME = "gitx"
CONFIG_FILE_NAME = "config.json"

T = TypeVar("T")


@dataclass(slots=True)
class GlobalsConfig:
    baseDir: Path = Path("${HOME}/sources/workspaces")
    defaultProvider: str = "github"
    editor: str = "code"


@dataclass(slots=True)
class RepoConfig:
    full_name: str
    url: str
    defaultBranch: str = "main"
    lastBranch: str = "main"
    path: str = "main"
    provider: Optional[str] = "github"
    org: Optional[str] = None

    def full_name_sanitized(self) -> str:
        return self.full_name.replace("/", "-")

    def name_sanitized(self) -> str:
        return self.full_name_sanitized().split("-", 1)[-1]

    def workspace_path(self) -> Path:
        return Path(os.path.expandvars(_config.globals.baseDir)) / self.full_name_sanitized()

    def repo_root_path(self) -> Path:
        return self.workspace_path() / f"_{self.name_sanitized()}"

    def main_path(self) -> Path:
        return self.workspace_path() / self.name_sanitized()

    def worktree_path_for_branch(self, branch: str) -> Path:
        return self.workspace_path() / f"{self.name_sanitized()}-{branch}"


@dataclass(slots=True)
class AppConfig:
    globals: GlobalsConfig = field(default_factory=GlobalsConfig)
    workspaces: dict[str, RepoConfig] = field(default_factory=dict)

    def save(self) -> None:
        save_config(self)

    @classmethod
    def load(cls) -> "AppConfig":
        return load_config()

    def resolve_workspace(self, label: str) -> RepoConfig:
        workspace: RepoConfig = None
        if label in self.workspaces.keys():
            workspace = self.workspaces[label]
        else:
            for ws in self.workspaces.values():
                if ws.full_name == label:
                    workspace = ws
                    break
        return workspace

    def get_value(self, path: str) -> Any:
        current: Any = self
        for segment in path.split("."):
            if is_dataclass(current):
                current = getattr(current, segment)
            elif isinstance(current, dict):
                current = current[segment]
            else:
                raise KeyError(path)
        return current

    def set_config_value(self, path: str, value: Any) -> None:
        parts = path.split(".")
        current: Any = self
        for i, segment in enumerate(parts):
            is_last = i == len(parts) - 1
            if is_dataclass(current):
                if is_last:
                    setattr(current, segment, value)
                else:
                    current = getattr(current, segment)
            elif isinstance(current, dict):
                if is_last:
                    current[segment] = value
                else:
                    current = current.setdefault(segment, {})
            else:
                raise KeyError(path)
        self.save()


def from_dict(cls: Type[T], data: dict[str, Any]) -> T:
    if not is_dataclass(cls):
        raise TypeError(f"{cls!r} is not a dataclass")

    kwargs: dict[str, Any] = {}

    for f in fields(cls):
        if f.name not in data:
            continue

        value = data[f.name]
        field_type = f.type
        origin = get_origin(field_type)

        if is_dataclass(field_type) and isinstance(value, dict):
            kwargs[f.name] = from_dict(field_type, value)

        elif origin is dict and isinstance(value, dict):
            _, value_type = get_args(field_type)
            if is_dataclass(value_type):
                kwargs[f.name] = {
                    k: from_dict(value_type, v)
                    for k, v in value.items()
                    if isinstance(v, dict)
                }
            else:
                kwargs[f.name] = value

        elif field_type is Path and isinstance(value, str):
            kwargs[f.name] = Path(value).expanduser()

        else:
            kwargs[f.name] = value

    return cls(**kwargs)


def to_dict(obj: Any) -> Any:
    return asdict(obj)


def get_config_path() -> Path:
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg_config_home) if xdg_config_home else Path.home() / ".config"
    return base / CONFIG_DIR_NAME / CONFIG_FILE_NAME


def load_config() -> AppConfig:
    path = get_config_path()
    if not path.exists():
        return AppConfig()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return AppConfig()
    if not isinstance(raw, dict):
        return AppConfig()
    return from_dict(AppConfig, raw)


def save_config(config: AppConfig) -> None:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(to_dict(config), indent=2, default=str),
        encoding="utf-8",
    )


def show_config() -> dict[str, Any]:
    return to_dict(_config)


# Load config once at module load time
_config = load_config()
