"""Behavior tests for the monster-AI effect estimation.

Two kinds of fixture, both synthetic: file-local probe participants whose
materializing handlers are booby-trapped (reused from the decision-input
harness, so an estimation path that mounted one fails loudly), and a
real-entity fixture that settles the very same plan through ``ActionResolver``.
No shipped key, display string or catalog symbol is named by a resolvable
literal: the three buff definitions these tests need are resolved from the live
rulebook by predicate, exactly as the candidate tests resolve the positional
marker.

The tests establish this slice's contracts: an estimate is the analytic average
of the d100 range under settlement's own hit gate and multi-strike topology (it
rolls no die, mounts no handler, pays nothing and emits no event); capacity and
a recipient's nonlethal floor bind inside every branch, so no later effect can
bill the same health point twice; ordered effects and a hit-dependent drain
follow settlement's commit order and read its one shared gate; the signed
features are bounded, normalized by the affected faction's capacity and
honestly labeled, with unvaluable harms refused rather than zeroed; and the
estimator's own rulebook inputs join the recorded tuning fingerprint.
"""

from tools.spec_traceability import covers_requirement

import unittest
from dataclasses import replace
from unittest.mock import patch

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.rooms import Room

from world.rules import monster_behaviour as behaviour
from world.rules.action import ActionRequest, ActionResolver
from world.rules.buffs import BUFF_DEFINITIONS
from world.rules.combat import (
    COMBAT_YAML,
    Battlefield,
    BattlefieldActionContext,
    _restored_amount,
    _roll_multiplier,
    _to_hit,
)
from world.rules.combat.scalars import (
    crosses_knockout,
    damage_multiplier,
    heal_amount,
    hit_margin,
    nonlethal_projection,
    staged_restoration,
    strike_amount,
    strike_lands,
)
from world.rules.monster_ai import (
    ApproximationClass,
    DecisionReads,
    DecisionScope,
    EstimationLimit,
    InvalidEstimate,
    InvalidEstimateReason,
    PlannedAction,
    build_decision_snapshot,
    enumerate_candidates,
    estimate_candidates,
    estimate_plan,
    roster_index,
    stable_identity,
)
from world.rules.monster_ai.candidates import Candidate, CandidateIdentity
from world.skills.effects import (
    DamagePolicy,
    EffectAudience,
    EffectPolicy,
    GaugeTransferPolicy,
)
from world.skills.registry import TargetSpec

from ._combat_session_helpers import (
    SYNTH_GLOW_ELEMENT,
    _monster,
    _player,
    open_synthetic_scope,
    synth_damage_skill,
    synth_innate_overlay,
)
from .combat_fixtures import FakeEntity
from .test_monster_ai_candidates import _suppress_innate_skills
from .test_monster_ai_snapshots import (
    _ProbeParticipant,
    _buff_record,
    _probe_field,
    _trait_record,
)

SCOPE = "normal:53:0"
ROUND = 53

#: One buff definition of each polarity and the rulebook's own diversion
#: budget, all resolved from the live catalog by predicate.
DEBUFF_KEY = next(
    key
    for key, definition in BUFF_DEFINITIONS.items()
    if definition.polarity == "debuff"
)
BUFF_KEY = next(
    key for key, definition in BUFF_DEFINITIONS.items() if definition.polarity == "buff"
)
DIVERT_KEY = next(
    key
    for key, definition in BUFF_DEFINITIONS.items()
    if "divert" in definition.modifiers
    and definition.modifiers["divert"]["target"] == "mp"
)
DIVERT_SPEC = BUFF_DEFINITIONS[DIVERT_KEY].modifiers["divert"]

#: The kit's SINGLE elemental-damage template, the base of every row here. Its
#: damage is the magic school, so the caster statistic these tests drive is
#: magic power (the physical sibling reads a different one).
STRIKE = synth_damage_skill(
    "t_est_strike",
    "估值裂擊",
    effects=(f"damage:{SYNTH_GLOW_ELEMENT}:magic",),
    cost={"mp": 12},
)
#: Two damage occurrences in one action: ordered capping on one recipient.
DOUBLE = replace(STRIKE, key="t_est_double", effects=[*STRIKE.effects, *STRIKE.effects])
#: One occurrence that rolls two strikes of its own.
TWIN = replace(
    STRIKE,
    key="t_est_twin",
    effect_policies=(EffectPolicy(damage=DamagePolicy(extra_strikes=1)),),
)
#: An evidence-conditional strike: it resolves only when the recipient carries
#: fresh evidence, which a decision's reads do not project.
CONDITIONAL = replace(
    STRIKE,
    key="t_est_conditional",
    effect_policies=(
        EffectPolicy(damage=DamagePolicy(repeat_when="forced_interaction")),
    ),
)
#: A damage occurrence plus its hit-dependent full-share mana drain.
DRAIN = replace(
    STRIKE,
    key="t_est_drain",
    cost={"mp": 10},
    effects=[*STRIKE.effects, "gauge_transfer:mp:drain:fixed:10"],
    effect_policies=(
        EffectPolicy(),
        EffectPolicy(
            requires_hit_from=0,
            transfer=GaugeTransferPolicy(caster_recovery_share=1.0),
        ),
    ),
)
#: The same row whose damage occurrence rolls two strikes: the drain reads that
#: occurrence's one shared gate instead of a second independent roll.
DRAIN_TWIN = replace(
    DRAIN,
    key="t_est_drain_twin",
    effect_policies=(
        EffectPolicy(damage=DamagePolicy(extra_strikes=1)),
        EffectPolicy(
            requires_hit_from=0,
            transfer=GaugeTransferPolicy(caster_recovery_share=1.0),
        ),
    ),
)
#: A damage occurrence plus a self-bound heal the actor's own gap caps.
PENANCE = replace(STRIKE, key="t_est_penance", effects=[*STRIKE.effects, "self_heal"])
#: A heal-only row: the shape an estimate with nothing omitted looks like.
MEND = replace(STRIKE, key="t_est_mend", effects=["self_heal"])
#: A row whose second effect is an own-side status: unsupported harm, refused.
SELF_HARM = replace(
    STRIKE,
    key="t_est_self_harm",
    effects=[*STRIKE.effects, f"self_buff_apply:{DEBUFF_KEY}"],
)
#: A row whose second effect hands a status to the enemy side: refused too.
FOE_WARD = replace(
    STRIKE,
    key="t_est_foe_ward",
    effects=[*STRIKE.effects, f"buff_apply:{BUFF_KEY}"],
)
#: A row whose second effect is an enemy-side status: unvalued, never refused.
CURSED = replace(
    STRIKE,
    key="t_est_cursed",
    effects=[*STRIKE.effects, f"buff_apply:{DEBUFF_KEY}"],
)
#: A row whose second effect drains a pool from a friendly audience.
FRIEND_LEECH = replace(
    STRIKE,
    key="t_est_friend_leech",
    target_spec=TargetSpec.AREA,
    effects=[*STRIKE.effects, "gauge_transfer:mp:drain:fixed:5"],
    effect_policies=(
        EffectPolicy(audience=EffectAudience.ENEMIES),
        EffectPolicy(audience=EffectAudience.ALLIES),
    ),
)
#: An area row that damages enemies and heals the actor's own side.
WARD = replace(
    STRIKE,
    key="t_est_ward",
    target_spec=TargetSpec.AREA,
    effects=[*STRIKE.effects, "heal:area"],
    effect_policies=(
        EffectPolicy(audience=EffectAudience.ENEMIES),
        EffectPolicy(audience=EffectAudience.ALLIES),
    ),
)
#: The same row with both arms pointing at the enemy: enemy healing is a harm.
FOE_MEND = replace(
    WARD,
    key="t_est_foe_mend",
    effect_policies=(
        EffectPolicy(audience=EffectAudience.ENEMIES),
        EffectPolicy(audience=EffectAudience.ENEMIES),
    ),
)
#: Two damage occurrences where the second depends on the first having landed.
GATED = replace(
    STRIKE,
    key="t_est_gated",
    effects=[*STRIKE.effects, *STRIKE.effects],
    effect_policies=(EffectPolicy(), EffectPolicy(requires_hit_from=0)),
)
#: A damage occurrence plus a health drain at full recovery share.
BLOOD = replace(
    STRIKE,
    key="t_est_blood",
    effects=[*STRIKE.effects, "gauge_transfer:hp:drain:fixed:5"],
    effect_policies=(
        EffectPolicy(),
        EffectPolicy(transfer=GaugeTransferPolicy(caster_recovery_share=1.0)),
    ),
)
#: An area row that damages every enemy and drains every enemy's mana.
SIPHON = replace(
    STRIKE,
    key="t_est_siphon",
    target_spec=TargetSpec.AREA,
    effects=[*STRIKE.effects, "gauge_transfer:mp:drain:fixed:10"],
    effect_policies=(
        EffectPolicy(audience=EffectAudience.ENEMIES),
        EffectPolicy(
            audience=EffectAudience.ENEMIES,
            requires_hit_from=0,
            transfer=GaugeTransferPolicy(caster_recovery_share=1.0),
        ),
    ),
)
#: A damage occurrence plus a grant revocation aimed at the actor's own side.
STRIPPED = replace(
    STRIKE,
    key="t_est_stripped",
    effects=[*STRIKE.effects, "revoke_grants"],
    effect_policies=(EffectPolicy(), EffectPolicy(audience=EffectAudience.ALLIES)),
)
#: A damage occurrence plus a cleanse aimed at the enemy.
PURGED = replace(
    STRIKE,
    key="t_est_purged",
    effects=[*STRIKE.effects, "cleanse:status"],
)
#: A row charging two different pools.
COSTLY = replace(STRIKE, key="t_est_costly", cost={"mp": 10, "sp": 4})


