"""Phase-reaction self-recovery behavior tests (rapture-renewal-climax-heal).

Synthetic entities, synthetic rule tables, and synthetic qualifier skills
only: the shipped-content touch for this change is the skill-registry census
in ``world/skills/tests/test_skill_registry.py``, and the shipped
``state_reactions.yaml`` rule is proven through loader validation plus the
module-import load (the rulebook is validated at import time).

The phase dispatcher fires only on canonical climax phase *transitions*, so
"once per climax" is a property of the existing machinery, not of a flag:
entering 進行中 heals, and anything that happens while the holder already sits
in 進行中 (an extension, another gained stimulus) triggers nothing.
"""

import math
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from tools.spec_traceability import covers_requirement

from typeclasses.characters import PlayerCharacter
from world.rules.action import CommitFailed, PendingEffect, RejectReason, _commit
from world.rules.pleasure import apply_pleasure_gain
from world.rules.rulebook.schema import Rule
from world.rules.sexual_state import _apply_climax_phase_set
from world.rules.state_reactions import (
    dispatch_phase_reaction,
    validate_state_reaction_rules,
)
from world.skills.registry import SkillCategory, SkillKind, TargetSpec, _skill

from ._combat_session_helpers import _race_key, open_synthetic_scope
from .combat_fixtures import FakeEntity

# --- Synthetic fixtures (file-local, never shipped content) ---------------

_T_RENEWAL_KEY = "t_synth_renewal"

#: The qualifier skill the synthetic rules gate on: PASSIVE, no prerequisites,
#: no effects — the same qualifier-row shape ``pain_to_pleasure`` has, so
#: ``can_use_skill`` reduces to ownership.
_T_RENEWAL = _skill(
    _T_RENEWAL_KEY,
    "合成回生",
    "合成測試用被動：進入高潮進行中期相時無成本自癒。",
    SkillKind.PASSIVE,
    TargetSpec.NONE,
    usable_out_of_combat=True,
    element=None,
    category=SkillCategory.ENHANCEMENT,
)

#: The shipped rule's shape replicated on synthetic keys (task 3.1).
_T_HEAL_RULE = Rule(
    id="t_synth_climax_self_heal",
    when={
        "field": "climax_phase",
        "equals": "進行中",
        "skill_qualified": _T_RENEWAL_KEY,
    },
    then={"self_heal_max_fraction": 0.5},
)


def _patch_registry():
    """Swap the skills registry map for the single synthetic qualifier."""
    return patch("world.skills.registry.SKILL_REGISTRY", {_T_RENEWAL_KEY: _T_RENEWAL})


class _FakeAttributes:
    """Minimal in-memory attribute handler for pure dispatcher unit tests."""

    def __init__(self):
        self._store = {}

    def get(self, key, default=None, category=None):
        return self._store.get((key, category), default)

    def has(self, key, category=None):
        return (key, category) in self._store


def _holder(hp=100, max_hp=None, owned=(_T_RENEWAL_KEY,)):
    """A synthetic holder: combat-fake traits plus an attributes facade."""
    entity = FakeEntity("t_heal_holder", hp=hp, max_hp=max_hp, owned=list(owned))
    entity.attributes = _FakeAttributes()
    return entity


# ---------------------------------------------------------------------------
# 2.1 Loader: the self-recovery fraction is validated fail-closed
# ---------------------------------------------------------------------------


