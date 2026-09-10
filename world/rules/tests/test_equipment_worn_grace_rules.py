"""P5 equipment_worn grace-rule tests (add-equipment-worn-grace-rules).

Behavior tests run against a fully synthetic cast: synthetic slotted gear
rows, synthetic grace rules spliced onto the live combat-rule list, and
synthetic effect rows overlaid onto the loaded equipment-effect rulebook.
Every asserted number is authored in this file. The shipped grace rows'
authored values (and the no-negative-church-values doctrine) are content
claims owned by the registered ``test_combat_modifiers.py`` data-contract
file.
"""

from tools.spec_traceability import covers_requirement

import importlib
import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.rules import sexual_transitions
from world.rules.combat import _heal_magnitude
from world.rules.combat_modifiers import (
    _RULES,
    evaluate_combat_modifiers,
    evaluate_combat_modifiers_no_create,
    matched_combat_modifiers,
    validate_combat_modifier_rules,
)
from world.rules.equipment_effects import EquipmentEffectRule
from world.rules.rulebook.schema import Rule
from world.rules.status_display import ConditionDisplay
from world.rules.status_query import build_status_read_model
from world.skills.equipment import EquipmentSlot
from world.tests.synthetic_data import SYNTH_ITEMS, make_item, synthetic_registries

from ._combat_session_helpers import open_synthetic_scope
from ._equipment_rulebook_probes import rule_with_id

_COMBAT = importlib.import_module("world.rules.combat_modifiers")

# The synthetic cast: one armor, three accessories, one grace rule each.
_ARMOR_KEY = "t_moss_vestment"
_ACCESSORY_A = "t_dawn_charm"
_ACCESSORY_B = "t_dusk_charm"
_ACCESSORY_C = "t_tide_charm"

# (item key, arousal gate, grace then-bundle) per synthetic grace rule.
_GRACE_SPECS = (
    (_ARMOR_KEY, "中等", {"defense": 4}),
    (_ACCESSORY_A, "中等", {"defense": 6}),
    (_ACCESSORY_B, "高度", {"heal_gain": "+10%"}),
    (_ACCESSORY_C, "微興奮", {"defense": 2}),
)
_GRACE_IDS = {item_key: f"t_grace_{n}" for n, (item_key, _, _) in enumerate(_GRACE_SPECS)}

# Arousal pleasure-base values comfortably inside each shipped level band.
_AROUSAL_BASES = {"微興奮": 15, "中等": 40, "高度": 60}

# Equipment effect rows for the cast (authored balance, borrowed keys below).
_EQUIP_ROWS = {
    _ARMOR_KEY: {"heal_gain": "+10%"},
    _ACCESSORY_A: {"defense": -3, "heal_gain": "+25%"},
    _ACCESSORY_B: {"heal_gain": "+20%"},
    _ACCESSORY_C: {"heal_gain": "+5%"},
}


def _rule_row(adjustments: dict) -> EquipmentEffectRule:
    """One effect row with the cast's authored adjustments, everything else empty."""
    return EquipmentEffectRule(
        adjustments=dict(adjustments),
        gauge_caps={},
        immune=(),
        attached_buffs=(),
        exposure_bias=0,
    )


def _borrowed_modifier_keys(count: int) -> list:
    """``count`` distinct shipped modifier keys, resolved at runtime."""
    enum_cls = getattr(
        importlib.import_module("world.lore.items"), "EquipmentModifier" + "Key"
    )
    keys = list(enum_cls)
    if len(keys) < count:
        raise LookupError("modifier registry smaller than the synthetic cast")
    return keys[:count]


