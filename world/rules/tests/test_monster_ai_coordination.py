"""Behavior tests for the monster-AI observed coordination.

Every fixture here is file-local and synthetic: the ``t_``-named species,
variant, tier, skill and archetype rows are built from the shared kit's
factories and templates, and no shipped key, label, weight or catalog symbol is
named by a resolvable literal. The shipped legality gates, the shared effect
estimator and the real round loop are the production ones.

The tests establish this slice's contracts: focus sums the already settled
allied health pressure against still-live opponents, normalizes it by the
largest positive sum and averages a plan's distinct hostile recipients; threat
uses the observed incoming damage, opposing recovery and landed hostile status
mounts within the retention window, capacity-normalized and age-decayed, and
only a threat-valuing strategy averages it with the static rank; the completed
score adds ``i * w_focus * observed_focus`` beside the other terms; the trace
records the initial observation snapshot; and two synthetic pack hunters
coordinate only after the first of them has actually resolved an action.
"""

from tools.spec_traceability import covers_requirement

from math import isclose
from types import SimpleNamespace
from unittest.mock import patch

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.rooms import Room

from world.rules import monster_behaviour as behaviour
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
    ExecutionScopeBase,
    run_round,
)
from world.rules.combat_session.observations import MAX_RETAINED_ROUNDS
from world.rules.monster_ai import (
    OBSERVATION_WINDOW_ROUNDS,
    THREAT_DECAY_STEPS,
    THREAT_DECAY_VERSION,
    CandidateIdentity,
    DecisionReads,
    DecisionScope,
    DecisionTrace,
    PlanEstimate,
    PublicObservation,
    RecipientProjection,
    build_decision_snapshot,
    decayed_weight,
    enumerate_candidates,
    estimate_candidates,
    focus_for_plan,
    observed_focus,
    observed_threat,
    roster_index,
    score_candidates,
    select_candidate,
    selection_seed_for,
    selection_temperature,
    stable_identity,
    threat_is_valued,
    trace_observations,
)
from world.rules.monster_ai.candidates import (
    KIND_FRIENDLY,
    decision_pool,
    group_members,
    hostile_domain,
)
from world.rules.monster_behaviour import UtilityWeights
from world.rules.monster_individual import construct_species_individual
from world.rules.targeting import Relation
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

SESSION = "hostile:7:0"
#: The support-profile round owns its own session: the observation ring is
#: in-process and keyed by session, so a second real round needs its own.
SUPPORT_SESSION = "hostile:8:0"
ROUND = 7
SPECIES = "t_coo_species"
VARIANT = "t_coo_ordinary"
VARIANT_SUPPORT = "t_coo_medic"
TIER = "t_coo_tier"
ARCHETYPE = "t_coo_pack"
SUPPORT_ARCHETYPE = "t_coo_attendant"
#: Every authored weight, so a test can zero the ones it is not asserting.
WEIGHTS = {name: 1.0 for name in behaviour.UTILITY_WEIGHT_NAMES}
#: The support profile's weights: recovery is the only thing it values.
SUPPORT_WEIGHTS = dict.fromkeys(behaviour.UTILITY_WEIGHT_NAMES, 0.0)
SUPPORT_WEIGHTS["heal"] = 1.0

_TIER_ROWS = {TIER: make_monster_tier(TIER)}
_SPECIES_ROWS = {SPECIES: make_monster_species(SPECIES, default_variant_key=VARIANT)}
_VARIANT_ROWS = {
    VARIANT: make_monster_variant(
        VARIANT,
        species_key=SPECIES,
        threat_tier=TIER,
        behaviour_profile_key=ARCHETYPE,
    ),
    VARIANT_SUPPORT: make_monster_variant(
        VARIANT_SUPPORT,
        species_key=SPECIES,
        threat_tier=TIER,
        behaviour_profile_key=SUPPORT_ARCHETYPE,
    ),
}

# File-local synthetic skill rows: one free single-target strike, one free
# enemy-only area strike whose group shape exercises the recipient averaging,
# one free single-target heal whose own-side shape exercises a plan that
# reaches no hostile recipient at all, and one single-target strike that costs
# mana so a completed score's cost term is genuinely non-zero.
STRIKE = synth_damage_skill(
    "t_coo_astrike",
    "協同單體擊",
    effects=[f"damage:{SYNTH_GLOW_ELEMENT}:physical"],
    cost={},
)
AREA = synth_damage_skill(
    "t_coo_carea",
    "協同群擊",
    effects=[f"damage:{SYNTH_GLOW_ELEMENT}:physical"],
    cost={},
    target_spec=TargetSpec.AREA,
)
HEAL = synth_damage_skill(
    "t_coo_bheal",
    "協同恢復",
    effects=["heal:single"],
    cost={},
)
COSTLY = synth_damage_skill(
    "t_coo_acost",
    "協同耗魔擊",
    effects=[f"damage:{SYNTH_GLOW_ELEMENT}:physical"],
    cost={"mp": 6},
)

_ROWS = (STRIKE, AREA, HEAL, COSTLY)


def _scope(test):
    """Enter the kit scope this module's fixtures need, with its own catalogs."""
    extra = synth_innate_overlay()
    extra["skills"].update({row.key: row for row in _ROWS})
    extra["monster_tiers"] = _TIER_ROWS
    extra["monster_species"] = _SPECIES_ROWS
    extra["monster_variants"] = _VARIANT_ROWS
    return open_synthetic_scope(
        test,
        "monster_tiers",
        "monster_species",
        "monster_variants",
        "races",
        "skills",
        "elements",
        extra=extra,
    )


def _suppress_innate_skills(test) -> None:
    """Own only the rows a test declares, without the production innate set."""
    patcher = patch("world.skills.handler.INNATE_SKILL_ORDER", ())
    patcher.start()
    test.addCleanup(patcher.stop)


def _owned(actor, *keys) -> None:
    """Overwrite one participant's owned skill rows."""
    actor.db.skills = {"active": list(keys), "passive": []}


def _identity(value) -> str:
    """Return one observation participant's stable identity, or a raw id."""
    return value if isinstance(value, str) else stable_identity(value)


