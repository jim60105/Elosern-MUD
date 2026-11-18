"""Per-image gallery job queue and the shared serialization lock.

One ``GalleryJobRecord`` exists per REQUESTED IMAGE, keyed
``art:<full-subject-key>:gen:<image-id>``. Scenes and portraits share exactly
one process-wide ``queue_lock`` and one worker concurrency slot. Every job
write happens under that lock: enqueue, claim, lease reclaim and settle. The
external worker subprocess never runs under the lock -- it executes on a
background Twisted thread -- so concurrent drains, ``@art`` commands, and
``on_commit`` enqueues serialize on fast DB transactions only.

The queue carries no subject-keyed record: an automatic idempotency decision
belongs to the shared gallery guard (``service.py``), and a gallery job is
deleted the moment it reaches a terminal settle (a card append on success, a
recorded gallery error on failure). Settles resolve the record by its own job
key, never re-derived from the subject.
"""

import hashlib
import math
import os
import threading
import time
import uuid
from pathlib import Path

from django.conf import settings
from django.db import transaction
from evennia.utils.create import create_script

from world.art import gallery as gallery_api
from world.art import gallery_kinds
from world.art.paths import resolved_under_store_root
from world.art.sd_worker import prompt_digest
from world.art.store import ArtAssetStatus, GalleryJobRecord
from world.art.subjects import (
    ArtSubject,
    ArtSubjectError,
    ArtSubjectKind,
    parse_subject,
)
from world.lore.monster_visuals import is_registered_monster_visual_key
from world.prompts.loader import PromptLibraryError

# The single shared serialization lock for every scene and portrait operation.
queue_lock = threading.Lock()

MAX_PENDING_GALLERY_JOBS = 8


def pending_gallery_jobs(subject: ArtSubject) -> list[dict]:
    """Read at most eight newest in-flight image identities without settlement."""
    with queue_lock:
        rows = {}
        records = GalleryJobRecord.objects.filter(
            db_key__startswith=f"{record_key(subject)}:gen:"
        ).order_by("pk")
        for record in records.iterator():
            image_id = record.db.gallery_image_id
            timestamp = record.db.enqueued_at
            if (
                record.db.kind != subject.kind.value
                or record.db.subject_key != subject.key
                or record.db.status not in (ArtAssetStatus.PENDING, ArtAssetStatus.IN_PROGRESS)
                or gallery_api._canonical_uuid_text(image_id) is None
                or record.key != gallery_record_key(subject, image_id)
                or isinstance(timestamp, bool)
                or not isinstance(timestamp, (int, float))
                or abs(timestamp) > 2**53 - 1
                or not math.isfinite(timestamp)
            ):
                continue
            if image_id in rows:
                continue
            if len(rows) == MAX_PENDING_GALLERY_JOBS:
                oldest = min(rows, key=lambda key: rows[key]["enqueued_at"])
                if timestamp <= rows[oldest]["enqueued_at"]:
                    continue
                del rows[oldest]
            rows[image_id] = {"image_id": image_id, "enqueued_at": timestamp}
        return sorted(
            rows.values(), key=lambda row: -row["enqueued_at"]
        )[:MAX_PENDING_GALLERY_JOBS]


def record_key(subject: ArtSubject) -> str:
    """The job-key prefix of one subject; never read or created as a record."""
    return f"art:{subject.full()}"


def gallery_record_key(subject: ArtSubject, image_id: str) -> str:
    """The script key of one requested gallery image (per-request unique)."""
    return f"{record_key(subject)}:gen:{image_id}"


def is_gallery_job(record: object) -> bool:
    """True when ``record`` is a well-formed per-image gallery job.

    A foreign record, an empty image id, or a job key that does not name its
    own image id is not a gallery job. Never an unconditional compatibility
    stub: malformed synthetic records must fail this check.
    """
    if not isinstance(record, GalleryJobRecord):
        return False
    image_id = str(record.db.gallery_image_id or "")
    key = str(record.db_key or "")
    return bool(image_id) and bool(key) and key.startswith("art:") and key.endswith(
        f":gen:{image_id}"
    )


def _gallery_job_in_flight_locked(subject: ArtSubject) -> bool:
    """The in-flight read without lock acquisition (an already-serialized caller).

    Only ``world.art.service``'s serialized mutation seam may use this: every
    public caller goes through :func:`gallery_job_in_flight`, which owns the
    lock. The question it answers is identical.
    """
    return any(
        record.db.kind == subject.kind.value
        and record.db.subject_key == subject.key
        and record.db.status in (ArtAssetStatus.PENDING, ArtAssetStatus.IN_PROGRESS)
        for record in _all_records()
        if is_gallery_job(record)
    )


