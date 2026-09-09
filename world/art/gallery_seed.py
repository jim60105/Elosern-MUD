"""Idempotent startup synchronization of the external bulk seed-art folder.

``gallery-seed-sync`` (design §7.1, D10): an operator prepares hundreds of
character/monster images offline and hands the server one read-only folder
(``ART_SEED_ROOT``, the ``PROMPT_ROOT`` precedent; compose bind-mounts the host
folder at ``/app/art-seed``). ``sync_all()`` walks the closed layout
``<seed root>/<kind-dir>/<subject-key>/<filename><ext>`` (``kind-dir`` exactly
``character`` / ``monster``), copies every accepted image into the store's
gallery path through the single confinement helper, and appends one unbound
``source`` ``seed`` card (no prompt pair, no generation seed/checkpoint/fields)
through the gallery write API.

**Path-derived idempotency, no bookkeeping.** A file's card ``image_id`` is
``uuid5`` of its slash-joined path relative to the seed root, so a re-run finds
every card already present and performs zero file I/O for it. Synchronization
is additive: it NEVER deletes, replaces, or reorders an existing card. A player
who DELETES a seed card gets the card and file back on the next start — the
accepted additive-mirror semantics: the seed tree is the operator's declared
set, and a no-bookkeeping sync cannot remember a tombstone. Malformed raw
entries additionally reserve their ``stored_identity``: a derived destination
any raw entry names is left byte-untouched and never carded, so a half-broken
card can never have the file behind it swapped out.

Only the derived id and the source extension enter the store path, so seed
filenames may contain spaces or Unicode freely; the extension must be an EXACT
member of the closed lowercase ``STORE_EXTENSIONS`` set (``.PNG`` is
unsupported, matching the stored-identity contract). Integrity rules around a
mis-mounted or hostile tree: the root itself must be a non-symlink directory
and every traversed directory must be a non-symlink directory. Classification
alone is never the boundary — a check-then-pathname-open is swappable in
between — so traversal descends from one ``O_NOFOLLOW`` directory fd and every
content file is opened RELATIVE to its verified parent fd with ``O_NOFOLLOW``
and re-verified by ``fstat`` AFTER the open: sources and manifests must be
regular single-link files within a hard size cap (seed images are
kilobyte-to-megabyte media; the cap bounds hostile memory use and rejects
special files), and the destination must also be a single-link regular file —
a planted symlink is refused at open (``ELOOP``) and a hard-linked inode is
never silently clobbered (identity paths are uuid5-derived, so a multi-link
destination is never a legitimate sync artifact). Content-identical
destinations are left byte-untouched; a differing unreferenced destination is
overwritten in place on the same inode BEFORE its card is appended, so a stale
orphan can never be served under a fresh card.

Per subject an optional ``manifest.json`` object may declare ``default`` (an
eligible image filename of this subject folder) and ``face_rect``. An invalid,
unreadable, or non-object manifest degrades WHOLE, with ONE diagnostic: the
first eligible file by sorted name becomes the default candidate and cards take
the API-filled ``DEFAULT_FACE_RECT``. The candidate's card becomes the
subject's default only when the subject has no default yet — including a
character whose default was deleted while other cards remain — so a player's
chosen default always survives a restart.

Monster subjects hold exactly one card by contract and ``append_card`` REPLACES
a full monster record, so a monster subject receives at most one seed card —
the candidate file — and no card ever replaces an existing raw entry (the
occupancy check reads the raw stored list, so even a malformed entry is
never replaced).

One bad entry never aborts the run: each failure is a bounded
``gallery_seed_sync`` diagnostic and the walk continues, with a per-run
diagnostic budget so a flood tree cannot drown the sink (the suppressed count
rides in the summary). Event discipline: an unset, absent, symlinked, or
unreadable root emits EXACTLY ONE ``gallery_seed_sync`` event and synchronizes
nothing; an admitted root emits exactly one summary event plus the bounded
diagnostics. Nothing ever raises out of ``sync_all()`` — a broken seed tree is
never a startup failure.

Imports stay inside the deterministic-path side of the package (gallery API,
paths confinement, subject model, observability facade, stdlib) — never the
worker, the sd-webui client, or any connectivity surface.
"""