def _rows() -> dict[str, object]:
    """The file-local skill rows one test registers."""
    return {
        row.key: row
        for row in (
            STRIKE,
            DOUBLE,
            TWIN,
            CONDITIONAL,
            DRAIN,
            DRAIN_TWIN,
            PENANCE,
            MEND,
            SELF_HARM,
            FOE_WARD,
            CURSED,
            FRIEND_LEECH,
            WARD,
            FOE_MEND,
            GATED,
            BLOOD,
            SIPHON,
            STRIPPED,
            PURGED,
            COSTLY,
        )
    }


def _scope(test, *extra_logicals):
    """Enter the kit scope this module's fixtures need."""
    extra = synth_innate_overlay()
    extra["skills"].update(_rows())
    return open_synthetic_scope(
        test,
        "monster_tiers",
        "races",
        "skills",
        "elements",
        *extra_logicals,
        extra=extra,
    )


def _set(participant, trait_key, value, *, current=None) -> None:
    """Overwrite one probe participant's persisted trait record."""
    participant.attributes.values["traits"][trait_key] = _trait_record(
        value, current=current
    )


def _shaped(actor, opponents, *, scope_index=0, event_context=None):
    """One decision's snapshot, read set, roster and context over probes."""
    context = BattlefieldActionContext(
        _probe_field(actor, *opponents), event_context=event_context or {}
    )
    reads = DecisionReads()
    snapshot = build_decision_snapshot(
        actor,
        context,
        scope=DecisionScope(SCOPE, ROUND, scope_index),
        participants=tuple(opponents),
        reads=reads,
    )
    return snapshot, reads, roster_index((actor, *opponents)), context


def _owned(actor, *keys) -> None:
    """Overwrite one probe participant's owned skill rows."""
    actor.db.skills = {"active": list(keys), "passive": []}


def _estimate(actor, opponents, *, scale=1.0, **decision_kwargs):
    """Enumerate and estimate one decision's candidates over probes."""
    snapshot, reads, roster, context = _shaped(actor, opponents, **decision_kwargs)
    candidates = enumerate_candidates(
        snapshot,
        actor=actor,
        context=context,
        roster=roster,
        reads=reads,
        scale=scale,
    )
    return estimate_candidates(
        candidates,
        snapshot=snapshot,
        actor=actor,
        context=context,
        roster=roster,
        reads=reads,
    )


def _only(estimates):
    """Return the single estimate one-row decision produced."""
    if len(estimates.estimates) != 1:
        raise AssertionError(f"expected one estimate, got {estimates.estimates!r}")
    return estimates.estimates[0]


def _widest(estimates, skill_key):
    """Return one skill's widest plan out of a decision's set.

    A mixed area skill contributes one plan per legal audience combination, and
    the one that reaches the actor's own side is the widest of them.
    """
    matching = [
        item for item in estimates.estimates if item.identity.skill_key == skill_key
    ]
    if not matching:
        raise AssertionError(f"no estimate for {skill_key!r} in {estimates.estimates!r}")
    return max(matching, key=lambda item: len(item.recipients))


def _pick(estimates, skill_key):
    """Return one skill's estimate out of a decision's set."""
    for item in estimates.estimates:
        if item.identity.skill_key == skill_key:
            return item
    raise AssertionError(f"no estimate for {skill_key!r} in {estimates.estimates!r}")


def _recipient(estimate, entity):
    """Return one identity's recipient projection."""
    for projection in estimate.recipients:
        if projection.identity == stable_identity(entity):
            return projection
    raise AssertionError(f"no projection for {stable_identity(entity)}")


def _deltas(estimate, entity) -> dict[str, float]:
    """Return one identity's projected pool changes by gauge."""
    for projection in estimate.resources:
        if projection.identity == stable_identity(entity):
            return dict(projection.deltas)
    return {}


def _hand(skill, recipients, routed, *, scale=1.0):
    """One hand-built candidate carrying its own declared routing."""
    ordered = tuple(sorted(stable_identity(target) for target in recipients))
    return Candidate(
        CandidateIdentity(skill.key, scale, ordered),
        PlannedAction(skill.key, scale, target_ids=ordered),
        recipients=tuple(recipients),
        routed=tuple(tuple(reached) for reached in routed),
    )


