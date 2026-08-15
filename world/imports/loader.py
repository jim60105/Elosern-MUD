"""All-or-nothing construction of validated imported characters."""

from pathlib import Path
from typing import Any

from django.db import transaction
from evennia.utils.create import create_object

from typeclasses.entities import LivingEntity
from typeclasses.npcs import NPC
from world.imports.validate import (
    BatchReport,
    validate_batch,
    validate_character,
)
from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY
from world.rules.traits import _trait_config, race_floor


class ImportRejected(Exception):
    def __init__(self, report: BatchReport):
        super().__init__("import batch rejected")
        self.report = report


def _resolve_trait_values(record: dict[str, Any]) -> dict[str, int]:
    values = race_floor(RACE_REGISTRY[record["race"]])
    values.update(record["stats"])
    return values


def instantiate_character(
    record: dict[str, Any], typeclass: type[LivingEntity] = NPC
) -> LivingEntity:
    report = validate_character(record)
    if not report.is_valid:
        raise ImportRejected(BatchReport([report]))
    return _instantiate_validated_character(record, typeclass)


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
    entity = create_object(typeclass, key=record["key"])
    entity.race = record["race"]
    entity.subrace = record.get("subrace")
    entity.sex = record["sex"]
    entity._apply_trait_config(
        _trait_config(_resolve_trait_values(record), RACE_REGISTRY[record["race"]].magic_cap)
    )
    entity.db.disguised_stats = record["disguised_stats"] or None
    entity.db.persona = record["persona"]
    entity.db.sexual = record["sexual_baseline"]
    entity.db.skills = {
        "active": record["skills"],
        "passive": record["passives"],
    }
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
    report = validate_batch(paths)
    if not report.all_valid:
        raise ImportRejected(report)
    with transaction.atomic():
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
        return entities
