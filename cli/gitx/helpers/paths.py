from pathlib import Path
from typing import Tuple

from ..config import AppConfig


def _is_full_git_url(target: str) -> bool:
    return target.startswith("https://") or target.startswith("git://") or target.startswith("git@")


def build_clone_url(target: str, provider: str) -> str:
    if _is_full_git_url(target):
        return target

    if "/" not in target:
        msg = "Repository must be in the form 'org/name' when using shorthand syntax."
        raise ValueError(msg)

    org, repo = target.split("/", 1)
    if provider == "github":
        return f"https://github.com/{org}/{repo}.git"

    msg = f"Unsupported provider: {provider}"
    raise ValueError(msg)


def build_clone_paths(target: str, cfg: AppConfig) -> Tuple[Path, Path]:
    if "/" not in target:
        msg = "Repository must be in the form 'org/name'"
        raise ValueError(msg)

    org, repo = target.split("/", 1)
    repo_root = cfg.globals.baseDir / org / repo / repo
    main_worktree = cfg.globals.baseDir / org / repo / f"{repo}-main"
    return repo_root, main_worktree
