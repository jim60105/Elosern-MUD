"""Read-only YAML source viewer (gm-portal-s4-world-data §4).

The allowlist is rebuilt on every request from three directories: the
rulebook YAML (``world/rules/rulebook/*.yaml``), its ``commerce/`` slices and
the prompt library (``prompts/*.yaml``). A source is named by an opaque,
root-qualified name (``rulebook/combat.yaml``, ``rulebook/commerce/altoria.yaml``,
``prompts/art.yaml``) so equal basenames in different roots never collide.

A request name is only ever looked up in that allowlist; it is never joined
onto a filesystem path. A candidate whose resolved path leaves its approved
root (an escaping symlink) is excluded from the allowlist and re-checked at
read time. What this returns is the file on disk, which is not necessarily
what the server loaded: rulebooks are applied by restart, prompts by the
explicit reload action.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from web.gm.readers.errors import SourceNotFound

#: The largest file the viewer returns (rulebooks and prompts are far smaller).
MAX_SOURCE_BYTES = 1_000_000


@dataclass(frozen=True)
class SourceRoot:
    """One approved directory and the name prefix of its files."""

    prefix: str
    group: str
    directory: Path
    reloadable: bool = False


def game_dir() -> Path:
    from django.conf import settings

    return Path(settings.GAME_DIR)


def prompt_dir() -> Path:
    """The prompt library root the loader reads (``settings.PROMPT_ROOT``)."""
    from django.conf import settings

    configured = getattr(settings, "PROMPT_ROOT", None)
    return Path(configured) if configured else game_dir() / "prompts"


def roots() -> tuple[SourceRoot, ...]:
    rulebook = game_dir() / "world" / "rules" / "rulebook"
    return (
        SourceRoot("rulebook", "rulebook", rulebook),
        SourceRoot("rulebook/commerce", "commerce", rulebook / "commerce"),
        SourceRoot("prompts", "prompts", prompt_dir(), reloadable=True),
    )


def _contained(path: Path, directory: Path) -> bool:
    try:
        resolved = path.resolve(strict=True)
        return resolved.is_file() and resolved.parent == directory.resolve(strict=True)
    except (OSError, ValueError, RuntimeError):  # observability: ignore R2: an unreadable or looping candidate is simply not allowlisted
        return False


def _display_path(path: Path) -> str:
    """The repository-relative path when inside the game directory."""
    try:
        return path.relative_to(game_dir()).as_posix()
    except ValueError:  # observability: ignore R2: a prompt root outside the repository shows its absolute path
        return path.as_posix()


def allowlist() -> dict[str, tuple[SourceRoot, Path]]:
    """``name -> (root, path)`` for every viewable file, built now."""
    allowed: dict[str, tuple[SourceRoot, Path]] = {}
    for root in roots():
        if not root.directory.is_dir():
            continue
        for path in sorted(root.directory.glob("*.yaml")):
            if _contained(path, root.directory):
                allowed[f"{root.prefix}/{path.name}"] = (root, path)
    return allowed


def list_sources() -> dict[str, Any]:
    items = []
    for name, (root, path) in sorted(allowlist().items()):
        items.append(
            {
                "name": name,
                "group": root.group,
                "source_path": _display_path(path),
                "size_bytes": path.stat().st_size,
                "reloadable": root.reloadable,
            }
        )
    return {"items": items}


def read_source(name: str) -> dict[str, Any]:
    """One allowlisted file's text, or ``source_not_found``."""
    found = allowlist().get(str(name))
    if found is None:
        raise SourceNotFound()
    root, path = found
    if not _contained(path, root.directory):
        raise SourceNotFound()
    try:
        raw = path.read_bytes()
        if len(raw) > MAX_SOURCE_BYTES:
            raise SourceNotFound()
        text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise SourceNotFound() from error
    return {
        "name": str(name),
        "group": root.group,
        "source_path": _display_path(path),
        "size_bytes": len(raw),
        "line_count": len(text.splitlines()),
        "reloadable": root.reloadable,
        "text": text,
    }


__all__ = ["MAX_SOURCE_BYTES", "allowlist", "list_sources", "read_source", "roots"]