def gallery_job_in_flight(subject: ArtSubject) -> bool:
    """True when a pending or in-progress gallery job exists for the subject.

    The automatic-generation guard's in-flight half: a spent job is marked
    terminal before it is deleted and a failed settle deletes its record, so
    ``pending``/``in_progress`` are exactly the live requests. A leftover
    terminal record is spent work the startup prune reclaims -- it never
    blocks a later automatic request.
    """
    with queue_lock:
        return _gallery_job_in_flight_locked(subject)


def gallery_image_pending(subject: ArtSubject, image_id: str) -> bool:
    """True when the exact requested image of ``subject`` is still live work.

    A read of the one job record keyed by ``(subject, image_id)``: pending or
    in progress and naming exactly this subject. Used by read-only presenters
    that already hold the requested image id, so no subject-wide scan is
    needed; nothing here claims, settles or creates a record.
    """
    if gallery_api._canonical_uuid_text(image_id) is None:
        return False
    with queue_lock:
        record = (
            GalleryJobRecord.objects.filter(db_key=gallery_record_key(subject, image_id))
            .order_by("pk")
            .first()
        )
        return bool(
            record is not None
            and is_gallery_job(record)
            and record.db.kind == subject.kind.value
            and record.db.subject_key == subject.key
            and record.db.gallery_image_id == image_id
            and record.db.status in (ArtAssetStatus.PENDING, ArtAssetStatus.IN_PROGRESS)
        )


def source_hash(description: str) -> str:
    """Deterministic sha256 of the canonical subject description."""
    return hashlib.sha256(description.encode("utf-8")).hexdigest()


def _prompt_digest_or_empty(subject: ArtSubject, description: str) -> str:
    """The rendered-prompt digest, or an empty sentinel when the library is broken.

    The digest is sha256 of the rendered positive+negative prompt pair. A
    broken prompt library (an admin mid-edit, an unreadable file) must never
    block an enqueue, so the failure degrades to an empty digest.
    """
    try:
        return prompt_digest(subject, description)
    except PromptLibraryError:
        return ""


def _all_records() -> list[GalleryJobRecord]:
    return list(GalleryJobRecord.objects.all())


def expected_gallery_identity(record: GalleryJobRecord) -> str | None:
    """The one per-image store identity a claimed job may publish, or ``None``.

    Derived from the job's own validated typed metadata: invalid kind/subject
    or an empty image id yields ``None`` (the publication is rejected), never
    a fixed fallback path.
    """
    image_id = str(record.db.gallery_image_id or "")
    kind = str(record.db.kind or "")
    subject_key = str(record.db.subject_key or "")
    if not image_id or not kind or not subject_key:
        return None
    try:
        parse_subject(f"{kind}:{subject_key}")
        directory = gallery_kinds.store_directory_for(kind)
    except (ArtSubjectError, KeyError):
        return None
    extension = str(settings.ART_SD_OUTPUT_EXTENSION)
    return f"gallery/{directory}/{subject_key}/{image_id}{extension}"


def _membership_is_current(record: GalleryJobRecord) -> bool:
    """True when the job's persisted subject still parses and is registered.

    A retired monster visual species (or an unparseable row) can never claim
    or publish again.
    """
    try:
        subject = parse_subject(f"{record.db.kind}:{record.db.subject_key}")
    except ArtSubjectError:
        return False
    if subject.kind is ArtSubjectKind.MONSTER and not is_registered_monster_visual_key(
        subject.key
    ):
        return False
    return True


def _validate_enqueue_subject(subject: ArtSubject) -> None:
    """The one refusal every enqueue entry applies before its write."""
    if not gallery_kinds.has_gallery(subject.kind.value):
        raise gallery_api.GalleryRecordError(
            f"subject kind {subject.kind.value!r} declares no gallery"
        )
    if subject.kind is ArtSubjectKind.MONSTER and not is_registered_monster_visual_key(
        subject.key
    ):
        raise gallery_api.GalleryRecordError(
            f"monster subject {subject.key!r} is not a registered visual species"
        )