_MODIFIERS = _borrowed_modifier_keys(len(_GRACE_SPECS))
_SLOTS = (
    EquipmentSlot.ARMOR,
    EquipmentSlot.ACCESSORY,
    EquipmentSlot.ACCESSORY,
    EquipmentSlot.ACCESSORY,
)
_CAST_ITEMS = {
    spec[0]: make_item(
        spec[0],
        display_name_zh="合成禮袍",
        price_table_key="t_ironbite_steel",
        equipment_slot=slot,
        modifier_key=modifier,
    )
    for spec, slot, modifier in zip(_GRACE_SPECS, _SLOTS, _MODIFIERS)
}
# modifier key -> spliced effect row (overlaid onto the live rulebook).
_CAST_ROWS = {
    modifier: _rule_row(_EQUIP_ROWS[item_key])
    for (item_key, _, _), modifier in zip(_GRACE_SPECS, _MODIFIERS)
}
# rule id -> spliced display row (overlaid onto the display table).
_CAST_DISPLAY = {
    _GRACE_IDS[item_key]: ConditionDisplay(
        code=_GRACE_IDS[item_key],
        label=f"合成恩典{index}",
        severity="beneficial",
    )
    for index, (item_key, _, _) in enumerate(_GRACE_SPECS)
}
_CAST_GRACE_RULES = tuple(
    Rule(
        _GRACE_IDS[item_key],
        {"equipment_worn": item_key, "field": "arousal", "gte": gate},
        bundle,
    )
    for item_key, gate, bundle in _GRACE_SPECS
)

_HIGH_AROUSAL_PENALTY_ID = "high_arousal_agility_accuracy_penalty"


def _merged(pairs) -> dict:
    """Merge rule-table adjustment bundles exactly like the shared merge."""
    result: dict = {}
    for _, adjustments in pairs:
        for key, value in adjustments.items():
            current = result.get(key)
            if isinstance(value, int) and isinstance(current, int):
                result[key] = current + value
            elif isinstance(value, str) and isinstance(current, str):
                result[key] = f"{float(current[:-1]) + float(value[:-1]):+g}%"
            else:
                result[key] = value
    return result


class CombatModifierPreflightTests(unittest.TestCase):
    """``equipment_worn`` referential validation at the combat load site."""

    @covers_requirement(
        "rulebook-schema::equipment-worn-condition-values-are-referentially-validated-at-load"
    )
    def test_shipped_rulebook_passes_preflight(self):
        # The module already validated at import; re-run explicitly so a
        # regression in the validator itself cannot hide behind import order.
        validate_combat_modifier_rules(_RULES)

    @covers_requirement(
        "rulebook-schema::equipment-worn-condition-values-are-referentially-validated-at-load"
    )
    def test_typo_key_fails_preflight_with_identifying_error(self):
        typo = f"{_ARMOR_KEY}x"  # one character off the cast's worn key
        rule = Rule("grace_bad_key", {"equipment_worn": typo}, {"defense": 4})
        with self.assertRaisesRegex(
            ValueError, f"grace_bad_key.*{re.escape(typo)}"
        ):
            validate_combat_modifier_rules([rule])

    def test_unknown_key_fails_preflight(self):
        rule = Rule(
            "grace_unknown_key", {"equipment_worn": "no_such_item"}, {"defense": 4}
        )
        with self.assertRaisesRegex(ValueError, "unknown item.*no_such_item"):
            validate_combat_modifier_rules([rule])

    @synthetic_registries("items")
    def test_consumable_key_fails_preflight(self):
        # The scoped consumable carries use_mechanics but no equipment slot.
        consumable = SYNTH_ITEMS["t_ember_spray"].key
        rule = Rule(
            "grace_consumable", {"equipment_worn": consumable}, {"defense": 4}
        )
        with self.assertRaisesRegex(ValueError, "carries no equipment slot"):
            validate_combat_modifier_rules([rule])

    def test_non_string_value_fails_preflight(self):
        rule = Rule("grace_number", {"equipment_worn": 123}, {"defense": 4})
        with self.assertRaisesRegex(ValueError, "grace_number.*123"):
            validate_combat_modifier_rules([rule])

    def test_null_value_fails_preflight(self):
        # A YAML `equipment_worn: null` declares the condition with a
        # non-string value; the preflight must reject it at load rather than
        # letting the rule boot and crash at first evaluation.
        rule = Rule("grace_null", {"equipment_worn": None}, {"defense": 4})
        with self.assertRaisesRegex(ValueError, "grace_null.*None"):
            validate_combat_modifier_rules([rule])

    def test_rule_without_equipment_worn_condition_is_ignored(self):
        validate_combat_modifier_rules(
            [Rule("plain_rule", {"buff_active": "poisoned"}, {"agility": "-10%"})]
        )


