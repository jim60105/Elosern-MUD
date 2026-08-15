"""Frozen no-create status read model tests (foundation section 3.3)."""

import unittest

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.buffs import _add_buff
from world.rules.combat_session import engage
from world.rules.status_query import (
    StatusQueryError,
    build_character_read_model,
    build_status_read_model,
)


def _actor(testcase):
    actor = create_object(PlayerCharacter, key="status actor")
    actor.race = "human"
    actor.apply_race_baseline()
    return actor


class StatusReadModelTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.actor = _actor(self)
        self.actor.location = self.room1

    @covers_requirement(
        "webclient-status-presentation::compact-status-reports-canonical-true-resources"
    )
    def test_resources_report_stored_true_values(self):
        model = build_status_read_model(self.actor)
        self.assertEqual(model.resources["hp"], model.resources["hp"])
        self.assertEqual(model.resources["hp"].current, 100)
        self.assertEqual(model.resources["hp"].maximum, 100)
        self.assertEqual(model.resources["mp"].maximum, 100)
        self.assertEqual(model.resources["sp"].maximum, 100)
        self.actor.traits.hp.current = 30
        model = build_status_read_model(self.actor)
        self.assertEqual(model.resources["hp"].current, 30)
        self.assertEqual(model.resources["hp"].maximum, 100)

    @covers_requirement(
        "webclient-status-presentation::compact-status-reports-canonical-true-resources"
    )
    def test_active_disguise_never_changes_true_resources(self):
        self.actor.traits.hp.current = 80
        self.actor.traits.mp.current = 40
        self.actor.traits.sp.current = 30
        self.actor.db.disguised_stats = {"hp": 200, "mp": 150, "sp": 90}
        model = build_status_read_model(self.actor)
        self.assertEqual(model.resources["hp"].current, 80)
        self.assertEqual(model.resources["hp"].maximum, 100)
        self.assertEqual(model.resources["mp"].current, 40)
        self.assertEqual(model.resources["sp"].current, 30)
        self.assertTrue(model.disguise_active)

    @covers_requirement(
        "webclient-status-presentation::compact-status-reports-canonical-true-resources"
    )
    def test_missing_gauge_fails_closed(self):
        self.actor.attributes.remove("traits", category="traits")
        with self.assertRaises(StatusQueryError):
            build_status_read_model(self.actor)

    @covers_requirement(
        "webclient-status-presentation::status-conditions-use-deterministic-matched-modifiers"
    )
    def test_poisoned_buff_reports_duration_and_exact_adjustment(self):
        _add_buff(self.actor, "poisoned")
        # poison remaining_seconds defaults to definition duration 300.
        model = build_status_read_model(self.actor)
        poisoned = next(
            condition for condition in model.conditions if condition.code == "poisoned"
        )
        self.assertEqual(poisoned.label, "中毒")
        self.assertEqual(poisoned.severity, "harmful")
        self.assertEqual(poisoned.remaining_seconds, 300)
        penalty = next(
            condition
            for condition in model.conditions
            if condition.code == "poison_agility_penalty"
        )
        self.assertEqual(penalty.modifiers, {"agility": "-10%"})

    @covers_requirement(
        "webclient-status-presentation::status-conditions-use-deterministic-matched-modifiers"
    )
    def test_sexual_threshold_appears_only_while_matched(self):
        model = build_status_read_model(self.actor)
        self.assertFalse(
            any(c.code == "high_arousal_agility_accuracy_penalty" for c in model.conditions)
        )
        self.actor.sexual.pleasure.base = 85
        model = build_status_read_model(self.actor)
        entry = next(
            c for c in model.conditions if c.code == "high_arousal_agility_accuracy_penalty"
        )
        self.assertEqual(entry.modifiers, {"agility": "-20%", "accuracy": -15})
        self.assertEqual(entry.severity, "warning")

    @covers_requirement(
        "combat-modifier-table::the-eight-previously-dead-passive-buff-combat-prediction-skills-each-grant-a-real-adjustment"
    )
    def test_owned_skill_adjustment_appears_in_status_conditions(self):
        self.actor.db.skills = {"active": [], "passive": ["defense_instinct"]}
        model = build_status_read_model(self.actor)
        entry = next(
            c for c in model.conditions if c.code == "defense_instinct_defense_bonus"
        )
        self.assertEqual(entry.modifiers, {"defense": 5})
        self.assertEqual(entry.severity, "beneficial")
        self.assertEqual(entry.label, "防禦直覺防禦提升")

    @covers_requirement(
        "combat-modifier-table::the-eight-previously-dead-passive-buff-combat-prediction-skills-each-grant-a-real-adjustment"
    )
    def test_all_sink_skill_conditions_match_the_bundle_verbatim(self):
        self.actor.db.skills = {
            "active": [],
            "passive": [
                "defense_instinct",
                "guardian_instinct",
                "retainer_martial_training",
                "precise_mana_control",
                "extreme_endurance",
            ],
        }
        from world.rules.combat_modifiers import evaluate_combat_modifiers

        self.assertEqual(
            evaluate_combat_modifiers(self.actor),
            {
                "defense": 10,
                "atk_phys": 5,
                "mp_cost": "-10%",
                "sp_cost": "-10%",
            },
        )
        model = build_status_read_model(self.actor)
        conditions = {c.code: c for c in model.conditions}
        expected = {
            "defense_instinct_defense_bonus": {"defense": 5},
            "guardian_instinct_defense_bonus": {"defense": 5},
            "retainer_martial_training_atk_phys_bonus": {"atk_phys": 5},
            "precise_mana_control_mp_cost_reduction": {"mp_cost": "-10%"},
            "extreme_endurance_sp_cost_reduction": {"sp_cost": "-10%"},
        }
        self.assertEqual(set(conditions) & set(expected), set(expected))
        for code, modifiers in expected.items():
            with self.subTest(code=code):
                self.assertEqual(conditions[code].modifiers, modifiers)
                self.assertEqual(conditions[code].severity, "beneficial")
                self.assertTrue(conditions[code].label)

    def test_dual_wield_style_bonus_appears_only_while_dual_wielding(self):
        self.actor.db.skills = {"active": [], "passive": ["dual_wield_style"]}
        self.actor.db.equipment = {
            "weapon_main": "left_blade",
            "weapon_off": "right_blade",
        }
        model = build_status_read_model(self.actor)
        entry = next(
            c for c in model.conditions if c.code == "dual_wield_style_atk_phys_bonus"
        )
        self.assertEqual(entry.modifiers, {"atk_phys": 5})
        self.assertEqual(entry.severity, "beneficial")
        self.assertEqual(entry.label, "雙持劍術攻擊提升")
        self.actor.db.equipment = {"weapon_main": "left_blade", "weapon_off": None}
        model = build_status_read_model(self.actor)
        self.assertFalse(
            any(
                c.code == "dual_wield_style_atk_phys_bonus"
                for c in model.conditions
            )
        )

    def test_status_read_does_not_materialize_equipment_handler(self):
        self.actor.db.skills = {"active": [], "passive": ["dual_wield_style"]}
        self.actor.db.equipment = {
            "weapon_main": "left_blade",
            "weapon_off": "right_blade",
        }
        self.assertNotIn("equipment", vars(self.actor))
        build_status_read_model(self.actor)
        self.assertNotIn("equipment", vars(self.actor))

    @covers_requirement(
        "webclient-status-presentation::status-presentation-has-no-mutation-side-effects"
    )
    def test_unmaterialized_sexual_baseline_remains_unmaterialized(self):
        self.actor.db.sexual = {
            "arousal": "平靜",
            "wetness": "乾燥",
            "shame": "無",
            "exposure": "遮蔽",
            "climax_phase": "未達",
            "sensitivity": {},
            "climax_today": 0,
            "virgin": True,
            "experience_types": [],
        }
        self.assertIsNone(self.actor.attributes.get("sexual_traits", category="traits"))
        build_status_read_model(self.actor)
        self.assertIsNone(
            self.actor.attributes.get("sexual_traits", category="traits"),
            "reading status must not materialize the sexual handler",
        )

    @covers_requirement("webclient-status-presentation::the-no-create-status-read-model-resolves-the-derived-arousal-level-from-stored-pleasure-not-a-raw-arousal-key")
    def test_status_panel_reflects_live_pleasure_on_materialized_entity(self):
        self.actor.sexual.pleasure.base = 61
        model = build_status_read_model(self.actor)
        entry = next(
            c for c in model.conditions if c.code == "high_arousal_agility_accuracy_penalty"
        )
        self.assertEqual(entry.label, "高度興奮敏捷與準度減損")
        self.assertEqual(entry.modifiers, {"agility": "-20%", "accuracy": -15})

    @covers_requirement("webclient-status-presentation::the-no-create-status-read-model-resolves-the-derived-arousal-level-from-stored-pleasure-not-a-raw-arousal-key")
    def test_status_panel_entry_disappears_when_pleasure_drops_below_the_band(self):
        self.actor.sexual.pleasure.base = 61
        first = build_status_read_model(self.actor)
        self.assertTrue(
            any(
                c.code == "high_arousal_agility_accuracy_penalty"
                for c in first.conditions
            )
        )
        self.actor.sexual.pleasure.base = 59
        second = build_status_read_model(self.actor)
        self.assertFalse(
            any(
                c.code == "high_arousal_agility_accuracy_penalty"
                for c in second.conditions
            )
        )

    @covers_requirement("webclient-status-presentation::the-no-create-status-read-model-resolves-the-derived-arousal-level-from-stored-pleasure-not-a-raw-arousal-key")
    def test_status_of_unmaterialized_entity_resolves_from_baseline_without_materializing(self):
        self.actor.db.sexual = {
            "arousal": "極限",
            "wetness": "乾燥",
            "shame": "無",
            "exposure": "極低",
            "climax_phase": "未達",
            "sensitivity": {},
            "climax_today": 0,
            "virgin": True,
            "experience_types": [],
        }
        self.assertIsNone(self.actor.attributes.get("sexual_traits", category="traits"))
        model = build_status_read_model(self.actor)
        entry = next(
            c for c in model.conditions if c.code == "high_arousal_agility_accuracy_penalty"
        )
        self.assertEqual(entry.modifiers, {"agility": "-20%", "accuracy": -15})
        self.assertIsNone(
            self.actor.attributes.get("sexual_traits", category="traits"),
            "status reads must not materialize the sexual handler",
        )

    @covers_requirement("webclient-status-presentation::the-no-create-status-read-model-resolves-the-derived-arousal-level-from-stored-pleasure-not-a-raw-arousal-key")
    def test_status_panel_tracks_a_ceilinged_stored_base(self):
        # CounterTrait.base's setter clamps writes into [0, 100]; the status
        # reader must resolve the stored base exactly as the live trait.value
        # read does, including at the ceiling.
        self.actor.sexual.pleasure.base = 95
        self.actor.sexual.pleasure.base += 14
        self.assertEqual(self.actor.sexual.pleasure.value, 100)
        model = build_status_read_model(self.actor)
        self.assertTrue(
            any(
                c.code == "high_arousal_agility_accuracy_penalty"
                for c in model.conditions
            )
        )

    @covers_requirement("webclient-status-presentation::the-no-create-status-read-model-resolves-the-derived-arousal-level-from-stored-pleasure-not-a-raw-arousal-key")
    def test_status_panel_rejects_a_boolean_stored_base(self):
        self.actor.sexual.pleasure.base = 60
        raw = dict(self.actor.attributes.get("sexual_traits", category="traits"))
        raw["pleasure"] = dict(raw["pleasure"])
        raw["pleasure"]["base"] = True
        self.actor.attributes.add("sexual_traits", raw, category="traits")
        model = build_status_read_model(self.actor)
        self.assertFalse(
            any(
                c.code == "high_arousal_agility_accuracy_penalty"
                for c in model.conditions
            )
        )

    def test_malformed_buff_cache_and_entries_fail_closed(self):
        self.actor.attributes.add("buffs", "junk")
        with self.assertRaises(StatusQueryError):
            build_status_read_model(self.actor)
        self.actor.attributes.add("buffs", None)
        model = build_status_read_model(self.actor)
        self.assertEqual(model.conditions, ())
        self.actor.attributes.add("buffs", {"bad": "junk"})
        with self.assertRaises(StatusQueryError):
            build_status_read_model(self.actor)

    def test_paused_zero_stack_and_expired_buff_entries_are_skipped(self):
        self.actor.attributes.add(
            "buffs",
            {
                "paused_one": {"definition_key": "poisoned", "stacks": 1, "paused": True},
                "zero_stacks": {"definition_key": "poisoned", "stacks": 0},
                "expired": {"definition_key": "poisoned", "stacks": 1, "remaining_seconds": 0},
            },
        )
        model = build_status_read_model(self.actor)
        self.assertEqual(model.conditions, ())

    def test_unknown_buff_definition_fails_closed(self):
        self.actor.attributes.add(
            "buffs", {"mystery": {"definition_key": "nope", "stacks": 1}}
        )
        with self.assertRaises(StatusQueryError):
            build_status_read_model(self.actor)

    def test_malformed_combat_record_fails_closed(self):
        for raw in ("junk", {"mode": "bandit", "rounds_elapsed": 1}):
            self.actor.attributes.add("active_combat", raw)
            with self.assertRaises(StatusQueryError):
                build_status_read_model(self.actor)
        self.actor.attributes.add(
            "active_combat", {"mode": "hostile", "rounds_elapsed": -1}
        )
        with self.assertRaises(StatusQueryError):
            build_status_read_model(self.actor)


class CharacterReadModelTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.actor = _actor(self)

    def _traits(self):
        return dict(self.actor.attributes.get("traits", category="traits"))

    def _model(self):
        return build_character_read_model(self.actor)

    def test_reads_gauges_statics_and_counters(self):
        model = self._model()
        self.assertEqual(
            [trait.key for trait in model.traits],
            ["hp", "mp", "sp", "atk_phys", "agility", "defense", "magic_level", "guild_merit"],
        )
        hp = next(trait for trait in model.traits if trait.key == "hp")
        self.assertEqual(hp.current, 100)
        self.assertEqual(hp.maximum, 100)
        atk = next(trait for trait in model.traits if trait.key == "atk_phys")
        self.assertIsNone(atk.maximum)
        self.assertEqual(model.wallet, 0)

    def test_malformed_gauge_base_modifier_and_multiplier_fail_closed(self):
        for field in ("base", "mod", "mult"):
            traits = self._traits()
            traits["hp"] = {**traits["hp"], field: True}
            self.actor.attributes.add("traits", traits, category="traits")
            with self.assertRaises(StatusQueryError):
                self._model()

    def test_gauge_current_validation_fails_closed(self):
        for value in (True, -1, 10**9):
            traits = self._traits()
            traits["hp"]["current"] = value
            self.actor.attributes.add("traits", traits, category="traits")
            with self.assertRaises(StatusQueryError):
                self._model()

    def test_malformed_static_and_counter_traits_fail_closed(self):
        traits = self._traits()
        del traits["atk_phys"]
        self.actor.attributes.add("traits", traits, category="traits")
        with self.assertRaises(StatusQueryError):
            self._model()
        traits["atk_phys"] = {"base": True}
        self.actor.attributes.add("traits", traits, category="traits")
        with self.assertRaises(StatusQueryError):
            self._model()
        traits["guild_merit"] = {"base": -5}
        self.actor.attributes.add("traits", traits, category="traits")
        with self.assertRaises(StatusQueryError):
            self._model()

    def test_non_sequence_passive_and_junk_accessories_are_skipped(self):
        self.actor.db.skills = {"active": [], "passive": "none"}
        model = self._model()
        self.assertEqual(model.passive_keys, ())
        self.actor.db.equipment = {
            "weapon_main": "plain_sword",
            "weapon_off": None,
            "armor": None,
            "accessories": ["ring", 5, None],
        }
        model = self._model()
        self.assertEqual(
            [row.slot for row in model.equipment], ["weapon_main", "accessory"]
        )

    def test_malformed_disguise_fails_closed(self):
        self.actor.db.disguised_stats = "yes"
        with self.assertRaises(StatusQueryError):
            self._model()
        self.actor.db.disguised_stats = {"": 5}
        with self.assertRaises(StatusQueryError):
            self._model()
        self.actor.db.disguised_stats = {"atk_phys": True}
        with self.assertRaises(StatusQueryError):
            self._model()

    def test_malformed_wallet_fails_closed(self):
        for value in (True, -1):
            self.actor.db.wallet = value
            with self.assertRaises(StatusQueryError):
                self._model()


class LevelRefComparisonTests(unittest.TestCase):
    def test_ordinal_comparisons_accept_levelref_str_and_int(self):
        from world.rules.status_query import _LevelRef

        levels = ("a", "b", "c")
        ref = _LevelRef(1, levels)
        self.assertEqual(ref, _LevelRef(1, levels))
        self.assertEqual(ref, "b")
        self.assertEqual(ref == 1, True)
        self.assertTrue(ref >= 0)
        self.assertTrue(ref <= "c")
        self.assertTrue(ref < 2)
        self.assertTrue(ref > 0)


if __name__ == "__main__":
    unittest.main()