def _enqueue_gallery_job_locked(
    subject: ArtSubject,
    description: str,
    *,
    image_id: str,
    binding: dict | None,
    face_rect: dict | None,
    requested_fields: list,
    replacement_image_id: str | None = None,
    creation_draft: bool = False,
) -> GalleryJobRecord:
    """Create one per-image job without lock acquisition (already-serialized caller).

    Only ``world.art.service``'s serialized mutation seam uses this; every
    public caller goes through :func:`enqueue_gallery_job`, which owns the lock.
    The enqueue rules are exactly the public wrapper's, plus the optional
    server-authorized ``replacement_image_id`` metadata a draft portrait request
    records so settlement can replace exactly its own previous creation image.
    """
    _validate_enqueue_subject(subject)
    digest = source_hash(description)
    record = create_script(
        GalleryJobRecord,
        key=gallery_record_key(subject, image_id),
        persistent=True,
        interval=0,
    )
    record.db.kind = subject.kind.value
    record.db.subject_key = subject.key
    record.db.gallery_image_id = image_id
    record.db.gallery_binding = binding
    record.db.gallery_face_rect = face_rect
    record.db.gallery_requested_fields = list(requested_fields)
    record.db.gallery_replacement_image_id = replacement_image_id
    record.db.gallery_creation_draft = creation_draft
    record.db.source_description = description
    record.db.source_hash = digest
    record.db.prompt_digest = _prompt_digest_or_empty(subject, description)
    record.db.aspect_ratio = _aspect_ratio_for(subject)
    record.db.status = ArtAssetStatus.PENDING
    record.db.enqueued_at = time.time()
    return record


def enqueue_gallery_job(
    subject: ArtSubject,
    description: str,
    *,
    image_id: str,
    binding: dict | None,
    face_rect: dict | None,
    requested_fields: list,
) -> GalleryJobRecord:
    """Create exactly one per-image gallery job record under the queue lock.

    There is deliberately NO find-or-create and NO consolidation here: every
    call is one requested image with its own freshly minted ``image_id``, and
    two requests for one subject MUST produce two independent jobs. The
    record carries the pending card's binding, face rectangle, and requested
    field ids verbatim (validated upstream at the service boundary) and never
    an output identity -- its published artifact is a gallery card. A kind
    whose declaration grants no gallery, or an unregistered monster key, is
    refused before any write.
    """
    with queue_lock:
        return _enqueue_gallery_job_locked(
            subject,
            description,
            image_id=image_id,
            binding=binding,
            face_rect=face_rect,
            requested_fields=requested_fields,
        )


def claim(limit: int) -> list[GalleryJobRecord]:
    """Claim up to ``limit`` pending gallery jobs under the lock.

    Each claimed job becomes ``in_progress`` with a ``claimed_at`` lease,
    a fresh generation token, and an incremented attempt count. The lock is
    released before any worker work.
    """
    with queue_lock:
        pending = [
            record
            for record in _all_records()
            if is_gallery_job(record) and record.db.status == ArtAssetStatus.PENDING
        ]
        # Filter out retired monster subjects that do not match registered
        # visual species before any work is claimed for them.
        pending = [record for record in pending if _membership_is_current(record)]
        pending.sort(key=lambda record: record.db.enqueued_at or 0.0)
        claimed = pending[: max(limit, 0)]
        now = time.time()
        for record in claimed:
            record.db.status = ArtAssetStatus.IN_PROGRESS
            record.db.claimed_at = now
            record.db.attempt_count = int(record.db.attempt_count or 0) + 1
            record.db.last_error_code = None
            record.db.generation_token = uuid.uuid4().hex
        return claimed


def reclaim_expired_leases(timeout: float) -> int:
    """Reclaim ``in_progress`` gallery jobs whose lease has expired to ``pending``.

    A crashed or timed-out worker never leaves a job stuck.
    """
    now = time.time()
    reclaimed = 0
    with queue_lock:
        for record in _all_records():
            if not is_gallery_job(record):
                continue
            if record.db.status != ArtAssetStatus.IN_PROGRESS:
                continue
            claimed_at = record.db.claimed_at
            if claimed_at is None or now - float(claimed_at) >= timeout:
                record.db.status = ArtAssetStatus.PENDING
                record.db.claimed_at = None
                reclaimed += 1
    return reclaimed


def _record_by_db_key(db_key: str) -> GalleryJobRecord | None:
    """Resolve one job by its OWN stored key (never re-derived)."""
    return GalleryJobRecord.objects.filter(db_key=db_key).first()


def _remove_tmp(tmp_path: str) -> None:
    """Best-effort removal of a stale or failed temporary output file."""
    try:
        os.unlink(tmp_path)
    except OSError:
        pass