class ScalarExpressionTests(unittest.TestCase):
    """The shared scalar arithmetic settlement and estimation both call."""

    @covers_requirement("monster-ai-effect-estimation::damage-estimates-use-settlement-arithmetic-without-settlement")
    def test_the_multiplier_ladder_is_banded_by_margin_with_a_critical_face(self):
        self.assertEqual(damage_multiplier(100, 0.0), 2.0)
        self.assertEqual(damage_multiplier(60, 40.0), 1.5)
        self.assertEqual(damage_multiplier(50, 39.0), 1.0)

    @covers_requirement("monster-ai-effect-estimation::damage-estimates-use-settlement-arithmetic-without-settlement")
    def test_the_margin_is_the_roll_plus_agility_over_the_defender_threshold(self):
        # 51 is the rulebook's defender constant: this roll lands exactly.
        self.assertEqual(
            hit_margin(
                51,
                attacker_agility=0.0,
                attacker_accuracy=0.0,
                defender_agility=0.0,
            ),
            0.0,
        )
        self.assertTrue(strike_lands(0.0))
        self.assertFalse(strike_lands(-0.5))
        self.assertEqual(
            hit_margin(
                50,
                attacker_agility=10.0,
                attacker_accuracy=2.0,
                defender_agility=5.0,
            ),
            6.0,
        )

    @covers_requirement("monster-ai-effect-estimation::damage-estimates-use-settlement-arithmetic-without-settlement")
    def test_the_strike_amount_composes_potency_defense_rider_and_scale(self):
        # 30 x 1.0 x 2.0 rounds to 60, minus 10 defense.
        self.assertEqual(
            strike_amount(attack=30.0, multiplier=1.0, coefficient=2.0, defense=10.0),
            50,
        )
        # Half of the same solid hit: round(30 x 1.5) = 45, minus 10, halved.
        self.assertEqual(
            strike_amount(
                attack=30.0, multiplier=1.5, coefficient=1.0, defense=10.0, scale=0.5
            ),
            18,
        )
        # A hit below the floor still lands the rulebook's minimum.
        self.assertEqual(
            strike_amount(attack=1.0, multiplier=1.0, coefficient=1.0, defense=10.0),
            1,
        )
        # The devastation rider is added after the defense subtraction.
        self.assertEqual(
            strike_amount(
                attack=10.0,
                multiplier=1.0,
                coefficient=1.0,
                defense=10.0,
                rider=4,
            ),
            4,
        )

    @covers_requirement("monster-ai-effect-estimation::damage-estimates-use-settlement-arithmetic-without-settlement")
    def test_the_heal_amount_is_floored_and_amplified_in_that_order(self):
        self.assertEqual(heal_amount(magic_power=35.0), 35)
        self.assertEqual(heal_amount(magic_power=1.0, coefficient=0.01), 1)
        # round(33 x 2.0) = 66, then +15% with floor rounding, never banker's.
        self.assertEqual(
            heal_amount(magic_power=33.0, coefficient=2.0, heal_gain="+15%"), 75
        )

    @covers_requirement("monster-ai-effect-estimation::damage-estimates-use-settlement-arithmetic-without-settlement")
    def test_the_capacity_caps_and_the_floor_are_the_settlement_ones(self):
        self.assertEqual(staged_restoration(amount=10, current=5.0, maximum=8.0), 3)
        self.assertEqual(staged_restoration(amount=10, current=0.0, maximum=8.0), 0)
        self.assertTrue(crosses_knockout(current=10.0, loss=12.0))
        self.assertEqual(nonlethal_projection(current=10.0, loss=12.0), 1.0)
        self.assertFalse(crosses_knockout(current=10.0, loss=4.0))
        self.assertEqual(nonlethal_projection(current=10.0, loss=4.0), 6.0)

    @covers_requirement("monster-ai-effect-estimation::damage-estimates-use-settlement-arithmetic-without-settlement")
    def test_the_settlement_handlers_stage_the_shared_expressions(self):
        attacker = FakeEntity("actor", atk_phys=30, agility=0, magic_power=11)
        defender = FakeEntity("target", defense=10, agility=0)
        for face in (1, 50, 51, 91, 100):
            self.assertEqual(
                _roll_multiplier(face, face - 51),
                damage_multiplier(face, face - 51),
            )
            self.assertEqual(
                _to_hit(attacker, defender, face),
                (strike_lands(face - 51), float(face - 51)),
            )
        # The heal handler's staging cap is the shared expression too.
        self.assertEqual(
            _restored_amount(defender, 10),
            staged_restoration(
                amount=10,
                current=float(defender.traits.hp._data["current"]),
                maximum=float(defender.traits.hp._data["base"]),
            ),
        )


