"""The sole writer of art asset/queue records and its deterministic seams.

``world/art/service.py`` owns every write to asset/queue records (design D1).
Presenters, workers, browsers, and ``world/ai`` never write them. The seams
reachable from gameplay are all deterministic:

- ``art_sync_all()`` -- idempotent startup sync of scene + monster subjects,
  every one routed through its kind's gallery declaration, and recovery of
  explicit named portrait policies.
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
force path that bypasses that guard. Monster routing arrived with
``gallery-monster-autogen`` below; the scene producers joined it in
``scene-asset-migration``.

Change ``gallery-monster-generation`` opens the seam to every gallery-bearing
kind: ``request_gallery_image`` accepts an entity OR an already-derived
``ArtSubject``, reads EVERY precondition from the kind's capability
declaration (age precondition, field selection, free text, bindings) instead
of hard-coding the character shape, and refuses an argument naming a
capability the kind does not declare — never silently dropping it. The staff
requeue seam becomes kind-neutral (``requeue_gallery_subject``); the retry
seam keeps its ``gallery-failure-visibility`` name and resolves any
gallery-bearing subject by its typed full key.

Change ``gallery-monster-autogen`` lands that routing: ``_ensure_gallery_subject``
(formerly ``_ensure_character_portrait``) is the ONE automatic-ensure helper
for EVERY gallery-bearing kind, and startup synchronization routes every
registered monster visual species through it instead of the classic
subject-keyed ``ensure``. The
classic generic-monster record is retired from production: the scene kind
switched its two producers to the same gallery ensure, retiring the classic
record from every production path. Startup order guarantees a seed card
occupies the gallery before the automatic pass: ``art_sync_all`` runs AFTER
the gallery prune and seed synchronization.

``ensure_scene_asset`` and the scene loop of ``_sync_registry_subjects`` use
the scene gallery ensure. That ensure skips an archetype whose gallery record
exists with no card and no recorded error: the record a player's deletion
leaves behind, so the bundled image stays in effect instead of being
regenerated on the next entry.
"""

import contextvars
import uuid
from contextlib import contextmanager
from pathlib import Path
from threading import get_ident
from typing import Iterator

from django.conf import settings
from django.db import transaction

from world.observability import log_error, log_info, log_warn
from world.rules.presentation_events import on_publication_commit

from world.art import gallery as gallery_api
from world.art import gallery_kinds
from world.art.gallery_prompt import (
    GalleryPromptError,
    validate_custom_prompt,
    validate_fields,
)
from world.art.paths import resolved_under_store_root
from world.art.queue import (
    _enqueue_gallery_job_locked,
    _gallery_job_in_flight_locked,
    enqueue_gallery_job,
    gallery_job_in_flight,
    queue_lock,
)
from world.art.store import ArtAssetStatus, GalleryJobRecord
from world.art.subjects import (
    ArtSubjectError,
    ArtSubject,
    ArtSubjectKind,
    DraftPortraitValues,
    character_ages,
    character_subject_for,
    draft_character_description,
    description_for,
    named_character_subject,
    parse_subject,
    monster_subject_for,
    scene_subject_for,
)
from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY
from world.lore.monster_visuals import get_monster_visual_registry


#: How long a serialized gallery mutation waits for the shared queue lock before
#: it reports a bounded internal error instead of blocking the caller forever.
#: It is a deadlock guard, not a throughput control: every legitimate holder
#: releases on its own fast database/finalization path.
_MUTATION_LOCK_TIMEOUT_SECONDS = 30.0


class GalleryMutationError(RuntimeError):
    """Raised when a serialized gallery mutation is entered or used illegally."""


class _MutationOwner:
    """The unforgeable sentinel proving a token came from this module."""


_MUTATION_OWNER = _MutationOwner()


class GalleryMutationToken:
    """The subject-bound proof that one serialized mutation scope is active.

    Minted only by :func:`serialized_gallery_mutation`; ``world/art/queue.py``'s
    private already-locked primitives and the common request seam accept it in
    place of reacquiring the non-reentrant queue lock. Identity, thread and
    lifetime are all checked, so a foreign subject, a token used from another
    thread, or one retained past its scope is rejected rather than silently
    reusing someone else's serialization.
    """

    __slots__ = ("subject_full", "thread_id", "owner", "closed")

    def __init__(self, subject_full: str, thread_id: int, owner: object) -> None:
        self.subject_full = subject_full
        self.thread_id = thread_id
        self.owner = owner
        self.closed = False


_active_mutation: contextvars.ContextVar[GalleryMutationToken | None] = (
    contextvars.ContextVar("elosern_gallery_mutation", default=None)
)