def _gallery_subject(record: GalleryJobRecord) -> ArtSubject:
    """Rebuild a gallery job record's typed subject from its persisted fields."""
    return parse_subject(f"{record.db.kind}:{record.db.subject_key}")


def settle_gallery_generated(
    job_key: str,
    *,
    generation_token: str,
    output_identity: str,
    tmp_path: str,
    prompt: dict,
    seed: int | None,
    checkpoint: str | None,
    image_size: dict[str, int] | None = None,
) -> dict | None:
    """Publish one generated gallery image as exactly one card append.

    Under the queue lock, while the claim's generation token is still
    current: validate that ``output_identity`` is the job's EXACT per-image
    identity and confined under the store root, atomically replace the
    temporary file onto it, THEN append the card through
    ``world/art/gallery.py`` (file write before card append, so an
    interruption leaves an orphan FILE reclaimed by the startup prune, never
    a card pointing at a missing file), and delete the spent job record. The
    card carries the verbatim prompt pair and server-reported seed from the
    returned generation, the configured checkpoint when one is set, and the
    job record's pending binding, face rectangle, and requested field ids.

    A job carrying server-authorized replacement metadata (the pending
    character's draft portrait) publishes through the gallery's one replacement
    helper inside the same database transaction: the new card becomes the
    default and exactly the named previous creation card is dropped, while
    unrelated cards and official preferences stay untouched. Removed card
    files are unlinked only after the transaction committed, the queue lock
    was released, and the gallery lock was released. A failed generation never
    reaches this path, so its previous card and default survive.

    A gallery job with no replacement metadata deletes NO prior file: a capped
    gallery's own append handles its displaced unreferenced file. Lock order is
    ``queue_lock -> database transaction -> gallery_lock`` (the only allowed
    order; ``gallery.py`` never acquires ``queue_lock``).

    Returns the stored card dict, or ``None`` for a stale claim (the
    temporary file is removed first). A wrong, escaping, or malformed
    identity removes the temporary file and raises; no out-of-root file or
    card is written. A record whose persisted kind/subject no longer parses
    or whose species is no longer registered is spent work that can never
    append: its (un-rewound) published file stays an orphan for the startup
    prune, the record is deleted, and the settle reports ``None`` rather than
    raising inside the queue lock.
    """
    removed_identities: list = []
    stored: dict | None = None
    with queue_lock:
        record = _record_by_db_key(job_key)
        if record is None or not is_gallery_job(record):
            _remove_tmp(tmp_path)
            return None
        if not _membership_is_current(record):
            _remove_tmp(tmp_path)
            _finish_gallery_job(record, ArtAssetStatus.FAILED)
            return None
        if (
            record.db.status != ArtAssetStatus.IN_PROGRESS
            or record.db.generation_token != generation_token
        ):
            _remove_tmp(tmp_path)
            return None
        expected = expected_gallery_identity(record)
        if expected is None or output_identity != expected:
            _remove_tmp(tmp_path)
            raise ValueError(
                f"output identity {output_identity!r} is not the job's per-image identity"
            )
        target = resolved_under_store_root(output_identity)
        if target is None:
            _remove_tmp(tmp_path)
            raise ValueError(
                f"gallery identity {output_identity!r} escapes the store root"
            )
        try:
            os.replace(tmp_path, target)
        except BaseException:
            _remove_tmp(tmp_path)
            raise
        try:
            subject = _gallery_subject(record)
        except ArtSubjectError:  # corrupt record: it can never resolve a gallery
            _finish_gallery_job(record, ArtAssetStatus.FAILED)
            return None
        card_fields: dict = {
            "image_id": str(record.db.gallery_image_id),
            "stored_identity": output_identity,
            "prompt": prompt,
            "seed": seed,
            "checkpoint": checkpoint or None,
            "requested_fields": list(record.db.gallery_requested_fields or []),
            "binding": record.db.gallery_binding,
            "image_size": image_size,
            "source": "generated",
        }
        face_rect = record.db.gallery_face_rect
        if face_rect:
            if image_size is not None:
                gallery_api.validate_face_rect(face_rect, image_size=image_size)
            card_fields["face_rect"] = face_rect
        replacement_image_id = record.db.gallery_replacement_image_id
        creation_draft = bool(record.db.gallery_creation_draft)
        card_snapshot = gallery_api.card_state_snapshot(subject)
        job_status_before = record.db.status
        try:
            with transaction.atomic():
                if creation_draft:
                    # A creation-draft settlement ALWAYS takes default
                    # ownership, even with no previous creation card, so an
                    # unrelated gallery default can never keep presenting over
                    # the portrait the player just requested.
                    stored, removed_identities = gallery_api.append_replacement_card(
                        subject,
                        replaced_image_id=replacement_image_id,
                        **card_fields,
                    )
                else:
                    stored = gallery_api.append_card(subject, **card_fields)
                # The recorded error describes the LAST generation attempt, so a
                # successful append clears it. Non-authoritative like the
                # terminal marking below: the appended card is the publish, and
                # a failed clear must never rewrite this settle's outcome.
                try:
                    gallery_api.clear_error(subject)
                except Exception:  # noqa: BLE001 - the appended card is authoritative
                    pass
                # The card append is the authoritative publish: a failure
                # deleting the spent record afterwards must never rewrite this
                # settle's outcome; the terminal marking below keeps it
                # unclaimable.
                _finish_gallery_job(record, ArtAssetStatus.DONE)
        except BaseException:
            # Nothing from this settlement committed: no card was appended and
            # no previous card was dropped, so no file may be unlinked. The
            # idmapped attribute values the rolled-back writes replaced stay
            # readable in process, so they are written back to the snapshot.
            removed_identities = []
            gallery_api.restore_card_state(card_snapshot)
            try:
                record.db.status = job_status_before
            except Exception:  # noqa: BLE001 - diagnostic state only
                pass
            raise
    # Committed removals are unlinked only now: the database transaction
    # committed, and both the queue and gallery serialization were released.
    for identity in removed_identities:
        gallery_api.unlink_stored_file(subject, identity)
    return stored


