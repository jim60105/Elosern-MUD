"""Behavior tests for the unconditional disguise reveal (collapse-veil-reveal-line).

This world admits exactly one grade of veil: only the bloodline-gated divine
mystery can write one, so a reveal either lifts the veil it finds or finds
none. The bare ``reveal_disguise`` prefix is the whole grammar; any payload —
including the retired ``reveal_disguise:true_name`` form — fails at parse and
therefore at registry load. The reported-no-op contract is unchanged: a
reveal that finds no veil completes as a clean no-op rather than a rejection,
so the attempt neither leaks the veil's existence through a rejection reason
nor fails the action. The clear stays in ``world/rules/skill_effects.py``
beside the placement write, and a rolled-back resolution restores layer and
placement record byte-equal together.

All skills are file-local synthetic rows; no shipped-content skill names and
no data-contract tagging appear here.
"""

from tools.spec_traceability import covers_requirement

import inspect
import unittest
from copy import deepcopy
from pathlib import Path

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    CommitFailed,
    PendingEffect,
    RejectReason,
    _commit,
    _handle_reveal_disguise,
    _handle_set_disguise,
    _snapshot_touched,
)
from world.rules.action_preview import preview_skill
from world.rules.skill_effects import (
    apply_divine_disguise,
    apply_disguise_effect,
    clear_disguise_effect,
    mundane_veil_values,
    reveal_can_pierce,
    reveal_disguise_effect,
    was_cast_placed,
)
from world.rules.targeting import RoomActionContext
from world.rules.traits import get_display_value
from world.skills.registry import TargetSpec
from world.tests.synthetic_data import make_skill

from ._combat_session_helpers import open_synthetic_scope

_DISPLAYED_COMBAT_FIVE = ("atk_phys", "agility", "defense", "magic_power", "hp")

# File-local synthetic rows: the reveal and an unrelated resolving effect
# (the parity guard's non-reveal probe), both zero-cost and context-free,
# mirroring the veil-cast suite.
_T_REVEAL = make_skill(
    "t_reveal_disguise",
    effects=["reveal_disguise"],
    target_spec=TargetSpec.SINGLE,
    cost={},
)
_T_UNRELATED = make_skill(
    "t_look_but_do_not_see",
    effects=["cleanse:status"],
    target_spec=TargetSpec.SINGLE,
    cost={},
)


class _FakeDB:
    """Attribute-proxy double: a missing attribute reads as None, and
    deleting a missing attribute is a silent no-op (Evennia semantics)."""

    def __init__(self, **attrs):
        self.__dict__.update(attrs)

    def __getattr__(self, name):
        return None

    def __delattr__(self, name):
        if name in self.__dict__:
            del self.__dict__[name]


class _FakeEntity:
    def __init__(self, **attrs):
        self.db = _FakeDB(**attrs)


class RevealPrimitiveTests(unittest.TestCase):
    """The deterministic-core write clears any veil it finds."""

    @covers_requirement("skill-handler::the-disguise-layer-has-an-unconditional-reveal-primitive")
    def test_reveal_lifts_an_authored_veil(self):
        entity = _FakeEntity()
        apply_disguise_effect(entity, {"atk_phys": 60})
        self.assertTrue(reveal_disguise_effect(entity))
        self.assertIsNone(entity.db.disguised_stats)
        self.assertFalse(was_cast_placed(entity))

    @covers_requirement("skill-handler::the-disguise-layer-has-an-unconditional-reveal-primitive")
    def test_reveal_lifts_a_veil_the_verb_placed(self):
        entity = _FakeEntity()
        apply_divine_disguise(entity)
        self.assertTrue(reveal_disguise_effect(entity))
        self.assertIsNone(entity.db.disguised_stats)
        self.assertIsNone(entity.db.disguise_placed_by_cast)
        self.assertFalse(was_cast_placed(entity))

    @covers_requirement("skill-handler::the-disguise-layer-has-an-unconditional-reveal-primitive")
    def test_reveal_against_an_unveiled_target_is_a_clean_no_op(self):
        entity = _FakeEntity()
        self.assertFalse(reveal_disguise_effect(entity))
        self.assertIsNone(entity.db.disguised_stats)
        self.assertFalse(was_cast_placed(entity))

    @covers_requirement("skill-handler::the-disguise-layer-has-an-unconditional-reveal-primitive")
    def test_clearing_reveal_removes_layer_and_placement_record_in_one_operation(self):
        # An authored veil is cleared just like a cast-placed one: the write
        # never leaves a stale placement record behind a cleared layer.
        for placed in (False, True):
            with self.subTest(placed=placed):
                attrs = {"disguised_stats": {"atk_phys": 60}}
                if placed:
                    attrs["disguise_placed_by_cast"] = True
                entity = _FakeEntity(**attrs)
                self.assertTrue(reveal_disguise_effect(entity))
                self.assertIsNone(entity.db.disguised_stats)
                self.assertIsNone(entity.db.disguise_placed_by_cast)


