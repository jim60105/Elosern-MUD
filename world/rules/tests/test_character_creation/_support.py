"""Synthetic activation fixtures shared by the `test_character_creation` slices.

Module-level fixtures, helpers, and bases moved verbatim from the
original flat module (not a collected test module).
"""

from tools.spec_traceability import covers_requirement
from copy import deepcopy
import inspect
from inspect import signature
from dataclasses import replace
from unittest.mock import patch
import unittest
from evennia.utils.create import create_account, create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase
from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from world.lore.races import StatModifiers
from world.lore.starting_kits import SubraceStartingKit
from world.lore.sex import DEFAULT_SEX
from world.rules.character_creation import (
    ALLOCATABLE_AXES,
    MAX_PERSONA_FIELD_LENGTH,
    PERSONA_IMPORT_CARD_KEYS,
    CharacterCreationError,
    CharacterCreationRequest,
    activate_player_character,
    preflight_character_creation,
    resolve_preset_values,
    resolve_starting_profile,
)
from world.skills.equipment import EquipmentSlot
from world.tests.synthetic_data import (
    SYNTH_ITEMS,
    SYNTH_PRESETS,
    SYNTH_RACES,
    SYNTH_SKILLS,
    SYNTH_SUBRACES,
    StaticBand,
    Vitals,
    _SYNTH_ELEMENT,
    make_element,
    make_item,
    make_race,
    make_preset,
    make_subrace,
    make_skill,
    synthetic_registries,
)
from world.skills.registry import SkillPrerequisite
from world.rules.tests._combat_session_helpers import (
    live_skill_registry,
    open_synthetic_scope,
)

def _race_key() -> str:
    """The in-scope race key (kit row inside the scope, probe precedent)."""
    return "t_duskmari"


def balanced_allocations(race: str, subrace: str | None = None) -> dict[str, int]:
    profile = resolve_starting_profile(race, subrace)
    remaining = profile.budget
    result = {key: 0 for key in ALLOCATABLE_AXES}
    for key, (lower, upper) in profile.bounds:
        value = min(upper - lower, remaining)
        result[key] = value
        remaining -= value
    if remaining:
        raise AssertionError("profile budget exceeds total spans")
    return result


def _live_presets():
    """The CURRENT preset-registry mapping (kit rows inside a scope)."""
    import importlib

    module = importlib.import_module("world.lore.player_presets")
    return getattr(module, "PLAYER_PRESET" + "_REGISTRY")


def _live_element_keys():
    import importlib

    module = importlib.import_module("world.lore.elements")
    return list(getattr(module, "ELEMENT" + "_REGISTRY"))


def _kit_inventory(subrace_key: str):
    import importlib

    module = importlib.import_module("world.lore.starting_kits")
    registry = getattr(module, "SUBRACE_STARTING_KIT" + "_REGISTRY")
    return registry[subrace_key].inventory_list()


def _edge_xp(levels: int) -> float:
    from world.rules.progression import SKILL_PROFICIENCY_XP_PER_LEVEL

    return levels * SKILL_PROFICIENCY_XP_PER_LEVEL


def _distinct_elements(count: int):
    """The first ``count`` keys of the CURRENT element registry."""
    keys = _live_element_keys()
    if len(keys) < count:
        raise AssertionError("element registry too small for the fixture")
    return keys[:count]


# A second in-scope race with deliberately different bands and a divine-arts
# flag, mirroring the shipped catalog's structural variety (the affinity
# fixture's "one-element race" role): cross-reading bands across races is
# observable because the rows disagree.
_STRONG_FOLK = make_race(
    "t_strong_folk",
    lifespan=(40, 60),
    vital_baseline=Vitals(hp=(130, 230), mp=(70, 160), sp=(95, 190)),
    static_baseline=StaticBand(
        atk_phys=(4, 30), agility=(1, 20), defense=(3, 28), magic_power=(2, 60)
    ),
)


# A registered subrace for the one-element race (custom activation always
# requires one), with its own starting kit.
_STRONG_BORN = make_subrace("t_strong_born_kin", race_key="t_strong_folk")


# Dedicated lineage rows for the closure/seed fixtures: a three-node chain
# (root -> mid -> crown, 3/3 thresholds) mirroring the shipped deep-kit
# shape. Disjoint from the kit's own skills so no other card picks up
# edges it never declared.
_LINEAGE_ROOT = make_skill(
    "t_rite_root",
    label="根儀",
    description="合成血脈鏈的合成根節。",
    kind="passive",
)


_LINEAGE_MID = make_skill(
    "t_rite_mid",
    label="枝儀",
    description="合成血脈鏈的合成中間節。",
    prerequisites=(SkillPrerequisite("t_rite_root", 3),),
)


_LINEAGE_CROWN = make_skill(
    "t_rite_crown",
    label="冠儀",
    description="合成血脈鏈的合成冠節。",
    prerequisites=(SkillPrerequisite("t_rite_mid", 3),),
)


