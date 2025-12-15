import subprocess
import sys
from pathlib import Path
from rich.console import Console


console = Console()


def cmd(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*args],
        cwd=str(path),
        stdin=sys.stdin,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )


def cmd_capture(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*args],
        cwd=str(path),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
