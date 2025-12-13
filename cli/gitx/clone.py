"""Implementation of `gitx clone` command."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Tuple

from rich.console import Console
from rich.panel import Panel

from .config import AppConfig

console = Console()


def _is_full_git_url(target: str) -> bool:
    return target.startswith("https://") or target.startswith("git://") or target.startswith("git@")


def build_clone_url(target: str, provider: str) -> str:
    """Build a full git URL from a shorthand like "org/repo".

    Currently only supports GitHub via HTTPS.
    """

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
    """Return (repo_root, main_worktree_path).

    repo_root is where the bare clone goes; main_worktree_path is for the main branch.
    """

    if "/" not in target:
        msg = "Repository must be in the form 'org/name'"
        raise ValueError(msg)

    org, repo = target.split("/", 1)
    repo_root = cfg.workspaces.base_dir / org / repo
    main_worktree = cfg.workspaces.base_dir / org / f"{repo}-main"
    return repo_root, main_worktree


def run_gitx_clone(target: str, cfg: AppConfig) -> int:
    """Execute the gitx clone workflow.

    1. git clone <url> <path>
    2. git checkout --detach
    3. git worktree add <path>-main main
    """

    url = build_clone_url(target, cfg.workspaces.provider)
    repo_root, main_worktree = build_clone_paths(target, cfg)

    repo_root_parent = repo_root.parent
    repo_root_parent.mkdir(parents=True, exist_ok=True)

    if repo_root.exists():
        console.print(Panel.fit(f"[yellow]Directory already exists:[/] {repo_root}", title="gitx clone"))
        return 1

    # 1. git clone
    console.rule("git clone")
    result = subprocess.run(
        ["git", "clone", url, str(repo_root)],
        stdin=sys.stdin,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    if result.returncode != 0:
        return int(result.returncode)

    # 2. git checkout --detach (in cloned repo)
    console.rule("git checkout --detach")
    result = subprocess.run(
        ["git", "checkout", "--detach"],
        cwd=str(repo_root),
        stdin=sys.stdin,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    if result.returncode != 0:
        return int(result.returncode)

    # 3. git worktree add <path>-main main
    console.rule("git worktree add main worktree")
    result = subprocess.run(
        ["git", "worktree", "add", str(main_worktree), "main"],
        cwd=str(repo_root),
        stdin=sys.stdin,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    if result.returncode != 0:
        return int(result.returncode)

    console.print(Panel.fit(f"[green]Workspace created:[/] {main_worktree}", title="gitx clone"))
    return 0
