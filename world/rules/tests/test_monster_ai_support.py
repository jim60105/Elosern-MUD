"""Behavior tests for the monster-AI tactical support valuation.

Every fixture here is file-local and synthetic: the ``t_``-named buff
definitions, modifier rules, skills, species, variant and tier rows are built
from the shared kit's factories and templates, and no shipped key, label or
catalog symbol is named by a resolvable literal. The modifier engine, the
shared legality gates and ``ActionResolver`` are the production ones.

The tests establish this slice's contracts: owned healing, supported buffs and
hostile control enter the same bounded candidate pipeline and the same legality
gates, with the mandatory single-target restrictions staying hostile-damage
only; an estimate follows the submitted effect audience plan and never sums an
ally the plan omits; a mount is worth what its projected modifier difference is
over one next action opportunity, so a reapplied, dominated, expired or
opportunity-less mount is worth exactly zero and an unvaluable modifier is
reported instead of invented; the score adds recovery as an unscaled baseline
and control inside the intelligence-scaled term; and the production adapter
selects and settles a real support and a real control action whose recipients
change on committed reload while a bystander does not.
"""

from tools.spec_traceability import covers_requirement

from dataclasses import replace
from math import isclose
from unittest.mock import patch

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.rooms import Room

from world.rules import monster_behaviour as behaviour
from world.rules.action import ActionRequest, ActionResolver, plan_effect_audiences
from world.rules.buffs import BUFF_DEFINITIONS, BuffDefinition, apply_buff
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.combat_modifiers import _RULES, evaluate_combat_modifiers
from world.rules.combat_session.policies import _enemy_policy
from world.rules.combat_session.records import CombatSessionRecord
from world.rules.monster_ai import (
    EstimationLimit,
    DecisionReads,
    DecisionScope,
    PlannedAction,
    build_decision_snapshot,
    enumerate_candidates,
    estimate_candidates,
    estimate_plan,
    roster_index,
    score_candidates,
    stable_identity,
)
from world.rules.monster_ai.candidates import (
    SEAL_BUFF_KEY,
    Candidate,
    CandidateIdentity,
)
from world.rules.monster_ai.estimation import InvalidEstimate
from world.rules.monster_behaviour import (
    BehaviourProfile,
    DecisionMode,
    UtilityWeights,
)
from world.rules.monster_individual import construct_species_individual
from world.rules.rulebook.schema import Rule
from world.skills.effects import EffectAudience, EffectPolicy
from world.skills.registry import TargetSpec
from world.tests.synthetic_data import (
    make_monster_species,
    make_monster_tier,
    make_monster_variant,
)

from ._combat_session_helpers import (
    SYNTH_GLOW_ELEMENT,
    _player,
    open_synthetic_scope,
    synth_damage_skill,
    synth_innate_overlay,
)

SCOPE = "normal:61:0"
ROUND = 61
SPECIES = "t_sup_species"
VARIANT = "t_sup_ordinary"
TIER = "t_sup_tier"
ARCHETYPE = "t_sup_support"
SESSION = "hostile:9:0"
#: Every authored weight, so a test can zero the ones it is not asserting.
WEIGHTS = {name: 1.0 for name in behaviour.UTILITY_WEIGHT_NAMES}

# --- synthetic buff definitions and the rules that give them a value --------
ARMOR_KEY = "t_sup_armor"
STRONG_KEY = "t_sup_strong"
LOCK_KEY = "t_sup_lock"
SLOW_KEY = "t_sup_slow"
CHANCE_KEY = "t_sup_chance"
EMPTY_KEY = "t_sup_empty"
EXPIRED_KEY = "t_sup_expired"
DOT_KEY = "t_sup_dot"
OPAQUE_KEY = "t_sup_opaque"
OPAQUE_MODIFIER = "t_sup_opaque_modifier"

_DEFINITIONS = (
    BuffDefinition(
        key=ARMOR_KEY, duration=60, tick_interval=None, stacking="refresh",
        modifiers={},
    ),
    BuffDefinition(
        key=STRONG_KEY, duration=60, tick_interval=None, stacking="refresh",
        modifiers={},
    ),
    BuffDefinition(
        key=LOCK_KEY, duration=30, tick_interval=None, stacking="refresh",
        polarity="debuff", modifiers={},
    ),
    BuffDefinition(
        key=SLOW_KEY, duration=15, tick_interval=None, stacking="refresh",
        polarity="debuff", modifiers={},
    ),
    BuffDefinition(
        key=CHANCE_KEY, duration=30, tick_interval=None, stacking="refresh",
        polarity="debuff", modifiers={},
    ),
    BuffDefinition(
        key=EMPTY_KEY, duration=60, tick_interval=None, stacking="refresh",
        polarity="debuff", modifiers={},
    ),
    # A declared window that has already run out: no opportunity at all.
    BuffDefinition(
        key=EXPIRED_KEY, duration=0, tick_interval=None, stacking="refresh",
        polarity="debuff", modifiers={},
    ),
    BuffDefinition(
        key=DOT_KEY, duration=60, tick_interval=10, stacking="refresh",
        polarity="debuff", modifiers={"rate": {"target": "hp", "delta": -4}},
    ),
    BuffDefinition(
        key=OPAQUE_KEY, duration=60, tick_interval=None, stacking="refresh",
        polarity="debuff", modifiers={},
    ),
)