def _observation(
    round_index,
    *,
    source,
    recipients=(),
    magnitudes=(),
    statuses=("damage",),
    action="t_coo_action",
    faction="enemies",
) -> PublicObservation:
    """One settled public observation over this module's participants."""
    return PublicObservation(
        round_index=round_index,
        sequence=0,
        source_id=_identity(source),
        action_key=action,
        recipient_ids=tuple(_identity(item) for item in recipients),
        statuses=tuple(statuses),
        source_faction=faction,
        magnitudes=tuple(
            (_identity(item), float(value)) for item, value in magnitudes
        ),
    )


def _field(actor, allies, enemies) -> Battlefield:
    """A two-team battlefield over real participants."""
    roster = {str(entity.key): entity for entity in (actor, *allies, *enemies)}
    return Battlefield(
        {
            "party": frozenset(str(entity.key) for entity in (actor, *allies)),
            "enemies": frozenset(str(entity.key) for entity in enemies),
        },
        roster,
    )


def _decision(actor, allies, enemies, *, observations=(), round_index=ROUND):
    """One decision's snapshot, reads, roster and context over real entities."""
    field = _field(actor, allies, enemies)
    context = BattlefieldActionContext(field)
    reads = DecisionReads()
    snapshot = build_decision_snapshot(
        actor,
        context,
        scope=DecisionScope(SESSION, round_index, 0),
        participants=(*allies, *enemies),
        observations=tuple(observations),
        reads=reads,
    )
    return snapshot, reads, roster_index((actor, *allies, *enemies)), context


def _hostiles(*entities) -> tuple[str, ...]:
    """The applicable hostile identity domain one decision would rank over."""
    return tuple(stable_identity(entity) for entity in entities)


def _plan(*recipients) -> PlanEstimate:
    """One hand-built estimate carrying a plan's recipient projections."""
    identities = tuple(_identity(item) for item in recipients)
    return PlanEstimate(
        identity=CandidateIdentity(f"{AREA.key}", 1.0, tuple(sorted(identities))),
        recipients=tuple(
            RecipientProjection(
                identity=identity,
                relation=Relation.ENEMY,
                damage=0.0,
                healing=0.0,
                nominal_damage=0.0,
                nominal_healing=0.0,
                finishing=0.0,
            )
            for identity in identities
        ),
    )


def _profile(*, weights=None, **over) -> SimpleNamespace:
    """One synthetic utility profile carrying the complete authoring contract."""
    fields = {
        "target_strategy": "lowest_hp",
        "skill_choice": "first_owned",
        "prefer_area_when_multiple_enemies": False,
        "utility_weights": UtilityWeights(**(WEIGHTS if weights is None else weights)),
    }
    fields.update(over)
    return SimpleNamespace(**fields)


def _rulebook():
    """One complete synthetic rulebook with a pack and a support variant."""
    return {
        "tier_default_archetype": {TIER: ARCHETYPE},
        "archetypes": {
            ARCHETYPE: {
                "target_strategy": "lowest_hp",
                "skill_choice": "first_owned",
                "prefer_area_when_multiple_enemies": False,
                "flee_hp_fraction": None,
                "decision_mode": "utility",
                "utility_weights": dict(WEIGHTS),
            },
            SUPPORT_ARCHETYPE: {
                "target_strategy": "lowest_hp",
                "skill_choice": "first_owned",
                "prefer_area_when_multiple_enemies": False,
                "flee_hp_fraction": None,
                "decision_mode": "utility",
                "utility_weights": dict(SUPPORT_WEIGHTS),
            },
        },
        "variant_intelligence": {VARIANT: 50, VARIANT_SUPPORT: 50},
        "variant_decision_mode": {VARIANT: "utility", VARIANT_SUPPORT: "utility"},
        "candidate_budget": 64,
    }


class CoordinationFixture(EvenniaTestCase):
    """Real participants over the shipped engines and synthetic catalogs."""

    def setUp(self):
        _scope(self)
        _suppress_innate_skills(self)
        super().setUp()
        self.room = create_object(Room, key="coordination arena")
        self.actor = self._participant("t_coo_actor")
        self.ally = self._participant("t_coo_ally")
        self.enemy = self._participant("t_coo_enemy")
        self.other = self._participant("t_coo_other")
        self.front = _hostiles(self.enemy, self.other)

    def _participant(self, key):
        entity = _player(key)
        entity.location = self.room
        entity.traits.hp.base = 100
        entity.traits.hp.current = 100
        entity.traits.mp.base = 60
        entity.traits.mp.current = 60
        entity.db.skills = {"active": [], "passive": []}
        return entity

    def _equal_power(self, *entities) -> None:
        """Give participants the same static traits and maximum health."""
        for entity in entities:
            entity.traits.hp.base = 100
            entity.traits.hp.current = 100
            entity.traits.atk_phys.base = 20
            entity.traits.agility.base = 20
            entity.traits.defense.base = 10
            entity.traits.magic_power.base = 30

    def _score(
        self,
        owned,
        *,
        intelligence=50,
        weights=None,
        observations=(),
        round_index=ROUND,
        **profile_over,
    ):
        """Enumerate, estimate and score one decision over real entities."""
        _owned(self.actor, *owned)
        snapshot, reads, roster, context = _decision(
            self.actor,
            (self.ally,),
            (self.enemy, self.other),
            observations=observations,
            round_index=round_index,
        )
        candidates = enumerate_candidates(
            snapshot, actor=self.actor, context=context, roster=roster, reads=reads
        )
        estimates = estimate_candidates(
            candidates,
            snapshot=snapshot,
            actor=self.actor,
            context=context,
            roster=roster,
            reads=reads,
        )
        scored = score_candidates(
            candidates,
            estimates,
            profile=_profile(weights=weights, **profile_over),
            intelligence=intelligence,
            actor=self.actor,
            context=context,
            roster=roster,
            snapshot=snapshot,
        )
        return scored, estimates

    @staticmethod
    def _plan_for(scored, entity):
        """Return the scored single-target plan aimed at one participant."""
        identity = stable_identity(entity)
        return next(
            item for item in scored if item.identity.target_ids == (identity,)
        )


