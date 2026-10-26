"""All-or-nothing construction of validated imported characters."""

from pathlib import Path
from typing import Any

from django.db import transaction
from evennia.utils.create import create_object

from typeclasses.entities import LivingEntity
from typeclasses.npcs import NPC
from world.imports.validate import (
    BatchReport,
    Issue,
    validate_batch,
    validate_character,
)
from world.lore.npc_card import normalize_card
from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY
from world.observability import log_info, log_warn
from world.rules.fatigue import initialize_fatigue_state
from world.rules.npc_identity import validate_npc_title
from world.rules.npc_capabilities import (
    CapabilityValidationError,
    assemble_capabilities,
    validate_capabilities,
)
from world.rules.npc_persona import initialize_npc_persona
from world.rules.traits import _trait_config, race_floor


class ImportRejected(Exception):
    def __init__(self, report: BatchReport):
        super().__init__("import batch rejected")
        self.report = report


def _log_rejection(
    report: BatchReport, typeclass: type[LivingEntity], reason: str
) -> None:
    """Warn at a batch rejection site; context carries batch-level ids only."""
    log_warn(
        "import_batch_rejected",
        context={
            "records": len(report.records),
            "rejected": sum(1 for record in report.records if not record.is_valid),
            "typeclass": typeclass.__name__,
            "reason": reason,
        },
    )


def _flag_existing_npc_names(report: BatchReport) -> list[str]:
    """Attach a ``key`` rejection to every valid record colliding with a persisted NPC.

    The author-supplied name at the import face is the record ``key`` -- the
    value every display surface composes with the title -- and NPC names are
    world-unique (npc-identity-titles). The check lives here, not in the CLI:
    a file linter cannot answer "is this name taken right now", and the query
    only carries meaning inside the load transaction (design D4). The check is
    a lookup-then-create predicate without a database uniqueness constraint
    (Evennia object keys are deliberately not globally unique across
    typeclasses), so the two public loader boundaries declare the explicit
    operational precondition below: imports that share the NPC key namespace
    must be serialized by their caller.

    ``filter_family`` is the family query: ``NPC.objects.filter`` pins the
    exact typeclass path and would miss subclasses such as ``LLMNPC`` (design
    D5). Fail-closed collision semantics (design D6): never reuse, rename, or
    overwrite an existing entity. A key held by a player character, monster,
    room or object is NOT a collision -- the invariant covers NPC names only.
    """
    keys = sorted({record["key"] for record in report.character_records})
    if not keys:
        return []
    taken = set(
        NPC.objects.filter_family(db_key__in=keys).values_list("db_key", flat=True)
    )
    if not taken:
        return []
    for record_report in report.records:
        if (
            record_report.is_valid
            and record_report.record is not None
            and record_report.record.get("record_type") == "character"
            and record_report.record["key"] in taken
        ):
            record_report.rejections.append(
                Issue(
                    "key",
                    f"npc name {record_report.record['key']!r} already used "
                    "by an existing NPC",
                )
            )
    return sorted(taken)


def _resolve_trait_values(record: dict[str, Any]) -> dict[str, int]:
    """Build the trait values the record's stats describe, literally.

    Every record loads the same way: the race floor for the keys the record
    omits, the record's own literal values for the ones it supplies. No
    capability, declaration order or authored default multiplies, re-derives or
    replaces a stated value.
    """
    values = race_floor(RACE_REGISTRY[record["race"]])
    values.update(record["stats"])
    return values


def _resolve_capability_rooms(tag: str) -> list[Any]:
    """Every tagged object the capability core may inspect for one anchor."""
    from evennia.utils.search import search_object_by_tag

    return list(search_object_by_tag(tag))


