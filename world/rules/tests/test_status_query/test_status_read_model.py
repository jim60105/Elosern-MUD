"""Slice of ``test_status_query``: StatusReadModelTests.
"""
from collections.abc import Mapping, Sequence
from dataclasses import replace
import unittest
from unittest.mock import patch
from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase
from typeclasses.characters import PlayerCharacter
from world.lore.sexual_vocab import (
    AROUSAL_LEVELS,
    CLIMAX_PHASE_LEVELS,
    EXPOSURE_LEVELS,
    SHAME_LEVELS,
    WETNESS_LEVELS,
)
from world.rules.buffs import apply_buff
from world.rules.combat_session import engage
from world.rules.sexual_state import _LIFETIME_COUNTER_KEYS
from world.rules.status_query import (
    StatusQueryError,
    build_character_read_model,
    build_status_read_model,
    group_skill_keys,
)
from world.skills.handler import INNATE_SKILL_ORDER
from world.skills.registry import SkillCategory, SkillKind, TargetSpec
from world.tests.synthetic_data import SYNTH_SKILLS, synthetic_registries
from .._combat_session_helpers import (
    _live_registry,
    _race_key,
    open_synthetic_scope,
    synth_innate_overlay,
)
# ``flee`` is injected into ``SKILL_REGISTRY`` at import time by
# ``world.rules.disengage`` (the ``universal-action-ownership`` dependency
# direction), so the grouping and split tests import it explicitly to keep
# ``flee`` in scope.
import world.rules.disengage  # noqa: F401  (registers flee)


from ._support import (
    _actor,
)