class RevealGrammarRegressionTests(unittest.TestCase):
    """The defect this change exists to fix: before, a weaker reveal (bare
    ``reveal_disguise`` at ``MUNDANE_ONLY``) wrongly cleared every authored
    veil in shipped content, because an authored veil always read as
    mundane. After, the strength vocabulary that produced that reading no
    longer exists: exactly one grade of veil, exactly one catalog skill that
    can declare a reveal, and no weaker form can be authored at all."""

    @covers_requirement("skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass")
    def test_no_payload_can_be_declared_on_the_reveal_prefix(self):
        for payload in ("reveal_disguise:true_name", "reveal_disguise:everything"):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    make_skill(
                        "t_bad_reveal_variant",
                        effects=[payload],
                        target_spec=TargetSpec.SINGLE,
                        cost={},
                    )

    def test_the_survivor_still_lifts_an_authored_veil(self):
        # Same synthetic authored-veil shape shipped elf cards carry: no
        # placement record, so the veil is one the verb did not place.
        entity = _FakeEntity()
        apply_disguise_effect(entity, {"atk_phys": 60, "agility": 40})
        self.assertTrue(reveal_can_pierce(entity))
        self.assertTrue(reveal_disguise_effect(entity))
        self.assertIsNone(entity.db.disguised_stats)


class _RevealCastTestCase(EvenniaTest):
    """Live-human cast fixture mirroring the veil-cast suite."""

    def setUp(self):
        super().setUp()
        open_synthetic_scope(
            self,
            "skills",
            extra={
                "skills": {
                    _T_REVEAL.key: _T_REVEAL,
                    _T_UNRELATED.key: _T_UNRELATED,
                }
            },
        )
        self.caster = create_object(PlayerCharacter, key="reveal-caster")
        self.caster.race = "human"
        self.caster.apply_race_baseline()
        self.target = create_object(PlayerCharacter, key="reveal-target")
        self.target.race = "human"
        self.target.apply_race_baseline()
        self.caster.location = self.room1
        self.target.location = self.room1
        self.caster.db.skills = {
            "active": [_T_REVEAL.key, _T_UNRELATED.key],
            "passive": [],
        }

    def _cast(self, skill_key, *, targets=None, actor=None):
        actor = actor or self.caster
        return ActionResolver.resolve(
            ActionRequest(
                actor,
                skill_key,
                list(targets or []),
                RoomActionContext(actor.location, {}),
            )
        )

    def _true_traits(self, entity):
        return deepcopy(dict(entity.traits.trait_data))