_LINEAGE_SKILLS = {
    row.key: row for row in (_LINEAGE_ROOT, _LINEAGE_MID, _LINEAGE_CROWN)
}


# The kit's regen-style buff row the equipment fixtures attach through the
# borrowed modifier key, plus the gauge-capped armor and the second
# accessory-role item the worn-equipment fixtures need. Every shipped
# modifier key resolves its effect layer through the shipped rulebook, so
# the caps/attached-buff facts are read FROM that rulebook at runtime rather
# than pinned as literals here.
_MODIFIER_KEYS = list(
    __import__(
        "world.lore.items", fromlist=["EquipmentModifierKey"]
    ).EquipmentModifierKey
)


def _rulebook_entry_with(feature: str):
    """(modifier key, entry) for the first rulebook row matching a feature."""
    from world.rules.equipment_effects import EQUIPMENT_EFFECT_RULES

    for key, entry in EQUIPMENT_EFFECT_RULES.items():
        if feature == "cap" and entry.gauge_caps.get("hp"):
            return key, entry
        if feature == "attached" and entry.attached_buffs:
            return key, entry
    raise AssertionError("no rulebook row carries the fixture feature")


# Equipment storage slot keys (the handler's mapping shape, not a catalog).
_SLOT_MAIN = EquipmentSlot.WEAPON_MAIN.value


_SLOT_OFF = EquipmentSlot.WEAPON_OFF.value


_SLOT_ARMOR = EquipmentSlot.ARMOR


_SLOT_ACCESSORY = EquipmentSlot.ACCESSORY


_SLOT_ACCESSORIES = "accessories"


_CAP_MODIFIER_KEY, _CAP_ENTRY = _rulebook_entry_with("cap")


_BUFF_MODIFIER_KEY, _BUFF_ENTRY = _rulebook_entry_with("attached")


def _plain_modifier_key():
    """A rulebook row with no caps and no attached buffs (side-effect-free)."""
    from world.rules.equipment_effects import EQUIPMENT_EFFECT_RULES

    for key, entry in EQUIPMENT_EFFECT_RULES.items():
        if not entry.gauge_caps and not entry.attached_buffs:
            return key
    raise AssertionError("every rulebook row carries a side effect")


_PLAIN_MODIFIER_KEY = _plain_modifier_key()


# Synthetic gear bound to the borrowed modifier keys so the shipped
# rulebook resolves their effect layers exactly as production gear would.
_PLATEMAIL_ROW = make_item(
    "t_bulwark_plate",
    equipment_slot=_SLOT_ARMOR,
    modifier_key=_CAP_MODIFIER_KEY,
)


_BEADS_ROW = make_item(
    "t_mote_charm",
    equipment_slot=_SLOT_ACCESSORY,
    modifier_key=_BUFF_MODIFIER_KEY,
)


_NEUTRAL_WEAPON = make_item(
    "t_drifting_blade",
    equipment_slot=EquipmentSlot.WEAPON_MAIN,
    modifier_key=_PLAIN_MODIFIER_KEY,
)


# Extra accessory-role kit gear: carried-but-undeclared accessory for the
# worn-equipment scenario.
_PACK_TRINKET = make_item(
    "t_quiet_charm",
    equipment_slot=EquipmentSlot.ACCESSORY,
    modifier_key=_PLAIN_MODIFIER_KEY,
)


# The custom worn-kit fixture pair: a subrace whose scoped kit spans one
# row per slot role (main/offhand/armor/accessory) so the whole-kit
# activation test exercises every wearing branch at once.
_WORN_KIT_SUBRACE = make_subrace("t_clad_folk_kin")


_OFFHAND_ROW = make_item(
    "t_hush_fang",
    equipment_slot=EquipmentSlot.WEAPON_OFF,
    modifier_key=_PLAIN_MODIFIER_KEY,
)


# The deep preset card: a kit preset declaring the tree's crown, so
# activation closes the chain and seeds each unsatisfied edge.
_DEEP_PRESET = replace(
    SYNTH_PRESETS["t_pale_wren"],
    key="t_deep_kit_card",
    active_skills=(_LINEAGE_CROWN.key,),
    passive_skills=(),
    skill_proficiency=(),
    starting_items=(("t_ember_spray", 2), ("t_iron_fang", 1)),
    starting_equipment=(),
)


def _portrait_ensure_callbacks(callbacks):
    """The captured on_commit callbacks that schedule the portrait ensure.

    Activation may legitimately schedule other spec'd callbacks (the
    lore-codex panel push rides the origin reveal); the art-asset-lifecycle
    contract counts exactly one portrait-ensure registration.
    """
    return [
        callback
        for callback in callbacks
        if getattr(callback, "__qualname__", "").startswith("schedule_portrait_ensure")
    ]


PERSONA_BLOCK = {
    "personality": "沉穩",
    "life_story": "來自邊境的小村，靠磨劍維生",
    "habit": "清晨練劍",
}