class SelfHealFractionLoaderTests(unittest.TestCase):
    """The loader recognizes ``self_heal_max_fraction`` and rejects bad forms."""

    def _rule(self, fraction, rule_id="t_synth_bad_heal", event=False):
        when = {"field": "climax_phase", "equals": "進行中"}
        if event:
            when = {"event": "hp_loss"}
        return Rule(id=rule_id, when=when, then={"self_heal_max_fraction": fraction})

    @covers_requirement("damage-state-feedback::a-qualified-passive-self-recovers-once-on-canonical-climax-entry")
    def test_accepted_fractions_load(self):
        for fraction in (0.5, 1):
            with self.subTest(fraction=fraction):
                validate_state_reaction_rules(
                    [self._rule(fraction, f"t_synth_ok_heal_{fraction}")]
                )

    @covers_requirement("damage-state-feedback::a-qualified-passive-self-recovers-once-on-canonical-climax-entry")
    def test_malformed_fraction_fails_naming_the_rule(self):
        for label, fraction in {
            "zero": 0,
            "negative": -0.5,
            "above_one": 1.5,
            "infinite": math.inf,
            "nan": math.nan,
            "string": "half",
            "boolean": True,
            "none": None,
        }.items():
            with self.subTest(label=label):
                with self.assertRaises(ValueError) as caught:
                    validate_state_reaction_rules(
                        [self._rule(fraction, f"t_synth_bad_heal_{label}")]
                    )
                self.assertIn(f"t_synth_bad_heal_{label}", str(caught.exception))
                self.assertIn("self_heal_max_fraction", str(caught.exception))

    @covers_requirement("damage-state-feedback::a-qualified-passive-self-recovers-once-on-canonical-climax-entry")
    def test_event_conditioned_self_heal_is_rejected(self):
        # The heal is a phase action; an event-conditioned rule could never
        # execute it (dispatch_outcome_reaction owns a disjoint vocabulary),
        # so it must not silently dead-load.
        with self.assertRaises(ValueError) as caught:
            validate_state_reaction_rules([self._rule(0.5, "t_synth_event_heal", event=True)])
        self.assertIn("t_synth_event_heal", str(caught.exception))


# ---------------------------------------------------------------------------
# 2.2 Dispatcher: the max-HP-fraction self-heal executes on entry
# ---------------------------------------------------------------------------


class PhaseSelfHealDispatchTests(unittest.TestCase):
    """The phase dispatcher applies the authored fraction on canonical entry."""

    def _dispatch(self, entity, rules=None, from_phase="接近", to_phase="進行中"):
        dispatch_phase_reaction(
            entity,
            from_phase=from_phase,
            to_phase=to_phase,
            rules=rules if rules is not None else [_T_HEAL_RULE],
        )

    @covers_requirement("damage-state-feedback::a-qualified-passive-self-recovers-once-on-canonical-climax-entry")
    def test_deeply_wounded_holder_gains_the_floored_fraction(self):
        entity = _holder(hp=20, max_hp=100)
        with _patch_registry():
            self._dispatch(entity)
        # floor(100 x 0.5) = 50, clamped by the 80-point gap -> 50.
        self.assertEqual(entity.traits.hp.current, 70)

    @covers_requirement("damage-state-feedback::a-qualified-passive-self-recovers-once-on-canonical-climax-entry")
    def test_lightly_wounded_holder_rises_to_exactly_maximum(self):
        entity = _holder(hp=80, max_hp=100)
        with _patch_registry():
            self._dispatch(entity)
        # floor = 50 but only 20 HP are missing: the heal clamps to the gap.
        self.assertEqual(entity.traits.hp.current, 100)

    @covers_requirement("damage-state-feedback::a-qualified-passive-self-recovers-once-on-canonical-climax-entry")
    def test_downed_holder_gains_nothing(self):
        for hp in (0, -5):
            with self.subTest(hp=hp):
                entity = _holder(hp=hp, max_hp=100)
                with _patch_registry():
                    self._dispatch(entity)
                self.assertEqual(entity.traits.hp.current, hp)

    @covers_requirement("damage-state-feedback::a-qualified-passive-self-recovers-once-on-canonical-climax-entry")
    def test_unqualified_holder_receives_nothing(self):
        entity = _holder(hp=20, max_hp=100, owned=())
        with _patch_registry():
            self._dispatch(entity)
        self.assertEqual(entity.traits.hp.current, 20)

    @covers_requirement("damage-state-feedback::a-qualified-passive-self-recovers-once-on-canonical-climax-entry")
    def test_unknown_qualifier_resolves_to_no_heal(self):
        entity = _holder(hp=20, max_hp=100)
        unknown = Rule(
            id="t_synth_unknown_qualifier",
            when={
                "field": "climax_phase",
                "equals": "進行中",
                "skill_qualified": "t_synth_never_registered",
            },
            then={"self_heal_max_fraction": 0.5},
        )
        with _patch_registry():
            self._dispatch(entity, rules=[unknown])
        self.assertEqual(entity.traits.hp.current, 20)

    @covers_requirement("damage-state-feedback::a-qualified-passive-self-recovers-once-on-canonical-climax-entry")
    def test_unreadable_or_non_positive_maximum_restores_nothing(self):
        # Unreadable: the entity carries no HP trait at all.
        entity = _holder(hp=50, max_hp=100)
        entity.traits = None
        with _patch_registry():
            self._dispatch(entity)
        # Non-positive maximum: the fake gauge's stored base drops to zero.
        entity = _holder(hp=50, max_hp=100)
        entity.traits.hp._data["base"] = 0
        with _patch_registry():
            self._dispatch(entity)
        self.assertEqual(entity.traits.hp.current, 50)

    @covers_requirement("damage-state-feedback::a-qualified-passive-self-recovers-once-on-canonical-climax-entry")
    def test_over_maximum_holder_restores_nothing(self):
        # A holder already above maximum has no gap: the heal must not shave
        # the surplus down (a heal never decreases HP).
        entity = _holder(hp=120, max_hp=100)
        with _patch_registry():
            self._dispatch(entity)
        self.assertEqual(entity.traits.hp.current, 120)