from collections.abc import Mapping
import errno
import json
import os
from pathlib import Path
from stat import S_ISDIR, S_ISLNK, S_ISREG
import uuid

from django.conf import settings

from world.art.formats import STORE_EXTENSIONS
from world.art.gallery import (
    GALLERY_KIND_DIRECTORIES,
    GalleryRecordError,
    append_card,
    record_for,
    set_default,
    validate_face_rect,
)
from world.art.paths import resolved_under_store_root
from world.art.subjects import ArtSubject, ArtSubjectError, ArtSubjectKind
from world.observability import log_info, log_warn

# Event name (design §9): skip, per-entry diagnostic, and summary all share it
# and carry a "phase" discriminator in context.
SEED_SYNC_EVENT = "gallery_seed_sync"

# The manifest filename inside a subject folder. Nothing else in the tree is
# ever parsed as a manifest; root- and kind-level files are ignored.
MANIFEST_FILENAME = "manifest.json"

# Namespace pinning every derived id: the same relative path always yields the
# same image_id across restarts and hosts, and no other derivation in the
# engine can collide with it.
SEED_ID_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "aios-embed:elosern/art-seed")

# Per-run budget for bounded leaf diagnostics. Beyond it the walk still
# continues; only the event emission is capped and the suppressed count is
# reported in the summary.
_MAX_DIAGNOSTICS = 32

# Hard cap on any single file read from the (hostile-capable) seed tree and on
# any pre-existing destination we would overwrite. Seed images are
# kilobyte-to-megabyte media; anything past the cap is refused without being
# buffered into memory.
_MAX_FILE_BYTES = 32 * 1024 * 1024

# kind-dir -> typed kind (traversal order comes from the sorted listing).
_KIND_DIRECTORIES: dict[str, ArtSubjectKind] = {
    directory: kind for kind, directory in GALLERY_KIND_DIRECTORIES.items()
}


class _SeedFileRejected(Exception):
    """Internal: an opened file failed post-open verification."""


def derive_image_id(relative_path: str) -> str:
    """The canonical lowercase uuid5 image_id for a seed-root-relative path.

    The public spelling is the contract other code and tests derive ids with;
    it is pure and never raises.
    """
    return str(uuid.uuid5(SEED_ID_NAMESPACE, relative_path))


class _Diagnostics:
    """Bounded diagnostic counter emitting capped facade events."""

    def __init__(self) -> None:
        self.emitted = 0
        self.suppressed = 0

    def emit(self, reason: str, **context: object) -> None:
        if self.emitted < _MAX_DIAGNOSTICS:
            self.emitted += 1
            log_warn(
                SEED_SYNC_EVENT,
                context={"phase": "diagnostic", "reason": reason, **context},
            )
        else:
            self.suppressed += 1


def _open_dir_fd(name: str, *, dir_fd: int | None = None) -> int:
    """Open a directory no-follow (``O_NOFOLLOW``), raising ``OSError`` on refusal.

    With ``dir_fd`` the name is resolved relative to an already-verified
    parent directory fd, so no intermediate component of the walk is ever
    re-resolved through a swappable pathname.
    """
    return os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=dir_fd)