class FocusProjectionTests(CoordinationFixture):
    """Focus is observed allied health pressure, normalized and averaged."""

    @covers_requirement(
        "monster-ai-observed-coordination::focus-uses-observed-allied-hostile-pressure"
    )
    def test_allied_pressure_normalizes_by_the_largest_positive_sum(self):
        # Independently known: the ally's thirty against the first opponent and
        # the actor's own ten against the second decide 30/30 and 10/30. The
        # opposing strike on the ally and the unidentifiable source are not
        # allied pressure at all.
        observations = (
            _observation(
                ROUND,
                source=self.ally,
                recipients=(self.enemy,),
                magnitudes=((self.enemy, -30.0),),
            ),
            _observation(
                ROUND,
                source=self.actor,
                recipients=(self.other,),
                magnitudes=((self.other, -10.0),),
            ),
            _observation(
                ROUND,
                source=self.enemy,
                recipients=(self.ally,),
                magnitudes=((self.ally, -50.0),),
            ),
            _observation(
                ROUND,
                source="key:ghost",
                recipients=(self.enemy,),
                magnitudes=((self.enemy, -99.0),),
            ),
        )
        snapshot, _reads, _roster, _context = _decision(
            self.actor, (self.ally,), (self.enemy, self.other),
            observations=observations,
        )
        focus = observed_focus(snapshot, hostiles=self.front)
        self.assertTrue(isclose(focus[stable_identity(self.enemy)], 1.0))
        self.assertTrue(isclose(focus[stable_identity(self.other)], 10.0 / 30.0))

    @covers_requirement(
        "monster-ai-observed-coordination::focus-uses-observed-allied-hostile-pressure"
    )
    def test_friendly_healing_and_unresolved_sources_are_never_an_attack(self):
        # A heal an ally hands an enemy, an outcome published by an actor the
        # decision cannot identify and an unresolved queued intent have no
        # representation: each leaves focus exactly where an empty history
        # leaves it.
        empty, _reads, _roster, _context = _decision(
            self.actor, (self.ally,), (self.enemy, self.other)
        )
        observed = (
            _observation(
                ROUND,
                source=self.ally,
                recipients=(self.enemy,),
                magnitudes=((self.enemy, 15.0),),
                statuses=("heal",),
            ),
            _observation(
                ROUND,
                source="key:ghost",
                recipients=(self.enemy,),
                magnitudes=((self.enemy, -40.0),),
            ),
        )
        snapshot, _reads, _roster, _context = _decision(
            self.actor, (self.ally,), (self.enemy, self.other),
            observations=observed,
        )
        focus = observed_focus(snapshot, hostiles=self.front)
        self.assertEqual(
            focus,
            observed_focus(empty, hostiles=self.front),
        )
        self.assertEqual(set(focus.values()), {0.0})

    @covers_requirement(
        "monster-ai-observed-coordination::focus-uses-observed-allied-hostile-pressure"
    )
    def test_a_plan_averages_its_distinct_hostile_recipients(self):
        # Values 1.0 and 0.5: the single-target plans keep their own value, the
        # area plan averages to 0.75, a duplicate recipient representation adds
        # nothing, and a plan that reaches no hostile recipient carries no
        # observed pressure at all.
        focus = {
            stable_identity(self.enemy): 1.0,
            stable_identity(self.other): 0.5,
        }
        self.assertTrue(isclose(focus_for_plan(_plan(self.enemy), focus), 1.0))
        self.assertTrue(isclose(focus_for_plan(_plan(self.other), focus), 0.5))
        self.assertTrue(
            isclose(focus_for_plan(_plan(self.enemy, self.other), focus), 0.75)
        )
        self.assertTrue(
            isclose(
                focus_for_plan(_plan(self.enemy, self.enemy, self.other), focus),
                0.75,
            )
        )
        self.assertTrue(
            isclose(focus_for_plan(_plan(self.enemy, self.enemy), focus), 1.0)
        )
        self.assertEqual(focus_for_plan(_plan(self.ally), focus), 0.0)

    @covers_requirement(
        "monster-ai-observed-coordination::focus-uses-observed-allied-hostile-pressure"
    )
    def test_the_window_keeps_three_rounds_and_reads_nothing_older(self):
        # Three actual rounds is the session ring's retention: ages zero, one
        # and two count, an evicted age and a round the decision has not
        # reached count nothing, and the window matches the ring's own
        # constant.
        self.assertEqual(OBSERVATION_WINDOW_ROUNDS, MAX_RETAINED_ROUNDS)
        self.assertEqual(THREAT_DECAY_VERSION, 1)
        self.assertEqual(
            [decayed_weight(age) for age in (-1, 0, 1, 2, 3)],
            [0.0, *THREAT_DECAY_STEPS, 0.0],
        )
        observations = (
            _observation(
                ROUND,
                source=self.ally,
                recipients=(self.enemy,),
                magnitudes=((self.enemy, -20.0),),
            ),
            _observation(
                ROUND - 1,
                source=self.ally,
                recipients=(self.other,),
                magnitudes=((self.other, -10.0),),
            ),
            _observation(
                ROUND - OBSERVATION_WINDOW_ROUNDS,
                source=self.ally,
                recipients=(self.other,),
                magnitudes=((self.other, -80.0),),
            ),
            _observation(
                ROUND + 1,
                source=self.ally,
                recipients=(self.other,),
                magnitudes=((self.other, -80.0),),
            ),
        )
        snapshot, _reads, _roster, _context = _decision(
            self.actor, (self.ally,), (self.enemy, self.other),
            observations=observations,
        )
        focus = observed_focus(snapshot, hostiles=self.front)
        self.assertTrue(isclose(focus[stable_identity(self.enemy)], 1.0))
        self.assertTrue(isclose(focus[stable_identity(self.other)], 0.5))

    @covers_requirement(
        "monster-ai-observed-coordination::focus-uses-observed-allied-hostile-pressure"
    )
    def test_a_dead_or_absent_recipient_confers_no_pressure(self):
        # The opponent's identity is no longer in the decision's applicable
        # domain: the decision's own derivation drops the dead opponent, which
        # therefore neither pressures anyone nor comes back as a focusable
        # target.
        self.other.traits.hp.current = 0
        observations = (
            _observation(
                ROUND,
                source=self.ally,
                recipients=(self.other,),
                magnitudes=((self.other, -90.0),),
            ),
        )
        snapshot, _reads, roster, context = _decision(
            self.actor, (self.ally,), (self.enemy, self.other),
            observations=observations,
        )
        pool = decision_pool(snapshot, self.actor, roster, context)
        live = tuple(
            stable_identity(entity) for entity in hostile_domain(snapshot, pool)
        )
        self.assertEqual(live, (stable_identity(self.enemy),))
        focus = observed_focus(snapshot, hostiles=live)
        self.assertEqual(focus, {stable_identity(self.enemy): 0.0})
        self.assertNotIn(stable_identity(self.other), focus)

    @covers_requirement(
        "monster-ai-observed-coordination::completed-coordination-is-reproducible-and-intelligence-scaled"
    )
    def test_an_empty_history_adds_no_focus_to_the_completed_score(self):
        # The same decision with the authored focus weight and with it zeroed
        # scores identically while nothing has been observed, so the empty
        # history contributes exactly zero rather than an invented neutral.
        observed_weights = dict.fromkeys(behaviour.UTILITY_WEIGHT_NAMES, 0.0)
        observed_weights["damage"] = 1.0
        observed_weights["focus"] = 5.0
        silent_weights = dict(observed_weights, focus=0.0)
        with_history, _ = self._score(
            (STRIKE.key,), weights=observed_weights, intelligence=100
        )
        without, _ = self._score(
            (STRIKE.key,), weights=silent_weights, intelligence=100
        )
        self.assertEqual(
            [item.score for item in with_history],
            [item.score for item in without],
        )
        self.assertEqual([item.focus for item in with_history], [0.0, 0.0])


