"""Tests for the sexual-act-effect helpers, handlers, and their balance data.

Covers the pure functions in ``world/rules/sexual_act_effects.py``
(``resolve_part``, ``participants``, ``compute_pleasure_gain``, the
``_COUNTER_MUTATORS`` table, and the ``sexual_act_effects.yaml`` loader), the
``pleasure:``/``sexual_counter:`` effect handlers registered in
``world/rules/action.py`` (including the wetness/climax-phase cascade
replication and climax-extension staging), and the end-to-end cast path
through ``ActionResolver`` with a test-local act installed via ``patch.dict``.
"""

from tools.spec_traceability import covers_requirement

import ast
import inspect
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import yaml

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from world.lore.sexual_vocab import GENERIC_BODY_PART
from world.quests.catalog import register_catalog
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    RejectReason,
    _EFFECT_HANDLERS,
    _apply_pleasure_gain,
    _handle_act_pair_event,
    _handle_actor_sexual_event,
    _handle_sexual_event,
    _handle_pleasure_effect,
    _handle_sexual_counter_effect,
)
from world.rules.sexual_act_effects import (
    _COUNTER_MUTATORS,
    _OBSERVER_GATED_COUNTERS,
    _OBSERVER_GATED_EVENTS,
    compute_pleasure_gain,
    load_effects_config,
    observers_present,
    pair_event_name,
    participants,
    resolve_part,
)
from world.rules.sexual_state import _LIFETIME_COUNTER_KEYS, SexualState
from world.rules.targeting import RoomActionContext
from world.skills.registry import SKILL_REGISTRY, TargetSpec
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY
from world.skills.sexual_acts._builder import (
    _ACTOR_SCOPED_EVENTS,
    SexualActDef,
    _act_family,
)


def _neutral_participant(part: str = "私處", sensitivity: str = "普通", shame: str = "無"):
    """Build a duck-typed participant at the multiplier floors for unit tests."""
    return SimpleNamespace(
        sexual=SimpleNamespace(
            sensitivity={part: SimpleNamespace(level=sensitivity)},
            shame=SimpleNamespace(level=shame),
        )
    )


def _effects_yaml(
    multipliers: dict[str, float] | None = None,
    threshold: int = 20,
) -> Path:
    """Write a temporary sexual_act_effects.yaml copy and return its path.

    The temporary directory is kept alive on a module list for the process
    lifetime so the returned path stays valid for the calling test.
    """
    directory = TemporaryDirectory()
    _TEMP_DIRECTORIES.append(directory)
    path = Path(directory.name) / "sexual_act_effects.yaml"
    payload = {
        "participant_multipliers": (
            {"1": 1.0, "2": 1.1, "3+": 1.2} if multipliers is None else multipliers
        ),
        "climax_extension_threshold": threshold,
    }
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path


_TEMP_DIRECTORIES: list[TemporaryDirectory] = []


class EffectsConfigTests(unittest.TestCase):
    """The sexual_act_effects.yaml contract (design D-3)."""

    @covers_requirement("sexual-act-effects::sexual-act-effects-yaml-declares-the-participant-count-table-and-the-climax-extension-threshold-validated-at-load")
    def test_shipped_table_loads_and_exposes_both_values(self):
        config = load_effects_config()
        self.assertEqual(config.participant_multipliers["1"], 1.0)
        self.assertEqual(config.participant_multipliers["2"], 1.1)
        self.assertEqual(config.participant_multipliers["3+"], 1.2)
        self.assertEqual(config.climax_extension_threshold, 20)

    @covers_requirement("sexual-act-effects::sexual-act-effects-yaml-declares-the-participant-count-table-and-the-climax-extension-threshold-validated-at-load")
    def test_missing_threshold_fails_closed_naming_the_field(self):
        path = _effects_yaml()
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        del payload["climax_extension_threshold"]
        path.write_text(yaml.safe_dump(payload), encoding="utf-8")
        with self.assertRaises(ValueError) as caught:
            load_effects_config(path)
        self.assertIn("climax_extension_threshold", str(caught.exception))

    @covers_requirement("sexual-act-effects::sexual-act-effects-yaml-declares-the-participant-count-table-and-the-climax-extension-threshold-validated-at-load")
    def test_non_ascending_multiplier_table_fails_closed(self):
        with self.assertRaises(ValueError) as caught:
            load_effects_config(
                _effects_yaml(multipliers={"1": 1.2, "2": 1.1, "3+": 1.2})
            )
        self.assertIn("participant_multipliers", str(caught.exception))

    def test_unknown_top_level_field_fails_closed(self):
        path = _effects_yaml()
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        payload["stray_field"] = True
        path.write_text(yaml.safe_dump(payload), encoding="utf-8")
        with self.assertRaises(ValueError) as caught:
            load_effects_config(path)
        self.assertIn("stray_field", str(caught.exception))

    def test_extra_multiplier_key_fails_closed(self):
        with self.assertRaises(ValueError):
            load_effects_config(
                _effects_yaml(multipliers={"1": 1.0, "2": 1.1, "3+": 1.2, "4+": 1.3})
            )

    def test_non_positive_threshold_fails_closed(self):
        for bad in (0, -1, 1.5):
            with self.subTest(threshold=bad):
                with self.assertRaises(ValueError):
                    load_effects_config(_effects_yaml(threshold=bad))

    def test_participant_multiplier_buckets_counts(self):
        config = load_effects_config()
        self.assertEqual(config.participant_multiplier(1), 1.0)
        self.assertEqual(config.participant_multiplier(2), 1.1)
        for count in (3, 4, 30):
            with self.subTest(count=count):
                self.assertEqual(config.participant_multiplier(count), 1.2)
        for bad in (0, -2, 1.5, True):
            with self.subTest(count=bad):
                with self.assertRaises(ValueError):
                    config.participant_multiplier(bad)