def _require_active_mutation_token(
    token: object, subject: ArtSubject
) -> GalleryMutationToken:
    """Validate one caller-supplied mutation token against the live scope."""
    if not isinstance(token, GalleryMutationToken) or token.owner is not _MUTATION_OWNER:
        raise GalleryMutationError("a foreign gallery mutation token was rejected")
    if token.closed:
        raise GalleryMutationError("a gallery mutation token was used outside its scope")
    if token.thread_id != get_ident():
        raise GalleryMutationError("a gallery mutation token was used from another thread")
    if token.subject_full != subject.full():
        raise GalleryMutationError(
            "a gallery mutation token covers a different subject"
        )
    if _active_mutation.get() is not token:
        raise GalleryMutationError("a gallery mutation token is not the active scope")
    return token


@contextmanager
def serialized_gallery_mutation(subject: ArtSubject) -> Iterator[GalleryMutationToken]:
    """Hold the shared queue serialization around one subject-bound mutation.

    Acquires the ONE non-reentrant ``queue_lock`` BEFORE the caller opens its
    database transaction and yields a subject-bound token the common request
    seam and the queue's private already-locked primitives accept instead of
    reacquiring the lock. This is service-owned: it writes no character
    attribute, and the caller owns the transaction. The order is
    ``deferred callbacks -> queue lock -> database transaction -> gallery
    lock``; the callback deferral scope must therefore wrap this one.

    The same character may nest: an inner entry for the same subject on the
    same thread reuses the active unit (the lock is not reentrant). A foreign
    subject or another thread is rejected before any wait. The lock is released
    on every exit path; a token used afterwards is rejected.
    """
    active = _active_mutation.get()
    if active is not None:
        if active.thread_id != get_ident():
            raise GalleryMutationError(
                "a gallery mutation cannot nest on another thread"
            )
        if active.subject_full != subject.full():
            raise GalleryMutationError(
                "a gallery mutation for another subject cannot nest here"
            )
        yield active
        return
    if not queue_lock.acquire(timeout=_MUTATION_LOCK_TIMEOUT_SECONDS):
        raise GalleryMutationError("the gallery queue stayed serialized")
    token = GalleryMutationToken(subject.full(), get_ident(), _MUTATION_OWNER)
    context_token = _active_mutation.set(token)
    try:
        yield token
    finally:
        token.closed = True
        _active_mutation.reset(context_token)
        queue_lock.release()


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


#: The typed producers that re-validate a supplied/referenced subject for a
#: registry-backed gallery kind (``gallery-monster-generation`` for monster
#: visual species, ``scene-kind-gallery`` for scene archetypes). A kind with
#: no entry here is either entity-derived (character, resolved through
#: ``_living_entity_for_stable_key``) or declares no gallery at all; presence
#: in this mapping always agrees with the kind's gallery declaration.
_GALLERY_REGISTRY_PRODUCERS = {
    ArtSubjectKind.MONSTER.value: monster_subject_for,
    ArtSubjectKind.SCENE.value: scene_subject_for,
}


def _official_default_slot(subject, entity):
    """The chain's official slot for an automatic-path subject.

    The automatic-generation guard's official-satisfied condition
    (``official-art-resolution-contracts``): a subject whose stored provenance
    resolves a REGISTERED content reference and whose entity passes the kind's
    age precondition (already checked by the caller) is left without an
    automatic card whenever the startup snapshot holds that reference's
    default image, exactly as a subject that already holds a card is left
    alone. The presentation chain then shows the read-only official default.

    The check reuses the chain's own step (``official_default_slot``), so the
    guard and the presentation agree by construction; it reads stored state
    plus the startup snapshot only — nothing is recorded, enqueued, acquired,
    or mutated, the subject's named portrait policy is untouched, and the
    manual generation seams stay available. A subject whose reference the
    caller cannot see answers no facts, so its automatic request proceeds
    exactly as before. Registry-backed kinds resolve from their validated typed
    subject with no entity (the startup suppression gap this change closes).
    """
    from world.art.gallery_match import official_default_slot

    return official_default_slot(subject, entity)


def _emit_registry_suppression(subject, slot) -> None:
    """Emit the one bounded info event for a registry-subject official skip.

    Only a kind whose official reference is registry-derived (a monster visual
    species or a scene archetype) can be satisfied without any spawned entity;
    that is the path this change fixes, so that path alone reports the
    suppression. The event carries business identifiers only — the subject,
    kind, content reference, and the closed ``official_default`` reason — and
    never a prompt, credentials, root, or file path.
    """
    policy = gallery_kinds.capabilities_for(
        subject.kind.value
    ).official_reference_policy
    if policy not in ("visual_species", "scene_archetype"):
        return
    log_info(
        "art_auto_generation_suppressed",
        context={
            "subject": subject.full(),
            "kind": subject.kind.value,
            "reference": slot.source_identity,
            "reason": "official_default",
        },
    )


