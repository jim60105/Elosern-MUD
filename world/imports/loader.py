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
from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY
from world.observability import log_info, log_warn
from world.rules.npc_identity import validate_npc_title
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
    values = race_floor(RACE_REGISTRY[record["race"]])
    values.update(record["stats"])
    return values


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
    report = validate_character(record)
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
    record: dict[str, Any], typeclass: type[LivingEntity] = NPC
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
    entity = create_object(typeclass, key=record["key"])
    entity.race = record["race"]
    entity.subrace = record.get("subrace")
    entity.sex = record["sex"]
    if isinstance(entity, NPC):
        entity.npc_title = title
    entity._apply_trait_config(
        _trait_config(_resolve_trait_values(record))
    )
    entity.db.disguised_stats = record["disguised_stats"] or None
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
    # Persist the adult identity the art gate reads, and establish the explicit
    # named portrait policy (design D2): the character's unique-portrait subject
    # derives only from this policy, never from its display name or role.
    entity.db.age = record["age"]
    entity.db.apparent_age = record["apparent_age"]
    entity.db.portrait_policy = {"mode": "named", "stable_key": record["key"]}
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
    report = validate_batch(paths)
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
            _instantiate_validated_character(record, typeclass)
            for record in report.character_records
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
