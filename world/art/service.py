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
kept the classic subject-keyed pipeline until ``scene-asset-migration``
switched its two producers to the same gallery ensure, retiring the classic
record from every production path — ``@art retry``'s classic arm likewise
skips every gallery-bearing kind, so a legacy record is never reactivated or
reset. Pre-existing classic monster records are left in place — not deleted,
not reset — and keep resolving through the display chain's classic step;
pre-existing classic scene records are converted by
``migrate_classic_scene_records`` below. Startup order guarantees a seed card
occupies the gallery before the automatic pass: ``art_sync_all`` runs AFTER
the gallery prune and seed synchronization.

Change ``scene-asset-migration`` adds ``migrate_classic_scene_records`` — the
startup conversion of settled classic scene outputs into scene gallery cards,
run immediately before the gallery prune — and switches ``ensure_scene_asset``
and the scene loop of ``_sync_registry_subjects`` to the scene gallery ensure.
That ensure skips an archetype whose gallery record exists with no card and
no recorded error: the record a player's deletion leaves behind, so the
bundled image stays in effect instead of being regenerated on the next entry.
"""

import io
import math
import uuid
from pathlib import Path

from django.conf import settings
from django.db import transaction
from PIL import Image

from world.observability import log_error, log_info, log_warn

from world.art import gallery as gallery_api
from world.art import gallery_kinds
from world.art.gallery_prompt import (
    GalleryPromptError,
    validate_custom_prompt,
    validate_fields,
)
# The startup conversion reuses the seed sync's own never-overwrite copy
# primitive (design D1 step 3) instead of hand-rolling an atomic write.
from world.art.gallery_seed import _MAX_FILE_BYTES, _publish_under_store
from world.art.paths import resolved_under_store_root
from world.art.presenter import _validated_output_identity
from world.art.queue import (
    enqueue_gallery_job,
    gallery_job_in_flight,
    is_gallery_job,
)
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import (
    ArtSubjectError,
    ArtSubject,
    ArtSubjectKind,
    character_ages,
    character_subject_for,
    description_for,
    parse_subject,
    monster_subject_for,
    scene_subject_for,
)
from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY
from world.lore.monster_visuals import get_monster_visual_registry


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


def _official_default_satisfies(subject, entity) -> bool:
    """True when an eligible official reference already resolves a default image.

    The automatic-generation guard's official-satisfied condition
    (``official-art-resolution-contracts``): a subject whose stored provenance
    resolves a REGISTERED content reference and whose entity passes the kind's
    age precondition (already checked by the caller) is left without an
    automatic card whenever the startup snapshot holds that reference's
    default image, exactly as a subject that already holds a card is left
    alone. The presentation chain then shows the read-only official default.

    The check reuses the chain's own step (``official_default_for``), so the
    guard and the presentation agree by construction; it reads stored state
    plus the startup snapshot only — nothing is recorded, enqueued, acquired,
    or mutated, the subject's named portrait policy is untouched, and the
    manual generation seams stay available. A subject whose reference the
    caller cannot see answers False, so its automatic request proceeds exactly
    as before: a character or NPC without authored provenance, a registry-keyed
    monster subject (the automatic paths pass a bare ``ArtSubject``, which
    carries no stored species identity), and any reference the snapshot does
    not hold.
    """
    from world.art.gallery_match import official_default_for

    return official_default_for(subject, entity) is not None


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
    if _official_default_satisfies(subject, entity):
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
            _ensure_gallery_subject(entity)
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
    gallery guard every character path uses (change ``scene-asset-migration``
    switched the scene loop from the classic ``ensure``), so startup never
    writes a classic record for either kind. The scene loop uses the
    scene-specific ensure that honors a player's deletion; a pre-existing
    classic monster record is left in place and keeps resolving through the
    display chain's classic step. Every failure is bounded per subject so one
    bad entry never aborts the remaining sync.
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
    ``art_scene_migration``, ``art_gallery_prune`` and ``art_seed_sync`` so
    classic records are converted, the prune has swept, and a seed card
    occupies a subject's gallery before the automatic guard reads it.
    """
    try:
        _sync_registry_subjects()
    except Exception as error:  # pragma: no cover - defensive startup isolation
        log_error("art_startup_registry_sync_failed", context={"scope": "registry-sync"}, exc=error)
    try:
        _recover_named_portraits()
    except Exception as error:  # pragma: no cover - defensive startup isolation
        log_error("art_startup_recovery_failed", context={"scope": "portrait-recovery"}, exc=error)