def _standard_gallery_request_kwargs(capability) -> dict:
    """The standard deterministic staff/automatic request shape for a kind.

    The ``appearance``-only selection belongs to the character vocabulary and
    is passed only where the declaration supports field selection; a kind
    without it requests with no selection. Every such request carries the
    fitted default face rectangle (face_rect=None) and no binding or free text.
    """
    fields = ("appearance",) if capability.supports_field_selection else ()
    return {"fields": fields, "face_rect": None}


def _guarded_gallery_request(subject, entity) -> bool:
    """One guarded automatic-path-style request for a resolved gallery subject.

    Returns True when a gallery generation was requested, False when the
    automatic-generation guard suppressed it: the subject already holds a card
    or an in-flight job, or (``official-art-resolution-contracts``) its
    eligible official content reference already resolves a default image in
    the startup snapshot, in which case the presentation chain shows that
    read-only image and no card is minted. For a kind that declares the
    canonical-age precondition the age pair is read immediately before the
    request (design D3): a rejection is deterministic and produces no record,
    no prompt, and no worker call. The kind's declaration decides the request
    shape — never a comparison against a particular kind.
    """
    capability = gallery_kinds.capabilities_for(subject.kind.value)
    if capability.requires_age_precondition:
        if entity is None:
            raise ArtSubjectError(
                f"a gallery request for {subject.full()!r} requires the entity carrying the portrait subject"
            )
        character_ages(entity)
    official = _official_default_slot(subject, entity)
    if official.facts is not None:
        _emit_registry_suppression(subject, official)
        return False
    if _gallery_auto_generation_pending(subject):
        return False
    request_gallery_image(
        entity if entity is not None else subject,
        **_standard_gallery_request_kwargs(capability),
    )
    return True


def _ensure_gallery_subject(entity_or_subject) -> bool:
    """Request one automatic gallery card for ANY gallery-bearing subject when its gallery warrants it.

    The ONE automatic-ensure helper for every gallery-bearing kind (change
    ``gallery-monster-autogen``), serving either a gameplay entity (a
    character, derived through its typed producer) or an already-derived
    ``ArtSubject`` (a registry-backed subject such as a monster visual
    species).
    Returns True when a gallery generation was requested, False when the
    gallery guard suppressed the automatic path. The subject kind's
    declaration — age precondition, field selection, default rect — drives
    everything through the shared guarded helper, so a kind that declares no
    age precondition never reads an age attribute, and NO gallery-bearing
    subject ever writes a classic fixed-identity record on an automatic path.
    """
    if isinstance(entity_or_subject, ArtSubject):
        return _guarded_gallery_request(entity_or_subject, None)
    subject = character_subject_for(entity_or_subject)
    if subject is None:
        return False
    return _guarded_gallery_request(subject, entity_or_subject)


