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
from world.lore.races import RACE_REGISTRY
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


def _instantiate_validated_character(
    record: dict[str, Any], typeclass: type[LivingEntity] = NPC
) -> LivingEntity:
    entity = create_object(typeclass, key=record["key"])
    entity.race = record["race"]
    entity.subrace = record.get("subrace")
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
    return entity


def load_batch(
    paths: list[Path], typeclass: type[LivingEntity] = NPC
) -> list[LivingEntity]:
    report = validate_batch(paths)
    if not report.all_valid:
        raise ImportRejected(report)
    with transaction.atomic():
        return [
            _instantiate_validated_character(record, typeclass)
            for record in report.character_records
        ]
