"""World snapshots: create, list, delete, download, and request restoration.

Runs inside the live server. A save is the SQLite world database plus the
generated art store (``server.saves.layout`` describes where each half
lives). The operation sits below game rules: it copies whole stores and never
writes a game field; restoration only stages a request, and the stdlib
pre-start tool (``server.saves.restore``) applies it before the next start.

Consistency: one snapshot at a time (``_snapshot_lock``); the art store is
held still through ``world.art.publication.paused`` across the database
backup and the art mirror, so no art file is written mid-snapshot and the
saved database and art agree. The database copy uses SQLite's online backup
API (``pages=-1``: one pass under a shared lock, which briefly delays writer
commits), never a byte copy of the live file. Art files are hardlinked into
the save (copy fallback), which is safe because every live art writer
replaces files atomically and never writes in place.

Retention: each automatic kind keeps at most ``GM_AUTOSAVE_KEEP`` saves after
a successful creation, oldest first; manual saves are never pruned. While a
restore target is pinned (in memory during a request, then by the persisted
``RESTORE_PENDING`` marker) pruning of the target's kind is deferred; the
startup step :func:`startup_report` completes it after application.
"""

from __future__ import annotations

import base64
import os
import pickle
import shutil
import sqlite3
import tarfile
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from server.saves import inventory
from server.saves.layout import (
    AUTOMATIC_KINDS,
    DB_FILENAME,
    KIND_AUTO_RESTORE,
    KIND_MANUAL,
    KINDS,
    MANIFEST_FILENAME,
    MANIFEST_VERSION,
    PARTIAL_SUFFIX,
    ART_RESERVED_NAMES,
    ManifestError,
    SaveDeleteForbidden,
    SaveError,
    SaveInProgress,
    SaveIncompatible,
    SaveLayout,
    SaveNotFound,
    atomic_write_json,
    atomic_write_text,
    is_complete,
    iter_complete_ids,
    new_save_id,
    normalize_label,
    read_json,
    read_manifest,
    read_pending,
    validate_save_id,
)
from world.observability import log_error, log_info, log_warn

_snapshot_lock = threading.Lock()
_restore_lock = threading.Lock()
#: The save id a running restore request has selected (``None`` otherwise).
_pinned_target: str | None = None

_CHUNK_BYTES = 64 * 1024
_TAR_BLOCK = tarfile.BLOCKSIZE
#: Seconds a backup connection waits on a busy source before failing.
_BACKUP_BUSY_TIMEOUT = 30.0
#: Seconds between the restore response and Evennia's shutdown.
SHUTDOWN_DELAY_SECONDS = 2.0


# --- metadata -----------------------------------------------------------------


@dataclass(frozen=True)
class SaveInfo:
    """One complete save as the portal lists it."""

    id: str
    label: str
    kind: str
    created_at: str
    clock: dict[str, Any] | None
    players: list[dict[str, Any]]
    migrations: dict[str, str]
    file_count: int
    size_bytes: int
    pending: bool = False

    @classmethod
    def from_manifest(cls, manifest: dict[str, Any], *, pending: bool = False) -> "SaveInfo":
        return cls(
            id=str(manifest["id"]),
            label=str(manifest.get("label") or ""),
            kind=str(manifest["kind"]),
            created_at=str(manifest.get("created_at") or ""),
            clock=manifest.get("clock") if isinstance(manifest.get("clock"), dict) else None,
            players=[p for p in manifest.get("players") or [] if isinstance(p, dict)],
            migrations=dict(manifest.get("migrations") or {}),
            file_count=int(manifest.get("file_count") or 0),
            size_bytes=int(manifest.get("size_bytes") or 0),
            pending=pending,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "created_at": self.created_at,
            "clock": self.clock,
            "players": self.players,
            "migrations": self.migrations,
            "file_count": self.file_count,
            "size_bytes": self.size_bytes,
            "deletable": self.kind == KIND_MANUAL,
            "pending": self.pending,
        }


