"""Persisted, exam-scoped execution overlays and reducing-only equipment limits.

The later guild-exam lifecycle calls preflight against its proposed real kit,
then activates inside its start transaction. This module never starts an exam.
The module-level profile map is validated at import (rulebook tests re-seat it
through the idempotent ``reload_restriction_profiles`` re-validation).
"""

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from typing import Any

from django.db import transaction
import yaml

from world.lore.items import ITEM_REGISTRY
from world.observability import log_info
from world.rules.equipment import normalized_equipment, sync_equipment_gauge_limits
from world.rules.equipment_effects import equipment_adjustments
from world.rules.progression import can_use_skill
from world.rules.surfaces import (
    attribute_snapshot, restore_attribute_best_effort, restore_traits, snapshot_traits,
)
from world.skills.effects import StatMultiplyEffect
from world.skills.equipment import ACCESSORY_MAX_SLOTS, EquipmentSlot
from world.skills.registry import SKILL_REGISTRY
from world.skills.restrictions import exam_restriction


class RestrictionError(ValueError):
    """The host, kit, or examination identity is not usable."""


@dataclass(frozen=True)
class RestrictionProfile:
    rank: str
    accessory: str | None
    weapon: str
    armor: str
    top_skill: str
    allowed_skills: tuple[str, ...]
    ceilings: Mapping[str, int]
    initiative_agility: int | None


def _lineage(top_key: str, root_key: str) -> tuple[str, ...]:
    """Include both lower sword branches, without granting learned ownership."""
    def ancestry(key, visiting=()):
        if key in visiting or key not in SKILL_REGISTRY:
            raise RestrictionError("invalid examination lineage")
        edges = SKILL_REGISTRY[key].prerequisites
        if not edges:
            return {key}, 0
        roots = set()
        depth = 0
        for edge in edges:
            edge_roots, edge_depth = ancestry(edge.skill_key, (*visiting, key))
            roots.update(edge_roots)
            depth = max(depth, edge_depth + 1)
        return roots, depth

    roots, depth = ancestry(top_key)
    if roots != {root_key}:
        raise RestrictionError("examination top skill is outside the sword lineage")
    return tuple(
        key for key in SKILL_REGISTRY
        if ancestry(key)[0] == roots and ancestry(key)[1] <= depth
    )


def load_restriction_profiles(document: Mapping) -> Mapping[str, RestrictionProfile]:
    """Validate authored references before any restriction can be activated."""
    if not isinstance(document, Mapping) or set(document) != {"sword_root", "guild_exam_policies"}:
        raise RestrictionError("invalid restriction rulebook fields")
    if not isinstance(document["guild_exam_policies"], Mapping):
        raise RestrictionError("restriction profiles must be a mapping")
    profiles = {}
    for rank, row in document["guild_exam_policies"].items():
        if not isinstance(rank, str) or not rank or not isinstance(row, Mapping):
            raise RestrictionError("invalid restriction profile identity")
        if set(row) != {"accessory", "weapon", "armor", "top_skill", "body_skill", "ceilings", "initiative_agility"}:
            raise RestrictionError("invalid restriction profile fields")
        for field, slot in (("weapon", EquipmentSlot.WEAPON_MAIN), ("armor", EquipmentSlot.ARMOR)):
            item = ITEM_REGISTRY.get(row[field])
            if item is None or item.equipment_slot is not slot or item.guild_property:
                raise RestrictionError(f"invalid restriction {field}")
        accessory = row["accessory"]
        if accessory is not None:
            item = ITEM_REGISTRY.get(accessory)
            if item is None or item.equipment_slot is not EquipmentSlot.ACCESSORY or not item.guild_property:
                raise RestrictionError("invalid guild accessory")
        allowed = ["basic_attack", "flee", *_lineage(row["top_skill"], document["sword_root"])]
        body = row["body_skill"]
        if body is not None:
            skill = SKILL_REGISTRY.get(body)
            if skill is None or not any(isinstance(effect, StatMultiplyEffect) and effect.multiplier == 1.2 for effect in skill.parsed_effects):
                raise RestrictionError("invalid permitted body enhancement")
            allowed.append(body)
        ceilings = row["ceilings"]
        if not isinstance(ceilings, Mapping) or any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in ceilings.values()):
            raise RestrictionError("invalid reducing ceilings")
        if ceilings and set(ceilings) != {"hp", "mp", "sp", "atk_phys", "agility", "defense", "magic_power"}:
            raise RestrictionError("incomplete reducing ceilings")
        initiative = row["initiative_agility"]
        if ceilings and (isinstance(initiative, bool) or not isinstance(initiative, int) or initiative <= 0):
            raise RestrictionError("invalid initiative ceiling")
        profiles[rank] = RestrictionProfile(rank, accessory, row["weapon"], row["armor"], row["top_skill"], tuple(dict.fromkeys(allowed)), MappingProxyType(dict(ceilings)), initiative)
    return MappingProxyType(profiles)


