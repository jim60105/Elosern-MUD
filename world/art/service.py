"""The sole writer of art asset/queue records and its deterministic seams.

``world/art/service.py`` owns every write to asset/queue records (design D1).
Presenters, workers, browsers, and ``world/ai`` never write them. The seams
reachable from gameplay are all deterministic:

- ``art_sync_all()`` -- idempotent startup sync of scene + generic-monster
  subjects (scene records classic, monster subjects gallery-guarded) and
  recovery of explicit named portrait policies.
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
force path that bypasses that guard. Scenes stay on the classic subject-keyed
pipeline; monster routing arrived with ``gallery-monster-autogen`` below.

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
monster tier through it instead of the classic subject-keyed ``ensure``. The
classic generic-monster record is retired from production: the scene kind
becomes the only classic-record producer on any path — ``@art retry``'s
classic arm likewise skips every gallery-bearing kind, so a legacy monster
record is never reactivated or reset. Pre-existing classic monster records
are left in place — not deleted, not reset — and keep resolving through the
display chain's classic step. Startup order guarantees a seed card occupies
the gallery before the automatic pass: ``art_sync_all`` runs AFTER the
gallery prune and seed synchronization.
"""

import uuid
from pathlib import Path

from django.conf import settings
from django.db import transaction

from world.observability import log_error, log_info, log_warn

from world.art import gallery as gallery_api
from world.art import gallery_kinds
from world.art.gallery_prompt import (
    GalleryPromptError,
    validate_custom_prompt,
    validate_fields,
)
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
    ArtSubject,
    ArtSubjectKind,
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


#: The typed producers that re-validate a supplied/referenced subject for a
#: registry-backed gallery kind (``gallery-monster-generation``). A kind with
#: no entry here is either entity-derived (character, resolved through
#: ``_living_entity_for_stable_key``) or declares no gallery at all; presence
#: in this mapping always agrees with the kind's gallery declaration.
_GALLERY_REGISTRY_PRODUCERS = {ArtSubjectKind.MONSTER.value: monster_subject_for}


def _standard_gallery_request_kwargs(capability) -> dict:
    """The standard deterministic staff/automatic request shape for a kind.

    The ``appearance``-only selection belongs to the character vocabulary and
    is passed only where the declaration supports field selection; a kind
    without it requests with no selection. Every such request carries the
    shared default face rectangle and no binding or free text.
    """
    fields = ("appearance",) if capability.supports_field_selection else ()
    return {"fields": fields, "face_rect": dict(gallery_api.DEFAULT_FACE_RECT)}


def _guarded_gallery_request(subject, entity) -> bool:
    """One guarded automatic-path-style request for a resolved gallery subject.

    Returns True when a gallery generation was requested, False when the
    automatic-generation guard suppressed it. For a kind that declares the
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
    ``ArtSubject`` (a registry-backed subject such as a monster tier).
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
    monster tier key and a kind-order scan could then re-drive the wrong
    subject (``gallery-monster-generation``, design: collision safety). The
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

    * registry-backed kinds re-validate through the kind's typed producer
      (an unregistered registry entry is the producer's typed rejection —
      the caller's key alone is never trusted);
    * character-kind keys resolve through the module's existing stable-key
      live-entity lookup and the existing typed subject producer;
    * every other kind (today: scene) has no subject behind a bare key and
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
    """Idempotently ensure every registered subject, routed by its kind's gallery declaration.

    The scene kind declares no gallery and stays on the classic
    subject-keyed ``ensure`` — the only classic-record producer left (change
    ``gallery-monster-autogen``). Every monster tier routes through the
    shared automatic-ensure helper under the same gallery guard every
    character path uses, and startup never writes a classic record for it;
    a pre-existing classic monster record is left in place and keeps
    resolving through the display chain's classic step. Every failure is
    bounded per subject so one bad entry never aborts the remaining sync.
    """
    for archetype in SCENE_ARCHETYPE_REGISTRY:
        try:
            subject = scene_subject_for(archetype)
            queue_ensure(subject, description_for(subject))
        except ArtSubjectError as error:
            log_warn("art_startup_sync_skipped", context={"kind": "scene", "key": archetype}, exc=error)
    for tier in MONSTER_TIER_REGISTRY:
        try:
            subject = monster_subject_for(tier)
            _ensure_gallery_subject(subject)
        except Exception as error:  # noqa: BLE001 - bounded per tier, never aborts startup
            log_warn("art_startup_sync_skipped", context={"kind": "monster", "key": tier}, exc=error)


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

    Routes every ``SCENE_ARCHETYPE_REGISTRY`` entry through the classic
    ensure and every ``MONSTER_TIER_REGISTRY`` entry through the shared
    gallery automatic-ensure helper, then rescans living characters carrying
    an explicit named portrait policy. Every record write flows through the
    queue under the shared lock; a failure is bounded and never aborts
    startup. Runs as a startup step AFTER ``art_gallery_prune`` and
    ``art_seed_sync`` so a seed card always occupies a subject's gallery
    before the automatic guard reads it.
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
    subject such as a monster tier is re-validated through its kind's typed
    producer, never trusted from the caller's key alone). EVERY precondition
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
    # The face rectangle is shared gallery-card metadata, not a kind
    # capability: a supplied rect is validated for every gallery kind, and
    # ``None`` keeps the shared default downstream.
    if face_rect is not None:
        face_rect = gallery_api.validate_face_rect(face_rect)
    # 3. The declared age precondition, read immediately before the request.
    # A kind without the declaration never reads the age attribute at all.
    age = None
    if capability.requires_age_precondition:
        if entity is None:
            raise ArtSubjectError(
                f"a gallery request for {subject.full()!r} requires the entity carrying the portrait subject"
            )
        age, _apparent_age = character_ages(entity)
    # 4. Description: the selection and free text exist only where declared;
    # a kind without them gets its registry-driven description (monster kind)
    # or base identity text — never an empty character description.
    description = description_for(
        subject,
        entity=entity,
        age=age,
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