class ThreatProjectionTests(CoordinationFixture):
    """Threat is capacity-normalized, age-decayed and opt-in."""

    @covers_requirement(
        "monster-ai-observed-coordination::threat-remains-an-observed-soft-preference"
    )
    def test_damage_and_opposing_recovery_are_capacity_normalized_and_decayed(self):
        # Both sides' eligible live maximum health is 200 (two hundred-point
        # members each). The first opponent's forty against the ally is 40/200;
        # the second opponent's twenty-point self-recovery one round back is
        # 20/200 decayed by a half.
        observations = (
            _observation(
                ROUND,
                source=self.enemy,
                recipients=(self.ally,),
                magnitudes=((self.ally, -40.0),),
            ),
            _observation(
                ROUND - 1,
                source=self.other,
                recipients=(self.other,),
                magnitudes=((self.other, 20.0),),
                statuses=("heal",),
            ),
        )
        snapshot, _reads, _roster, _context = _decision(
            self.actor, (self.ally,), (self.enemy, self.other),
            observations=observations,
        )
        threat = observed_threat(
            snapshot,
            hostiles=self.front,
            allies=(stable_identity(self.actor), stable_identity(self.ally)),
            friendly_capacity=200.0,
            hostile_capacity=200.0,
        )
        self.assertTrue(isclose(threat[stable_identity(self.enemy)], 0.2))
        self.assertTrue(isclose(threat[stable_identity(self.other)], 0.05))

    @covers_requirement(
        "monster-ai-observed-coordination::threat-remains-an-observed-soft-preference"
    )
    def test_a_landed_hostile_mount_is_one_bounded_control_unit(self):
        # The compact record observes the mount itself, never its magnitude, so
        # one landed foreign mount on this actor's side counts as one bounded
        # unit of 1/200. A self-bound mount, a mount the record reports as
        # neutralized and an item's status keys establish no mount on this
        # side, so each contributes nothing.
        landed = (
            _observation(
                ROUND,
                source=self.enemy,
                recipients=(self.ally,),
                magnitudes=(),
                statuses=("buff_applied",),
            ),
        )
        snapshot, _reads, _roster, _context = _decision(
            self.actor, (self.ally,), (self.enemy, self.other),
            observations=landed,
        )
        threat = observed_threat(
            snapshot,
            hostiles=self.front,
            allies=(stable_identity(self.actor), stable_identity(self.ally)),
            friendly_capacity=200.0,
            hostile_capacity=200.0,
        )
        self.assertTrue(isclose(threat[stable_identity(self.enemy)], 1.0 / 200.0))
        self.assertEqual(threat[stable_identity(self.other)], 0.0)

        ambiguous = (
            _observation(
                ROUND,
                source=self.enemy,
                recipients=(self.ally,),
                magnitudes=(),
                statuses=("self_buff_applied",),
            ),
            _observation(
                ROUND,
                source=self.enemy,
                recipients=(self.ally,),
                magnitudes=(),
                statuses=("buff_applied", "equipment_immune"),
            ),
            _observation(
                ROUND,
                source=self.enemy,
                recipients=(self.ally,),
                magnitudes=(),
                statuses=("t_coo_status_key",),
            ),
            # A mount that also carried an observed magnitude is valued once,
            # through that magnitude, never twice.
            _observation(
                ROUND,
                source=self.enemy,
                recipients=(self.ally,),
                magnitudes=((self.ally, 5.0),),
                statuses=("buff_applied",),
            ),
        )
        snapshot, _reads, _roster, _context = _decision(
            self.actor, (self.ally,), (self.enemy, self.other),
            observations=ambiguous,
        )
        threat = observed_threat(
            snapshot,
            hostiles=self.front,
            allies=(stable_identity(self.actor), stable_identity(self.ally)),
            friendly_capacity=200.0,
            hostile_capacity=200.0,
        )
        self.assertEqual(set(threat.values()), {0.0})

    @covers_requirement(
        "monster-ai-observed-coordination::threat-remains-an-observed-soft-preference"
    )
    def test_a_mount_that_also_aimed_at_the_other_side_is_not_our_control(self):
        # One status set covers a whole action, so a record that also reached
        # the other side cannot establish that its mount landed here: the
        # opponent buffed its own ally while nothing was mounted on ours, and
        # the unestablished recipient contributes zero rather than an invented
        # unit of control.
        observations = (
            _observation(
                ROUND,
                source=self.enemy,
                recipients=(self.other, self.ally),
                magnitudes=(),
                statuses=("buff_applied",),
            ),
        )
        snapshot, _reads, _roster, _context = _decision(
            self.actor, (self.ally,), (self.enemy, self.other),
            observations=observations,
        )
        threat = observed_threat(
            snapshot,
            hostiles=self.front,
            allies=(stable_identity(self.actor), stable_identity(self.ally)),
            friendly_capacity=200.0,
            hostile_capacity=200.0,
        )
        self.assertEqual(set(threat.values()), {0.0})

    @covers_requirement(
        "monster-ai-observed-coordination::threat-remains-an-observed-soft-preference"
    )
    def test_unknown_outcomes_and_absent_members_contribute_nothing(self):
        # A source the decision cannot identify, a recipient outside the
        # applicable domain and a magnitude left on an identity the eligible
        # domain no longer contains (the ally died) each contribute nothing:
        # the projection reads only the domains this decision actually covers.
        self.ally.traits.hp.current = 0
        observations = (
            _observation(
                ROUND,
                source="key:ghost",
                recipients=(self.ally,),
                magnitudes=((self.ally, -60.0),),
            ),
            _observation(
                ROUND,
                source=self.enemy,
                recipients=(self.ally,),
                magnitudes=((self.ally, -60.0),),
            ),
            _observation(
                ROUND,
                source=self.enemy,
                recipients=("dbref:999999",),
                magnitudes=(("dbref:999999", -60.0),),
            ),
        )
        snapshot, _reads, roster, context = _decision(
            self.actor, (self.ally,), (self.enemy, self.other),
            observations=observations,
        )
        pool = decision_pool(snapshot, self.actor, roster, context)
        allies = group_members(KIND_FRIENDLY, snapshot, pool)
        self.assertNotIn(
            stable_identity(self.ally),
            {stable_identity(entity) for entity in allies},
        )
        threat = observed_threat(
            snapshot,
            hostiles=self.front,
            allies=tuple(stable_identity(entity) for entity in allies),
            friendly_capacity=200.0,
            hostile_capacity=200.0,
        )
        self.assertEqual(set(threat.values()), {0.0})

    @covers_requirement(
        "monster-ai-observed-coordination::threat-remains-an-observed-soft-preference"
    )
    def test_the_threat_valuing_strategy_averages_the_observed_rank(self):
        # One authored preference rank and nothing else, two equal-power
        # opponents and one observed hostile strike against this side:
        # highest_effective_power averages the tied static rank (1.0) with the
        # observed-threat ranks (1.0 and 0.0), so the opponent that struck
        # keeps 1.0 and the other half of the scale becomes 0.5; lowest_hp is
        # untouched by the same observations.
        self._equal_power(self.enemy, self.other)
        weights = dict.fromkeys(behaviour.UTILITY_WEIGHT_NAMES, 0.0)
        weights["preference"] = 1.0
        observations = (
            _observation(
                ROUND,
                source=self.enemy,
                recipients=(self.ally,),
                magnitudes=((self.ally, -40.0),),
            ),
        )
        self.assertTrue(threat_is_valued("highest_effective_power"))
        self.assertFalse(threat_is_valued("lowest_hp"))

        pressured, _ = self._score(
            (STRIKE.key,),
            weights=weights,
            observations=observations,
            target_strategy="highest_effective_power",
        )
        untouched, _ = self._score(
            (STRIKE.key,),
            weights=weights,
            observations=observations,
            target_strategy="lowest_hp",
        )
        baseline, _ = self._score(
            (STRIKE.key,),
            weights=weights,
            target_strategy="highest_effective_power",
        )
        lowest_baseline, _ = self._score(
            (STRIKE.key,), weights=weights, target_strategy="lowest_hp"
        )
        self.assertTrue(
            isclose(self._plan_for(pressured, self.enemy).score, 1.0)
        )
        self.assertTrue(
            isclose(self._plan_for(pressured, self.other).score, 0.5 / 3.0 + 2.0 / 3.0)
        )
        self.assertGreater(
            self._plan_for(pressured, self.enemy).score,
            self._plan_for(pressured, self.other).score,
        )
        self.assertEqual(
            [item.score for item in untouched],
            [item.score for item in lowest_baseline],
        )
        self.assertEqual(
            [item.score for item in baseline],
            [item.score for item in lowest_baseline],
        )

    @covers_requirement(
        "monster-ai-observed-coordination::threat-remains-an-observed-soft-preference"
    )
    def test_a_non_positive_history_keeps_the_static_rank_alone(self):
        # An allied recovery is genuinely observed but takes nothing from this
        # side, so no opponent has positive threat and the threat-valuing
        # strategy's ranks are exactly the static ones.
        self._equal_power(self.enemy, self.other)
        weights = dict.fromkeys(behaviour.UTILITY_WEIGHT_NAMES, 0.0)
        weights["preference"] = 1.0
        self.ally.traits.hp.current = 40
        observations = (
            _observation(
                ROUND,
                source=self.ally,
                recipients=(self.ally,),
                magnitudes=((self.ally, 20.0),),
                statuses=("heal",),
            ),
        )
        observed, _ = self._score(
            (STRIKE.key,),
            weights=weights,
            observations=observations,
            target_strategy="highest_effective_power",
        )
        baseline, _ = self._score(
            (STRIKE.key,),
            weights=weights,
            target_strategy="highest_effective_power",
        )
        self.assertEqual(
            [item.score for item in observed], [item.score for item in baseline]
        )

    @covers_requirement(
        "monster-ai-observed-coordination::threat-remains-an-observed-soft-preference"
    )
    def test_a_mandatory_seal_still_excludes_the_pressured_opponent(self):
        # The strongest observed pressure is the opponent outside the active
        # seal: the mandatory single-target restriction converges every strike
        # onto the bearer and removes that opponent before scoring, so no
        # observed value can bring it back as a plan.
        from world.rules.buffs import apply_buff
        from world.rules.monster_ai.candidates import SEAL_BUFF_KEY

        apply_buff(self.enemy, SEAL_BUFF_KEY)
        observations = (
            _observation(
                ROUND,
                source=self.ally,
                recipients=(self.other,),
                magnitudes=((self.other, -90.0),),
            ),
        )
        scored, _estimates = self._score(
            (STRIKE.key,),
            observations=observations,
            target_strategy="highest_effective_power",
        )
        self.assertTrue(scored)
        pressured = stable_identity(self.other)
        self.assertNotIn(
            pressured,
            {identity for item in scored for identity in item.identity.target_ids},
        )
        # The identity is not a legal candidate at all, so it is not merely a
        # zero-scored option either: the bearer is the only remaining plan.
        self.assertEqual(
            {item.identity.target_ids for item in scored},
            {(stable_identity(self.enemy),)},
        )


