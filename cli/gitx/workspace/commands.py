"""Workspace commands for gitx.

Implements:
- gitx workspace add <repo> <branch>
- gitx workspace go <repo> <branch>
- gitx workspace list <repo>
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List

from rich.console import Console
from rich.table import Table

from ..config import AppConfig
from .paths import RepoIdentifier, repo_root_path, workspace_path

console = Console()


def _git(repo_root: Path, *args: str) -> int:
    console.print(f"[blue]Running git command:[/] git {' '.join(args)}")
    return int(
        subprocess.run(
            ["git", *args],
            cwd=str(repo_root),
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
        ).returncode
    )


def _git_capture(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def _branch_exists(repo_root: Path, branch: str) -> bool:
    # Check local branch
    local = _git_capture(repo_root, "show-ref", "--verify", f"refs/heads/{branch}")
    if local.returncode == 0:
        return True

    # Check remote tracking branch
    remote = _git_capture(repo_root, "show-ref", "--verify", f"refs/remotes/origin/{branch}")
    return remote.returncode == 0


def workspace_add(repo_str: str, branch: str, cfg: AppConfig) -> int:
    repo = RepoIdentifier.parse(repo_str)
    repo_root = repo_root_path(repo, cfg)
    ws_path = workspace_path(repo, branch, cfg)

    if not repo_root.exists():
        console.print(f"[red]Repository root does not exist:[/] {repo_root}")
        return 1

    ws_path.parent.mkdir(parents=True, exist_ok=True)

    console.print(f"Adding workspace for [bold]{repo_str}[/] on branch [bold]{branch}[/]")

    exit_code = _git(repo_root, "fetch", "--all")
    if exit_code != 0:
        return exit_code

    if not _branch_exists(repo_root, branch):
        console.print(f"[yellow]Branch '{branch}' does not exist locally or on origin.[/]")
        console.print("Do you want to create it from the current HEAD and push to origin? [y/N]: ", end="")
        try:
            answer = input().strip().lower()
        except EOFError:
            answer = ""

        if answer not in {"y", "yes"}:
            console.print("[red]Aborting: branch was not created.[/]")
            return 1

        # Create branch from current HEAD
        exit_code = _git(repo_root, "checkout", "-b", branch)
        if exit_code != 0:
            console.print(f"[red]Failed to create branch '{branch}'.[/]")
            return exit_code

        # Push and set upstream
        exit_code = _git(repo_root, "push", "-u", "origin", branch)
        if exit_code != 0:
            console.print(f"[red]Failed to push branch '{branch}' to origin.[/]")
            return exit_code

    exit_code = _git(repo_root, "worktree", "add", str(ws_path), branch)
    return exit_code


def workspace_go(repo_str: str, branch: str, cfg: AppConfig) -> int:
    repo = RepoIdentifier.parse(repo_str)
    repo_root = repo_root_path(repo, cfg)
    ws_path = workspace_path(repo, branch, cfg)

    if not ws_path.exists():
        console.print("Workspace does not exist, creating via 'workspace add'.")
        code = workspace_add(repo_str, branch, cfg)
        if code != 0:
            return code

    # Print cd command so the caller can eval it if desired.
    console.print(f"cd {str(ws_path)}")

    subprocess.run([cfg.globals.editor, str(ws_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return 0


def _iter_worktrees(repo_root: Path) -> Iterable[str]:
    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=str(repo_root),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []

    paths: List[str] = []
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            _, path = line.split(" ", 1)
            paths.append(path)
    return paths


def workspace_list(repo_str: str, cfg: AppConfig) -> int:
    repo = RepoIdentifier.parse(repo_str)
    repo_root = repo_root_path(repo, cfg)

    if not repo_root.exists():
        console.print(f"[red]Repository root does not exist:[/] {repo_root}")
        return 1

    worktrees = list(_iter_worktrees(repo_root))

    table = Table(title=f"Worktrees for {repo_str}")
    table.add_column("Path", style="cyan")

    for path in worktrees:
        table.add_row(path)

    console.print(table)
    return 0
