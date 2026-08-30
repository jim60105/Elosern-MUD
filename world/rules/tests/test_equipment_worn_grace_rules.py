"""P5 equipment_worn grace-rule tests (add-equipment-worn-grace-rules).

Covers the combat rulebook's ``equipment_worn`` load-site preflight, the
sexual-transition loader's vocabulary rejection, and the authored 恩典
(grace) rules: arousal-gated firing, preview/resolution/presentation parity,
the declared multi-accessory stack, the heal funnel, malformed-storage
fail-closed behaviour, and the no-negative-Church-values doctrine check.
"""

from tools.spec_traceability import covers_requirement

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
from world.rules.rulebook.schema import Rule
from world.rules.status_query import build_status_read_model

GRACE_RULE_IDS = (
    "sister_vestment_grace",
    "saintess_vestment_grace",
    "holy_emblem_grace",
    "pilgrim_medallion_grace",
)


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
        rule = Rule(
            "grace_bad_key", {"equipment_worn": "sister_vestmenst"}, {"defense": 4}
        )
        with self.assertRaisesRegex(ValueError, "grace_bad_key.*sister_vestmenst"):
            validate_combat_modifier_rules([rule])

    def test_unknown_key_fails_preflight(self):
        rule = Rule(
            "grace_unknown_key", {"equipment_worn": "no_such_item"}, {"defense": 4}
        )
        with self.assertRaisesRegex(ValueError, "unknown item.*no_such_item"):
            validate_combat_modifier_rules([rule])

    def test_consumable_key_fails_preflight(self):
        # healing_potion is a use_mechanics consumable: no equipment slot.
        rule = Rule(
            "grace_consumable", {"equipment_worn": "healing_potion"}, {"defense": 4}
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
                "  when: {equipment_worn: sister_vestments}\n"
                "  then: {field: wetness, delta: '+1'}\n",
                encoding="utf-8",
            )
            with patch.object(
                sexual_transitions, "_RULE_PATH", path
            ):
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


class GraceBehaviorTests(EvenniaTestCase):
    """Arousal-gated grace rules through the shared combat contexts."""

    def _wearing(self, *, armor=None, accessories=()):
        entity = _player("grace wearer")
        entity.db.equipment = {
            "weapon_main": None,
            "weapon_off": None,
            "armor": armor,
            "accessories": list(accessories),
        }
        return entity

    @covers_requirement(
        "combat-modifier-table::equipment-worn-conditions-match-a-shared-worn-item-fact"
    )
    def test_preview_no_create_and_partial_context_agree_with_resolution(self):
        entity = self._wearing(armor="sister_vestments")
        entity.sexual.pleasure.base = 40
        live = evaluate_combat_modifiers(entity)
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
        self.assertIn("sister_vestment_grace", dict(partial))
        self.assertEqual(dict(partial)["sister_vestment_grace"], {"defense": 4})

    def test_presentation_read_model_lists_the_matched_grace(self):
        entity = self._wearing(armor="sister_vestments")
        entity.sexual.pleasure.base = 40
        model = build_status_read_model(entity)
        codes = {condition.code: condition for condition in model.conditions}
        self.assertIn("sister_vestment_grace", codes)
        self.assertEqual(codes["sister_vestment_grace"].modifiers, {"defense": 4})
        self.assertEqual(codes["sister_vestment_grace"].label, "修女聖袍恩典")

    def test_multi_accessory_stack_merges_grace_rows(self):
        # 聖女聖袍 + 光輝聖徽 + 朝聖者銅符 (all within the accessory budget),
        # arousal 高度: the three grace rows merge to defense +8 and the
        # emblem's heal_gain +10% (declare the stack's real ceiling).
        entity = self._wearing(
            armor="saintess_vestments",
            accessories=("radiant_holy_emblem", "pilgrim_medallion"),
        )
        entity.sexual.pleasure.base = 60
        matches = matched_combat_modifiers(entity)
        grace_rows = [
            (rule_id, adjustments)
            for rule_id, adjustments in matches
            if rule_id in GRACE_RULE_IDS
        ]
        self.assertEqual(
            [rule_id for rule_id, _ in grace_rows],
            [
                "saintess_vestment_grace",
                "holy_emblem_grace",
                "pilgrim_medallion_grace",
            ],
        )
        self.assertEqual(_merged(grace_rows), {"defense": 8, "heal_gain": "+10%"})
        # The full evaluated bundle folds the equipment bundle (saintess
        # defense -3, merged heal_gain +50%) and the high-arousal penalty on
        # top — everything fans out of the same single formula.
        self.assertEqual(
            evaluate_combat_modifiers(entity),
            {
                "defense": 5,
                "heal_gain": "+60%",
                "agility": "-20%",
                "accuracy": -15,
            },
        )
        model = build_status_read_model(entity)
        codes = {condition.code for condition in model.conditions}
        for rule_id in (
            "saintess_vestment_grace",
            "holy_emblem_grace",
            "pilgrim_medallion_grace",
        ):
            self.assertIn(rule_id, codes)

    def test_emblem_grace_raises_skill_heal_through_the_funnel(self):
        entity = _player("grace healer")
        self.assertEqual(_heal_magnitude(entity), 40)
        entity.db.equipment = {
            "weapon_main": None,
            "weapon_off": None,
            "armor": None,
            "accessories": ["radiant_holy_emblem"],
        }
        # Emblem equipment heal_gain +20% alone.
        self.assertEqual(_heal_magnitude(entity), 48)
        entity.sexual.pleasure.base = 60
        # Grace +10% merges through the same funnel: floor(40 * 1.30) == 52.
        self.assertEqual(_heal_magnitude(entity), 52)

    def test_low_arousal_is_silent_for_every_grace(self):
        for armor, accessories, rule_id in (
            ("sister_vestments", (), "sister_vestment_grace"),
            ("saintess_vestments", (), "saintess_vestment_grace"),
            (None, ("radiant_holy_emblem",), "holy_emblem_grace"),
            (None, ("pilgrim_medallion",), "pilgrim_medallion_grace"),
        ):
            with self.subTest(rule=rule_id):
                entity = self._wearing(armor=armor, accessories=accessories)
                entity.sexual.pleasure.base = 0
                self.assertNotIn(rule_id, dict(matched_combat_modifiers(entity)))

    def test_malformed_equipment_storage_confers_no_grace(self):
        entity = self._wearing()
        entity.db.equipment = "corrupt"
        entity.sexual.pleasure.base = 60
        # Fail-closed: the worn-item fact is empty, so no graces match; only
        # the arousal-driven penalty row fires.
        self.assertEqual(
            evaluate_combat_modifiers(entity),
            {"agility": "-20%", "accuracy": -15},
        )

    def test_grace_adjustments_carry_no_negative_church_values(self):
        # 光明教會 doctrine (以坦露為聖、恩賜為正): no grace rule may carry a
        # negative adjustment — the grace set is a blessing, not a curse.
        for rule in _RULES:
            if rule.id not in GRACE_RULE_IDS:
                continue
            for key, value in rule.then.items():
                if isinstance(value, int):
                    self.assertGreaterEqual(value, 0, (rule.id, key))
                elif isinstance(value, str) and value.endswith("%"):
                    self.assertGreaterEqual(int(value[:-1]), 0, (rule.id, key))


if __name__ == "__main__":
    unittest.main()