_RULES_EXTRA = (
    Rule(id="t_sup_armor_rule", when={"buff_active": ARMOR_KEY}, then={"defense": 5}),
    Rule(
        id="t_sup_strong_rule",
        when={"buff_active": STRONG_KEY},
        then={"defense": 12},
    ),
    Rule(
        id="t_sup_lock_rule",
        when={"buff_active": LOCK_KEY},
        then={"actions_per_turn": 0},
    ),
    Rule(
        id="t_sup_slow_rule",
        when={"buff_active": SLOW_KEY},
        then={"agility_flat": -5},
    ),
    Rule(
        id="t_sup_chance_rule",
        when={"buff_active": CHANCE_KEY},
        then={"actions_per_turn": 0, "chance": 50},
    ),
    Rule(
        id="t_sup_dot_rule",
        when={"buff_active": DOT_KEY},
        then={"accuracy": -5},
    ),
    # A modifier this model has no meaning for: its value must be reported, not
    # invented.
    Rule(
        id="t_sup_opaque_rule",
        when={"buff_active": OPAQUE_KEY},
        then={OPAQUE_MODIFIER: 3},
    ),
)

# --- file-local skill rows --------------------------------------------------
#: A single-target heal: the own-side shape.
HEAL = synth_damage_skill(
    "t_sup_heal", "支援治療", effects=["heal:single"], cost={"mp": 3}
)
#: An area heal: the own-side group shape.
MEND_AREA = synth_damage_skill(
    "t_sup_mend_area",
    "支援群療",
    effects=["heal:area"],
    cost={"mp": 5},
    target_spec=TargetSpec.AREA,
)
#: An area heal whose second effect becomes a friendly mount.
MIXED = replace(
    MEND_AREA,
    key="t_sup_mixed",
    effects=["heal:area", f"buff_apply:{ARMOR_KEY}"],
    effect_policies=(
        EffectPolicy(),
        EffectPolicy(audience=EffectAudience.ALLIES),
    ),
)
#: A friendly single-target mount.
WARD = synth_damage_skill(
    "t_sup_ward", "支援護甲", effects=[f"buff_apply:{ARMOR_KEY}"], cost={"mp": 3}
)
#: The same mount under a definition that projects a weaker change.
WARD_WEAK = replace(WARD, key="t_sup_ward_weak")
#: A hostile single-target lock: the control shape.
LOCK = synth_damage_skill(
    "t_sup_lock_skill", "支援定身", effects=[f"buff_apply:{LOCK_KEY}"], cost={"mp": 3}
)
#: The same lock under a change the model cannot value.
OPAQUE = replace(
    LOCK, key="t_sup_opaque_skill", effects=[f"buff_apply:{OPAQUE_KEY}"]
)
#: A hostile slow: the offense-reduction shape.
SLOW = replace(LOCK, key="t_sup_slow_skill", effects=[f"buff_apply:{SLOW_KEY}"])
#: A hostile lock that only applies half the time.
CHANCE = replace(LOCK, key="t_sup_chance_skill", effects=[f"buff_apply:{CHANCE_KEY}"])
#: A hostile lock whose declared window has run out.
EXPIRED = replace(LOCK, key="t_sup_expired_skill", effects=[f"buff_apply:{EXPIRED_KEY}"])
#: A hostile mount that declares a health effect over time as well.
DOT = replace(LOCK, key="t_sup_dot_skill", effects=[f"buff_apply:{DOT_KEY}"])
#: The actor-bound self heal: the implicit binding shape.
SELF_MEND = replace(
    HEAL, key="t_sup_self_mend", effects=["self_heal"], target_spec=TargetSpec.SELF
)
#: A damage occurrence that pays health and then heals the actor.
PENALTY = synth_damage_skill(
    "t_sup_penalty",
    "支援代價",
    effects=[f"damage:{SYNTH_GLOW_ELEMENT}:magic", "self_heal"],
    cost={"hp": 4},
)
#: The same row without the health payment.
FREE_MEND = replace(PENALTY, key="t_sup_free_mend", cost={"mp": 3})
#: A self heal that only runs when the damage occurrence landed.
ATTENDED = replace(
    synth_damage_skill(
        "t_sup_attended",
        "支援追療",
        effects=[f"damage:{SYNTH_GLOW_ELEMENT}:magic", "self_heal"],
        cost={"mp": 3},
    ),
    effect_policies=(EffectPolicy(), EffectPolicy(requires_hit_from=0)),
)
#: A hostile single-target damage row, for the mandatory-restriction check.
STRIKE = synth_damage_skill(
    "t_sup_strike",
    "支援單體擊",
    effects=[f"damage:{SYNTH_GLOW_ELEMENT}:physical"],
    cost={"mp": 3},
)

_ROWS = (
    HEAL,
    MEND_AREA,
    MIXED,
    WARD,
    WARD_WEAK,
    LOCK,
    OPAQUE,
    SLOW,
    CHANCE,
    EXPIRED,
    DOT,
    SELF_MEND,
    PENALTY,
    FREE_MEND,
    ATTENDED,
    STRIKE,
)