#: The shipped rulebook this module validates at import and on every reload.
_RULEBOOK_PATH = Path(__file__).parent / "rulebook" / "guild_exam_restrictions.yaml"

#: The live restriction profile map, keyed by examination rank. Preflight reads
#: it through the module attribute at call time; ``reload_restriction_profiles``
#: rebinds it so a rulebook test or synthetic scope can re-seat the shipped
#: rows.
PROFILES: Mapping[str, RestrictionProfile] = load_restriction_profiles(
    yaml.safe_load(_RULEBOOK_PATH.read_text())
)


def reload_restriction_profiles(path: Path | None = None) -> None:
    """Re-validate and rebind the profile map (idempotent startup sync).

    Reload outside any open synthetic scope: it rebinds the live map to the
    production rows, so profiles a still-open exam scope patched in are dropped
    mid-test (the scope's restore closure then reverts them).
    """
    global PROFILES
    document = yaml.safe_load((path or _RULEBOOK_PATH).read_text())
    PROFILES = load_restriction_profiles(document)


def _permitted_neutral(host, profile, key):
    value = getattr(host.traits, key).value
    multiplier = 1.0
    owned = [
        *host.skills._raw.get("active", []),
        *host.skills._raw.get("passive", []),
    ]
    for skill_key in dict.fromkeys(owned):
        if skill_key not in profile.allowed_skills:
            continue
        skill = SKILL_REGISTRY.get(skill_key)
        if skill is None:
            continue
        for effect in skill.parsed_effects:
            if isinstance(effect, StatMultiplyEffect) and effect.trait == key:
                multiplier *= effect.multiplier
    for grant in host.skills.conferred_grants():
        if grant.skill_key not in profile.allowed_skills:
            continue
        source_skill = SKILL_REGISTRY.get(grant.skill_key)
        if source_skill is None:
            continue
        for effect in source_skill.parsed_effects:
            if isinstance(effect, StatMultiplyEffect) and effect.trait == key:
                multiplier *= effect.multiplier * grant.scale
    return round(value * multiplier)