class ResolvePartTests(EvenniaTestCase):
    """resolve_part collapses None and Monster entities to the generic channel."""

    def setUp(self):
        super().setUp()
        self.humanoid = create_object(PlayerCharacter, key="resolve humanoid")
        self.humanoid.race = "human"
        self.humanoid.apply_race_baseline()
        self.monster = create_object(Monster, key="resolve monster")

    @covers_requirement("sexual-act-effects::resolve-part-collapses-a-monster-target-or-an-undeclared-part-to-the-generic-body-part-channel")
    def test_non_monster_with_declared_part_resolves_to_that_part(self):
        self.assertEqual(resolve_part(self.humanoid, "乳房"), "乳房")

    @covers_requirement("sexual-act-effects::resolve-part-collapses-a-monster-target-or-an-undeclared-part-to-the-generic-body-part-channel")
    def test_monster_resolves_to_the_generic_channel_regardless_of_declared_part(self):
        self.assertEqual(resolve_part(self.monster, "乳房"), GENERIC_BODY_PART)

    @covers_requirement("sexual-act-effects::resolve-part-collapses-a-monster-target-or-an-undeclared-part-to-the-generic-body-part-channel")
    def test_undeclared_part_resolves_to_the_generic_channel_for_any_entity(self):
        self.assertEqual(resolve_part(self.humanoid, None), GENERIC_BODY_PART)
        self.assertEqual(resolve_part(self.monster, None), GENERIC_BODY_PART)


class _EqualStub:
    """Distinct instances that compare equal, to pin identity-based dedup."""

    def __init__(self, value: int):
        self.value = value

    def __eq__(self, other):
        return isinstance(other, _EqualStub) and other.value == self.value

    def __hash__(self):
        return hash(self.value)


class ParticipantsTests(unittest.TestCase):
    """The actor-first, deduplicated participant list contract (design D-2)."""

    @covers_requirement("sexual-act-effects::participants-resolves-the-actor-first-deduplicated-participant-list-from-an-act-s-targets")
    def test_solo_act_targets_containing_only_the_actor(self):
        actor = object()
        self.assertEqual(participants(actor, [actor]), [actor])

    @covers_requirement("sexual-act-effects::participants-resolves-the-actor-first-deduplicated-participant-list-from-an-act-s-targets")
    def test_two_person_act_targets_excluding_the_actor(self):
        actor, other = object(), object()
        self.assertEqual(participants(actor, [other]), [actor, other])

    @covers_requirement("sexual-act-effects::participants-resolves-the-actor-first-deduplicated-participant-list-from-an-act-s-targets")
    def test_area_act_never_duplicates_the_actor(self):
        actor, ally, enemy = object(), object(), object()
        result = participants(actor, [actor, ally, enemy])
        self.assertEqual(result, [actor, ally, enemy])
        self.assertEqual(result.count(actor), 1)

    @covers_requirement("sexual-act-effects::participants-resolves-the-actor-first-deduplicated-participant-list-from-an-act-s-targets")
    def test_equal_but_distinct_targets_are_both_kept(self):
        actor = object()
        first, second = _EqualStub(1), _EqualStub(1)
        self.assertEqual(first, second)
        result = participants(actor, [first, second])
        self.assertEqual(result, [actor, first, second])


class ObserversPresentTests(EvenniaTestCase):
    """The deterministic, no-create presence read (design D-2)."""

    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="observer actor")

    @covers_requirement("sexual-act-effects::observers-present-returns-whether-any-entity-besides-the-actor-observes-a-cast")
    def test_area_cast_with_a_non_actor_target_is_observed_by_construction(self):
        self.assertTrue(observers_present(self.actor, [object()], {}))

    @covers_requirement("sexual-act-effects::observers-present-returns-whether-any-entity-besides-the-actor-observes-a-cast")
    def test_self_cast_alone_in_a_room_is_unobserved(self):
        room = SimpleNamespace(contents=[self.actor])
        self.assertFalse(observers_present(self.actor, [self.actor], {"room": room}))

    @covers_requirement("sexual-act-effects::observers-present-returns-whether-any-entity-besides-the-actor-observes-a-cast")
    def test_self_cast_with_a_co_located_living_entity_is_observed(self):
        occupant = create_object(PlayerCharacter, key="observer occupant")
        room = SimpleNamespace(contents=[self.actor, occupant])
        self.assertTrue(observers_present(self.actor, [self.actor], {"room": room}))

    @covers_requirement("sexual-act-effects::observers-present-returns-whether-any-entity-besides-the-actor-observes-a-cast")
    def test_self_cast_with_only_non_living_room_objects_is_unobserved(self):
        room = SimpleNamespace(contents=[self.actor, SimpleNamespace(key="exit")])
        self.assertFalse(observers_present(self.actor, [self.actor], {"room": room}))

    @covers_requirement("sexual-act-effects::observers-present-returns-whether-any-entity-besides-the-actor-observes-a-cast")
    def test_self_cast_on_a_battlefield_with_only_the_actor_is_unobserved(self):
        battlefield = SimpleNamespace(roster={"actor": self.actor})
        self.assertFalse(
            observers_present(self.actor, [self.actor], {"battlefield": battlefield})
        )

    @covers_requirement("sexual-act-effects::observers-present-returns-whether-any-entity-besides-the-actor-observes-a-cast")
    def test_self_cast_on_a_battlefield_with_another_member_is_observed(self):
        battlefield = SimpleNamespace(
            roster={"actor": self.actor, "enemy": object()}
        )
        self.assertTrue(
            observers_present(self.actor, [self.actor], {"battlefield": battlefield})
        )

    @covers_requirement("sexual-act-effects::observers-present-returns-whether-any-entity-besides-the-actor-observes-a-cast")
    def test_missing_context_reads_as_unobserved(self):
        self.assertFalse(observers_present(self.actor, [self.actor], {}))