_TIER_ROWS = {TIER: make_monster_tier(TIER)}
_SPECIES_ROWS = {SPECIES: make_monster_species(SPECIES, default_variant_key=VARIANT)}
_VARIANT_ROWS = {
    VARIANT: make_monster_variant(
        VARIANT,
        species_key=SPECIES,
        threat_tier=TIER,
        behaviour_profile_key=ARCHETYPE,
    )
}


def _scope(test, *extra_logicals):
    """Enter the kit scope this module's fixtures need, with its own catalogs."""
    extra = synth_innate_overlay()
    extra["skills"].update({row.key: row for row in _ROWS})
    extra["monster_tiers"] = _TIER_ROWS
    extra["monster_species"] = _SPECIES_ROWS
    extra["monster_variants"] = _VARIANT_ROWS
    buffs = patch.dict(
        BUFF_DEFINITIONS, {row.key: row for row in _DEFINITIONS}, clear=False
    )
    buffs.start()
    test.addCleanup(buffs.stop)
    rules = patch("world.rules.combat_modifiers._RULES", [*_RULES, *_RULES_EXTRA])
    rules.start()
    test.addCleanup(rules.stop)
    return open_synthetic_scope(
        test,
        "monster_tiers",
        "monster_species",
        "monster_variants",
        "races",
        "skills",
        "elements",
        *extra_logicals,
        extra=extra,
    )


def _suppress_innate_skills(test) -> None:
    """Own only the rows a test declares, without the production innate set."""
    patcher = patch("world.skills.handler.INNATE_SKILL_ORDER", ())
    patcher.start()
    test.addCleanup(patcher.stop)


def _field(actor, allies, enemies) -> Battlefield:
    """A two-team battlefield over real participants."""
    roster = {str(entity.key): entity for entity in (actor, *allies, *enemies)}
    return Battlefield(
        {
            "party": frozenset(str(entity.key) for entity in (actor, *allies)),
            "enemy": frozenset(str(entity.key) for entity in enemies),
        },
        roster,
    )


def _decision(actor, allies, enemies, *, scope_index=0, event_context=None):
    """One decision's snapshot, read set, roster and context over real entities."""
    field = _field(actor, allies, enemies)
    context = BattlefieldActionContext(field, event_context=event_context or {})
    reads = DecisionReads()
    snapshot = build_decision_snapshot(
        actor,
        context,
        scope=DecisionScope(SCOPE, ROUND, scope_index),
        participants=(*allies, *enemies),
        reads=reads,
    )
    return snapshot, reads, roster_index((actor, *allies, *enemies)), context


def _enumerate(actor, allies, enemies, **decision_kwargs):
    """Enumerate one decision's candidates over real entities."""
    snapshot, reads, roster, context = _decision(
        actor, allies, enemies, **decision_kwargs
    )
    return enumerate_candidates(
        snapshot, actor=actor, context=context, roster=roster, reads=reads
    )


def _estimate(actor, allies, enemies, **decision_kwargs):
    """Enumerate and estimate one decision's candidates over real entities."""
    snapshot, reads, roster, context = _decision(
        actor, allies, enemies, **decision_kwargs
    )
    candidates = enumerate_candidates(
        snapshot, actor=actor, context=context, roster=roster, reads=reads
    )
    estimates = estimate_candidates(
        candidates, snapshot=snapshot, actor=actor, context=context, roster=roster,
        reads=reads,
    )
    return candidates, estimates


def _only(estimates):
    """Return the single estimate one decision produced."""
    if len(estimates.estimates) != 1:
        raise AssertionError(f"expected one estimate, got {estimates.estimates!r}")
    return estimates.estimates[0]


def _pick(estimates, skill_key):
    """Return one skill's estimate out of a decision's set."""
    for item in estimates.estimates:
        if item.identity.skill_key == skill_key:
            return item
    raise AssertionError(f"no estimate for {skill_key!r} in {estimates.estimates!r}")


def _by_identity(estimates):
    """Index one decision's estimates by their canonical candidate identity."""
    return {item.identity: item for item in estimates.estimates}


def _best_scores(scored) -> dict[str, float]:
    """Return each skill key's highest score out of one decision's candidates."""
    return {
        key: max(
            item.score for item in scored if item.identity.skill_key == key
        )
        for key in {item.identity.skill_key for item in scored}
    }


def _recipient(estimate, entity):
    """Return one identity's recipient projection."""
    for projection in estimate.recipients:
        if projection.identity == stable_identity(entity):
            return projection
    raise AssertionError(f"no projection for {stable_identity(entity)}")


def _owned(actor, *keys) -> None:
    """Overwrite one participant's owned skill rows."""
    actor.db.skills = {"active": list(keys), "passive": []}


def _hand(skill, recipients, *, scale=1.0, actor=None, context=None, reads=None):
    """One hand-built candidate carrying the routing the planner derives."""
    ordered = tuple(sorted(stable_identity(target) for target in recipients))
    routed = None
    if actor is not None and context is not None:
        routed = tuple(
            tuple(reached)
            for reached in plan_effect_audiences(
                actor, context, skill, list(recipients), readings=reads
            )
        )
    return Candidate(
        CandidateIdentity(skill.key, scale, ordered),
        PlannedAction(skill.key, scale, target_ids=ordered),
        recipients=tuple(recipients),
        routed=routed,
    )


