import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.pretty import pprint
from rich.table import Table
from rich.panel import Panel

from .config import RepoConfig, get_config_path, show_config, _config
from .helpers import git
from .helpers.update import maybe_check_for_update

console = Console()

app = typer.Typer(add_completion=True)

config = typer.Typer(no_args_is_help=True)
branch = typer.Typer(no_args_is_help=True)

app.add_typer(config, name="config")
app.add_typer(branch, name="branch")


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context) -> None:
    maybe_check_for_update(console)


# ===========================================================================
# core
# ===========================================================================

def resolve_worktree(
    repo_cfg: RepoConfig,
    branch: Optional[str],
    *,
    interactive: bool = True,
) -> Path:
    if branch is None:
        branch = repo_cfg.lastBranch or repo_cfg.defaultBranch

    if branch in git.iter_worktrees(repo_cfg):
        repo_cfg.lastBranch = branch
        _config.save()
        return repo_cfg.worktree_path_for(branch)

    if not interactive:
        raise RuntimeError("Worktree does not exist")

    if not git.branch_exists(repo_cfg.main_git_path(), branch):
        create_branch = typer.confirm(
            f"Branch '{branch}' does not exist. Create it from current HEAD?",
            default=False,
        )
        if not create_branch:
            raise RuntimeError("Branch does not exist")

        try:
            git.create_branch(repo_cfg, branch)
        except git.GitCommandFailed as exc:
            raise RuntimeError(f"Failed to create branch '{branch}': {exc}") from exc

    create_worktree = typer.confirm(
        f"Worktree for branch '{branch}' does not exist. Create it?",
        default=True,
    )
    if not create_worktree:
        raise RuntimeError("Worktree does not exist")

    git.add_worktree(repo_cfg, branch)

    repo_cfg.lastBranch = branch
    _config.save()

    return repo_cfg.worktree_path_for(branch)


# ===========================================================================
# go
# ===========================================================================

@app.command()
def go(repo: str, branch: Optional[str] = None) -> None:
    repo_cfg: RepoConfig | None = _config.resolve_workspace(repo)

    if repo_cfg is None:
        clone_repo = typer.confirm(
            f"Repository '{repo}' does not exist. Clone it?",
            default=True,
        )
        if not clone_repo:
            raise typer.Exit(code=1)

        try:
            repo_cfg = git.clone_and_add_worktree(repo)
        except Exception as exc:  # GitCommandFailed, GitxError, etc.
            console.print(f"[red]{exc}[/]")
            raise typer.Exit(code=1)

        _config.workspaces.update({repo: repo_cfg})
        _config.save()

    try:
        path = resolve_worktree(repo_cfg, branch)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=1)

    print(str(path))
    raise typer.Exit(code=0)


# ===========================================================================
# code
# ===========================================================================

