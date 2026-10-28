"""The only source/layout file writer: one guarded single-document effect.

A named command handler produces exactly one :class:`Effect` -- create,
replace or remove of one canonical document -- and the executor hands it to
:meth:`DocumentWriter.publish` together with the expected presence (the
content fingerprint, or :data:`ABSENT`). Nothing else in the service writes a
workspace file.

Publication, with the parent directory reached through the confined
no-follow descriptor walk:

1. recheck the target's current presence/fingerprint against the expectation
   immediately before publishing (:class:`StaleDocument` on a mismatch);
2. create/replace: write and flush a sibling temporary file; replace renames it
   over the target atomically; create links it to the target name, which
   cannot overwrite an existing file, then drops the temporary name;
   remove: unlink the target;
3. flush the parent directory before acknowledging durable success.

Outcomes (see docs/development/map-editor.md, "Durability"):

- any failure before the rename/link/unlink leaves the target untouched and
  removes the temporary file: :class:`SaveFailed`;
- a real error from the rename/link/unlink is classified by errno: the
  "not performed" errnos are :class:`SaveFailed` (``EEXIST`` on create and
  ``ENOENT`` on remove are :class:`StaleDocument`), any other errno is
  :class:`SaveUncertain`;
- after publication, a failed directory flush is :class:`SaveUncertain`.

The recheck and the publication are not atomic against another process
writing the same files; the fingerprint guard detects accidental overwrites
under continuous file following and makes no compare-and-swap claim.
"""

from __future__ import annotations

import errno
import hashlib
import os
import stat
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from .confinement import ConfinedWorkspace, ConfinementError

ABSENT = "absent"
CREATE = "create"
REPLACE = "replace"
REMOVE = "remove"
ACTIONS = frozenset({CREATE, REPLACE, REMOVE})

#: Errnos after which the rename/link/unlink is known not to have happened.
NOT_PERFORMED = frozenset(
    {
        errno.EACCES,
        errno.EPERM,
        errno.EROFS,
        errno.ENOSPC,
        errno.EDQUOT,
        errno.EXDEV,
        errno.ENOENT,
        errno.EEXIST,
        errno.ENOTDIR,
        errno.EISDIR,
    }
)
#: ``link`` errnos meaning the filesystem has no hard links.
NO_HARD_LINKS = frozenset({errno.EPERM, errno.ENOTSUP, errno.EOPNOTSUPP})

_READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | getattr(os, "O_NONBLOCK", 0)
_WRITE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC

#: Fault-injection stages, in publication order (tests only; production passes
#: no fault hook).
STAGES = ("write_temp", "flush_temp", "before_publish", "publish", "flush_directory")


def fingerprint_bytes(data: bytes) -> str:
    """The content fingerprint (equal to the core's ``fingerprint_text``)."""

    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True, slots=True)
class Effect:
    """One internal single-document effect; clients never choose one."""

    action: str
    relative_path: str
    text: str | None = None

    def __post_init__(self) -> None:
        if self.action not in ACTIONS:
            raise ValueError(f"unknown effect action {self.action!r}")
        if (self.action == REMOVE) != (self.text is None):
            raise ValueError("create/replace carry text; remove carries none")

    @property
    def data(self) -> bytes:
        assert self.text is not None
        return self.text.encode("utf-8")

    @property
    def result(self) -> str:
        """The target's presence after this effect."""

        return ABSENT if self.text is None else fingerprint_bytes(self.data)


class WriteError(Exception):
    code = "save_failed"

    def __init__(self, message: str, relative_path: str) -> None:
        super().__init__(message)
        self.relative_path = relative_path


class StaleDocument(WriteError):
    """Disk no longer holds the expected presence/content."""

    code = "stale_document"


class SaveFailed(WriteError):
    """Publication did not happen; the prior presence/content is intact."""

    code = "save_failed"


class SaveUncertain(WriteError):
    """Publication may have happened; durability is unknown until a reread."""

    code = "save_uncertain"