class ObserverGatedNameTests(unittest.TestCase):
    """The observer-gated event/counter name tables (design D-3)."""

    @covers_requirement("sexual-act-effects::watched-during-activity-and-watched-count-are-observer-gated-the-gated-names-are-declared-as-module-constants")
    def test_gated_event_set_names_exactly_watched_during_activity(self):
        self.assertEqual(_OBSERVER_GATED_EVENTS, frozenset({"watched_during_activity"}))

    @covers_requirement("sexual-act-effects::watched-during-activity-and-watched-count-are-observer-gated-the-gated-names-are-declared-as-module-constants")
    def test_gated_counter_set_names_exactly_watched_count(self):
        self.assertEqual(_OBSERVER_GATED_COUNTERS, frozenset({"watched_count"}))

    @covers_requirement("sexual-act-effects::watched-during-activity-and-watched-count-are-observer-gated-the-gated-names-are-declared-as-module-constants")
    def test_gated_events_are_a_subset_of_the_actor_scoped_vocabulary(self):
        self.assertLessEqual(_OBSERVER_GATED_EVENTS, _ACTOR_SCOPED_EVENTS)

    @covers_requirement("sexual-act-effects::watched-during-activity-and-watched-count-are-observer-gated-the-gated-names-are-declared-as-module-constants")
    def test_gated_counters_are_a_subset_of_the_sanctioned_mutator_table(self):
        self.assertLessEqual(_OBSERVER_GATED_COUNTERS, set(_COUNTER_MUTATORS))

    @covers_requirement("sexual-act-effects::watched-during-activity-and-watched-count-are-observer-gated-the-gated-names-are-declared-as-module-constants")
    def test_no_act_declares_watched_count_as_a_participant_counter(self):
        # The gated counter is actor-scoped by definition (being watched is a
        # fact about the performing actor); a participant-side declaration
        # would bypass the gate, since a non-actor participant implies a
        # non-actor target, which always reads as observed.
        for key, act in SEXUAL_ACT_REGISTRY.items():
            with self.subTest(key=key):
                self.assertNotIn("watched_count", act.participant_counters)


class ComputePleasureGainTests(unittest.TestCase):
    """The base × ratio × sensitivity × shame × crowd formula (design D-3)."""

    @covers_requirement("sexual-act-effects::compute-pleasure-gain-scales-base-pleasure-by-ratio-sensitivity-shame-and-participant-count")
    def test_neutral_participant_receives_the_ratio_scaled_base(self):
        participant = _neutral_participant()
        self.assertEqual(
            compute_pleasure_gain(participant, "私處", 10, 1.0, 1),
            10,
        )

    @covers_requirement("sexual-act-effects::compute-pleasure-gain-scales-base-pleasure-by-ratio-sensitivity-shame-and-participant-count")
    def test_higher_sensitivity_increases_the_gain(self):
        neutral = _neutral_participant(sensitivity="普通")
        extreme = _neutral_participant(sensitivity="極高")
        low = compute_pleasure_gain(neutral, "私處", 10, 1.0, 1)
        high = compute_pleasure_gain(extreme, "私處", 10, 1.0, 1)
        self.assertGreater(high, low)
        self.assertEqual(high, 18)

    @covers_requirement("sexual-act-effects::compute-pleasure-gain-scales-base-pleasure-by-ratio-sensitivity-shame-and-participant-count")
    def test_zero_ratio_returns_zero_regardless_of_multipliers(self):
        participant = _neutral_participant(sensitivity="敏感異常", shame="強烈")
        self.assertEqual(
            compute_pleasure_gain(participant, "私處", 10, 0.0, 3),
            0,
        )

    def test_participant_count_ladder_scales_the_gain(self):
        participant = _neutral_participant()
        solo = compute_pleasure_gain(participant, "私處", 10, 1.0, 1)
        duo = compute_pleasure_gain(participant, "私處", 10, 1.0, 2)
        group = compute_pleasure_gain(participant, "私處", 10, 1.0, 4)
        self.assertEqual((solo, duo, group), (10, 11, 12))

    def test_shame_multiplier_scales_the_gain(self):
        floor = compute_pleasure_gain(
            _neutral_participant(shame="無"), "私處", 10, 1.0, 1
        )
        mid = compute_pleasure_gain(
            _neutral_participant(shame="中等"), "私處", 10, 1.0, 1
        )
        self.assertEqual(floor, 10)
        self.assertEqual(mid, 8)


class CounterMutatorTableTests(unittest.TestCase):
    """The explicit counter-name-to-mutator table (design D-6)."""

    @covers_requirement("sexual-act-effects::the-counter-to-mutator-table-is-explicit-and-structurally-verified-against-sexualstate")
    def test_climax_count_maps_to_record_climax_count_not_record_climax(self):
        self.assertEqual(_COUNTER_MUTATORS["climax_count"], "record_climax_count")
        self.assertIn("record_climax", dir(SexualState))
        self.assertIsNot(_COUNTER_MUTATORS["climax_count"], "record_climax")

    @covers_requirement("sexual-act-effects::the-counter-to-mutator-table-is-explicit-and-structurally-verified-against-sexualstate")
    def test_every_value_names_a_real_callable_sexualstate_method(self):
        for counter_name, mutator in _COUNTER_MUTATORS.items():
            with self.subTest(counter=counter_name, mutator=mutator):
                self.assertTrue(callable(getattr(SexualState, mutator)))

    @covers_requirement("sexual-act-effects::the-counter-to-mutator-table-is-explicit-and-structurally-verified-against-sexualstate")
    def test_table_keys_equal_the_lifetime_counter_names_exactly(self):
        self.assertEqual(set(_COUNTER_MUTATORS), set(_LIFETIME_COUNTER_KEYS))