def _open_file_bytes(name: str, *, dir_fd: int) -> bytes:
    """Read a no-follow regular single-link file relative to a verified fd.

    Raises ``FileNotFoundError`` when the name is absent, ``OSError`` when it
    cannot be opened (a planted symlink answers ``ELOOP`` at open), and
    ``_SeedFileRejected`` when post-open verification fails: not a regular
    file, hard-linked (``st_nlink != 1``, so two names can never alias the
    bytes we classify), or past the size cap (checked on the ``fstat`` size
    before reading, so a hostile giant is never buffered).
    """
    fd = _open_nofollow(name, dir_fd=dir_fd, flags=os.O_RDONLY)
    try:
        stat_result = os.fstat(fd)
        if not S_ISREG(stat_result.st_mode) or stat_result.st_nlink != 1:
            raise _SeedFileRejected(name)
        if stat_result.st_size > _MAX_FILE_BYTES:
            raise _SeedFileRejected(name)
        chunks: list[bytes] = []
        remaining = _MAX_FILE_BYTES + 1
        while remaining:
            chunk = os.read(fd, min(remaining, 1 << 20))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
    finally:
        os.close(fd)
    if len(payload) > _MAX_FILE_BYTES:
        raise _SeedFileRejected(name)
    return payload


def _open_nofollow(name: str, *, dir_fd: int, flags: int) -> int:
    """``openat``-style open of the final component with ``O_NOFOLLOW``."""
    return os.open(name, flags | os.O_NOFOLLOW, dir_fd=dir_fd)


def _publish_under_store(identity: str, payload: bytes) -> bool:
    """Materialize ``identity`` under the store root; True when bytes changed.

    The identity has already passed the confinement helper; this primitive is
    race-safe anyway: every directory component is opened no-follow RELATIVE
    to the verified parent fd (creating it when absent), and the final file is
    opened ``O_RDWR | O_CREAT | O_NOFOLLOW`` and ``fstat``-verified AFTER the
    open — a swapped-in symlink answers ``ELOOP``, a non-regular file or a
    hard-linked inode is refused, and an existing file past the size cap is
    refused rather than compared byte-for-byte from hostile memory. Identical
    content leaves the file byte-untouched; different content is written in
    place on the same inode (readers never see an unlinked gap).

    Raises ``_SeedFileRejected`` for any refusal and ``OSError`` for I/O
    failure; callers map both to bounded diagnostics.
    """
    store_root = Path(str(settings.ART_STORE_ROOT)).resolve()
    parts = identity.split("/")
    opened: list[int] = []
    try:
        parent_fd = _open_dir_fd(str(store_root))
        opened.append(parent_fd)
        for part in parts[:-1]:
            try:
                child_fd = _open_dir_fd(part, dir_fd=parent_fd)
            except FileNotFoundError:  # observability: ignore R2: a missing component is created below, not a fault
                try:
                    os.mkdir(part, dir_fd=parent_fd)
                except FileExistsError:  # observability: ignore R2: a lost creation race is resolved by the reopen below
                    pass  # lost a creation race; the reopen below resolves it
                child_fd = _open_dir_fd(part, dir_fd=parent_fd)
            opened.append(child_fd)
            parent_fd = child_fd
        try:
            fd = _open_nofollow(
                parts[-1], dir_fd=parent_fd, flags=os.O_RDWR | os.O_CREAT
            )
        except OSError as error:
            # A planted symlink at the destination answers ELOOP at open.
            if error.errno == errno.ELOOP:
                raise _SeedFileRejected(identity) from error
            raise
        opened.append(fd)
        stat_result = os.fstat(fd)
        if not S_ISREG(stat_result.st_mode) or stat_result.st_nlink != 1:
            raise _SeedFileRejected(identity)
        existing = b""
        remaining = _MAX_FILE_BYTES + 1
        while remaining:
            chunk = os.read(fd, min(remaining, 1 << 20))
            if not chunk:
                break
            existing += chunk
            remaining -= len(chunk)
        if len(existing) > _MAX_FILE_BYTES:
            raise _SeedFileRejected(identity)
        if existing == payload:
            return False
        os.lseek(fd, 0, os.SEEK_SET)
        written = 0
        while written < len(payload):
            written += os.write(fd, payload[written:])
        os.ftruncate(fd, len(payload))
        return True
    finally:
        for fd in reversed(opened):
            try:
                os.close(fd)
            except OSError:  # observability: ignore R2: close failure cannot undo a completed write
                pass