def preflight_exam_restriction(host: Any, target_rank: str, *, equipment: Mapping | None = None) -> dict:
    """Validate a real proposed kit and natural strength without modifying host."""
    from typeclasses.npcs import NPC

    if not isinstance(host, NPC):
        raise RestrictionError("examination restrictions require an NPC host")
    if exam_restriction(host) is not None:
        raise RestrictionError("host already restricted")
    profile = PROFILES.get(target_rank)
    if profile is None:
        raise RestrictionError("unknown restriction profile")
    proposed = host if equipment is None else SimpleNamespace(db=SimpleNamespace(equipment=equipment))
    kit = normalized_equipment(proposed)
    if kit is None:
        raise RestrictionError("invalid examination loadout")
    if kit.get("weapon_main") != profile.weapon or kit.get("armor") != profile.armor or kit.get("weapon_off") is not None:
        raise RestrictionError("invalid examination military pair")
    accessories = kit.get("accessories")
    if not isinstance(accessories, (list, tuple)) or len(accessories) + bool(profile.accessory) > ACCESSORY_MAX_SLOTS:
        raise RestrictionError("no examination accessory slot")
    for key in accessories:
        item = ITEM_REGISTRY.get(key)
        if item is None or item.equipment_slot is not EquipmentSlot.ACCESSORY or item.guild_property:
            raise RestrictionError("invalid examination accessory loadout")
    if equipment is None:
        inventory = list(host.db.inventory or [])
        for key in (profile.weapon, profile.armor, *accessories):
            if key not in inventory:
                raise RestrictionError("examination equipment is not held")
            inventory.remove(key)
    for key in profile.allowed_skills:
        if key in {"basic_attack", "flee"}:
            continue
        if not can_use_skill(host, SKILL_REGISTRY[key]):
            raise RestrictionError(f"unusable permitted lineage: {key}")
    # The equipment reader accepts the proposed stored mapping without a write.
    gear = equipment_adjustments(proposed)
    neutral = {}
    for key, ceiling in profile.ceilings.items():
        if key in {"hp", "mp", "sp"}:
            if getattr(host.traits, key).base < ceiling:
                raise RestrictionError(f"naturally weak host: {key}")
            continue
        gear_key = "agility_flat" if key == "agility" else key
        target = ceiling - gear.get(gear_key, 0)
        if key == "agility" and target != profile.initiative_agility:
            raise RestrictionError("kit does not preserve initiative reference")
        if target < 0 or _permitted_neutral(host, profile, key) < target:
            raise RestrictionError(f"naturally weak host: {key}")
        neutral[key] = target
    return {"host_id": host.pk, "target_rank": target_rank, "allowed_skills": list(profile.allowed_skills), "ceilings": dict(profile.ceilings), "neutral_ceilings": neutral, "accessory": profile.accessory}


def activate_exam_restriction(host: Any, exam_id: str, target_rank: str) -> None:
    """Issue/wear the real accessory and persist the qualified policy atomically."""
    if not isinstance(exam_id, str) or not exam_id:
        raise RestrictionError("invalid examination identity")
    record = preflight_exam_restriction(host, target_rank)
    snapshots = {key: attribute_snapshot(host, key) for key in ("guild_exam_restriction", "equipment", "inventory")}
    traits = snapshot_traits(host)
    try:
        with transaction.atomic():
            record["exam_id"] = exam_id
            record["previous_equipment"] = normalized_equipment(host)
            record["previous_inventory"] = list(host.db.inventory or [])
            if record["accessory"]:
                inventory = [*record["previous_inventory"], record["accessory"]]
                equipment = deepcopy(record["previous_equipment"])
                equipment["accessories"] = [*equipment["accessories"], record["accessory"]]
                host.db.inventory = inventory
                host.db.equipment = equipment
            host.db.guild_exam_restriction = record
            sync_equipment_gauge_limits(host)
    except Exception:
        for key, snapshot in snapshots.items():
            restore_attribute_best_effort(host, key, snapshot)
        restore_traits(host, traits)
        raise
    log_info("guild_exam_restriction_activate", context={"exam": exam_id, "host": host.pk, "target": target_rank})


def remove_exam_restriction(host: Any, exam_id: str) -> bool:
    """Remove only the named exam's overlay; an absent record is idempotent."""
    record = exam_restriction(host)
    if record is None:
        return False
    if record["exam_id"] != exam_id:
        raise RestrictionError("examination restriction identity mismatch")
    snapshots = {key: attribute_snapshot(host, key) for key in ("guild_exam_restriction", "equipment", "inventory")}
    traits = snapshot_traits(host)
    try:
        with transaction.atomic():
            host.db.equipment = deepcopy(dict(record["previous_equipment"]))
            host.db.inventory = list(record["previous_inventory"])
            host.attributes.remove("guild_exam_restriction")
            sync_equipment_gauge_limits(host)
    except Exception:
        for key, snapshot in snapshots.items():
            restore_attribute_best_effort(host, key, snapshot)
        restore_traits(host, traits)
        raise
    log_info("guild_exam_restriction_remove", context={"exam": exam_id, "host": host.pk, "target": record["target_rank"]})
    return True
