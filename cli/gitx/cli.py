"""Typer application and command wiring for gitx."""

from __future__ import annotations

import sys
from typing import List, Optional

import typer
from rich.console import Console

from .clone import run_gitx_clone
from .config import AppConfig, load_config, save_config_value, show_config
from .workspace.commands import workspace_add, workspace_go, workspace_list

console = Console()

config_app = typer.Typer(help="Manage gitx configuration")
workspace_app = typer.Typer(help="Manage worktree-based workspaces")

app = typer.Typer(add_completion=False, help="gitx – transparent git superset with workspace helpers")

app.add_typer(config_app, name="config")
app.add_typer(workspace_app, name="workspace")


@app.command()
def clone(
    repo: str = typer.Argument(..., help="Repository to clone, e.g. 'org/name' or full git URL"),
) -> None:
    """Clone a repository into the configured workspaces directory and set up worktrees."""

    cfg = load_config()
    try:
        exit_code = run_gitx_clone(repo, cfg)
    except ValueError as exc:  # invalid input
        console.print(f"[red]{exc}")
        raise typer.Exit(code=1) from exc

    raise typer.Exit(code=exit_code)


@config_app.command("set")
def config_set(key: str, value: str) -> None:
    """Set a configuration value, e.g. workspaces.baseDir."""

    try:
        save_config_value(key, value)
    except ValueError as exc:
        console.print(f"[red]{exc}")
        raise typer.Exit(code=1) from exc


@config_app.command("get")
def config_get(key: str) -> None:
    """Get a configuration value."""

    cfg = show_config()
    parts = key.split(".")
    cur = cfg
    for part in parts:
        if not isinstance(cur, dict) or part not in cur:
            raise typer.Exit(code=1)
        cur = cur[part]
    console.print(cur)


@config_app.command("show")
def config_show() -> None:
    """Show the full configuration."""

    cfg = show_config()
    console.print(cfg)


@workspace_app.command("add")
def workspace_add_cmd(repo: str, branch: str) -> None:
    cfg = load_config()
    try:
        code = workspace_add(repo, branch, cfg)
    except ValueError as exc:
        console.print(f"[red]{exc}")
        raise typer.Exit(code=1) from exc
    raise typer.Exit(code=code)


@workspace_app.command("go")
def workspace_go_cmd(repo: str, branch: str) -> None:
    cfg = load_config()
    try:
        code = workspace_go(repo, branch, cfg)
    except ValueError as exc:
        console.print(f"[red]{exc}")
        raise typer.Exit(code=1) from exc
    raise typer.Exit(code=code)


@workspace_app.command("list")
def workspace_list_cmd(repo: str) -> None:
    cfg = load_config()
    try:
        code = workspace_list(repo, cfg)
    except ValueError as exc:
        console.print(f"[red]{exc}")
        raise typer.Exit(code=1) from exc
    raise typer.Exit(code=code)