def settle_gallery_failed(
    job_key: str, *, generation_token: str, error: str | None
) -> ArtSubject | None:
    """Terminal failure for a gallery job: no card, bounded code, spent record gone.

    While the claim is still current, records the bounded error code (and its
    timestamp) on the subject's gallery record through the gallery write API
    -- every existing card stays intact, NO card is appended -- then deletes
    the spent job record. A job whose persisted subject no longer resolves or
    whose species is no longer registered is deleted without recording an
    error (its gallery cannot be addressed). A stale claim (missing record,
    requeued, reclaimed, or token mismatch) is a side-effect-free no-op
    returning ``None``.
    """
    with queue_lock:
        record = _record_by_db_key(job_key)
        if record is None or not is_gallery_job(record):
            return None
        if (
            record.db.status != ArtAssetStatus.IN_PROGRESS
            or record.db.generation_token != generation_token
        ):
            return None
        if not _membership_is_current(record):
            _finish_gallery_job(record, ArtAssetStatus.FAILED)
            return None
        try:
            subject = _gallery_subject(record)
        except ArtSubjectError:  # corrupt record: nowhere to record the error
            _finish_gallery_job(record, ArtAssetStatus.FAILED)
            return None
        gallery_api.record_error(subject, error or "settle_error")
        _finish_gallery_job(record, ArtAssetStatus.FAILED)
        return subject


def _finish_gallery_job(record: GalleryJobRecord, status: str) -> None:
    """Mark a spent gallery job terminal, then delete it (both best-effort).

    The card append (or failed settle) already decided this job's outcome.
    Marking the terminal status first keeps the record unclaimable even when
    the delete fails: claim and lease reclaim only touch pending/in-progress
    work, and the startup prune sweeps terminal gallery jobs, so a lost delete
    delays cleanup and can never re-publish. A save that also fails leaves an
    in-progress record with a live token, which the shared reclaim re-runs
    once and self-settles as a rejected duplicate -- bounded, never corrupt.
    """
    try:
        record.db.status = status
        record.save()
    except Exception:  # noqa: BLE001 - the reclaim self-heals this DB-failure corner
        pass
    try:
        record.delete()
    except Exception:  # noqa: BLE001 - the retained terminal record is pruned at startup
        pass


def failed_keys() -> list[str]:
    """Canonical subject keys whose last gallery generation attempt failed.

    Read from the gallery error accessor: a terminal job is deleted, so
    deleted job ids are never a retry database. Unique and sorted.
    """
    with queue_lock:
        return sorted(
            {state.subject.full() for state in gallery_api.erroring_subjects()}
        )


def _aspect_ratio_for(subject: ArtSubject) -> str:
    return "16:9" if subject.kind.value == "scene" else "3:4"
