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
"""

from django.db import transaction
from evennia import logger

from world.art.adult import PortraitRejected, portrait_eligibility
from world.art.queue import ensure as queue_ensure
from world.art.subjects import (
    ArtSubjectError,
    character_subject_for,
    description_for,
    monster_subject_for,
    scene_subject_for,
)
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY


def _ensure_character_portrait(entity) -> None:
    """Gate, derive, describe, and enqueue one character portrait subject.

    Runs the adult gate immediately before the queue write for every portrait
    subject (design D3). The gate is a pure function of the canonical age
    attributes, so a rejection is deterministic and produces no record, no
    prompt, and no worker call.
    """
    subject = character_subject_for(entity)
    if subject is None:
        return
    portrait_eligibility(entity)
    age = int(entity.db.age)
    description = description_for(subject, entity=entity, age=age)
    queue_ensure(subject, description)


def _gate_at_schedule(entity) -> bool:
    """Run the adult gate at schedule time; return False if ineligible.

    The spec requires the gate at schedule time *and* again immediately before
    the queue write. A rejection at schedule time logs the named diagnostic and
    no record/prompt/job is ever produced; a later correction re-enables the
    next lifecycle attempt.
    """
    try:
        portrait_eligibility(entity)
    except PortraitRejected as error:
        logger.log_info(f"art portrait skipped at schedule: {error}")
        return False
    return True


def schedule_portrait_ensure(entity) -> None:
    """Register an exception-safe post-commit portrait ensure for an entity.

    The adult gate runs at schedule time; if it rejects, nothing is scheduled
    and no record is produced. Otherwise ``transaction.on_commit`` registers
    the ensure, which re-runs the gate immediately before the queue write.
    Django runs on_commit callbacks synchronously on the committing thread
    after commit, so the callback catches every art error and never
    propagates: a committed creation or import is always reported as success
    (design D7).
    """
    if not _gate_at_schedule(entity):
        return

    def _safe():
        try:
            _ensure_character_portrait(entity)
        except PortraitRejected as error:
            logger.log_info(f"art portrait skipped: {error}")
        except Exception as error:  # noqa: BLE001 - bounded, never propagates
            logger.log_warn(f"art portrait ensure failed: {error}")

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
        except ArtSubjectError:
            continue
        if subject is not None and subject.key == stable_key:
            return entity
    return None


def retry_character_portrait(stable_key: str) -> None:
    """Re-enqueue one failed character portrait through the adult gate.

    The subject is re-derived from the living entity that owns the explicit
    named policy for ``stable_key`` and the gate runs again; an unknown key,
    a missing entity, or an ineligible character is a named rejection with no
    record change (staff retry path, design D3).
    """
    entity = _living_entity_for_stable_key(stable_key)
    if entity is None:
        raise ArtSubjectError(
            f"no living character carries portrait stable_key {stable_key!r}"
        )
    _ensure_character_portrait(entity)


def requeue_character_portrait(stable_key: str) -> None:
    """Force-regenerate one character portrait through the adult gate.

    Resolves the owning entity and re-runs the gate before resetting the
    record; an unknown key or an ineligible character is a named rejection
    with no record change (staff requeue path, design D3).
    """
    entity = _living_entity_for_stable_key(stable_key)
    if entity is None:
        raise ArtSubjectError(
            f"no living character carries portrait stable_key {stable_key!r}"
        )
    portrait_eligibility(entity)
    from world.art.queue import requeue as queue_requeue

    subject = character_subject_for(entity)
    if subject is None:
        raise ArtSubjectError(
            f"character {entity.key!r} carries no named portrait policy"
        )
    queue_requeue(subject)


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
        logger.log_warn(f"art scene ensure skipped: {error}")


def _sync_registry_subjects() -> None:
    """Idempotently ensure a record for every scene and generic-monster subject."""
    for archetype in SCENE_ARCHETYPE_REGISTRY:
        try:
            subject = scene_subject_for(archetype)
            queue_ensure(subject, description_for(subject))
        except ArtSubjectError as error:
            logger.log_warn(f"art startup sync skipped scene {archetype!r}: {error}")
    for tier in MONSTER_TIER_REGISTRY:
        try:
            subject = monster_subject_for(tier)
            queue_ensure(subject, description_for(subject))
        except ArtSubjectError as error:
            logger.log_warn(f"art startup sync skipped monster {tier!r}: {error}")


def _recover_named_portraits() -> None:
    """Rescan living characters with an explicit named policy and ensure them.

    Recovers an enqueue that failed after an earlier gameplay commit. The
    adult gate re-runs; a permanently ineligible subject is skipped with a
    diagnostic and never retried by a later recovery pass (design D7).
    """
    from evennia.objects.models import ObjectDB

    from typeclasses.entities import LivingEntity

    for entity in ObjectDB.objects.all():
        if not isinstance(entity, LivingEntity):
            continue
        try:
            subject = character_subject_for(entity)
        except ArtSubjectError as error:
            logger.log_warn(f"art recovery skipped {entity.key}: {error}")
            continue
        if subject is None:
            continue
        try:
            portrait_eligibility(entity)
        except PortraitRejected as error:
            logger.log_info(f"art recovery skipped portrait: {error}")
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
        logger.log_err(f"art startup registry sync failed: {error}")
    try:
        _recover_named_portraits()
    except Exception as error:  # pragma: no cover - defensive startup isolation
        logger.log_err(f"art startup portrait recovery failed: {error}")
