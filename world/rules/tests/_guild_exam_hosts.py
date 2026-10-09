"""Synthetic branch-qualified persistent exam hosts for guild-exam tests.

Builds one persistent adventurer NPC with a normal outfit that differs from
the synthetic exam kit, a real guild limit accessory, a usable synthetic
sword root, canonical age, a persona card, and the provenance/qualification
bindings ``qualified_host`` resolves -- all from synthetic rows, never shipped
people, items or restriction profiles.
"""

from __future__ import annotations

from contextlib import ExitStack
from types import MappingProxyType
from unittest.mock import patch

from evennia.utils.create import create_object

from typeclasses.npcs import NPC
from world.lore.guild_adventurers import ExamQualification, GuildAdventurer
from world.lore.items import EquipmentModifierKey
from world.lore.npc_card import NpcCard, NpcCardIdentity
from world.rules.equipment import toggle_equipment
from world.rules.equipment_effects import EquipmentEffectRule
from world.rules.guild_exam_restrictions import RestrictionProfile
from world.rules.human_guild_hosts import PERSON_ATTRIBUTE
from world.skills.equipment import EquipmentSlot
from world.skills.handler import INNATE_SKILL_KEYS
from world.tests.synthetic_data import make_item, make_skill

HOST_PERSON_KEY = "t_exam_person"
HOST_NAME = "合成考官‧霜脊"
HOST_AGE = 41

EXAM_ROOT = make_skill("t_exam_root_cut", effects=["damage:none:physical"], cost={})
NORMAL_BLADE = make_item("t_exam_normal_blade", equipment_slot=EquipmentSlot.WEAPON_MAIN, modifier_key=EquipmentModifierKey.PLAIN_SWORD)
NORMAL_ARMOR = make_item("t_exam_normal_armor", equipment_slot=EquipmentSlot.ARMOR, modifier_key=EquipmentModifierKey.LEATHER_ARMOR)
NORMAL_CHARM = make_item("t_exam_normal_charm", equipment_slot=EquipmentSlot.ACCESSORY, modifier_key=EquipmentModifierKey.SILVER_HAIRPIN)
KIT_BLADE = make_item("t_exam_kit_blade", equipment_slot=EquipmentSlot.WEAPON_MAIN, modifier_key=EquipmentModifierKey.PLAIN_SWORD)
KIT_ARMOR = make_item("t_exam_kit_armor", equipment_slot=EquipmentSlot.ARMOR, modifier_key=EquipmentModifierKey.LEATHER_ARMOR)
LIMIT_RING = make_item("t_exam_limit_ring", equipment_slot=EquipmentSlot.ACCESSORY, modifier_key=EquipmentModifierKey.GUILD_LIMIT_D, sellable=False, guild_property=True)

EXAM_ITEMS = {item.key: item for item in (NORMAL_BLADE, NORMAL_ARMOR, NORMAL_CHARM, KIT_BLADE, KIT_ARMOR, LIMIT_RING)}
EXAM_SKILLS = {EXAM_ROOT.key: EXAM_ROOT}

# Reducing ceilings well below the host's literal bases, so the restriction
# visibly lowers the persistent host; equipment effects are zeroed below.
_CEILINGS = MappingProxyType({
    "hp": 60, "mp": 40, "sp": 40, "atk_phys": 6, "agility": 5, "defense": 6, "magic_power": 5,
})


def _profile(rank: str) -> RestrictionProfile:
    return RestrictionProfile(
        rank, LIMIT_RING.key, KIT_BLADE.key, KIT_ARMOR.key, EXAM_ROOT.key,
        (*INNATE_SKILL_KEYS, EXAM_ROOT.key), _CEILINGS, 5,
    )


EXAM_PROFILES = MappingProxyType({rank: _profile(rank) for rank in ("E", "D")})
_ZERO_RULE = EquipmentEffectRule({}, {}, (), (), 0)
EXAM_EFFECT_RULES = {item.modifier_key: _ZERO_RULE for item in EXAM_ITEMS.values()}

CARD = NpcCard(
    identity=NpcCardIdentity(public="合成分會的常駐冒險者，偶爾主持升階考核。"),
    appearance="身形結實，披著褪色斗篷，腰間掛一柄舊劍。",
    personality="沉穩、講規矩，對後輩有耐心。",
    speech_style="句子短，語氣平穩。",
    life_story="在合成港口長大，靠護送委託累積名聲。",
    habit="清晨擦劍，傍晚記帳。",
)


def exam_scope_extra() -> dict[str, dict[str, object]]:
    """Synthetic rows the exam host fixture adds to an open registry scope."""
    return {"skills": dict(EXAM_SKILLS), "items": dict(EXAM_ITEMS)}


def install_exam_host_policies(test, branch_key: str) -> None:
    """Patch restriction profiles, equipment rules and the qualification table."""
    person = GuildAdventurer(
        HOST_PERSON_KEY, HOST_NAME, "合成常駐冒險者", "t_exam_person_profile",
        "t_exam_home", "B", "t_coastal", (200, 120, 120, 40, 40, 40, 40),
        EXAM_ROOT.key, (NORMAL_BLADE.key, NORMAL_ARMOR.key), "t_exam_routine",
        branch_key=branch_key,
    )
    stack = ExitStack()
    test.addCleanup(stack.close)
    for target, value in (
        ("world.rules.guild_exam_restrictions.PROFILES", EXAM_PROFILES),
        ("world.rules.equipment_effects.EQUIPMENT_EFFECT_RULES", EXAM_EFFECT_RULES),
        ("world.rules.human_guild_hosts.ADVENTURER_REGISTRY", MappingProxyType({person.key: person})),
        ("world.rules.human_guild_hosts.EXAM_QUALIFICATIONS", tuple(
            ExamQualification(branch_key, rank, person.key) for rank in EXAM_PROFILES
        )),
    ):
        stack.enter_context(patch(target, value))


def make_exam_host(location, *, key: str = HOST_NAME) -> NPC:
    """One persistent qualified adventurer wearing its normal outfit."""
    from typeclasses.npcs import ensure_npc_canonical_age
    from world.rules.npc_persona import initialize_npc_persona

    host = create_object(NPC, key=key, location=location)
    host.race = "human"
    host.apply_race_baseline()
    host.attributes.add(PERSON_ATTRIBUTE, HOST_PERSON_KEY)
    for gauge_key in ("hp", "mp", "sp"):
        gauge = host.traits.get(gauge_key)
        gauge.base = 200
        gauge.rate = 0
        gauge.current = 200
    for stat_key in ("atk_phys", "agility", "defense", "magic_power"):
        host.traits.get(stat_key).base = 40
    host.db.skills = {"active": [EXAM_ROOT.key], "passive": []}
    host.db.skill_proficiency = {EXAM_ROOT.key: 350.0}
    ensure_npc_canonical_age(host, age=HOST_AGE, apparent_age=HOST_AGE)
    initialize_npc_persona(host, CARD.to_record(), {"kind": "profile", "profile": "t_exam_person_profile"})
    host.db.inventory = [NORMAL_BLADE.key, NORMAL_ARMOR.key, NORMAL_CHARM.key]
    for item_key in host.db.inventory:
        outcome = toggle_equipment(host, item_key)
        if outcome.outcome != "success":
            raise AssertionError(f"synthetic normal outfit rejected: {outcome}")
    return host