def default_layout() -> SaveLayout:
    """The live layout from settings (read per call, never at import)."""
    from django.conf import settings

    return SaveLayout(
        db_file=Path(settings.DATABASES["default"]["NAME"]),
        saves_root=Path(settings.GM_SAVES_ROOT),
        art_root=Path(settings.ART_STORE_ROOT),
    )


def project_root() -> Path:
    from django.conf import settings

    return Path(settings.GAME_DIR)


def autosave_keep() -> int:
    from django.conf import settings

    return int(settings.GM_AUTOSAVE_KEEP)


def world_metadata() -> dict[str, Any]:
    """Informational player summary; clock provenance belongs to the copy."""
    from typeclasses.characters import PlayerCharacter
    players = []
    for character in PlayerCharacter.objects.all().order_by("id"):
        location = character.location
        players.append({
            "name": str(character.key),
            "location": str(location.key) if location is not None else None,
        })
    return {"players": players}


def snapshot_clock(db_path: Path) -> dict[str, Any] | None:
    """Read the saved Script Attribute, never a later live clock.

    This is a trusted, server-created database copy, not uploaded pickle data.
    Missing/corrupt clock storage cannot establish a console baseline.
    """
    from world.rules.clock import WorldDateTime

    connection = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)
    try:
        row = connection.execute(
            "SELECT a.db_value FROM scripts_scriptdb s "
            "JOIN scripts_scriptdb_db_attributes sa ON sa.scriptdb_id = s.id "
            "JOIN typeclasses_attribute a ON a.id = sa.attribute_id "
            "WHERE s.db_key = ? AND a.db_key = ? AND a.db_category IS NULL "
            "ORDER BY s.id LIMIT 1",
            ("world_clock", "tick"),
        ).fetchone()
        if row is None:
            return None
        tick = pickle.loads(base64.b64decode(row[0], validate=True))
        if type(tick) is not int or tick < 0:
            return None
        calendar = WorldDateTime.from_tick(tick)
        return {
            "tick": tick,
            "year": calendar.year,
            "season": calendar.season_name,
            "day": calendar.day_in_season,
            "hour": calendar.hour,
            "minute": calendar.minute,
        }
    except Exception as error:
        log_warn("save_clock_unreadable", context={"database": str(db_path)}, exc=error)
        return None
    finally:
        connection.close()


# --- snapshot -----------------------------------------------------------------


def _backup_database(source: Path, target: Path) -> None:
    """Consistent copy of ``source`` through SQLite's online backup API."""
    target.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(f"{source.resolve().as_uri()}?mode=ro", uri=True, timeout=_BACKUP_BUSY_TIMEOUT)
    try:
        dst = sqlite3.connect(target)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def is_transient_art_file(name: str) -> bool:
    """A writer's temporary file (``.<name>.<random>.tmp``), never saved."""
    return name.startswith(".") and name.endswith(".tmp")


def _mirror_art(art_root: Path, target: Path) -> list[dict[str, Any]]:
    """Hardlink every live art file into ``target``; copy when linking fails.

    Skips the reserved save/restore directories, symlinks, and writers'
    temporary files. A file that vanishes mid-walk is skipped. Returns the
    saved file inventory (relative path and size).
    """
    target.mkdir(parents=True, exist_ok=True)
    files: list[dict[str, Any]] = []
    if not art_root.is_dir():
        return files
    for directory, subdirs, names in os.walk(art_root):
        here = Path(directory)
        relative_dir = here.relative_to(art_root)
        if relative_dir == Path("."):
            subdirs[:] = [name for name in subdirs if name not in ART_RESERVED_NAMES]
        subdirs[:] = sorted(name for name in subdirs if not (here / name).is_symlink())
        for name in sorted(names):
            source = here / name
            if is_transient_art_file(name) or source.is_symlink() or not source.is_file():
                continue
            relative = (relative_dir / name).as_posix()
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                _link_or_copy(source, destination)
                size = destination.stat().st_size
            except FileNotFoundError:  # observability: ignore R2: a file removed mid-walk was unreferenced; it is not part of the save
                continue
            files.append({"path": relative, "size": size})
    return files


