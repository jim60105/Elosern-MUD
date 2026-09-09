"""The sole writer of art asset/queue records and its deterministic seams.

``world/art/service.py`` owns every write to asset/queue records (design D1).
Presenters, workers, browsers, and ``world/ai`` never write them. The seams
reachable from gameplay are all deterministic:

- ``art_sync_all()`` -- idempotent startup sync of scene + generic-monster
  subjects and recovery of explicit named portrait policies.
- ``schedule_portrait_ensure(entity)`` -- post-commit portrait ensure for a
  player-created or validated-import character.
- ``ensure_scene_asset(archetype)`` -- room-entry scene ensure.
- ``schedule_occupant_portrait(occupant)`` -- post-commit named-NPC spawn
  ensure (SceneBuilder seam).

Every seam is failure-isolated: an art failure logs a bounded diagnostic and
never rolls back creation, import, spawn, or movement (design D7).

Gallery generation (change ``gallery-generation-jobs``) adds two seams:
``request_gallery_image`` — the only gameplay-reachable entry point that
queues a gallery generation, validating subject/binding/rect BEFORE any
queue write and never consulting the connectivity probe (the connectivity
import boundary holds package-wide) — and ``prune_gallery_orphans``, the
idempotent startup reclaim of orphan gallery files and unclaimable gallery
job records.

The automatic character-portrait retrofit (change ``gallery-autogen-retrofit``)
routes every automatic path — creation, validated import, named-NPC spawn,
startup recovery, staff retry — and the staff character requeue through
``request_gallery_image`` as one unbound appearance-only card with the shared
default face rectangle: a character subject never writes a classic
fixed-identity record. Automatic paths request only when the subject's gallery
holds no card and no gallery job is in flight; ``@art requeue`` is the one
force path that bypasses that guard. Scenes and monster tiers stay on the
classic subject-keyed pipeline.
"""

import uuid
from pathlib import Path

from django.conf import settings
from django.db import transaction

from world.observability import log_error, log_info, log_warn

from world.art import gallery as gallery_api
from world.art.paths import resolved_under_store_root
from world.art.queue import (
    ensure as queue_ensure,
    enqueue_gallery_job,
    gallery_job_in_flight,
    is_gallery_job,
)
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import (
    ArtSubjectError,
    character_ages,
    character_subject_for,
    description_for,
    parse_subject,
    monster_subject_for,
    scene_subject_for,
)
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY


def _gallery_auto_generation_pending(subject) -> bool:
    """True when the subject's gallery already occupies it: any card or an in-flight job.

    The automatic-generation idempotency guard (change ``gallery-autogen-retrofit``):
    a subject whose gallery holds any card — generated, seed-synced, or
    player-kept — or whose generation is already pending/in-progress is left
    alone. ``cards_for`` is the tolerant valid-card read, so a malformed entry
    (ignored by every read, never resolvable) never blocks a real generation.
    """
    if gallery_api.cards_for(subject):
        return True
    return gallery_job_in_flight(subject)


def _ensure_character_portrait(entity) -> bool:
    """Validate ages, then request one automatic gallery card when the gallery warrants it.

    Returns True when a gallery generation was requested, False when the
    gallery guard suppressed the automatic path. Reads the canonical age pair
    immediately before the request for every portrait subject (design D3):
    a rejection is deterministic and produces no record, no prompt, and no
    worker call. The request itself is the gallery seam — one unbound card
    built from the subject's standard deterministic description with the
    shared default face rectangle; a character subject never writes a classic
    fixed-identity record on an automatic path.
    """
    subject = character_subject_for(entity)
    if subject is None:
        return False
    character_ages(entity)
    if _gallery_auto_generation_pending(subject):
        return False
    request_gallery_image(entity, face_rect=dict(gallery_api.DEFAULT_FACE_RECT))
    return True


def _ages_eligible_at_schedule(entity) -> bool:
    """Check canonical ages at schedule time; return False if ineligible.

    The spec requires the age check at schedule time *and* again immediately
    before the queue write. A rejection at schedule time logs the named
    diagnostic and no record/prompt/job is ever produced; a later correction
    re-enables the next lifecycle attempt.
    """
    try:
        character_ages(entity)
    except ArtSubjectError as error:
        log_info("art_portrait_skipped", context={"stage": "schedule"}, exc=error)
        return False
    return True


