from __future__ import annotations

import json
import subprocess
import time
from importlib import metadata as importlib_metadata
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import typer
from rich.console import Console

from ..config import _config

PACKAGE_NAME = "gitx-cli"
PYPI_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"
CHECK_INTERVAL_SECONDS = 60 * 60 * 24  # 24 hours


def _get_current_version() -> Optional[str]:
    try:
        return importlib_metadata.version(PACKAGE_NAME)
    except importlib_metadata.PackageNotFoundError:
        return None
    except Exception:
        return None


def _get_latest_version(timeout: float = 2.0) -> Optional[str]:
    try:
        with urlopen(PYPI_URL, timeout=timeout) as response:  # type: ignore[call-arg]
            if response.status != 200:
                return None
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError, OSError):
        return None

    info = payload.get("info") if isinstance(payload, dict) else None
    if not isinstance(info, dict):
        return None
    latest = info.get("version")
    if not isinstance(latest, str):
        return None
    return latest


def _should_check_for_update(now: float) -> bool:
    if not getattr(_config.globals, "autoUpdateCheck", True):
        return False

    last = getattr(_config.globals, "lastUpdateCheck", 0.0) or 0.0
    if last <= 0.0:
        return True

    return (now - last) >= CHECK_INTERVAL_SECONDS


def _record_check_time(timestamp: float) -> None:
    try:
        _config.globals.lastUpdateCheck = float(timestamp)
        _config.save()
    except Exception:
        # Never fail CLI execution because config persistence failed.
        pass


def _run_pipx_upgrade(console: Console, target_version: str) -> None:
    try:
        result = subprocess.run(
            ["pipx", "upgrade", PACKAGE_NAME],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        console.print(
            "[red]pipx is not available in PATH.[/] "
            "Please update manually with: [bold]pipx upgrade gitx-cli[/]",
        )
        return
    except Exception as exc:  # pragma: no cover - very defensive
        console.print(f"[red]Failed to run pipx upgrade: {exc}[/]")
        return

    if result.returncode != 0:
        console.print("[red]gitx-cli upgrade via pipx failed.[/]")
        if result.stderr:
            console.print(result.stderr.strip())
        return

    console.print(f"[green]gitx-cli successfully upgraded to {target_version}.[/]")


def maybe_check_for_update(console: Console) -> None:
    """Check PyPI for a newer gitx-cli and offer to update via pipx.

    This runs at most once per CHECK_INTERVAL_SECONDS, is best-effort,
    and will never abort the main CLI command.
    """

    now = time.time()

    if not _should_check_for_update(now):
        return

    # Record check time early so we do not retry aggressively if
    # network or PyPI are temporarily unavailable.
    _record_check_time(now)

    current = _get_current_version()
    latest = _get_latest_version()

    if not current or not latest or latest == current:
        return

    console.print(
        f"[yellow]A new gitx-cli version is available: {current} -> {latest}[/]"
    )

    if not typer.confirm("Upgrade gitx-cli using pipx now?", default=False):
        return

    _run_pipx_upgrade(console, latest)
