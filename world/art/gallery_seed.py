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
set, and a no-bookkeeping sync cannot remember a tombstone.

Only the derived id and the source extension enter the store path, so seed
filenames may contain spaces or Unicode freely; the extension must be an EXACT
member of the closed lowercase ``STORE_EXTENSIONS`` set (``.PNG`` is
unsupported, matching the stored-identity contract). Integrity rules around a
mis-mounted or hostile tree: every traversed directory must be a non-symlink
directory and every accepted file a non-symlink regular file (``is_symlink``
is an lstat check — ``Path.is_file``/``copyfile`` would otherwise follow a
planted link out of the read-only mount), and when a derived card is absent the
seed bytes are (re)written to the deterministic unreferenced destination BEFORE
the card is appended, so a stale orphan can never be served under a fresh card.

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
rides in the summary). Event discipline: an unset, absent, or unreadable root
emits EXACTLY ONE ``gallery_seed_sync`` event and synchronizes nothing; an
admitted root emits exactly one summary event plus the bounded diagnostics.
Nothing ever raises out of ``sync_all()`` — a broken seed tree is never a
startup failure.

Imports stay inside the deterministic-path side of the package (gallery API,
paths confinement, subject model, observability facade, stdlib) — never the
worker, the sd-webui client, or any connectivity surface.
"""

from pathlib import Path
import json
import shutil
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

# kind-dir -> typed kind (traversal order comes from the sorted listing).
_KIND_DIRECTORIES: dict[str, ArtSubjectKind] = {
    directory: kind for kind, directory in GALLERY_KIND_DIRECTORIES.items()
}


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


def _child_entries(directory: Path) -> list[Path] | None:
    """All child entries of ``directory`` in sorted name order, or None.

    ``None`` signals an unreadable directory — the caller's bounded
    diagnostic signal. Entries are returned UNclassified (symlinks included);
    every consumer must classify before touching bytes, and directory
    traversal must reject symlinks through ``_is_plain_dir`` so a planted link
    inside the read-only mount is never followed.
    """
    try:
        return sorted(directory.iterdir(), key=lambda path: path.name)
    except OSError:  # observability: ignore R2: unreadability is the caller's bounded diagnostic signal
        return None


def _is_plain_dir(entry: Path) -> bool:
    """True when ``entry`` is a real directory (an lstat check on symlinks)."""
    return not entry.is_symlink() and entry.is_dir()


def _is_regular_file(entry: Path) -> bool:
    """True when ``entry`` is a real regular file (symlinks excluded)."""
    return not entry.is_symlink() and entry.is_file()


def _parse_manifest(
    manifest: Path, eligible_names: set[str], diagnostics: _Diagnostics, subject: str
) -> tuple[str | None, dict | None]:
    """Return ``(default_filename, face_rect)`` for one subject folder.

    An absent manifest yields ``(None, None)`` silently (the documented
    fallback). Any violation (unreadable, symlinked, non-JSON, not an object,
    unexpected keys, a ``default`` naming anything not in the eligible image
    set, an invalid ``face_rect``) yields ``(None, None)`` after EXACTLY ONE
    diagnostic: an invalid manifest degrades whole, never partially, so the
    sorted-name candidate and the API-filled shared rectangle apply.
    """
    if not manifest.exists() and not manifest.is_symlink():
        return None, None
    if not _is_regular_file(manifest):
        diagnostics.emit("manifest_unreadable", subject=subject)
        return None, None
    try:
        raw = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # observability: ignore R2: an unreadable manifest degrades whole via the diagnostic below
        diagnostics.emit("manifest_unreadable", subject=subject)
        return None, None
    if not isinstance(raw, dict) or not set(raw) <= {"default", "face_rect"}:
        diagnostics.emit("manifest_not_a_valid_object", subject=subject)
        return None, None
    face_rect = None
    if "face_rect" in raw:
        try:
            face_rect = validate_face_rect(raw["face_rect"])
        except GalleryRecordError:
            diagnostics.emit("manifest_invalid_face_rect", subject=subject)
            return None, None
    default_name = raw.get("default")
    if default_name is None:
        return None, face_rect
    if not isinstance(default_name, str) or default_name not in eligible_names:
        diagnostics.emit("manifest_default_not_an_eligible_file", subject=subject)
        return None, None
    return default_name, face_rect


def _raw_occupancy(subject: ArtSubject) -> tuple[int, set[str]]:
    """``(raw entry count, raw image ids)`` of the subject's record.

    Read directly from the record, never through the tolerant ``cards_for``:
    a malformed stored entry still OCCUPIES the record (a monster append
    would replace it, a duplicate id would corrupt it), so the never-replace
    guarantee and the duplicate-id check must both see it. The tolerant read
    would also emit unrelated invalid-card events on every sync.
    """
    record = record_for(subject)
    if record is None:
        return 0, set()
    cards = list(record.db.cards or [])
    ids = {
        entry["image_id"]
        for entry in cards
        if isinstance(entry, dict) and isinstance(entry.get("image_id"), str)
    }
    return len(cards), ids


def _has_raw_default(subject: ArtSubject) -> bool:
    """True when the subject already names a default (raw read, tolerant)."""
    record = record_for(subject)
    return record is not None and record.db.default_image_id is not None


def _sync_subject(
    kind_directory: str,
    kind: ArtSubjectKind,
    subject_dir: Path,
    diagnostics: _Diagnostics,
    counters: dict[str, int],
) -> None:
    """Synchronize one ``<kind-dir>/<subject-key>/`` folder; never raises."""
    try:
        subject = ArtSubject(kind, subject_dir.name)
    except ArtSubjectError:  # observability: ignore R2: reported through the bounded diagnostic emitter below
        diagnostics.emit(
            "invalid_subject_key_skipped", kind=kind_directory, entry=subject_dir.name
        )
        return
    subject_key = subject.full()
    entries = _child_entries(subject_dir)
    if entries is None:
        diagnostics.emit("subject_directory_unreadable", subject=subject_key)
        return
    images: list[Path] = []
    for entry in entries:
        if entry.name == MANIFEST_FILENAME:
            continue
        if entry.is_dir():
            diagnostics.emit("nested_directory_skipped", subject=subject_key, entry=entry.name)
        elif entry.is_symlink():
            diagnostics.emit("symlink_skipped", subject=subject_key, entry=entry.name)
        elif not entry.is_file():
            diagnostics.emit("non_regular_entry_skipped", subject=subject_key, entry=entry.name)
        elif entry.suffix not in STORE_EXTENSIONS:
            diagnostics.emit(
                "unsupported_extension_skipped", subject=subject_key, entry=entry.name
            )
        else:
            images.append(entry)
    if not images:
        return
    default_name, face_rect = _parse_manifest(
        subject_dir / MANIFEST_FILENAME, {image.name for image in images}, diagnostics, subject_key
    )
    candidate_name = default_name or images[0].name
    raw_count, existing_ids = _raw_occupancy(subject)
    had_default = _has_raw_default(subject)

    if kind is ArtSubjectKind.MONSTER and raw_count > 0:
        # append_card REPLACES a full monster record: the never-replace
        # guarantee forbids touching a subject whose raw list holds any entry,
        # malformed included. Files whose card is already present are the
        # ordinary no-op; the rest count as blocked and earn ONE diagnostic
        # only when something genuinely could not be honored.
        blocked = sum(
            1
            for image in images
            if derive_image_id(f"{kind_directory}/{subject.key}/{image.name}") not in existing_ids
        )
        counters["monster_cap_skipped"] += blocked
        if blocked:
            diagnostics.emit("monster_card_present_skipped", subject=subject_key, blocked=blocked)
        return

    for image in images:
        image_id = derive_image_id(f"{kind_directory}/{subject.key}/{image.name}")
        if image_id in existing_ids:
            counters["already_present"] += 1
            continue
        if kind is ArtSubjectKind.MONSTER and image.name != candidate_name:
            # The monster one-card cap: only the candidate file may ever be
            # appended for this subject.
            counters["monster_cap_skipped"] += 1
            diagnostics.emit("monster_cap_skipped", subject=subject_key, entry=image.name)
            continue
        identity = (
            f"gallery/{kind_directory}/{subject.key}/{image_id}{image.suffix}"
        )
        destination = resolved_under_store_root(identity)
        if destination is None:
            diagnostics.emit(
                "identity_refused_by_confinement", subject=subject_key, entry=image.name
            )
            continue
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.is_symlink() or destination.is_dir():
                diagnostics.emit("destination_refused", subject=subject_key, entry=image.name)
                continue
            # The destination is unreferenced (its card is absent), so the
            # seed bytes are always (re)written before the card is published —
            # a stale or tampered orphan can never be served under a fresh
            # seed card, and a copy that died before the append self-heals.
            shutil.copyfile(image, destination)
            counters["copied"] += 1
        except OSError:  # observability: ignore R2: reported through the bounded diagnostic emitter below
            diagnostics.emit("copy_failed", subject=subject_key, entry=image.name)
            continue
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
            diagnostics.emit("card_append_rejected", subject=subject_key, entry=image.name)
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
    from traversal — an unset, absent, or unreadable root emits exactly one
    skip event and returns; every admitted root ends in exactly one summary
    event (plus bounded diagnostics). The outermost catch exists only for
    unforeseen faults: a seed tree is never a startup failure, so nothing
    ever raises out of here.
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
        if not root.is_dir():
            log_warn(
                SEED_SYNC_EVENT,
                context={"phase": "skip", "reason": "seed_root_absent", "root": configured},
            )
            return {"skipped": True, **counters}
        kind_entries = _child_entries(root)
        if kind_entries is None:
            log_warn(
                SEED_SYNC_EVENT,
                context={"phase": "skip", "reason": "seed_root_unreadable", "root": configured},
            )
            return {"skipped": True, **counters}
        for kind_entry in kind_entries:
            kind = _KIND_DIRECTORIES.get(kind_entry.name)
            if kind is None:
                if _is_plain_dir(kind_entry) or kind_entry.is_dir():
                    diagnostics.emit("unknown_kind_directory_skipped", entry=kind_entry.name)
                continue
            if not _is_plain_dir(kind_entry):
                diagnostics.emit(
                    "symlinked_kind_directory_skipped", kind=kind_entry.name
                )
                continue
            subject_entries = _child_entries(kind_entry)
            if subject_entries is None:
                diagnostics.emit("kind_directory_unreadable", kind=kind_entry.name)
                continue
            for subject_dir in subject_entries:
                if not subject_dir.is_dir():
                    continue
                if not _is_plain_dir(subject_dir):
                    diagnostics.emit(
                        "symlinked_subject_directory_skipped",
                        kind=kind_entry.name,
                        entry=subject_dir.name,
                    )
                    continue
                counters["subjects"] += 1
                _sync_subject(kind_entry.name, kind, subject_dir, diagnostics, counters)
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