def _link_or_copy(source: Path, destination: Path) -> None:
    try:
        os.link(source, destination, follow_symlinks=False)
    except FileNotFoundError:
        raise
    except OSError:  # observability: ignore R2: a failed link falls back to a copy; a failed copy propagates
        shutil.copy2(source, destination, follow_symlinks=False)


def _remove_tree(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def _publish(layout: SaveLayout, save_id: str) -> None:
    """Rename both partial halves; the database half (with the manifest) last."""
    art_final = layout.art_dir(save_id)
    os.rename(layout.art_partial(save_id), art_final)
    try:
        os.rename(layout.db_partial(save_id), layout.db_dir(save_id))
    except BaseException:
        _remove_tree(art_final)
        raise


def _deferred_kinds(layout: SaveLayout) -> set[str]:
    """Automatic kinds whose pruning waits for a pinned restore target."""
    kinds: set[str] = set()
    for target in (_pinned_target, read_pending(layout)):
        if target is None:
            continue
        try:
            kinds.add(read_manifest(layout, target)["kind"])
        except ManifestError:  # observability: ignore R2: a vanished target pins nothing
            continue
    return kinds


def create_snapshot(
    kind: str,
    label: str,
    *,
    layout: SaveLayout | None = None,
    metadata: Callable[[], dict[str, Any]] | None = None,
    clock_reader: Callable[[Path], dict[str, Any] | None] | None = None,
) -> SaveInfo:
    """Create one complete save of the live world and return its info."""
    if kind not in KINDS:
        raise ValueError(f"unknown save kind {kind!r}")
    layout = layout or default_layout()
    if not _snapshot_lock.acquire(blocking=False):
        raise SaveInProgress("a snapshot is already running")
    try:
        if kind != KIND_AUTO_RESTORE and read_pending(layout) is not None:
            # A restore is staged and the server is shutting down: a new save
            # here would be lost to the restore.
            raise SaveInProgress("a restore is pending")
        info = _create_locked(
            kind, normalize_label(label), layout, metadata or world_metadata,
            clock_reader or snapshot_clock,
        )
    finally:
        _snapshot_lock.release()
    if kind in AUTOMATIC_KINDS and kind not in _deferred_kinds(layout):
        _prune_kind(layout, kind)
    return info


def _create_locked(
    kind: str,
    label: str,
    layout: SaveLayout,
    metadata: Callable[[], dict[str, Any]],
    clock_reader: Callable[[Path], dict[str, Any] | None] = snapshot_clock,
) -> SaveInfo:
    from world.art import publication

    moment = datetime.now(timezone.utc)
    save_id = new_save_id(moment)
    while (layout.saves_root / save_id).exists() or layout.db_partial(save_id).exists():
        save_id = new_save_id(moment)
    db_partial = layout.db_partial(save_id)
    art_partial = layout.art_partial(save_id)
    # Microseconds order saves created within the same second (ids only
    # carry whole seconds plus a random suffix).
    created_at = moment.isoformat(timespec="microseconds")
    try:
        layout.saves_root.mkdir(parents=True, exist_ok=True)
        layout.art_saves_root.mkdir(parents=True, exist_ok=True)
        db_partial.mkdir()
        with publication.paused():
            _backup_database(layout.db_file, db_partial / DB_FILENAME)
            art_files = _mirror_art(layout.art_root, art_partial)
        rows = inventory.applied_migrations(db_partial / DB_FILENAME)
        world = metadata()
        db_size = (db_partial / DB_FILENAME).stat().st_size
        art_size = sum(entry["size"] for entry in art_files)
        manifest = {
            "version": MANIFEST_VERSION,
            "id": save_id,
            "label": label,
            "kind": kind,
            "created_at": created_at,
            "clock": clock_reader(db_partial / DB_FILENAME),
            "players": world.get("players") or [],
            "migrations": inventory.latest_per_app(rows),
            "file_count": len(art_files) + 1,
            "size_bytes": db_size + art_size,
            "files": {"db": {"path": DB_FILENAME, "size": db_size}, "art": art_files},
        }
        atomic_write_json(db_partial / MANIFEST_FILENAME, manifest)
        _publish(layout, save_id)
    except BaseException as error:
        for path in (db_partial, art_partial):
            try:
                _remove_tree(path)
            except OSError as cleanup_error:
                log_warn("save_cleanup_failed", context={"save": save_id, "path": str(path)}, exc=cleanup_error)
        log_error("save_failed", context={"save": save_id, "kind": kind}, exc=error)
        raise
    info = SaveInfo.from_manifest(manifest)
    log_info(
        "save_created",
        context={
            "save": save_id,
            "kind": kind,
            "file_count": info.file_count,
            "size_bytes": info.size_bytes,
        },
    )
    return info


# --- listing, deletion, retention ---------------------------------------------


def _complete_manifests(layout: SaveLayout) -> list[dict[str, Any]]:
    """Manifests of every complete save, oldest first (creation time, then id)."""
    manifests = []
    for save_id in iter_complete_ids(layout):
        try:
            manifests.append(read_manifest(layout, save_id))
        except ManifestError:  # observability: ignore R2: a save removed between listing and reading is simply absent
            continue
    manifests.sort(key=lambda manifest: (str(manifest.get("created_at") or ""), manifest["id"]))
    return manifests


def list_saves(*, layout: SaveLayout | None = None) -> list[SaveInfo]:
    """Every complete save, newest first."""
    layout = layout or default_layout()
    pending = read_pending(layout)
    saves = [
        SaveInfo.from_manifest(manifest, pending=manifest["id"] == pending)
        for manifest in _complete_manifests(layout)
    ]
    saves.reverse()
    return saves


def get_save(save_id: str, *, layout: SaveLayout | None = None) -> SaveInfo:
    layout = layout or default_layout()
    validate_save_id(save_id)
    if not is_complete(layout, save_id):
        raise SaveNotFound(save_id)
    return SaveInfo.from_manifest(read_manifest(layout, save_id))


def _remove_save(layout: SaveLayout, save_id: str) -> None:
    """Delete both halves; the database half first so it is never listed half-gone."""
    _remove_tree(layout.db_dir(save_id))
    _remove_tree(layout.art_dir(save_id))


def delete_save(save_id: str, *, layout: SaveLayout | None = None) -> SaveInfo:
    """Delete one manual save (automatic saves are refused)."""
    layout = layout or default_layout()
    info = get_save(save_id, layout=layout)
    if info.kind != KIND_MANUAL:
        raise SaveDeleteForbidden(save_id)
    if read_pending(layout) == save_id or _pinned_target == save_id or _restore_lock.locked():
        # A restore request may be about to pin this very save.
        raise SaveInProgress("a restore request is running or pending")
    _remove_save(layout, save_id)
    log_info("save_deleted", context={"save": save_id, "kind": info.kind, "reason": "manual"})
    return info


def _prune_kind(layout: SaveLayout, kind: str) -> list[str]:
    """Delete the oldest saves of one automatic kind beyond the limit."""
    keep = autosave_keep()
    protected = {read_pending(layout), _pinned_target}
    ids = [
        manifest["id"]
        for manifest in _complete_manifests(layout)
        if manifest["id"] not in protected and manifest["kind"] == kind
    ]
    removed = []
    for save_id in ids[: max(0, len(ids) - keep)]:
        try:
            _remove_save(layout, save_id)
        except OSError as error:
            log_warn("save_retention_failed", context={"save": save_id, "kind": kind}, exc=error)
            continue
        removed.append(save_id)
        log_info("save_deleted", context={"save": save_id, "kind": kind, "reason": "retention"})
    return removed


def apply_retention(*, layout: SaveLayout | None = None) -> list[str]:
    """Prune every automatic kind whose pruning is not deferred."""
    layout = layout or default_layout()
    deferred = _deferred_kinds(layout)
    removed: list[str] = []
    for kind in AUTOMATIC_KINDS:
        if kind not in deferred:
            removed += _prune_kind(layout, kind)
    return removed


# --- restore request ------------------------------------------------------------


def check_compatible(save_id: str, *, layout: SaveLayout, root: Path | None = None) -> None:
    """Refuse a save holding a migration the current code does not ship."""
    rows = inventory.applied_migrations(layout.saved_db(save_id))
    unknown = inventory.unknown_migrations(rows, inventory.known_migrations(root or project_root()))
    if unknown:
        raise SaveIncompatible(", ".join(unknown[:5]))


def schedule_evennia_shutdown() -> None:
    """Shut the server down through Evennia's path after the response is sent."""
    import evennia
    from twisted.internet import reactor

    def _shutdown() -> None:
        evennia.SESSION_HANDLER.portal_shutdown()

    reactor.callFromThread(reactor.callLater, SHUTDOWN_DELAY_SECONDS, _shutdown)


def request_restore(
    save_id: str,
    *,
    layout: SaveLayout | None = None,
    schedule_shutdown: Callable[[], None] | None = None,
    metadata: Callable[[], dict[str, Any]] | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Save the current world, stage ``save_id`` for the next start, shut down."""
    global _pinned_target
    layout = layout or default_layout()
    validate_save_id(save_id)
    if not _restore_lock.acquire(blocking=False):
        raise SaveInProgress("a restore request is already running")
    try:
        if read_pending(layout) is not None:
            raise SaveInProgress("a restore is already pending")
        target = get_save(save_id, layout=layout)
        check_compatible(save_id, layout=layout, root=root)
        _pinned_target = save_id
        try:
            pre_save = create_snapshot(
                KIND_AUTO_RESTORE,
                f"讀取「{target.label or save_id}」前",
                layout=layout,
                metadata=metadata,
            )
            atomic_write_text(layout.pending_marker, save_id + "\n")
        except BaseException:
            _pinned_target = None
            apply_retention(layout=layout)
            raise
        _pinned_target = None
        try:
            (schedule_shutdown or schedule_evennia_shutdown)()
        except BaseException as error:
            # Never leave a staged restore behind a server that keeps running:
            # the next unrelated restart would apply it unannounced.
            layout.pending_marker.unlink(missing_ok=True)
            log_error("save_failed", context={"save": save_id, "kind": target.kind, "stage": "shutdown"}, exc=error)
            apply_retention(layout=layout)
            raise
        log_info(
            "save_restore_requested",
            context={"save": save_id, "kind": target.kind, "pre_save": pre_save.id},
        )
        return {"save": save_id, "pre_restore_save": pre_save.id, "shutdown": True}
    finally:
        _restore_lock.release()


# --- restore results --------------------------------------------------------------


def latest_restore_result(*, layout: SaveLayout | None = None) -> dict[str, Any] | None:
    layout = layout or default_layout()
    data = read_json(layout.result_file)
    if not isinstance(data, dict) or data.get("outcome") not in {"restored", "failed"}:
        return None
    return {
        "save": data.get("save"),
        "kind": data.get("kind"),
        "label": data.get("label"),
        "outcome": data.get("outcome"),
        "reason": data.get("reason"),
        "finished_at": data.get("finished_at"),
    }


def pending_restore(*, layout: SaveLayout | None = None) -> str | None:
    return read_pending(layout or default_layout())


def startup_report(*, layout: SaveLayout | None = None) -> None:
    """Startup step: translate the restore result once, then finish retention."""
    layout = layout or default_layout()
    data = read_json(layout.result_file)
    if isinstance(data, dict) and not data.get("reported"):
        context = {"save": data.get("save"), "kind": data.get("kind")}
        if data.get("outcome") == "restored":
            log_info("save_restored", context=context)
        else:
            # The pre-start tool already rolled back; the server runs on the
            # original world, so this is a warning with the recorded reason.
            log_warn("save_restore_failed", context={**context, "reason": data.get("reason")})
        atomic_write_json(layout.result_file, {**data, "reported": True})
    apply_retention(layout=layout)


# --- download ---------------------------------------------------------------------


@dataclass(frozen=True)
class ArchivePlan:
    """A validated save ready to stream as an uncompressed tar."""

    save_id: str
    length: int
    members: list[tuple[bytes, Path, int]]

    @property
    def filename(self) -> str:
        return f"elosern-save-{self.save_id}.tar"


def plan_archive(save_id: str, *, layout: SaveLayout | None = None) -> ArchivePlan:
    """Validate a save and lay out its tar members before streaming starts."""
    layout = layout or default_layout()
    validate_save_id(save_id)
    if not is_complete(layout, save_id):
        raise SaveNotFound(save_id)
    manifest = read_manifest(layout, save_id)
    mtime = _manifest_mtime(manifest)
    entries: list[tuple[str, Path]] = [
        (MANIFEST_FILENAME, layout.manifest_path(save_id)),
        (DB_FILENAME, layout.saved_db(save_id)),
    ]
    art_dir = layout.art_dir(save_id)
    for entry in manifest["files"]["art"]:
        relative = str(entry.get("path") or "")
        if not relative or relative.startswith("/") or ".." in Path(relative).parts:
            raise SaveNotFound(save_id)
        entries.append((f"art/{relative}", art_dir / relative))
    members = []
    length = 2 * _TAR_BLOCK
    for name, path in entries:
        try:
            stat = path.lstat()
        except OSError as error:  # observability: ignore R2: a file pruned since validation means the save is gone
            raise SaveNotFound(save_id) from error
        if not path.is_file() or path.is_symlink():
            raise SaveNotFound(save_id)
        info = tarfile.TarInfo(f"{save_id}/{name}")
        info.size = stat.st_size
        info.mtime = mtime
        info.mode = 0o644
        header = info.tobuf(format=tarfile.PAX_FORMAT, encoding="utf-8", errors="strict")
        members.append((header, path, stat.st_size))
        length += len(header) + _padded(stat.st_size)
    return ArchivePlan(save_id=save_id, length=length, members=members)


def _padded(size: int) -> int:
    return (size + _TAR_BLOCK - 1) // _TAR_BLOCK * _TAR_BLOCK


def _manifest_mtime(manifest: dict[str, Any]) -> int:
    try:
        return int(datetime.fromisoformat(str(manifest.get("created_at"))).timestamp())
    except ValueError:  # observability: ignore R2: an unparsable timestamp only affects archive member mtimes
        return 0


def iter_archive(plan: ArchivePlan) -> Iterator[bytes]:
    """Yield the tar stream; a short or missing file aborts the stream."""
    for header, path, size in plan.members:
        yield header
        remaining = size
        with path.open("rb") as handle:
            while remaining:
                chunk = handle.read(min(_CHUNK_BYTES, remaining))
                if not chunk:
                    raise SaveError(f"{path.name} shrank while streaming")
                remaining -= len(chunk)
                yield chunk
        padding = _padded(size) - size
        if padding:
            yield b"\0" * padding
    yield b"\0" * (2 * _TAR_BLOCK)


__all__ = [
    "SaveInfo",
    "apply_retention",
    "create_snapshot",
    "delete_save",
    "get_save",
    "iter_archive",
    "latest_restore_result",
    "list_saves",
    "pending_restore",
    "plan_archive",
    "request_restore",
    "startup_report",
]
