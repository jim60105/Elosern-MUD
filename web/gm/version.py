"""The game version, read from the project's single version source.

``pyproject.toml`` ``[project].version`` is the only declared version; the
project is not an installed distribution (``tool.uv.package = false``), so
``importlib.metadata`` cannot answer. The container image ships the file at
the game root.
"""

from __future__ import annotations

import functools
import tomllib
from pathlib import Path

from django.conf import settings


@functools.lru_cache(maxsize=1)
def game_version() -> str:
    """Return ``[project].version``; raise when the source is unreadable."""
    path = Path(settings.GAME_DIR) / "pyproject.toml"
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    version = data["project"]["version"]
    if not isinstance(version, str) or not version:
        raise ValueError("pyproject.toml [project].version is not a non-empty string")
    return version
