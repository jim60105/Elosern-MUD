"""One-to-one rule and invariant tests for sexual transitions."""

from tools.spec_traceability import covers_requirement

import inspect
from pathlib import Path
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.rulebook.schema import Rule, load_rules
from world.rules import sexual_transitions
from world.rules.sexual_state import decay_tick
from world.rules.sexual_transitions import (
    FIELD_KINDS,
    RuleConvergenceError,
    _apply_then,
    _parse_delta,
    _validate_rule_effect,
    apply_event,
)


RULE_PATH = Path(__file__).parents[1] / "rulebook" / "sexual.yaml"
RULES = {rule.id: rule for rule in load_rules(RULE_PATH)}


class FixedRng:
    """RNG stub returning a chosen in-range value."""

    def __init__(self, value: int):
        self.value = value
        self.calls: list[tuple[int, int]] = []

    def randint(self, lower: int, upper: int) -> int:
        self.calls.append((lower, upper))
        if not lower <= self.value <= upper:
            raise AssertionError(f"{self.value} is outside [{lower}, {upper}]")
        return self.value


class SexualTransitionTests(EvenniaTest):
    def _entity(self):
        entity = create_object(PlayerCharacter, key="transition target")
        entity.race = "human"
        entity.apply_race_baseline()
        return entity

    def test_rule_arousal_up_on_stimulus(self):
        entity = self._entity()
        rng = FixedRng(14)
        apply_event(entity, "stimulus_applied", rng=rng)
        self.assertEqual(entity.sexual.pleasure.value, 14)
        self.assertIn((8, 14), rng.calls)

    @covers_requirement("sexual-transition-rulebook::pleasure-targeting-rules-write-through-the-bounded-counter-kind-and-report-their-arousal-level-crossing-under-the-field-name-arousal")
    def test_rule_arousal_up_on_sustained_stimulus(self):
        entity = self._entity()
        apply_event(entity, "sustained_stimulus_applied")
        self.assertEqual(entity.sexual.pleasure.value, 6)

    def test_rule_arousal_extreme_stimulus_to_max(self):
        entity = self._entity()
        entity.sexual.pleasure.base = 15
        apply_event(entity, "extreme_stimulus_applied")
        self.assertEqual(entity.sexual.pleasure.value, 100)
        self.assertEqual(entity.sexual.arousal.level, "極限")

    def test_rule_arousal_reset_after_climax(self):
        entity = self._entity()
        entity.sexual.pleasure.base = 60
        apply_event(entity, "climax_ends", rng=FixedRng(-25))
        self.assertEqual(entity.sexual.pleasure.value, 15)
        self.assertEqual(entity.sexual.arousal.level, "微興奮")

    @covers_requirement("sexual-transition-rulebook::ordered-level-field-rules-write-through-the-field-s-own-live-trait-object-never-through-a-second-write-path")
    def test_rule_wetness_follows_arousal(self):
        entity = self._entity()
        entity.sexual.pleasure.base = 10
        apply_event(entity, "stimulus_applied", rng=FixedRng(8))
        self.assertEqual(entity.sexual.wetness.value, 1)

    @covers_requirement("sexual-transition-rulebook::pleasure-targeting-rules-write-through-the-bounded-counter-kind-and-report-their-arousal-level-crossing-under-the-field-name-arousal")
    def test_band_crossing_pleasure_delta_reports_an_arousal_change(self):
        entity = self._entity()
        entity.sexual.pleasure.base = 10
        changes = apply_event(entity, "stimulus_applied", rng=FixedRng(8))
        self.assertEqual(entity.sexual.pleasure.value, 18)
        self.assertEqual(changes, {"arousal": "up", "wetness": "up"})
        self.assertEqual(entity.sexual.wetness.value, 1)

    @covers_requirement("sexual-transition-rulebook::pleasure-targeting-rules-write-through-the-bounded-counter-kind-and-report-their-arousal-level-crossing-under-the-field-name-arousal")
    def test_band_staying_pleasure_delta_reports_no_change(self):
        entity = self._entity()
        entity.sexual.pleasure.base = 20
        changes = apply_event(entity, "stimulus_applied", rng=FixedRng(8))
        self.assertEqual(entity.sexual.pleasure.value, 28)
        self.assertEqual(changes, {})
        self.assertEqual(entity.sexual.wetness.value, 0)

    @covers_requirement("sexual-transition-rulebook::pleasure-targeting-rules-write-through-the-bounded-counter-kind-and-report-their-arousal-level-crossing-under-the-field-name-arousal")
    def test_climax_gate_still_fires_from_a_pleasure_driven_arousal_change(self):
        entity = self._entity()
        apply_event(entity, "extreme_stimulus_applied")
        self.assertEqual(entity.sexual.pleasure.value, 100)
        self.assertEqual(entity.sexual.arousal.level, "極限")
        self.assertEqual(entity.sexual.climax_phase.level, "接近")

    def test_pleasure_engine_never_uses_the_counter_current_channel(self):
        # CounterTrait.value is (current + mod) * mult and falls back to base
        # only while no "current" key is stored: one stray .current write
        # would freeze the gauge and hide every later .base write. The engine
        # writes base exclusively; pin the raw-storage invariant across rule
        # mutation and decay.
        entity = self._entity()
        entity.sexual.pleasure.base = 10
        apply_event(entity, "stimulus_applied", rng=FixedRng(8))
        decay_tick(entity, 1800)
        raw = entity.attributes.get(
            "sexual_traits", default={}, category="traits"
        )["pleasure"]
        self.assertNotIn("current", raw)
        self.assertEqual(raw["base"], entity.sexual.pleasure.value)

    def test_pleasure_writes_route_through_base_only(self):
        source = inspect.getsource(sexual_transitions)
        self.assertNotIn(".pleasure.current", source)
        self.assertIn("trait.base +=", source)
        state_source = inspect.getsource(decay_tick)
        self.assertNotIn(".current", state_source)
        self.assertIn("trait.base =", state_source)

    def test_rule_wetness_up_on_direct_stimulus(self):
        entity = self._entity()
        rng = FixedRng(2)
        apply_event(entity, "direct_stimulus_applied", rng=rng)
        self.assertEqual(entity.sexual.wetness.value, 2)
        self.assertEqual(rng.calls, [(1, 2)])

    def test_rule_wetness_max_on_climax(self):
        entity = self._entity()
        apply_event(entity, "climax_ends", rng=FixedRng(-25))
        self.assertEqual(entity.sexual.wetness.level, "泛濫")

    @covers_requirement("sexual-transition-rulebook::sensitivity-rules-target-the-body-part-supplied-by-the-triggering-event-not-a-fixed-part-named-in-the-rule")
    def test_rule_sensitivity_up_on_frequent_stimulation(self):
        entity = self._entity()
        apply_event(entity, "frequent_stimulation", part="乳房")
        self.assertEqual(entity.sexual.sensitivity["乳房"].value, 1)
        apply_event(entity, "frequent_stimulation", part="私處")
        self.assertEqual(entity.sexual.sensitivity["私處"].value, 1)
        self.assertEqual(entity.sexual.sensitivity["乳房"].value, 1)
        with self.assertRaises(KeyError):
            apply_event(entity, "frequent_stimulation")

    @covers_requirement("sexual-transition-rulebook::race-specific-behavior-and-narrative-only-fields-have-no-row-in-sexual-yaml")
    def test_rule_climax_gate(self):
        entity = self._entity()
        apply_event(entity, "extreme_stimulus_applied")
        self.assertEqual(entity.sexual.climax_phase.level, "接近")
        apply_event(entity, "extreme_stimulus_applied")
        self.assertEqual(entity.sexual.climax_phase.level, "接近")
        entity.sexual.climax_phase.value = "進行中"
        apply_event(entity, "extreme_stimulus_applied")
        self.assertEqual(entity.sexual.climax_phase.level, "進行中")

    def test_rule_climax_phase_critical_point_to_in_progress(self):
        entity = self._entity()
        entity.sexual.climax_phase.value = "接近"
        apply_event(entity, "stimulus_applied", rng=FixedRng(8))
        self.assertEqual(entity.sexual.climax_phase.level, "進行中")
        other = self._entity()
        apply_event(other, "stimulus_applied", rng=FixedRng(8))
        self.assertEqual(other.sexual.climax_phase.level, "未達")
        high = self._entity()
        high.sexual.pleasure.base = 85
        apply_event(high, "stimulus_applied", rng=FixedRng(8))
        self.assertEqual(high.sexual.climax_phase.level, "接近")

    def test_rule_climax_phase_ends_to_afterglow(self):
        entity = self._entity()
        entity.sexual.climax_phase.value = "進行中"
        apply_event(entity, "climax_ends", rng=FixedRng(-25))
        self.assertEqual(entity.sexual.climax_phase.level, "餘韻")

    def test_rule_climax_today_increment_on_climax(self):
        entity = self._entity()
        entity.sexual.record_climax()
        entity.sexual.record_climax()
        apply_event(entity, "climax_ends", rng=FixedRng(-25))
        self.assertEqual(entity.sexual.climax_today, 3)

    def test_rule_virginity_once(self):
        entity = self._entity()
        apply_event(entity, "first_vaginal_penetration")
        self.assertFalse(entity.sexual.virgin)

    def test_rule_experience_vaginal_added(self):
        entity = self._entity()
        apply_event(entity, "first_vaginal_penetration")
        self.assertIn("陰道性交", entity.sexual.experience_types)

    def test_rule_experience_masturbation_added(self):
        entity = self._entity()
        apply_event(entity, "masturbation_climax")
        self.assertIn("自慰", entity.sexual.experience_types)

    def test_rule_experience_lesbian_added(self):
        entity = self._entity()
        apply_event(entity, "penetrative_sex_with_female")
        self.assertIn("女女性愛", entity.sexual.experience_types)

    def test_rule_experience_titfuck_added(self):
        entity = self._entity()
        apply_event(entity, "breast_sex_performed")
        self.assertIn("乳交", entity.sexual.experience_types)

    def test_rule_experience_watched_added(self):
        entity = self._entity()
        apply_event(entity, "watched_during_activity")
        self.assertIn("被觀看", entity.sexual.experience_types)

    def test_rule_experience_exposure_added(self):
        entity = self._entity()
        apply_event(entity, "public_exposure")
        self.assertIn("露出", entity.sexual.experience_types)

    def test_rule_experience_interspecies_added(self):
        entity = self._entity()
        apply_event(entity, "sexual_activity_with_nonhuman")
        self.assertIn("異種性愛", entity.sexual.experience_types)

    def test_rule_shame_up_on_exposure_increase(self):
        entity = self._entity()
        apply_event(entity, "clothing_damaged_in_combat")
        self.assertEqual(entity.sexual.shame.value, 1)

    def test_rule_shame_up_on_public_sexual_activity(self):
        entity = self._entity()
        apply_event(entity, "public_sexual_activity")
        self.assertEqual(entity.sexual.shame.value, 1)

    def test_rule_shame_up_on_watched(self):
        entity = self._entity()
        apply_event(entity, "watched_during_activity")
        self.assertEqual(entity.sexual.shame.value, 1)

    def test_rule_exposure_up_on_clothing_damaged(self):
        entity = self._entity()
        apply_event(entity, "clothing_damaged_in_combat")
        self.assertEqual(entity.sexual.exposure.value, 1)

    def test_rule_sp_cost_on_climax(self):
        entity = self._entity()
        before = entity.traits.sp.value
        rng = FixedRng(-25)
        apply_event(entity, "climax_ends", rng=rng)
        self.assertEqual(entity.traits.sp.value, before - 25)
        entity.traits.sp.current = 10
        apply_event(entity, "climax_ends", rng=FixedRng(-25))
        self.assertEqual(entity.traits.sp.value, 0)

    def test_every_rule_id_has_a_test(self):
        expected = {f"test_rule_{rule_id}" for rule_id in RULES}
        actual = {
            name
            for name, _ in inspect.getmembers(type(self), inspect.isfunction)
            if name.startswith("test_rule_")
        }
        self.assertEqual(actual, expected)

    @covers_requirement("sexual-transition-rulebook::field-kinds-covers-exactly-the-fields-targeted-by-sexual-yaml-structurally-enforced")
    def test_field_kinds_covers_every_targetable_field(self):
        self.assertEqual(
            set(FIELD_KINDS),
            {rule.then["field"] for rule in RULES.values()},
        )

    def test_virginity_once_is_irreversible(self):
        entity = self._entity()
        apply_event(entity, "first_vaginal_penetration")
        self.assertFalse(entity.sexual.virgin)
        apply_event(entity, "first_vaginal_penetration")
        self.assertFalse(entity.sexual.virgin)
        entity.sexual.virgin = True
        self.assertFalse(entity.sexual.virgin)

    @covers_requirement("sexual-transition-rulebook::virgin-and-experience-types-rules-are-irreversible-and-append-only-end-to-end-through-apply-event")
    def test_experience_types_only_grows(self):
        entity = self._entity()
        apply_event(entity, "masturbation_climax")
        first = entity.sexual.experience_types
        apply_event(entity, "first_vaginal_penetration")
        second = entity.sexual.experience_types
        apply_event(entity, "masturbation_climax")
        third = entity.sexual.experience_types
        self.assertLess(first, second)
        self.assertEqual(second, third)
        self.assertEqual(third, frozenset({"自慰", "陰道性交"}))

    def test_climax_phase_rules_route_through_guard(self):
        source = inspect.getsource(sexual_transitions)
        self.assertNotIn(".climax_phase.value =", source)
        self.assertNotIn("._traits.climax_phase", source)
        self.assertIn("_apply_climax_phase_set(entity, then[\"set\"])", source)

    @covers_requirement("sexual-transition-rulebook::climax-today-increments-through-sexualstate-record-climax-never-through-sexualstate-s-private-handler")
    def test_climax_today_never_touches_private_traits(self):
        source = inspect.getsource(sexual_transitions)
        self.assertNotIn("entity.sexual._traits", source)

    def test_fixed_point_loop_terminates_on_a_synthetic_oscillation(self):
        rules = [
            Rule("start", {"event": "start"}, {"field": "pleasure", "delta": "+6"}),
            Rule(
                "a_up",
                {"field_changed": "arousal", "direction": "up"},
                {"field": "exposure", "delta": "+1"},
            ),
            Rule(
                "e_up",
                {"field_changed": "exposure", "direction": "up"},
                {"field": "pleasure", "delta": "-6"},
            ),
            Rule(
                "a_down",
                {"field_changed": "arousal", "direction": "down"},
                {"field": "exposure", "delta": "-1"},
            ),
            Rule(
                "e_down",
                {"field_changed": "exposure", "direction": "down"},
                {"field": "pleasure", "delta": "+6"},
            ),
        ]
        entity = self._entity()
        entity.sexual.pleasure.base = 10
        entity.sexual.exposure.value = 1
        with patch.object(sexual_transitions, "_RULES", rules):
            with self.assertRaises(RuleConvergenceError):
                apply_event(entity, "start", max_passes=7)

    def test_excluded_rules_and_fields_are_absent(self):
        serialized = repr([(rule.when, rule.then) for rule in RULES.values()])
        for excluded in (
            "race",
            "species",
            "elf",
            "身體感受",
            "興奮要素",
            "被注視感受",
            "最後性活動",
            "基本資訊.狀態",
            "lte",
            "actions_per_turn",
        ):
            self.assertNotIn(excluded, serialized)

    @covers_requirement("sexual-transition-rulebook::the-one-rule-targeting-a-vital-gauge-outside-sexualstate-writes-through-change-3-s-entity-traits-surface-never-through-sexualstate")
    def test_sp_cost_never_reaches_through_entity_sexual(self):
        source = inspect.getsource(_apply_then)
        branch = source.rsplit("    else:\n", 1)[1]
        self.assertIn("getattr(entity.traits, field)", branch)
        self.assertIn("trait.current +=", branch)
        self.assertNotIn("entity.sexual", branch)

    def test_delta_parser_rejects_malformed_and_descending_ranges(self):
        self.assertEqual(_parse_delta("+1"), 1)
        self.assertEqual(_parse_delta("-30..-20"), (-30, -20))
        for malformed in ("1", "+2..+1", "+1..-1", "-1..+1", "1..2", ""):
            with self.subTest(malformed=malformed):
                with self.assertRaises(ValueError):
                    _parse_delta(malformed)

    def test_pass_context_is_snapshotted_before_mutation(self):
        entity = self._entity()
        entity.sexual.pleasure.base = 71
        apply_event(entity, "stimulus_applied", rng=FixedRng(14))
        self.assertEqual(entity.sexual.arousal.level, "極限")
        self.assertEqual(entity.sexual.climax_phase.level, "接近")

    @covers_requirement("sexual-transition-rulebook::sexual-yaml-loads-through-change-6-s-shared-rule-loader-with-no-second-parser")
    def test_yaml_order_does_not_change_pass_matching(self):
        expected = self._entity()
        expected.sexual.pleasure.base = 71
        apply_event(expected, "stimulus_applied", rng=FixedRng(14))

        reversed_order = self._entity()
        reversed_order.sexual.pleasure.base = 71
        with patch.object(
            sexual_transitions,
            "_RULES",
            list(reversed(sexual_transitions._RULES)),
        ):
            apply_event(reversed_order, "stimulus_applied", rng=FixedRng(14))
        self.assertEqual(
            reversed_order.sexual.climax_phase.level,
            expected.sexual.climax_phase.level,
        )

    @covers_requirement("sexual-transition-rulebook::every-climax-phase-targeting-rule-routes-exclusively-through-change-7-s--apply-climax-phase-set")
    def test_climax_gate_does_not_apply_from_afterglow(self):
        entity = self._entity()
        entity.sexual.pleasure.base = 85
        entity.sexual.climax_phase.value = "餘韻"
        apply_event(entity, "unrelated_event")
        self.assertEqual(entity.sexual.climax_phase.level, "餘韻")

    @covers_requirement("sexual-transition-rulebook::apply-event-is-the-single-entry-point-evaluating-every-rule-to-a-fixed-point")
    def test_event_context_cannot_override_authoritative_state(self):
        entity = self._entity()
        with self.assertRaisesRegex(ValueError, "reserved keys"):
            apply_event(entity, "unrelated_event", arousal="極限")
        with self.assertRaisesRegex(ValueError, "reserved keys"):
            apply_event(
                entity,
                "unrelated_event",
                _changed={"exposure": "up"},
            )
        self.assertEqual(entity.sexual.climax_phase.level, "未達")
        self.assertEqual(entity.sexual.shame.level, "無")

    def test_max_passes_must_be_positive(self):
        with self.assertRaises(ValueError):
            apply_event(self._entity(), "unrelated_event", max_passes=0)

    def test_vital_gauge_effect_validation_rejects_invalid_shapes(self):
        invalid_effects = (
            {"field": "sp", "set": 10},
            {"field": "sp", "delta": "+1"},
            {"field": "sp", "delta": "-1..+1"},
        )
        for then in invalid_effects:
            with self.subTest(then=then):
                with self.assertRaises(ValueError):
                    _validate_rule_effect(Rule("invalid", {"event": "x"}, then))