def request_gallery_image(entity_or_subject, *, fields=(), custom_prompt="", binding=None, face_rect=None) -> str:
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
    """
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
        if entity is None:
            raise ArtSubjectError(
                f"a gallery request for {subject.full()!r} requires the entity carrying the portrait subject"
            )
        _age, apparent_age = character_ages(entity)
    # 4. Description: the selection and free text exist only where declared;
    # a kind without them gets its registry-driven description (monster kind)
    # or base identity text — never an empty character description.
    description = description_for(
        subject,
        entity=entity,
        apparent_age=apparent_age,
        fields=selected if capability.supports_field_selection else None,
        custom_prompt=custom if capability.supports_free_text else "",
    )
    image_id = str(uuid.uuid4())
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


# --- Classic scene conversion (change ``scene-asset-migration``) -------------


def _classic_scene_output_identities(record) -> tuple[str, ...]:
    """The record's distinct stored identities, current output first."""
    identities: list[str] = []
    for identity in (record.db.output_identity, record.db.prior_output_identity):
        if isinstance(identity, str) and identity and identity not in identities:
            identities.append(identity)
    return tuple(identities)


def _delete_classic_scene_files(
    record_key: str, identities: tuple[str, ...], referenced: set[str]
) -> None:
    """Unlink every existing confined classic file no gallery card references.

    A failed unlink is one bounded diagnostic per identity and never stops the
    remaining files: the record is already gone, so this pass cannot retry,
    and the event is the only trace that names the file left behind.
    """
    for identity in identities:
        if identity in referenced:
            continue
        resolved = resolved_under_store_root(identity)
        if resolved is None or not resolved.is_file():
            continue
        try:
            resolved.unlink()
        except OSError as error:
            log_warn(
                "art_scene_migration_failed",
                context={"record": record_key, "identity": identity},
                exc=error,
            )


def _scene_created_at(record, resolved: Path) -> float:
    """The record's completion timestamp, or the classic file's mtime."""
    completed_at = record.db.completed_at
    if (
        isinstance(completed_at, (int, float))
        and not isinstance(completed_at, bool)
        and math.isfinite(completed_at)
    ):
        return float(completed_at)
    return resolved.stat().st_mtime


def _scene_image_size(payload: bytes) -> dict[str, int]:
    """The pixel size of the copied bytes, decoded exactly as the seed sync does."""
    with Image.open(io.BytesIO(payload)) as image:
        width, height = image.size
    if width <= 0 or height <= 0:
        raise ValueError("the classic scene output declares no positive pixel size")
    return {"width": width, "height": height}


def _convert_classic_scene_output(record, subject: ArtSubject, identity: str) -> None:
    """Copy one presentable classic output into the scene gallery as one card.

    The copy goes through the seed sync's own never-overwrite primitive under a
    fresh uuid4 name, and the size is decoded from the copied bytes, so the
    appended card is contract-valid without a second read of the classic file.
    """
    resolved = resolved_under_store_root(identity)
    if resolved is None or not resolved.is_file():
        raise ValueError(f"classic scene identity {identity!r} is not presentable")
    payload = resolved.read_bytes()
    if len(payload) > _MAX_FILE_BYTES:
        raise ValueError(f"classic scene identity {identity!r} is past the store size cap")
    image_size = _scene_image_size(payload)
    image_id = str(uuid.uuid4())
    stored_identity = (
        f"gallery/{gallery_kinds.store_directory_for(subject.kind.value)}/"
        f"{subject.key}/{image_id}{Path(identity).suffix.lower()}"
    )
    _publish_under_store(stored_identity, payload)
    gallery_api.append_card(
        subject,
        image_id=image_id,
        stored_identity=stored_identity,
        prompt=None,
        seed=None,
        checkpoint=None,
        requested_fields=[],
        binding=None,
        image_size=image_size,
        source="generated",
        created_at=_scene_created_at(record, resolved),
    )


def _migrate_classic_scene_record(record) -> str:
    """Convert or drop one classic scene record; return its counted outcome.

    A ``pending``/``in_progress`` record is untouched. A ``done`` record whose
    output is presentable and whose gallery holds no card appends one card,
    then the record and its own files go. Every other settled state — a card
    already present, ``failed``, ``missing``, an unregistered archetype, or a
    ``done`` record without a presentable output — drops the record and its
    unreferenced files without creating a card. The record is deleted only
    after the card append committed; the classic files are unlinked only after
    the record is gone, so an interruption leaves work the next pass completes
    (a copy is an orphan file the prune reclaims in the same startup).
    """
    status = str(record.db.status or "")
    if status in ArtAssetStatus.ACTIVE:
        return "skipped"
    try:
        subject = scene_subject_for(str(record.db.subject_key or ""))
    except ArtSubjectError:  # observability: ignore R2: an unregistered archetype is the documented drop case
        subject = None
    converted = False
    if subject is not None and status == ArtAssetStatus.DONE:
        identity = _validated_output_identity(subject, record.db.output_identity)
        if identity is not None and not gallery_api.cards_for(subject):
            _convert_classic_scene_output(record, subject, identity)
            converted = True
    identities = _classic_scene_output_identities(record)
    referenced = gallery_api.referenced_stored_identities()
    record_name = str(record.db_key)
    record.delete()
    _delete_classic_scene_files(record_name, identities, referenced)
    return "converted" if converted else "dropped"