class SpreadProjectionTests(unittest.TestCase):
    """The analytic spread, its gates, its caps and its honest labels."""

    def setUp(self):
        _scope(self)
        _suppress_innate_skills(self)
        self.actor = _ProbeParticipant("t_est_actor", skills=(STRIKE.key,))
        self.enemy = _ProbeParticipant("t_est_enemy", pk=7)
        # A clean spread: the roll alone decides, so faces 51..90 are base hits,
        # 91..99 are solid hits and the hundredth face is the critical one.
        _set(self.actor, "magic_power", 30)
        _set(self.actor, "agility", 0)
        _set(self.actor, "hp", 40, current=40)
        _set(self.enemy, "defense", 10)
        _set(self.enemy, "agility", 0)
        _set(self.enemy, "hp", 30, current=30)

    @covers_requirement("monster-ai-effect-estimation::damage-estimates-use-settlement-arithmetic-without-settlement")
    @covers_requirement("monster-ai-effect-estimation::health-and-resource-features-are-bounded-and-signed")
    def test_one_strike_averages_the_range_inside_every_capacity_branch(self):
        # Faces 1..50 miss; 51..90 land round(30) - 10 = 20; 91..99 land
        # round(45) - 10 = 35; face 100 crits for round(60) - 10 = 50. Capped by
        # the enemy's 30 health, the solid and critical branches lose 30, so the
        # average actual loss is (40 x 20 + 9 x 30 + 30) / 100 = 11.0 -- not the
        # 11.65 the uncapped average of the range would claim.
        estimate = _only(_estimate(self.actor, (self.enemy,)))
        projection = _recipient(estimate, self.enemy)
        self.assertAlmostEqual(projection.damage, 11.0)
        self.assertAlmostEqual(projection.nominal_damage, 11.65)
        # Ten faces reach zero health, so the knockout likelihood is ten percent.
        self.assertAlmostEqual(projection.finishing, 0.10)
        self.assertAlmostEqual(estimate.finishing, 0.10)
        self.assertAlmostEqual(estimate.damage.magnitude, 11.0 / 30)
        self.assertEqual(estimate.damage.direction.name, "BENEFIT")
        # The wasted overkill is exactly the nominal effect capacity refused.
        self.assertAlmostEqual(estimate.waste.magnitude, 0.65 / 11.65)
        self.assertEqual(estimate.waste.direction.name, "HARM")
        # The template charges twelve mana of the actor's twenty.
        self.assertAlmostEqual(estimate.cost, 0.6)
        self.assertEqual(_deltas(estimate, self.actor)["mp"], -12.0)

    @covers_requirement("monster-ai-effect-estimation::damage-estimates-use-settlement-arithmetic-without-settlement")
    def test_a_two_strike_occurrence_caps_the_sum_not_the_average(self):
        # Each strike lands half the time for 10, 20 or 30 damage on a 5-health
        # target, so any landing strike already crosses it. Averaging the capped
        # sums gives 0.75 x 5 = 3.75; capping the summed average afterwards
        # would claim the full 5.
        _owned(self.actor, TWIN.key)
        _set(self.actor, "magic_power", 20)
        _set(self.enemy, "defense", 10)
        _set(self.enemy, "hp", 5, current=5)
        estimate = _only(_estimate(self.actor, (self.enemy,)))
        projection = _recipient(estimate, self.enemy)
        self.assertAlmostEqual(projection.damage, 3.75)
        self.assertAlmostEqual(projection.finishing, 0.75)
        self.assertEqual(estimate.classification, ApproximationClass.CONSERVATIVE)
        self.assertIn(EstimationLimit.HIT_REACTIONS_UNMODELED, estimate.limits)

    @covers_requirement("monster-ai-effect-estimation::damage-estimates-use-settlement-arithmetic-without-settlement")
    def test_ordered_occurrences_bill_the_remaining_health_once(self):
        # Two identical 30.1-average occurrences against 50 health: every branch
        # of the second acts on what the first left, so the total is the 50
        # health that existed, never the 60.2 the two nominal amounts claim.
        _owned(self.actor, DOUBLE.key)
        _set(self.actor, "magic_power", 20)
        _set(self.actor, "agility", 90)
        _set(self.enemy, "defense", 0)
        _set(self.enemy, "agility", 0)
        _set(self.enemy, "hp", 50, current=50)
        estimate = _only(_estimate(self.actor, (self.enemy,)))
        projection = _recipient(estimate, self.enemy)
        self.assertAlmostEqual(projection.damage, 50.0)
        self.assertAlmostEqual(projection.nominal_damage, 60.2)
        self.assertAlmostEqual(projection.finishing, 1.0)
        self.assertAlmostEqual(estimate.waste.magnitude, 10.2 / 60.2)

    @covers_requirement("monster-ai-effect-estimation::uncertain-effects-have-conservative-explicit-limits")
    def test_a_recipient_floor_caps_the_loss_at_one_stored_point(self):
        _owned(self.actor, DOUBLE.key)
        _set(self.actor, "magic_power", 20)
        _set(self.actor, "agility", 90)
        _set(self.enemy, "defense", 0)
        _set(self.enemy, "agility", 0)
        _set(self.enemy, "hp", 20, current=20)
        protected = _only(
            _estimate(
                self.actor,
                (self.enemy,),
                event_context={"nonlethal_keys": frozenset({self.enemy.key})},
            )
        )
        lethal = _only(_estimate(self.actor, (self.enemy,)))
        self.assertAlmostEqual(_recipient(protected, self.enemy).damage, 19.0)
        self.assertAlmostEqual(_recipient(lethal, self.enemy).damage, 20.0)
        self.assertIn(EstimationLimit.NONLETHAL_FLOOR_APPLIED, protected.limits)
        self.assertNotIn(EstimationLimit.NONLETHAL_FLOOR_APPLIED, lethal.limits)

    @covers_requirement("monster-ai-effect-estimation::damage-estimates-use-settlement-arithmetic-without-settlement")
    def test_a_hit_dependent_effect_reads_the_occurrences_own_gate(self):
        # Both rows land half the time per strike for a ten-mana request. The
        # one-strike row drains 0.5 x 10 = 5. The two-strike row's dependent
        # drain reads that occurrence's one shared gate, 1 - 0.5^2 = 0.75, so it
        # drains 7.5: reading a second independent roll would give 5 again, and
        # re-rolling per strike would give 10.
        for key, enemy_delta, actor_delta in (
            (DRAIN.key, -5.0, -5.0),
            (DRAIN_TWIN.key, -7.5, -2.5),
        ):
            with self.subTest(skill=key):
                _owned(self.actor, key)
                _set(self.actor, "agility", 0)
                _set(self.actor, "mp", 100, current=20)
                _set(self.actor, "magic_power", 20)
                _set(self.enemy, "defense", 10)
                _set(self.enemy, "agility", 0)
                _set(self.enemy, "hp", 100, current=100)
                _set(self.enemy, "mp", 100, current=20)
                estimate = _only(_estimate(self.actor, (self.enemy,)))
                self.assertAlmostEqual(
                    _deltas(estimate, self.enemy)["mp"], enemy_delta
                )
                # Twenty mana, the drain's credit, then the ten-mana cost.
                self.assertAlmostEqual(
                    _deltas(estimate, self.actor)["mp"], actor_delta
                )
                self.assertIn(EstimationLimit.GATED_EFFECT_WEIGHTED, estimate.limits)

    @covers_requirement("monster-ai-effect-estimation::uncertain-effects-have-conservative-explicit-limits")
    def test_a_full_share_drain_credits_the_projected_actual_removal(self):
        # A target holding three mana, a ten-mana request and a full recovery
        # share, with the actor at twenty mana and a ten-mana cost: crediting
        # the request rather than the actual removal would leave the actor
        # above 13, and it would credit a recovery the target never lost.
        _owned(self.actor, DRAIN.key)
        _set(self.actor, "agility", 90)
        _set(self.actor, "magic_power", 20)
        _set(self.actor, "mp", 100, current=20)
        _set(self.enemy, "agility", 0)
        _set(self.enemy, "defense", 0)
        _set(self.enemy, "hp", 100, current=100)
        _set(self.enemy, "mp", 3, current=3)
        estimate = _only(_estimate(self.actor, (self.enemy,)))
        self.assertEqual(_deltas(estimate, self.enemy)["mp"], -3.0)
        self.assertEqual(_deltas(estimate, self.actor)["mp"], -7.0)
        self.assertNotIn(EstimationLimit.GATED_EFFECT_WEIGHTED, estimate.limits)

    @covers_requirement("monster-ai-effect-estimation::uncertain-effects-have-conservative-explicit-limits")
    def test_a_missed_prerequisite_credits_nothing_at_all(self):
        # The actor can never land on this defender, so the occurrence's gate
        # never opens: the dependent drain credits no recovery, and nothing
        # lands, so both health features stay empty.
        _owned(self.actor, DRAIN.key)
        _set(self.actor, "agility", 0)
        _set(self.actor, "magic_power", 20)
        _set(self.actor, "mp", 100, current=20)
        _set(self.enemy, "agility", 400)
        _set(self.enemy, "hp", 100, current=100)
        _set(self.enemy, "mp", 100, current=20)
        estimate = _only(_estimate(self.actor, (self.enemy,)))
        self.assertNotIn("mp", _deltas(estimate, self.enemy))
        self.assertEqual(_deltas(estimate, self.actor)["mp"], -10.0)
        self.assertAlmostEqual(estimate.damage.magnitude, 0.0)
        self.assertAlmostEqual(estimate.healing.magnitude, 0.0)
        self.assertAlmostEqual(_recipient(estimate, self.enemy).damage, 0.0)

    @covers_requirement("monster-ai-effect-estimation::uncertain-effects-have-conservative-explicit-limits")
    def test_a_recovery_is_clamped_before_the_cost_is_deducted(self):
        # Settlement applies the staged effects first and the payment last, so a
        # full pool absorbs the credit into its own bound before the cost comes
        # out of it: a twenty-mana maximum leaves ten, never thirteen.
        _owned(self.actor, DRAIN.key)
        _set(self.actor, "agility", 90)
        _set(self.actor, "magic_power", 20)
        _set(self.actor, "mp", 20, current=20)
        _set(self.enemy, "agility", 0)
        _set(self.enemy, "defense", 0)
        _set(self.enemy, "hp", 100, current=100)
        _set(self.enemy, "mp", 3, current=3)
        estimate = _only(_estimate(self.actor, (self.enemy,)))
        self.assertEqual(_deltas(estimate, self.actor)["mp"], -10.0)

    @covers_requirement("monster-ai-effect-estimation::uncertain-effects-have-conservative-explicit-limits")
    def test_a_known_diversion_budget_reduces_the_estimate(self):
        # The recipient's live diversion absorbs the authored fraction of each
        # landing strike's residual, clamped by what is left of its budget and
        # by the pool it pays from; a spent budget absorbs nothing.
        _owned(self.actor, STRIKE.key)
        _set(self.actor, "magic_power", 20)
        _set(self.actor, "agility", 90)
        _set(self.enemy, "defense", 0)
        _set(self.enemy, "agility", 0)
        _set(self.enemy, "hp", 100, current=100)
        _set(self.enemy, "mp", 100, current=100)
        absorbed = lambda residual: min(  # noqa: E731  (one readable local rule)
            round(residual * DIVERT_SPEC["fraction"]), DIVERT_SPEC["cap"], 100
        )
        expected = (99 * absorbed(30) + absorbed(40)) / 100
        self.enemy.attributes.values["buffs"] = {
            DIVERT_KEY: {**_buff_record(DIVERT_KEY), "divert_consumed": 0}
        }
        shielded = _only(_estimate(self.actor, (self.enemy,)))
        self.assertAlmostEqual(_recipient(shielded, self.enemy).damage, 30.1 - expected)
        # The budget is spent in whole points once for the occurrence.
        self.assertEqual(
            _deltas(shielded, self.enemy)["mp"], -float(int(round(expected)))
        )
        self.assertIn(EstimationLimit.DIVERSION_ABSORBED, shielded.limits)
        self.enemy.attributes.values["buffs"] = {
            DIVERT_KEY: {
                **_buff_record(DIVERT_KEY),
                "divert_consumed": DIVERT_SPEC["cap"],
            }
        }
        spent = _only(_estimate(self.actor, (self.enemy,)))
        self.assertAlmostEqual(_recipient(spent, self.enemy).damage, 30.1)
        self.assertNotIn(EstimationLimit.DIVERSION_ABSORBED, spent.limits)

    @covers_requirement("monster-ai-effect-estimation::health-and-resource-features-are-bounded-and-signed")
    def test_allied_healing_moves_the_feature_the_other_way(self):
        _owned(self.actor, WARD.key)
        _set(self.actor, "hp", 40, current=30)
        _set(self.actor, "magic_power", 10)
        _set(self.actor, "agility", 90)
        _set(self.enemy, "hp", 100, current=100)
        _set(self.enemy, "defense", 0)
        _set(self.enemy, "agility", 0)
        estimate = _widest(_estimate(self.actor, (self.enemy,)), WARD.key)
        # The heal stages against the actor's pre-action gap of ten, so at most
        # ten of it is ever useful, and the feature is that gap over the ally
        # faction's capacity.
        self.assertAlmostEqual(_recipient(estimate, self.actor).healing, 10.0)
        self.assertAlmostEqual(estimate.healing.magnitude, 10.0 / 40)
        self.assertEqual(estimate.healing.direction.name, "BENEFIT")

    @covers_requirement("monster-ai-effect-estimation::health-and-resource-features-are-bounded-and-signed")
    def test_enemy_healing_is_a_harm(self):
        _owned(self.actor, FOE_MEND.key)
        _set(self.actor, "magic_power", 10)
        _set(self.actor, "agility", 90)
        _set(self.enemy, "hp", 100, current=50)
        _set(self.enemy, "defense", 0)
        _set(self.enemy, "agility", 0)
        estimate = _widest(_estimate(self.actor, (self.enemy,)), FOE_MEND.key)
        self.assertGreater(_recipient(estimate, self.enemy).healing, 0.0)
        self.assertEqual(estimate.healing.direction.name, "HARM")

    @covers_requirement("monster-ai-effect-estimation::damage-estimates-use-settlement-arithmetic-without-settlement")
    @covers_requirement("monster-ai-effect-estimation::health-and-resource-features-are-bounded-and-signed")
    def test_a_staged_heal_never_exceeds_the_pre_action_gap(self):
        _owned(self.actor, PENANCE.key)
        _set(self.actor, "magic_power", 10)
        _set(self.actor, "agility", 90)
        _set(self.actor, "hp", 40, current=40)
        _set(self.enemy, "hp", 100, current=100)
        _set(self.enemy, "defense", 0)
        _set(self.enemy, "agility", 0)
        estimate = _only(_estimate(self.actor, (self.enemy,)))
        # A full-health actor stages no restoration at all, even though the very
        # same action damages the enemy in front of it.
        self.assertEqual(_recipient(estimate, self.actor).healing, 0.0)
        self.assertGreater(_recipient(estimate, self.enemy).damage, 0.0)

    @covers_requirement("monster-ai-effect-estimation::health-and-resource-features-are-bounded-and-signed")
    def test_own_side_damage_is_a_negative_term(self):
        _owned(self.actor, WARD.key)
        _set(self.actor, "hp", 40, current=40)
        _set(self.actor, "magic_power", 10)
        _set(self.actor, "agility", 90)
        _set(self.enemy, "hp", 100, current=100)
        _set(self.enemy, "defense", 0)
        _set(self.enemy, "agility", 0)
        # The complete roster is the plan whose own-side damage is largest: the
        # selected-audience damage reaches the actor as well as the enemy.
        row = replace(
            WARD,
            key="t_est_broad",
            effect_policies=(EffectPolicy(), EffectPolicy(audience=EffectAudience.ALLIES)),
        )
        _owned(self.actor, row.key)
        with patch.dict("world.skills.registry.SKILL_REGISTRY", {row.key: row}):
            estimate = _widest(_estimate(self.actor, (self.enemy,)), row.key)
        own_loss = _recipient(estimate, self.actor).damage
        enemy_loss = _recipient(estimate, self.enemy).damage
        self.assertGreater(own_loss, 0.0)
        # The feature is the enemy loss over the enemy faction's capacity minus
        # the own-side loss over the ally faction's capacity, so the plan's own
        # damage measurably lowers it.
        self.assertAlmostEqual(
            estimate.damage.magnitude, enemy_loss / 100.0 - own_loss / 40.0
        )
        self.assertLess(estimate.damage.magnitude, enemy_loss / 100.0)

    @covers_requirement("monster-ai-effect-estimation::uncertain-effects-have-conservative-explicit-limits")
    def test_an_unvaluable_harm_is_refused_instead_of_zeroed(self):
        _owned(self.actor, SELF_HARM.key)
        estimate = _only(_estimate(self.actor, (self.enemy,)))
        self.assertIsInstance(estimate, InvalidEstimate)
        self.assertEqual(
            estimate.reason, InvalidEstimateReason.UNSUPPORTED_HARMFUL_OUTCOME
        )
        self.assertIn("friendly recipient", estimate.detail)

    @covers_requirement("monster-ai-effect-estimation::uncertain-effects-have-conservative-explicit-limits")
    def test_a_hostile_benefit_is_refused_too(self):
        _owned(self.actor, FOE_WARD.key)
        estimate = _only(_estimate(self.actor, (self.enemy,)))
        self.assertIsInstance(estimate, InvalidEstimate)
        self.assertIn("hostile recipient", estimate.detail)

    @covers_requirement("monster-ai-effect-estimation::uncertain-effects-have-conservative-explicit-limits")
    def test_an_enemy_side_status_is_unvalued_but_never_refused(self):
        _owned(self.actor, CURSED.key)
        estimate = _only(_estimate(self.actor, (self.enemy,)))
        self.assertNotIsInstance(estimate, InvalidEstimate)
        self.assertTrue(estimate.diagnostics)
        self.assertIn(EstimationLimit.UNMODELED_BENEFIT_ZERO, estimate.limits)
        self.assertGreater(_recipient(estimate, self.enemy).damage, 0.0)

    @covers_requirement("monster-ai-effect-estimation::uncertain-effects-have-conservative-explicit-limits")
    def test_a_candidate_that_takes_from_a_friend_is_refused_while_others_survive(self):
        _owned(self.actor, FRIEND_LEECH.key)
        estimates = _estimate(self.actor, (self.enemy,))
        reasons = [
            item.reason
            for item in estimates.estimates
            if isinstance(item, InvalidEstimate)
        ]
        self.assertEqual(reasons, [InvalidEstimateReason.UNSUPPORTED_HARMFUL_OUTCOME])
        self.assertTrue(
            any(not isinstance(item, InvalidEstimate) for item in estimates.estimates)
        )

    @covers_requirement("monster-ai-effect-estimation::health-and-resource-features-are-bounded-and-signed")
    def test_a_non_finite_read_is_a_typed_state_not_an_exception(self):
        _owned(self.actor, STRIKE.key)
        # A non-finite number reaches the estimator only through a read, and the
        # settlement rulebook already forbids one anywhere else: the boundary is
        # exercised here through the decision read the estimator consumes.
        for bad in (float("inf"), float("nan")):
            with self.subTest(value=bad):
                with patch.object(
                    DecisionReads,
                    "modifiers",
                    lambda _self, _entity, bad=bad: {
                        "accuracy": bad,
                        "actions_per_turn": 1,
                    },
                ):
                    estimate = _only(_estimate(self.actor, (self.enemy,)))
                self.assertIsInstance(estimate, InvalidEstimate)
                self.assertEqual(
                    estimate.reason, InvalidEstimateReason.NON_FINITE_FEATURE
                )
                self.assertIn("accuracy", estimate.detail)

    @covers_requirement("monster-ai-effect-estimation::damage-estimates-use-settlement-arithmetic-without-settlement")
    def test_the_estimate_rolls_nothing_mounts_nothing_and_writes_nothing(self):
        _owned(self.actor, STRIKE.key)
        before = {
            label: {key: dict(record) for key, record in probe.attributes.values.items()}
            for label, probe in (("actor", self.actor), ("enemy", self.enemy))
        }
        with (
            patch("world.rules.dice.roll_d100", side_effect=AssertionError("dice")),
            patch(
                "world.rules.combat.damage.roll_d100",
                side_effect=AssertionError("dice"),
            ),
            patch.object(
                ActionResolver, "resolve", side_effect=AssertionError("settlement")
            ),
        ):
            estimate = _only(_estimate(self.actor, (self.enemy,)))
        self.assertNotIsInstance(estimate, InvalidEstimate)
        for label, probe in (("actor", self.actor), ("enemy", self.enemy)):
            stored = {
                key: dict(record) for key, record in probe.attributes.values.items()
            }
            self.assertEqual(stored, before[label])

    @covers_requirement("monster-ai-effect-estimation::uncertain-effects-have-conservative-explicit-limits")
    def test_an_evidence_conditional_strike_is_not_credited(self):
        _owned(self.actor, CONDITIONAL.key)
        estimate = _only(_estimate(self.actor, (self.enemy,)))
        self.assertIn(EstimationLimit.EVIDENCE_STRIKE_UNCREDITED, estimate.limits)
        # The unconditional strike is still modeled, so the row keeps a body.
        self.assertAlmostEqual(_recipient(estimate, self.enemy).damage, 11.0)

    @covers_requirement("monster-ai-effect-estimation::uncertain-effects-have-conservative-explicit-limits")
    def test_a_plan_that_omits_nothing_classifies_as_exact(self):
        _set(self.actor, "magic_power", 10)
        _set(self.actor, "hp", 40, current=30)
        snapshot, reads, roster, context = _shaped(self.actor, (self.enemy,))
        estimate = estimate_plan(
            _hand(MEND, (self.actor,), ((self.actor,),)),
            snapshot=snapshot,
            actor=self.actor,
            context=context,
            roster=roster,
            reads=reads,
        )
        self.assertNotIsInstance(estimate, InvalidEstimate)
        self.assertEqual(estimate.classification, ApproximationClass.EXACT)
        self.assertEqual(estimate.limits, ())
        self.assertAlmostEqual(_recipient(estimate, self.actor).healing, 10.0)