class DocumentWriter:
    def __init__(
        self,
        workspace: ConfinedWorkspace,
        max_document_bytes: int,
        *,
        fault: Callable[[str], None] | None = None,
    ) -> None:
        self.workspace = workspace
        self.max_document_bytes = max_document_bytes
        self.fault = fault

    def _fault(self, stage: str) -> None:
        if self.fault is not None:
            self.fault(stage)

    # -- reads -----------------------------------------------------------
    def _presence_at(self, parent: int, name: str) -> tuple[str, bytes | None, int | None]:
        """``(presence, bytes, mode)`` of one entry under an open directory."""

        try:
            fd = os.open(name, _READ_FLAGS, dir_fd=parent)
        except FileNotFoundError:
            return ABSENT, None, None
        except OSError as error:
            return f"unreadable:{errno.errorcode.get(error.errno, error.errno)}", None, None
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                return "unreadable:not_regular_file", None, None
            if info.st_size > self.max_document_bytes:
                return "unreadable:too_large", None, None
            chunks = []
            while chunk := os.read(fd, 1024 * 1024):
                chunks.append(chunk)
            data = b"".join(chunks)
            return fingerprint_bytes(data), data, stat.S_IMODE(info.st_mode)
        finally:
            os.close(fd)

    def read(self, relative_path: str) -> tuple[str, bytes | None]:
        """The current presence and bytes of one writable document."""

        try:
            parent, name = self.workspace.open_writable_parent(relative_path)
        except ConfinementError as error:
            if error.code == "missing":
                return ABSENT, None
            return f"unreadable:{error.code}", None
        try:
            presence, data, _ = self._presence_at(parent, name)
            return presence, data
        finally:
            os.close(parent)

    # -- publication -----------------------------------------------------
    def publish(self, effect: Effect, expected: str) -> str:
        """Publish one effect if disk still holds ``expected``; return the new presence."""

        path = effect.relative_path
        if (effect.action == CREATE) != (expected == ABSENT):
            raise ValueError("create expects absence; replace/remove expect a fingerprint")
        try:
            parent, name = self.workspace.open_writable_parent(path, create=effect.action == CREATE)
        except ConfinementError as error:
            if error.code == "missing" and expected != ABSENT:
                raise StaleDocument("the document's directory no longer exists", path) from error
            raise SaveFailed(f"cannot reach the document: {error}", path) from error
        except OSError as error:
            raise SaveFailed(f"cannot reach the document: {error.strerror}", path) from error
        try:
            current, _, mode = self._presence_at(parent, name)
            if current != expected:
                raise StaleDocument("the document changed on disk; reread before writing", path)
            if effect.action == REMOVE:
                self._remove(parent, name, path)
            else:
                self._write(parent, name, path, effect, mode)
            try:
                self._fault("flush_directory")
                os.fsync(parent)
            except OSError as error:
                raise SaveUncertain(
                    f"the directory flush failed after publication: {error.strerror or error}", path
                ) from error
        finally:
            os.close(parent)
        return effect.result

    def _remove(self, parent: int, name: str, path: str) -> None:
        try:
            self._fault("before_publish")
        except OSError as error:
            raise SaveFailed(f"removal was not attempted: {error.strerror or error}", path) from error
        try:
            self._fault("publish")
            os.unlink(name, dir_fd=parent)
        except OSError as error:
            if error.errno == errno.ENOENT:
                raise StaleDocument("the document was already removed on disk", path) from error
            raise _classified(error, path, "removal") from error

    def _write(self, parent: int, name: str, path: str, effect: Effect, mode: int | None) -> None:
        temp = f".{name}.{uuid.uuid4().hex}.tmp"
        try:
            self._write_temp(parent, temp, effect.data, mode)
            self._fault("before_publish")
        except OSError as error:
            _discard(parent, temp)
            raise SaveFailed(f"the new content was not published: {error.strerror or error}", path) from error
        if effect.action == REPLACE:
            try:
                self._fault("publish")
                os.replace(temp, name, src_dir_fd=parent, dst_dir_fd=parent)
            except OSError as error:
                _discard(parent, temp)
                raise _classified(error, path, "replacement") from error
            return
        try:
            self._fault("publish")
            os.link(temp, name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
        except OSError as error:
            _discard(parent, temp)
            if error.errno == errno.EEXIST:
                raise StaleDocument("a file appeared where absence was expected", path) from error
            if error.errno in NO_HARD_LINKS:
                self._create_exclusive(parent, name, path, effect.data)
                return
            raise _classified(error, path, "creation") from error
        # Published: a leftover temporary name does not undo the creation and is
        # never discovered (it does not end in ``.yaml``).
        _discard(parent, temp)

    def _write_temp(self, parent: int, temp: str, data: bytes, mode: int | None) -> None:
        self._fault("write_temp")
        fd = os.open(temp, _WRITE_FLAGS, 0o666, dir_fd=parent)
        try:
            if mode is not None:
                os.fchmod(fd, mode)
            view = memoryview(data)
            while view:
                view = view[os.write(fd, view):]
            self._fault("flush_temp")
            os.fsync(fd)
        finally:
            os.close(fd)

    def _create_exclusive(self, parent: int, name: str, path: str, data: bytes) -> None:
        """Fallback create on a filesystem without hard links."""

        try:
            fd = os.open(name, _WRITE_FLAGS, 0o666, dir_fd=parent)
        except FileExistsError as error:
            raise StaleDocument("a file appeared where absence was expected", path) from error
        except OSError as error:
            raise SaveFailed(f"the document was not created: {error.strerror}", path) from error
        try:
            try:
                view = memoryview(data)
                while view:
                    view = view[os.write(fd, view):]
                os.fsync(fd)
            finally:
                os.close(fd)
        except OSError as error:
            # Do not leave a truncated document behind; whether even that
            # removal is durable is unknown, so the outcome stays uncertain.
            _discard(parent, name)
            raise SaveUncertain(f"the document was partly created: {error.strerror}", path) from error


def _classified(error: OSError, path: str, what: str) -> WriteError:
    if error.errno in NOT_PERFORMED:
        return SaveFailed(f"the {what} did not happen: {error.strerror or error}", path)
    return SaveUncertain(f"the {what} may have happened: {error.strerror or error}", path)


def _discard(parent: int, temp: str) -> None:
    try:
        os.unlink(temp, dir_fd=parent)
    except FileNotFoundError:
        pass
    except OSError:
        # observability: ignore R2: the editor service has no game logging
        # facade; a leftover temporary name is inert (never discovered).
        pass


__all__ = [
    "ABSENT",
    "CREATE",
    "DocumentWriter",
    "Effect",
    "REMOVE",
    "REPLACE",
    "STAGES",
    "SaveFailed",
    "SaveUncertain",
    "StaleDocument",
    "WriteError",
    "fingerprint_bytes",
]
