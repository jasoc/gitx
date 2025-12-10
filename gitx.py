#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path

BASE_DIR = Path.home() / "sources" / "worktrees"

def run(cmd, cwd=None):
    print(">>", " ".join(cmd))
    subprocess.check_call(cmd, cwd=cwd)

def parse_repo_path(repo_url: str) -> Path:
    # estrae org/name da URL tipo:
    # https://github.com/acme/bla.git
    # git@github.com:acme/bla.git
    cleaned = repo_url.replace("git@", "https://")
    cleaned = cleaned.replace(":", "/")
    cleaned = cleaned.rstrip(".git")

    if "github.com" in cleaned:
        parts = cleaned.split("github.com/")[1].split("/")
        if len(parts) >= 2:
            return Path(parts[0]) / parts[1]

    # fallback minimale
    name = repo_url.rstrip("/").split("/")[-1].rstrip(".git")
    return Path("unknown") / name

def wt_clone(repo_url):
    repo_rel = parse_repo_path(repo_url)
    repo_path = BASE_DIR / repo_rel

    # If the directory already exists, ask confirmation
    if repo_path.exists():
        print(f"La directory '{repo_path}' esiste già.")
        ans = input("Vuoi sovrascriverla? (y/n) ").strip().lower()
        if ans != "y":
            print("Abortito.")
            sys.exit(1)
        else:
            print(f"Rimuovo '{repo_path}' ...")
            import shutil
            shutil.rmtree(repo_path)

    os.makedirs(repo_path.parent, exist_ok=True)

    print(f"Cloning into {repo_path} ...")
    run(["git", "clone", repo_url, str(repo_path)])

    # Step 1: detach so 'main' becomes free
    print("Detaching main worktree from branch...")
    run(["git", "checkout", "--detach"], cwd=str(repo_path))

    # Step 2: create main worktree
    print("Creating main worktree...")
    main_worktree = Path(f"{repo_path}-main")
    run(["git", "worktree", "add", str(main_worktree), "main"], cwd=str(repo_path))

    print("Done.")

def worktree_path(repo_rel: str, branch: str) -> Path:
    # branch con slash → sostituire per evitare path strani
    safe_branch = branch.replace("/", "-")
    repo_path = BASE_DIR / repo_rel
    return Path(f"{repo_path}-{safe_branch}")

def wt_add(repo_rel, branch):
    repo_path = BASE_DIR / repo_rel
    wt_path = worktree_path(repo_rel, branch)

    print(f"Creating worktree at {wt_path} ...")
    run(["git", "fetch"], cwd=str(repo_path))
    run(["git", "worktree", "add", str(wt_path), branch], cwd=str(repo_path))

    print("Done.")

def wt_code(repo_rel, branch):
    wt_path = worktree_path(repo_rel, branch)

    if not wt_path.exists():
        print("Worktree does not exist, creating it...")
        wt_add(repo_rel, branch)

    print(f"Entering {wt_path}")
    run(["code", f"{wt_path}"], cwd=str(wt_path))
    print("\nTo enter manually:")
    print(f"cd {wt_path}\n")

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  wt clone <repo-url>")
        print("  wt add <reponame> <branch>")
        print("  wt go <reponame> <branch>")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "clone" and len(sys.argv) == 3:
        wt_clone(sys.argv[2])
    elif cmd == "add" and len(sys.argv) == 4:
        wt_add(sys.argv[2], sys.argv[3])
    elif cmd == "code" and len(sys.argv) == 4:
        wt_code(sys.argv[2], sys.argv[3])
    else:
        print("Invalid command or missing args.")
        sys.exit(1)

if __name__ == "__main__":
    main()