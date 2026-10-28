"""Workspace confinement: the only way the service touches workspace files.

A document identity is a canonical workspace-relative path. It resolves only
inside the allowlisted roots:

- world sources and editor layouts, exactly the paths the core recognises
  (``elosern_map_core.sources.expected_document``) under ``content/maps`` and
  ``content/map-editor-layouts``;
- the two generated artifacts, read-only to every command; only the
  partition job publishes the partition artifact
  (:meth:`ConfinedWorkspace.open_partition_artifact_parent`).

Confinement is enforced at the actual open, not by an earlier path check: the
file is reached by walking from a directory descriptor of the real workspace
root, one component at a time, with ``O_NOFOLLOW``. Any symbolic link below the
root -- escaping or not -- is refused, so a path that was checked cannot be
swapped for a link before it is opened. Sizes are bounded with ``fstat`` before
a single byte is read.

External static sources (hashed for reference-context freshness only, never
returned) use the same descriptor walk under the workspace root.
"""

from __future__ import annotations

import errno
import os
import stat
from pathlib import Path

from elosern_map_core.sources import (
    FIXED_SOURCES,
    LAYOUT_DIRECTORY,
    SOURCE_DIRECTORIES,
    expected_document,
)

PARTITION_ARTIFACT = "world/maps/data/district_partition.json"
REFERENCE_CONTEXT_ARTIFACT = "content/map-reference-context.json"
ARTIFACTS = frozenset({PARTITION_ARTIFACT, REFERENCE_CONTEXT_ARTIFACT})

_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | getattr(os, "O_NONBLOCK", 0)


class ConfinementError(ValueError):
    """A path was refused; ``code`` is the stable machine reason."""

    def __init__(self, code: str, relative_path: object, message: str) -> None:
        self.code = code
        self.relative_path = relative_path if isinstance(relative_path, str) else repr(relative_path)
        super().__init__(message)


def split_relative(relative_path: object) -> tuple[str, ...]:
    """Validate the lexical shape of a workspace-relative path."""

    if not isinstance(relative_path, str) or not relative_path:
        raise ConfinementError("invalid_document_id", relative_path, "a document id must be a non-empty string")
    if "\0" in relative_path or "\\" in relative_path:
        raise ConfinementError("invalid_document_id", relative_path, "a document id may not contain NUL or backslash")
    if relative_path.startswith("/") or (len(relative_path) > 1 and relative_path[1] == ":"):
        raise ConfinementError("traversal", relative_path, "absolute paths are refused")
    parts = tuple(relative_path.split("/"))
    if any(part in ("", ".", "..") for part in parts):
        raise ConfinementError("traversal", relative_path, "empty, '.' and '..' components are refused")
    return parts


def resolve_document_id(relative_path: object) -> str:
    """Return the canonical id of an allowlisted document, or raise."""

    split_relative(relative_path)
    assert isinstance(relative_path, str)
    if relative_path in ARTIFACTS or expected_document(relative_path) is not None:
        return relative_path
    raise ConfinementError(
        "not_allowlisted", relative_path, "the path is outside the allowlisted source/layout/artifact set"
    )