def schedule_portrait_ensure(entity) -> None:
    """Register an exception-safe post-commit portrait ensure for an entity.

    The canonical-age check runs at schedule time; if it rejects, nothing is
    scheduled and no record is produced. Otherwise ``transaction.on_commit``
    registers the ensure, which re-checks the ages immediately before the queue
    write.
    Django runs on_commit callbacks synchronously on the committing thread
    after commit, so the callback catches every art error and never
    propagates: a committed creation or import is always reported as success
    (design D7).
    """
    if not _ages_eligible_at_schedule(entity):
        return

    def _safe():
        try:
            _ensure_character_portrait(entity)
        except ArtSubjectError as error:
            log_info("art_portrait_skipped", context={"stage": "ensure"}, exc=error)
        except Exception as error:  # noqa: BLE001 - bounded, never propagates
            log_warn("art_portrait_ensure_failed", context={"entity": entity.key}, exc=error)

    transaction.on_commit(_safe)


def schedule_occupant_portrait(occupant) -> None:
    """Register the post-commit portrait ensure for a spawned occupant.

    Called from the SceneBuilder spawn path only for an occupant carrying an
    explicit named portrait policy (design D9); the on_commit callback fires
    only after the materialization transaction commits, so an art failure can
    never roll back a materialized scene.
    """
    schedule_portrait_ensure(occupant)


def _living_entity_for_stable_key(stable_key: str):
    """Return the living entity carrying an explicit named policy for a key."""
    from evennia.objects.models import ObjectDB

    from typeclasses.entities import LivingEntity

    for entity in ObjectDB.objects.all():
        if not isinstance(entity, LivingEntity):
            continue
        try:
            subject = character_subject_for(entity)
        except ArtSubjectError:  # observability: ignore R2: scan skip; the unpaired entity yields no portrait request
            continue
        if subject is not None and subject.key == stable_key:
            return entity
    return None


def retry_character_portrait(stable_key: str) -> bool:
    """Re-attempt one character portrait through the age check and the gallery guard.

    The subject is re-derived from the living entity that owns the explicit
    named policy for ``stable_key`` and the ages are re-checked; an unknown key,
    a missing entity, or an ineligible character is a named rejection with no
    record change (staff retry path, design D3). Returns True only when a
    gallery generation was actually requested, so ``@art retry`` counts
    truthfully when the guard leaves an already-carded subject alone.
    """
    entity = _living_entity_for_stable_key(stable_key)
    if entity is None:
        raise ArtSubjectError(
            f"no living character carries portrait stable_key {stable_key!r}"
        )
    return _ensure_character_portrait(entity)


def requeue_character_portrait(stable_key: str) -> None:
    """Force-regenerate one character portrait through the age check and the gallery.

    Resolves the owning entity and re-checks the canonical ages before issuing
    exactly one gallery generation request — appending a new card on success
    and never replacing an existing one. Requeue is the staff force path: it
    deliberately bypasses the automatic-generation idempotency guard, so a
    subject that already holds cards still gets one new generation. An unknown
    key or an ineligible character is a named rejection with no record change
    (staff requeue path, design D3). A character subject never writes a
    classic fixed-identity record here.
    """
    entity = _living_entity_for_stable_key(stable_key)
    if entity is None:
        raise ArtSubjectError(
            f"no living character carries portrait stable_key {stable_key!r}"
        )
    character_ages(entity)
    request_gallery_image(entity, face_rect=dict(gallery_api.DEFAULT_FACE_RECT))


def ensure_scene_asset(archetype) -> None:
    """Ensure the scene asset record for a validated archetype (idempotent).

    ``None`` or an unresolvable archetype is a side-effect-free no-op. Art
    failures are bounded and never block the player's move.
    """
    if archetype is None or archetype not in SCENE_ARCHETYPE_REGISTRY:
        return
    try:
        subject = scene_subject_for(archetype)
        description = description_for(subject)
        queue_ensure(subject, description)
    except Exception as error:  # noqa: BLE001 - bounded, never blocks the move
        log_warn("art_scene_ensure_skipped", context={"archetype": archetype}, exc=error)


