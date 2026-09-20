"""Slice of ``test_sexual_act_effects``: ComputePleasureGainTests, CounterMutatorTableTests, ApplyPleasureGainTests, SharedPleasureModuleTests, ClimaxExtensionTests.
"""
from tools.spec_traceability import covers_requirement
import ast
import inspect
from dataclasses import replace
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
    _EFFECT_HANDLER_SURFACES,
    _handle_act_pair_event,
    _handle_actor_sexual_event,
    _handle_sexual_event,
    _handle_pleasure_effect,
    _handle_sexual_counter_effect,
    _handle_target_sexual_event,
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
from world.rules.pleasure import apply_pleasure_gain
from world.rules.sexual_state import _LIFETIME_COUNTER_KEYS, SexualState
from world.rules.sexual_resist import ResistVerdict
from world.rules.targeting import RoomActionContext
from world.skills.registry import TargetSpec
from world.skills.sexual_acts._builder import (
    _ACTOR_SCOPED_EVENTS,
    SexualActDef,
    _act_family,
)
from .._combat_session_helpers import _live_registry, _race_key
# The YAML field vocabulary of the effects config, resolved through the
# config dataclass at import (the loader owns the names; this module never
# spells a shipped field name as a literal).
import dataclasses as _dc


from ._support import (
    _neutral_participant,
)


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
        self.entity.race = _race_key()
        self.entity.apply_race_baseline()

    @covers_requirement("sexual-act-effects::one-shared-pleasure-entry-point-replicates-wetness-follows-arousal-and-the-climax-phase-progression-directly-preserving-the-two-step-未達-接近-進行中-semantic")
    def test_first_crossing_into_limit_moves_climax_phase_to_approaching_only(self):
        self.entity.sexual.pleasure.base = 84
        self.assertEqual(self.entity.sexual.climax_phase.level, "未達")
        apply_pleasure_gain(self.entity, 1)
        self.assertEqual(self.entity.sexual.climax_phase.level, "接近")

    @covers_requirement("sexual-act-effects::one-shared-pleasure-entry-point-replicates-wetness-follows-arousal-and-the-climax-phase-progression-directly-preserving-the-two-step-未達-接近-進行中-semantic")
    def test_further_gain_while_already_approaching_moves_to_in_progress(self):
        self.entity.sexual.pleasure.base = 100
        self.entity.sexual.climax_phase.value = "接近"
        apply_pleasure_gain(self.entity, 1)
        self.assertEqual(self.entity.sexual.climax_phase.level, "進行中")

    @covers_requirement("sexual-act-effects::one-shared-pleasure-entry-point-replicates-wetness-follows-arousal-and-the-climax-phase-progression-directly-preserving-the-two-step-未達-接近-進行中-semantic")
    def test_one_gain_application_never_advances_two_phases(self):
        self.entity.sexual.pleasure.base = 84
        apply_pleasure_gain(self.entity, 30)
        self.assertEqual(self.entity.sexual.climax_phase.level, "接近")

    @covers_requirement("sexual-act-effects::one-shared-pleasure-entry-point-replicates-wetness-follows-arousal-and-the-climax-phase-progression-directly-preserving-the-two-step-未達-接近-進行中-semantic")
    def test_arousal_band_crossing_raises_wetness_by_exactly_one(self):
        self.entity.sexual.pleasure.base = 10
        self.assertEqual(self.entity.sexual.wetness.value, 0)
        apply_pleasure_gain(self.entity, 10)
        self.assertEqual(self.entity.sexual.wetness.value, 1)

    @covers_requirement("sexual-act-effects::one-shared-pleasure-entry-point-replicates-wetness-follows-arousal-and-the-climax-phase-progression-directly-preserving-the-two-step-未達-接近-進行中-semantic")
    def test_same_band_gain_leaves_wetness_unchanged(self):
        self.entity.sexual.pleasure.base = 10
        apply_pleasure_gain(self.entity, 4)
        self.assertEqual(self.entity.sexual.wetness.value, 0)

    @covers_requirement("sexual-act-effects::one-shared-pleasure-entry-point-replicates-wetness-follows-arousal-and-the-climax-phase-progression-directly-preserving-the-two-step-未達-接近-進行中-semantic")
    def test_captures_are_the_first_two_statements_before_mutation(self):
        tree = ast.parse(inspect.getsource(apply_pleasure_gain))
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