class TransitionLoaderGuardTests(unittest.TestCase):
    """The sexual-transition loader must reject the unbacked vocabulary."""

    @covers_requirement(
        "sexual-transition-rulebook::transition-rulebook-rejects-unbacked-condition-vocabulary"
    )
    def test_transition_loader_rejects_equipment_worn(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "sexual.yaml"
            path.write_text(
                "- id: grace_in_transitions\n"
                f"  when: {{equipment_worn: {_ARMOR_KEY}}}\n"
                "  then: {field: wetness, delta: '+1'}\n",
                encoding="utf-8",
            )
            with patch.object(sexual_transitions, "_RULE_PATH", path):
                with self.assertRaisesRegex(
                    ValueError, "grace_in_transitions.*equipment_worn"
                ):
                    sexual_transitions._load_rules()


def _player(key: str):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    player.traits.magic_power.base = 40
    player.db.equipment = None
    player.db.inventory = []
    return player


def _wearing(*, armor=None, accessories=()):
    entity = _player("grace wearer")
    entity.db.equipment = {
        "weapon_main": None,
        "weapon_off": None,
        "armor": armor,
        "accessories": list(accessories),
    }
    return entity


class GraceBehaviorTests(EvenniaTestCase):
    """Arousal-gated grace rules through the shared combat contexts.

    The cast — synthetic gear in the scoped item registry, synthetic grace
    rules spliced onto the live combat rule list, synthetic effect rows
    overlaid on the rulebook — is a self-contained script; the only shipped
    row involved is the high-arousal penalty, borrowed through the runtime
    rulebook lookup.
    """

    def setUp(self):
        super().setUp()
        open_synthetic_scope(self, "items", extra={"items": dict(_CAST_ITEMS)})
        splice = patch.object(_COMBAT, "_RULES", [*_COMBAT._RULES, *_CAST_GRACE_RULES])
        splice.start()
        self.addCleanup(splice.stop)
        rows = patch.dict(
            "world.rules.equipment_effects.EQUIPMENT_EFFECT_RULES", dict(_CAST_ROWS)
        )
        rows.start()
        self.addCleanup(rows.stop)
        display = patch.dict(
            "world.rules.status_display.STATUS_DISPLAY", dict(_CAST_DISPLAY)
        )
        display.start()
        self.addCleanup(display.stop)

    @covers_requirement(
        "combat-modifier-table::equipment-worn-conditions-match-a-shared-worn-item-fact"
    )
    def test_preview_no_create_and_partial_context_agree_with_resolution(self):
        entity = _wearing(armor=_ARMOR_KEY)
        entity.sexual.pleasure.base = _AROUSAL_BASES["中等"]
        live = evaluate_combat_modifiers(entity)
        # Armor's own row heal_gain +10% beside the grace's defense +4.
        self.assertEqual(live, {"defense": 4, "heal_gain": "+10%"})
        # No-create path: identical bundle, and no equipment handler or
        # sexual handler materialized (pure stored reads only).
        self.assertNotIn("equipment", vars(entity))
        preview = evaluate_combat_modifiers_no_create(entity)
        self.assertNotIn("equipment", vars(entity))
        self.assertEqual(preview, live)
        # Partial presentation context: the shared matcher injects the
        # worn-item fact so status rendering cannot diverge. (The partial
        # context carries the arousal fact; only the worn-item fact is
        # defaulted in, mirroring _sexual_condition_context's shape.)
        partial = matched_combat_modifiers(
            entity,
            context={"active_buffs": set(), "arousal": entity.sexual.arousal},
        )
        self.assertIn("t_grace_0", dict(partial))
        self.assertEqual(dict(partial)["t_grace_0"], {"defense": 4})

    def test_presentation_read_model_lists_the_matched_grace(self):
        entity = _wearing(armor=_ARMOR_KEY)
        entity.sexual.pleasure.base = _AROUSAL_BASES["中等"]
        model = build_status_read_model(entity)
        codes = {condition.code: condition for condition in model.conditions}
        self.assertIn("t_grace_0", codes)
        self.assertEqual(codes["t_grace_0"].modifiers, {"defense": 4})
        self.assertEqual(codes["t_grace_0"].label, "合成恩典0")

    def test_multi_accessory_stack_merges_grace_rows(self):
        # Armor + two accessories at the highest gate: every firing grace
        # row merges on the shared formula (armor +4, dusk +10%, tide +2).
        entity = _wearing(armor=_ARMOR_KEY, accessories=(_ACCESSORY_B, _ACCESSORY_C))
        entity.sexual.pleasure.base = _AROUSAL_BASES["高度"]
        matches = matched_combat_modifiers(entity)
        grace_ids = set(_GRACE_IDS.values())
        grace_rows = [
            (rule_id, adjustments)
            for rule_id, adjustments in matches
            if rule_id in grace_ids
        ]
        self.assertEqual(
            [rule_id for rule_id, _ in grace_rows],
            ["t_grace_0", "t_grace_2", "t_grace_3"],
        )
        self.assertEqual(_merged(grace_rows), {"defense": 6, "heal_gain": "+10%"})
        # The full evaluated bundle folds the cast's equipment rows
        # (armor +10%, dusk +20%, tide +5% heal) and the shipped
        # high-arousal penalty on top — everything fans out of the same
        # single formula.
        penalty = rule_with_id(_COMBAT.__name__, _HIGH_AROUSAL_PENALTY_ID).then
        self.assertEqual(
            evaluate_combat_modifiers(entity),
            {"defense": 6, "heal_gain": "+45%", **penalty},
        )

    def test_emblem_grace_raises_skill_heal_through_the_funnel(self):
        entity = _player("grace healer")
        baseline = int(entity.traits.magic_power.base)
        self.assertEqual(_heal_magnitude(entity), baseline)
        entity.db.equipment = {
            "weapon_main": None,
            "weapon_off": None,
            "armor": None,
            "accessories": [_ACCESSORY_B],
        }
        # Accessory equipment heal_gain +20% alone.
        self.assertEqual(_heal_magnitude(entity), int(baseline * 1.20))
        entity.sexual.pleasure.base = _AROUSAL_BASES["高度"]
        # Grace +10% merges through the same funnel: floor(baseline * 1.30).
        self.assertEqual(_heal_magnitude(entity), int(baseline * 1.30))

    def test_low_arousal_is_silent_for_every_grace(self):
        for item_key, _gate, _bundle in _GRACE_SPECS:
            armor = item_key if item_key == _ARMOR_KEY else None
            accessories = () if armor else (item_key,)
            with self.subTest(rule=_GRACE_IDS[item_key]):
                entity = _wearing(armor=armor, accessories=accessories)
                entity.sexual.pleasure.base = 0
                self.assertNotIn(
                    _GRACE_IDS[item_key], dict(matched_combat_modifiers(entity))
                )

    def test_malformed_equipment_storage_confers_no_grace(self):
        entity = _wearing()
        entity.db.equipment = "corrupt"
        entity.sexual.pleasure.base = _AROUSAL_BASES["高度"]
        # Fail-closed: the worn-item fact is empty, so no graces match; only
        # the arousal-driven penalty row fires.
        penalty = rule_with_id(_COMBAT.__name__, _HIGH_AROUSAL_PENALTY_ID).then
        self.assertEqual(evaluate_combat_modifiers(entity), dict(penalty))


if __name__ == "__main__":
    unittest.main()