def migrate_classic_scene_records() -> dict:
    """Startup conversion of settled classic scene records into scene gallery cards.

    Runs at every startup immediately BEFORE ``prune_gallery_orphans`` (design
    D2), so a copy whose card append failed is an unreferenced ``gallery/``
    file the prune deletes in the same startup, while a record whose deletion
    failed is retried at the next one. Idempotent: a second pass finds no
    classic scene records and changes nothing. Every record is converted or
    dropped independently — one failure is a bounded diagnostic carrying the
    record key and never aborts startup or the remaining records. Returns and
    emits ``{"converted", "dropped", "skipped"}``.
    """
    counts = {"converted": 0, "dropped": 0, "skipped": 0}
    records = [
        record
        for record in ArtAssetRecord.objects.all()
        if not is_gallery_job(record)
        and str(record.db.kind or "") == ArtSubjectKind.SCENE.value
    ]
    records.sort(key=lambda record: str(record.db_key))
    for record in records:
        try:
            counts[_migrate_classic_scene_record(record)] += 1
        except Exception as error:  # noqa: BLE001 - one bad record never aborts startup
            log_warn(
                "art_scene_migration_failed",
                context={"record": str(record.db_key)},
                exc=error,
            )
    log_info("art_scene_migration", context=counts)
    return counts


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


def _delete_unregistered_classic_records(
    registered_monster_keys: frozenset[str], referenced: set[str]
) -> tuple[int, int]:
    """Delete classic monster records of unregistered keys and their own files.

    Classic outputs live outside ``gallery/``, so the file phase cannot reach
    them: each record's ``output_identity`` and ``prior_output_identity`` are
    unlinked here, through store-root confinement, unless a gallery card
    references the same identity. Files go first and the record only after
    every one of them is gone: a failed unlink keeps the record, so the next
    pass retries instead of leaving a file no record can ever reach again. A
    record whose files are already missing is simply deleted. Returns
    ``(records, files)`` deleted.
    """
    records_deleted = 0
    files_deleted = 0
    for record in list(ArtAssetRecord.objects.all()):
        try:
            if is_gallery_job(record):
                continue
            if str(record.db.kind or "") != ArtSubjectKind.MONSTER.value:
                continue
            if record.db.subject_key in registered_monster_keys:
                continue
            record_name = str(record.db_key)
            unlink_failed = False
            for identity in (record.db.output_identity, record.db.prior_output_identity):
                if not isinstance(identity, str) or not identity or identity in referenced:
                    continue
                resolved = resolved_under_store_root(identity)
                if resolved is None:
                    continue
                try:
                    if not resolved.is_file():
                        continue
                    resolved.unlink()
                    files_deleted += 1
                except OSError as error:
                    unlink_failed = True
                    log_warn(
                        "gallery_prune_failed",
                        context={"phase": "classic-file", "record": record_name, "path": identity},
                        exc=error,
                    )
            if unlink_failed:
                continue
            record.delete()
            records_deleted += 1
        except Exception as error:  # noqa: BLE001 - one bad record never stops the sweep
            log_warn(
                "gallery_prune_failed",
                context={"phase": "classic-record", "record": str(record.db_key)},
                exc=error,
            )
    return records_deleted, files_deleted


def prune_gallery_orphans() -> dict:
    """Idempotent startup reclaim of orphan gallery files and spent records.

    Phases, in order:

    1. Every monster gallery record whose key is not a registered visual
       species is deleted (through the gallery API's sole writer).
    2. The gallery reference set is read (read-only through the gallery API).
    3. Every gallery job record that can never be claimed or published again
       (unresolvable subject, unregistered monster key, or a status outside
       ``pending``/``in_progress``) is deleted, and every classic monster
       record of an unregistered key is deleted together with its own
       unreferenced output files.
    4. Every file under the store root's ``gallery/`` tree that no card of
       any remaining gallery record references is deleted — including the
       cards of the records phase 1 removed.

    The unregistered-key rules run only when the visual registry builds
    non-empty; the classic phase also needs the reference set. Every path is
    resolved through the single store-root confinement helper, so nothing
    outside ``ART_STORE_ROOT`` is ever unlinked, and a referenced file is
    NEVER deleted. Every failure phase is bounded: an unreadable tree or a
    failing deletion is a named diagnostic and the prune continues; the
    function itself never raises, so startup never aborts because of it.

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
        for record in list(ArtAssetRecord.objects.all()):
            try:
                if not is_gallery_job(record):
                    continue
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
    if registered is not None and referenced is not None:
        # Without the reference set a classic file cannot be proven
        # unreferenced, so its record is kept for the next pass instead of
        # being deleted with its files left behind.
        try:
            classic_records, classic_files = _delete_unregistered_classic_records(
                registered, referenced
            )
            records_unregistered += classic_records
            files_deleted += classic_files
        except Exception as error:  # noqa: BLE001 - bounded scan failure
            log_error("gallery_prune_failed", context={"phase": "classic-records"}, exc=error)
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