def _ensure_scene_gallery_subject(subject: ArtSubject) -> bool:
    """Request one automatic scene gallery card unless the archetype must stay empty.

    The scene producers' shared automatic ensure (change
    ``scene-asset-migration``): the gallery-bearing scene kind routes through
    the same guarded helper every gallery kind uses, EXCEPT for the one state
    the shared guard cannot distinguish from a fresh gallery — a record that
    exists with no card and no recorded error, which is exactly what
    ``gallery.remove_card`` leaves behind when a player deletes the only card.
    Specification 3 says deleting returns the archetype to its bundled image,
    so that state requests nothing; a failed first generation records an error
    (``record_error`` creates the record), so it is still retried. Returns
    ``True`` when a generation was requested.
    """
    record = gallery_api.record_for(subject)
    if (
        record is not None
        and not gallery_api.cards_for(subject)
        and record.db.last_error_code is None
    ):
        return False
    return _ensure_gallery_subject(subject)


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
    scheduled and no record is produced. Otherwise the shared publication
    commit registration (``world.rules.presentation_events``) registers the
    ensure, which re-checks the ages immediately before the queue write. That
    registration is the same commit contract as a raw ``on_commit`` for the
    ordinary path, while letting a mutation that holds queue serialization
    defer the ensure until it has released its locks.
    Django runs on_commit callbacks synchronously on the committing thread
    after commit, so the callback catches every art error and never
    propagates: a committed creation or import is always reported as success
    (design D7).
    """
    if not _ages_eligible_at_schedule(entity):
        return

    def _safe():
        try:
            _ensure_gallery_subject(entity)
        except ArtSubjectError as error:
            log_info("art_portrait_skipped", context={"stage": "ensure"}, exc=error)
        except Exception as error:  # noqa: BLE001 - bounded, never propagates
            log_warn("art_portrait_ensure_failed", context={"entity": entity.key}, exc=error)

    on_publication_commit(_safe)


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


def _resolve_gallery_subject(subject: ArtSubject) -> tuple[ArtSubject, object]:
    """Resolve one erroring gallery subject to its canonical subject and entity.

    Resolution is ALWAYS through the subject's OWN kind producer — never a
    scan across kinds, because a character stable key may legally equal a
    monster visual species key and a kind-order scan could then re-drive the
    wrong subject (``gallery-monster-generation``, design: collision safety). The
    entity is returned for kinds that declare the age precondition and is
    ``None`` for registry-backed kinds. An unresolvable subject — no living
    character, an unregistered registry entry, a kind with no gallery — is a
    typed ``ArtSubjectError`` with no record change.
    """
    capability = gallery_kinds.capabilities_for(subject.kind.value)
    if not capability.has_gallery:
        raise ArtSubjectError(f"subject {subject.full()!r} declares no gallery")
    if capability.requires_age_precondition:
        entity = _living_entity_for_stable_key(subject.key)
        if entity is None:
            raise ArtSubjectError(
                f"no living character carries portrait stable_key {subject.key!r}"
            )
        resolved = character_subject_for(entity)
        if resolved is None:
            raise ArtSubjectError(
                f"character carrying stable_key {subject.key!r} no longer yields a portrait subject"
            )
        return resolved, entity
    producer = _GALLERY_REGISTRY_PRODUCERS.get(subject.kind.value)
    if producer is None:  # pragma: no cover - every gallery kind has a producer
        raise ArtSubjectError(
            f"no typed producer resolves subject kind {subject.kind.value!r}"
        )
    return producer(subject.key), None


def resolve_gallery_subject_by_key(subject_key: str) -> tuple[ArtSubject, object | None]:
    """Resolve a serialized full subject key to its typed subject and entity.

    The ONE public read-only seam of ``gallery-card-update-api``: the
    webclient gallery presenter rail and the gallery management adapters
    resolve a rail ``subject_key`` back to its live entity here instead of
    duplicating the lookup. The key is parsed through the shared typed
    parser, then dispatched on its OWN kind — never a scan across kinds, so
    a character stable key legally equal to a scene archetype or monster
    tier can only ever resolve its own kind's subject:

    * registry-backed gallery kinds — monster visual species and (since
      ``scene-kind-gallery``) scene archetypes — re-validate through the
      kind's typed producer (an unregistered registry entry is the
      producer's typed rejection — the caller's key alone is never trusted);
    * character-kind keys resolve through the module's existing stable-key
      live-entity lookup and the existing typed subject producer;
    * a kind with neither a registry producer nor the character resolution
      is the same typed ``ArtSubjectError`` as any unresolvable key.

    The entity is returned only for the character kind and is ``None`` for
    registry kinds. The resolver checks NO preconditions (age, capability),
    reads and writes NO gallery record, and publishes NO presentation — the
    preconditions stay where they already are. The live-entity branch is the
    existing scan over every living entity, cost for cost.
    """
    subject = parse_subject(subject_key)
    producer = _GALLERY_REGISTRY_PRODUCERS.get(subject.kind.value)
    if producer is not None:
        return producer(subject.key), None
    if subject.kind is ArtSubjectKind.CHARACTER:
        entity = _living_entity_for_stable_key(subject.key)
        if entity is None:
            raise ArtSubjectError(
                f"no living character carries portrait stable_key {subject.key!r}"
            )
        resolved = character_subject_for(entity)
        if resolved is None:
            raise ArtSubjectError(
                f"character carrying stable_key {subject.key!r} no longer yields a portrait subject"
            )
        return resolved, entity
    raise ArtSubjectError(
        f"no typed producer resolves subject kind {subject.kind.value!r}"
    )


def retry_gallery_subject(subject: ArtSubject) -> bool:
    """Re-attempt one gallery subject through its kind preconditions and the gallery guard.

    Takes the erroring subject's TYPED subject (the record identity ``@art
    retry`` already holds — ``gallery-monster-generation``), so resolution
    cannot confuse a character key with an identically-spelled monster key.
    The subject is re-validated through its own kind's producer — the living
    entity that owns the explicit named policy and the ages for an
    age-declaring kind, the registry entry for a registry kind; an unknown
    key, a missing entity, or an ineligible character is a named rejection
    with no record change (staff retry path, design D3). Returns True only
    when a gallery generation was actually requested, so ``@art retry``
    counts truthfully when the guard leaves an already-carded subject alone.

    When the guard declines only because the gallery already holds cards, the
    subject's recorded error is moot — the guard will suppress every future
    automatic or retry request for a carded subject of ANY gallery kind and
    nothing else would ever clear it — so the seam clears it here. A decline
    for any other reason (an in-flight job) keeps the recorded error.
    """
    subject, entity = _resolve_gallery_subject(subject)
    requested = _guarded_gallery_request(subject, entity)
    if not requested and gallery_api.cards_for(subject):
        gallery_api.clear_error(subject)
    return requested


def requeue_gallery_subject(subject: ArtSubject) -> None:
    """Force-regenerate one gallery subject through its kind preconditions and the gallery.

    The kind-neutral staff force path (``gallery-monster-generation``,
    formerly ``requeue_character_portrait``): re-validates the subject
    through its own kind's producer, and for an age-declaring kind resolves
    the owning entity and re-checks the canonical ages before issuing exactly
    one gallery generation request. Requeue deliberately bypasses the
    automatic-generation idempotency guard, so a subject that already holds
    cards still gets one new generation — appended for a kind with no declared
    maximum, and replacing under the cap for a capped kind such as monster. An
    unresolvable subject or an ineligible character is a named rejection with
    no record change (staff requeue path, design D3). A gallery-bearing
    subject never writes or resets a classic fixed-identity record here.
    """
    subject, entity = _resolve_gallery_subject(subject)
    capability = gallery_kinds.capabilities_for(subject.kind.value)
    if capability.requires_age_precondition and entity is None:  # pragma: no cover - resolver guarantees the entity
        raise ArtSubjectError(
            f"no living character carries portrait stable_key {subject.key!r}"
        )
    request_gallery_image(
        entity if entity is not None else subject,
        **_standard_gallery_request_kwargs(capability),
    )


def ensure_scene_asset(archetype) -> None:
    """Ensure the scene gallery card request for a validated archetype (idempotent).

    ``None`` or an unresolvable archetype is a side-effect-free no-op. The
    scene kind is gallery-bearing (change ``scene-asset-migration``), so the
    room-entry seam routes through the shared automatic-generation guard: one
    gallery request only when the subject has no card, no in-flight job, and
    either no gallery record or a record carrying a recorded error. A gallery
    record with no card and no error is a player's deletion and requests
    nothing. Art failures are bounded and never block the player's move.
    """
    if archetype is None or archetype not in SCENE_ARCHETYPE_REGISTRY:
        return
    try:
        _ensure_scene_gallery_subject(scene_subject_for(archetype))
    except Exception as error:  # noqa: BLE001 - bounded, never blocks the move
        log_warn("art_scene_ensure_skipped", context={"archetype": archetype}, exc=error)


def _sync_registry_subjects() -> None:
    """Idempotently ensure every registered subject, routed by its kind's gallery declaration.

    Every registered scene archetype and every registered monster visual
    species routes through the shared automatic-ensure helper under the same
    gallery guard every character path uses, so startup never writes a
    subject-keyed record for either kind. The scene loop uses the
    scene-specific ensure that honors a player's deletion. Every failure is
    bounded per subject so one bad entry never aborts the remaining sync.
    """
    for archetype in SCENE_ARCHETYPE_REGISTRY:
        try:
            subject = scene_subject_for(archetype)
            _ensure_scene_gallery_subject(subject)
        except Exception as error:  # noqa: BLE001 - bounded per archetype, never aborts startup
            log_warn("art_startup_sync_skipped", context={"kind": "scene", "key": archetype}, exc=error)
    for visual_key in get_monster_visual_registry():
        try:
            subject = monster_subject_for(visual_key)
            _ensure_gallery_subject(subject)
        except Exception as error:  # noqa: BLE001 - bounded per tier, never aborts startup
            log_warn("art_startup_sync_skipped", context={"kind": "monster", "key": visual_key}, exc=error)

def _recover_named_portraits() -> None:
    """Rescan living characters with an explicit named policy and ensure them.

    Recovers an enqueue that failed after an earlier gameplay commit. The
    canonical-age check re-runs; a permanently ineligible subject is skipped
    with a diagnostic and never retried by a later recovery pass (design D7).
    The shared automatic-generation guard inside ``_ensure_gallery_subject``
    restricts the recovery to subjects with an empty gallery and no in-flight
    job: a subject whose gallery already holds a card, or whose generation is
    already pending/in-progress, is left alone (change
    ``gallery-autogen-retrofit``).

    A creation-pending character is never recovered: its early named policy is
    established by the draft portrait request, and the pending shell carries no
    canonical ages. Any existing draft job/card stays with the normal
    settlement/reconnect path, and startup must not manufacture an automatic
    replacement for it (change ``creation-draft-portrait-request``).
    """
    from evennia.objects.models import ObjectDB

    from typeclasses.entities import LivingEntity

    for entity in ObjectDB.objects.all():
        if not isinstance(entity, LivingEntity):
            continue
        if bool(getattr(entity, "creation_pending", False)):
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
        _ensure_gallery_subject(entity)


def art_sync_all() -> None:
    """Idempotent startup synchronization plus named-policy recovery.

    Routes every ``SCENE_ARCHETYPE_REGISTRY`` entry and every registered
    monster visual species through the shared gallery automatic-ensure
    helper, then rescans living characters carrying an explicit named
    portrait policy. The scene loop honors a player's deletion through the
    scene-specific ensure (change ``scene-asset-migration``). Every record
    write flows through the queue under the shared lock; a failure is bounded
    and never aborts startup. Runs as a startup step AFTER
    ``art_gallery_prune`` and ``art_seed_sync`` so the prune has swept and a
    seed card occupies a subject's gallery before the automatic guard reads it.
    """
    try:
        _sync_registry_subjects()
    except Exception as error:  # pragma: no cover - defensive startup isolation
        log_error("art_startup_registry_sync_failed", context={"scope": "registry-sync"}, exc=error)
    try:
        _recover_named_portraits()
    except Exception as error:  # pragma: no cover - defensive startup isolation
        log_error("art_startup_recovery_failed", context={"scope": "portrait-recovery"}, exc=error)


def _pending_player_character(entity) -> bool:
    """True for a ``PlayerCharacter`` still inside character creation.

    Imported here rather than at module scope: the typeclasses layer depends on
    world state, and this module must stay importable by the queue, the worker
    and the art tests without pulling it in.
    """
    from typeclasses.characters import PlayerCharacter

    return isinstance(entity, PlayerCharacter) and bool(
        getattr(entity, "creation_pending", False)
    )


def request_gallery_image(
    entity_or_subject,
    *,
    fields=(),
    custom_prompt="",
    binding=None,
    face_rect=None,
    draft_values=None,
    mutation_token=None,
    replacement_image_id=None,
) -> str:
    """Validate, mint, and enqueue exactly one gallery image request.

    The ONLY gameplay-reachable entry point for gallery generation
    (change ``gallery-generation-jobs``), now serving EVERY gallery-bearing
    subject kind (change ``gallery-monster-generation``). Accepts either a
    gameplay entity — derived through the existing typed producer for its
    kind — or an already-derived :class:`ArtSubject` (a registry-backed
    subject such as a monster visual species is re-validated through its
    kind's typed producer, never trusted from the caller's key alone). EVERY precondition
    is read from the subject kind's capability declaration instead of being
    hard-coded to the character shape: the canonical-age check applies only
    where the kind declares it; a field selection, free text, or binding is
    accepted only where the kind declares the capability, and an argument
    naming an undeclared capability is a typed rejection at this boundary
    that NAMES the capability — never silently dropped, because a card whose
    ``requested_fields`` provenance would lie is worse than a refusal.
    Validated arguments are checked through the ``world/art/gallery_prompt``
    and ``world/art/gallery.py`` validators BEFORE any queue write — every
    rejection raises a typed error at this boundary and leaves no record, no
    file, no card, and no rendered prompt behind. The freshly minted
    lowercase-uuid ``image_id`` keys one independent job (two requests, two
    jobs).

    Deliberately never imports or consults ``world.art.connectivity``: an
    unreachable sd-webui server is a reported ``failed`` settle carrying its
    bounded named error code on the subject's gallery record (design §12.3.1),
    not a gate. The caller-side failure isolation is the existing post-commit
    pattern the auto-generation retrofit wires: because every rejection
    raises before any write, a wrapped call can never roll back committed
    gameplay. Returns the minted ``image_id``.

    The ONE typed exception to the canonical-age precondition is the pending
    character's draft request (change ``creation-draft-portrait-request``):
    ``draft_values`` carries the validated race/subrace/sex/apparent-age
    snapshot and the description is composed exclusively from it. That branch
    is accepted only with the serialized mutation token its rules owner holds,
    only for an owned pending player character, and only with an empty field
    selection, no binding and no face rectangle; every ordinary or activated
    request still reads the canonical age pair and refuses a pending character
    without validated draft values. ``replacement_image_id`` is the
    server-authorized previous creation image the draft settlement may replace;
    it is rejected on every ordinary request. There is no generic
    ``skip_age_check`` flag and no alternate public queue bypass.
    """
    if draft_values is not None and not isinstance(draft_values, DraftPortraitValues):
        raise ArtSubjectError(
            "draft_values must be the validated draft-portrait snapshot"
        )
    if draft_values is None and (mutation_token is not None or replacement_image_id is not None):
        raise GalleryMutationError(
            "a mutation token or replacement metadata requires validated draft values"
        )
    if draft_values is not None:
        if mutation_token is None:
            raise GalleryMutationError(
                "a draft portrait request requires the serialized mutation scope"
            )
        if fields or binding is not None or face_rect is not None:
            raise ArtSubjectError(
                "a pending draft portrait request carries no field selection, "
                "binding or face rectangle"
            )
    # 1. Derive the subject through the kind's typed producer. A raw subject
    # for a registry-backed kind is re-validated through its kind's producer
    # right here — the caller's key alone is never trusted, and no later
    # precondition reads the raw subject. A raw subject for an
    # entity-derived kind carries no entity with it, and its declared
    # preconditions need the entity — the typed rejection below.
    if isinstance(entity_or_subject, ArtSubject):
        subject = entity_or_subject
        entity = None
        registry_producer = _GALLERY_REGISTRY_PRODUCERS.get(subject.kind.value)
        if registry_producer is not None:
            subject = registry_producer(subject.key)
    else:
        entity = entity_or_subject
        if draft_values is not None:
            # The pending shell's policy may not be committed yet, so the named
            # subject is derived from its primary key instead of its attribute.
            subject = named_character_subject(entity)
        else:
            subject = character_subject_for(entity)
    if subject is None:
        raise ArtSubjectError(
            f"subject source {getattr(entity, 'key', entity_or_subject)!r} yields no portrait subject"
        )
    capability = gallery_kinds.capabilities_for(subject.kind.value)
    if not capability.has_gallery:
        raise ArtSubjectError(
            f"subject kind {subject.kind.value!r} declares no gallery"
        )
    if draft_values is not None:
        if not _pending_player_character(entity):
            raise ArtSubjectError(
                "a draft portrait request requires an owned pending player character"
            )
        _require_active_mutation_token(mutation_token, subject)
    # 2. Capability-gated argument validation, each error naming the
    # undeclared capability when the declaration rejects the argument.
    # The catalog validator is itself kind-aware: an empty selection stays
    # legal for every gallery kind, a non-empty one is rejected where the
    # declaration admits no field selection, naming the capability.
    selected = validate_fields(fields, kind=subject.kind.value)
    if capability.supports_free_text:
        custom = validate_custom_prompt(custom_prompt)
    elif custom_prompt:
        # Normalize through the SAME validator first: whitespace-only text is
        # the established legal no-op and carries nothing the kind could lose;
        # only text that survives normalization NAMES the undeclared
        # capability and is rejected. A non-text argument fails the validator.
        if validate_custom_prompt(custom_prompt):
            raise GalleryPromptError(
                f"subject kind {subject.kind.value!r} declares no free-text support; "
                "non-empty custom prompt text is rejected"
            )
        custom = ""
    else:
        custom = ""
    if capability.supports_bindings:
        binding = gallery_api.validate_binding(binding)
    elif binding is not None:
        raise gallery_api.GalleryRecordError(
            f"subject kind {subject.kind.value!r} declares no binding support; "
            "a binding argument is rejected"
        )
    # A supplied face rectangle is accepted only where the kind declares
    # face-rectangle support (the same text the sole writer raises), and is
    # then validated; ``None`` keeps the shared default downstream.
    if face_rect is not None and not capability.supports_face_rect:
        raise gallery_api.GalleryRecordError(
            f"subject kind {subject.kind.value!r} declares no face rectangle support"
        )
    if face_rect is not None:
        planned_image_size = {
            "width": int(settings.ART_SD_PORTRAIT_WIDTH),
            "height": int(settings.ART_SD_PORTRAIT_HEIGHT),
        }
        face_rect = gallery_api.validate_face_rect(face_rect, image_size=planned_image_size)
    # 3. The declared age precondition, read immediately before the request.
    # A kind without the declaration never reads the age attribute at all.
    apparent_age = None
    if capability.requires_age_precondition:
        if draft_values is not None:
            apparent_age = draft_values.apparent_age
        else:
            if entity is None:
                raise ArtSubjectError(
                    f"a gallery request for {subject.full()!r} requires the entity carrying the portrait subject"
                )
            if _pending_player_character(entity):
                raise ArtSubjectError(
                    f"a gallery request for pending character {subject.full()!r} "
                    "requires validated draft portrait values"
                )
            _age, apparent_age = character_ages(entity)
    # 4. Description: the selection and free text exist only where declared;
    # a kind without them gets its registry-driven description (monster kind)
    # or base identity text — never an empty character description.
    if draft_values is not None:
        description = draft_character_description(draft_values, custom)
    else:
        description = description_for(
            subject,
            entity=entity,
            apparent_age=apparent_age,
            fields=selected if capability.supports_field_selection else None,
            custom_prompt=custom if capability.supports_free_text else "",
        )
    image_id = str(uuid.uuid4())
    if mutation_token is not None:
        _enqueue_gallery_job_locked(
            subject,
            description,
            image_id=image_id,
            binding=binding,
            face_rect=face_rect,
            requested_fields=list(selected),
            replacement_image_id=replacement_image_id,
        )
    else:
        enqueue_gallery_job(
            subject,
            description,
            image_id=image_id,
            binding=binding,
            face_rect=face_rect,
            requested_fields=list(selected),
        )
    log_info(
        "gallery_generate",
        context={"subject": subject.full(), "image_id": image_id, "kind": subject.kind.value},
    )
    return image_id




def _gallery_job_is_unclaimable(record, registered_monster_keys=None) -> bool:
    """True when a gallery job record can never be claimed or published again.

    A whose-subject-no-longer-resolves row, a monster row whose key is not a
    registered visual species (when the registered key set is known), and a
    row whose status is neither ``pending`` nor ``in_progress`` can never
    publish. A lease-expired ``in_progress`` job is RETAINED — reclaiming it
    to ``pending`` is the shared queue's lease-reclaim job, so a job whose
    worker died is retried, not silently dropped.
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
    if (
        registered_monster_keys is not None
        and str(record.db.kind or "") == ArtSubjectKind.MONSTER.value
        and record.db.subject_key not in registered_monster_keys
    ):
        return True
    status = str(record.db.status or "")
    return status not in (ArtAssetStatus.PENDING, ArtAssetStatus.IN_PROGRESS)


