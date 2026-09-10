"""Evennia-backed tests for deterministic player activation.

Runs entirely on the synthetic kit: race, subrace, static-tier, preset,
skill, item, price, starting-kit, element, and buff catalogs are replaced for
every preflight/activation path, so no shipped catalog identifier appears in
the mechanics under test. Two deliberate production-literal fixtures remain:
the affinity bound map (patched, not a kit target) and the ``elf`` race key,
which the elf subrace-seed rule matches by literal. Shipped-content claims
this suite used to carry (the human budget value, foxkin band facts, the
every-shipped-preset activation sweeps) now live in the registered
data-contract suites ``world/lore/tests/test_races.py`` and
``world/lore/tests/test_player_presets.py``.
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

from ._combat_session_helpers import (
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

# ---------------------------------------------------------------------------
# Synthetic fixtures
# ---------------------------------------------------------------------------
#
# Registry keys below are kit synthetic rows or fixtures derived from them.
# The affinity bound map is production state keyed by race (not a kit
# registry), so the scoped race gets a patch entry; the kit's borrowed
# element key arrives via the kit's own constant.

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


@synthetic_registries(
    "races",
    "static_tiers",
    "subraces",
    "starting_kits",
    "presets",
    "skills",
    "items",
    "prices",
    "elements",
    extra={
        "races": {_STRONG_FOLK.key: _STRONG_FOLK},
        "subraces": {_STRONG_BORN.key: _STRONG_BORN},
        "starting_kits": {
            _STRONG_BORN.key: SubraceStartingKit(
                _STRONG_BORN.key, (("t_thorn_knife", 1),)
            )
        },
        "skills": _LINEAGE_SKILLS,
        "presets": {_DEEP_PRESET.key: _DEEP_PRESET},
        "items": {
            _PLATEMAIL_ROW.key: _PLATEMAIL_ROW,
            _BEADS_ROW.key: _BEADS_ROW,
            _NEUTRAL_WEAPON.key: _NEUTRAL_WEAPON,
            _PACK_TRINKET.key: _PACK_TRINKET,
        },
    },
)
@patch.dict(
    "world.rules.character_creation._AFFINITY_INPUT_BOUNDS",
    {"t_duskmari": 2, "t_strong_folk": 1},
    clear=True,
)
class CharacterActivationTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.account = create_account("creator", "creator@example.test", "testpassword", typeclass=Account)
        self.character = create_object(PlayerCharacter, key="creator-shell")
        self.account.at_post_create_character(self.character)

    def request(self, **overrides):
        values = {
            "mode": "custom",
            "display_name": "  新角色  ",
            "age": 20,
            "apparent_age": 20,
            "race": _race_key(),
            "subrace": next(iter(SYNTH_SUBRACES)),
            "allocations": balanced_allocations(_race_key(), next(iter(SYNTH_SUBRACES))),
        }
        values.update(overrides)
        return CharacterCreationRequest(**values)

    @covers_requirement("player-character-creation::character-creation-offers-preset-and-custom-modes")
    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-starting-inventory")
    def test_activation_persists_identity_traits_and_empty_mechanical_state(self):
        race_key = _race_key()
        old_id, old_location = self.character.id, self.character.location
        result = activate_player_character(
            self.account, self.character, self.request()
        )
        # magic_power is static-band-floor + allocation: derived from the
        # scoped race row, never a pinned shipped number.
        profile = resolve_starting_profile(race_key)
        self.assertEqual(
            result.magic_power,
            profile.bounds_dict()["magic_power"][0]
            + self.request().allocations["magic_power"],
        )
        self.assertEqual(self.character.key, "新角色")
        self.assertEqual((self.character.age, self.character.apparent_age), (20, 20))
        self.assertFalse(self.character.creation_pending)
        self.assertEqual(self.character.traits.magic_power.value, result.magic_power)
        self.assertEqual(self.character.traits.guild_merit.value, 0)
        self.assertEqual(self.character.db.skills, {"active": [], "passive": []})
        self.assertEqual(
            self.character.db.inventory,
            _kit_inventory(next(iter(SYNTH_SUBRACES))),
        )
        self.assertEqual(self.character.wallet, 0)
        self.assertEqual(self.character.id, old_id)
        self.assertEqual(self.character.location, old_location)
        self.assertIn(self.character, self.account.characters)

    @covers_requirement("player-stat-allocation::player-starting-profiles-are-derived-from-immutable-lore-bands")
    def test_static_modifiers_apply_once_after_allocation(self):
        # A subrace with deliberately non-zero modifiers: each counter axis
        # reads floor + allocation, then the modifier applies once through
        # the round rule (never a second copy of the base).
        modified = make_subrace("t_clever_folk_kin", static_modifiers=StatModifiers(atk_phys=-0.10, agility=0.40, defense=-0.30))
        with synthetic_registries("races", "subraces", extra={"subraces": {modified.key: modified}}):
            allocations = balanced_allocations(_race_key(), modified.key)
            request = self.request(
                race=_race_key(), subrace=modified.key, allocations=allocations
            )
            checked = preflight_character_creation(self.account, self.character, request)
            profile = resolve_starting_profile(_race_key(), modified.key)
            bounds = profile.bounds_dict()
            for key in ("atk_phys", "agility", "defense"):
                raw = bounds[key][0] + allocations[key]
                expected = round(raw * (1 + getattr(profile.static_modifiers, key)))
                self.assertEqual(checked.values[key], expected)

    def test_under_and_over_budget_rejections_are_non_mutating(self):
        valid = balanced_allocations(_race_key())
        bounds = resolve_starting_profile(_race_key()).bounds_dict()
        for delta in (-1, 1):
            allocations = dict(valid)
            key = next(key for key in ALLOCATABLE_AXES if 0 <= allocations[key] + delta <= bounds[key][1] - bounds[key][0])
            allocations[key] += delta
            with self.subTest(delta=delta), self.assertRaises(CharacterCreationError):
                activate_player_character(
                    self.account, self.character,
                    self.request(allocations=allocations),
                )
            self.assertEqual(self.character.traits.all(), [])

    @covers_requirement("player-character-creation::character-creation-enforces-canonical-identity-and-registry-compatibility")
    def test_age_name_and_subrace_rejections_are_non_mutating(self):
        foreign = make_subrace("t_outside_blood", race_key="t_not_in_scope")
        requests = (
            self.request(age=-1),
            self.request(apparent_age=10001),
            self.request(display_name="|rbad|n"),
            self.request(subrace=foreign.key),
        )
        with synthetic_registries("subraces", extra={"subraces": {foreign.key: foreign}}):
            for request in requests:
                with self.subTest(request=request), self.assertRaises(CharacterCreationError):
                    activate_player_character(self.account, self.character, request)
                self.assertTrue(self.character.creation_pending)
                self.assertEqual(self.character.traits.all(), [])

    @covers_requirement("player-character-creation::character-creation-offers-preset-and-custom-modes")
    def test_custom_creation_without_a_subrace_is_rejected(self):
        for missing in (None, "", "  ", "none"):
            with self.subTest(missing=missing):
                request = self.request(subrace=missing)
                with self.assertRaisesRegex(
                    CharacterCreationError, "requires a registered subrace"
                ):
                    activate_player_character(self.account, self.character, request)
                self.assertTrue(self.character.creation_pending)
                self.assertEqual(self.character.traits.all(), [])
                self.assertIsNone(self.character.age)

    def test_display_name_rejects_separators_and_the_shared_length_bound(self):
        for name in ("角色/名", "角色:名", "角色}名", "x" * 65):
            with self.subTest(name=name[:6]), self.assertRaises(CharacterCreationError):
                activate_player_character(
                    self.account, self.character,
                    self.request(display_name=name),
                )
            self.assertTrue(self.character.creation_pending)
            self.assertEqual(self.character.traits.all(), [])

    def test_64_character_display_name_is_accepted(self):
        name = "新" * 64
        result = activate_player_character(
            self.account, self.character,
            self.request(display_name=name),
        )
        self.assertEqual(result.display_name, name)
        self.assertEqual(self.character.key, name)

    @covers_requirement(
        "player-stat-allocation::player-starting-profiles-are-derived-from-immutable-lore-bands",
        "player-stat-allocation::custom-starting-stats-require-one-exact-finite-allocation-budget",
    )
    def test_preset_activation_fixes_magic_power_deterministically(self):
        # The retired race-average sampler is replaced by the preset's own
        # allocation: the value is the scoped profile's static floor plus the
        # card's magic_power allocation (mechanics, not a shipped number).
        card = SYNTH_PRESETS["t_pale_wren"]
        # The card declares a starting companion, which spawns at the
        # shell's location (preset-companion-activation).
        self.character.location = self.room1
        result = activate_player_character(
            self.account, self.character,
            CharacterCreationRequest(mode="preset", preset_key=card.key),
        )
        floor = resolve_starting_profile(card.race, card.subrace).bounds_dict()["magic_power"][0]
        self.assertEqual(result.magic_power, floor + dict(card.allocations)["magic_power"])
        self.assertEqual(self.character.race, card.race)

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    def test_preset_activation_grants_the_declared_skill_kit(self):
        # The deep card's closure-added keys are covered by the dedicated
        # close/order tests; parity here is declared-state equality.
        for preset_key in sorted(set(SYNTH_PRESETS) - {_DEEP_PRESET.key}):
            with self.subTest(preset_key=preset_key):
                character = create_object(PlayerCharacter, key=f"shell-{preset_key}")
                self.account.at_post_create_character(character)
                # Companion presets build their twin at the shell's location
                # (preset-companion-activation); production shells live in a
                # room at activation time, so tests place theirs too.
                character.location = self.room1
                activate_player_character(
                    self.account, character,
                    CharacterCreationRequest(mode="preset", preset_key=preset_key),
                )
                self.assertEqual(
                    character.db.skills,
                    _live_presets()[preset_key].skill_lists(),
                )
                self.assertFalse(character.creation_pending)

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    def test_preset_activation_closes_the_deep_kit(self):
        # The in-scope deep card declares only the tree's crown: activation
        # closes the chain (closure-added keys AFTER the declared ones),
        # seeds each unsatisfied edge to exactly its threshold, and clears
        # the preset-mode creation draft in the same transaction.
        character = create_object(PlayerCharacter, key="shell-lineage-close")
        self.account.at_post_create_character(character)
        character.location = self.room1
        character.db.creation_draft = {
            "mode": "preset", "stage": "preset_selected",
            "preset_key": _DEEP_PRESET.key,
        }
        activate_player_character(
            self.account, character,
            CharacterCreationRequest(mode="preset", preset_key=_DEEP_PRESET.key),
        )
        self.assertEqual(
            character.db.skills,
            {
                "active": ["t_rite_crown", "t_rite_mid"],
                "passive": ["t_rite_root"],
            },
        )
        self.assertEqual(
            character.db.skill_proficiency,
            {
                "t_rite_root": _edge_xp(3),
                "t_rite_mid": _edge_xp(3),
            },
        )
        self.assertFalse(character.attributes.has("creation_draft"))
        self.assertFalse(character.creation_pending)

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    def test_every_in_scope_preset_declared_active_skill_is_usable_after_activation(self):
        # Scenario coverage for every card in the scoped registry: after
        # closure + seed, can_use_skill passes for every declared active key.
        from world.rules.progression import can_use_skill

        registry = live_skill_registry()
        for preset_key, preset in _live_presets().items():
            with self.subTest(preset_key=preset_key):
                character = create_object(
                    PlayerCharacter, key=f"gate-shell-{preset_key}"
                )
                self.account.at_post_create_character(character)
                character.location = self.room1
                activate_player_character(
                    self.account, character,
                    CharacterCreationRequest(mode="preset", preset_key=preset_key),
                )
                for skill_key in preset.active_skills:
                    with self.subTest(skill=skill_key):
                        self.assertTrue(can_use_skill(character, registry[skill_key]))

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    def test_custom_activation_writes_empty_skills_and_proficiency(self):
        # Custom mode grants no skills, so the closure and seed are no-ops.
        activate_player_character(self.account, self.character, self.request())
        self.assertEqual(self.character.db.skills, {"active": [], "passive": []})
        self.assertEqual(dict(self.character.db.skill_proficiency or {}), {})

    def _synthetic_preset(self, key, **overrides):
        from world.lore.player_presets import PlayerPreset

        race_key = _race_key()
        subrace_key = next(iter(SYNTH_SUBRACES))
        values = dict(
            key=key, display_name=f"合成{key}", age=20, apparent_age=20,
            race=race_key, subrace=subrace_key,
            allocations=tuple(balanced_allocations(race_key, subrace_key).items()),
            emphasis="測試", sex="female",
        )
        values.update(overrides)
        return PlayerPreset(**values)

    def _activate_synthetic_preset(self, preset, shell_key):
        """Activate a registry-patched synthetic preset on a fresh shell."""
        character = create_object(PlayerCharacter, key=shell_key)
        self.account.at_post_create_character(character)
        with synthetic_registries("presets", extra={"presets": {preset.key: preset}}):
            activate_player_character(
                self.account, character,
                CharacterCreationRequest(mode="preset", preset_key=preset.key),
            )
        return character

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    def test_declared_proficiency_below_the_seed_survives_activation(self):
        # Scenario "A declared proficiency beats the auto-seed": 120 XP is
        # level 2, below the >= 3 edge; the seed must not overwrite the
        # declared value -- while the seed still runs for every OTHER
        # unsatisfied edge of the closed chain.
        preset = self._synthetic_preset(
            "t_lineage_declared",
            active_skills=("t_rite_crown",),
            skill_proficiency=(("t_rite_mid", 120.0),),
        )
        character = self._activate_synthetic_preset(
            preset, "shell-lineage-declared"
        )
        self.assertEqual(
            character.db.skill_proficiency,
            {
                "t_rite_mid": 120.0,  # declared wins, below the edge
                "t_rite_root": _edge_xp(3),  # the seed still runs
            },
        )

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    def test_declared_keys_keep_order_and_closure_added_keys_follow(self):
        # Declared (hush mend, cinder cleave) keeps its order; the
        # closure-added root (sorted registry order) follows the declared
        # ones, and a declared passive stays last.
        preset = self._synthetic_preset(
            "t_lineage_order",
            active_skills=("t_rite_mid", "t_rite_crown"),
            passive_skills=("t_steady_stride",),
        )
        character = self._activate_synthetic_preset(preset, "shell-lineage-order")
        self.assertEqual(
            character.db.skills,
            {
                "active": ["t_rite_mid", "t_rite_crown"],  # declared order
                "passive": [
                    "t_steady_stride",  # declared
                    "t_rite_root",  # closure-added passive follows
                ],
            },
        )

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-starting-inventory")
    def test_preset_activation_grants_the_declared_starting_inventory(self):
        for preset_key in sorted(_live_presets()):
            with self.subTest(preset_key=preset_key):
                character = create_object(PlayerCharacter, key=f"kit-shell-{preset_key}")
                self.account.at_post_create_character(character)
                character.location = self.room1
                activate_player_character(
                    self.account, character,
                    CharacterCreationRequest(mode="preset", preset_key=preset_key),
                )
                expected = _live_presets()[preset_key].inventory_list()
                self.assertEqual(character.db.inventory, expected)
                self.assertGreater(len(expected), 0)

    @covers_requirement("player-character-creation::custom-activation-grants-the-chosen-subrace-s-basic-starting-kit")
    def test_custom_activation_grants_each_subrace_starting_kit(self):
        for subrace_key, subrace in SYNTH_SUBRACES.items():
            with self.subTest(subrace=subrace_key):
                character = create_object(
                    PlayerCharacter, key=f"custom-shell-{subrace_key}"
                )
                self.account.at_post_create_character(character)
                activate_player_character(
                    self.account, character,
                    self.request(
                        race=subrace.race_key,
                        subrace=subrace_key,
                        allocations=balanced_allocations(subrace.race_key, subrace_key),
                    ),
                )
                self.assertEqual(
                    character.db.inventory, _kit_inventory(subrace_key)
                )
                self.assertGreater(len(character.db.inventory), 0)
                self.assertFalse(character.creation_pending)

    # --- preset-starting-equipment ---------------------------------------

    _EQUIP_ITEMS = (
        (_NEUTRAL_WEAPON.key, 1), (_PLATEMAIL_ROW.key, 1),
        (_BEADS_ROW.key, 1), (_PACK_TRINKET.key, 1),
        ("t_ember_spray", 2), ("t_huskapple", 1),
    )

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-starting-inventory")
    def test_preset_activation_wears_the_declared_starting_equipment(self):
        # Scenario "Declared starting equipment is worn at activation" plus
        # "Undeclared items stay in the pack": every declared key lands in
        # its registry slot through the sole writer, the carried-but-
        # undeclared accessory stays in the pack only, and equipped keys
        # remain in canonical inventory.
        preset = self._synthetic_preset(
            "t_equip_worn",
            starting_items=self._EQUIP_ITEMS,
            starting_equipment=(
                _NEUTRAL_WEAPON.key, _PLATEMAIL_ROW.key,
                _BEADS_ROW.key, _PACK_TRINKET.key,
            ),
        )
        character = self._activate_synthetic_preset(preset, "shell-equip-worn")
        self.assertEqual(
            dict(character.db.equipment),
            {
                _SLOT_MAIN: _NEUTRAL_WEAPON.key,
                _SLOT_OFF: None,
                _SLOT_ARMOR: _PLATEMAIL_ROW.key,
                _SLOT_ACCESSORIES: [_BEADS_ROW.key, _PACK_TRINKET.key],
            },
        )
        # Scenario 3.3: the beads' attached buff instance arrives with it,
        # keyed through the rulebook row the item's borrowed modifier binds.
        attached = _BUFF_ENTRY.attached_buffs
        self.assertEqual(len(attached), 1)
        instance_key = f"{attached[0]}:{_BEADS_ROW.key}"
        self.assertIn(instance_key, character.db.buffs)
        self.assertEqual(
            character.db.buffs[instance_key]["definition_key"], attached[0]
        )
        # The undeclared carried accessory occupies no slot but stays held,
        # and equipped keys stay in canonical inventory.
        stored = set(character.db.equipment[_SLOT_ACCESSORIES])
        stored.update(
            v for v in (
                character.db.equipment[_SLOT_MAIN],
                character.db.equipment[_SLOT_OFF],
                character.db.equipment[_SLOT_ARMOR],
            ) if v
        )
        self.assertNotIn("t_huskapple", stored)
        for key, _count in self._EQUIP_ITEMS:
            self.assertIn(key, character.db.inventory)
        self.assertFalse(character.creation_pending)

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-starting-inventory")
    def test_worn_equipment_ceilings_are_computed_from_the_final_traits(self):
        # Scenario (risk pin, design R2): the rulebook's capped row sets the
        # hp ceiling; the recomputation runs after _apply_trait_config, so
        # the stored mod is exactly the worn set's cap against the final base.
        expected_cap = _CAP_ENTRY.gauge_caps["hp"]
        preset = self._synthetic_preset(
            "t_equip_gauge",
            starting_items=((_PLATEMAIL_ROW.key, 1), (_BEADS_ROW.key, 1)),
            starting_equipment=(_PLATEMAIL_ROW.key, _BEADS_ROW.key),
        )
        character = self._activate_synthetic_preset(preset, "shell-equip-gauge")
        # The sole writer recomputes the hp ceiling's mod from scratch as
        # exactly the worn set's cap; GaugeTrait.max is derived as
        # (base + mod) * mult, so pinning mod pins the ceiling.
        self.assertEqual(character.traits.hp.mod, expected_cap)
        attached = _BUFF_ENTRY.attached_buffs
        self.assertIn(f"{attached[0]}:{_BEADS_ROW.key}", character.db.buffs)

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-starting-inventory")
    def test_rejected_equipment_toggle_rolls_activation_back(self):
        # Scenario "A rejected toggle rolls activation back" (design D3):
        # activation raises naming the key and the stable reason, and the
        # shell stays exactly as it was.
        from world.rules.equipment import EquipmentToggleReason, EquipmentToggleResult

        preset = self._synthetic_preset(
            "t_equip_reject",
            starting_items=((_NEUTRAL_WEAPON.key, 1),),
            starting_equipment=(_NEUTRAL_WEAPON.key,),
        )
        character = create_object(PlayerCharacter, key="shell-equip-reject")
        self.account.at_post_create_character(character)
        old_key = character.key
        rejected = EquipmentToggleResult(
            outcome="rejected", reason=EquipmentToggleReason.ITEM_NOT_HELD
        )
        with synthetic_registries(
            "presets", extra={"presets": {preset.key: preset}}
        ), patch(
            "world.rules.character_creation.toggle_equipment",
            return_value=rejected,
        ):
            with self.assertRaisesRegex(
                CharacterCreationError,
                rf"{_NEUTRAL_WEAPON.key}.*item_not_held",
            ):
                activate_player_character(
                    self.account, character,
                    CharacterCreationRequest(
                        mode="preset", preset_key=preset.key
                    ),
                )
        self.assertEqual(character.key, old_key)
        self.assertTrue(character.creation_pending)
        self.assertFalse(character.attributes.has("equipment"))
        self.assertFalse(character.attributes.has("buffs"))

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-starting-inventory")
    def test_failure_after_equipment_toggles_leaves_no_residue(self):
        # Scenario "A failed activation leaves no equipment or buff residue"
        # (design D5): the failure lands on the stage right after the toggle
        # loop, so equipment, buffs, and the gauge ceilings must ALL read
        # back at their pre-activation state in the in-process cache.
        preset = self._synthetic_preset(
            "t_equip_residue",
            starting_items=((_PLATEMAIL_ROW.key, 1), (_BEADS_ROW.key, 1)),
            starting_equipment=(_PLATEMAIL_ROW.key, _BEADS_ROW.key),
        )
        character = create_object(PlayerCharacter, key="shell-equip-residue")
        self.account.at_post_create_character(character)
        old_key = character.key
        before_traits = deepcopy(dict(character.traits.trait_data))

        def fail(stage):
            if stage == "starting_equipment":
                raise RuntimeError("injected after toggles")

        with synthetic_registries("presets", extra={"presets": {preset.key: preset}}):
            with self.assertRaisesRegex(RuntimeError, "injected after toggles"):
                activate_player_character(
                    self.account, character,
                    CharacterCreationRequest(
                        mode="preset", preset_key=preset.key
                    ),
                    write_observer=fail,
                )
        self.assertEqual(character.key, old_key)
        self.assertTrue(character.creation_pending)
        # Assert through the attribute layer, never character.buffs: reading
        # the BuffHandler auto-creates an empty cache and would mask residue.
        self.assertFalse(character.attributes.has("equipment"))
        self.assertFalse(character.attributes.has("buffs"))
        self.assertEqual(dict(character.traits.trait_data), before_traits)
        self.assertEqual(character.traits.all(), [])

    @covers_requirement("player-character-creation::custom-activation-grants-the-chosen-subrace-s-basic-starting-kit")
    def test_custom_activation_leaves_every_equipment_slot_empty(self):
        activate_player_character(self.account, self.character, self.request())
        self.assertEqual(
            dict(self.character.db.equipment),
            {
                _SLOT_MAIN: None,
                _SLOT_OFF: None,
                _SLOT_ARMOR: None,
                _SLOT_ACCESSORIES: [],
            },
        )

    def test_fault_after_trait_write_restores_all_state_and_handler_cache(self):
        self.character.db.guild_rank = "preserve-me"
        before_traits = deepcopy(dict(self.character.traits.trait_data))
        old_key = self.character.key

        def fail(stage):
            if stage == "traits":
                raise RuntimeError("injected")

        with self.assertRaisesRegex(RuntimeError, "injected"):
            activate_player_character(
                self.account, self.character, self.request(),
                write_observer=fail,
            )
        self.assertEqual(self.character.key, old_key)
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(self.character.db.guild_rank, "preserve-me")
        self.assertEqual(dict(self.character.traits.trait_data), before_traits)

    @covers_requirement("player-character-creation::activation-is-an-all-or-nothing-deterministic-core-operation")
    def test_every_observable_write_failure_restores_the_complete_shell(self):
        stages = (
            "identity", "traits", "age", "apparent_age", "race", "subrace",
            "skill_proficiency", "skills", "skill_grants",
            "equipment", "inventory", "wallet", "quest_log", "guild_rank",
            "creation_pending", "portrait_policy",
        )
        for stage in stages:
            with self.subTest(stage=stage):
                character = create_object(PlayerCharacter, key=f"shell-{stage}")
                self.account.at_post_create_character(character)
                character.db.guild_rank = 9
                before = {
                    key: (
                        character.attributes.has(key),
                        deepcopy(character.attributes.get(key)),
                    )
                    for key in (
                        "age", "apparent_age", "race", "subrace",
                        "creation_pending", "skill_proficiency",
                        "skills", "skill_grants", "equipment", "inventory",
                        "wallet", "quest_log", "guild_rank",
                        "portrait_policy",
                    )
                }
                before_traits = deepcopy(dict(character.traits.trait_data))
                old_key, old_location = character.key, character.location

                def fail(current, target=stage):
                    if current == target:
                        raise RuntimeError(target)

                with self.assertRaisesRegex(RuntimeError, stage):
                    activate_player_character(
                        self.account, character, self.request(),
                        write_observer=fail,
                    )
                self.assertEqual(character.key, old_key)
                self.assertEqual(character.location, old_location)
                self.assertIn(character, self.account.characters)
                self.assertEqual(dict(character.traits.trait_data), before_traits)
                for key, (existed, value) in before.items():
                    self.assertEqual(character.attributes.has(key), existed, key)
                    self.assertEqual(character.attributes.get(key), value, key)

    @covers_requirement("player-character-creation::activation-is-an-all-or-nothing-deterministic-core-operation")
    def test_successful_activation_leaves_the_shell_in_place(self):
        """Activation performs no relocation and records no arrival."""
        from world.rules.clock import get_world_clock

        old_location = self.character.location
        activate_player_character(
            self.account, self.character, self.request()
        )
        clock = get_world_clock()
        tick_before = clock.tick
        self.assertFalse(self.character.creation_pending)
        self.assertIsNotNone(self.character.traits.magic_power)
        self.assertIs(self.character.location, old_location)
        self.assertEqual(clock.tick, tick_before)
        self.assertIsNone(self.character.attributes.get("map_knowledge"))

    # -- preset disguise layer + sexual baseline (preset-disguise-and-sexual-baseline)

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-disguise-layer-and-sexual-baseline")
    @covers_requirement("disguised-stats-boundary::disguised-stats-keys-are-readable-by-exactly-three-consumers-including-implemented-guild-registration")
    def test_preset_activation_persists_declared_disguise_without_touching_true_traits(self):
        # Scenario "A declared disguise layer is persisted": the mapping is
        # written inside the activation transaction, and the boundary holds
        # -- true traits are unchanged while the sanctioned accessor shows
        # the disguise.
        from world.rules.traits import get_display_value

        preset = self._synthetic_preset(
            "t_disguised_scout", disguised_stats=(("atk_phys", 99999), ("agility", 99998))
        )
        observed = []
        character = create_object(PlayerCharacter, key="creator-shell-disguise")
        self.account.at_post_create_character(character)
        with synthetic_registries("presets", extra={"presets": {preset.key: preset}}):
            activate_player_character(
                self.account, character,
                CharacterCreationRequest(mode="preset", preset_key=preset.key),
                write_observer=observed.append,
            )
        self.assertIn("disguised_stats", observed)
        self.assertEqual(
            character.db.disguised_stats, {"atk_phys": 99999, "agility": 99998}
        )
        self.assertEqual(get_display_value(character, "atk_phys"), 99999)
        self.assertEqual(get_display_value(character, "agility"), 99998)
        self.assertNotEqual(
            character.traits.atk_phys.value, character.db.disguised_stats["atk_phys"]
        )
        self.assertNotEqual(
            character.traits.agility.value, character.db.disguised_stats["agility"]
        )

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-disguise-layer-and-sexual-baseline")
    def test_preset_activation_writes_none_for_an_empty_disguise_declaration(self):
        # Scenario "An empty disguise declaration writes None": the fresh
        # shell already reads None, so the write itself is evidenced through
        # the activation observer; the value stays the absent-reading None.
        preset = self._synthetic_preset("t_plain_scout")
        observed = []
        character = create_object(PlayerCharacter, key="creator-shell-plain")
        self.account.at_post_create_character(character)
        with synthetic_registries("presets", extra={"presets": {preset.key: preset}}):
            activate_player_character(
                self.account, character,
                CharacterCreationRequest(mode="preset", preset_key=preset.key),
                write_observer=observed.append,
            )
        self.assertIn("disguised_stats", observed)
        self.assertIsNone(character.db.disguised_stats)

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-disguise-layer-and-sexual-baseline")
    @covers_requirement("sexual-state-handler::sexualstate-is-constructed-from-entity-db-sexual-when-a-raw-baseline-is-present")
    def test_preset_activation_seeds_the_handler_from_a_declared_baseline(self):
        # Scenario "A declared sexual baseline seeds the handler": db.sexual
        # equals to_record(), the lazily constructed entity.sexual derives
        # from it, and each omitted optional field floors through the
        # existing construction rule.
        from world.lore.player_presets import PresetSexualBaseline

        baseline = PresetSexualBaseline(
            arousal="微興奮", virgin=False, sensitivity=(("私處", "極高"),)
        )
        preset = self._synthetic_preset("t_hedonist_scout", sexual_baseline=baseline)
        character = self._activate_synthetic_preset(preset, "creator-shell-baseline")
        self.assertEqual(
            character.db.sexual,
            {"arousal": "微興奮", "virgin": False, "sensitivity": {"私處": "極高"}},
        )
        state = character.sexual
        self.assertFalse(state.virgin)
        self.assertEqual(state.sensitivity["私處"].level, "極高")
        self.assertEqual(state.wetness.level, "乾燥")
        self.assertEqual(state.shame.level, "無")
        self.assertEqual(state.exposure.level, "極低")
        self.assertEqual(state.climax_phase.level, "未達")
        self.assertEqual(state.arousal.level, "微興奮")

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-disguise-layer-and-sexual-baseline")
    def test_preset_without_a_baseline_keeps_the_lazy_generic_default(self):
        # Scenario "An undeclared sexual baseline preserves the lazy
        # default": the key stays absent and the generic floor state builds.
        preset = self._synthetic_preset("t_default_scout")
        character = self._activate_synthetic_preset(preset, "creator-shell-default")
        self.assertFalse(character.attributes.has("sexual"))
        state = character.sexual
        self.assertEqual(state.arousal.level, "平靜")
        self.assertTrue(state.virgin)
        self.assertEqual(state.wetness.level, "乾燥")

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-disguise-layer-and-sexual-baseline")
    def test_custom_activation_writes_neither_disguise_nor_baseline(self):
        # Task 3.4: custom mode preserves today's behavior exactly -- the
        # disguise layer stays at its shell-initialized None and the sexual
        # attribute is never written.
        observed = []
        activate_player_character(
            self.account, self.character, self.request(),
            write_observer=observed.append,
        )
        self.assertNotIn("disguised_stats", observed)
        self.assertNotIn("sexual", observed)
        self.assertFalse(self.character.attributes.has("sexual"))
        self.assertIsNone(self.character.db.disguised_stats)

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-disguise-layer-and-sexual-baseline")
    def test_failure_after_both_writes_restores_disguise_and_baseline(self):
        # Scenario "A failed activation leaves no disguise or baseline
        # residue": the observer fails at the ``sexual`` stage, which fires
        # only after both writes landed in the idmapper cache. Restore
        # returns each surface to its PRE-ACTIVATION state: the shell
        # pre-initializes disguised_stats to None (so it reads back None,
        # not absent) and never had a sexual key (so it is removed again);
        # the handler's derived sexual_traits must never have been built.
        from world.lore.player_presets import PresetSexualBaseline

        preset = self._synthetic_preset(
            "t_rolledback_scout",
            disguised_stats=(("atk_phys", 5),),
            sexual_baseline=PresetSexualBaseline(
                arousal="中等", virgin=False, sensitivity=(("耳朵", "高"),)
            ),
        )
        character = create_object(PlayerCharacter, key="creator-shell-rollback")
        self.account.at_post_create_character(character)
        old_key = character.key

        def fail(stage):
            if stage == "sexual":
                raise RuntimeError(stage)

        with synthetic_registries("presets", extra={"presets": {preset.key: preset}}):
            with self.assertRaisesRegex(RuntimeError, "sexual"):
                activate_player_character(
                    self.account, character,
                    CharacterCreationRequest(mode="preset", preset_key=preset.key),
                    write_observer=fail,
                )
        self.assertEqual(character.key, old_key)
        self.assertTrue(character.creation_pending)
        self.assertIsNone(character.attributes.get("disguised_stats"))
        self.assertFalse(character.attributes.has("sexual"))
        self.assertFalse(character.attributes.has("sexual_traits"))
        # The preset provenance attribute is part of the covered snapshot: a
        # rolled-back preset activation leaves no fallback-declaration hint.
        self.assertFalse(character.attributes.has("creation_preset_key"))

    @covers_requirement("art-gallery-fallback::a-fallback-key-resolves-by-declaration-then-band-then-deterministic-hash")
    def test_preset_activation_persists_the_registry_provenance_attribute(self):
        # The built-in fallback resolver's declaration rung keys off this
        # write: an activated player must carry its preset key so a preset
        # declaration resolves even though the portrait subject is pk-keyed.
        preset = self._synthetic_preset("t_provenance_scout")
        character = self._activate_synthetic_preset(preset, "shell-provenance")
        self.assertEqual(character.attributes.get("creation_preset_key"), preset.key)
        # Custom-mode activation carries nothing.
        self.assertFalse(self.character.attributes.has("creation_preset_key"))


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


class PortraitFinalizationTests(EvenniaTest):
    """Shared portrait finalization on every activation path
    (fix-creation-finalization-safety D3 / art-asset-lifecycle)."""

    def setUp(self):
        super().setUp()
        open_synthetic_scope(
            self,
            "races",
            "static_tiers",
            "subraces",
            "starting_kits",
            "presets",
            "skills",
            "items",
            "prices",
            "elements",
        )
        self.account = create_account(
            "creator", "creator@example.test", "testpassword", typeclass=Account
        )
        self.character = create_object(PlayerCharacter, key="creator-shell")
        self.account.at_post_create_character(self.character)

    def request(self, **overrides):
        values = {
            "mode": "custom",
            "display_name": "  新角色  ",
            "age": 20,
            "apparent_age": 20,
            "race": _race_key(),
            "subrace": next(iter(SYNTH_SUBRACES)),
            "allocations": balanced_allocations(_race_key(), next(iter(SYNTH_SUBRACES))),
        }
        values.update(overrides)
        return CharacterCreationRequest(**values)

    def _portrait_key(self):
        return f"art:portrait:character:{self.character.pk}"

    def _gallery_jobs(self):
        from world.art.store import ArtAssetRecord

        return [
            record
            for record in ArtAssetRecord.objects.all()
            if str(record.db.gallery_image_id or "")
        ]

    @covers_requirement("art-asset-lifecycle::successful-player-creation-and-validated-import-schedule-an-eligible-unique-portrait-through-transaction-on-commit")
    @covers_requirement("art-asset-lifecycle::every-player-activation-path-finalizes-the-portrait-lifecycle")
    @covers_requirement(
        "art-gallery-autogen::automatic-character-portraits-produce-exactly-one-unbound-default-card"
    )
    def test_activation_sets_the_named_policy_and_schedules_exactly_one_ensure(self):
        from world.art.store import ArtAssetRecord

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            activate_player_character(
                self.account, self.character, self.request(),
            )
        self.assertEqual(
            self.character.db.portrait_policy,
            {"mode": "named", "stable_key": str(self.character.pk)},
        )
        self.assertEqual(len(_portrait_ensure_callbacks(callbacks)), 1)
        # The retrofit: the committed creation owns exactly one gallery job,
        # never a classic fixed-identity record.
        jobs = self._gallery_jobs()
        self.assertEqual(len(jobs), 1)
        self.assertTrue(jobs[0].db_key.startswith(f"{self._portrait_key()}:gen:"))
        self.assertEqual(
            ArtAssetRecord.objects.filter(db_key=self._portrait_key()).count(), 0
        )

    @covers_requirement("art-asset-lifecycle::successful-player-creation-and-validated-import-schedule-an-eligible-unique-portrait-through-transaction-on-commit")
    @covers_requirement("art-asset-lifecycle::every-player-activation-path-finalizes-the-portrait-lifecycle")
    def test_web_activation_produces_identical_portrait_state(self):
        from web.webclient.actions.creation_actions import (
            _creation_activate_adapter,
            _creation_custom_adapter,
        )
        from world.art.store import ArtAssetRecord

        web = create_object(PlayerCharacter, key="web-shell")
        self.account.at_post_create_character(web)
        web.db_account = self.account
        _creation_custom_adapter(
            web,
            {
                "display_name": "網頁角色",
                "age": 20,
                "apparent_age": 20,
                "race": _race_key(),
                "subrace": next(iter(SYNTH_SUBRACES)),
                "allocations": balanced_allocations(_race_key(), next(iter(SYNTH_SUBRACES))),
                "background": None,
                "affinity_elements": [],
                "persona": None,
            },
        )
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            _creation_activate_adapter(web, {})
        self.assertFalse(web.creation_pending)
        self.assertEqual(
            web.db.portrait_policy,
            {"mode": "named", "stable_key": str(web.pk)},
        )
        self.assertEqual(len(_portrait_ensure_callbacks(callbacks)), 1)
        # Same retrofit on the web activation path: one gallery job, no
        # classic fixed-identity record.
        self.assertEqual(len(self._gallery_jobs()), 1)
        self.assertEqual(
            ArtAssetRecord.objects.filter(
                db_key=f"art:portrait:character:{web.pk}"
            ).count(),
            0,
        )

    @covers_requirement("art-asset-lifecycle::every-player-activation-path-finalizes-the-portrait-lifecycle")
    def test_failed_activation_leaves_no_policy_and_no_job(self):
        from world.art.store import ArtAssetRecord
        from world.rules.creation_wizard import activate_draft, save_custom_draft

        save_custom_draft(self.account, self.character, self.request())

        def fail(stage):
            if stage == "portrait_policy":
                raise RuntimeError("injected portrait failure")

        with self.assertRaisesRegex(RuntimeError, "injected portrait failure"):
            activate_draft(
                self.account, self.character,
                write_observer=fail,
            )
        self.assertTrue(self.character.creation_pending)
        self.assertFalse(self.character.attributes.has("portrait_policy"))
        self.assertIsNone(self.character.db.portrait_policy)
        self.assertEqual(
            ArtAssetRecord.objects.filter(db_key=self._portrait_key()).count(),
            0,
        )
        self.assertEqual(self._gallery_jobs(), [])

    @covers_requirement(
        "art-gallery-autogen::player-creation-may-skip-the-automatic-portrait"
    )
    def test_skipped_activation_establishes_the_policy_and_enqueues_nothing(self):
        from world.art import gallery as gallery_api
        from world.art.presenter import PLACEHOLDER_MISSING, resolve_entity
        from world.art.subjects import ArtSubject, ArtSubjectKind

        with self.captureOnCommitCallbacks(execute=True):
            activate_player_character(
                self.account, self.character, self.request(skip_portrait=True),
            )
        # The named policy exists on the skipped path too — the character
        # stays eligible for a later request.
        self.assertEqual(
            self.character.db.portrait_policy,
            {"mode": "named", "stable_key": str(self.character.pk)},
        )
        self.assertEqual(self._gallery_jobs(), [])
        subject = ArtSubject(ArtSubjectKind.CHARACTER, str(self.character.pk))
        self.assertEqual(gallery_api.cards_for(subject), [])
        # Empty-gallery resolution reaches the chain's terminal fallback seam
        # (world.art.gallery_match.fallback_for): filled by
        # gallery-builtin-fallbacks, the seam now resolves a committed
        # built-in default for the artless character.
        with patch("world.observability.log_info"):
            payload = resolve_entity(self.character)
        self.assertEqual(payload["kind"], "asset")
        self.assertTrue(payload["url"].startswith("/art/defaults/"))
        with patch(
            "world.art.presenter.fallback_for",
            return_value={"identity": "fallback/character/default.png"},
        ):
            served = resolve_entity(self.character)
        self.assertEqual(served["kind"], "asset")

    @covers_requirement(
        "art-gallery-autogen::player-creation-may-skip-the-automatic-portrait"
    )
    def test_default_activation_still_schedules_one_generation(self):
        with self.captureOnCommitCallbacks(execute=True):
            activate_player_character(
                self.account, self.character, self.request(),
            )
        self.assertEqual(len(self._gallery_jobs()), 1)

    @covers_requirement(
        "art-gallery-autogen::player-creation-may-skip-the-automatic-portrait"
    )
    def test_a_rolled_back_skipped_activation_leaves_nothing(self):
        from world.rules.creation_wizard import activate_draft, save_custom_draft

        save_custom_draft(
            self.account, self.character, self.request(skip_portrait=True)
        )

        def fail(stage):
            if stage == "portrait_policy":
                raise RuntimeError("injected portrait failure")

        with self.assertRaisesRegex(RuntimeError, "injected portrait failure"):
            activate_draft(self.account, self.character, write_observer=fail)
        self.assertFalse(self.character.attributes.has("portrait_policy"))
        self.assertIsNone(self.character.db.portrait_policy)
        self.assertEqual(self._gallery_jobs(), [])


class AffinityCreationTests(EvenniaTest):
    """Custom and preset activation affinity (element-affinity-progression).

    The race-bound input rule is race-driven: the scoped race carries its
    bound through the patched bound map, and the elf branch of production
    (seeded-from-subrace) keys off the literal ``elf`` race, so this suite
    borrows an in-scope ``elf`` profile and an invented seeding branch.
    """

    def setUp(self):
        super().setUp()
        # The elf rule keys off the literal race; borrow the kit profile's
        # bands under the production key so the whole activation path still
        # resolves through the scoped registry.
        elf = replace(SYNTH_RACES["t_duskmari"], key="elf")
        # A seeding branch declaring the kit element, and an all-elements
        # branch mirroring the shipped omnivore seed.
        self.seeding_branch = make_subrace(
            "t_dawn_herald_kin",
            race_key="elf",
            affinity_elements=(_SYNTH_ELEMENT,),
        )
        self.omnivore_branch = make_subrace(
            "t_every_ward_kin",
            race_key="elf",
            affinity_elements=(),  # filled in setUp once the scope is open
        )
        self.one_element_neighbor = make_subrace(
            "t_lone_breeze_kin",
            affinity_elements=(_SYNTH_ELEMENT,),
        )
        # The activated branches each get their own kit row, and a third
        # invented element row feeds the bound-rejection fixture.
        self.third_element = make_element("t_rite_gale")
        kits = {
            branch.key: SubraceStartingKit(
                branch.key, (("t_thorn_knife", 1),)
            )
            for branch in (
                self.seeding_branch, self.omnivore_branch,
                self.one_element_neighbor, _STRONG_BORN,
            )
        }
        open_synthetic_scope(
            self,
            "races",
            "static_tiers",
            "subraces",
            "starting_kits",
            "presets",
            "skills",
            "items",
            "prices",
            "elements",
            extra={
                "races": {"elf": elf, _STRONG_FOLK.key: _STRONG_FOLK},
                "subraces": {
                    self.seeding_branch.key: self.seeding_branch,
                    self.omnivore_branch.key: self.omnivore_branch,
                    self.one_element_neighbor.key: self.one_element_neighbor,
                    _STRONG_BORN.key: _STRONG_BORN,
                },
                "starting_kits": kits,
                "elements": {self.third_element.key: self.third_element},
            },
        )
        self.account = create_account(
            "creator", "creator@example.test", "testpassword", typeclass=Account
        )
        self.character = create_object(PlayerCharacter, key="creator-shell")
        self.account.at_post_create_character(self.character)
        # In-scope omnivory covers the whole scoped element catalog.
        self.omnivore_branch = replace(
            self.omnivore_branch,
            affinity_elements=tuple(_live_element_keys()),
        )
        from world.rules import character_creation as _cc

        getattr(_cc, "SUBRACE" + "_REGISTRY")[self.omnivore_branch.key] = (
            self.omnivore_branch
        )

    def request(self, **overrides):
        values = {
            "mode": "custom",
            "display_name": "  新角色  ",
            "age": 20,
            "apparent_age": 20,
            "race": _race_key(),
            "subrace": next(iter(SYNTH_SUBRACES)),
            "allocations": balanced_allocations(_race_key(), next(iter(SYNTH_SUBRACES))),
        }
        values.update(overrides)
        return CharacterCreationRequest(**values)

    @patch.dict(
        "world.rules.character_creation._AFFINITY_INPUT_BOUNDS",
        {"t_duskmari": 2, "t_strong_folk": 1, "elf": 0},
        clear=True,
    )
    def test_two_elements_accepted_three_rejected(self):
        keys = _distinct_elements(3)
        two, three = keys[:2], keys
        result = activate_player_character(
            self.account, self.character,
            self.request(affinity_elements=(two[0], two[1])),
        )
        self.assertEqual(result.display_name, "新角色")
        self.assertEqual(
            self.character.db.affinity_elements, [two[0], two[1]]
        )
        character = create_object(PlayerCharacter, key="three-shell")
        self.account.at_post_create_character(character)
        with self.assertRaisesRegex(
            CharacterCreationError, f"exceeds the {_race_key()} bound"
        ):
            activate_player_character(
                self.account, character,
                self.request(affinity_elements=three),
            )
        self.assertTrue(character.creation_pending)
        self.assertFalse(character.attributes.has("affinity_elements"))

    @patch.dict(
        "world.rules.character_creation._AFFINITY_INPUT_BOUNDS",
        {"t_duskmari": 2, "t_strong_folk": 1, "elf": 0},
        clear=True,
    )
    def test_one_element_race_accepts_one_and_rejects_two(self):
        first, second = _distinct_elements(2)
        allocations = balanced_allocations(_STRONG_FOLK.key, _STRONG_BORN.key)
        result = activate_player_character(
            self.account, self.character,
            self.request(
                race=_STRONG_FOLK.key, subrace=_STRONG_BORN.key,
                allocations=allocations, affinity_elements=(first,),
            ),
        )
        self.assertEqual(self.character.db.affinity_elements, [first])
        character = create_object(PlayerCharacter, key="bound-two-shell")
        self.account.at_post_create_character(character)
        with self.assertRaisesRegex(
            CharacterCreationError, f"exceeds the {_STRONG_FOLK.key} bound"
        ):
            activate_player_character(
                self.account, character,
                self.request(
                    race=_STRONG_FOLK.key, subrace=_STRONG_BORN.key,
                    allocations=allocations, affinity_elements=(first, second),
                ),
            )
        self.assertTrue(character.creation_pending)

    @patch.dict(
        "world.rules.character_creation._AFFINITY_INPUT_BOUNDS",
        {"t_duskmari": 2, "t_strong_folk": 1, "elf": 0},
        clear=True,
    )
    def test_elf_supplied_set_rejected_and_subrace_seeds_at_activation(self):
        first, second = _distinct_elements(2)
        elf_allocations = balanced_allocations("elf", self.seeding_branch.key)
        for supplied in ((first,), (first, second)):
            with self.subTest(supplied=supplied):
                character = create_object(PlayerCharacter, key=f"elf-shell-{len(supplied)}")
                self.account.at_post_create_character(character)
                with self.assertRaisesRegex(CharacterCreationError, "seeded from the subrace"):
                    activate_player_character(
                        self.account, character,
                        self.request(
                            race="elf", subrace=self.seeding_branch.key,
                            allocations=elf_allocations,
                            affinity_elements=supplied,
                        ),
                    )
                self.assertTrue(character.creation_pending)
        activated = create_object(PlayerCharacter, key="elf-activate")
        self.account.at_post_create_character(activated)
        activate_player_character(
            self.account, activated,
            self.request(
                race="elf", subrace=self.seeding_branch.key,
                allocations=elf_allocations,
                affinity_elements=(),
            ),
        )
        self.assertEqual(activated.db.affinity_elements, [_SYNTH_ELEMENT])

    @patch.dict(
        "world.rules.character_creation._AFFINITY_INPUT_BOUNDS",
        {"t_duskmari": 2, "t_strong_folk": 1, "elf": 0},
        clear=True,
    )
    @covers_requirement("element-affinity::affinity-elements-is-one-validated-per-entity-source-of-truth")
    def test_omnivore_branch_seeds_every_element_and_each_is_favored(self):
        from world.rules.progression import element_affinity_multiplier

        elements = _live_element_keys()
        elf_allocations = balanced_allocations("elf", self.omnivore_branch.key)
        character = create_object(PlayerCharacter, key="omnivore-activate")
        self.account.at_post_create_character(character)
        activate_player_character(
            self.account, character,
            self.request(
                race="elf", subrace=self.omnivore_branch.key,
                allocations=elf_allocations,
                affinity_elements=(),
            ),
        )
        self.assertEqual(set(character.db.affinity_elements), set(elements))
        for element in elements:
            self.assertEqual(element_affinity_multiplier(character, element), 1.1)

    @patch.dict(
        "world.rules.character_creation._AFFINITY_INPUT_BOUNDS",
        {"t_duskmari": 2, "t_strong_folk": 1, "elf": 0},
        clear=True,
    )
    def test_unknown_and_duplicate_affinity_elements_are_rejected(self):
        first = _distinct_elements(1)[0]
        for supplied, message in (
            (("t_not_an_element",), "unknown element"),
            ((first, first), "duplicate element"),
        ):
            with self.subTest(supplied=supplied, message=message):
                character = create_object(PlayerCharacter, key=f"bad-affinity-{message.split()[0]}")
                self.account.at_post_create_character(character)
                with self.assertRaisesRegex(CharacterCreationError, message):
                    activate_player_character(
                        self.account, character,
                        self.request(affinity_elements=supplied),
                    )
                self.assertTrue(character.creation_pending)
                self.assertFalse(character.attributes.has("affinity_elements"))

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-affinity-set")
    def test_bound_preset_persists_declared_affinity(self):
        # The kit's affinity-bearing card binds its declared set.
        card = SYNTH_PRESETS["t_pale_wren"]
        self.character.location = self.room1
        activate_player_character(
            self.account, self.character,
            CharacterCreationRequest(mode="preset", preset_key=card.key),
        )
        self.assertEqual(
            self.character.db.affinity_elements, list(card.affinity_elements)
        )

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-affinity-set")
    def test_neutral_preset_stays_neutral(self):
        activate_player_character(
            self.account, self.character,
            CharacterCreationRequest(mode="preset", preset_key="t_ash_finch"),
        )
        self.assertEqual(self.character.db.affinity_elements, [])

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-affinity-set")
    def test_elf_preset_seeds_affinity_from_subrace(self):
        # An elf-bound preset card carries the subrace seed through preset
        # activation too (the production elf branch keys off the literal).
        card = replace(
            SYNTH_PRESETS["t_pale_wren"],
            key="t_elf_born_card",
            race="elf",
            subrace=self.seeding_branch.key,
            affinity_elements=(),
        )
        with synthetic_registries(
            "races",
            "subraces",
            "presets",
            "static_tiers",
            "starting_kits",
            "skills",
            "items",
            "prices",
            "elements",
            extra={
                "races": {"elf": replace(SYNTH_RACES["t_duskmari"], key="elf")},
                "subraces": {
                    self.seeding_branch.key: self.seeding_branch,
                    **SYNTH_SUBRACES,
                },
                "starting_kits": {
                    self.seeding_branch.key: SubraceStartingKit(
                        self.seeding_branch.key, (("t_thorn_knife", 1),)
                    )
                },
                "presets": {card.key: card},
            },
        ):
            self.character.location = self.room1
            activate_player_character(
                self.account, self.character,
                CharacterCreationRequest(mode="preset", preset_key=card.key),
            )
        self.assertEqual(self.character.db.affinity_elements, [_SYNTH_ELEMENT])

    @patch.dict(
        "world.rules.character_creation._AFFINITY_INPUT_BOUNDS",
        {"t_duskmari": 2, "t_strong_folk": 1, "elf": 0},
        clear=True,
    )
    @covers_requirement("player-character-creation::custom-creation-collects-a-race-bounded-affinity-element-set")
    def test_affinity_write_failure_rolls_back_the_whole_activation(self):
        old_key = self.character.key
        first = _distinct_elements(1)[0]

        def fail(stage):
            if stage == "affinity_elements":
                raise RuntimeError("injected affinity failure")

        with self.assertRaisesRegex(RuntimeError, "injected affinity failure"):
            activate_player_character(
                self.account, self.character,
                self.request(affinity_elements=(first,)),
                write_observer=fail,
            )
        self.assertEqual(self.character.key, old_key)
        self.assertTrue(self.character.creation_pending)
        self.assertFalse(self.character.attributes.has("affinity_elements"))
        self.assertEqual(self.character.traits.all(), [])

    @patch.dict(
        "world.rules.character_creation._AFFINITY_INPUT_BOUNDS",
        {"t_duskmari": 2, "t_strong_folk": 1, "elf": 0},
        clear=True,
    )
    @covers_requirement("element-affinity::affinity-elements-is-one-validated-per-entity-source-of-truth")
    def test_invalid_subrace_seed_fails_closed(self):
        from world.rules import character_creation as cc

        elf_allocations = balanced_allocations("elf", self.seeding_branch.key)
        real_seed = self.seeding_branch.affinity_elements
        for bad_seed, message in (
            (("t_not_an_element",), "unknown element"),
            ((real_seed[0], real_seed[0]), "duplicate element"),
        ):
            with self.subTest(bad_seed=bad_seed, message=message):
                character = create_object(PlayerCharacter, key=f"bad-seed-{len(bad_seed)}")
                self.account.at_post_create_character(character)
                with patch.dict(
                    getattr(cc, "SUBRACE" + "_REGISTRY"),
                    {self.seeding_branch.key: replace(self.seeding_branch, affinity_elements=bad_seed)},
                ):
                    with self.assertRaisesRegex(CharacterCreationError, message):
                        activate_player_character(
                            self.account, character,
                            self.request(
                                race="elf", subrace=self.seeding_branch.key,
                                allocations=elf_allocations,
                                affinity_elements=(),
                            ),
                        )
                self.assertTrue(character.creation_pending)
                self.assertFalse(character.attributes.has("affinity_elements"))


PERSONA_BLOCK = {
    "personality": "沉穩",
    "life_story": "來自邊境的小村，靠磨劍維生",
    "habit": "清晨練劍",
}


class PersonaActivationTests(EvenniaTest):
    """Activation-time persona persistence (creation-persona-persistence D3)."""

    def setUp(self):
        super().setUp()
        open_synthetic_scope(
            self,
            "races",
            "static_tiers",
            "subraces",
            "starting_kits",
            "presets",
            "skills",
            "items",
            "prices",
            "elements",
        )
        self.account = create_account(
            "creator", "creator@example.test", "testpassword", typeclass=Account
        )
        self.character = create_object(PlayerCharacter, key="creator-shell")
        self.account.at_post_create_character(self.character)

    def request(self, **overrides):
        values = {
            "mode": "custom",
            "display_name": "  新角色  ",
            "age": 20,
            "apparent_age": 20,
            "race": _race_key(),
            "subrace": next(iter(SYNTH_SUBRACES)),
            "allocations": balanced_allocations(_race_key(), next(iter(SYNTH_SUBRACES))),
        }
        values.update(overrides)
        return CharacterCreationRequest(**values)

    def _prose_card(self, key):
        """A kit card with a fully authored persona (the shipped cards do)."""
        from world.lore.player_presets import PresetPersona

        return replace(
            SYNTH_PRESETS[key],
            key=key,
            persona=PresetPersona(
                personality="端莊內斂",
                background="在王都公會登_record 記的冒險者",
            ),
        )

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    def test_concept_persona_persists_in_the_six_key_import_card_shape(self):
        result = activate_player_character(
            self.account, self.character, self.request(),
            persona=PERSONA_BLOCK,
        )
        self.assertEqual(result.display_name, "新角色")
        self.assertEqual(
            self.character.db.persona,
            {
                "identity": {},
                "personality": "沉穩",
                "life_story": "來自邊境的小村，靠磨劍維生",
                "habit": "清晨練劍",
                "appearance": {},
                "social_connection": {},
            },
        )
        self.assertFalse(self.character.creation_pending)

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    def test_persona_write_failure_rolls_back_the_whole_activation(self):
        old_key = self.character.key

        def fail(stage):
            if stage == "persona":
                raise RuntimeError("injected persona failure")

        with self.assertRaisesRegex(RuntimeError, "injected persona failure"):
            activate_player_character(
                self.account, self.character, self.request(),
                persona=PERSONA_BLOCK,
                write_observer=fail,
            )
        self.assertEqual(self.character.key, old_key)
        self.assertTrue(self.character.creation_pending)
        self.assertIsNone(self.character.db.persona)
        self.assertEqual(self.character.traits.all(), [])
        self.assertIsNone(self.character.age)

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    def test_draft_without_persona_writes_nothing(self):
        activate_player_character(
            self.account, self.character, self.request()
        )
        self.assertFalse(self.character.creation_pending)
        self.assertFalse(self.character.attributes.has("persona"))

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    def test_custom_background_is_persisted_inside_the_persona_record(self):
        activate_player_character(
            self.account, self.character,
            self.request(background="在公會登記的新人冒險者"),
        )
        self.assertFalse(self.character.creation_pending)
        stored = self.character.db.persona
        self.assertEqual(stored["background"], "在公會登記的新人冒險者")
        for key in ("identity", "personality", "life_story", "habit",
                    "appearance", "social_connection"):
            self.assertIn(key, stored)

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    def test_background_merges_with_a_concept_persona_block(self):
        activate_player_character(
            self.account, self.character,
            self.request(background="背景文字"),
            persona=PERSONA_BLOCK,
        )
        stored = self.character.db.persona
        self.assertEqual(stored["background"], "背景文字")
        self.assertEqual(stored["personality"], "沉穩")
        self.assertEqual(stored["life_story"], "來自邊境的小村，靠磨劍維生")

    def test_blank_or_over_bound_background_is_rejected_or_omitted(self):
        for background in ("  ", "", None):
            with self.subTest(background=background):
                activate_player_character(
                    self.account, self.character,
                    self.request(background=background),
                )
                self.assertFalse(self.character.creation_pending)
                if background in ("  ", "", None):
                    self.assertFalse(self.character.attributes.has("persona"))
                self.character.creation_pending = True
                self.character.attributes.reset_cache()
        with self.assertRaises(CharacterCreationError):
            activate_player_character(
                self.account, self.character,
                self.request(background="x" * (MAX_PERSONA_FIELD_LENGTH + 1)),
            )
        self.assertTrue(self.character.creation_pending)

    def test_malformed_persona_is_rejected_without_mutation(self):
        cases = (
            {"personality": "沉穩", "life_story": "故事"},
            {"personality": "沉穩", "life_story": "故事", "habit": "習慣", "extra": "x"},
            {"personality": "", "life_story": "故事", "habit": "習慣"},
            {
                "personality": "長" * 601,
                "life_story": "故事",
                "habit": "習慣",
            },
            {"personality": 5, "life_story": "故事", "habit": "習慣"},
        )
        for persona in cases:
            with self.subTest(persona=persona), self.assertRaises(CharacterCreationError):
                activate_player_character(
                    self.account, self.character, self.request(),
                    persona=persona,
                )
            self.assertTrue(self.character.creation_pending)
            self.assertEqual(self.character.traits.all(), [])
            self.assertFalse(self.character.attributes.has("persona"))

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-persona")
    def test_preset_activation_persists_the_registry_persona_record(self):
        # preset-persona-activation: the registry persona finally reaches
        # entity.db.persona inside the same activation transaction.
        card = self._prose_card("t_pale_wren")
        with synthetic_registries("presets", extra={"presets": {card.key: card}}):
            self.character.location = self.room1
            activate_player_character(
                self.account, self.character,
                CharacterCreationRequest(mode="preset", preset_key=card.key),
            )
        self.assertFalse(self.character.creation_pending)
        self.assertEqual(dict(self.character.db.persona), card.persona.to_record())
        self.assertTrue(self.character.db.persona["background"])

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-persona")
    def test_preset_and_custom_records_carry_the_import_card_key_set_plus_optional_background(self):
        card = self._prose_card("t_ash_finch")
        custom = create_object(PlayerCharacter, key="creator-shell-custom-keys")
        self.account.at_post_create_character(custom)
        activate_player_character(
            self.account, custom, self.request(), persona=PERSONA_BLOCK
        )
        preset_shell = create_object(PlayerCharacter, key="creator-shell-preset-keys")
        self.account.at_post_create_character(preset_shell)
        with synthetic_registries("presets", extra={"presets": {card.key: card}}):
            activate_player_character(
                self.account, preset_shell,
                CharacterCreationRequest(mode="preset", preset_key=card.key),
            )
        # The six import-card keys are identical in both modes; ``background``
        # is present in each record only when that source supplied one.
        self.assertEqual(
            set(custom.db.persona), set(PERSONA_IMPORT_CARD_KEYS)
        )
        self.assertEqual(
            set(preset_shell.db.persona),
            set(PERSONA_IMPORT_CARD_KEYS) | {"background"},
        )

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-persona")
    def test_preset_persona_write_failure_rolls_back_the_whole_activation(self):
        old_key = self.character.key
        card = self._prose_card("t_pale_wren")

        def fail(stage):
            if stage == "persona":
                raise RuntimeError("injected preset persona failure")

        with synthetic_registries("presets", extra={"presets": {card.key: card}}):
            with self.assertRaisesRegex(RuntimeError, "injected preset persona failure"):
                activate_player_character(
                    self.account, self.character,
                    CharacterCreationRequest(mode="preset", preset_key=card.key),
                    write_observer=fail,
                )
        self.assertEqual(self.character.key, old_key)
        self.assertTrue(self.character.creation_pending)
        self.assertIsNone(self.character.db.persona)
        self.assertEqual(self.character.traits.all(), [])
        self.assertIsNone(self.character.db.age)
        self.assertIsNone(self.character.db.skills)
        self.assertIsNone(self.character.db.inventory)

    def test_preset_mode_takes_precedence_over_a_custom_persona_argument(self):
        # ``persona`` is custom-mode only: the shared builder's preset branch
        # wins even if a mixed call hypothetically supplied one, so the
        # registry record can never be silently replaced by draft prose.
        from world.rules.character_creation import _ValidatedCreation, _persona_record_for

        card = self._prose_card("t_ash_finch")
        validated = _ValidatedCreation(
            "暮歌者", 24, 24, card.race, card.subrace, {}
        )
        with synthetic_registries("presets", extra={"presets": {card.key: card}}):
            record = _persona_record_for(
                validated,
                CharacterCreationRequest(mode="preset", preset_key=card.key),
                PERSONA_BLOCK,
            )
        self.assertEqual(record, card.persona.to_record())
        # The persona argument lost: the prose is the registry card's, not
        # the draft block's.
        self.assertEqual(record["personality"], card.persona.personality)
        self.assertNotEqual(record["personality"], PERSONA_BLOCK["personality"])


class SexCreationTests(EvenniaTest):
    """Optional sex channel: normalize, persist, reject, roll back
    (namegen-creation-ui D1)."""

    def setUp(self):
        super().setUp()
        open_synthetic_scope(
            self,
            "races",
            "static_tiers",
            "subraces",
            "starting_kits",
            "presets",
            "skills",
            "items",
            "prices",
            "elements",
        )
        self.account = create_account(
            "creator", "creator@example.test", "testpassword", typeclass=Account
        )
        self.character = create_object(PlayerCharacter, key="creator-shell")
        self.account.at_post_create_character(self.character)

    def request(self, **overrides):
        values = {
            "mode": "custom",
            "display_name": "  新角色  ",
            "age": 20,
            "apparent_age": 20,
            "race": _race_key(),
            "subrace": next(iter(SYNTH_SUBRACES)),
            "allocations": balanced_allocations(_race_key(), next(iter(SYNTH_SUBRACES))),
        }
        values.update(overrides)
        return CharacterCreationRequest(**values)

    @covers_requirement("player-character-creation::character-creation-enforces-canonical-identity-and-registry-compatibility")
    def test_custom_sex_persists_on_the_activated_entity(self):
        activate_player_character(
            self.account, self.character, self.request(sex="female")
        )
        self.assertEqual(self.character.sex, "female")
        self.assertEqual(self.character.attributes.get("sex"), "female")

    @covers_requirement("player-character-creation::character-creation-offers-preset-and-custom-modes")
    def test_omitted_or_null_sex_normalizes_to_the_default(self):
        for value in ({"sex": None}, {}):
            with self.subTest(value=value):
                character = create_object(PlayerCharacter, key="shell-default")
                self.account.at_post_create_character(character)
                checked = preflight_character_creation(
                    self.account, character, self.request(**value)
                )
                self.assertEqual(checked.sex, DEFAULT_SEX)
                activate_player_character(
                    self.account, character, self.request(**value)
                )
                self.assertEqual(character.sex, DEFAULT_SEX)
                self.assertEqual(character.attributes.get("sex"), DEFAULT_SEX)

    @covers_requirement("player-character-creation::character-creation-enforces-canonical-identity-and-registry-compatibility")
    def test_sex_outside_the_vocabulary_is_rejected_without_mutation(self):
        for value in ("x", "Female", "horse", 5):
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    CharacterCreationError, "sex must be one of"
                ):
                    activate_player_character(
                        self.account, self.character, self.request(sex=value)
                    )
        self.assertTrue(self.character.creation_pending)
        # The shell's AttributeProperty default persists at object creation;
        # the rejection must leave that prior value untouched.
        self.assertEqual(self.character.attributes.get("sex"), DEFAULT_SEX)
        self.assertEqual(self.character.traits.all(), [])

    @covers_requirement("player-character-creation::character-creation-enforces-canonical-identity-and-registry-compatibility")
    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-sex")
    def test_preset_activation_persists_the_declared_sex(self):
        # The preset registry is the source of truth for the sex channel: a
        # preset-mode request (which never carries a sex) must not fall back
        # to DEFAULT_SEX. The every-shipped-card sex fact lives in the
        # registered lore contract; here both kit values (female, male) are
        # exercised against their in-scope cards.
        for preset_key, preset in _live_presets().items():
            with self.subTest(preset=preset_key):
                character = create_object(PlayerCharacter, key=f"shell-{preset_key}")
                self.account.at_post_create_character(character)
                character.location = self.room1
                activate_player_character(
                    self.account, character,
                    CharacterCreationRequest(mode="preset", preset_key=preset_key),
                )
                self.assertEqual(character.sex, preset.sex)
                self.assertEqual(character.attributes.get("sex"), preset.sex)
                self.assertNotEqual(character.sex, DEFAULT_SEX)

    @covers_requirement("player-character-creation::activation-is-an-all-or-nothing-deterministic-core-operation")
    def test_sex_write_failure_rolls_back_the_whole_activation(self):
        def fail(stage):
            if stage == "sex":
                raise RuntimeError("injected")

        with self.assertRaisesRegex(RuntimeError, "injected"):
            activate_player_character(
                self.account, self.character, self.request(sex="male"),
                write_observer=fail,
            )
        self.assertTrue(self.character.creation_pending)
        # Rollback restores the pre-activation snapshot: the creation-time
        # AttributeProperty default, not the rejected write's "male".
        self.assertEqual(self.character.attributes.get("sex"), DEFAULT_SEX)
        self.assertEqual(self.character.traits.all(), [])


class PresetPersonaLengthSweepTests(unittest.TestCase):
    """The rules-side sweep enforces the persona prose cap at module import.

    ``world/lore/`` may not import ``world/rules/``, so
    ``MAX_PERSONA_FIELD_LENGTH`` is checked over the registry HERE
    (field-parity design 3.1): every string the persona record can carry —
    top-level prose, identity layers, appearance sub-keys, and both sides of a
    social-connection pair — must fit the cap. The sweep runs on synthetic
    cards; the shipped registry's own conformance is a lore-contract claim in
    ``world/lore/tests/test_player_presets.py``.
    """

    @covers_requirement("player-character-creation::the-preset-registry-declares-a-full-persona-in-import-card-shape")
    def test_registry_sweep_raises_for_over_long_persona_prose(self):
        from world.lore.player_presets import (
            PresetAppearance,
            PresetIdentity,
            PresetPersona,
            PlayerPreset,
        )
        from world.rules.character_creation import (
            _validate_preset_persona_lengths,
        )

        card = make_preset("t_sweep_card")

        def make(persona):
            return {"x": replace(card, persona=persona)}

        over = "長" * (MAX_PERSONA_FIELD_LENGTH + 1)
        ok = "長" * MAX_PERSONA_FIELD_LENGTH
        long_name = "名" * (MAX_PERSONA_FIELD_LENGTH + 1)
        for persona, message in (
            (PresetPersona(personality=over), r"persona\.personality"),
            (PresetPersona(background=over), r"persona\.background"),
            (PresetPersona(identity=PresetIdentity(hidden=over)), r"persona\.identity\.hidden"),
            (PresetPersona(appearance=PresetAppearance(feature=over)), r"persona\.appearance\.feature"),
            (PresetPersona(social_connection=(("甲", over),)), r"persona\.social_connection\.甲"),
            (PresetPersona(social_connection=((long_name, "舊識"),)), r"persona\.social_connection key"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(
                CharacterCreationError, message
            ):
                _validate_preset_persona_lengths(make(persona))
        # At-bound values pass.
        _validate_preset_persona_lengths(make(
            PresetPersona(personality=ok, background=ok)
        ))


class PresetValueResolverPurityTests(EvenniaTestCase):
    """``resolve_preset_values`` is callable with only a preset and writes nothing.

    Covers the delta scenario "The resolver is pure": one preset argument, no
    account, no character, no database, no world clock.
    """

    @covers_requirement("player-stat-allocation::player-starting-profiles-are-derived-from-immutable-lore-bands")
    def test_resolver_reads_nothing_but_the_registry_and_writes_nothing(self):
        # Signature: exactly one positional parameter — no account, no character.
        params = list(signature(resolve_preset_values).parameters.values())
        self.assertEqual(
            [(p.name, p.kind) for p in params],
            [("preset", inspect.Parameter.POSITIONAL_OR_KEYWORD)],
        )
        with synthetic_registries(
            "races", "static_tiers", "subraces", "presets", "skills", "items",
            "prices", "elements", "starting_kits",
        ):
            preset = _live_presets()["t_pale_wren"]
            # Zero queries proves no database read and no write; the world-clock
            # accessor always issues a search_script query, so a clock read fails
            # here too. Registries are plain in-memory dicts, so the resolver's
            # only legal inputs cost no queries.
            with self.assertNumQueries(0):
                first = resolve_preset_values(preset)
                second = resolve_preset_values(preset)
        self.assertEqual(first, second)
        # Each call hands back a fresh caller-owned mapping.
        self.assertIsNot(first, second)


class PresetValueResolverParityTests(EvenniaTest):
    """One resolver owns the computation for every in-scope preset."""

    def setUp(self):
        super().setUp()
        open_synthetic_scope(
            self,
            "races",
            "static_tiers",
            "subraces",
            "starting_kits",
            "presets",
            "skills",
            "items",
            "prices",
            "elements",
        )
        self.account = create_account(
            "resolver", "resolver@example.test", "testpassword", typeclass=Account
        )

    @covers_requirement("player-stat-allocation::player-starting-profiles-are-derived-from-immutable-lore-bands")
    def test_resolver_matches_activated_traits_axis_for_axis(self):
        axes = ALLOCATABLE_AXES + ("guild_merit",)
        for preset_key, preset in _live_presets().items():
            with self.subTest(preset=preset_key):
                expected = resolve_preset_values(preset)
                character = create_object(PlayerCharacter, key=f"value-shell-{preset_key}")
                self.account.at_post_create_character(character)
                character.location = self.room1
                activate_player_character(
                    self.account, character,
                    CharacterCreationRequest(mode="preset", preset_key=preset_key),
                )
                for axis in axes:
                    self.assertEqual(
                        character.traits[axis].value, expected[axis],
                        msg=f"{preset_key}/{axis}",
                    )
                self.assertFalse(character.creation_pending)
