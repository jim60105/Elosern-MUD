"""Regression tests for the display-only disguise boundary."""

from pathlib import Path

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.traits import get_display_value

FORBIDDEN_MODULES = (
    "world/rules/combat.py",
    "world/rules/dice.py",
    "world/rules/targeting.py",
)


class DisguiseBoundaryTests(EvenniaTest):
    def test_forbidden_rules_modules_do_not_read_disguise_layer(self):
        root = Path(__file__).resolve().parents[3]
        for relative_path in FORBIDDEN_MODULES:
            path = root / relative_path
            if path.exists():
                source = path.read_text(encoding="utf-8")
                self.assertNotIn("disguised_stats", source, relative_path)
                self.assertNotIn("get_display_value", source, relative_path)

    def test_accessor_changes_display_without_changing_true_values(self):
        entity = create_object(PlayerCharacter, key="disguised")
        entity.race = "elf"
        entity.apply_race_baseline()
        true_attack = entity.traits.atk_phys.value
        true_defense = entity.traits.defense.value
        entity.db.disguised_stats = {"atk_phys": 60, "magic_level": 30}
        self.assertEqual(get_display_value(entity, "atk_phys"), 60)
        self.assertEqual(get_display_value(entity, "defense"), true_defense)
        self.assertEqual(entity.traits.atk_phys.value, true_attack)
        self.assertEqual(entity.traits.magic_level.value, 0)