class ApplyPleasureGainTests(EvenniaTestCase):
    """The wetness/climax-phase cascade replication (design D-5)."""

    def setUp(self):
        super().setUp()
        self.entity = create_object(PlayerCharacter, key="pleasure gain")
        self.entity.race = "human"
        self.entity.apply_race_baseline()

    @covers_requirement("sexual-act-effects::the-pleasure-handler-replicates-wetness-follows-arousal-and-the-climax-phase-progression-directly-preserving-the-two-step-未達-接近-進行中-semantic")
    def test_first_crossing_into_limit_moves_climax_phase_to_approaching_only(self):
        self.entity.sexual.pleasure.base = 84
        self.assertEqual(self.entity.sexual.climax_phase.level, "未達")
        _apply_pleasure_gain(self.entity, 1)
        self.assertEqual(self.entity.sexual.climax_phase.level, "接近")

    @covers_requirement("sexual-act-effects::the-pleasure-handler-replicates-wetness-follows-arousal-and-the-climax-phase-progression-directly-preserving-the-two-step-未達-接近-進行中-semantic")
    def test_further_gain_while_already_approaching_moves_to_in_progress(self):
        self.entity.sexual.pleasure.base = 100
        self.entity.sexual.climax_phase.value = "接近"
        _apply_pleasure_gain(self.entity, 1)
        self.assertEqual(self.entity.sexual.climax_phase.level, "進行中")

    @covers_requirement("sexual-act-effects::the-pleasure-handler-replicates-wetness-follows-arousal-and-the-climax-phase-progression-directly-preserving-the-two-step-未達-接近-進行中-semantic")
    def test_one_gain_application_never_advances_two_phases(self):
        self.entity.sexual.pleasure.base = 84
        _apply_pleasure_gain(self.entity, 30)
        self.assertEqual(self.entity.sexual.climax_phase.level, "接近")

    @covers_requirement("sexual-act-effects::the-pleasure-handler-replicates-wetness-follows-arousal-and-the-climax-phase-progression-directly-preserving-the-two-step-未達-接近-進行中-semantic")
    def test_arousal_band_crossing_raises_wetness_by_exactly_one(self):
        self.entity.sexual.pleasure.base = 10
        self.assertEqual(self.entity.sexual.wetness.value, 0)
        _apply_pleasure_gain(self.entity, 10)
        self.assertEqual(self.entity.sexual.wetness.value, 1)

    @covers_requirement("sexual-act-effects::the-pleasure-handler-replicates-wetness-follows-arousal-and-the-climax-phase-progression-directly-preserving-the-two-step-未達-接近-進行中-semantic")
    def test_same_band_gain_leaves_wetness_unchanged(self):
        self.entity.sexual.pleasure.base = 10
        _apply_pleasure_gain(self.entity, 4)
        self.assertEqual(self.entity.sexual.wetness.value, 0)

    @covers_requirement("sexual-act-effects::the-pleasure-handler-replicates-wetness-follows-arousal-and-the-climax-phase-progression-directly-preserving-the-two-step-未達-接近-進行中-semantic")
    def test_captures_are_the_first_two_statements_before_mutation(self):
        tree = ast.parse(inspect.getsource(_apply_pleasure_gain))
        function = tree.body[0]
        statements = [
            node
            for node in function.body
            if not (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant)
            )
        ]
        first, second = statements[:2]
        self.assertTrue(ast.unparse(first).startswith("pre_arousal_ordinal ="))
        self.assertTrue(ast.unparse(second).startswith("was_at_critical_point ="))


class ClimaxExtensionTests(EvenniaTestCase):
    """The extension trigger compares the pre-clamp gain, not the applied delta."""

    def setUp(self):
        super().setUp()
        self.entity = create_object(PlayerCharacter, key="extension entity")
        self.entity.race = "human"
        self.entity.apply_race_baseline()

    @covers_requirement("sexual-act-effects::the-pleasure-effect-handler-resolves-each-participant-s-part-and-ratio-by-role-applies-gain-and-stages-a-climax-extension-when-a-進行中-participant-s-computed-gain-meets-threshold")
    def test_qualifying_gain_on_in_progress_stages_an_extension(self):
        self.entity.sexual.climax_phase.value = "進行中"
        _apply_pleasure_gain(self.entity, 30)
        self.assertEqual(self.entity.sexual.pending_climax_extension, 1)

    @covers_requirement("sexual-act-effects::the-pleasure-effect-handler-resolves-each-participant-s-part-and-ratio-by-role-applies-gain-and-stages-a-climax-extension-when-a-進行中-participant-s-computed-gain-meets-threshold")
    def test_gain_that_clamps_at_the_ceiling_still_stages_an_extension(self):
        self.entity.sexual.pleasure.base = 95
        self.entity.sexual.climax_phase.value = "進行中"
        _apply_pleasure_gain(self.entity, 30)
        self.assertEqual(self.entity.sexual.pleasure.base, 100)
        self.assertEqual(self.entity.sexual.pending_climax_extension, 1)

    @covers_requirement("sexual-act-effects::the-pleasure-effect-handler-resolves-each-participant-s-part-and-ratio-by-role-applies-gain-and-stages-a-climax-extension-when-a-進行中-participant-s-computed-gain-meets-threshold")
    def test_gain_below_threshold_on_in_progress_does_not_stage(self):
        self.entity.sexual.climax_phase.value = "進行中"
        _apply_pleasure_gain(self.entity, 10)
        self.assertEqual(self.entity.sexual.pending_climax_extension, 0)

    @covers_requirement("sexual-act-effects::the-pleasure-effect-handler-resolves-each-participant-s-part-and-ratio-by-role-applies-gain-and-stages-a-climax-extension-when-a-進行中-participant-s-computed-gain-meets-threshold")
    def test_gain_on_non_in_progress_never_stages_an_extension(self):
        for phase in ("未達", "接近", "餘韻"):
            with self.subTest(phase=phase):
                self.entity.sexual.climax_phase.value = phase
                _apply_pleasure_gain(self.entity, 30)
                self.assertEqual(self.entity.sexual.pending_climax_extension, 0)