def _profile(**over) -> BehaviourProfile:
    """One synthetic utility profile carrying the complete authoring contract."""
    fields = {
        "target_strategy": "lowest_hp",
        "skill_choice": "first_owned",
        "prefer_area_when_multiple_enemies": False,
        "flee_hp_fraction": None,
        "decision_mode": DecisionMode.UTILITY,
        "utility_weights": UtilityWeights(**WEIGHTS),
    }
    fields.update(over)
    return BehaviourProfile(**fields)


def _rulebook(*, intelligence=None, weights=None):
    """One complete synthetic rulebook whose variant is a utility monster."""
    return {
        "tier_default_archetype": {TIER: ARCHETYPE},
        "archetypes": {
            ARCHETYPE: {
                "target_strategy": "lowest_hp",
                "skill_choice": "first_owned",
                "prefer_area_when_multiple_enemies": False,
                "flee_hp_fraction": None,
                "decision_mode": "utility",
                "utility_weights": (
                    dict(WEIGHTS) if weights is None else dict(weights)
                ),
            }
        },
        "variant_intelligence": (
            {VARIANT: 50} if intelligence is None else intelligence
        ),
        "variant_decision_mode": {VARIANT: "utility"},
        "candidate_budget": 64,
    }


class SupportFixture(EvenniaTestCase):
    """Real participants over the shipped engines and synthetic catalogs."""

    def setUp(self):
        _scope(self)
        _suppress_innate_skills(self)
        super().setUp()
        self.room = create_object(Room, key="support arena")
        self.actor = self._participant("t_sup_actor")
        self.ally = self._participant("t_sup_ally")
        self.enemy = self._participant("t_sup_enemy")
        self.other = self._participant("t_sup_other")

    def _participant(self, key):
        entity = _player(key)
        entity.location = self.room
        entity.traits.hp.base = 100
        entity.traits.hp.current = 100
        entity.traits.mp.base = 60
        entity.traits.mp.current = 60
        entity.traits.magic_power.base = 40
        entity.traits.defense.base = 10
        entity.traits.agility.base = 20
        entity.db.skills = {"active": [], "passive": []}
        return entity

    def _open_tuning(self, **kwargs):
        """Load and patch one synthetic rulebook, its profiles and its tuning."""
        book = _rulebook(**kwargs)
        profiles = behaviour._load_behaviour_profiles(book, tiers={TIER})
        tuning = behaviour._load_ai_tuning(
            book,
            profiles=profiles,
            species=_SPECIES_ROWS,
            variants=_VARIANT_ROWS,
        )
        patcher = patch.multiple(
            behaviour,
            MONSTER_BEHAVIOUR_YAML=book,
            BEHAVIOUR_PROFILES=profiles,
            MONSTER_AI_TUNING=tuning,
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        return tuning


class SupportCandidateTests(SupportFixture):
    """Owned healing, buffs and control reach the candidate pipeline."""

    @covers_requirement(
        "monster-ai-tactical-support::support-uses-existing-legal-audience-plans"
    )
    def test_a_heal_offers_the_decisions_own_side_only(self):
        self.ally.traits.hp.current = 40
        _owned(self.actor, HEAL.key)
        candidates = _enumerate(self.actor, (self.ally,), (self.enemy,))
        targets = {
            identity for candidate in candidates.candidates
            for identity in candidate.identity.target_ids
        }
        # The wounded ally is reachable and the enemy never is: the heal's
        # domain is the decision's own side only.
        self.assertIn(stable_identity(self.ally), targets)
        self.assertNotIn(stable_identity(self.enemy), targets)
        self.assertTrue(
            targets <= {stable_identity(self.actor), stable_identity(self.ally)}
        )

    @covers_requirement(
        "monster-ai-tactical-support::support-uses-existing-legal-audience-plans"
    )
    def test_full_health_heals_stay_legal_with_zero_recovery_and_a_real_cost(self):
        # Both the actor and the ally are at full health, so neither heal can
        # recover anything -- and both plans remain legal with a real charge.
        _owned(self.actor, HEAL.key)
        candidates, estimates = _estimate(self.actor, (self.ally,), (self.enemy,))
        self.assertGreaterEqual(len(candidates.candidates), 1)
        for estimate in estimates.estimates:
            self.assertNotIsInstance(estimate, InvalidEstimate)
            self.assertAlmostEqual(estimate.healing.magnitude, 0.0)
            self.assertAlmostEqual(estimate.cost, 3 / 60)

    @covers_requirement(
        "monster-ai-tactical-support::support-uses-existing-legal-audience-plans"
    )
    def test_an_omitted_ally_contributes_no_healing_while_the_self_effect_stays(self):
        # The broad plan reaches the ally, the submitted one omits it: the
        # estimate follows the submitted audience plan, not the broad preview.
        self.ally.traits.hp.current = 40
        self.actor.traits.hp.current = 40
        snapshot, reads, roster, context = _decision(
            self.actor, (self.ally,), (self.enemy,)
        )
        broad = _hand(
            MIXED,
            (self.actor, self.ally),
            actor=self.actor,
            context=context,
            reads=reads,
        )
        narrow = _hand(
            MIXED, (self.actor,), actor=self.actor, context=context, reads=reads
        )
        wide = estimate_plan(
            broad, snapshot=snapshot, actor=self.actor, context=context, roster=roster,
            reads=reads,
        )
        omitted = estimate_plan(
            narrow, snapshot=snapshot, actor=self.actor, context=context,
            roster=roster, reads=reads,
        )
        self.assertGreater(_recipient(wide, self.ally).healing, 0.0)
        self.assertEqual(
            [item.identity for item in omitted.recipients],
            [stable_identity(self.actor)],
        )
        self.assertGreater(_recipient(omitted, self.actor).healing, 0.0)

    @covers_requirement(
        "monster-ai-tactical-support::support-uses-existing-legal-audience-plans"
    )
    def test_friendly_support_is_not_redirected_by_the_seal(self):
        # The mandatory restrictions narrow hostile single-target *damage*: the
        # sealed enemy stays the strike's only target while the sealed ally is
        # still a legal friendly heal target.
        apply_buff(self.ally, SEAL_BUFF_KEY)
        apply_buff(self.enemy, SEAL_BUFF_KEY)
        _owned(self.actor, STRIKE.key, HEAL.key)
        candidates = _enumerate(self.actor, (self.ally,), (self.enemy,))
        by_skill = {}
        for candidate in candidates.candidates:
            by_skill.setdefault(candidate.identity.skill_key, set()).update(
                candidate.identity.target_ids
            )
        self.assertEqual(by_skill[STRIKE.key], {stable_identity(self.enemy)})
        self.assertIn(stable_identity(self.ally), by_skill[HEAL.key])

    @covers_requirement(
        "monster-ai-tactical-support::support-uses-existing-legal-audience-plans"
    )
    def test_an_actor_bound_skill_presents_the_implicit_binding(self):
        self.actor.traits.hp.current = 40
        _owned(self.actor, SELF_MEND.key)
        candidates, estimates = _estimate(self.actor, (self.ally,), (self.enemy,))
        self.assertEqual(len(candidates.candidates), 1)
        plan = candidates.plans[0]
        self.assertEqual(plan.target_ids, ())
        self.assertIsNone(plan.shorthand)
        self.assertGreater(_only(estimates).healing.magnitude, 0.0)

    @covers_requirement(
        "monster-ai-tactical-support::support-uses-existing-legal-audience-plans"
    )
    def test_a_hostile_mount_is_a_candidate_and_an_own_side_debuff_is_refused(self):
        # The own-side debuff shape is an area mount whose audience is the
        # actor's own side: the plan reaches its own participants, and the
        # closed classifier still refuses to value a debuff there.
        own_harm = replace(
            MEND_AREA,
            key="t_sup_own_harm",
            effects=[f"buff_apply:{LOCK_KEY}"],
            effect_policies=(EffectPolicy(audience=EffectAudience.ALLIES),),
        )
        with patch.dict(
            "world.skills.registry.SKILL_REGISTRY", {own_harm.key: own_harm}
        ):
            _owned(self.actor, LOCK.key, own_harm.key)
            estimates = _estimate(self.actor, (self.ally,), (self.enemy,))[1]
        lock = _pick(estimates, LOCK.key)
        self.assertNotIsInstance(lock, InvalidEstimate)
        self.assertGreater(lock.control.magnitude, 0.0)
        refused = [
            item
            for item in estimates.estimates
            if isinstance(item, InvalidEstimate)
            and item.identity.skill_key == own_harm.key
        ]
        self.assertTrue(refused)
        self.assertIn("friendly recipient", refused[0].detail)


class HealingPaymentTests(SupportFixture):
    """Healing uses the shared scalars, prerequisites and payment."""

    @covers_requirement(
        "monster-ai-tactical-support::healing-projects-payment-and-actual-prerequisites"
    )
    def test_a_health_payment_is_projected_before_the_ordered_effects(self):
        # A full-health actor charges four health and then heals itself. The
        # payment is a real projected own-side loss, and the restoration is
        # still staged against the pre-action gap settlement stages it against,
        # so nothing is credited that the resolver would not apply.
        _owned(self.actor, PENALTY.key)
        candidates, estimates = _estimate(self.actor, (), (self.enemy,))
        paying = _only(estimates)
        self.assertNotIsInstance(paying, InvalidEstimate)
        self.assertEqual(len(candidates.candidates), 1)
        self.assertAlmostEqual(_recipient(paying, self.actor).damage, 4.0)
        self.assertAlmostEqual(paying.healing.magnitude, 0.0)
        # Four health of a hundred-point pool: the cost feature sees the charge.
        self.assertAlmostEqual(paying.cost, 4 / 100)
        # The same row without the payment differs by exactly the payment's
        # share of the own-side capacity and by nothing else.
        _owned(self.actor, FREE_MEND.key)
        free = _only(_estimate(self.actor, (), (self.enemy,))[1])
        self.assertAlmostEqual(paying.damage.value, free.damage.value - 4 / 100)

    @covers_requirement(
        "monster-ai-tactical-support::healing-projects-payment-and-actual-prerequisites"
    )
    def test_the_same_row_without_a_health_payment_projects_no_own_side_loss(self):
        _owned(self.actor, FREE_MEND.key)
        estimate = _only(_estimate(self.actor, (), (self.enemy,))[1])
        self.assertAlmostEqual(_recipient(estimate, self.actor).damage, 0.0)
        self.assertGreater(estimate.damage.value, 0.0)
        self.assertAlmostEqual(estimate.cost, 3 / 60)

    @covers_requirement(
        "monster-ai-tactical-support::healing-projects-payment-and-actual-prerequisites"
    )
    def test_a_missed_prerequisite_credits_no_recovery(self):
        # The actor can never land on this defender, so the heal that depends on
        # the occurrence credits nothing at all.
        self.actor.traits.hp.current = 40
        _owned(self.actor, ATTENDED.key)
        certain = _only(_estimate(self.actor, (), (self.enemy,))[1])
        self.assertGreater(certain.healing.magnitude, 0.0)
        self.enemy.traits.agility.base = 4000
        missed = _only(_estimate(self.actor, (), (self.enemy,))[1])
        self.assertAlmostEqual(missed.healing.magnitude, 0.0)
        self.assertIn(EstimationLimit.GATED_EFFECT_WEIGHTED, missed.limits)

    @covers_requirement(
        "monster-ai-tactical-support::healing-projects-payment-and-actual-prerequisites"
    )
    def test_recovery_is_capped_by_the_projected_missing_health(self):
        self.ally.traits.hp.current = 95
        _owned(self.actor, HEAL.key)
        candidates, estimates = _estimate(self.actor, (self.ally,), (self.enemy,))
        narrow = next(
            estimate
            for estimate in estimates.estimates
            if estimate.identity.target_ids == (stable_identity(self.ally),)
        )
        projection = _recipient(narrow, self.ally)
        # Five missing health of a hundred-point ally faction.
        self.assertAlmostEqual(projection.healing, 5.0)
        self.assertAlmostEqual(narrow.healing.magnitude, 5.0 / 200)
        self.assertEqual(len(candidates.candidates), 2)


class ControlValuationTests(SupportFixture):
    """Control is concrete marginal opportunity value, never a face value."""

    @covers_requirement(
        "monster-ai-tactical-support::control-value-is-concrete-marginal-opportunity-value"
    )
    def test_a_lock_denies_its_share_of_the_factions_opportunities(self):
        # Two enemies of one action each: locking one removes exactly half the
        # faction's baseline opportunities, and the lock carries nothing else.
        _owned(self.actor, LOCK.key)
        candidates, estimates = _estimate(self.actor, (), (self.enemy, self.other))
        self.assertEqual(len(candidates.candidates), 2)
        for estimate in estimates.estimates:
            self.assertAlmostEqual(estimate.control.magnitude, 0.5)
            self.assertEqual(estimate.control.direction.name, "BENEFIT")
            self.assertAlmostEqual(estimate.damage.magnitude, 0.0)
            self.assertAlmostEqual(estimate.healing.magnitude, 0.0)

    @covers_requirement(
        "monster-ai-tactical-support::control-value-is-concrete-marginal-opportunity-value"
    )
    def test_a_slow_is_valued_by_the_offensive_impact_it_takes_away(self):
        # A five-point agility penalty on a forty-power, twenty-agility enemy
        # is 40 x (5 / 100) = 2 points of offensive impact, normalized by the
        # hundred-health faction that offense threatens.
        _owned(self.actor, SLOW.key)
        estimate = _only(_estimate(self.actor, (), (self.enemy,))[1])
        self.assertAlmostEqual(estimate.control.magnitude, 2.0 / 100)

    @covers_requirement(
        "monster-ai-tactical-support::control-value-is-concrete-marginal-opportunity-value"
    )
    def test_a_friendly_mount_is_valued_by_the_health_it_protects(self):
        # Five points of defense on an ally prevents five points of incoming
        # health per strike, normalized by the two-hundred-health own side.
        _owned(self.actor, WARD.key)
        estimates = _estimate(self.actor, (self.ally,), (self.enemy,))[1]
        allied = next(
            estimate
            for estimate in estimates.estimates
            if estimate.identity.target_ids == (stable_identity(self.ally),)
        )
        self.assertAlmostEqual(allied.control.magnitude, 5.0 / 200)

    @covers_requirement(
        "monster-ai-tactical-support::control-value-is-concrete-marginal-opportunity-value"
    )
    def test_a_reapplied_mount_is_worth_zero(self):
        apply_buff(self.ally, ARMOR_KEY)
        _owned(self.actor, WARD.key)
        estimate = next(
            item
            for item in _estimate(self.actor, (self.ally,), (self.enemy,))[1].estimates
            if item.identity.target_ids == (stable_identity(self.ally),)
        )
        self.assertAlmostEqual(estimate.control.magnitude, 0.0)
        self.assertIn(EstimationLimit.CONTROL_ZERO_MARGINAL, estimate.limits)

    @covers_requirement(
        "monster-ai-tactical-support::control-value-is-concrete-marginal-opportunity-value"
    )
    def test_a_mount_a_stronger_one_already_outweighs_is_worth_zero(self):
        apply_buff(self.ally, STRONG_KEY)
        _owned(self.actor, WARD_WEAK.key)
        estimate = next(
            item
            for item in _estimate(self.actor, (self.ally,), (self.enemy,))[1].estimates
            if item.identity.target_ids == (stable_identity(self.ally),)
        )
        self.assertAlmostEqual(estimate.control.magnitude, 0.0)
        self.assertIn(EstimationLimit.CONTROL_ZERO_MARGINAL, estimate.limits)
        self.assertTrue(
            any("already holds" in line for line in estimate.diagnostics)
        )

    @covers_requirement(
        "monster-ai-tactical-support::control-value-is-concrete-marginal-opportunity-value"
    )
    def test_an_expired_window_and_a_beneficiary_without_opportunity_are_zero(self):
        _owned(self.actor, EXPIRED.key)
        expired = _only(_estimate(self.actor, (), (self.enemy,))[1])
        self.assertAlmostEqual(expired.control.magnitude, 0.0)
        self.assertIn(EstimationLimit.CONTROL_NO_OPPORTUNITY, expired.limits)
        # A locked beneficiary has no action left to deny.
        apply_buff(self.enemy, LOCK_KEY)
        _owned(self.actor, SLOW.key)
        locked = _only(_estimate(self.actor, (), (self.enemy,))[1])
        self.assertAlmostEqual(locked.control.magnitude, 0.0)
        self.assertIn(EstimationLimit.CONTROL_NO_OPPORTUNITY, locked.limits)

    @covers_requirement(
        "monster-ai-tactical-support::control-value-is-concrete-marginal-opportunity-value"
    )
    def test_a_chance_locked_mount_is_weighted_by_its_probability(self):
        # Half the time the lock applies, so half of one enemy's one baseline
        # opportunity of two is denied.
        _owned(self.actor, CHANCE.key)
        estimates = _estimate(self.actor, (), (self.enemy, self.other))[1]
        self.assertEqual(len(estimates.estimates), 2)
        for estimate in estimates.estimates:
            self.assertAlmostEqual(estimate.control.magnitude, 0.25)
            self.assertIn(EstimationLimit.CONTROL_CHANCE_WEIGHTED, estimate.limits)

    @covers_requirement(
        "monster-ai-tactical-support::control-value-is-concrete-marginal-opportunity-value"
    )
    def test_an_unvaluable_modifier_is_reported_and_never_invented(self):
        _owned(self.actor, OPAQUE.key)
        estimate = _only(_estimate(self.actor, (), (self.enemy,))[1])
        self.assertAlmostEqual(estimate.control.magnitude, 0.0)
        self.assertIn(EstimationLimit.CONTROL_MODIFIER_UNSUPPORTED, estimate.limits)
        self.assertIn(EstimationLimit.CONTROL_ZERO_MARGINAL, estimate.limits)

    @covers_requirement(
        "monster-ai-tactical-support::control-value-is-concrete-marginal-opportunity-value"
    )
    def test_a_mounts_own_health_effect_over_time_stays_reported(self):
        _owned(self.actor, DOT.key)
        estimate = _only(_estimate(self.actor, (), (self.enemy,))[1])
        self.assertGreater(estimate.control.magnitude, 0.0)
        self.assertIn(EstimationLimit.OVER_TIME_EFFECT_UNMODELED, estimate.limits)


class SupportScoreTests(SupportFixture):
    """The completed score keeps baseline healing and scaled control."""

    def _score(self, owned, *, intelligence, weights, **profile_over):
        _owned(self.actor, *owned)
        snapshot, reads, roster, context = _decision(
            self.actor, (self.ally,), (self.enemy, self.other)
        )
        candidates = enumerate_candidates(
            snapshot, actor=self.actor, context=context, roster=roster, reads=reads
        )
        estimates = estimate_candidates(
            candidates, snapshot=snapshot, actor=self.actor, context=context,
            roster=roster, reads=reads,
        )
        scored = score_candidates(
            candidates,
            estimates,
            profile=_profile(utility_weights=UtilityWeights(**weights), **profile_over),
            intelligence=intelligence,
            actor=self.actor,
            context=context,
            roster=roster,
            snapshot=snapshot,
        )
        return scored, estimates

    @covers_requirement(
        "monster-ai-tactical-support::completed-tactical-score-retains-baseline-healing"
    )
    def test_the_score_is_the_baseline_recovery_plus_scaled_control(self):
        weights = dict.fromkeys(behaviour.UTILITY_WEIGHT_NAMES, 0.0)
        weights["heal"] = 2.0
        weights["control"] = 3.0
        self.ally.traits.hp.current = 40
        scored, estimates = self._score(
            (HEAL.key, LOCK.key), intelligence=50, weights=weights
        )
        paired = _by_identity(estimates)
        for item in scored:
            estimate = paired[item.identity]
            expected = 2.0 * estimate.healing.value + 0.5 * 3.0 * estimate.control.value
            self.assertTrue(isclose(item.score, expected), (item.score, expected))
            self.assertTrue(isclose(item.healing, estimate.healing.value))
            self.assertTrue(isclose(item.control, estimate.control.value))
        # The recovery term is real, so the heal really is worth taking.
        self.assertTrue(
            any(item.healing > 0 and item.score > 0 for item in scored)
        )

    @covers_requirement(
        "monster-ai-tactical-support::completed-tactical-score-retains-baseline-healing"
    )
    def test_immediate_healing_is_available_at_every_intelligence(self):
        weights = dict.fromkeys(behaviour.UTILITY_WEIGHT_NAMES, 0.0)
        weights["heal"] = 2.0
        weights["control"] = 3.0
        self.ally.traits.hp.current = 40
        scores = {}
        for intelligence in (0, 100):
            scored, _estimates = self._score(
                (HEAL.key, LOCK.key), intelligence=intelligence, weights=weights
            )
            scores[intelligence] = _best_scores(scored)
        # Recovery is intelligence-independent; control is not.
        self.assertTrue(
            isclose(scores[0][HEAL.key], scores[100][HEAL.key])
            and scores[0][HEAL.key] > 0
        )
        self.assertAlmostEqual(scores[0][LOCK.key], 0.0)
        self.assertGreater(scores[100][LOCK.key], 0.0)

    @covers_requirement(
        "monster-ai-tactical-support::completed-tactical-score-retains-baseline-healing"
    )
    def test_an_enemy_side_mount_and_an_own_side_harm_move_the_score_the_right_way(self):
        weights = dict.fromkeys(behaviour.UTILITY_WEIGHT_NAMES, 0.0)
        weights["heal"] = 1.0
        weights["damage"] = 1.0
        self.ally.traits.hp.current = 40
        scored, _estimates = self._score(
            (HEAL.key,), intelligence=0, weights=weights
        )
        # The wounded ally's candidate is the useful one, and it outweighs the
        # plan that would have left the actor's own side untouched.
        self.assertGreater(max(item.score for item in scored), 0.0)
        self.assertGreater(max(item.healing for item in scored), 0.0)


class SupportAdapterTests(SupportFixture):
    """The production adapter selects and settles real support and control."""

    def setUp(self):
        super().setUp()
        self._open_tuning()
        self.player = self._participant("t_sup_player")
        self.player.traits.hp.base = 400
        self.player.traits.hp.current = 400
        self.bystander = self._participant("t_sup_bystander")
        self.bystander.traits.hp.base = 400
        self.bystander.traits.hp.current = 400
        self.monster = construct_species_individual(
            SPECIES, VARIANT, key="t_sup_monster"
        )
        self.monster.location = self.room
        self.monster.traits.hp.base = 300
        self.monster.traits.hp.current = 300
        self.monster.traits.mp.base = 100
        self.monster.traits.mp.current = 100
        self.monster.traits.magic_power.base = 40
        self.record = CombatSessionRecord(
            session_id=SESSION,
            mode="hostile",
            room_id=self.room.pk,
            player_ids=(self.player.pk,),
            enemy_ids=(self.monster.pk,),
            fled_ids=(),
            knocked_out_ids=(),
            rounds_elapsed=0,
            exam_id=None,
        )

    def _best(self, scored, **_kwargs):
        """Select the highest-scoring candidate, for a deterministic assertion."""
        return max(scored, key=lambda item: item.score)

    def _battlefield(self, allies, enemies):
        return _field(self.monster, allies, enemies)

    def _committed(self, entity, trait_key):
        return float(
            ObjectDB.objects.get(id=entity.pk)
            .attributes.get("traits", default={}, category="traits")[trait_key][
                "current"
            ]
        )

    @covers_requirement(
        "monster-ai-tactical-support::control-value-is-concrete-marginal-opportunity-value"
    )
    def test_a_real_heal_is_chosen_and_committed_to_the_wounded_recipient(self):
        # The monster can only heal, and only the wounded ally is worth healing:
        # the real session adapter selects that request and the resolver commits
        # the restoration while the bystander stays untouched.
        self.ally.traits.hp.base = 300
        self.ally.traits.hp.current = 100
        _owned(self.monster, HEAL.key)
        before_mp = self._committed(self.monster, "mp")
        field = self._battlefield((self.ally,), (self.player, self.bystander))
        with patch("world.rules.monster_ai.selection.select_candidate", self._best):
            request = _enemy_policy(self.monster, field, self.record)
        self.assertIsNotNone(request)
        self.assertEqual(request.skill_key, HEAL.key)
        self.assertEqual([target.key for target in request.targets], [self.ally.key])
        result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success", getattr(result, "detail", result))
        self.assertGreater(self._committed(self.ally, "hp"), 100)
        self.assertEqual(self._committed(self.monster, "mp"), before_mp - 3)
        self.assertEqual(self._committed(self.player, "hp"), 400)
        self.assertEqual(self._committed(self.bystander, "hp"), 400)

    @covers_requirement(
        "monster-ai-tactical-support::control-value-is-concrete-marginal-opportunity-value"
    )
    def test_a_real_hostile_mount_is_chosen_and_committed(self):
        _owned(self.monster, LOCK.key)
        before_mp = self._committed(self.monster, "mp")
        field = self._battlefield((), (self.player, self.bystander))
        with patch("world.rules.monster_ai.selection.select_candidate", self._best):
            request = _enemy_policy(self.monster, field, self.record)
        self.assertIsNotNone(request)
        self.assertEqual(request.skill_key, LOCK.key)
        result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success", getattr(result, "detail", result))
        # The chosen recipient carries the lock; the bystander does not.
        chosen = request.targets[0]
        other = self.bystander if chosen is self.player else self.player
        self.assertEqual(evaluate_combat_modifiers(chosen).get("actions_per_turn"), 0)
        self.assertNotIn("actions_per_turn", evaluate_combat_modifiers(other))
        self.assertEqual(self._committed(self.monster, "mp"), before_mp - 3)
