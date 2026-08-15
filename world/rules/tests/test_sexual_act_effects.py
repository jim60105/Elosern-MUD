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
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from world.lore.sexual_vocab import GENERIC_BODY_PART
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    _EFFECT_HANDLERS,
    _apply_pleasure_gain,
    _handle_sexual_event,
    _handle_pleasure_effect,
    _handle_sexual_counter_effect,
)
from world.rules.sexual_act_effects import (
    _COUNTER_MUTATORS,
    compute_pleasure_gain,
    load_effects_config,
    participants,
    resolve_part,
)
from world.rules.sexual_state import _LIFETIME_COUNTER_KEYS, SexualState
from world.rules.targeting import RoomActionContext
from world.skills.registry import SKILL_REGISTRY, TargetSpec
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY
from world.skills.sexual_acts._builder import _act_family


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


class ResolvePartTests(EvenniaTest):
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


class ApplyPleasureGainTests(EvenniaTest):
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


class ClimaxExtensionTests(EvenniaTest):
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
    """sexual_event:<name> entries reuse the existing handler unchanged (D-8)."""

    @covers_requirement("sexual-act-effects::sexual-event-name-entries-in-an-act-s-effects-reuse-the-existing-handler-and-dispatch-table-unchanged")
    def test_declared_event_calls_apply_event_with_the_resolved_part(self):
        skill, act = self._build_duo_act(sexual_events=("frequent_stimulation",))
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(
                act.key,
                [self.target],
                {"sexual": {"part": "私處"}},
            )
            self.assertEqual(result.outcome, "success")
            self.assertEqual(self.target.sexual.sensitivity["私處"].level, "高")

    @covers_requirement("sexual-act-effects::sexual-event-name-entries-in-an-act-s-effects-reuse-the-existing-handler-and-dispatch-table-unchanged")
    def test_no_new_handler_is_registered_for_sexual_event(self):
        self.assertIs(_EFFECT_HANDLERS["sexual_event"], _handle_sexual_event)


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
