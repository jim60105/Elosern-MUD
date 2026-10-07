"""Pre-start restore tool (standard library only).

    python -m server.saves.restore --apply-pending

Both launchers (``scripts/serve.sh``, ``docker-entrypoint.sh``) run this
before ``evennia migrate``. A restore cannot run inside the live server (the
SQLite file and Evennia's object caches are in use), so the server only
writes ``RESTORE_PENDING`` and shuts down; this tool applies it before the
next start. It must not import Django, Evennia, or the observability facade:
it reports on stdout and in ``RESTORE_RESULT.json``, which the next server
start translates into ``save_restored`` / ``save_restore_failed`` events.

Procedure for a pending save:

1. Verify: the id, the manifest, every inventoried file (present, regular,
   exact size), the saved database (``PRAGMA quick_check``), and migration
   compatibility with the current code. Any failure removes the marker,
   writes a failure result, and lets startup continue on the current world.
2. Stage independent writable copies of the save next to the live stores
   (same volumes): ``<db dir>/.restore-staging`` and
   ``<art root>/.restore-staging``.
3. Move the live database (with any ``-journal``/``-wal``/``-shm``) and every
   top-level live art entry aside into ``.restore-aside``; the art root is a
   volume mount point, so entries move rather than the root. ``.saves``
   stays where it is.
4. Install the staged copies.
5. Success removes the moved-aside originals and the marker. A failure in
   steps 3-4 moves the originals back, removes the marker, and continues a
   normal start. The save archive is never consumed.

Exit status is 0 whenever startup may continue. It is 2 when the live stores
may be inconsistent — a rollback that itself failed, or ``.restore-aside``
left over from an interrupted run — so the launcher (``set -e``) stops before
the server starts on a damaged world; the operator recovers by hand from the
directories named on stdout. That is an operational limitation, not a
crash-recovery protocol.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Any

from server.saves import inventory
from server.saves.layout import (
    ASIDE_DIRNAME,
    ART_RESERVED_NAMES,
    DB_FILENAME,
    STAGING_DIRNAME,
    ManifestError,
    SaveError,
    SaveIncompatible,
    SaveLayout,
    atomic_write_json,
    read_manifest,
    utc_now_iso,
    validate_save_id,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_SIDECARS = ("-journal", "-wal", "-shm")

EXIT_OK = 0
EXIT_UNSAFE = 2


class RestoreFailed(Exception):
    """A verification or installation failure; startup continues."""


class RollbackFailed(Exception):
    """The original stores could not be put back; startup must stop."""


def _say(message: str) -> None:
    print(f"[restore] {message}", flush=True)


# --- verification ------------------------------------------------------------


def verify(layout: SaveLayout, save_id: str, project_root: Path) -> dict[str, Any]:
    """Check one save completely before anything live is touched."""
    try:
        manifest = read_manifest(layout, save_id)
    except ManifestError as error:
        raise RestoreFailed(f"manifest invalid: {error}") from error
    saved_db = layout.saved_db(save_id)
    db_entry = manifest["files"].get("db")
    if not isinstance(db_entry, dict):
        raise RestoreFailed("manifest lacks the database entry")
    _check_file(saved_db, db_entry.get("size"))
    art_dir = layout.art_dir(save_id)
    if not art_dir.is_dir() or art_dir.is_symlink():
        raise RestoreFailed("art half missing")
    for entry in manifest["files"]["art"]:
        relative = str(entry.get("path") or "") if isinstance(entry, dict) else ""
        parts = Path(relative).parts
        if not relative or Path(relative).is_absolute() or ".." in parts or parts[0] in ART_RESERVED_NAMES:
            raise RestoreFailed(f"unsafe art path in manifest: {relative!r}")
        if any((art_dir / Path(*parts[:depth])).is_symlink() for depth in range(1, len(parts))):
            raise RestoreFailed(f"art path crosses a link: {relative!r}")
        _check_file(art_dir / relative, entry.get("size"))
    _quick_check(saved_db)
    try:
        rows = inventory.applied_migrations(saved_db)
    except sqlite3.Error as error:
        raise RestoreFailed(f"saved database has no migration table: {error}") from error
    unknown = inventory.unknown_migrations(rows, inventory.known_migrations(project_root))
    if unknown:
        raise RestoreFailed(f"{SaveIncompatible.code}: unknown migrations {', '.join(unknown[:5])}")
    return manifest


def _check_file(path: Path, size: Any) -> None:
    if path.is_symlink() or not path.is_file():
        raise RestoreFailed(f"missing file: {path.name}")
    if not isinstance(size, int) or path.stat().st_size != size:
        raise RestoreFailed(f"size mismatch: {path.name}")


def _quick_check(db_path: Path) -> None:
    uri = f"{db_path.resolve().as_uri()}?mode=ro&immutable=1"
    try:
        connection = sqlite3.connect(uri, uri=True)
        try:
            result = connection.execute("PRAGMA quick_check").fetchone()
        finally:
            connection.close()
    except sqlite3.Error as error:
        raise RestoreFailed(f"saved database unreadable: {error}") from error
    if not result or result[0] != "ok":
        raise RestoreFailed("saved database failed its integrity check")


# --- staging, swap, rollback ----------------------------------------------------


def _fsync_tree(root: Path) -> None:
    for directory, _subdirs, names in os.walk(root):
        for name in names:
            fd = os.open(Path(directory) / name, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)


def _rmtree(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


class Swap:
    """The live-store replacement with an exact record of what moved."""

    def __init__(self, layout: SaveLayout) -> None:
        self.layout = layout
        self.db_dir = layout.db_file.parent
        self.db_staging = self.db_dir / STAGING_DIRNAME
        self.db_aside = self.db_dir / ASIDE_DIRNAME
        self.art_staging = layout.art_root / STAGING_DIRNAME
        self.art_aside = layout.art_root / ASIDE_DIRNAME
        self.moved_db: list[str] = []
        self.moved_art: list[str] = []
        self.installed_db = False
        self.installed_art: list[str] = []

    def stage(self, save_id: str, art_files: list[str]) -> None:
        for path in (self.db_staging, self.art_staging):
            _rmtree(path)
        self.db_staging.mkdir(parents=True)
        shutil.copy2(self.layout.saved_db(save_id), self.db_staging / DB_FILENAME)
        _fsync_tree(self.db_staging)
        self.layout.art_root.mkdir(parents=True, exist_ok=True)
        self.art_staging.mkdir()
        # Only the verified, manifest-listed regular files are installed:
        # anything else in the archive (a planted link, a stray file) is not.
        source = self.layout.art_dir(save_id)
        for relative in art_files:
            target = self.art_staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / relative, target, follow_symlinks=False)
        _fsync_tree(self.art_staging)

    def move_aside(self) -> None:
        self.db_aside.mkdir()
        for suffix in ("", *DB_SIDECARS):
            name = DB_FILENAME + suffix
            source = self.db_dir / name
            if source.exists() or source.is_symlink():
                os.rename(source, self.db_aside / name)
                self.moved_db.append(name)
        self.art_aside.mkdir()
        for name in sorted(os.listdir(self.layout.art_root)):
            if name in ART_RESERVED_NAMES:
                continue
            os.rename(self.layout.art_root / name, self.art_aside / name)
            self.moved_art.append(name)

    def install(self) -> None:
        os.rename(self.db_staging / DB_FILENAME, self.layout.db_file)
        self.installed_db = True
        install_art(self)

    def rollback(self) -> None:
        try:
            for name in reversed(self.installed_art):
                _rmtree(self.layout.art_root / name)
            if self.installed_db:
                self.layout.db_file.unlink(missing_ok=True)
                for suffix in DB_SIDECARS:
                    # A sidecar created against the installed file must never
                    # be paired with the original database.
                    if DB_FILENAME + suffix not in self.moved_db:
                        (self.db_dir / (DB_FILENAME + suffix)).unlink(missing_ok=True)
            for name in self.moved_db:
                os.rename(self.db_aside / name, self.db_dir / name)
            for name in self.moved_art:
                os.rename(self.art_aside / name, self.layout.art_root / name)
            for path in (self.db_aside, self.art_aside):
                if path.exists():
                    path.rmdir()
        except OSError as error:
            raise RollbackFailed(str(error)) from error



def _cleanup_best_effort(paths: tuple[Path, ...], *, committed: bool = False) -> None:
    """Remove work directories; report, never raise, when one cannot go.

    After a committed swap a moved-aside original that cannot be removed is
    renamed to ``.restore-done-<time>`` so it never reads as an interrupted
    restore on the next start; the operator may delete it.
    """
    for path in paths:
        try:
            _rmtree(path)
        except OSError as error:  # the tool runs without the facade; stdout is its report
            _say(f"could not remove {path}: {error}")
            if committed and path.name == ASIDE_DIRNAME and path.exists():
                kept = path.with_name(f".restore-done-{utc_now_iso().replace(':', '')}")
                try:
                    os.rename(path, kept)
                    _say(f"kept the replaced originals in {kept}")
                except OSError as rename_error:
                    _say(f"could not rename {path}: {rename_error}")


def install_art(swap: Swap) -> None:
    """Move every staged art entry into the live art root."""
    for name in sorted(os.listdir(swap.art_staging)):
        os.rename(swap.art_staging / name, swap.layout.art_root / name)
        swap.installed_art.append(name)


# --- entry point ------------------------------------------------------------------


def _write_result(layout: SaveLayout, payload: dict[str, Any]) -> None:
    atomic_write_json(layout.result_file, {**payload, "finished_at": utc_now_iso(), "reported": False})


def apply_pending(layout: SaveLayout, project_root: Path = PROJECT_ROOT) -> int:
    """Apply ``RESTORE_PENDING`` if present; return the process exit status."""
    marker = layout.pending_marker
    db_aside = layout.db_file.parent / ASIDE_DIRNAME
    art_aside = layout.art_root / ASIDE_DIRNAME
    # Checked on EVERY start, marker or not: a failed rollback or an
    # interrupted run leaves the original world only in these directories,
    # and starting without them would migrate a fresh, empty database.
    if db_aside.exists() or art_aside.exists():
        _say(f"refusing to start: an earlier restore left {db_aside} / {art_aside}; recover them by hand")
        return EXIT_UNSAFE
    if not marker.exists():
        _say("no pending restore")
        return EXIT_OK
    raw = marker.read_text(encoding="utf-8", errors="replace").strip()
    save_id = None
    manifest: dict[str, Any] = {}
    swap = Swap(layout)
    try:
        try:
            save_id = validate_save_id(raw)
        except SaveError as error:
            raise RestoreFailed("pending marker holds a malformed save id") from error
        _say(f"applying save {save_id}")
        manifest = verify(layout, save_id, project_root)
        swap.stage(save_id, [str(entry["path"]) for entry in manifest["files"]["art"]])
        swap.move_aside()
        swap.install()
    except Exception as error:  # every failure here is reported and rolled back below
        reason = str(error) or type(error).__name__
        _say(f"restore failed: {reason}")
        try:
            swap.rollback()
        except RollbackFailed as rollback_error:
            _say(f"ROLLBACK FAILED: {rollback_error}; originals remain in {swap.db_aside} and {swap.art_aside}")
            marker.unlink(missing_ok=True)
            _write_result(layout, {
                "save": save_id,
                "kind": manifest.get("kind"),
                "label": manifest.get("label"),
                "outcome": "failed",
                "reason": reason,
                "rollback": "failed",
            })
            return EXIT_UNSAFE
        _cleanup_best_effort((swap.db_staging, swap.art_staging))
        marker.unlink(missing_ok=True)
        _write_result(layout, {
            "save": save_id,
            "kind": manifest.get("kind"),
            "label": manifest.get("label"),
            "outcome": "failed",
            "reason": reason,
        })
        return EXIT_OK
    # The swap is committed: a cleanup failure must not stop the start. A
    # leftover committed aside is renamed out of the stale-aside check.
    _cleanup_best_effort((swap.db_staging, swap.art_staging, swap.db_aside, swap.art_aside), committed=True)
    marker.unlink(missing_ok=True)
    _write_result(layout, {
        "save": save_id,
        "kind": manifest.get("kind"),
        "label": manifest.get("label"),
        "outcome": "restored",
        "reason": None,
    })
    _say(f"restored save {save_id}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m server.saves.restore", description=__doc__.splitlines()[0])
    parser.add_argument("--apply-pending", action="store_true", required=True, help="apply RESTORE_PENDING if present")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--db-file", type=Path, default=None)
    parser.add_argument("--saves-root", type=Path, default=None)
    parser.add_argument("--art-root", type=Path, default=None)
    args = parser.parse_args(argv)
    default = SaveLayout.for_project(args.project_root)
    layout = SaveLayout(
        db_file=args.db_file or default.db_file,
        saves_root=args.saves_root or default.saves_root,
        art_root=args.art_root or default.art_root,
    )
    return apply_pending(layout, args.project_root)


if __name__ == "__main__":
    sys.exit(main())