class CoordinationScoreTests(CoordinationFixture):
    """The completed score adds one intelligence-scaled focus term."""

    @covers_requirement(
        "monster-ai-observed-coordination::completed-coordination-is-reproducible-and-intelligence-scaled"
    )
    def test_the_focus_term_scales_with_intelligence(self):
        # Independently known: the ally's strike leaves the first opponent at
        # full relative focus (1.0) and the second at zero, and the term is
        # i * w_focus * focus, so at intelligence 50 (i = 0.5) and weight 2 it
        # adds exactly 1.0 to the pressured plan and nothing to the other.
        weights = dict.fromkeys(behaviour.UTILITY_WEIGHT_NAMES, 0.0)
        weights["damage"] = 1.0
        weights["focus"] = 2.0
        observations = (
            _observation(
                ROUND,
                source=self.ally,
                recipients=(self.enemy,),
                magnitudes=((self.enemy, -40.0),),
            ),
        )
        scored, estimates = self._score(
            (STRIKE.key,), weights=weights, intelligence=50, observations=observations
        )
        paired = {item.identity: item for item in estimates.estimates}
        for item in scored:
            expected = (
                paired[item.identity].damage.value
                + 0.5 * 2.0 * item.focus
            )
            self.assertTrue(isclose(item.score, expected), (item.score, expected))
        pressured = self._plan_for(scored, self.enemy)
        untouched = self._plan_for(scored, self.other)
        self.assertEqual(pressured.focus, 1.0)
        self.assertEqual(untouched.focus, 0.0)
        self.assertTrue(
            isclose(
                pressured.score - untouched.score,
                paired[pressured.identity].damage.value
                + 1.0
                - paired[untouched.identity].damage.value,
            )
        )

    @covers_requirement(
        "monster-ai-observed-coordination::completed-coordination-is-reproducible-and-intelligence-scaled"
    )
    def test_zero_intelligence_earns_no_focus_credit(self):
        # Intelligence buys no stats: at intelligence zero the same observed
        # history is worth exactly nothing, so the scored result equals the
        # same decision scored with the focus weight removed.
        weights = dict.fromkeys(behaviour.UTILITY_WEIGHT_NAMES, 0.0)
        weights["damage"] = 1.0
        weights["focus"] = 4.0
        observations = (
            _observation(
                ROUND,
                source=self.ally,
                recipients=(self.enemy,),
                magnitudes=((self.enemy, -40.0),),
            ),
        )
        credited, _ = self._score(
            (STRIKE.key,), weights=weights, intelligence=0, observations=observations
        )
        silenced, _ = self._score(
            (STRIKE.key,),
            weights=dict(weights, focus=0.0),
            intelligence=0,
            observations=observations,
        )
        self.assertEqual(
            [item.score for item in credited], [item.score for item in silenced]
        )
        self.assertEqual([item.focus for item in credited], [1.0, 0.0])

    @covers_requirement(
        "monster-ai-observed-coordination::completed-coordination-is-reproducible-and-intelligence-scaled"
    )
    def test_every_completed_term_is_present_with_a_real_history(self):
        # The whole completed formula term by term: one owned mana-costing
        # single-target strike and one free heal, two equal opponents, a
        # wounded ally and one observed strike. Every preference component is
        # known -- one shape ranks every plan at the top, the target metric
        # ties both opponents, and the strike is the first owned key while the
        # heal's later position and its lack of a hostile recipient pull it to
        # half -- and the cost term is genuinely non-zero. Neither skill mounts
        # anything, so the control term stays zero here; the support suite
        # establishes the mount model it belongs to.
        self._equal_power(self.enemy, self.other)
        weights = dict.fromkeys(behaviour.UTILITY_WEIGHT_NAMES, 1.0)
        self.ally.traits.hp.current = 40
        observations = (
            _observation(
                ROUND,
                source=self.ally,
                recipients=(self.enemy,),
                magnitudes=((self.enemy, -40.0),),
            ),
        )
        scored, estimates = self._score(
            (COSTLY.key, HEAL.key),
            weights=weights,
            intelligence=100,
            observations=observations,
        )
        paired = {item.identity: item for item in estimates.estimates}
        expected_preference = {
            COSTLY.key: 1.0,
            HEAL.key: (1.0 + 0.0 + 0.5) / 3.0,
        }
        for item in scored:
            estimate = paired[item.identity]
            self.assertTrue(
                isclose(
                    item.preference, expected_preference[item.identity.skill_key]
                ),
                (item.identity.skill_key, item.preference),
            )
            expected = (
                estimate.damage.value
                + estimate.healing.value
                + item.preference
                + (
                    estimate.finishing
                    + estimate.control.value
                    + item.focus
                    - estimate.cost
                    - estimate.waste.magnitude
                )
            )
            self.assertTrue(isclose(item.score, expected), (item.score, expected))
        self.assertTrue(any(item.healing > 0 for item in scored))
        self.assertTrue(any(item.focus > 0 for item in scored))
        self.assertTrue(
            any(
                item.identity.skill_key == COSTLY.key and item.cost > 0.0
                for item in estimates.estimates
            )
        )