# ---------------------------------------------------------------------------
# 2.3 Once per climax: the transition, not the state, settles the heal
# ---------------------------------------------------------------------------


class PhaseSelfHealOncePerTransitionTests(unittest.TestCase):
    """Only a canonical entry into 進行中 pays out; other edges never do."""

    @covers_requirement("damage-state-feedback::a-qualified-passive-self-recovers-once-on-canonical-climax-entry")
    def test_entry_into_in_progress_heals_and_exit_edges_do_not(self):
        entity = _holder(hp=20, max_hp=100)
        with _patch_registry():
            dispatch_phase_reaction(entity, "接近", "進行中", rules=[_T_HEAL_RULE])
            self.assertEqual(entity.traits.hp.current, 70)
            # Leaving the phase is not an entry: nothing further is restored.
            dispatch_phase_reaction(entity, "進行中", "餘韻", rules=[_T_HEAL_RULE])
            dispatch_phase_reaction(entity, "餘韻", "未達", rules=[_T_HEAL_RULE])
        self.assertEqual(entity.traits.hp.current, 70)


class RaptureRenewalClimaxFlowTests(EvenniaTest):
    """The pleasure path walks the canonical cycle; the heal follows entry."""

    def setUp(self):
        super().setUp()
        open_synthetic_scope(self, "skills", "elements", "races", "subraces", "static_tiers")
        self.actor = create_object(PlayerCharacter, key="t_heal_cleric", location=self.room1)
        self.actor.race = _race_key()
        self.actor.apply_race_baseline()
        self.actor.db.skills = {"active": [], "passive": [_T_RENEWAL_KEY]}

        self.plain = create_object(PlayerCharacter, key="t_plain_holder", location=self.room1)
        self.plain.race = _race_key()
        self.plain.apply_race_baseline()
        self.plain.db.skills = {"active": [], "passive": []}

        registry_patch = _patch_registry()
        registry_patch.start()
        self.addCleanup(registry_patch.stop)
        rules_patch = patch(
            "world.rules.state_reactions.STATE_REACTION_RULES", [_T_HEAL_RULE]
        )
        rules_patch.start()
        self.addCleanup(rules_patch.stop)

    def _enter_climax(self, entity):
        apply_pleasure_gain(entity, 100)
        apply_pleasure_gain(entity, 0)
        self.assertEqual(entity.sexual.climax_phase.level, "進行中")

    def _stored_hp(self, entity):
        return int(entity.traits.hp.current)

    @covers_requirement("damage-state-feedback::a-qualified-passive-self-recovers-once-on-canonical-climax-entry")
    def test_qualified_holder_heals_once_per_entry_and_extension_heals_nothing(self):
        max_hp = int(self.actor.traits.hp.max)
        self.actor.traits.hp.current = max_hp // 2 - 10  # deeply wounded
        before = self._stored_hp(self.actor)

        self._enter_climax(self.actor)
        after_entry = self._stored_hp(self.actor)
        self.assertEqual(after_entry, before + max_hp // 2)

        # A further stimulus while already in 進行中 extends/stages but never
        # re-enters the phase: the dispatcher is not called, nothing heals.
        apply_pleasure_gain(self.actor, 30)
        self.assertEqual(self.actor.sexual.climax_phase.level, "進行中")
        self.assertEqual(self._stored_hp(self.actor), after_entry)

        # A second climax cycle pays out again: once per climax, not once ever.
        _apply_climax_phase_set(self.actor, "餘韻")
        _apply_climax_phase_set(self.actor, "未達")
        self.actor.traits.hp.current = max_hp // 2 - 10
        self._enter_climax(self.actor)
        self.assertEqual(self._stored_hp(self.actor), max_hp // 2 - 10 + max_hp // 2)

    @covers_requirement("damage-state-feedback::a-qualified-passive-self-recovers-once-on-canonical-climax-entry")
    def test_holder_without_the_passive_receives_nothing(self):
        max_hp = int(self.plain.traits.hp.max)
        self.plain.traits.hp.current = max_hp // 2 - 10
        before = self._stored_hp(self.plain)

        self._enter_climax(self.plain)
        self.assertEqual(self._stored_hp(self.plain), before)

    @covers_requirement("damage-state-feedback::a-qualified-passive-self-recovers-once-on-canonical-climax-entry")
    def test_a_low_damage_climax_cannot_overheal(self):
        max_hp = int(self.actor.traits.hp.max)
        self.actor.traits.hp.current = max_hp - max_hp // 5  # only 20% missing
        self._enter_climax(self.actor)
        # The heal clamps to the missing 20%; nothing is banked for later.
        self.assertEqual(self._stored_hp(self.actor), max_hp)

    @covers_requirement("damage-state-feedback::a-qualified-passive-self-recovers-once-on-canonical-climax-entry")
    def test_failed_settlement_restores_hp_phase_and_pleasure_together(self):
        max_hp = int(self.actor.traits.hp.max)
        self.actor.traits.hp.current = max_hp // 2 - 10
        pleasure_before = self.actor.sexual.pleasure.base
        hp_before = self._stored_hp(self.actor)
        self.assertEqual(self.actor.sexual.climax_phase.level, "未達")

        effects = [
            PendingEffect(
                self.actor,
                f"t_pleasure_peak|{self.actor.key}|100",
                frozenset({"sexual", "traits", "buffs"}),
                lambda: (
                    apply_pleasure_gain(self.actor, 100),
                    apply_pleasure_gain(self.actor, 0),
                ),
            ),
            PendingEffect(
                self.actor,
                "boom",
                frozenset({"sexual", "traits", "buffs"}),
                lambda: (_ for _ in ()).throw(RuntimeError("injected commit error")),
            ),
        ]
        with self.assertRaises(CommitFailed) as caught:
            _commit(effects, char="tester", action="t_rapture_renewal_heal")
        self.assertIs(caught.exception.reason, RejectReason.COMMIT_FAILED)

        # HP, climax phase and the pleasure gauge roll back together: the
        # enclosing face's snapshot covers the phase dispatcher's new HP write.
        self.assertEqual(self._stored_hp(self.actor), hp_before)
        self.assertEqual(self.actor.sexual.climax_phase.level, "未達")
        self.assertEqual(self.actor.sexual.pleasure.base, pleasure_before)