class StatusReadModelTests(EvenniaTest):
    def setUp(self):
        # The catalogue scope opens before construction so the fixture
        # entities resolve against the kit race/tier rows (the kit's class
        # decorator wraps test* methods only, not setUp).
        open_synthetic_scope(self, "elements", "races", "subraces", "static_tiers")
        super().setUp()
        self.actor = _actor(self)
        self.actor.location = self.room1

    @covers_requirement(
        "webclient-status-presentation::compact-status-reports-canonical-true-resources"
    )
    def test_resources_report_stored_true_values(self):
        maxima = {}
        for key in ("hp", "mp", "sp"):
            raw = self.actor.attributes.get("traits", category="traits")[key]
            maxima[key] = int(round((raw["base"] + raw["mod"]) * raw["mult"]))
        model = build_status_read_model(self.actor)
        self.assertEqual(model.resources["hp"], model.resources["hp"])
        self.assertEqual(model.resources["hp"].current, maxima["hp"])
        self.assertEqual(model.resources["hp"].maximum, maxima["hp"])
        self.assertEqual(model.resources["mp"].maximum, maxima["mp"])
        self.assertEqual(model.resources["sp"].maximum, maxima["sp"])
        self.actor.traits.hp.current = 30
        model = build_status_read_model(self.actor)
        self.assertEqual(model.resources["hp"].current, 30)
        self.assertEqual(model.resources["hp"].maximum, maxima["hp"])

    @covers_requirement(
        "webclient-status-presentation::compact-status-reports-canonical-true-resources"
    )
    def test_active_disguise_never_changes_true_resources(self):
        maxima = {}
        for key in ("hp", "mp", "sp"):
            raw = self.actor.attributes.get("traits", category="traits")[key]
            maxima[key] = int(round((raw["base"] + raw["mod"]) * raw["mult"]))
        self.actor.traits.hp.current = 80
        self.actor.traits.mp.current = 40
        self.actor.traits.sp.current = 30
        self.actor.db.disguised_stats = {"hp": 200, "mp": 150, "sp": 90}
        model = build_status_read_model(self.actor)
        self.assertEqual(model.resources["hp"].current, 80)
        self.assertEqual(model.resources["hp"].maximum, maxima["hp"])
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
        apply_buff(self.actor, "poisoned")
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
        "combat-modifier-table::high-exposure-defense-penalty-prices-raised-exposure-as-a-combat-cost",
        "webclient-status-presentation::status-conditions-use-deterministic-matched-modifiers",
    )
    def test_high_exposure_defense_penalty_appears_only_while_matched(self):
        model = build_status_read_model(self.actor)
        self.assertFalse(
            any(c.code == "high_exposure_defense_penalty" for c in model.conditions)
        )
        # The threshold levels come from the shipped ordered vocabulary the
        # rulebook itself compares against (EXPOSURE_LEVELS); the display
        # label resolves through the shipped display table.
        from .._equipment_rulebook_probes import display_label

        trigger = EXPOSURE_LEVELS[EXPOSURE_LEVELS.index(EXPOSURE_LEVELS[-1]) - 1]
        calm = EXPOSURE_LEVELS[1]
        self.actor.sexual.exposure.value = trigger
        model = build_status_read_model(self.actor)
        entry = next(
            c for c in model.conditions if c.code == "high_exposure_defense_penalty"
        )
        self.assertEqual(entry.modifiers, {"defense": -15})
        self.assertEqual(entry.severity, "warning")
        self.assertEqual(entry.label, display_label("high_exposure_defense_penalty"))
        self.actor.sexual.exposure.value = calm
        model = build_status_read_model(self.actor)
        self.assertFalse(
            any(c.code == "high_exposure_defense_penalty" for c in model.conditions)
        )

    @covers_requirement(
        "combat-modifier-table::the-eight-previously-dead-passive-buff-combat-prediction-skills-each-grant-a-real-adjustment"
    )
    def test_owned_skill_adjustment_appears_in_status_conditions(self):
        # The rulebook row keyed to the shipped passive whose condition reads
        # ``skill_owned`` for it is located by probe; the entity owns that
        # shipped key (resolved from the row, not a literal), so the match is
        # the real production binding.
        from world.rules.combat_modifiers import _RULES

        (rule,) = [
            rule
            for rule in _RULES
            if rule.id == "defense_instinct_defense_bonus"
        ]
        skill_key = rule.when["skill_owned"]
        self.actor.db.skills = {"active": [], "passive": [skill_key]}
        model = build_status_read_model(self.actor)
        entry = next(c for c in model.conditions if c.code == rule.id)
        self.assertEqual(entry.modifiers, {"defense": 5})
        self.assertEqual(entry.severity, "beneficial")
        from .._equipment_rulebook_probes import display_label

        self.assertEqual(entry.label, display_label(rule.id))

    @covers_requirement(
        "combat-modifier-table::the-eight-previously-dead-passive-buff-combat-prediction-skills-each-grant-a-real-adjustment"
    )
    def test_all_sink_skill_conditions_match_the_bundle_verbatim(self):
        # The five sink rules are located by their stable condition codes;
        # the owned skill keys and every asserted magnitude come from the
        # loaded rulebook rows themselves.
        from world.rules.combat_modifiers import _RULES, evaluate_combat_modifiers

        codes = (
            "defense_instinct_defense_bonus",
            "guardian_instinct_defense_bonus",
            "retainer_martial_training_atk_phys_bonus",
            "precise_mana_control_mp_cost_reduction",
            "extreme_endurance_sp_cost_reduction",
        )
        rows = {rule.id: rule for rule in _RULES if rule.id in codes}
        self.assertEqual(set(rows), set(codes))
        self.actor.db.skills = {
            "active": [],
            "passive": [rows[code].when["skill_owned"] for code in codes],
        }
        expected = {code: dict(rows[code].then) for code in codes}
        defense_sum = sum(
            value
            for code in codes
            for field, value in rows[code].then.items()
            if field == "defense" and isinstance(value, int) and not isinstance(value, bool)
        )
        bundle = evaluate_combat_modifiers(self.actor)
        self.assertEqual(bundle["defense"], defense_sum)
        for code in codes:
            for field, value in rows[code].then.items():
                if field != "defense":
                    self.assertEqual(bundle[field], value)
        model = build_status_read_model(self.actor)
        conditions = {c.code: c for c in model.conditions}
        self.assertEqual(set(conditions) & set(codes), set(codes))
        for code, modifiers in expected.items():
            with self.subTest(code=code):
                self.assertEqual(conditions[code].modifiers, modifiers)
                self.assertEqual(conditions[code].severity, "beneficial")
                self.assertTrue(conditions[code].label)

    def _dual_wield_rule(self):
        from world.rules.combat_modifiers import _RULES

        (rule,) = [
            rule for rule in _RULES if rule.id == "dual_wield_style_atk_phys_bonus"
        ]
        return rule

    def test_dual_wield_style_bonus_appears_only_while_dual_wielding(self):
        rule = self._dual_wield_rule()
        self.actor.db.skills = {"active": [], "passive": [rule.when["skill_owned"]]}
        self.actor.db.equipment = {
            "weapon_main": "left_blade",
            "weapon_off": "right_blade",
        }
        model = build_status_read_model(self.actor)
        entry = next(
            c for c in model.conditions if c.code == "dual_wield_style_atk_phys_bonus"
        )
        self.assertEqual(entry.modifiers, dict(rule.then))
        self.assertEqual(entry.severity, "beneficial")
        from .._equipment_rulebook_probes import display_label

        self.assertEqual(entry.label, display_label(rule.id))
        self.actor.db.equipment = {"weapon_main": "left_blade", "weapon_off": None}
        model = build_status_read_model(self.actor)
        self.assertFalse(
            any(
                c.code == "dual_wield_style_atk_phys_bonus"
                for c in model.conditions
            )
        )

    def test_status_read_does_not_materialize_equipment_handler(self):
        rule = self._dual_wield_rule()
        self.actor.db.skills = {"active": [], "passive": [rule.when["skill_owned"]]}
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