class ScaleGateAndPoolTests(unittest.TestCase):
    """The clauses the estimate must establish beyond one plain strike."""

    def setUp(self):
        _scope(self)
        _suppress_innate_skills(self)
        self.actor = _ProbeParticipant("t_est_actor", skills=(STRIKE.key,))
        self.enemy = _ProbeParticipant("t_est_enemy", pk=7)
        _set(self.actor, "magic_power", 30)
        _set(self.actor, "agility", 0)
        _set(self.actor, "hp", 40, current=40)
        _set(self.actor, "mp", 100, current=20)
        _set(self.enemy, "defense", 10)
        _set(self.enemy, "agility", 0)
        _set(self.enemy, "hp", 100, current=100)

    def _plan(self, skill, recipients, routed, *, scale=1.0):
        """Estimate one hand-built plan over the probe participants."""
        snapshot, reads, roster, context = _shaped(self.actor, (self.enemy,))
        return estimate_plan(
            _hand(skill, recipients, routed, scale=scale),
            snapshot=snapshot,
            actor=self.actor,
            context=context,
            roster=roster,
            reads=reads,
        )

    @covers_requirement("monster-ai-effect-estimation::damage-estimates-use-settlement-arithmetic-without-settlement")
    def test_a_non_default_scale_scales_the_effects_and_their_cost(self):
        # Faces 1..50 miss; 51..90 land round(30) - 10 = 20, 91..99 land
        # round(45) - 10 = 35 and face 100 crits for 50. Halved, the same faces
        # land 10, 18 and 25, so the expected loss is (400 + 162 + 25) / 100 =
        # 5.87 while the twelve-mana cost is charged as six.
        estimate = self._plan(STRIKE, (self.enemy,), ((self.enemy,),), scale=0.5)
        self.assertNotIsInstance(estimate, InvalidEstimate)
        self.assertAlmostEqual(_recipient(estimate, self.enemy).damage, 5.87)
        self.assertAlmostEqual(estimate.cost, 6.0 / 20.0)

    @covers_requirement("monster-ai-effect-estimation::damage-estimates-use-settlement-arithmetic-without-settlement")
    @covers_requirement("monster-ai-effect-estimation::uncertain-effects-have-conservative-explicit-limits")
    def test_a_gated_damage_occurrence_is_omitted_rather_than_marginalized(self):
        # The second occurrence reads the first one's gate, so half the time it
        # would act on a recipient the first already hit. Crediting it on every
        # branch would overstate the plan, so it is omitted and reported: the
        # estimate is the first occurrence's own range alone.
        estimate = self._plan(GATED, (self.enemy,), ((self.enemy,), (self.enemy,)))
        self.assertAlmostEqual(_recipient(estimate, self.enemy).damage, 11.65)
        self.assertIn(EstimationLimit.GATED_EFFECT_OMITTED, estimate.limits)

    @covers_requirement("monster-ai-effect-estimation::damage-estimates-use-settlement-arithmetic-without-settlement")
    def test_independent_drain_gates_sum_rather_than_multiply(self):
        # Two enemies, each holding ten mana and each reached half the time by
        # the damage occurrence its drain depends on: the actor recovers
        # 0.5 x 10 from each of them, ten in all. Multiplying the gates would
        # claim only 2.5, and one closed gate would erase the other's removal.
        second = _ProbeParticipant("t_est_second", pk=8)
        for target in (self.enemy, second):
            _set(target, "mp", 30, current=10)
            _set(target, "defense", 10)
            _set(target, "agility", 0)
        _owned(self.actor, SIPHON.key)
        snapshot, reads, roster, context = _shaped(self.actor, (self.enemy, second))
        estimates = estimate_candidates(
            enumerate_candidates(
                snapshot,
                actor=self.actor,
                context=context,
                roster=roster,
                reads=reads,
            ),
            snapshot=snapshot,
            actor=self.actor,
            context=context,
            roster=roster,
            reads=reads,
        )
        estimate = _pick(estimates, SIPHON.key)
        self.assertAlmostEqual(_deltas(estimate, self.enemy)["mp"], -5.0)
        self.assertAlmostEqual(_deltas(estimate, second)["mp"], -5.0)
        self.assertAlmostEqual(_deltas(estimate, self.actor)["mp"], -2.0)

    @covers_requirement("monster-ai-effect-estimation::damage-estimates-use-settlement-arithmetic-without-settlement")
    @covers_requirement("monster-ai-effect-estimation::uncertain-effects-have-conservative-explicit-limits")
    def test_a_health_drain_credits_only_the_projected_loss(self):
        # The actor starts ten points below its maximum, so a five-point health
        # drain against a healthy recipient credits five. Against a recipient
        # the same action has already emptied, the drain removes nothing and so
        # credits nothing at all.
        _set(self.actor, "hp", 40, current=30)
        _set(self.actor, "agility", 90)
        _set(self.enemy, "defense", 0)
        drained = self._plan(BLOOD, (self.enemy,), ((self.enemy,), (self.enemy,)))
        self.assertAlmostEqual(_deltas(drained, self.actor)["hp"], 5.0)
        self.assertAlmostEqual(
            _recipient(drained, self.enemy).damage, 45.15 + 5.0
        )
        _set(self.enemy, "hp", 2, current=2)
        spent = self._plan(BLOOD, (self.enemy,), ((self.enemy,), (self.enemy,)))
        self.assertNotIn("hp", _deltas(spent, self.actor))
        self.assertAlmostEqual(_recipient(spent, self.enemy).damage, 2.0)
        # Nothing was removed, so nothing was credited: the actor has no
        # health projection in this plan at all.
        identities = {item.identity for item in spent.recipients}
        self.assertNotIn(stable_identity(self.actor), identities)

    @covers_requirement("monster-ai-effect-estimation::damage-estimates-use-settlement-arithmetic-without-settlement")
    def test_a_same_recipient_heal_gets_no_fresh_allowance(self):
        # The restoration is staged against the recipient's *pre-action* gap, so
        # an enemy at full health stages nothing even though the same action
        # damages it first -- the nominal heal never becomes a healing point.
        _owned(self.actor, FOE_MEND.key)
        _set(self.actor, "agility", 90)
        estimate = _widest(_estimate(self.actor, (self.enemy,)), FOE_MEND.key)
        projection = _recipient(estimate, self.enemy)
        self.assertGreater(projection.damage, 0.0)
        self.assertEqual(projection.healing, 0.0)
        self.assertGreater(projection.nominal_healing, 0.0)

    @covers_requirement("monster-ai-effect-estimation::health-and-resource-features-are-bounded-and-signed")
    def test_the_cost_feature_spans_every_charged_pool(self):
        # Two charged pools make the feature their mean: ten of twenty mana and
        # four of twenty stamina is 0.35. A pool holding nothing contributes
        # zero rather than an infinite fraction, so the same row over an empty
        # stamina pool is 0.25.
        measured = self._plan(COSTLY, (self.enemy,), ((self.enemy,),))
        self.assertAlmostEqual(measured.cost, (0.5 + 0.2) / 2)
        _set(self.actor, "sp", 20, current=0)
        empty = self._plan(COSTLY, (self.enemy,), ((self.enemy,),))
        self.assertAlmostEqual(empty.cost, 0.5 / 2)

    @covers_requirement("monster-ai-effect-estimation::uncertain-effects-have-conservative-explicit-limits")
    def test_an_unclassified_own_side_outcome_is_refused(self):
        # Revoking grants from the actor's own side takes something away, and
        # this model does not know that class's outcome: the plan is refused
        # rather than valued at zero.
        estimate = self._plan(
            STRIPPED, (self.enemy,), ((self.enemy,), (self.actor,))
        )
        self.assertIsInstance(estimate, InvalidEstimate)
        self.assertEqual(
            estimate.reason, InvalidEstimateReason.UNSUPPORTED_HARMFUL_OUTCOME
        )
        self.assertIn("friendly recipient", estimate.detail)

    @covers_requirement("monster-ai-effect-estimation::uncertain-effects-have-conservative-explicit-limits")
    def test_cleansing_a_hostile_recipient_is_refused(self):
        # A cleanse removes its recipient's debuffs, which on a hostile
        # recipient hands the enemy a benefit the estimate cannot value.
        estimate = self._plan(
            PURGED, (self.enemy,), ((self.enemy,), (self.enemy,))
        )
        self.assertIsInstance(estimate, InvalidEstimate)
        self.assertIn("hostile recipient", estimate.detail)


