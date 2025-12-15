import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from ..config import RepoConfig, _config
from .paths import build_clone_url
from .cli import cmd, cmd_capture


# ===========================================================================
# errors
# ===========================================================================


class BranchDoesNotExist(RuntimeError):
    def __init__(self, branch: str):
        super().__init__(f"Branch does not exist: {branch}")
        self.branch = branch


class WorktreeDoesNotExist(RuntimeError):
    def __init__(self, branch: str):
        super().__init__(f"Worktree does not exist for branch: {branch}")
        self.branch = branch


class GitCommandFailed(RuntimeError):
    def __init__(self, args: list[str], result: subprocess.CompletedProcess):
        print(f"Git command failed ({result.returncode}): {' '.join(args)} {result}")
        super().__init__(f"Git command failed ({result.returncode}): {' '.join(args)} {result.stdout} {result.stderr}")
        self.args = args
        self.code = result.returncode


class GitxError(RuntimeError):
    pass


# ===========================================================================
# models
# ===========================================================================

@dataclass
class BranchStatus:
    name: str
    remote: Optional[str]
    has_local: bool
    ahead: int
    behind: int
    is_current: bool


# ===========================================================================
# primitives
# ===========================================================================

def branch_exists(repo_root: Path, branch: str) -> bool:
    local = cmd(repo_root, "git", "show-ref", "--verify", f"refs/heads/{branch}")
    if local.returncode == 0:
        return True

    remote = cmd(repo_root, "git", "show-ref", "--verify", f"refs/remotes/origin/{branch}")
    return remote.returncode == 0


def iter_worktrees(repo: RepoConfig) -> Iterable[str]:
    repo_root = repo.repo_root_path()
    result = cmd_capture(repo_root, "git", "worktree", "list", "--porcelain")
    if result.returncode != 0 or not result.stdout:
        return []

    branches: list[str] = []
    current_branch: Optional[str] = None

    for raw in result.stdout.splitlines():
        line = raw.strip()

        if line.startswith("worktree "):
            current_branch = None

        elif line.startswith("branch "):
            ref = line.split(" ", 1)[1].strip()
            if ref.startswith("refs/heads/"):
                current_branch = ref.split("/")[-1]
                branches.append(current_branch)

    return branches


# ===========================================================================
# worktrees
# ===========================================================================

def create_branch(repo: RepoConfig, branch: str) -> None:
    repo_root = repo.repo_root_path()

    res = cmd(repo_root, "git", "checkout", "-b", branch)
    if res.returncode != 0:
        raise GitCommandFailed(["git", "checkout", "-b", branch], res)

    res = cmd(repo_root, "git", "push", "-u", "origin", branch)
    if res.returncode != 0:
        raise GitCommandFailed(["git", "push", "-u", "origin", branch], res)


def add_worktree(repo: RepoConfig, branch: str) -> None:
    repo_root = repo.repo_root_path()

    res = cmd(repo_root, "git", "fetch", "--all")
    if res.returncode != 0:
        raise GitCommandFailed(["git", "fetch", "--all"], res)

    if not branch_exists(repo_root, branch):
        raise BranchDoesNotExist(branch)

    res = cmd(repo_root, "git", "checkout", "--detach")
    if res.returncode != 0:
        raise GitCommandFailed(["git", "checkout", "--detach"], res)

    res = cmd(
        repo_root,
        "git",
        "worktree",
        "add",
        str(repo.worktree_path_for_branch(branch)),
        branch,
    )
    if res.returncode != 0:
        raise GitCommandFailed(
            ["git", "worktree", "add", str(repo.worktree_path_for_branch(branch)), branch],
            res,
        )


def delete_branch(repo: RepoConfig, branch: str, *, delete_remote: bool = False) -> None:
    repo_root = repo.repo_root_path()

    local = cmd(repo_root, "git", "show-ref", "--verify", f"refs/heads/{branch}")
    remote = cmd(repo_root, "git", "show-ref", "--verify", f"refs/remotes/origin/{branch}")

    # No local branch and remote deletion not requested: behave as before
    if local.returncode != 0 and not delete_remote:
        raise BranchDoesNotExist(branch)

    # If a local branch exists, clean up worktree and local ref
    if local.returncode == 0:
        wt_path = repo.worktree_path_for_branch(branch)
        if wt_path.exists():
            res = cmd(repo_root, "git", "worktree", "remove", str(wt_path))
            if res.returncode != 0:
                raise GitCommandFailed(["git", "worktree", "remove", str(wt_path)], res)

        res = cmd(repo_root, "git", "branch", "-d", branch)
        if res.returncode != 0:
            raise GitCommandFailed(["git", "branch", "-d", branch], res)

    # Optionally delete the remote branch, even if there is no local one
    if delete_remote:
        if remote.returncode != 0:
            raise BranchDoesNotExist(branch)

        res = cmd(repo_root, "git", "push", "origin", "--delete", branch)
        if res.returncode != 0:
            raise GitCommandFailed(["git", "push", "origin", "--delete", branch], res)