def _apply_capabilities(
    record: dict[str, Any],
    entity: LivingEntity,
    typeclass: type[LivingEntity],
) -> None:
    """Assemble the record's declared capabilities onto the constructed entity.

    Runs inside the caller's all-or-nothing transaction, after the attribute
    writes. The validation phase already rejected an unusable declaration set
    as a named batch issue; this is the second, fail-closed gate: the SAME
    shared core re-validates the complete declaration set with a room resolver,
    and the assembler attaches exactly the plan it returns. A missing,
    ambiguous or non-Room anchor therefore rejects the whole batch (prepared
    entities included) instead of persisting a half-assembled host. A record
    declaring no capabilities is a no-op on the first statement.
    """
    entries = record.get("components")
    if not entries:
        return
    if not issubclass(typeclass, NPC):
        raise ValueError(
            f"record {record['key']!r}: capability components assemble NPCs "
            f"only, not {typeclass.__name__}"
        )
    try:
        plan = validate_capabilities(
            entries, room_resolver=_resolve_capability_rooms
        )
        attached = assemble_capabilities(entity, plan)
    except CapabilityValidationError as error:
        raise ValueError(f"record {record['key']!r}: {error}") from error
    # Emitted only when the enclosing transaction commits: a later record can
    # still fail and roll the whole batch back, and a success event must never
    # describe an NPC that was never persisted. The context is frozen at
    # registration time.
    transaction.on_commit(
        lambda context={
            "char": record["key"],
            "components": list(attached),
        }: log_info("import_capabilities_assembled", context=context)
    )


def instantiate_character(
    record: dict[str, Any], typeclass: type[LivingEntity] = NPC
) -> LivingEntity:
    """Validate one record and construct it, upholding NPC-name uniqueness.

    Serialization precondition (npc-identity-titles): the existing-NPC name
    gate is a lookup-then-create predicate, not a database constraint. A
    caller running concurrent imports that can share the NPC key namespace
    MUST serialize them outside this function (single content-loading writer,
    one import at a time); an ordinary transaction does not serialize a
    missing-row check.
    """
    report = validate_character(record, typeclass)
    if not report.is_valid:
        rejected = BatchReport([report])
        _log_rejection(rejected, typeclass, "validation")
        raise ImportRejected(rejected)
    with transaction.atomic():
        # The same existing-NPC name gate load_batch applies (design D4): the
        # public single-record entry is a load boundary too, and the world's
        # NPC-name namespace does not care which entry point arrived first.
        single = BatchReport([report])
        if _flag_existing_npc_names(single):
            _log_rejection(single, typeclass, "existing_npc_name")
            raise ImportRejected(single)
        # The validated record carries the lineage auto-seed normalization
        # (use-driven-skill-lineage DC6): ownership closure and exact seeded
        # proficiency. Instantiate exactly what was validated.
        entity = _instantiate_validated_character(report.record, typeclass)
    # Only after the transaction exited successfully (same contract as
    # load_batch's commit event).
    log_info(
        "import_batch_committed",
        context={"records": 1, "typeclass": typeclass.__name__},
    )
    return entity


def _resolve_affinity_elements(record: dict[str, Any]) -> list[str]:
    """Resolve the record's affinity set or the elf subrace seed.

    A record carrying ``affinity_elements`` persists it verbatim (validated
    semantically before load). An elf record never carries a set -- the loader
    seeds it from ``SUBRACE_REGISTRY[subrace].affinity_elements`` so no elf
    can contradict its subrace (element-affinity-progression D3).
    """
    race_key = record["race"]
    if race_key == "elf":
        from world.rules.character_creation import validate_affinity_seed

        subrace = SUBRACE_REGISTRY[record["subrace"]]
        seed = validate_affinity_seed(subrace.affinity_elements)
        return list(seed)
    return list(record.get("affinity_elements") or ())