class EstimationIntegrationTests(EvenniaTestCase):
    """The estimate against real, committed settlement."""

    def setUp(self):
        _scope(self)
        super().setUp()
        self.room = create_object(Room, key="estimation arena")
        self.monster = _monster("t_est_monster")
        self.monster.location = self.room
        self.monster.traits.mp.base = 100
        self.monster.traits.mp.current = 20

    def _participant(self, key, hp=500, mp=100):
        entity = _player(key)
        entity.location = self.room
        entity.traits.hp.base = hp
        entity.traits.hp.current = hp
        entity.traits.mp.base = mp
        entity.traits.mp.current = mp
        return entity

    def _field(self, *opponents):
        roster = {str(self.monster.key): self.monster}
        for entity in opponents:
            roster[str(entity.key)] = entity
        return Battlefield(
            {
                "monsters": frozenset({str(self.monster.key)}),
                "party": frozenset(str(entity.key) for entity in opponents),
            },
            roster,
        )

    def _estimate(self, target, skill_key):
        """One decision's estimate for one owned skill."""
        context = BattlefieldActionContext(self._field(target))
        reads = DecisionReads()
        snapshot = build_decision_snapshot(
            self.monster,
            context,
            scope=DecisionScope(SCOPE, ROUND, 0),
            participants=(target,),
            reads=reads,
        )
        roster = roster_index((self.monster, target))
        candidates = enumerate_candidates(
            snapshot,
            actor=self.monster,
            context=context,
            roster=roster,
            reads=reads,
        )
        estimates = estimate_candidates(
            candidates,
            snapshot=snapshot,
            actor=self.monster,
            context=context,
            roster=roster,
            reads=reads,
        )
        return context, _pick(estimates, skill_key)

    def _committed(self, entity, trait_key) -> float:
        """One entity's committed gauge value, read back from a fresh row."""
        return float(
            ObjectDB.objects.get(id=entity.pk)
            .attributes.get("traits", default={}, category="traits")[trait_key]["current"]
        )

    @covers_requirement("monster-ai-effect-estimation::damage-estimates-use-settlement-arithmetic-without-settlement")
    def test_the_estimate_matches_the_settled_range_over_every_face(self):
        self.monster.db.skills = {"active": [STRIKE.key], "passive": []}
        self.monster.traits.atk_phys.base = 40
        self.monster.traits.magic_power.base = 40
        self.monster.traits.agility.base = 10
        target = self._participant("t_est_target", hp=500)
        target.traits.defense.base = 10
        target.traits.agility.base = 20
        context, estimate = self._estimate(target, STRIKE.key)
        self.assertNotIsInstance(estimate, InvalidEstimate)
        projection = _recipient(estimate, target)
        settled = 0.0
        for face in range(1, 101):
            target.traits.hp.current = 500
            self.monster.traits.mp.current = 20
            with patch("world.rules.combat.damage.roll_d100", return_value=face):
                result = ActionResolver.resolve(
                    ActionRequest(self.monster, STRIKE.key, [target], context, scale=1.0)
                )
            self.assertEqual(result.outcome, "success", result.detail)
            settled += 500 - self._committed(target, "hp")
        self.assertAlmostEqual(settled / 100, projection.damage, places=4)

    @covers_requirement("monster-ai-effect-estimation::damage-estimates-use-settlement-arithmetic-without-settlement")
    def test_the_drain_projection_matches_the_committed_pools(self):
        self.monster.db.skills = {"active": [DRAIN.key], "passive": []}
        self.monster.traits.magic_power.base = 20
        self.monster.traits.agility.base = 90
        target = self._participant("t_est_target", hp=500, mp=3)
        target.traits.defense.base = 0
        target.traits.agility.base = 0
        context, estimate = self._estimate(target, DRAIN.key)
        self.assertNotIsInstance(estimate, InvalidEstimate)
        with patch("world.rules.combat.damage.roll_d100", return_value=60):
            result = ActionResolver.resolve(
                ActionRequest(self.monster, DRAIN.key, [target], context, scale=1.0)
            )
        self.assertEqual(result.outcome, "success", result.detail)
        self.assertEqual(self._committed(self.monster, "mp"), 13.0)
        self.assertEqual(self._committed(target, "mp"), 0.0)
        self.assertEqual(_deltas(estimate, self.monster)["mp"], -7.0)
        self.assertEqual(_deltas(estimate, target)["mp"], -3.0)


class EstimationTuningTests(unittest.TestCase):
    """The estimator's own rulebook inputs are part of the recorded tuning."""

    @covers_requirement("monster-ai-effect-estimation::uncertain-effects-have-conservative-explicit-limits")
    def test_the_estimation_rulebook_leaves_move_the_fingerprint(self):
        base = behaviour.MONSTER_AI_TUNING.fingerprint
        with patch.dict(COMBAT_YAML["damage"], {"crit_multiplier": 3.0}):
            self.assertNotEqual(
                behaviour._load_ai_tuning(behaviour.MONSTER_BEHAVIOUR_YAML).fingerprint,
                base,
            )
        with patch.dict(COMBAT_YAML["heal"], {"floor": 2}):
            self.assertNotEqual(
                behaviour._load_ai_tuning(behaviour.MONSTER_BEHAVIOUR_YAML).fingerprint,
                base,
            )
        self.assertEqual(
            behaviour._load_ai_tuning(behaviour.MONSTER_BEHAVIOUR_YAML).fingerprint,
            base,
        )


if __name__ == "__main__":
    unittest.main()