def _parse_manifest(
    subject_fd: int, eligible_names: set[str], diagnostics: _Diagnostics, subject: str
) -> tuple[str | None, dict | None]:
    """Return ``(default_filename, face_rect)`` for one subject folder fd.

    An absent manifest yields ``(None, None)`` silently (the documented
    fallback). Any violation (unreadable, symlinked, oversized, non-UTF-8,
    non-JSON, not an object, unexpected keys, a ``default`` naming anything
    not in the eligible image set, an invalid ``face_rect``) yields
    ``(None, None)`` after EXACTLY ONE diagnostic: an invalid manifest degrades
    WHOLE, never partially, so the sorted-name candidate and the API-filled
    shared rectangle apply.
    """
    try:
        raw_bytes = _open_file_bytes(MANIFEST_FILENAME, dir_fd=subject_fd)
    except FileNotFoundError:  # observability: ignore R2: an absent manifest is the documented silent fallback
        return None, None
    except OSError:  # observability: ignore R2: an unreadable manifest degrades whole via the diagnostic below
        diagnostics.emit("manifest_unreadable", subject=subject)
        return None, None
    except _SeedFileRejected:  # observability: ignore R2: degradation is the bounded diagnostic below
        diagnostics.emit("manifest_unreadable", subject=subject)
        return None, None
    try:
        raw = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):  # observability: ignore R2: malformed JSON degrades whole via the diagnostic below
        diagnostics.emit("manifest_unreadable", subject=subject)
        return None, None
    if not isinstance(raw, dict) or not set(raw) <= {"default", "face_rect"}:
        diagnostics.emit("manifest_not_a_valid_object", subject=subject)
        return None, None
    face_rect = None
    if "face_rect" in raw:
        try:
            face_rect = validate_face_rect(raw["face_rect"])
        except GalleryRecordError:  # observability: ignore R2: an invalid rect degrades whole via the diagnostic below
            diagnostics.emit("manifest_invalid_face_rect", subject=subject)
            return None, None
    default_name = raw.get("default")
    if default_name is None:
        return None, face_rect
    if not isinstance(default_name, str) or default_name not in eligible_names:
        diagnostics.emit("manifest_default_not_an_eligible_file", subject=subject)
        return None, None
    return default_name, face_rect


def _raw_occupancy(subject: ArtSubject) -> tuple[int, set[str], set[str]]:
    """``(raw entry count, raw image ids, raw stored identities)`` of the record.

    Read directly from the record, never through the tolerant ``cards_for``:
    a malformed stored entry still OCCUPIES the record (a monster append would
    replace it, a duplicate id would corrupt it) AND still reserves its
    ``stored_identity`` (the file behind it is referenced even when the card
    no longer parses), so the never-replace guarantee, the duplicate-id check,
    and the byte-level never-overwrite must all see it. The tolerant read would
    also emit unrelated invalid-card events on every sync.
    """
    record = record_for(subject)
    if record is None:
        return 0, set(), set()
    cards = list(record.db.cards or [])
    ids: set[str] = set()
    identities: set[str] = set()
    for entry in cards:
        # Stored entries round-trip as Evennia's _SaverDict, never plain dict.
        if not isinstance(entry, Mapping):
            continue
        image_id = entry.get("image_id")
        if isinstance(image_id, str):
            ids.add(image_id)
        identity = entry.get("stored_identity")
        if isinstance(identity, str):
            identities.add(identity)
    return len(cards), ids, identities


def _has_raw_default(subject: ArtSubject) -> bool:
    """True when the subject already names a default (raw read, tolerant)."""
    record = record_for(subject)
    return record is not None and record.db.default_image_id is not None