class SharedPleasureModuleTests(unittest.TestCase):
    """The shared pleasure module's invariants (item-effect-model design §5.6)."""

    _ROOT = Path(__file__).resolve().parents[3]
    _PRODUCTION_DIRS = ("commands", "server", "tests", "tools", "typeclasses", "web", "world")
    # The closed sanctioned writer set (delta ADDED requirement): the shared
    # module's two functions plus the rulebook engine and clock-decay branches
    # design D6 keeps outside the appliers.
    _SANCTIONED = {
        ("world/rules/pleasure.py", "apply_pleasure_gain"),
        ("world/rules/pleasure.py", "zero_pleasure"),
        ("world/rules/sexual_transitions.py", "_apply_then"),
        ("world/rules/sexual_state/lifecycle.py", "decay_tick"),
    }

    @staticmethod
    def _production_sources(root):
        for directory in SharedPleasureModuleTests._PRODUCTION_DIRS:
            base = root / directory
            for path in sorted(base.rglob("*.py")):
                if "tests" in path.relative_to(root).parts or "__pycache__" in path.parts:
                    continue
                yield path

    def _pleasure_writes(self, tree):
        """Yield (function name, assignment) for trait writes onto pleasure.

        Covers direct ``...pleasure.base/.value`` assignments, assignments to a
        local bound to ``entity.sexual.pleasure``, and ``getattr(entity.sexual,
        field)`` trait dispatch inside a function whose dispatch set names
        ``pleasure`` (the rulebook engine and the decay tick both write through
        a local ``trait`` binding).
        """
        for function in [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]:
            bound_to_pleasure = set()
            dispatches_pleasure = False
            for node in ast.walk(function):
                if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                    continue
                value, target = node.value, node.targets[0]
                source = ast.unparse(value)
                if isinstance(target, ast.Name):
                    if "pleasure" in source:
                        bound_to_pleasure.add(target.id)
                    if isinstance(value, ast.Call) and ast.unparse(value).startswith(
                        "getattr("
                    ) and ".sexual," in source.replace(" ", ""):
                        names = {
                            constant.value
                            for constant in ast.walk(function)
                            if isinstance(constant, ast.Constant)
                            and isinstance(constant.value, str)
                        }
                        if "pleasure" in names:
                            bound_to_pleasure.add(target.id)
                            dispatches_pleasure = True
            del dispatches_pleasure
            for node in ast.walk(function):
                if not isinstance(node, (ast.Assign, ast.AugAssign)):
                    continue
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if not isinstance(target, ast.Attribute) or target.attr not in (
                        "base",
                        "value",
                    ):
                        continue
                    chain = ast.unparse(target)
                    owner = chain.rsplit(".", 1)[0]
                    head = owner.split(".", 1)[0]
                    if ".pleasure." in f"{chain}." or (
                        head in bound_to_pleasure and owner in bound_to_pleasure
                    ):
                        yield function.name, node

    @covers_requirement("sexual-act-effects::every-deterministic-pleasure-write-lives-in-one-shared-module")
    def test_no_production_code_outside_the_sanctioned_writers_assigns_pleasure(self):
        offenders = []
        for path in self._production_sources(self._ROOT):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            relative = path.relative_to(self._ROOT).as_posix()
            for function_name, node in self._pleasure_writes(tree):
                if (relative, function_name) not in self._SANCTIONED:
                    offenders.append(f"{relative}:{node.lineno} in {function_name}()")
        self.assertEqual(offenders, [])

    def test_the_shared_module_does_not_import_the_cast_pipeline(self):
        """The transitive world-internal import closure of pleasure.py never
        names the ``world.rules.action`` module or package, so a non-cast
        caller cannot pull the cast pipeline in through it."""
        seen, stack = set(), ["world.rules.pleasure"]
        while stack:
            module = stack.pop()
            if module in seen:
                continue
            seen.add(module)
            base = self._ROOT / module.replace(".", "/")
            candidates = [base.with_suffix(".py"), base / "__init__.py"]
            for path in candidates:
                if path.exists():
                    break
            else:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                    names = [node.module] + [
                        f"{node.module}.{alias.name}" for alias in node.names
                    ]
                else:
                    continue
                for name in names:
                    if name.startswith("world"):
                        stack.append(name)
        offenders = {
            name
            for name in seen
            if name == "world.rules.action" or name.startswith("world.rules.action.")
        }
        self.assertEqual(offenders, set())


class ClimaxExtensionTests(EvenniaTestCase):
    """The extension trigger compares the pre-clamp gain, not the applied delta."""

    def setUp(self):
        super().setUp()
        self.entity = create_object(PlayerCharacter, key="extension entity")
        self.entity.race = _race_key()
        self.entity.apply_race_baseline()

    @covers_requirement("sexual-act-effects::the-pleasure-effect-handler-resolves-each-participant-s-part-and-ratio-by-role-applies-gain-and-stages-a-climax-extension-when-a-進行中-participant-s-computed-gain-meets-threshold")
    def test_qualifying_gain_on_in_progress_stages_an_extension(self):
        self.entity.sexual.climax_phase.value = "進行中"
        apply_pleasure_gain(self.entity, 30)
        self.assertEqual(self.entity.sexual.pending_climax_extension, 1)

    @covers_requirement("sexual-act-effects::the-pleasure-effect-handler-resolves-each-participant-s-part-and-ratio-by-role-applies-gain-and-stages-a-climax-extension-when-a-進行中-participant-s-computed-gain-meets-threshold")
    def test_gain_that_clamps_at_the_ceiling_still_stages_an_extension(self):
        self.entity.sexual.pleasure.base = 95
        self.entity.sexual.climax_phase.value = "進行中"
        apply_pleasure_gain(self.entity, 30)
        self.assertEqual(self.entity.sexual.pleasure.base, 100)
        self.assertEqual(self.entity.sexual.pending_climax_extension, 1)

    @covers_requirement("sexual-act-effects::the-pleasure-effect-handler-resolves-each-participant-s-part-and-ratio-by-role-applies-gain-and-stages-a-climax-extension-when-a-進行中-participant-s-computed-gain-meets-threshold")
    def test_gain_below_threshold_on_in_progress_does_not_stage(self):
        self.entity.sexual.climax_phase.value = "進行中"
        apply_pleasure_gain(self.entity, 10)
        self.assertEqual(self.entity.sexual.pending_climax_extension, 0)

    @covers_requirement("sexual-act-effects::the-pleasure-effect-handler-resolves-each-participant-s-part-and-ratio-by-role-applies-gain-and-stages-a-climax-extension-when-a-進行中-participant-s-computed-gain-meets-threshold")
    def test_gain_on_non_in_progress_never_stages_an_extension(self):
        for phase in ("未達", "接近", "餘韻"):
            with self.subTest(phase=phase):
                self.entity.sexual.climax_phase.value = phase
                apply_pleasure_gain(self.entity, 30)
                self.assertEqual(self.entity.sexual.pending_climax_extension, 0)