# ===========================================================================
# status
# ===========================================================================

def _worktree_paths_by_branch(repo: RepoConfig) -> dict[str, str]:
    repo_root = repo.repo_root_path()
    result = cmd_capture(repo_root, "git", "worktree", "list", "--porcelain")
    if result.returncode != 0 or not result.stdout:
        return {}

    mapping: dict[str, str] = {}
    current_path: Optional[str] = None

    for raw in result.stdout.splitlines():
        line = raw.strip()
        if line.startswith("worktree "):
            current_path = line.split(" ", 1)[1].strip()
        elif line.startswith("branch ") and current_path:
            ref = line.split(" ", 1)[1].strip()
            if ref.startswith("refs/heads/"):
                mapping[ref.split("/")[-1]] = current_path

    return mapping


def list_branches_with_status(repo: RepoConfig) -> List[BranchStatus]:
    repo_root = repo.repo_root_path()

    current_branch = None
    res = cmd_capture(repo_root, "git", "rev-parse", "--abbrev-ref", "HEAD")
    if res.returncode == 0 and res.stdout and res.stdout.strip() != "HEAD":
        current_branch = res.stdout.strip()

    res = cmd_capture(
        repo_root,
        "git",
        "for-each-ref",
        "--format=%(refname:short)\t%(upstream:short)\t%(upstream:track)",
        "refs/heads",
    )
    if res.returncode != 0 or not res.stdout:
        return []

    statuses: dict[str, BranchStatus] = {}
    locals: set[str] = set()

    def parse_track(track: str) -> tuple[int, int]:
        ahead = behind = 0
        if "ahead" in track:
            ahead = int(track.split("ahead")[1].split()[0])
        if "behind" in track:
            behind = int(track.split("behind")[1].split()[0])
        return ahead, behind

    for line in res.stdout.splitlines():
        name, upstream, track = (line.split("\t") + ["", ""])[:3]
        locals.add(name)
        ahead, behind = parse_track(track)
        statuses[name] = BranchStatus(
            name=name,
            remote=upstream or None,
            has_local=True,
            ahead=ahead,
            behind=behind,
            is_current=(name == current_branch),
        )

    res = cmd_capture(repo_root, "git", "for-each-ref", "--format=%(refname:short)", "refs/remotes")
    if res.returncode == 0 and res.stdout:
        for ref in res.stdout.splitlines():
            if ref.endswith("/HEAD") or "/" not in ref:
                continue
            _, name = ref.split("/", 1)
            if name not in locals:
                statuses[name] = BranchStatus(
                    name=name,
                    remote=ref,
                    has_local=False,
                    ahead=0,
                    behind=0,
                    is_current=False,
                )

    return [statuses[k] for k in sorted(statuses)]


# ===========================================================================
# clone
# ===========================================================================

def clone_and_add_worktree(target: str) -> RepoConfig:
    url = build_clone_url(target, _config.globals.defaultProvider)

    repo_cfg = RepoConfig(
        full_name=target,
        url=url,
        lastBranch="",
        defaultBranch="",
    )

    repo_root = repo_cfg.repo_root_path()
    repo_root.parent.mkdir(parents=True, exist_ok=True)

    res = cmd(repo_root.parent, "git", "clone", url, str(repo_root))
    if res.returncode != 0:
        raise GitCommandFailed(["git", "clone", url], res)

    res = cmd(repo_root, "git", "checkout", "--detach")
    if res.returncode != 0:
        raise GitCommandFailed(["git", "checkout", "--detach"], res)

    head = cmd(repo_root, "git", "symbolic-ref", "refs/remotes/origin/HEAD")
    if head.returncode == 0 and head.stdout:
        default = head.stdout.strip().split("/")[-1]
    else:
        for c in ("main", "master"):
            if cmd(repo_root, "git", "rev-parse", "--verify", f"origin/{c}").returncode == 0:
                default = c
                break
        else:
            raise GitxError("Cannot determine default branch")

    add_worktree(repo_cfg, default)
    repo_cfg.defaultBranch = default

    return repo_cfg