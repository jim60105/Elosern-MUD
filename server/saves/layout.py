"""Save identities, on-disk layout, and manifest access (standard library only).

Shared by the live server (``server.saves.snapshot``) and the pre-start
restore tool (``server.saves.restore``), which runs before Django or Evennia
is initialised, so nothing here may import either.

A save has one half in each persistent volume, because hardlinks cannot
cross volumes::

    <saves_root>/<id>/evennia.db3          # the database volume
    <saves_root>/<id>/manifest.json
    <art_root>/.saves/<id>/...              # the art volume, mirrored tree
    <saves_root>/RESTORE_PENDING            # a save id awaiting application
    <saves_root>/RESTORE_RESULT.json        # the latest application outcome

A save is listed only when both halves and its manifest exist; the database
half (which holds the manifest) is published last and removed first.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

SAVE_ID_PATTERN = re.compile(r"^\d{8}T\d{6}-[0-9a-f]{6}$")

KIND_MANUAL = "manual"
KIND_AUTO_RESTORE = "auto_restore"
KIND_AUTO_INTERVENTION = "auto_intervention"
KINDS = (KIND_MANUAL, KIND_AUTO_RESTORE, KIND_AUTO_INTERVENTION)
AUTOMATIC_KINDS = (KIND_AUTO_RESTORE, KIND_AUTO_INTERVENTION)

DB_FILENAME = "evennia.db3"
MANIFEST_FILENAME = "manifest.json"
PENDING_FILENAME = "RESTORE_PENDING"
RESULT_FILENAME = "RESTORE_RESULT.json"
ART_SAVES_DIRNAME = ".saves"
PARTIAL_SUFFIX = ".partial"
#: Work directories of the pre-start tool, beside the live database and
#: inside the live art root. Snapshots and restores never mirror them.
STAGING_DIRNAME = ".restore-staging"
ASIDE_DIRNAME = ".restore-aside"
ART_RESERVED_NAMES = frozenset({ART_SAVES_DIRNAME, STAGING_DIRNAME, ASIDE_DIRNAME})

MANIFEST_VERSION = 1
LABEL_MAX_LENGTH = 80


class SaveError(Exception):
    """A save operation refusal carrying a stable snake_case ``code``."""

    code = "save_failed"


class InvalidSaveId(SaveError):
    code = "invalid_save_id"


class SaveNotFound(SaveError):
    code = "save_not_found"


class SaveIncompatible(SaveError):
    code = "save_incompatible"


class SaveInProgress(SaveError):
    code = "save_in_progress"


class SaveDeleteForbidden(SaveError):
    code = "save_delete_forbidden"


class ManifestError(SaveError):
    """A manifest that is missing, unreadable, or structurally invalid."""

    code = "save_not_found"


def validate_save_id(value: Any) -> str:
    """Return ``value`` when it is a well-formed save id; raise otherwise.

    Every path built from an id goes through this first, so a malformed id
    never reaches the filesystem.
    """
    if not isinstance(value, str) or not SAVE_ID_PATTERN.fullmatch(value):
        raise InvalidSaveId(str(value)[:64])
    return value


def new_save_id(now: datetime | None = None) -> str:
    """``YYYYMMDDTHHMMSS-<6 hex>`` in UTC; ids sort chronologically."""
    moment = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return f"{moment:%Y%m%dT%H%M%S}-{secrets.token_hex(3)}"


def normalize_label(value: Any) -> str:
    """A single-line label of at most :data:`LABEL_MAX_LENGTH` characters."""
    text = value if isinstance(value, str) else ""
    text = "".join(" " if ch.isspace() else ch for ch in text if ch.isprintable() or ch.isspace())
    return " ".join(text.split())[:LABEL_MAX_LENGTH]


@dataclass(frozen=True)
class SaveLayout:
    """Where the live world and its saves live."""

    db_file: Path
    saves_root: Path
    art_root: Path

    @classmethod
    def for_project(cls, project_root: Path) -> "SaveLayout":
        root = Path(project_root)
        return cls(
            db_file=root / "server" / "db" / DB_FILENAME,
            saves_root=root / "server" / "db" / "saves",
            art_root=root / "server" / ".art",
        )

    @property
    def art_saves_root(self) -> Path:
        return self.art_root / ART_SAVES_DIRNAME

    @property
    def pending_marker(self) -> Path:
        return self.saves_root / PENDING_FILENAME

    @property
    def result_file(self) -> Path:
        return self.saves_root / RESULT_FILENAME

    def db_dir(self, save_id: str) -> Path:
        return self.saves_root / validate_save_id(save_id)

    def art_dir(self, save_id: str) -> Path:
        return self.art_saves_root / validate_save_id(save_id)

    def db_partial(self, save_id: str) -> Path:
        return self.saves_root / (validate_save_id(save_id) + PARTIAL_SUFFIX)

    def art_partial(self, save_id: str) -> Path:
        return self.art_saves_root / (validate_save_id(save_id) + PARTIAL_SUFFIX)

    def manifest_path(self, save_id: str) -> Path:
        return self.db_dir(save_id) / MANIFEST_FILENAME

    def saved_db(self, save_id: str) -> Path:
        return self.db_dir(save_id) / DB_FILENAME


def read_manifest(layout: SaveLayout, save_id: str) -> dict[str, Any]:
    """Parse and structurally check one save's manifest."""
    path = layout.manifest_path(save_id)
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise ManifestError(f"{save_id}: manifest missing") from error
    except OSError as error:
        raise ManifestError(f"{save_id}: manifest unreadable") from error
    try:
        data = json.loads(raw)
    except ValueError as error:
        raise ManifestError(f"{save_id}: manifest is not JSON") from error
    if not isinstance(data, dict) or data.get("id") != save_id:
        raise ManifestError(f"{save_id}: manifest identity mismatch")
    if data.get("kind") not in KINDS:
        raise ManifestError(f"{save_id}: manifest kind invalid")
    files = data.get("files")
    if not isinstance(files, dict) or not isinstance(files.get("art"), list):
        raise ManifestError(f"{save_id}: manifest file inventory invalid")
    return data


def is_complete(layout: SaveLayout, save_id: str) -> bool:
    """True when both halves exist and the manifest is valid."""
    if not layout.saved_db(save_id).is_file() or not layout.art_dir(save_id).is_dir():
        return False
    try:
        read_manifest(layout, save_id)
    except ManifestError:
        return False
    return True


def iter_complete_ids(layout: SaveLayout) -> Iterator[str]:
    """Every complete save id, oldest first."""
    try:
        names = sorted(os.listdir(layout.saves_root))
    except FileNotFoundError:
        return
    for name in names:
        if SAVE_ID_PATTERN.fullmatch(name) and is_complete(layout, name):
            yield name


def read_pending(layout: SaveLayout) -> str | None:
    """The save id named by ``RESTORE_PENDING`` (validated), or ``None``."""
    try:
        text = layout.pending_marker.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    try:
        return validate_save_id(text)
    except InvalidSaveId:
        return None


def atomic_write_text(path: Path, text: str) -> None:
    """Write ``text`` beside ``path`` and atomically replace it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:  # observability: ignore R2: best-effort temp cleanup; the original error propagates
            pass
        raise


def atomic_write_json(path: Path, data: Any) -> None:
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def read_json(path: Path) -> Any:
    """Parse a JSON file, or ``None`` when it is absent or invalid."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # observability: ignore R2: absent or corrupt status files read as no data
        return None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
