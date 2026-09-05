"""All-or-nothing construction of validated imported characters."""

from pathlib import Path
from typing import Any

from django.db import transaction
from evennia.utils.create import create_object

from typeclasses.entities import LivingEntity
from typeclasses.npcs import NPC
from world.imports import assembly
from world.imports.validate import (
    BatchReport,
    Issue,
    validate_batch,
    validate_character,
)
from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY
from world.observability import log_info, log_warn
from world.rules import profession_config
from world.rules.npc_identity import validate_npc_title
from world.rules.npc_schedules import set_npc_schedule
from world.rules.profession_assembly import (
    ProfessionAssemblyError,
    assemble_profession_components,
)
from world.rules.traits import _trait_config, build_initial_traits, race_floor


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


def _resolve_trait_values(
    record: dict[str, Any], tier: str | None = None
) -> dict[str, int]:
    """Build the trait values the record's stats describe.

    The tier branch is the profession line's ONLY tier influence (design D4):
    it runs when the caller passes a registry ``default_tier`` AND the record
    declares no literal stats, and it routes through the race-baseline tiered
    construction (``build_initial_traits(race, subrace, tier)`` — the same
    construction ``initial_trait_config`` wraps). A record declaring any
    literal stat keeps the unchanged race-floor-plus-literals path, and every
    ``tier=None`` call is byte-identical to the pre-change loader.
    """
    stats = record["stats"]
    if tier is not None and not stats:
        return build_initial_traits(record["race"], record.get("subrace"), tier)
    values = race_floor(RACE_REGISTRY[record["race"]])
    values.update(stats)
    return values


def _apply_profession(
    record: dict[str, Any],
    entity: LivingEntity,
    typeclass: type[LivingEntity],
    profession_row: profession_config.Profession | None = None,
) -> None:
    """Assemble the record's profession blueprint onto the constructed entity.

    Runs inside the caller's all-or-nothing transaction, after the attribute
    writes. The validation phase already rejected an incomplete plan as a
    named batch issue; this is the second, fail-closed gate (the same
    ``resolve_plan`` the validator ran), so the batch can never persist a
    half-assembled or identity-less component set. Construction uses the
    validator's resolved ROW snapshot (``profession_row``) whenever the caller
    is the validated boundary, never a fresh cache lookup, so a rulebook
    reload between the two gates cannot mix rows inside one entity. An absent
    ``profession`` is a no-op on the first statement — the byte-identity
    guarantee.
    """
    profession_key = record.get("profession")
    if not profession_key:
        return
    if not issubclass(typeclass, NPC):
        # Unreachable through the validated load boundary (validation names it
        # as an issue); the explicit raise keeps a direct caller honest.
        raise ValueError(
            f"record {record['key']!r}: profession {profession_key!r} assembles "
            f"NPC components only, not {typeclass.__name__}"
        )
    profession = (
        profession_row
        if profession_row is not None
        else profession_config.get_profession(profession_key)
    )
    if profession is None:
        raise ValueError(
            f"record {record['key']!r}: unknown profession {profession_key!r}"
        )
    # The shared deterministic-core attach mechanism (declarative-service-hosts):
    # the same helper the guild service-host sync calls, so import and sync
    # assembly can never drift. Its identity-gap check is this function's
    # second gate, translated verbatim into the record-named ValueError the
    # batch-rejection path expects.
    try:
        attached = assemble_profession_components(
            entity, profession, assembly.explicit_map(record)
        )
    except ProfessionAssemblyError as error:
        named = "; ".join(
            f"component {type_key!r} is missing authored identity kwargs {fields}"
            for type_key, fields in sorted(error.missing.items())
        )
        raise ValueError(f"record {record['key']!r}: profession {named}") from error
    if profession.schedule_template is not None and isinstance(entity, NPC):
        set_npc_schedule(
            entity,
            {"schema_version": 1, "template": profession.schedule_template},
        )
    # Emitted only when the enclosing transaction commits: a later record can
    # still fail and roll the whole batch back, and a success event must never
    # describe an NPC that was never persisted. The context is frozen at
    # registration time.
    transaction.on_commit(
        lambda context={
            "char": record["key"],
            "profession": profession_key,
            "components": list(attached),
        }: log_info("import_profession_assembled", context=context)
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
        entity = _instantiate_validated_character(
            report.record, typeclass, report.profession_row
        )
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


def _profession_default_tier(
    record: dict[str, Any],
    profession_row: profession_config.Profession | None = None,
) -> str | None:
    """The row's default tier, visible only to the empty-stats trait path."""
    profession_key = record.get("profession")
    if not profession_key or record["stats"]:
        return None
    profession = (
        profession_row
        if profession_row is not None
        else profession_config.get_profession(profession_key)
    )
    return profession.default_tier if profession is not None else None


def _instantiate_validated_character(
    record: dict[str, Any],
    typeclass: type[LivingEntity] = NPC,
    profession_row: profession_config.Profession | None = None,
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
        _trait_config(
            _resolve_trait_values(
                record, _profession_default_tier(record, profession_row)
            )
        )
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
    _apply_profession(record, entity, typeclass, profession_row)
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
            _instantiate_validated_character(
                record_report.record, typeclass, record_report.profession_row
            )
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
