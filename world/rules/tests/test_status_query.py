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
        self.actor.sexual.arousal.value = "極限"
        model = build_status_read_model(self.actor)
        entry = next(
            c for c in model.conditions if c.code == "high_arousal_agility_accuracy_penalty"
        )
        self.assertEqual(entry.modifiers, {"agility": "-20%", "accuracy": -15})
        self.assertEqual(entry.severity, "warning")

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


if __name__ == "__main__":
    unittest.main()