class ConfinedWorkspace:
    """Descriptor-walk reads beneath one real workspace root."""

    def __init__(self, root: str | os.PathLike[str]) -> None:
        self.root = Path(os.path.realpath(root))

    # -- descriptor walk -------------------------------------------------
    def _open_directory(self, parts: tuple[str, ...], relative_path: str) -> int:
        fd = os.open(self.root, _DIR_FLAGS)
        try:
            for part in parts:
                try:
                    next_fd = os.open(part, _DIR_FLAGS, dir_fd=fd)
                except OSError as error:
                    raise _walk_error(error, relative_path, fd, part) from error
                os.close(fd)
                fd = next_fd
        except BaseException:
            os.close(fd)
            raise
        return fd

    def open_writable_parent(self, relative_path: object, *, create: bool = False) -> tuple[int, str]:
        """``(parent_fd, name)`` for a writable source/layout document.

        Generated artifacts are never writable. With ``create`` a missing
        directory is made one component at a time below the workspace root,
        through the same no-follow descriptor walk, so a linked directory is
        refused instead of followed. The caller closes ``parent_fd``.
        """

        canonical = resolve_document_id(relative_path)
        if canonical in ARTIFACTS:
            raise ConfinementError("not_writable", canonical, "generated artifacts are read-only")
        return self._walk_parent(canonical, create=create)

    def open_partition_artifact_parent(self, *, create: bool = False) -> tuple[int, str]:
        """``(parent_fd, name)`` of the partition artifact, for its job only.

        The partition job's guarded publication is the single writer of a
        generated artifact (no command, route or client names this path).
        The reference-context artifact stays read-only. With ``create``
        missing directories are made through the same no-follow walk.
        """

        return self._walk_parent(PARTITION_ARTIFACT, create=create)

    def _walk_parent(self, canonical: str, *, create: bool) -> tuple[int, str]:
        parts = split_relative(canonical)
        fd = os.open(self.root, _DIR_FLAGS)
        try:
            for part in parts[:-1]:
                try:
                    next_fd = os.open(part, _DIR_FLAGS, dir_fd=fd)
                except FileNotFoundError:
                    if not create:
                        raise ConfinementError("missing", canonical, "the directory does not exist") from None
                    try:
                        os.mkdir(part, 0o777, dir_fd=fd)
                        # The new entry is durable only once its parent is flushed.
                        os.fsync(fd)
                    except FileExistsError:
                        pass
                    try:
                        next_fd = os.open(part, _DIR_FLAGS, dir_fd=fd)
                    except OSError as error:
                        raise _walk_error(error, canonical, fd, part) from error
                except OSError as error:
                    raise _walk_error(error, canonical, fd, part) from error
                os.close(fd)
                fd = next_fd
        except BaseException:
            os.close(fd)
            raise
        return fd, parts[-1]

    def _read(self, relative_path: str, parts: tuple[str, ...], limit: int) -> bytes:
        parent = self._open_directory(parts[:-1], relative_path)
        try:
            try:
                fd = os.open(parts[-1], _FILE_FLAGS, dir_fd=parent)
            except OSError as error:
                raise _walk_error(error, relative_path, parent, parts[-1]) from error
        finally:
            os.close(parent)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise ConfinementError("not_regular_file", relative_path, "only regular files are read")
            if info.st_size > limit:
                raise ConfinementError(
                    "too_large", relative_path, f"{info.st_size} bytes exceeds the {limit}-byte limit"
                )
            chunks: list[bytes] = []
            remaining = limit + 1
            while remaining > 0:
                chunk = os.read(fd, min(remaining, 1024 * 1024))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            data = b"".join(chunks)
            if len(data) > limit:
                raise ConfinementError("too_large", relative_path, f"exceeds the {limit}-byte limit")
            return data
        finally:
            os.close(fd)

    # -- public reads ----------------------------------------------------
    def read_document(self, relative_path: object, limit: int) -> bytes:
        """Read one allowlisted source/layout/artifact document."""

        canonical = resolve_document_id(relative_path)
        return self._read(canonical, split_relative(canonical), limit)

    def read_external(self, relative_path: object, limit: int) -> bytes:
        """Read one external static source for hashing only (never returned)."""

        parts = split_relative(relative_path)
        assert isinstance(relative_path, str)
        return self._read(relative_path, parts, limit)

    def exists(self, relative_path: str) -> bool:
        """Whether a regular, non-link file exists at a confined path."""

        parts = split_relative(relative_path)
        try:
            parent = self._open_directory(parts[:-1], relative_path)
        except ConfinementError as error:
            if error.code == "missing":
                return False
            raise
        try:
            info = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            return False
        finally:
            os.close(parent)
        if stat.S_ISLNK(info.st_mode):
            raise ConfinementError("symlink_rejected", relative_path, "symbolic links are not followed")
        return stat.S_ISREG(info.st_mode)

    def list_yaml(self, relative_directory: str) -> tuple[tuple[str, str | None], ...]:
        """``(relative_path, refusal_code)`` for every ``*.yaml`` entry.

        A regular file has refusal ``None``; a link or other entry type is
        still reported, with its refusal, so the caller can diagnose it rather
        than silently drop an authored document.
        """

        parts = split_relative(relative_directory)
        try:
            fd = self._open_directory(parts, relative_directory)
        except ConfinementError as error:
            if error.code == "missing":
                return ()
            raise
        try:
            rows: list[tuple[str, str | None]] = []
            with os.scandir(fd) as entries:
                for entry in entries:
                    if not entry.name.endswith(".yaml"):
                        continue
                    path = f"{relative_directory}/{entry.name}"
                    if entry.is_symlink():
                        rows.append((path, "symlink_rejected"))
                    elif entry.is_file(follow_symlinks=False):
                        rows.append((path, None))
                    else:
                        rows.append((path, "not_regular_file"))
            return tuple(sorted(rows))
        finally:
            os.close(fd)

    def discover_world(self) -> tuple[tuple[str, str | None], ...]:
        """The world source set (same rule as the core discovery), confined."""

        rows: list[tuple[str, str | None]] = []
        for relative_path in FIXED_SOURCES:
            try:
                if self.exists(relative_path):
                    rows.append((relative_path, None))
            except ConfinementError as error:
                rows.append((relative_path, error.code))
        for directory in SOURCE_DIRECTORIES:
            try:
                rows.extend(self.list_yaml(directory))
            except ConfinementError as error:
                rows.append((directory, error.code))
        return tuple(sorted(rows))

    def discover_layouts(self) -> tuple[tuple[str, str | None], ...]:
        try:
            return self.list_yaml(LAYOUT_DIRECTORY)
        except ConfinementError as error:
            return ((LAYOUT_DIRECTORY, error.code),)


def _is_link(dir_fd: int, name: str) -> bool:
    try:
        return stat.S_ISLNK(os.stat(name, dir_fd=dir_fd, follow_symlinks=False).st_mode)
    except OSError:
        return False


def _walk_error(error: OSError, relative_path: str, dir_fd: int, name: str) -> ConfinementError:
    # O_NOFOLLOW reports ELOOP for a final link and, combined with
    # O_DIRECTORY, ENOTDIR for a link to a directory: decide by lstat.
    if error.errno in (errno.ELOOP, errno.EMLINK) or (
        error.errno == errno.ENOTDIR and _is_link(dir_fd, name)
    ):
        return ConfinementError("symlink_rejected", relative_path, "symbolic links are not followed")
    if error.errno == errno.ENOTDIR:
        return ConfinementError("not_directory", relative_path, "a path component is not a directory")
    if error.errno == errno.ENOENT:
        return ConfinementError("missing", relative_path, "the file does not exist")
    return ConfinementError("unreadable", relative_path, f"cannot open: {error.strerror}")


__all__ = [
    "ARTIFACTS",
    "ConfinedWorkspace",
    "ConfinementError",
    "PARTITION_ARTIFACT",
    "REFERENCE_CONTEXT_ARTIFACT",
    "resolve_document_id",
    "split_relative",
]