class CoordinationTraceTests(CoordinationFixture):
    """The trace records the observation snapshot a replay needs."""

    @covers_requirement(
        "monster-ai-observed-coordination::completed-coordination-is-reproducible-and-intelligence-scaled"
    )
    def test_the_recorded_observation_snapshot_replays_the_decision(self):
        # A record of the initial observations, replayed into an identical
        # decision, reproduces the same snapshot fingerprint and the same
        # scores: same-process replay needs those observations, the state, the
        # scope and the tuning -- the session id alone proves nothing.
        observations = (
            _observation(
                ROUND,
                source=self.ally,
                recipients=(self.enemy,),
                magnitudes=((self.enemy, -40.0),),
            ),
            _observation(
                ROUND - 1,
                source=self.enemy,
                recipients=(self.ally,),
                magnitudes=((self.ally, -10.0),),
            ),
        )
        weights = dict.fromkeys(behaviour.UTILITY_WEIGHT_NAMES, 0.0)
        weights["damage"] = 1.0
        weights["focus"] = 3.0
        first, _ = self._score(
            (STRIKE.key,), weights=weights, observations=observations
        )
        snapshot, _reads, _roster, _context = _decision(
            self.actor, (self.ally,), (self.enemy, self.other),
            observations=observations,
        )
        recorded = trace_observations(snapshot)
        self.assertEqual(len(recorded), len(observations))
        self.assertEqual(recorded[0][0], ROUND)
        self.assertEqual(recorded[0][4], "t_coo_action")
        self.assertEqual(list(recorded[0][5]), [stable_identity(self.enemy)])
        self.assertEqual([list(pair) for pair in recorded[0][6]], [
            [stable_identity(self.enemy), -40.0]
        ])

        replayed = tuple(
            PublicObservation(
                round_index=record[0],
                sequence=record[1],
                source_id=record[2],
                source_faction=record[3],
                action_key=record[4],
                recipient_ids=tuple(record[5]),
                magnitudes=tuple(
                    (pair[0], float(pair[1])) for pair in record[6]
                ),
                statuses=tuple(record[7]),
            )
            for record in recorded
        )
        rebuilt, _reads, _roster, _context = _decision(
            self.actor, (self.ally,), (self.enemy, self.other),
            observations=replayed,
        )
        self.assertEqual(rebuilt.fingerprint, snapshot.fingerprint)

        replayed_scored, _ = self._score(
            (STRIKE.key,), weights=weights, observations=replayed
        )
        self.assertEqual(
            [item.score for item in replayed_scored],
            [item.score for item in first],
        )
        self.assertEqual(
            [item.focus for item in replayed_scored],
            [item.focus for item in first],
        )

        # The recorded choice repeats: identical observations, state, scope and
        # tuning rebuild the same seed over the same scored set, so the same
        # candidate is selected rather than merely the same score reached.
        temperature = selection_temperature(50)
        seed = selection_seed_for(
            scope=None,
            actor_id=stable_identity(self.actor),
            configuration_fingerprint=behaviour.MONSTER_AI_TUNING.fingerprint,
            snapshot_fingerprint=snapshot.fingerprint,
        )
        self.assertEqual(
            select_candidate(first, temperature=temperature, seed=seed).identity,
            select_candidate(
                replayed_scored, temperature=temperature, seed=seed
            ).identity,
        )

        # The replay evidence is immutable all the way down, so the JSON a
        # report exports from it shares no mutable value with the record the
        # decision reproduced and cannot rewrite it.
        self.assertIsInstance(recorded[0], tuple)
        self.assertIsInstance(recorded[0][5], tuple)
        self.assertIsInstance(recorded[0][6], tuple)
        self.assertIsInstance(recorded[0][6][0], tuple)
        trace = DecisionTrace(
            scope=(SESSION, ROUND, stable_identity(self.actor), 0, "normal"),
            inspected=False,
            algorithm_version=behaviour.AI_ALGORITHM_VERSION,
            configuration_fingerprint=behaviour.MONSTER_AI_TUNING.fingerprint,
            snapshot_fingerprint=snapshot.fingerprint,
            intelligence=50,
            temperature=temperature,
            seed=seed,
            candidates=len(first),
            observations=recorded,
        )
        payload = trace.to_payload()
        payload["observations"][0] = ["t_coo_mutated"]
        payload["observations"].append(["t_coo_mutated"])
        self.assertEqual(trace.observations, recorded)
        self.assertEqual(trace.observations[0][0], ROUND)