class RevealCastResolutionTests(_RevealCastTestCase):
    """Cast semantics: outcome tokens, the no-op contract, and the sealed
    write surface."""

    @covers_requirement(
        "skill-handler::the-disguise-layer-has-an-unconditional-reveal-primitive",
        "action-resolution-pipeline::the-effect-resolution-registry-is-open-"
        "prefix-keyed-and-every-handler-declares-its",
    )
    def test_reveal_lifts_an_authored_veil(self):
        # The shipped-preset shape: a character card declaration with no
        # placement record is lifted.
        self.target.db.disguised_stats = {"atk_phys": 7, "agility": 9}
        before = self._true_traits(self.target)
        result = self._cast(_T_REVEAL.key, targets=[self.target])
        self.assertEqual(result.outcome, "success")
        self.assertIsNone(self.target.db.disguised_stats)
        self.assertFalse(self.target.attributes.has("disguised_stats"))
        self.assertFalse(self.target.attributes.has("disguise_placed_by_cast"))
        self.assertEqual(self._true_traits(self.target), before)
        for key in _DISPLAYED_COMBAT_FIVE:
            self.assertEqual(
                get_display_value(self.target, key),
                getattr(self.target.traits, key).value,
            )
        self.assertIn(
            "reveal_lifted", [entry.kind for entry in result.event_log.entries]
        )

    @covers_requirement(
        "skill-handler::the-disguise-layer-has-an-unconditional-reveal-primitive",
        "action-resolution-pipeline::the-effect-resolution-registry-is-open-"
        "prefix-keyed-and-every-handler-declares-its",
    )
    def test_reveal_lifts_a_veil_the_verb_placed(self):
        apply_divine_disguise(self.target)
        before = self._true_traits(self.target)
        result = self._cast(_T_REVEAL.key, targets=[self.target])
        self.assertEqual(result.outcome, "success")
        self.assertIsNone(self.target.db.disguised_stats)
        self.assertFalse(self.target.attributes.has("disguised_stats"))
        self.assertFalse(self.target.attributes.has("disguise_placed_by_cast"))
        self.assertFalse(was_cast_placed(self.target))
        self.assertEqual(self._true_traits(self.target), before)
        self.assertIn(
            "reveal_lifted", [entry.kind for entry in result.event_log.entries]
        )

    @covers_requirement(
        "skill-handler::the-disguise-layer-has-an-unconditional-reveal-primitive",
        "action-resolution-pipeline::the-effect-resolution-registry-is-open-"
        "prefix-keyed-and-every-handler-declares-its",
    )
    def test_reveal_against_an_unveiled_target_is_a_clean_no_op(self):
        target = create_object(PlayerCharacter, key="veil-free")
        target.race = "human"
        target.apply_race_baseline()
        target.location = self.room1
        result = self._cast(_T_REVEAL.key, targets=[target])
        self.assertEqual(result.outcome, "success")
        # The typeclass shell pre-initializes ``disguised_stats`` to None, so
        # an untouched target keeps that shell default: the reveal wrote
        # nothing and created no placement record.
        self.assertIsNone(target.db.disguised_stats)
        self.assertFalse(target.attributes.has("disguise_placed_by_cast"))
        self.assertFalse(was_cast_placed(target))
        kinds = [entry.kind for entry in result.event_log.entries]
        self.assertIn("reveal_noop", kinds)
        self.assertNotIn("reveal_lifted", kinds)

    @covers_requirement(
        "skill-handler::the-disguise-layer-has-an-unconditional-reveal-primitive",
        "action-resolution-pipeline::the-effect-resolution-registry-is-open-"
        "prefix-keyed-and-every-handler-declares-its",
    )
    def test_reveal_reads_and_writes_nothing_but_the_layer_and_its_placement_record(self):
        apply_divine_disguise(self.target)
        self.target.db.persona = {
            "personality": "沉穩",
            "identity": {"public": "旅行商人", "hidden": "落魄王族"},
        }
        before_traits = self._true_traits(self.target)
        before_persona = deepcopy(dict(self.target.db.persona))
        result = self._cast(_T_REVEAL.key, targets=[self.target])
        self.assertEqual(result.outcome, "success")
        self.assertFalse(self.target.attributes.has("disguised_stats"))
        self.assertFalse(self.target.attributes.has("disguise_placed_by_cast"))
        # True traits, persona (hidden identity included), and identity keys
        # are byte-identical: only the veil and its placement record moved.
        self.assertEqual(self._true_traits(self.target), before_traits)
        self.assertEqual(dict(self.target.db.persona), before_persona)
        self.assertEqual(self.target.key, "reveal-target")


class RevealPreviewTests(_RevealCastTestCase):
    """The shared preview accepts the reveal with an empty event context."""

    @covers_requirement("effect-context-validation::effect-handlers-declare-their-required-event-context")
    def test_preview_with_empty_context_reports_no_missing_effect_context(self):
        preview = preview_skill(
            self.caster, _T_REVEAL.key, RoomActionContext(self.room1, {})
        )
        self.assertTrue(preview.enabled)
        self.assertIsNot(preview.reason, RejectReason.MISSING_EFFECT_CONTEXT)