def _sync_registry_subjects() -> None:
    """Idempotently ensure a record for every scene and generic-monster subject."""
    for archetype in SCENE_ARCHETYPE_REGISTRY:
        try:
            subject = scene_subject_for(archetype)
            queue_ensure(subject, description_for(subject))
        except ArtSubjectError as error:
            log_warn("art_startup_sync_skipped", context={"kind": "scene", "key": archetype}, exc=error)
    for tier in MONSTER_TIER_REGISTRY:
        try:
            subject = monster_subject_for(tier)
            queue_ensure(subject, description_for(subject))
        except ArtSubjectError as error:
            log_warn("art_startup_sync_skipped", context={"kind": "monster", "key": tier}, exc=error)


def _recover_named_portraits() -> None:
    """Rescan living characters with an explicit named policy and ensure them.

    Recovers an enqueue that failed after an earlier gameplay commit. The
    canonical-age check re-runs; a permanently ineligible subject is skipped
    with a diagnostic and never retried by a later recovery pass (design D7).
    The shared automatic-generation guard inside ``_ensure_character_portrait``
    restricts the recovery to subjects with an empty gallery and no in-flight
    job: a subject whose gallery already holds a card, or whose generation is
    already pending/in-progress, is left alone (change
    ``gallery-autogen-retrofit``).
    """
    from evennia.objects.models import ObjectDB

    from typeclasses.entities import LivingEntity

    for entity in ObjectDB.objects.all():
        if not isinstance(entity, LivingEntity):
            continue
        try:
            subject = character_subject_for(entity)
        except ArtSubjectError as error:
            log_warn("art_recovery_skipped", context={"kind": "subject", "key": entity.key}, exc=error)
            continue
        if subject is None:
            continue
        try:
            character_ages(entity)
        except ArtSubjectError as error:
            log_info("art_recovery_skipped", context={"kind": "portrait", "key": entity.key}, exc=error)
            continue
        _ensure_character_portrait(entity)


def art_sync_all() -> None:
    """Idempotent startup synchronization plus named-policy recovery.

    Ensures a record for every ``SCENE_ARCHETYPE_REGISTRY`` and every
    ``MONSTER_TIER_REGISTRY`` entry, then rescans living characters carrying an
    explicit named portrait policy. Every record write flows through the queue
    under the shared lock; a failure is bounded and never aborts startup.
    """
    try:
        _sync_registry_subjects()
    except Exception as error:  # pragma: no cover - defensive startup isolation
        log_error("art_startup_registry_sync_failed", context={"scope": "registry-sync"}, exc=error)
    try:
        _recover_named_portraits()
    except Exception as error:  # pragma: no cover - defensive startup isolation
        log_error("art_startup_recovery_failed", context={"scope": "portrait-recovery"}, exc=error)


def request_gallery_image(entity, *, binding=None, face_rect=None) -> str:
    """Validate, mint, and enqueue exactly one gallery image request.

    The ONLY gameplay-reachable entry point for gallery generation
    (change ``gallery-generation-jobs``). Derives the subject through the
    existing typed producer, re-checks the canonical age pair exactly as the
    classic portrait ensure does, and validates the binding and face
    rectangle through the ``world/art/gallery.py`` validators BEFORE any
    queue write — every rejection raises a typed error at this boundary and
    leaves no record, no file, no card, and no rendered prompt behind. The
    freshly minted lowercase-uuid ``image_id`` keys one independent job
    (two requests, two jobs).

    Deliberately never imports or consults ``world.art.connectivity``: an
    unreachable sd-webui server is a reported ``failed`` settle carrying its
    bounded named error code on the subject's gallery record (design §12.3.1),
    not a gate. The caller-side failure isolation is the existing post-commit
    pattern the auto-generation retrofit wires: because every rejection
    raises before any write, a wrapped call can never roll back committed
    gameplay. Returns the minted ``image_id``.
    """
    subject = character_subject_for(entity)
    if subject is None:
        raise ArtSubjectError(
            f"character {getattr(entity, 'key', entity)!r} carries no portrait subject"
        )
    age, _apparent_age = character_ages(entity)
    binding = gallery_api.validate_binding(binding)
    if face_rect is not None:
        face_rect = gallery_api.validate_face_rect(face_rect)
    image_id = str(uuid.uuid4())
    description = description_for(subject, entity=entity, age=age)
    # No field selection in this change: the requested-field provenance is
    # the empty list until gallery-prompt-composition introduces selection.
    enqueue_gallery_job(
        subject,
        description,
        image_id=image_id,
        binding=binding,
        face_rect=face_rect,
        requested_fields=[],
    )
    log_info(
        "gallery_generate",
        context={"subject": subject.full(), "image_id": image_id, "kind": subject.kind.value},
    )
    return image_id