class _ActCastTestCase(EvenniaTest):
    """Shared fixture: an actor and one target in a room, plus test-local acts."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.actor = create_object(
            PlayerCharacter, key="act-actor", location=self.room1
        )
        self.actor.race = "human"
        self.actor.apply_race_baseline()
        self.actor.db.skills = {"active": [], "passive": []}
        self.target = create_object(
            PlayerCharacter, key="act-target", location=self.room1
        )
        self.target.race = "human"
        self.target.apply_race_baseline()

    def _install(self, skill, act):
        return (
            patch.dict(SEXUAL_ACT_REGISTRY, {act.key: act}),
            patch.dict(SKILL_REGISTRY, {skill.key: skill}),
        )

    def _cast(self, act_key, targets, event_context=None):
        # Every test-local duo act in this module is resistible=True (the
        # _build_duo_act default), so a real dice roll would make the cast
        # outcome flaky; force a compliant roll (both fixtures are floor
        # humans with equal contest scores, so roll=1 always complies).
        with patch("world.rules.action.roll_d100", return_value=1):
            return ActionResolver.resolve(
                ActionRequest(
                    self.actor,
                    act_key,
                    targets,
                    RoomActionContext(self.room1, event_context),
                )
            )

    def _build_duo_act(
        self,
        key: str = "test_duo",
        *,
        base_pleasure: int = 20,
        actor_part: str | None = "腰腹",
        target_part: str | None = "私處",
        actor_pleasure_ratio: float = 0.5,
        actor_counters: tuple[str, ...] = ("duo_act_count",),
        participant_counters: tuple[str, ...] = ("duo_act_count",),
        sexual_events: tuple[str, ...] = (),
    ):
        (skill, act), = _act_family(
            "關係",
            (
                key,
                "測試雙人行為",
                "僅存在於測試中的合成雙人行為。",
                TargetSpec.SINGLE,
                {},
                base_pleasure,
                actor_part,
                target_part,
                actor_pleasure_ratio,
                actor_counters,
                participant_counters,
                sexual_events,
                True,
            ),
        )
        return skill, act

    def _build_pair_act(
        self,
        key: str = "test_pair_act",
        *,
        pair_events: tuple[tuple[tuple[str, str], str], ...] | None = None,
    ):
        (skill, act), = _act_family(
            "關係",
            (
                key,
                "測試交合行為",
                "僅存在於測試中的合成交合行為。",
                TargetSpec.SINGLE,
                {},
                20,
                "私處",
                "私處",
                0.6,
                ("duo_act_count",),
                ("duo_act_count",),
                (),
                True,
                (
                    pair_events
                    if pair_events is not None
                    else (
                        (("female", "male"), "first_vaginal_penetration"),
                        (("female", "female"), "penetrative_sex_with_female"),
                        (("male", "male"), "penetrative_sex_with_male"),
                    )
                ),
            ),
        )
        return skill, act


class PleasureHandlerIntegrationTests(_ActCastTestCase):
    """The pleasure:<act_key> handler through the full cast pipeline."""

    @covers_requirement("sexual-act-effects::the-pleasure-effect-handler-resolves-each-participant-s-part-and-ratio-by-role-applies-gain-and-stages-a-climax-extension-when-a-進行中-participant-s-computed-gain-meets-threshold")
    def test_every_participant_gains_their_own_computed_pleasure(self):
        skill, act = self._build_duo_act(base_pleasure=20)
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(act.key, [self.target])
            self.assertEqual(result.outcome, "success")
            self.assertEqual(self.actor.sexual.pleasure.base, 11)
            self.assertEqual(self.target.sexual.pleasure.base, 22)

    @covers_requirement("sexual-act-effects::the-pleasure-effect-handler-resolves-each-participant-s-part-and-ratio-by-role-applies-gain-and-stages-a-climax-extension-when-a-進行中-participant-s-computed-gain-meets-threshold")
    def test_actor_uses_actor_part_and_target_uses_target_part(self):
        skill, act = self._build_duo_act(actor_part="腰腹", target_part="私處")
        self.actor.sexual.sensitivity["腰腹"] = "高"
        self.target.sexual.sensitivity["私處"] = "普通"
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(act.key, [self.target])
            self.assertEqual(result.outcome, "success")
            self.assertEqual(self.actor.sexual.pleasure.base, 15)
            self.assertEqual(self.target.sexual.pleasure.base, 22)

    @covers_requirement("sexual-act-effects::the-pleasure-effect-handler-resolves-each-participant-s-part-and-ratio-by-role-applies-gain-and-stages-a-climax-extension-when-a-進行中-participant-s-computed-gain-meets-threshold")
    def test_qualifying_gain_on_in_progress_target_stages_an_extension(self):
        skill, act = self._build_duo_act(base_pleasure=30)
        self.target.sexual.pleasure.base = 95
        self.target.sexual.climax_phase.value = "進行中"
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(act.key, [self.target])
            self.assertEqual(result.outcome, "success")
            self.assertEqual(self.target.sexual.pleasure.base, 100)
            self.assertEqual(self.target.sexual.pending_climax_extension, 1)

    def test_cast_stages_one_pending_effect_per_participant(self):
        skill, act = self._build_duo_act()
        with self._install(skill, act)[0]:
            pending = _handle_pleasure_effect(
                self.actor, [self.target], f"pleasure:{act.key}", {}, 1.0
            )
        self.assertEqual(len(pending), 2)
        self.assertIn(self.actor, [effect.entity for effect in pending])
        self.assertIn(self.target, [effect.entity for effect in pending])


class SexualCounterHandlerTests(_ActCastTestCase):
    """The sexual_counter:<act_key> role split (design D-7)."""

    @covers_requirement("sexual-act-effects::the-counter-effect-handler-increments-actor-counters-on-the-actor-and-participant-counters-on-every-other-participant")
    def test_actor_only_counter_increments_once_on_the_actor_only(self):
        skill, act = self._build_duo_act(
            actor_counters=("restraint_count",),
            participant_counters=(),
        )
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(act.key, [self.target])
            self.assertEqual(result.outcome, "success")
            self.assertEqual(self.actor.sexual.restraint_count, 1)
            self.assertEqual(self.target.sexual.restraint_count, 0)

    @covers_requirement("sexual-act-effects::the-counter-effect-handler-increments-actor-counters-on-the-actor-and-participant-counters-on-every-other-participant")
    def test_symmetric_counter_increments_on_both_sides(self):
        skill, act = self._build_duo_act()
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(act.key, [self.target])
            self.assertEqual(result.outcome, "success")
            self.assertEqual(self.actor.sexual.duo_act_count, 1)
            self.assertEqual(self.target.sexual.duo_act_count, 1)

    @covers_requirement("sexual-act-effects::the-counter-effect-handler-increments-actor-counters-on-the-actor-and-participant-counters-on-every-other-participant")
    def test_area_act_applies_participant_counters_to_every_other_participant(self):
        allies = []
        for index in range(3):
            ally = create_object(
                PlayerCharacter,
                key=f"act-ally-{index}",
                location=self.room1,
            )
            ally.race = "human"
            ally.apply_race_baseline()
            allies.append(ally)
        (skill, act), = _act_family(
            "關係",
            (
                "test_area_act",
                "測試群體行為",
                "僅存在於測試中的合成群體行為。",
                TargetSpec.AREA,
                {},
                10,
                "腰腹",
                "私處",
                0.5,
                (),
                ("group_act_count",),
                (),
                True,
            ),
        )
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(act.key, allies)
            self.assertEqual(result.outcome, "success")
            for ally in allies:
                self.assertEqual(ally.sexual.group_act_count, 1)
            self.assertEqual(self.actor.sexual.group_act_count, 0)

    def test_unknown_counter_name_rejects_the_action(self):
        skill, act = self._build_duo_act(
            actor_counters=("not_a_counter",),
            participant_counters=(),
        )
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(act.key, [self.target])
            self.assertEqual(result.outcome, "rejected")

    def test_rejected_cast_leaves_no_state_or_sensitivity_trait_behind(self):
        skill, act = self._build_duo_act(
            actor_counters=("not_a_counter",),
            participant_counters=(),
        )
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(act.key, [self.target])
            self.assertEqual(result.outcome, "rejected")
        for entity in (self.actor, self.target):
            self.assertEqual(entity.sexual.pleasure.base, 0)
            self.assertEqual(entity.sexual.duo_act_count, 0)
            self.assertEqual(
                list(entity.sexual.sensitivity.items()),
                [],
                "a rejected cast must not leave a lazily-created sensitivity trait",
            )


class MissingActRejectionTests(_ActCastTestCase):
    """Both handlers reject an act key absent from the registry (defensive)."""

    def test_pleasure_handler_rejects_an_absent_act_key(self):
        with self.assertRaises(Exception) as caught:
            _handle_pleasure_effect(
                self.actor, [self.target], "pleasure:never_registered", {}, 1.0
            )
        self.assertEqual(
            caught.exception.detail,
            "pleasure:never_registered names an act absent from SEXUAL_ACT_REGISTRY",
        )

    def test_counter_handler_rejects_an_absent_act_key(self):
        with self.assertRaises(Exception) as caught:
            _handle_sexual_counter_effect(
                self.actor, [self.target], "sexual_counter:never_registered", {}, 1.0
            )
        self.assertEqual(
            caught.exception.detail,
            "sexual_counter:never_registered names an act absent from SEXUAL_ACT_REGISTRY",
        )


class SexualEventReuseTests(_ActCastTestCase):
    """sexual_event:<name> entries reuse the existing handler; recipients follow D-3."""

    @covers_requirement("sexual-act-effects::sexual-event-name-entries-in-an-act-s-effects-reuse-the-existing-handler-and-dispatch-table-unchanged")
    def test_declared_event_calls_apply_event_for_every_participant(self):
        skill, act = self._build_duo_act(sexual_events=("frequent_stimulation",))
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(
                act.key,
                [self.target],
                {"sexual": {"part": "私處"}},
            )
            self.assertEqual(result.outcome, "success")
            self.assertEqual(self.target.sexual.sensitivity["私處"].level, "高")
            self.assertEqual(self.actor.sexual.sensitivity["私處"].level, "高")

    @covers_requirement("sexual-act-effects::sexual-event-name-entries-in-an-act-s-effects-reuse-the-existing-handler-and-dispatch-table-unchanged")
    def test_no_new_handler_is_registered_for_sexual_event(self):
        self.assertIs(_EFFECT_HANDLERS["sexual_event"], _handle_sexual_event)

    @covers_requirement("sexual-act-effects::sexual-event-name-entries-in-an-act-s-effects-reuse-the-existing-handler-and-dispatch-table-unchanged")
    def test_legacy_stimulus_event_stays_target_scoped(self):
        # D-9: _LEGACY_TARGET_SCOPED_EVENTS keeps the divine skill's declared
        # event on the cast's targets only — the acting entity is never a
        # recipient, so the divine-arts exemption from self-pleasure holds.
        pending = _handle_sexual_event(
            self.actor,
            [self.target],
            "sexual_event:stimulus_applied",
            {},
            1.0,
        )
        self.assertEqual(len(pending), 1)
        self.assertIs(pending[0].entity, self.target)

    @covers_requirement("sexual-act-effects::sexual-event-name-entries-in-an-act-s-effects-reuse-the-existing-handler-and-dispatch-table-unchanged")
    def test_self_act_event_reaches_the_actor_exactly_once(self):
        (skill, act), = _act_family(
            "獨處線",
            (
                "test_event_solo",
                "測試事件自慰",
                "僅存在於測試中的合成事件自慰行為。",
                TargetSpec.SELF,
                {},
                10,
                "私處",
                None,
                1.0,
                ("masturbation_count",),
                (),
                ("masturbation_climax",),
                True,
            ),
        )
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(act.key, [])
        self.assertEqual(result.outcome, "success")
        self.assertIn("自慰", self.actor.sexual.experience_types)


class ActorSexualEventHandlerTests(_ActCastTestCase):
    """The sexual_event_actor:<name> handler and its observer gating."""

    def _build_self_act(
        self,
        key: str = "test_actor_event",
        *,
        actor_counters: tuple[str, ...] = ("exposure_act_count",),
        sexual_events: tuple[str, ...] = ("self_exposure",),
    ):
        (skill, act), = _act_family(
            "羞恥",
            (
                key,
                "測試演出行為",
                "僅存在於測試中的合成自我演出行為。",
                TargetSpec.SELF,
                {},
                10,
                None,
                None,
                1.0,
                actor_counters,
                (),
                sexual_events,
                False,
            ),
        )
        return skill, act

    def _cast_self_in(self, act_key: str, room):
        return ActionResolver.resolve(
            ActionRequest(
                self.actor,
                act_key,
                [],
                RoomActionContext(room, {}),
            )
        )

    @covers_requirement("sexual-act-effects::sexual-event-actor-name-applies-the-named-event-to-the-actor-only")
    def test_actor_scoped_event_reaches_the_actor_and_never_a_target(self):
        skill, act = self._build_duo_act(sexual_events=("self_exposure",))
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(act.key, [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.sexual.exposure.value, 1)
        self.assertEqual(self.target.sexual.exposure.value, 0)

    @covers_requirement("sexual-act-effects::sexual-event-actor-name-applies-the-named-event-to-the-actor-only")
    def test_area_self_exposure_lands_on_the_performer_not_the_audience(self):
        (skill, act), = _act_family(
            "羞恥",
            (
                "test_area_self_exposure",
                "測試群體演出",
                "僅存在於測試中的合成群體演出行為。",
                TargetSpec.AREA,
                {},
                10,
                None,
                "腰腹",
                0.5,
                (),
                (),
                ("self_exposure",),
                True,
            ),
        )
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(act.key, [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.sexual.exposure.value, 1)
        self.assertEqual(self.target.sexual.exposure.value, 0)

    @covers_requirement("sexual-act-effects::watched-during-activity-and-watched-count-are-observer-gated-the-gated-names-are-declared-as-module-constants")
    def test_unobserved_cast_skips_the_watched_event_but_stages_the_others(self):
        alone = create_object(Room, key="actor event alone room")
        self.actor.location = alone
        skill, act = self._build_self_act(
            actor_counters=("watched_count", "exposure_act_count"),
            sexual_events=("self_exposure", "watched_during_activity"),
        )
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast_self_in(act.key, alone)
        self.assertEqual(result.outcome, "success")
        self.assertNotIn("被觀看", self.actor.sexual.experience_types)
        self.assertEqual(self.actor.sexual.watched_count, 0)
        self.assertEqual(self.actor.sexual.exposure.value, 1)
        self.assertEqual(self.actor.sexual.exposure_act_count, 1)

    @covers_requirement("sexual-act-effects::watched-during-activity-and-watched-count-are-observer-gated-the-gated-names-are-declared-as-module-constants")
    def test_observed_cast_fires_the_watched_event(self):
        skill, act = self._build_self_act(
            actor_counters=("watched_count",),
            sexual_events=("watched_during_activity",),
        )
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast_self_in(act.key, self.room1)
        self.assertEqual(result.outcome, "success")
        self.assertIn("被觀看", self.actor.sexual.experience_types)
        self.assertEqual(self.actor.sexual.watched_count, 1)

    @covers_requirement("sexual-act-effects::watched-during-activity-and-watched-count-are-observer-gated-the-gated-names-are-declared-as-module-constants")
    def test_unobserved_cast_skips_the_watched_counter_while_staging_others(self):
        alone = create_object(Room, key="counter alone room")
        self.actor.location = alone
        skill, act = self._build_self_act(
            actor_counters=("watched_count", "exposure_act_count"),
            sexual_events=(),
        )
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast_self_in(act.key, alone)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.sexual.watched_count, 0)
        self.assertEqual(self.actor.sexual.exposure_act_count, 1)


_CANONICAL_PAIR_EVENTS = (
    (("female", "male"), "first_vaginal_penetration"),
    (("female", "female"), "penetrative_sex_with_female"),
    (("male", "male"), "penetrative_sex_with_male"),
)


def _pair_act():
    """One test-local SexualActDef carrying the canonical three-pair table."""
    return SexualActDef(
        key="pair_test",
        unlock={},
        base_pleasure=10,
        actor_part="私處",
        target_part="私處",
        actor_pleasure_ratio=0.6,
        actor_counters=(),
        participant_counters=(),
        sexual_events=(),
        resistible=True,
        pair_events=_CANONICAL_PAIR_EVENTS,
    )


class PairEventNameTests(unittest.TestCase):
    """The pair_event_name selector implements the full D-12 table."""

    @covers_requirement("sexual-act-effects::the-pair-event-handler-resolves-one-sex-conditional-event-per-cast-and-applies-it-to-every-participant")
    def test_opposite_sex_pair_resolves_first_vaginal_penetration(self):
        act = _pair_act()
        actor = SimpleNamespace(sex="female")
        target = SimpleNamespace(sex="male")
        self.assertEqual(
            pair_event_name(actor, [target], act),
            "first_vaginal_penetration",
        )

    @covers_requirement("sexual-act-effects::the-pair-event-handler-resolves-one-sex-conditional-event-per-cast-and-applies-it-to-every-participant")
    def test_both_female_pair_resolves_the_lesbian_event(self):
        act = _pair_act()
        actor = SimpleNamespace(sex="female")
        target = SimpleNamespace(sex="female")
        self.assertEqual(
            pair_event_name(actor, [target], act),
            "penetrative_sex_with_female",
        )

    @covers_requirement("sexual-act-effects::the-pair-event-handler-resolves-one-sex-conditional-event-per-cast-and-applies-it-to-every-participant")
    def test_both_male_pair_resolves_the_gay_event(self):
        act = _pair_act()
        actor = SimpleNamespace(sex="male")
        target = SimpleNamespace(sex="male")
        self.assertEqual(
            pair_event_name(actor, [target], act),
            "penetrative_sex_with_male",
        )

    @covers_requirement("sexual-act-effects::the-pair-event-handler-resolves-one-sex-conditional-event-per-cast-and-applies-it-to-every-participant")
    def test_other_or_unknown_party_resolves_no_event(self):
        act = _pair_act()
        self.assertIsNone(
            pair_event_name(
                SimpleNamespace(sex="male"),
                [SimpleNamespace(sex="other")],
                act,
            )
        )
        self.assertIsNone(
            pair_event_name(
                SimpleNamespace(),
                [SimpleNamespace()],
                act,
            )
        )
        self.assertIsNone(
            pair_event_name(
                SimpleNamespace(sex="female"),
                [SimpleNamespace(sex="unknown")],
                act,
            )
        )

    @covers_requirement("sexual-act-effects::the-pair-event-handler-resolves-one-sex-conditional-event-per-cast-and-applies-it-to-every-participant")
    def test_pair_not_in_the_table_resolves_no_event(self):
        act = _pair_act()
        self.assertIsNone(
            pair_event_name(
                SimpleNamespace(sex="female"),
                [SimpleNamespace(sex="other")],
                act,
            )
        )

    @covers_requirement("sexual-act-effects::the-pair-event-handler-resolves-one-sex-conditional-event-per-cast-and-applies-it-to-every-participant")
    def test_single_participant_surviving_cast_resolves_no_event(self):
        act = _pair_act()
        self.assertIsNone(
            pair_event_name(SimpleNamespace(sex="female"), [], act)
        )

    @covers_requirement("sexual-act-effects::the-pair-event-handler-resolves-one-sex-conditional-event-per-cast-and-applies-it-to-every-participant")
    def test_none_sex_value_reads_as_the_unknown_default(self):
        act = _pair_act()
        self.assertIsNone(
            pair_event_name(
                SimpleNamespace(sex=None),
                [SimpleNamespace(sex="male")],
                act,
            )
        )

    @covers_requirement("sexual-act-effects::the-pair-event-handler-resolves-one-sex-conditional-event-per-cast-and-applies-it-to-every-participant")
    def test_corrupted_non_string_sex_value_reads_as_the_unknown_default(self):
        # A corrupted non-SEX_VALUES attribute can never crash the pair sort:
        # it normalizes to the unknown default, which matches no pair.
        act = _pair_act()
        self.assertIsNone(
            pair_event_name(
                SimpleNamespace(sex=123),
                [SimpleNamespace(sex="male")],
                act,
            )
        )


class MonsterPairEventTests(EvenniaTestCase):
    """A Monster target reads sex as the default, resolving no pair event."""

    def setUp(self):
        super().setUp()
        self.monster = create_object(Monster, key="pair monster")

    @covers_requirement("sexual-act-effects::the-pair-event-handler-resolves-one-sex-conditional-event-per-cast-and-applies-it-to-every-participant")
    def test_monster_target_resolves_no_event(self):
        act = _pair_act()
        actor = SimpleNamespace(sex="female")
        self.assertIsNone(pair_event_name(actor, [self.monster], act))
        self.assertEqual(self.monster.sex, "other")


class ActPairEventHandlerTests(_ActCastTestCase):
    """The act_pair_event:<key> handler through the full cast pipeline."""

    @covers_requirement("sexual-act-effects::the-pair-event-handler-resolves-one-sex-conditional-event-per-cast-and-applies-it-to-every-participant")
    def test_opposite_sex_cast_applies_the_event_to_every_participant(self):
        skill, act = self._build_pair_act()
        self.actor.sex = "female"
        self.target.sex = "male"
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(act.key, [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertFalse(self.actor.sexual.virgin)
        self.assertFalse(self.target.sexual.virgin)
        self.assertIn("陰道性交", self.actor.sexual.experience_types)
        self.assertIn("陰道性交", self.target.sexual.experience_types)

    @covers_requirement("sexual-act-effects::the-pair-event-handler-resolves-one-sex-conditional-event-per-cast-and-applies-it-to-every-participant")
    def test_other_unknown_party_stages_no_effect(self):
        skill, act = self._build_pair_act()
        self.actor.sex = "male"
        self.target.sex = "other"
        with self._install(skill, act)[0]:
            pending = _handle_act_pair_event(
                self.actor,
                [self.target],
                f"act_pair_event:{act.key}",
                {},
                1.0,
            )
        self.assertEqual(pending, [])

    @covers_requirement("sexual-act-effects::the-pair-event-handler-resolves-one-sex-conditional-event-per-cast-and-applies-it-to-every-participant")
    def test_absent_act_rejects_with_effect_resolution_failed(self):
        with self.assertRaises(Exception) as caught:
            _handle_act_pair_event(
                self.actor,
                [self.target],
                "act_pair_event:never_registered",
                {},
                1.0,
            )
        self.assertEqual(caught.exception.reason, RejectReason.EFFECT_RESOLUTION_FAILED)
        self.assertIn(
            "act_pair_event:never_registered",
            str(caught.exception.detail),
        )


class SoloActCastTests(_ActCastTestCase):
    """A SELF-target solo act casts and gains pleasure through the pipeline."""

    def test_solo_act_casts_and_applies_pleasure_to_the_actor(self):
        (skill, act), = _act_family(
            "獨處線",
            (
                "test_solo_act",
                "測試自慰行為",
                "僅存在於測試中的合成自慰行為。",
                TargetSpec.SELF,
                {},
                10,
                "私處",
                None,
                1.0,
                ("masturbation_count",),
                (),
                (),
                True,
            ),
        )
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(act.key, [])
            self.assertEqual(result.outcome, "success")
            self.assertEqual(self.actor.sexual.pleasure.base, 10)
            self.assertEqual(self.actor.sexual.masturbation_count, 1)


if __name__ == "__main__":
    unittest.main()
