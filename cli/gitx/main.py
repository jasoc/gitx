"""gitx Typer entrypoint.

This module exposes the Typer app as `app` for use in console scripts.
"""

from __future__ import annotations

from .cli import app

__all__ = ["app"]