def _sync_subject(
    kind_directory: str,
    kind: ArtSubjectKind,
    subject_name: str,
    kind_fd: int,
    diagnostics: _Diagnostics,
    counters: dict[str, int],
) -> None:
    """Synchronize one ``<kind-dir>/<subject-key>/`` folder; never raises."""
    try:
        subject = ArtSubject(kind, subject_name)
    except ArtSubjectError:  # observability: ignore R2: reported through the bounded diagnostic emitter below
        diagnostics.emit(
            "invalid_subject_key_skipped", kind=kind_directory, entry=subject_name
        )
        return
    subject_key = subject.full()
    try:
        subject_fd = _open_dir_fd(subject_name, dir_fd=kind_fd)
    except OSError:  # observability: ignore R2: reported through the bounded diagnostic emitter below
        diagnostics.emit("subject_directory_unreadable", subject=subject_key)
        return
    try:
        _sync_subject_open(kind_directory, subject, subject_fd, diagnostics, counters)
    finally:
        os.close(subject_fd)


def _sync_subject_open(
    kind_directory: str,
    subject: ArtSubject,
    subject_fd: int,
    diagnostics: _Diagnostics,
    counters: dict[str, int],
) -> None:
    """Synchronize one already-opened subject folder; never raises."""
    subject_key = subject.full()
    kind = subject.kind
    try:
        names = sorted(os.listdir(subject_fd))
    except OSError:  # observability: ignore R2: reported through the bounded diagnostic emitter below
        diagnostics.emit("subject_directory_unreadable", subject=subject_key)
        return
    images: list[str] = []
    for name in names:
        if name == MANIFEST_FILENAME:
            continue
        try:
            stat_result = os.lstat(name, dir_fd=subject_fd)
        except OSError:  # observability: ignore R2: a vanished listing entry is a silent no-op
            continue
        if S_ISLNK(stat_result.st_mode):
            diagnostics.emit("symlink_skipped", subject=subject_key, entry=name)
        elif S_ISDIR(stat_result.st_mode):
            diagnostics.emit("nested_directory_skipped", subject=subject_key, entry=name)
        elif not S_ISREG(stat_result.st_mode):
            diagnostics.emit("non_regular_entry_skipped", subject=subject_key, entry=name)
        elif Path(name).suffix not in STORE_EXTENSIONS:
            diagnostics.emit(
                "unsupported_extension_skipped", subject=subject_key, entry=name
            )
        else:
            images.append(name)
    if not images:
        return
    default_name, face_rect = _parse_manifest(
        subject_fd, set(images), diagnostics, subject_key
    )
    candidate_name = default_name or images[0]
    raw_count, existing_ids, referenced_identities = _raw_occupancy(subject)
    had_default = _has_raw_default(subject)

    if kind is ArtSubjectKind.MONSTER and raw_count > 0:
        # append_card REPLACES a full monster record: the never-replace
        # guarantee forbids touching a subject whose raw list holds any entry,
        # malformed included. Files whose card is already present are the
        # ordinary no-op; the rest count as blocked and earn ONE diagnostic
        # only when something genuinely could not be honored.
        present = sum(
            1
            for name in images
            if derive_image_id(f"{kind_directory}/{subject.key}/{name}") in existing_ids
        )
        counters["already_present"] += present
        blocked = len(images) - present
        counters["monster_cap_skipped"] += blocked
        if blocked:
            diagnostics.emit("monster_card_present_skipped", subject=subject_key, blocked=blocked)
        return

    for name in images:
        image_id = derive_image_id(f"{kind_directory}/{subject.key}/{name}")
        if image_id in existing_ids:
            counters["already_present"] += 1
            continue
        if kind is ArtSubjectKind.MONSTER and name != candidate_name:
            # The monster one-card cap: only the candidate file may ever be
            # appended for this subject.
            counters["monster_cap_skipped"] += 1
            diagnostics.emit("monster_cap_skipped", subject=subject_key, entry=name)
            continue
        identity = f"gallery/{kind_directory}/{subject.key}/{image_id}{Path(name).suffix}"
        if resolved_under_store_root(identity) is None:
            diagnostics.emit(
                "identity_refused_by_confinement", subject=subject_key, entry=name
            )
            continue
        if identity in referenced_identities:
            # A raw entry (valid or malformed) already points a card at this
            # exact file: never overwrite referenced bytes, never shadow the
            # entry with a second card.
            diagnostics.emit(
                "destination_referenced_skipped", subject=subject_key, entry=name
            )
            continue
        try:
            payload = _open_file_bytes(name, dir_fd=subject_fd)
        except OSError:  # observability: ignore R2: reported through the bounded diagnostic emitter below
            diagnostics.emit("source_unreadable", subject=subject_key, entry=name)
            continue
        except _SeedFileRejected:  # observability: ignore R2: reported through the bounded diagnostic emitter below
            diagnostics.emit("source_rejected", subject=subject_key, entry=name)
            continue
        try:
            changed = _publish_under_store(identity, payload)
        except _SeedFileRejected:  # observability: ignore R2: reported through the bounded diagnostic emitter below
            diagnostics.emit("destination_refused", subject=subject_key, entry=name)
            continue
        except OSError:  # observability: ignore R2: reported through the bounded diagnostic emitter below
            diagnostics.emit("copy_failed", subject=subject_key, entry=name)
            continue
        if changed:
            counters["copied"] += 1
        card_fields: dict = {
            "image_id": image_id,
            "stored_identity": identity,
            "prompt": None,
            "seed": None,
            "checkpoint": None,
            "requested_fields": [],
            "binding": None,
            "source": "seed",
        }
        if face_rect is not None:
            card_fields["face_rect"] = face_rect
        try:
            append_card(subject, **card_fields)
        except GalleryRecordError:  # observability: ignore R2: reported through the bounded diagnostic emitter below
            diagnostics.emit("card_append_rejected", subject=subject_key, entry=name)
            continue
        existing_ids.add(image_id)
        counters["appended"] += 1

    # Character default rule: the candidate becomes the default ONLY when the
    # subject had no default before this run — covering both a fresh record
    # (where the first append already auto-defaulted the first-appended card,
    # possibly not the candidate) and a record whose default was deleted while
    # other cards remained. A non-null prior default is never touched.
    if had_default or kind is not ArtSubjectKind.CHARACTER:
        return
    candidate_id = derive_image_id(f"{kind_directory}/{subject.key}/{candidate_name}")
    if candidate_id not in existing_ids:
        return
    current = record_for(subject)
    if current is not None and current.db.default_image_id == candidate_id:
        return
    try:
        set_default(subject, candidate_id)
        counters["defaults_set"] += 1
    except GalleryRecordError:  # observability: ignore R2: reported through the bounded diagnostic emitter below
        diagnostics.emit("default_set_rejected", subject=subject_key, entry=candidate_name)