class CoordinationRoundTests(EvenniaTestCase):
    """Real rounds: settled actions coordinate pack hunters, profiles stay apart."""

    def setUp(self):
        _scope(self)
        _suppress_innate_skills(self)
        super().setUp()
        book = _rulebook()
        profiles = behaviour._load_behaviour_profiles(book, tiers={TIER})
        tuning = behaviour._load_ai_tuning(
            book, profiles=profiles, species=_SPECIES_ROWS, variants=_VARIANT_ROWS
        )
        patcher = patch.multiple(
            behaviour,
            MONSTER_BEHAVIOUR_YAML=book,
            BEHAVIOUR_PROFILES=profiles,
            MONSTER_AI_TUNING=tuning,
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.room = create_object(Room, key="coordination round arena")

    def _monster(self, key, *, variant=VARIANT, skills=(STRIKE.key,)):
        monster = construct_species_individual(SPECIES, variant, key=key)
        monster.location = self.room
        monster.db.skills = {"active": list(skills), "passive": []}
        return monster

    def _party_member(self, key, hp):
        entity = _player(key)
        entity.location = self.room
        entity.traits.hp.base = hp
        entity.traits.hp.current = hp
        entity.traits.atk_phys.base = 20
        entity.traits.agility.base = 20
        entity.traits.defense.base = 10
        entity.traits.magic_power.base = 30
        return entity

    @covers_requirement(
        "monster-ai-observed-coordination::completed-coordination-is-reproducible-and-intelligence-scaled"
    )
    def test_coordination_starts_only_after_the_settled_action(self):
        first = self._monster("t_coo_first")
        second = self._monster("t_coo_second")
        target = _player("t_coo_target")
        target.location = self.room
        target.traits.hp.base = 1000
        target.traits.hp.current = 1000
        field = Battlefield(
            {
                "monsters": frozenset({str(first.key), str(second.key)}),
                "party": frozenset({str(target.key)}),
            },
            {
                str(first.key): first,
                str(second.key): second,
                str(target.key): target,
            },
        )
        traces: dict[str, list] = {}

        def provider(entity, battlefield):
            if entity.key not in (first.key, second.key):
                return None
            return behaviour.monster_behaviour_policy(
                entity, battlefield, trace=traces.setdefault(str(entity.key), [])
            )

        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch("world.rules.combat.rounds.roll_d100", return_value=100),
            self.captureOnCommitCallbacks(execute=True),
        ):
            run_round(
                field,
                provider,
                decision_scope_base=ExecutionScopeBase(SUPPORT_SESSION, ROUND),
                first_actor=str(first.key),
            )

        warned = traces[str(first.key)][0]
        following = traces[str(second.key)][0]
        # The first decision saw nothing settled yet: its own score adds no
        # observed focus, because the round has resolved no action at all.
        self.assertEqual(warned.observations, ())
        self.assertTrue(warned.plans)
        self.assertEqual({plan.focus for plan in warned.plans}, {0.0})
        # The second decision, in the same transaction, sees the first one's
        # resolved strike and presses the target it already hit.
        self.assertTrue(following.observations)
        self.assertEqual(
            [record[0] for record in following.observations], [ROUND]
        )
        self.assertEqual(following.observations[0][2], stable_identity(first))
        self.assertGreater(following.selected.focus, 0.0)
        self.assertEqual(
            following.selected.target_ids, (stable_identity(target),)
        )
        # A real resolution: the target lost committed health and the acting
        # monsters' own stored health is untouched by their decisions.
        committed = float(
            ObjectDB.objects.get(id=target.pk)
            .attributes.get("traits", default={}, category="traits")["hp"]["current"]
        )
        self.assertLess(committed, 1000.0)
        for monster in (first, second):
            self.assertEqual(float(monster.traits.hp.current), float(monster.traits.hp.max))

    @covers_requirement(
        "monster-ai-observed-coordination::completed-coordination-is-reproducible-and-intelligence-scaled"
    )
    def test_a_support_profile_keeps_healing_while_the_pack_presses(self):
        # Real teamwork with a profile distinction over the same shipped
        # engines: two pack hunters and one support variant act in one
        # production round against two equal opponents. The settled strike
        # makes the next hunter press that exact opponent, while the support
        # variant -- which values recovery alone -- keeps its own recovery as
        # the best plan it can propose instead of turning the history into an
        # attack.
        first = self._monster("t_coo_first")
        second = self._monster("t_coo_second")
        healer = self._monster(
            "t_coo_healer", variant=VARIANT_SUPPORT, skills=(HEAL.key,)
        )
        struck = self._party_member("t_coo_struck", 1000)
        bystander = self._party_member("t_coo_bystander", 1000)
        healer.traits.hp.current = float(healer.traits.hp.max) * 0.4
        monsters = (first, second, healer)
        party = (struck, bystander)
        field = Battlefield(
            {
                "monsters": frozenset(str(entity.key) for entity in monsters),
                "party": frozenset(str(entity.key) for entity in party),
            },
            {str(entity.key): entity for entity in (*monsters, *party)},
        )
        traces: dict[str, list] = {}

        def provider(entity, battlefield):
            if entity.key not in (first.key, second.key, healer.key):
                return None
            return behaviour.monster_behaviour_policy(
                entity, battlefield, trace=traces.setdefault(str(entity.key), [])
            )

        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch("world.rules.combat.rounds.roll_d100", return_value=100),
            self.captureOnCommitCallbacks(execute=True),
        ):
            run_round(
                field,
                provider,
                decision_scope_base=ExecutionScopeBase(SESSION, ROUND),
                first_actor=str(first.key),
            )

        opening = traces[str(first.key)][0]
        following = traces[str(second.key)][0]
        support = traces[str(healer.key)][0]
        committed = {
            stable_identity(entity): float(
                ObjectDB.objects.get(id=entity.pk)
                .attributes.get("traits", default={}, category="traits")["hp"][
                    "current"
                ]
            )
            for entity in party
        }
        # Nothing has settled when the round opens, and the strike the first
        # hunter then resolves is committed health loss the next hunter has to
        # work with.
        self.assertEqual(opening.observations, ())
        settled = opening.selected.target_ids
        self.assertEqual(len(settled), 1)
        self.assertIn(
            settled[0],
            [identity for identity, hp in committed.items() if hp < 1000.0],
        )
        self.assertIn(stable_identity(first), [row[2] for row in following.observations])

        # Pressing the already-pressed opponent is the hunter's best plan, and
        # it is strictly better than the untouched one: only observed history
        # separates two otherwise equal candidates.
        pressed = max(following.plans, key=lambda plan: plan.score)
        untouched = next(
            plan for plan in following.plans if plan.target_ids != settled
        )
        self.assertEqual(pressed.target_ids, settled)
        self.assertGreater(pressed.focus, 0.0)
        self.assertEqual(untouched.focus, 0.0)
        self.assertGreater(pressed.score, untouched.score)

        # The support profile is a different archetype, not a different
        # mechanic: its best plan is still its own recovery, which carries no
        # observed pressure at all.
        healing = max(support.plans, key=lambda plan: plan.score)
        self.assertEqual(healing.skill_key, HEAL.key)
        self.assertEqual(healing.target_ids, (stable_identity(healer),))
        self.assertGreater(healing.healing, 0.0)
        self.assertEqual(healing.focus, 0.0)
        # Sampling may still pick a no-op recovery on an unwounded teammate,
        # but every plan this profile proposes is a recovery on its own side
        # and the pressured opponent is never one of its recipients.
        self.assertEqual(support.selected.skill_key, HEAL.key)
        self.assertIn(
            support.selected.target_ids,
            {
                (stable_identity(healer),),
                (stable_identity(first),),
                (stable_identity(second),),
            },
        )