def _instantiate_validated_character(
    record: dict[str, Any],
    typeclass: type[LivingEntity] = NPC,
) -> LivingEntity:
    # The title's second, fail-closed gate runs BEFORE construction (design
    # D3): a caller that reached this seam with an unvalidated record raises
    # here instead of leaving a constructed entity behind. The stripped
    # canonical form returned by the validator is what gets persisted.
    # ``npc_title`` is declared as an AttributeProperty on ``NPC`` alone; for
    # any other target typeclass the record's title stays inert — assigning it
    # there would create a plain instance attribute that never survives a
    # reload (silent data loss).
    title = (
        validate_npc_title(record["title"]) if issubclass(typeclass, NPC) else ""
    )
    # The compact card's second, fail-closed gate also runs before
    # construction (npc-persona-import-cards D3): an unvalidated NPC record
    # with a non-card persona raises ``NpcCardError`` here instead of leaving
    # a half-built NPC behind for a caller outside the batch transaction.
    if issubclass(typeclass, NPC):
        normalize_card(record["persona"])
    entity = create_object(typeclass, key=record["key"])
    # Authored construction establishes the full/awake fatigue baseline once;
    # the initializer is absent-only, so it never refills an imported body.
    initialize_fatigue_state(entity)
    if "social_identities" in record and record["social_identities"]:
        from world.rules.social_identity import set_social_identities
        set_social_identities(entity, record["social_identities"])

    entity.race = record["race"]
    entity.subrace = record.get("subrace")
    entity.sex = record["sex"]
    if isinstance(entity, NPC):
        entity.npc_title = title
    entity._apply_trait_config(_trait_config(_resolve_trait_values(record)))
    entity.db.disguised_stats = record["disguised_stats"] or None
    if isinstance(entity, NPC):
        # The shared deterministic persona writer (npc-persona-import-cards
        # D3): the validated card plus versioned metadata with ``import``
        # provenance, inside the caller's batch transaction so a later
        # record's failure rolls both back with the batch.
        #
        # No authored official-content provenance is recorded
        # (official-content-provenance): an import record's shape names no
        # profile identity, and the ``import`` provenance kind below says so.
        # Inferring one from the record key, the display name, a profession, or
        # a service anchor would manufacture an authored identity out of
        # generated/operator text, so this path establishes no
        # ``npc_profile_key`` and the official reference layer resolves nothing
        # for an unprofiled imported NPC.
        initialize_npc_persona(
            entity, record["persona"], {"kind": "import", "record": record["key"]}
        )
    else:
        # Non-NPC targets keep the opaque persona contract: stored verbatim.
        entity.db.persona = record["persona"]
    entity.db.sexual = record["sexual_baseline"]
    entity.db.skills = {
        "active": record["skills"],
        "passive": record["passives"],
    }
    # The lineage auto-seed applied by validation (exact edge values; the
    # record's explicit entries won). Stored inside the same transaction, so
    # a rejected batch persists nothing, seed included.
    entity.db.skill_proficiency = dict(record.get("skill_proficiency") or {})
    entity.db.equipment = record["equipment"]
    entity.db.inventory = record["inventory"]
    entity.db.affinity_elements = _resolve_affinity_elements(record)
    if record.get("combat_traits") is not None:
        from world.rules.traits import set_combat_traits

        set_combat_traits(entity, record["combat_traits"])
    # Persist the canonical ages the art subject model reads, and establish the
    # explicit named portrait policy (design D2): the character's
    # unique-portrait subject derives only from this policy, never from its
    # display name or role.
    entity.db.age = record["age"]
    entity.db.apparent_age = record["apparent_age"]
    entity.db.portrait_policy = {"mode": "named", "stable_key": record["key"]}
    _apply_capabilities(record, entity, typeclass)
    return entity


def load_batch(
    paths: list[Path], typeclass: type[LivingEntity] = NPC
) -> list[LivingEntity]:
    """Validate record files and construct every character in one transaction.

    Serialization precondition (npc-identity-titles): the existing-NPC name
    gate is a lookup-then-create predicate, not a database constraint. A
    caller running concurrent imports that can share the NPC key namespace
    MUST serialize them outside this function (single content-loading writer,
    one batch at a time); an ordinary transaction does not serialize a
    missing-row check.
    """
    report = validate_batch(paths, typeclass)
    if not report.all_valid:
        _log_rejection(report, typeclass, "validation")
        raise ImportRejected(report)
    with transaction.atomic():
        # The existing-NPC name gate runs before anything is constructed
        # (design D4/D6): a hit rejects the whole batch inside the still-open
        # transaction, so nothing is persisted.
        if _flag_existing_npc_names(report):
            _log_rejection(report, typeclass, "existing_npc_name")
            raise ImportRejected(report)
        entities = [
            _instantiate_validated_character(record_report.record, typeclass)
            for record_report in report.character_reports
        ]
        # Post-commit portrait ensure, registered inside the all-or-nothing
        # batch so a rolled-back import emits nothing. The callback is the
        # service's exception-safe wrapper: an art failure never surfaces as an
        # import error (design D7).
        from world.art.service import schedule_portrait_ensure

        for entity in entities:
            schedule_portrait_ensure(entity)
    # Emitted only after the transaction has exited successfully: a commit
    # event must never describe a batch whose commit failed.
    log_info(
        "import_batch_committed",
        context={"records": len(entities), "typeclass": typeclass.__name__},
    )
    return entities