class RevealRollbackTests(_RevealCastTestCase):
    """A rolled-back reveal restores the layer and placement record byte-equal."""

    def _failing_effect(self, entity):
        return PendingEffect(
            entity,
            "injected failure",
            frozenset({"traits"}),
            lambda: (_ for _ in ()).throw(RuntimeError("injected")),
        )

    @covers_requirement(
        "action-resolution-pipeline::resolution-is-atomic-a-failure-at-any-"
        "step-leaves-zero-state-mutated",
        "disguised-stats-boundary::the-disguise-layer-records-whether-the-"
        "veil-verb-placed-it",
    )
    def test_failed_commit_restores_the_veil_and_placement_record_byte_equal(self):
        apply_divine_disguise(self.target)
        before = _snapshot_touched(self.target, frozenset({"traits"}))
        effects = [
            PendingEffect(
                self.target,
                "reveal_lifted|reveal-target",
                frozenset({"traits"}),
                lambda: reveal_disguise_effect(self.target),
            ),
            self._failing_effect(self.target),
        ]
        with self.assertRaises(CommitFailed):
            _commit(effects, char=str(self.caster.pk), action="test_reveal")
        self.assertEqual(
            _snapshot_touched(self.target, frozenset({"traits"})), before
        )
        self.assertEqual(self.target.db.disguised_stats, mundane_veil_values())
        self.assertTrue(was_cast_placed(self.target))


class RevealBoundaryParityTests(_RevealCastTestCase):
    """The clear stays in the classified writer module; the mundane appraisal
    lineage keeps no pierce path of its own."""

    def test_clear_disguise_effect_call_sites_stay_in_the_two_sanctioned_paths(self):
        # Every production module that can clear the layer: the cast-path
        # self-toggle handler and the reveal write. The mundane appraisal
        # lineage (真知鑑定, lore-documented as unable to pierce 神之祕法) is
        # a forward-declared seam with no cast path, so no third module may
        # clear a veil — a veil can only be lifted by the reveal line or by
        # its own caster.
        root = Path(__file__).resolve().parents[3]
        offenders = []
        for tree in ("world", "typeclasses", "commands"):
            for path in sorted((root / tree).rglob("*.py")):
                relative = path.relative_to(root).as_posix()
                if "/tests/" in f"/{relative}":
                    continue
                if "clear_disguise_effect" in path.read_text(encoding="utf-8"):
                    offenders.append(relative)
        self.assertEqual(
            offenders,
            # The self-toggle handler moved with the action package split.
            [
                "world/rules/action/effects/conferral.py",
                "world/rules/skill_effects.py",
            ],
            f"unclassified veil-clear call sites: {offenders}",
        )
        # Within conferral.py only the divine self-toggle calls the clear
        # directly: the reveal handler stages the deterministic-core write
        # instead. Stripping the two sanctioned handler sources leaves no
        # call behind anywhere else in the module.
        action_source = (
            root / "world/rules/action/effects/conferral.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "clear_disguise_effect(", inspect.getsource(_handle_set_disguise)
        )
        self.assertNotIn(
            "clear_disguise_effect(", inspect.getsource(_handle_reveal_disguise)
        )
        remainder = action_source
        for sanctioned in (
            inspect.getsource(_handle_set_disguise),
            inspect.getsource(_handle_reveal_disguise),
        ):
            remainder = remainder.replace(sanctioned, "")
        self.assertNotIn(
            "clear_disguise_effect(", remainder
        )

    def test_an_unrelated_skill_attempt_leaves_a_veil_byte_equal(self):
        # A resolving non-reveal effect (cleanse) cannot lift a veil: the
        # layer and its placement record stay exactly as they were, and no
        # reveal outcome is reported.
        apply_divine_disguise(self.target)
        before_layer = deepcopy(dict(self.target.db.disguised_stats))
        before = self._true_traits(self.target)
        result = self._cast(_T_UNRELATED.key, targets=[self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.target.db.disguised_stats, before_layer)
        self.assertTrue(was_cast_placed(self.target))
        self.assertEqual(self._true_traits(self.target), before)
        kinds = [entry.kind for entry in result.event_log.entries]
        self.assertNotIn("reveal_lifted", kinds)
        self.assertNotIn("reveal_noop", kinds)


if __name__ == "__main__":
    unittest.main()
