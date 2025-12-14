"""Typer application and command wiring for gitx."""

import subprocess
import sys
from typing import List, Optional

import typer
from rich.console import Console
from rich.pretty import pprint

from .config import WorkspaceConfig, show_config, _config
from .helpers import git
from rich.table import Table
from rich.console import Console
from rich.panel import Panel

console = Console()

config = typer.Typer(help="Manage gitx configuration", no_args_is_help=True)
workspace = typer.Typer(help="Manage worktree-based workspaces", no_args_is_help=True)
branch = typer.Typer(help="Manage git branches using worktrees", no_args_is_help=True)

app = typer.Typer(add_completion=True, help="gitx – transparent git superset with workspace helpers", no_args_is_help=True)

app.add_typer(config, name="config")
app.add_typer(branch, name="branch")
app.add_typer(workspace, name="workspace")


#
# TOP LEVEL
# gitx [go/clone] <repo> <branch>
#

@app.command()
def go(repo: str, branch: str = "main") -> None:
    """Switch to the specified workspace (creates it if needed)."""
    workspace: WorkspaceConfig = _config.resolve_workspace(repo)

    if branch not in git.iter_worktrees(workspace):
        console.print("Branch worktree does not exist; creating it now...")
        code = git.detach_new_worktree(workspace, branch)
        if code != 0:
            return code

    print(f"cd {str(workspace.worktree_path_for_branch(branch))}")
    raise typer.Exit(code=0)


@app.command()
def code(repo: str, branch: str = "main") -> None:
    """Open your editor against the specified workspace (creates it if needed)."""
    workspace: WorkspaceConfig = _config.resolve_workspace(repo)

    if branch not in git.iter_worktrees(workspace):
        console.print("Branch worktree does not exist; creating it now...")
        code = git.detach_new_worktree(workspace, branch)
        if code != 0:
            return code

    print(f"cd {str(workspace.worktree_path_for_branch(branch))}")
    subprocess.run([_config.globals.editor, str(workspace.worktree_path_for_branch(branch))], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    raise typer.Exit(code=0)

#
# CLONE
# gitx clone <repo>
#

@app.command()
def clone(
    repo: str = typer.Argument(..., help="Repository to clone, e.g. 'org/name' or full git URL"),
) -> None:
    """Clone a repository into the configured workspaces directory and set up worktrees."""
    workspace: WorkspaceConfig = _config.resolve_workspace(repo)

    if workspace is not None:
        console.print(
            Panel.fit(
                f"[yellow]Workspace already exists.[/] {workspace.workspace_path()}",
                title="gitx clone",
            )
        )
        raise typer.Exit(code=1)

    workspace = git.clone_and_add_worktree(repo)

    if isinstance(workspace, int) and workspace == 1:
        console.print(
            Panel.fit(
                "[red]Unable to determine default branch (no 'main' or 'master' found).[/]",
                title="gitx clone",
            )
        )
        raise typer.Exit(code=1)

    _config.workspaces.update({ repo: workspace })
    _config.save()

    console.print(
        Panel.fit(
            f"[green]Workspace created:[/] {workspace.worktree_path_for_branch(workspace.defaultBranch)}",
            title="gitx clone"
        )
    )

    raise typer.Exit(code=0)


#
# CONFIG
#


@config.command("set")
def config_set(key: str, value: str) -> None:
    """Set a configuration value, e.g. workspaces.baseDir."""
    _config.set_config_value(key, value)
    raise typer.Exit(code=0)


@config.command("get")
def config_get(key: str) -> None:
    """Get a configuration value."""
    console.print(_config.get_value(key))
    raise typer.Exit(code=0)


@config.command("show")
def config_show() -> None:
    """Show the full configuration."""
    cfg = show_config()
    pprint(cfg, expand_all=True, console=console)


#
# BRANCH
#


@branch.command("add")
def branch_add_cmd(repo: str, branch: str) -> None:
    workspace: WorkspaceConfig = _config.resolve_workspace(repo)
    if workspace is None:
        console.print(f"[yellow]Workspace '{repo}' does not exist.[/]")
        raise typer.Exit(code=1)
    git.detach_new_worktree(workspace, branch)
    raise typer.Exit(code=0)


@branch.command("delete")
def branch_delete_cmd(repo: str, branch: str) -> None:
    workspace: WorkspaceConfig = _config.resolve_workspace(repo)
    if workspace is None:
        console.print(f"[yellow]Workspace '{repo}' does not exist.[/]")
        raise typer.Exit(code=1)
    code = git.delete_branch(workspace, branch)
    raise typer.Exit(code=code)


@branch.command("list")
def workspace_list_cmd(repo: str) -> None:
    workspace: WorkspaceConfig = _config.resolve_workspace(repo)
    if workspace is None:
        console.print(f"[yellow]Workspace '{repo}' does not exist.[/]")
        raise typer.Exit(code=1)
    worktrees = list(git.iter_worktrees(workspace))
    table = Table(title=f"Worktrees for {workspace.workspace_path()}")
    table.add_column("Path", style="cyan")
    for path in worktrees:
        table.add_row(path)
    console.print(table)
    raise typer.Exit(code=0)
