"""Path logic for gitx workspaces."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..config import AppConfig
from . import WORKSPACE_SUFFIX_SEP


@dataclass(slots=True)
class RepoIdentifier:
    org: str
    name: str

    @classmethod
    def parse(cls, value: str) -> "RepoIdentifier":
        if "/" not in value:
            msg = "Repository must be in the form 'org/name'"
            raise ValueError(msg)
        org, name = value.split("/", 1)
        return cls(org=org, name=name)


def branch_to_suffix(branch: str) -> str:
    """Return the suffix used in workspace paths for the given branch name."""

    return branch.replace("/", WORKSPACE_SUFFIX_SEP)


def repo_root_path(repo: RepoIdentifier, cfg: AppConfig) -> Path:
    return cfg.workspaces.base_dir / repo.org / repo.name


def workspace_path(repo: RepoIdentifier, branch: str, cfg: AppConfig) -> Path:
    suffix = branch_to_suffix(branch)
    return cfg.workspaces.base_dir / repo.org / repo.name / f"{repo.name}{WORKSPACE_SUFFIX_SEP}{suffix}"