def _registered_monster_keys() -> frozenset[str] | None:
    """The registered visual species keys, built once per prune, or ``None``.

    ``None`` disables every unregistered-key deletion for this pass: a
    registry that fails to build, or builds empty, cannot prove that any
    stored monster key is unregistered, and the deletion is irreversible.
    """
    try:
        keys = frozenset(get_monster_visual_registry())
    except Exception as error:  # noqa: BLE001 - bounded: skip the unregistered-key phases
        log_error("gallery_prune_failed", context={"phase": "registry"}, exc=error)
        return None
    if not keys:
        log_warn(
            "gallery_prune_failed",
            context={"phase": "registry", "reason": "empty_registry"},
        )
        return None
    return keys




def prune_gallery_orphans() -> dict:
    """Idempotent startup reclaim of orphan gallery files and spent records.

    Phases, in order:

    1. Every monster gallery record whose key is not a registered visual
       species is deleted (through the gallery API's sole writer).
    2. The gallery reference set is read (read-only through the gallery API).
    3. Every gallery job record that can never be claimed or published again
       (unresolvable subject, unregistered monster key, or a status outside
       ``pending``/``in_progress``) is deleted.
    4. Every file under the store root's ``gallery/`` tree that no card of
       any remaining gallery record references is deleted — including the
       cards of the records phase 1 removed.

    The unregistered-key rules run only when the visual registry builds
    non-empty. Every path is resolved through the single store-root
    confinement helper, so nothing outside ``ART_STORE_ROOT`` is ever
    unlinked, and a referenced file is NEVER deleted. Every failure phase is
    bounded: an unreadable tree or a failing deletion is a named diagnostic
    and the prune continues; the function itself never raises, so startup
    never aborts because of it.

    Reads happen on the reactor thread during ``at_server_start``, before the
    scheduler can claim or publish anything — the queue lock is deliberately
    not taken here (the gallery record phase takes ``gallery_lock`` through
    the gallery API). A future mid-game re-use must take the queue lock too.
    """
    files_deleted = 0
    records_deleted = 0
    records_unregistered = 0
    registered = _registered_monster_keys()
    if registered is not None:
        try:
            records_unregistered += gallery_api.delete_unregistered_monster_records(registered)
        except Exception as error:  # noqa: BLE001 - bounded: the remaining phases still run
            log_error("gallery_prune_failed", context={"phase": "gallery-records"}, exc=error)
    referenced = None
    try:
        referenced = gallery_api.referenced_stored_identities()
    except Exception as error:  # noqa: BLE001 - bounded: skip the file phases, still prune job records
        log_error("gallery_prune_failed", context={"phase": "references"}, exc=error)
    try:
        for record in list(GalleryJobRecord.objects.all()):
            try:
                if _gallery_job_is_unclaimable(record, registered):
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
    result = {
        "files": files_deleted,
        "records": records_deleted,
        "records_unregistered": records_unregistered,
    }
    # The registered species count makes a partial registry diagnosable.
    log_info(
        "gallery_orphans_pruned",
        context={
            **result,
            "registered_species": len(registered) if registered is not None else None,
        },
    )
    return result