def _gallery_job_is_unclaimable(record) -> bool:
    """True when a gallery job record can never be claimed or published again.

    A whose-subject-no-longer-resolves row and a row whose status is neither
    ``pending`` nor ``in_progress`` can never publish. A lease-expired
    ``in_progress`` job is RETAINED — reclaiming it to ``pending`` is the
    shared queue's lease-reclaim job, so a job whose worker died is retried,
    not silently dropped.
    """
    try:
        parse_subject(f"{record.db.kind}:{record.db.subject_key}")
    except ArtSubjectError as error:
        # The deletion decision is itself a bounded diagnostic.
        log_warn(
            "gallery_prune_unresolvable_subject",
            context={"job": record.db_key},
            exc=error,
        )
        return True
    status = str(record.db.status or "")
    return status not in (ArtAssetStatus.PENDING, ArtAssetStatus.IN_PROGRESS)


def prune_gallery_orphans() -> dict:
    """Idempotent startup reclaim of orphan gallery files and spent job records.

    Deletes every file under the store root's ``gallery/`` tree that no card
    of any gallery record references (read-only through the gallery API), and
    every gallery job record that can
    never be claimed or published again (unresolvable subject, or a status
    outside ``pending``/``in_progress``). Every path is resolved through the
    single store-root confinement helper, so nothing outside
    ``ART_STORE_ROOT`` is ever unlinked, and a referenced file is NEVER
    deleted. Every failure phase is bounded: an unreadable tree or a failing
    deletion is a named diagnostic and the prune continues; the function
    itself never raises, so startup never aborts because of it.

    Reads happen on the reactor thread during ``at_server_start``, before the
    scheduler can claim or publish anything — the gallery and queue locks are
    deliberately not taken here. A future mid-game re-use must take them.
    """
    files_deleted = 0
    records_deleted = 0
    referenced = None
    try:
        referenced = gallery_api.referenced_stored_identities()
    except Exception as error:  # noqa: BLE001 - bounded: skip the file phase, still prune records
        log_error("gallery_prune_failed", context={"phase": "references"}, exc=error)
    if referenced is not None:
        # Without the reference set NOTHING may be deleted: a prune must
        # never remove a file a card references, and an unreadable set cannot
        # prove non-reference for any file.
        try:
            gallery_root = Path(settings.ART_STORE_ROOT) / "gallery"
            if gallery_root.is_dir():
                store_root = Path(settings.ART_STORE_ROOT)
                for path in gallery_root.rglob("*"):
                    try:
                        if not path.is_file():
                            continue
                        identity = path.relative_to(store_root).as_posix()
                        if identity in referenced:
                            continue
                        if resolved_under_store_root(identity) is None:
                            continue
                        path.unlink()
                        files_deleted += 1
                    except OSError as error:
                        log_warn(
                            "gallery_prune_failed",
                            context={"phase": "file", "path": str(path)},
                            exc=error,
                        )
        except Exception as error:  # noqa: BLE001 - an unreadable tree never aborts the prune
            log_error("gallery_prune_failed", context={"phase": "tree"}, exc=error)
    try:
        for record in list(ArtAssetRecord.objects.all()):
            try:
                if not is_gallery_job(record):
                    continue
                if _gallery_job_is_unclaimable(record):
                    record.delete()
                    records_deleted += 1
            except Exception as error:  # noqa: BLE001 - one bad record never stops the sweep
                log_warn(
                    "gallery_prune_failed",
                    context={"phase": "record", "job": record.db_key},
                    exc=error,
                )
    except Exception as error:  # noqa: BLE001 - bounded scan failure
        log_error("gallery_prune_failed", context={"phase": "record-scan"}, exc=error)
    log_info(
        "gallery_orphans_pruned",
        context={"files": files_deleted, "records": records_deleted},
    )
    return {"files": files_deleted, "records": records_deleted}
