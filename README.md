# gitx — git worktrees with superpowers

`gitx` is a tiny CLI that wraps **`git worktree`** to make multi‑branch workspaces trivial.

It is inspired by the "Workspaces" feature of GitLens Pro: instead of stashing half‑done changes or making junk commits just to switch context, each branch lives in its **own directory** (a dedicated worktree).

- No more random `git stash` before switching branch
- No more "WIP" commits just to avoid losing local changes
- Fast, repeatable context switches across many feature branches

All of this is built directly on top of **plain Git** and `git worktree`.

---

## Quick start

### Install (Linux / macOS)

```bash
curl -sfL https://gitx.parisius.dev | sh -
```

Then restart your shell (or ensure `$HOME/.local/bin` is on your `PATH`) and run:

```bash
gitx --help
```

### Install (Windows / PowerShell)

```powershell
irm https://gitx.parisius.dev | iex
```

Restart the terminal (or make sure `%USERPROFILE%\.local\bin` is on `PATH`) and run:

```powershell
gitx --help
```

### Minimal workflow example

```bash
# 1. Clone once and create a workspace for the default branch
gitx clone jasoc/gitx

# 2. Create a dedicated worktree for a feature branch
gitx branch add jasoc/gitx feature/my-work

# 3. Jump into the worktree for that branch (fish)
cd (gitx go jasoc/gitx -b feature/my-work)

# 4. Or open your editor directly on that branch
gitx code jasoc/gitx --branch feature/my-work

# 5. Next time you open your workspace, gitx restores the last-opened branch
```bash
cd (gitx go jasoc/gitx)  # jumps to feature/my-work
```

Each branch gets its own directory under your configured workspace base dir; your uncommitted changes stay where you left them.

---

## Command reference

```bash
# Workspaces based on git worktree
gitx clone jasoc/gitx
gitx go jasoc/gitx --branch develop
gitx code jasoc/gitx --branch develop

# Branch worktrees
gitx branch list jasoc/gitx
gitx branch add jasoc/gitx develop
gitx branch delete jasoc/gitx develop

# Configuration
gitx config show
gitx config get globals.editor
gitx config set globals.editor code
```

Notes:

- `clone` clones the repo once and creates a first worktree for the detected default branch (via `origin/HEAD`, `main`, `master`, …).
- `branch add` creates a new detached worktree for the given branch (creating and pushing the branch if it does not exist yet, with confirmation).
- `branch delete` removes the worktree and the local branch (and can optionally delete `origin/<branch>`).
- `go` ensures the worktree exists and prints the directory to `stdout` so you can use it with `cd (gitx go ...)`.
- `code` does the same as `go` but then launches your configured editor (`globals.editor`, default `code`).

---

## Configuration

`gitx` stores a small config file describing:

- `globals.baseDir` – where all workspaces live (default: `$HOME/sources/workspaces`)
- `globals.defaultProvider` – git provider used to build clone URLs (default: `github`)
- `globals.editor` – editor command for `gitx code` (default: `code`)
- `workspaces` – known workspaces, keyed by full repo name (e.g. `jasoc/gitx`)

Examples:

```bash
gitx config show

gitx config get globals.editor

gitx config set globals.baseDir "$HOME/sources/workspaces"
gitx config set globals.editor code
```

---

## Local development & local install

From the root of this repository:

### Run gitx via the local wrapper

```bash
./gitx clone jasoc/gitx
./gitx branch list jasoc/gitx
```

This uses Docker to spin up an isolated environment for the CLI.

### Build and install from source

```bash
make install
```

This builds the CLI wheel and installs it via `pipx`, so `gitx` is available globally for your user.

---

## License

See the `LICENSE` file in this repository for licensing details.
