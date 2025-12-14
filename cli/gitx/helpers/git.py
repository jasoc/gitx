"""Workspace commands for gitx.

Implements:
- gitx workspace add <repo> <branch>
- gitx workspace go <repo> <branch>
- gitx workspace list <repo>
"""


import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from rich.console import Console
from rich.table import Table

from ..config import AppConfig, WorkspaceConfig, _config
from .paths import build_clone_paths, build_clone_url

console = Console()


def _git(repo_root: Path, *args: str, cwd: bool = True):
    console.print(f"[dim]git {' '.join(args)}[/]")

    if cwd:
        return subprocess.run(
            ["git", *args],
            cwd=str(repo_root),
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
    else:
        return subprocess.run(
            ["git", *args],
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )


def _git_capture(repo_root: Path, *args: str, cwd: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a git command and capture its output.

    Unlike ``_git``, this helper is intended for read-only commands where we
    need to inspect ``stdout`` programmatically.
    """

    console.print(f"[dim]git {' '.join(args)}[/]")

    if cwd:
        return subprocess.run(
            ["git", *args],
            cwd=str(repo_root),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    else:
        return subprocess.run(
            ["git", *args],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )


@dataclass
class BranchStatus:
    name: str
    remote: Optional[str]
    has_local: bool
    ahead: int
    behind: int
    is_current: bool


def branch_exists(repo_root: Path, branch: str) -> bool:
    # Check local branch
    local = _git(repo_root, "show-ref", "--verify", f"refs/heads/{branch}")
    if local.returncode == 0:
        return True

    # Check remote tracking branch
    remote = _git(repo_root, "show-ref", "--verify", f"refs/remotes/origin/{branch}")
    return remote.returncode == 0


def delete_branch(workspace: WorkspaceConfig, branch: str) -> int:
    repo_root_path = workspace.repo_root_path()

    # Check if the branch exists locally only
    console.print(
        f"Checking local branch [bold]{branch}[/] in workspace [bold]{workspace.full_name}[/]",
    )
    local = _git(repo_root_path, "show-ref", "--verify", f"refs/heads/{branch}")
    if local.returncode != 0:
        console.print(f"[yellow]Branch '{branch}' does not exist locally.[/]")
        return 1

    # If there is a worktree for this branch, remove it first
    worktree_path = workspace.worktree_path_for_branch(branch)

    console.print(f"Removing worktree [bold]{worktree_path}[/] …")
    wt_res = _git(repo_root_path, "worktree", "remove", str(worktree_path))
    if wt_res.returncode != 0:
        console.print(f"[red]Failed to remove worktree '{worktree_path}'.[/]")
        return wt_res.returncode

    # Ask whether to delete from origin as well
    console.print(
        f"Do you also want to delete branch '[bold]{branch}[/]' from origin? [y/N]: ",
        end="",
    )
    try:
        answer = input().strip().lower()
    except EOFError:
        answer = ""

    delete_remote = answer in {"y", "yes"}

    # Delete local branch
    console.print(f"Deleting local branch [bold]{branch}[/] …")
    exit_res = _git(repo_root_path, "branch", "-d", branch)
    if exit_res.returncode != 0:
        console.print(f"[red]Failed to delete local branch '{branch}'.[/]")
        return exit_res.returncode

    # Optionally delete remote branch
    if delete_remote:
        console.print(f"Deleting remote branch [bold]origin/{branch}[/] …")
        exit_res = _git(repo_root_path, "push", "origin", "--delete", branch)
        if exit_res.returncode != 0:
            console.print(f"[red]Failed to delete branch '{branch}' from origin.[/]")
            return exit_res.returncode

    console.print(f"[green]Branch '{branch}' deleted successfully.[/]")
    return 0


def detach_new_worktree(workspace: WorkspaceConfig, branch: str) -> int:

    repo_root_path = workspace.repo_root_path()

    console.print(f"Adding workspace for [bold]{workspace.full_name}[/] on branch [bold]{branch}[/]")

    exit_res = _git(repo_root_path, "fetch", "--all")
    if exit_res.returncode != 0:
        return exit_res.returncode

    if not branch_exists(repo_root_path, branch):
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
        exit_res = _git(repo_root_path, "checkout", "-b", branch)
        print(exit_res)
        if exit_res.returncode != 0:
            console.print(f"[red]Failed to create branch '{branch}'.[/]")
            return exit_res.returncode

        # Push and set upstream
        exit_res = _git(repo_root_path, "push", "-u", "origin", branch)
        if exit_res.returncode != 0:
            console.print(f"[red]Failed to push branch '{branch}' to origin.[/]")
            return exit_res.returncode

    exit_res = _git(repo_root_path, "checkout", "--detach")
    exit_res = _git(repo_root_path, "worktree", "add", str(workspace.worktree_path_for_branch(branch)), branch)
    return exit_res.returncode


def iter_worktrees(workspace: WorkspaceConfig) -> Iterable[str]:
    """Return the list of branch names that have an attached worktree.

    This is primarily used to check whether a given branch already has a
    worktree. For richer information (including paths), prefer
    :func:`list_branches_with_status`.
    """

    repo_root = workspace.repo_root_path()
    result = _git_capture(repo_root, "worktree", "list", "--porcelain")
    if result.returncode != 0 or not result.stdout:
        return []

    branches: List[str] = []
    current_branch_ref: Optional[str] = None

    for raw in result.stdout.splitlines():
        line = raw.strip()
        if line.startswith("branch "):
            _, ref = line.split(" ", 1)
            ref = ref.strip()
            if ref.startswith("refs/heads/"):
                current_branch_ref = ref
                branch_name = ref.split("/")[-1]
                branches.append(branch_name)

    return branches


def _worktree_paths_by_branch(workspace: WorkspaceConfig) -> dict[str, str]:
    """Build a mapping ``branch_name -> worktree_path`` for the repository."""

    repo_root = workspace.repo_root_path()
    result = _git_capture(repo_root, "worktree", "list", "--porcelain")
    if result.returncode != 0 or not result.stdout:
        return {}

    mapping: dict[str, str] = {}
    current_path: Optional[str] = None

    for raw in result.stdout.splitlines():
        line = raw.strip()
        if line.startswith("worktree "):
            _, path = line.split(" ", 1)
            current_path = path.strip()
        elif line.startswith("branch ") and current_path is not None:
            _, ref = line.split(" ", 1)
            ref = ref.strip()
            if ref.startswith("refs/heads/"):
                branch_name = ref.split("/")[-1]
                mapping[branch_name] = current_path

    return mapping


def list_branches_with_status(workspace: WorkspaceConfig) -> List[BranchStatus]:
    """Return local branches enriched with remote and worktree information.

    For each local branch we expose:
    - its optional upstream (remote tracking branch)
    - ahead/behind counts with respect to the upstream
    - whether it has a dedicated worktree and its path
    - whether it is the current ``HEAD``
    """

    repo_root = workspace.repo_root_path()

    # Determine current branch (may be ``HEAD`` in detached mode).
    current_branch = None
    res_head = _git_capture(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    if res_head.returncode == 0 and res_head.stdout:
        name = res_head.stdout.strip()
        if name != "HEAD":
            current_branch = name

    # All local branches with their upstream and tracking summary.
    res_branches = _git_capture(
        repo_root,
        "for-each-ref",
        "--format=%(refname:short)\t%(upstream:short)\t%(upstream:track)",
        "refs/heads",
    )
    if res_branches.returncode != 0 or not res_branches.stdout:
        return []

    worktrees = _worktree_paths_by_branch(workspace)

    statuses: dict[str, BranchStatus] = {}
    local_branch_names: List[str] = []

    def _parse_upstream_track(track: str) -> tuple[int, int]:
        """Parse a ``%(upstream:track)`` string into (ahead, behind).

        Examples of track strings:
        - "[ahead 2]"
        - "[behind 1]"
        - "[ahead 2, behind 1]"
        - "[up to date]"
        - "" (no upstream)
        """

        track = track.strip()
        if not track:
            return 0, 0

        if track.startswith("[") and track.endswith("]"):
            track = track[1:-1].strip()

        if not track or track == "up to date" or track == "-":
            return 0, 0

        ahead = 0
        behind = 0
        parts = [p.strip() for p in track.split(",") if p.strip()]
        for part in parts:
            tokens = part.split()
            if len(tokens) != 2:
                continue
            kind, value = tokens
            try:
                count = int(value)
            except ValueError:
                continue
            if kind == "ahead":
                ahead = count
            elif kind == "behind":
                behind = count

        return ahead, behind

    for raw in res_branches.stdout.splitlines():
        if not raw.strip():
            continue
        parts = raw.split("\t")
        name = parts[0].strip()
        local_branch_names.append(name)
        upstream = parts[1].strip() if len(parts) > 1 else ""
        track = parts[2].strip() if len(parts) > 2 else ""
        remote: Optional[str] = upstream or None

        ahead, behind = _parse_upstream_track(track)

        statuses[name] = BranchStatus(
            name=name,
            remote=remote,
            has_local=True,
            ahead=ahead,
            behind=behind,
            is_current=(name == current_branch),
        )

    # Add remote-only branches (i.e. those without a local counterpart).
    res_remotes = _git_capture(
        repo_root,
        "for-each-ref",
        "--format=%(refname:short)",
        "refs/remotes",
    )
    if res_remotes.returncode == 0 and res_remotes.stdout:
        for raw in res_remotes.stdout.splitlines():
            ref = raw.strip()
            if not ref or ref.endswith("/HEAD"):
                # Skip symbolic heads like origin/HEAD
                continue

            # ref example: origin/feature/foo -> branch_name: feature/foo
            if "/" not in ref:
                continue

            _, branch_name = ref.split("/", 1)

            if branch_name in local_branch_names:
                # Already represented by the local branch row; ensure remote is set.
                status = statuses.get(branch_name)
                if status is not None and not status.remote:
                    status.remote = ref
                continue

            statuses[branch_name] = BranchStatus(
                name=branch_name,
                remote=ref,
                has_local=False,
                ahead=0,
                behind=0,
                is_current=False,
            )

    # Return statuses sorted by branch name for stable output.
    return [statuses[name] for name in sorted(statuses.keys())]


def clone_and_add_worktree(target: str) -> WorkspaceConfig | int:
    """Execute the gitx clone workflow.

    1. git clone <url> <path>
    2. git checkout --detach
    3. git worktree add <path>-main main
    """

    url = build_clone_url(target, _config.globals.defaultProvider)

    workspace_config = WorkspaceConfig(
        full_name=target,
        url=url,
        lastBranch="",
        defaultBranch=""
    )

    repo_root = workspace_config.repo_root_path()
    repo_root_parent = repo_root.parent
    repo_root_parent.mkdir(parents=True, exist_ok=True)

    # 1. git clone
    console.rule("git clone")
    repo_root.mkdir(parents=True, exist_ok=True)

    result = _git(repo_root_parent, "clone", url, str(repo_root), cwd=False)
    if result.returncode != 0:
        console.print(f"[red]Git clone failed with exit code {result.returncode}[/]")
        return int(result.returncode)

    # 2. git checkout --detach (in cloned repo)
    console.rule("git checkout --detach")
    result = _git(repo_root, "checkout", "--detach")
    if result.returncode != 0:
        console.print(f"[red]Git checkout failed with exit code {result.returncode}[/]")
        return int(result.returncode)

    # 3. determine default branch (prefer remote HEAD, fall back to main/master)
    master_branch = None
    result = _git(repo_root, "symbolic-ref", "refs/remotes/origin/HEAD")

    if result.returncode == 0 and result.stdout:
        # refs/remotes/origin/main -> main
        master_branch = result.stdout.strip().split("/")[-1]
    else:
        # try common candidates (remote then local)
        for candidate in ("origin/main", "origin/master", "main", "master"):
            check = _git(repo_root, "rev-parse", "--verify", candidate)

            if check.returncode == 0:
                master_branch = candidate.split("/")[-1]
                break

    if master_branch is None:
        return 1

    console.rule(f"git worktree add {str(workspace_config.worktree_path_for_branch(master_branch))} {master_branch}")
    result = _git(repo_root, "worktree", "add", str(workspace_config.worktree_path_for_branch(master_branch)), master_branch)
    if result.returncode != 0:
        return int(result.returncode)

    workspace_config.defaultBranch = master_branch

    return workspace_config