def sync_all() -> dict:
    """Idempotently mirror the seed tree into the gallery store (startup step).

    Returns the summary dict (also emitted as one ``gallery_seed_sync``
    summary event): ``skipped`` plus the counters. Root admission is separate
    from traversal — an unset, absent, symlinked, or unreadable root emits
    exactly one skip event and returns; every admitted root ends in exactly
    one summary event (plus bounded diagnostics). The outermost catch exists
    only for unforeseen faults: a seed tree is never a startup failure, so
    nothing ever raises out of here.
    """
    counters: dict[str, int] = {
        "subjects": 0,
        "copied": 0,
        "appended": 0,
        "already_present": 0,
        "monster_cap_skipped": 0,
        "defaults_set": 0,
    }
    diagnostics = _Diagnostics()
    try:
        configured = str(getattr(settings, "ART_SEED_ROOT", "") or "")
        root = Path(configured)
        if not configured.strip():
            log_warn(
                SEED_SYNC_EVENT,
                context={"phase": "skip", "reason": "seed_root_unset"},
            )
            return {"skipped": True, **counters}
        if root.is_symlink():
            log_warn(
                SEED_SYNC_EVENT,
                context={"phase": "skip", "reason": "seed_root_symlink", "root": configured},
            )
            return {"skipped": True, **counters}
        if not root.is_dir():
            log_warn(
                SEED_SYNC_EVENT,
                context={"phase": "skip", "reason": "seed_root_absent", "root": configured},
            )
            return {"skipped": True, **counters}
        try:
            root_fd = _open_dir_fd(str(root))
        except OSError:  # observability: ignore R2: the unreadable root below is the one bounded skip event
            log_warn(
                SEED_SYNC_EVENT,
                context={"phase": "skip", "reason": "seed_root_unreadable", "root": configured},
            )
            return {"skipped": True, **counters}
        try:
            try:
                kind_names = sorted(os.listdir(root_fd))
            except OSError:  # observability: ignore R2: the unreadable root is the one bounded skip event below
                kind_names = None
            if kind_names is None:
                log_warn(
                    SEED_SYNC_EVENT,
                    context={"phase": "skip", "reason": "seed_root_unreadable", "root": configured},
                )
                return {"skipped": True, **counters}
            for kind_name in kind_names:
                kind = _KIND_DIRECTORIES.get(kind_name)
                try:
                    kind_stat = os.lstat(kind_name, dir_fd=root_fd)
                except OSError:  # observability: ignore R2: a vanished listing entry is a silent no-op
                    continue
                if S_ISLNK(kind_stat.st_mode):
                    diagnostics.emit(
                        "symlinked_kind_directory_skipped"
                        if kind is not None
                        else "symlink_skipped",
                        kind=kind_name,
                    )
                    continue
                if kind is None:
                    if S_ISDIR(kind_stat.st_mode):
                        diagnostics.emit("unknown_kind_directory_skipped", entry=kind_name)
                    continue
                if not S_ISDIR(kind_stat.st_mode):
                    continue
                try:
                    kind_fd = _open_dir_fd(kind_name, dir_fd=root_fd)
                except OSError:  # observability: ignore R2: reported through the bounded diagnostic emitter below
                    diagnostics.emit("kind_directory_unreadable", kind=kind_name)
                    continue
                try:
                    try:
                        subject_names = sorted(os.listdir(kind_fd))
                    except OSError:  # observability: ignore R2: reported through the bounded diagnostic emitter below
                        diagnostics.emit("kind_directory_unreadable", kind=kind_name)
                        continue
                    for subject_name in subject_names:
                        try:
                            stat_result = os.lstat(subject_name, dir_fd=kind_fd)
                        except OSError:  # observability: ignore R2: a vanished listing entry is a silent no-op
                            continue
                        if S_ISLNK(stat_result.st_mode):
                            diagnostics.emit(
                                "symlinked_subject_directory_skipped",
                                kind=kind_name,
                                entry=subject_name,
                            )
                            continue
                        if not S_ISDIR(stat_result.st_mode):
                            continue
                        counters["subjects"] += 1
                        _sync_subject(
                            kind_name,
                            kind,
                            subject_name,
                            kind_fd,
                            diagnostics,
                            counters,
                        )
                finally:
                    os.close(kind_fd)
        finally:
            os.close(root_fd)
        counters["diagnostics"] = diagnostics.emitted
        counters["suppressed_diagnostics"] = diagnostics.suppressed
        log_info(
            SEED_SYNC_EVENT,
            context={"phase": "summary", "root": configured, **counters},
        )
        return {"skipped": False, **counters}
    except Exception as error:
        log_warn(
            SEED_SYNC_EVENT,
            context={"phase": "skip", "reason": "sync_failed"},
            exc=error,
        )
        return {"skipped": True, **counters}
