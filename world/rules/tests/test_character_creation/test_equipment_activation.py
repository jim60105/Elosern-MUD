"""Slice of ``test_character_creation``: CharacterActivationTests."""
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

from ._support import (
    _BEADS_ROW,
    _BUFF_ENTRY,
    _CAP_ENTRY,
    _DEEP_PRESET,
    _LINEAGE_SKILLS,
    _NEUTRAL_WEAPON,
    _OFFHAND_ROW,
    _PACK_TRINKET,
    _PLATEMAIL_ROW,
    _SLOT_ACCESSORIES,
    _SLOT_ARMOR,
    _SLOT_MAIN,
    _SLOT_OFF,
    _STRONG_BORN,
    _STRONG_FOLK,
    _WORN_KIT_SUBRACE,
    _race_key,
    balanced_allocations,
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
    def test_custom_activation_wears_the_whole_subrace_kit(self):
        # Scenario "A custom character wakes with its subrace kit" as
        # reversed by custom-kit-worn-at-activation: every kit item lands in
        # the slot its ItemDefinition.equipment_slot resolves to, through the
        # same toggle loop presets use. The fixture kit is deliberately
        # multi-item (weapon_main + weapon_off + buffed accessory + capped
        # armor — one collision-clean row per slot) because custom
        # activations exercise toggle_equipment, its buff attachment, and the
        # gauge-ceiling recompute for the first time (design D2).
        kit = SubraceStartingKit(
            _WORN_KIT_SUBRACE.key,
            (
                (_NEUTRAL_WEAPON.key, 1),
                # Quantity 2 pins the derivation: starting_equipment comes
                # from the kit's one entry per key, never from the flattened
                # inventory (a repeated key would toggle the item on and off).
                (_OFFHAND_ROW.key, 2),
                (_BEADS_ROW.key, 1),
                (_PLATEMAIL_ROW.key, 1),
            ),
        )
        with synthetic_registries(
            "races",
            "subraces",
            "starting_kits",
            "items",
            extra={
                "subraces": {_WORN_KIT_SUBRACE.key: _WORN_KIT_SUBRACE},
                "starting_kits": {_WORN_KIT_SUBRACE.key: kit},
                "items": {
                    _OFFHAND_ROW.key: _OFFHAND_ROW,
                    _NEUTRAL_WEAPON.key: _NEUTRAL_WEAPON,
                    _PLATEMAIL_ROW.key: _PLATEMAIL_ROW,
                    _BEADS_ROW.key: _BEADS_ROW,
                },
            },
        ):
            allocations = balanced_allocations(_race_key(), _WORN_KIT_SUBRACE.key)
            observed: list[str] = []
            activate_player_character(
                self.account, self.character,
                self.request(
                    subrace=_WORN_KIT_SUBRACE.key, allocations=allocations
                ),
                write_observer=observed.append,
            )
        # Every kit item occupies its registry-resolved slot.
        self.assertEqual(
            dict(self.character.db.equipment),
            {
                _SLOT_MAIN: _NEUTRAL_WEAPON.key,
                _SLOT_OFF: _OFFHAND_ROW.key,
                _SLOT_ARMOR: _PLATEMAIL_ROW.key,
                _SLOT_ACCESSORIES: [_BEADS_ROW.key],
            },
        )
        # Worn items remain in canonical inventory, exactly at kit quantities.
        self.assertEqual(
            self.character.db.inventory,
            [
                key
                for key, qty in kit.items
                for _ in range(qty)
            ],
        )
        # The beads' attached buff is present EXACTLY once for the multi-item
        # kit: one instance key with one stack and the definition the
        # rulebook row attaches (the idempotence surface a consumer reads).
        instance_key = f"{_BUFF_ENTRY.attached_buffs[0]}:{_BEADS_ROW.key}"
        self.assertIn(instance_key, self.character.db.buffs)
        self.assertEqual(len(self.character.db.buffs), 1)
        self.assertEqual(self.character.db.buffs[instance_key]["stacks"], 1)
        self.assertEqual(
            self.character.db.buffs[instance_key]["definition_key"],
            _BUFF_ENTRY.attached_buffs[0],
        )
        # The capped armor's gauge ceiling applies from activation: the sole
        # writer recomputes the hp ceiling's mod from scratch as exactly the
        # worn set's cap against the final traits.
        self.assertEqual(self.character.traits.hp.mod, _CAP_ENTRY.gauge_caps["hp"])
        # The shared stage fired exactly once, AFTER the inventory write the
        # toggle preflight depends on (an observed stage means a real
        # completed toggle sequence).
        self.assertEqual(observed.count("starting_equipment"), 1)
        self.assertLess(observed.index("inventory"), observed.index("starting_equipment"))
        self.assertFalse(self.character.creation_pending)