@app.command()
def code(repo: str, branch: Optional[str] = None) -> None:
    repo_cfg: RepoConfig | None = _config.resolve_workspace(repo)

    if repo_cfg is None:
        clone_repo = typer.confirm(
            f"Repository '{repo}' does not exist. Clone it?",
            default=True,
        )
        if not clone_repo:
            raise typer.Exit(code=1)

        try:
            repo_cfg = git.clone_and_add_worktree(repo)
        except Exception as exc:  # GitCommandFailed, GitxError, etc.
            console.print(f"[red]{exc}[/]")
            raise typer.Exit(code=1)

        _config.workspaces.update({repo: repo_cfg})
        _config.save()

    try:
        path = resolve_worktree(repo_cfg, branch)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=1)

    subprocess.run(
        [_config.globals.editor, str(path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    print(str(path))
    raise typer.Exit(code=0)


# ===========================================================================
# clone
# ===========================================================================

@app.command()
def clone(repo: str) -> None:
    repo_cfg: RepoConfig | None = _config.resolve_workspace(repo)

    if repo_cfg is not None:
        console.print(
            Panel.fit(
                f"[yellow]Repository already exists.[/] {repo_cfg.main_git_path()}",
                title="gitx clone",
            )
        )
        raise typer.Exit(code=1)

    try:
        repo_cfg = git.clone_and_add_worktree(repo)
    except Exception as exc:  # GitCommandFailed, GitxError, etc.
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=1)

    _config.workspaces.update({repo: repo_cfg})
    _config.save()

    console.print(
        Panel.fit(
            f"[green]Repository ready:[/] "
            f"{repo_cfg.worktree_path_for(repo_cfg.defaultBranch)}",
            title="gitx clone",
        )
    )

    raise typer.Exit(code=0)


# ===========================================================================
# config
# ===========================================================================

@config.command("set")
def config_set(key: str, value: str) -> None:
    _config.set_config_value(key, value)
    raise typer.Exit(code=0)


@config.command("get")
def config_get(key: str) -> None:
    console.print(_config.get_value(key))
    raise typer.Exit(code=0)


@config.command("show")
def config_show() -> None:
    pprint(show_config(), expand_all=True, console=console)
    raise typer.Exit(code=0)


@config.command("edit")
def config_edit() -> None:
    subprocess.run(
        [_config.globals.editor, str(get_config_path())],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    raise typer.Exit(code=0)


# ===========================================================================
# branch add
# ===========================================================================

@branch.command("add")
def branch_add(repo: str, branch: str) -> None:
    repo_cfg: RepoConfig | None = _config.resolve_workspace(repo)

    if repo_cfg is None:
        clone_repo = typer.confirm(
            f"Repository '{repo}' does not exist. Clone it?",
            default=True,
        )
        if not clone_repo:
            raise typer.Exit(code=1)

        if git.branch_exists(repo_cfg.repo_root_path(), branch):
            console.print(f"[red]Branch '{branch}' already exists locally.[/]")
            raise typer.Exit(code=0)

        try:
            repo_cfg = git.clone_and_add_worktree(repo)
        except Exception as exc:  # GitCommandFailed, GitxError, etc.
            console.print(f"[red]{exc}[/]")
            raise typer.Exit(code=1)

        _config.workspaces.update({repo: repo_cfg})
        _config.save()

    raise typer.Exit(code=0)


# ===========================================================================
# branch delete
# ===========================================================================

@branch.command("delete")
def branch_delete(repo: str, branch: str) -> None:
    repo_cfg: RepoConfig | None = _config.resolve_workspace(repo)

    if repo_cfg is None:
        console.print(f"[yellow]Repository '{repo}' does not exist.[/]")
        raise typer.Exit(code=1)

    delete_remote = typer.confirm(
        f"Also delete remote branch 'origin/{branch}'?",
        default=False,
    )

    try:
        git.delete_branch(repo_cfg, branch, delete_remote=delete_remote)
    except git.BranchDoesNotExist as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=1)
    except git.GitCommandFailed as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=1)

    raise typer.Exit(code=0)


# ===========================================================================
# branch list
# ===========================================================================

@branch.command("list")
def branch_list(repo: str) -> None:
    repo_cfg: RepoConfig | None = _config.resolve_workspace(repo)

    if repo_cfg is None:
        console.print(f"[yellow]Repository '{repo}' does not exist.[/]")
        raise typer.Exit(code=1)

    statuses = git.list_branches_with_status(repo_cfg)
    if not statuses:
        raise typer.Exit(code=0)

    table = Table(title=f"Branches for {repo_cfg.main_git_path()}")
    table.add_column("Branch")
    table.add_column("Remote")
    table.add_column("Local")
    table.add_column("Status")

    for s in statuses:
        name = f"* {s.name}" if s.is_current else s.name
        remote = s.remote or "-"
        local = "yes" if s.has_local else "no"

        if s.ahead == 0 and s.behind == 0:
            sync = "in sync"
        elif s.ahead > 0 and s.behind == 0:
            sync = f"↑ {s.ahead}"
        elif s.ahead == 0 and s.behind > 0:
            sync = f"↓ {s.behind}"
        else:
            sync = f"↑ {s.ahead} / ↓ {s.behind}"

        table.add_row(name, remote, local, sync)

    console.print(table)
    raise typer.Exit(code=0)