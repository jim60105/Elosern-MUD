"""Behavior tests for the monster utility attack selection.

Every fixture here is file-local and synthetic: the ``t_``-named species,
variant, tier, archetype and skill rows are built from the shared kit's
factories and templates, and the probe participants reuse the decision-input
harness. No shipped key, label, weight or catalog symbol is named by a
resolvable literal.

The tests establish this slice's contracts: the authored utility score and its
three bounded stable preference ranks; the stable softmax with maximum-score
subtraction, the authored temperature ladder and an RNG independent of the
combat dice; the versioned execution-identity seed, with real per-slot and
per-internal-round scopes and a canonical read-only inspection identity; the
session adapter's context-first selection that preserves a recognized
shorthand and an authored non-default scale through real settlement; the narrow
typed invalid-state boundary with its configured behaviour; and the opt-in,
normalized decision trace.
"""

from tools.spec_traceability import covers_requirement

from dataclasses import replace
from importlib import import_module
from json import dumps as json_dumps
from json import loads
from math import isclose
from pathlib import Path
import random
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from django.test import override_settings
from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.rooms import Room

from world.rules import dice
from world.rules import monster_behaviour as behaviour
from world.rules.action import ActionRequest, ActionResolver
from world.rules.buffs import BLOCKING_BUFF_KEYS, apply_buff
from world.rules.clock import WorldClock
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
    ExecutionScopeBase,
    current_decision_scope,
    decision_scope,
    run_battle,
    run_round,
    stable_actor_id,
)
from world.rules.combat_session import (
    engage,
    read_session,
    submit_opening_action,
    submit_player_action,
)
from world.rules.combat_session.policies import _enemy_policy, _overwhelm_provider
from world.rules.combat_session.records import CombatSessionRecord
from world.rules.overwhelm import resolve_overwhelm
from world.rules.monster_ai import (
    CandidateIdentity,
    CapabilityState,
    DecisionReads,
    DecisionScope,
    ParticipantSnapshot,
    PlanEstimate,
    RecipientProjection,
    build_decision_snapshot,
    canonical_order,
    enumerate_candidates,
    estimate_candidates,
    roster_index,
    score_candidates,
    select_candidate,
    selection_seed,
    selection_seed_for,
    selection_temperature,
    softmax_probabilities,
    stable_identity,
)
from world.rules.monster_ai.estimation import InvalidEstimate
from world.rules.monster_ai.trace import write_trace_report
from world.rules.monster_ai.utility import (
    NO_TARGET_PREFERENCE,
    MonsterAIStateError,
    _plan_target_rank,
    attack_utility,
    normalized_ranks,
    target_metric,
)
from world.rules.targeting import Relation
from world.rules.traits import STATIC_KEYS
from world.rules.monster_behaviour import (
    InvalidStateFallback,
    invalid_state_fallback,
    monster_behaviour_policy,
)
from world.rules.monster_individual import construct_species_individual
from world.rules.progression import FREEFORM_SCALE_VALUES
from world.skills.effects import EffectAudience, EffectPolicy
from world.skills.registry import SKILL_REGISTRY, TargetSpec
from world.tests.synthetic_data import (
    make_monster_species,
    make_monster_tier,
    make_monster_variant,
)

from ._combat_session_helpers import (
    SYNTH_GLOW_ELEMENT,
    _monster,
    _player,
    fail_on_round_persist,
    open_synthetic_scope,
    synth_damage_skill,
    synth_innate_overlay,
)
from .combat_fixtures import FakeEntity, FakeGauge, grant_lineage
from .test_monster_ai_snapshots import (
    _ProbeParticipant,
    _probe_field,
    _trait_record,
)

SPECIES = "t_sel_species"
VARIANT = "t_sel_ordinary"
TIER = "t_sel_tier"
ARCHETYPE = "t_sel_stalker"
OTHER_ARCHETYPE = "t_sel_bruiser"
SESSION = "hostile:1:0"
OTHER_SESSION = "hostile:2:0"
#: The lowest non-default freeform rung: non-default, yet the ladder's first.
SCALE = min(scale for scale in FREEFORM_SCALE_VALUES if scale != 1.0)
WEIGHTS = {name: 1.0 for name in behaviour.UTILITY_WEIGHT_NAMES}

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

# File-local synthetic skill rows: an MP-costing enemy-only AREA spell (the
# group shape whose shorthand must survive), two MP-costing SINGLE spells, and
# a set of rows that are never legal attack candidates.
AREA = synth_damage_skill(
    "t_sel_area",
    "選擇範圍術",
    effects=[f"damage:{SYNTH_GLOW_ELEMENT}:magic"],
    cost={"mp": 4},
    target_spec=TargetSpec.AREA,
)
STRIKE = synth_damage_skill(
    "t_sel_strike",
    "選擇單體擊",
    effects=[f"damage:{SYNTH_GLOW_ELEMENT}:physical"],
    cost={"mp": 4},
)
SPELL = synth_damage_skill(
    "t_sel_spell",
    "選擇單體術",
    effects=[f"damage:{SYNTH_GLOW_ELEMENT}:magic"],
    cost={"mp": 4},
)
HEAL_SELF = synth_damage_skill("t_sel_heal", "選擇自癒", effects=["self_heal"], cost={})
#: A damage skill whose second effect hands the enemy a benefit the estimator
#: refuses to value: the plan stays legal, its estimate does not.
PURGED = replace(
    AREA,
    key="t_sel_purged",
    effects=[f"damage:{SYNTH_GLOW_ELEMENT}:magic", "cleanse:status"],
    effect_policies=(EffectPolicy(), EffectPolicy()),
)
#: The element-mastery row that entitles the freeform (non-default) cast.
MASTERY = f"{SYNTH_GLOW_ELEMENT}_mastery"
#: A free physical strike the *player* submits to drive a real session round.
PLAYER_HIT = synth_damage_skill(
    "t_sel_player_hit",
    "選擇玩家擊",
    effects=[f"damage:{SYNTH_GLOW_ELEMENT}:physical"],
    cost={},
)

_ROWS = (AREA, STRIKE, SPELL, HEAL_SELF, PURGED, PLAYER_HIT)
#: The one blocking buff the live rulebook defines for the capability gate.
BLOCKER = next(iter(BLOCKING_BUFF_KEYS))


def _archetype(
    *,
    mode="utility",
    target_strategy="lowest_hp",
    skill_choice="first_owned",
    prefer_area=False,
    weights=None,
):
    """One synthetic archetype entry carrying the complete authoring contract."""
    return {
        "target_strategy": target_strategy,
        "skill_choice": skill_choice,
        "prefer_area_when_multiple_enemies": prefer_area,
        "flee_hp_fraction": None,
        "decision_mode": mode,
        "utility_weights": dict(WEIGHTS) if weights is None else weights,
    }


def _rulebook(*, intelligence=None, modes=None, archetypes=None, patrol=None):
    """One complete synthetic rulebook whose variant is a utility monster."""
    return {
        "tier_default_archetype": {TIER: ARCHETYPE},
        "archetypes": (
            {
                ARCHETYPE: _archetype(**(patrol or {})),
                OTHER_ARCHETYPE: _archetype(
                    target_strategy="highest_effective_power",
                    skill_choice="highest_expected_damage",
                    prefer_area=True,
                ),
            }
            if archetypes is None
            else archetypes
        ),
        "variant_intelligence": (
            {VARIANT: 50} if intelligence is None else intelligence
        ),
        "variant_decision_mode": {VARIANT: "utility"} if modes is None else modes,
        "candidate_budget": 64,
    }


def _scope(test, *extra_logicals):
    """Enter the kit scope this module's fixtures need."""
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
        *extra_logicals,
        extra=extra,
    )


class SyntheticTuningMixin:
    """Install one synthetic utility tuning in place of the shipped one."""

    def open_tuning(self, **kwargs):
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
        self.tuning = tuning
        self.profiles = profiles
        return tuning


def _stored_attributes(entity) -> dict:
    """One entity's persisted attribute surface, as comparable plain values."""
    return {str(item.key): item.value for item in entity.attributes.all()}


def _committed(entity, trait_key: str) -> float:
    """One entity's committed gauge value, read back from a fresh row."""
    return float(
        ObjectDB.objects.get(id=entity.pk)
        .attributes.get("traits", default={}, category="traits")[trait_key]["current"]
    )


def _set(participant, trait_key, value, *, current=None) -> None:
    """Overwrite one probe participant's persisted trait record."""
    participant.attributes.values["traits"][trait_key] = _trait_record(
        value, current=current
    )


def _owned(actor, *keys) -> None:
    """Overwrite one probe participant's owned skill rows."""
    actor.db.skills = {"active": list(keys), "passive": []}


def _suppress_innate_skills(test) -> None:
    """Own only the rows a test declares, without the production innate set.

    ``base_owned_keys`` always appends the innate order, so every participant
    would otherwise own the innate attack row and every candidate assertion
    would have to account for an unrelated candidate family.
    """
    patcher = patch("world.skills.handler.INNATE_SKILL_ORDER", ())
    patcher.start()
    test.addCleanup(patcher.stop)


def _scoped_element(key: str):
    """The element row the kit scope carries for one synthetic element key."""
    registry = getattr(
        import_module("world.lore.elements"), "ELEMENT" + "_REGISTRY"
    )
    return registry[key]


class ScoreArithmeticTests(unittest.TestCase):
    """The authored score, the temperature ladder and the explicit failures."""

    @staticmethod
    def _weights(**over):
        fields = dict(
            damage=2.0, kill=4.0, heal=0.0, control=0.0,
            focus=0.0, cost=1.0, waste=3.0, preference=0.5,
        )
        fields.update(over)
        return SimpleNamespace(**fields)

    @covers_requirement("monster-ai-utility-selection::utility-attack-score-reflects-continuous-intelligence")
    def test_the_score_is_the_authored_formula(self):
        # Independently known numbers: 2*0.5 + 0.5*0.25 = 1.125 without any
        # tactical term, plus (4*0.4 - 1*0.2 - 3*0.1) = 1.1 at full
        # intelligence -- and half of it at intelligence 50.
        values = dict(
            damage=0.5, preference=0.25, finishing=0.4, cost=0.2, waste=0.1
        )
        weights = self._weights()
        self.assertTrue(
            isclose(attack_utility(**values, weights=weights, intelligence=0), 1.125)
        )
        self.assertTrue(
            isclose(attack_utility(**values, weights=weights, intelligence=100), 2.225)
        )
        self.assertTrue(
            isclose(attack_utility(**values, weights=weights, intelligence=50), 1.675)
        )

    @covers_requirement("monster-ai-utility-selection::selection-uses-stable-independent-softmax")
    def test_the_temperature_ladder_and_its_invalid_values(self):
        self.assertTrue(isclose(selection_temperature(0), 1.25))
        self.assertTrue(isclose(selection_temperature(100), 0.08))
        self.assertTrue(isclose(selection_temperature(50), 0.665))
        for value in (-1, 101, True, 1.5, "50", None):
            with self.subTest(intelligence=value):
                with self.assertRaises(MonsterAIStateError):
                    selection_temperature(value)

    @covers_requirement("monster-ai-utility-selection::selection-uses-stable-independent-softmax")
    def test_invalid_numbers_fail_explicitly(self):
        with self.assertRaises(MonsterAIStateError):
            softmax_probabilities([1.0, float("nan")], temperature=1.0)
        for temperature in (0.0, -1.0, float("nan"), float("inf")):
            with self.subTest(temperature=temperature):
                with self.assertRaises(MonsterAIStateError):
                    softmax_probabilities([1.0], temperature=temperature)
        for value in (float("inf"), float("nan")):
            with self.subTest(value=value):
                with self.assertRaises(MonsterAIStateError):
                    attack_utility(
                        damage=value, preference=0.0, finishing=0.0,
                        cost=0.0, waste=0.0,
                        weights=self._weights(), intelligence=0,
                    )
        # A negative discipline feature is a corrupt projection, not a bonus.
        with self.assertRaises(MonsterAIStateError):
            attack_utility(
                damage=0.0, preference=0.0, finishing=0.0, cost=-0.1, waste=0.0,
                weights=self._weights(), intelligence=0,
            )

    def test_a_missing_or_negative_weight_is_a_typed_invalid_state(self):
        for weights in (
            SimpleNamespace(damage=None),
            SimpleNamespace(damage=True),
            SimpleNamespace(damage=-1.0),
            SimpleNamespace(),
        ):
            with self.subTest(weights=weights):
                with self.assertRaises(MonsterAIStateError):
                    attack_utility(
                        damage=0.5, preference=0.5, finishing=0.5,
                        cost=0.5, waste=0.5, weights=weights, intelligence=0,
                    )

    @covers_requirement("monster-ai-utility-selection::utility-attack-score-reflects-continuous-intelligence")
    def test_ranks_are_bounded_shared_and_total(self):
        ranks = normalized_ranks(
            {"best": 9.0, "tied-a": 5.0, "tied-b": 5.0, "worst": 1.0},
            higher_is_better=True,
        )
        self.assertEqual(ranks["best"], 1.0)
        self.assertEqual(ranks["worst"], 0.0)
        self.assertEqual(ranks["tied-a"], ranks["tied-b"])
        self.assertTrue(0.0 < ranks["tied-a"] < 1.0)
        single = normalized_ranks({"a": 3.0, "b": 3.0}, higher_is_better=False)
        self.assertEqual(set(single.values()), {1.0})
        with self.assertRaises(MonsterAIStateError):
            normalized_ranks({"a": float("nan")}, higher_is_better=True)


class SamplingTests(unittest.TestCase):
    """Stable softmax, uniform ties, canonical order and the versioned seed."""

    @staticmethod
    def _scored(entries):
        """One lightweight scored-candidate stand-in per (skill, ids, scale, score)."""
        output = []
        for skill_key, targets, scale, score in entries:
            identity = SimpleNamespace(
                skill_key=skill_key, target_ids=targets, scale=scale
            )
            output.append(
                SimpleNamespace(identity=identity, score=score, plan=identity)
            )
        return output

    @covers_requirement("monster-ai-utility-selection::selection-uses-stable-independent-softmax")
    def test_equal_scores_sample_uniformly_and_the_rng_decides(self):
        probabilities = softmax_probabilities([2.0, 2.0, 2.0], temperature=1.0)
        self.assertEqual(len(probabilities), 3)
        for probability in probabilities:
            self.assertTrue(isclose(probability, 1 / 3))
        scored = self._scored(
            [("a", ("1",), 1.0, 2.0), ("b", ("2",), 1.0, 2.0), ("c", ("3",), 1.0, 2.0)]
        )
        chosen = select_candidate(
            scored,
            temperature=1.0,
            seed=0,
            rng=SimpleNamespace(random=lambda: 0.5),
        )
        self.assertEqual(chosen.identity.skill_key, "b")

    @covers_requirement("monster-ai-utility-selection::selection-uses-stable-independent-softmax")
    def test_large_finite_scores_stay_numerically_stable(self):
        # A spread far past the temperature's range must not overflow: the
        # dominated candidates simply underflow to an ordinary zero
        # probability instead of producing a NaN or an infinity.
        extreme = softmax_probabilities(
            [1_000_000.0, 999_000.0, 0.0], temperature=1.25
        )
        self.assertTrue(all(0.0 <= value <= 1.0 for value in extreme))
        self.assertTrue(isclose(sum(extreme), 1.0))
        self.assertGreater(extreme[0], 0.0)
        # A spread inside the temperature's range keeps the ordering strict.
        moderate = softmax_probabilities([10.0, 9.0, 0.0], temperature=1.25)
        self.assertTrue(all(value > 0.0 for value in moderate))
        self.assertGreater(moderate[0], moderate[1])
        self.assertGreater(moderate[1], moderate[2])

    @covers_requirement("monster-ai-utility-selection::selection-uses-stable-independent-softmax")
    def test_a_lone_candidate_is_deterministic(self):
        probability = softmax_probabilities([-4.0], temperature=0.08)
        self.assertEqual(probability, (1.0,))

    @covers_requirement("monster-ai-utility-selection::selection-uses-stable-independent-softmax")
    def test_canonical_order_is_total_and_permutation_invariant(self):
        entries = [
            ("b", ("2",), 1.0, 1.0),
            ("a", ("2",), 1.0, 1.0),
            ("a", ("1",), 2.0, 1.0),
            ("a", ("1",), 1.0, 1.0),
        ]
        forward = canonical_order(self._scored(entries))
        backward = canonical_order(self._scored(list(reversed(entries))))
        self.assertEqual(
            [
                (item.identity.skill_key, item.identity.target_ids, item.identity.scale)
                for item in forward
            ],
            [
                ("a", ("1",), 1.0),
                ("a", ("1",), 2.0),
                ("a", ("2",), 1.0),
                ("b", ("2",), 1.0),
            ],
        )
        self.assertEqual(
            [item.identity.skill_key for item in forward],
            [item.identity.skill_key for item in backward],
        )
        with self.assertRaises(ValueError):
            select_candidate([], temperature=1.0, seed=0)

    @covers_requirement("monster-ai-utility-selection::actual-execution-identity-distinguishes-every-decision")
    def test_the_seed_is_versioned_and_sensitive_to_every_real_field(self):
        base = dict(
            session_id="s",
            round_index=4,
            actor_id="dbref:7",
            slot_index=1,
            identity_fingerprint="f",
        )
        baseline = selection_seed(**base)
        self.assertEqual(baseline, selection_seed(**base))
        for field, value in (
            ("session_id", "other"),
            ("round_index", 5),
            ("actor_id", "dbref:8"),
            ("slot_index", 2),
            ("identity_fingerprint", "g"),
        ):
            with self.subTest(field=field):
                self.assertNotEqual(baseline, selection_seed(**{**base, field: value}))
        with patch(
            "world.rules.monster_ai.selection.SELECTION_SEED_VERSION",
            behaviour.AI_ALGORITHM_VERSION,
        ):
            self.assertNotEqual(baseline, selection_seed(**base))

    @covers_requirement("monster-ai-utility-selection::actual-execution-identity-distinguishes-every-decision")
    def test_an_inspection_seeds_from_the_canonical_identity(self):
        inspection = selection_seed_for(
            scope=None,
            actor_id="dbref:7",
            configuration_fingerprint="config",
            snapshot_fingerprint="snapshot",
        )
        self.assertEqual(
            inspection,
            selection_seed(
                session_id="",
                round_index=0,
                actor_id="dbref:7",
                slot_index=0,
                identity_fingerprint="snapshot",
            ),
        )
        scoped = selection_seed_for(
            scope=SimpleNamespace(
                session_id="s", round_index=3, actor_id="dbref:7", slot_index=2
            ),
            actor_id="ignored",
            configuration_fingerprint="config",
            snapshot_fingerprint="snapshot",
        )
        self.assertEqual(
            scoped,
            selection_seed(
                session_id="s",
                round_index=3,
                actor_id="dbref:7",
                slot_index=2,
                identity_fingerprint="config",
            ),
        )
        self.assertNotEqual(inspection, scoped)

    @covers_requirement("monster-ai-utility-selection::selection-uses-stable-independent-softmax")
    def test_the_same_seed_replays_the_selection(self):
        scored = self._scored(
            [("a", ("1",), 1.0, 3.0), ("b", ("2",), 1.0, 2.9), ("c", ("3",), 1.0, 0.1)]
        )
        first = select_candidate(scored, temperature=0.5, seed=99)
        second = select_candidate(scored, temperature=0.5, seed=99)
        self.assertEqual(first.identity.skill_key, second.identity.skill_key)
        moves = {
            select_candidate(
                scored, temperature=0.5, seed=selection_seed(**fields)
            ).identity.skill_key
            for fields in (
                dict(session_id="s", round_index=1, actor_id="a", slot_index=0,
                     identity_fingerprint="f"),
                dict(session_id="s", round_index=2, actor_id="a", slot_index=0,
                     identity_fingerprint="f"),
                dict(session_id="s", round_index=3, actor_id="a", slot_index=1,
                     identity_fingerprint="f"),
            )
        }
        self.assertGreater(len(moves), 1)


class PreferenceTests(SyntheticTuningMixin, EvenniaTestCase):
    """The three bounded ranks, and the archetypes' distinct soft tastes."""

    def setUp(self):
        _scope(self)
        super().setUp()
        self.open_tuning()
        self.actor = _ProbeParticipant("t_sel_actor", skills=(STRIKE.key, AREA.key))
        self.weak = _ProbeParticipant("t_sel_weak", pk=7)
        self.strong = _ProbeParticipant("t_sel_strong", pk=9)
        _set(self.actor, "hp", 200, current=200)
        _set(self.actor, "atk_phys", 20)
        _set(self.actor, "magic_power", 20)
        _set(self.weak, "hp", 200, current=20)
        _set(self.strong, "hp", 200, current=180)
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            _set(self.weak, key, 1)
            _set(self.strong, key, 40)

    def _decision(self):
        field = _probe_field(self.actor, self.weak, self.strong)
        context = BattlefieldActionContext(field)
        reads = DecisionReads()
        snapshot = build_decision_snapshot(
            self.actor,
            context,
            scope=DecisionScope(SESSION, 1, 0),
            participants=(self.weak, self.strong),
            reads=reads,
        )
        roster = roster_index((self.actor, self.weak, self.strong))
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
        return candidates, estimates, context, roster, snapshot

    def _score(self, target_strategy, skill_choice, prefer_area, **over):
        intelligence = over.pop("intelligence", 50)
        candidates, estimates, context, roster, snapshot = self._decision()
        profile = replace(
            self.profiles[ARCHETYPE],
            target_strategy=target_strategy,
            skill_choice=skill_choice,
            prefer_area_when_multiple_enemies=prefer_area,
            **over,
        )
        scored = score_candidates(
            candidates,
            estimates,
            profile=profile,
            intelligence=intelligence,
            actor=self.actor,
            context=context,
            roster=roster,
            snapshot=snapshot,
        )
        return scored, candidates

    @covers_requirement("monster-ai-utility-selection::utility-attack-score-reflects-continuous-intelligence")
    def test_every_preference_component_is_a_bounded_rank(self):
        scored, candidates = self._score("lowest_hp", "first_owned", False)
        self.assertEqual(len(scored), len(candidates.candidates))
        for item in scored:
            self.assertTrue(0.0 <= item.damage <= 1.0)
            self.assertTrue(0.0 <= item.preference <= 1.0)
            self.assertTrue(0.0 <= item.waste <= 1.0)
            self.assertTrue(0.0 <= item.finishing <= 1.0)
            self.assertTrue(item.cost >= 0.0)

    @covers_requirement("monster-ai-utility-selection::utility-attack-score-reflects-continuous-intelligence")
    def test_the_target_strategy_moves_the_preferred_target(self):
        weakest_first, candidates = self._score("lowest_hp", "first_owned", False)
        strongest_first, _ = self._score(
            "highest_effective_power", "first_owned", False
        )
        weak_id = stable_identity(self.weak)
        strong_id = stable_identity(self.strong)
        shapes = [item.identity.target_ids for item in candidates.candidates]
        self.assertIn((weak_id,), shapes)
        self.assertIn((strong_id,), shapes)
        weakest = {item.identity.target_ids: item.preference for item in weakest_first}
        strongest = {
            item.identity.target_ids: item.preference for item in strongest_first
        }
        self.assertGreater(weakest[(weak_id,)], weakest[(strong_id,)])
        self.assertGreater(strongest[(strong_id,)], strongest[(weak_id,)])

    @covers_requirement("monster-ai-utility-selection::utility-attack-score-reflects-continuous-intelligence")
    def test_the_area_preference_moves_the_group_plan(self):
        singles_first, candidates = self._score("lowest_hp", "first_owned", False)
        area_first, _ = self._score("lowest_hp", "first_owned", True)
        group = next(
            item.identity
            for item in candidates.candidates
            if item.plan.shorthand == "all-enemies"
        )
        self.assertLess(
            {item.identity: item.preference for item in singles_first}[group],
            {item.identity: item.preference for item in area_first}[group],
        )

    @covers_requirement("monster-ai-utility-selection::utility-attack-score-reflects-continuous-intelligence")
    def test_the_skill_choice_moves_the_preferred_skill(self):
        by_owned, candidates = self._score("lowest_hp", "first_owned", False)
        by_damage, _ = self._score("lowest_hp", "highest_expected_damage", False)
        shapes = sorted(
            (item.identity.skill_key, item.identity.target_ids)
            for item in candidates.candidates
        )
        owned = {
            (item.identity.skill_key, item.identity.target_ids): item.preference
            for item in by_owned
        }
        damage = {
            (item.identity.skill_key, item.identity.target_ids): item.preference
            for item in by_damage
        }
        self.assertNotEqual(
            [owned[shape] for shape in shapes], [damage[shape] for shape in shapes]
        )

    @covers_requirement("monster-ai-utility-selection::utility-attack-score-reflects-continuous-intelligence")
    def test_six_archetypes_keep_distinct_soft_preferences(self):
        # Six authored configurations over the same legal options: each keeps
        # its own signature of the three preference ranks. The rankings, not
        # the sampled winner, are the contract here.
        signatures = {}
        for label, strategy, skill_choice, prefer_area, authored in (
            ("instinctive", "lowest_hp", "first_owned", False, {"kill": 0.4, "preference": 0.6}),
            ("pack_hunter", "lowest_hp", "highest_expected_damage", True, {"kill": 1.6, "preference": 0.4}),
            ("brute", "highest_effective_power", "highest_expected_damage", False, {"kill": 0.8, "preference": 0.5}),
            ("tactical_caster", "highest_effective_power", "highest_expected_damage", True, {"kill": 1.2, "preference": 0.3}),
            ("apex_predator", "highest_effective_power", "first_owned", True, {"kill": 1.8, "preference": 0.2}),
            ("ambush_predator", "lowest_hp", "first_owned", False, {"kill": 1.6, "preference": 0.9}),
        ):
            scored, candidates = self._score(
                strategy,
                skill_choice,
                prefer_area,
                utility_weights=behaviour.UtilityWeights(**{**WEIGHTS, **authored}),
            )
            group = next(
                item.identity
                for item in candidates.candidates
                if item.plan.shorthand == "all-enemies"
            )
            values = {item.identity: item.preference for item in scored}
            by_shape = {
                (item.identity.skill_key, item.identity.target_ids): item
                for item in scored
            }
            weak_single = by_shape[(STRIKE.key, (stable_identity(self.weak),))]
            group_plan = by_shape[(group.skill_key, group.target_ids)]
            signatures[label] = (
                weak_single.preference,
                by_shape[(STRIKE.key, (stable_identity(self.strong),))].preference,
                round(values[group], 6),
                round(weak_single.score, 6),
                round(group_plan.score, 6),
            )
        self.assertEqual(len(set(signatures.values())), len(signatures))
        self.assertNotEqual(
            signatures["instinctive"][0], signatures["brute"][0]
        )
        self.assertNotEqual(
            signatures["instinctive"][2], signatures["pack_hunter"][2]
        )

    @covers_requirement("monster-ai-utility-selection::utility-attack-score-reflects-continuous-intelligence")
    def test_intelligence_scales_only_the_tactical_terms(self):
        low, candidates = self._score(
            "lowest_hp", "first_owned", False, intelligence=10
        )
        high, _ = self._score("lowest_hp", "first_owned", False, intelligence=90)
        by_identity = {item.identity: item for item in high}
        for low_item in low:
            high_item = by_identity[low_item.identity]
            self.assertTrue(isclose(low_item.damage, high_item.damage))
            self.assertTrue(isclose(low_item.preference, high_item.preference))
            self.assertTrue(isclose(low_item.finishing, high_item.finishing))
            self.assertTrue(isclose(low_item.cost, high_item.cost))
            self.assertTrue(isclose(low_item.waste, high_item.waste))
            self.assertTrue(
                isclose(
                    high_item.score - low_item.score,
                    0.8
                    * (
                        WEIGHTS["kill"] * high_item.finishing
                        - WEIGHTS["cost"] * high_item.cost
                        - WEIGHTS["waste"] * high_item.waste
                    ),
                    abs_tol=1e-9,
                )
            )
        self.assertTrue(candidates.candidates)
        self.assertGreater(len(low), 1)

    def test_a_refused_projection_is_reported_and_never_valued(self):
        _owned(self.actor, PURGED.key, STRIKE.key)
        candidates, estimates, context, roster, snapshot = self._decision()
        refused = [
            item for item in estimates.estimates if isinstance(item, InvalidEstimate)
        ]
        self.assertTrue(refused, [item.identity for item in candidates.candidates])
        scored = score_candidates(
            candidates,
            estimates,
            profile=self.profiles[ARCHETYPE],
            intelligence=50,
            actor=self.actor,
            context=context,
            roster=roster,
            snapshot=snapshot,
        )
        self.assertEqual(len(scored) + len(refused), len(candidates.candidates))
        self.assertTrue(scored)


class TargetMetricTests(unittest.TestCase):
    """The target metric mirrors combat's capacity read, and its neutral case."""

    @staticmethod
    def _participant(*, hp=40.0, maximum=None, effective=10.0):
        resources = {} if maximum is None else {"hp": (int(hp), maximum)}
        return ParticipantSnapshot(
            identity="dbref:3",
            relation=Relation.ENEMY,
            present=True,
            in_range=True,
            alive=True,
            traits={"hp": hp},
            effective_traits={key: effective for key in STATIC_KEYS},
            resources=resources,
            capability=CapabilityState(blocked_by_buff=False, actions_per_turn=1),
            buffs=(),
        )

    @staticmethod
    def _plan(identity, recipients):
        return PlanEstimate(
            identity=CandidateIdentity(identity, 1.0, ()), recipients=recipients
        )

    def test_the_power_metric_scales_the_effective_stats_by_the_capacity(self):
        # Four traits of ten with a maximum of one hundred is 4000.
        self.assertEqual(
            target_metric(
                self._participant(maximum=100), "highest_effective_power"
            ),
            4000.0,
        )
        self.assertEqual(
            target_metric(self._participant(hp=25.0), "lowest_hp"), 25.0
        )

    def test_a_corrupt_capacity_never_inverts_the_comparison(self):
        # combat._max_hp clamps a negative maximum at zero, so the metric is
        # zero rather than a negative power that would reverse the ranks.
        self.assertEqual(
            target_metric(
                self._participant(maximum=-5), "highest_effective_power"
            ),
            0.0,
        )

    def test_an_unreadable_capacity_falls_back_to_stored_hp(self):
        # combat._max_hp falls back to the stored current value when no maximum
        # is readable: twenty-five stored hp of forty effective power is 1000.
        self.assertEqual(
            target_metric(
                self._participant(hp=25.0, maximum=None),
                "highest_effective_power",
            ),
            1000.0,
        )

    def test_a_plan_with_no_hostile_recipient_takes_the_neutral_rank(self):
        ally = RecipientProjection(
            identity="dbref:4",
            relation=Relation.ALLY,
            damage=0.0,
            healing=0.2,
            nominal_damage=0.0,
            nominal_healing=0.2,
            finishing=0.0,
        )
        hostile = RecipientProjection(
            identity="dbref:9",
            relation=Relation.ENEMY,
            damage=0.3,
            healing=0.0,
            nominal_damage=0.3,
            nominal_healing=0.0,
            finishing=0.0,
        )
        ranks = {"dbref:9": 1.0, "dbref:8": 0.0}
        self.assertEqual(
            _plan_target_rank(self._plan("t_sel_heal", (ally,)), ranks),
            NO_TARGET_PREFERENCE,
        )
        # "No hostile target to prefer" is not "the worst target available".
        self.assertNotEqual(NO_TARGET_PREFERENCE, 0.0)
        self.assertEqual(
            _plan_target_rank(self._plan("t_sel_strike", (hostile,)), ranks), 1.0
        )
        self.assertEqual(
            _plan_target_rank(self._plan("t_sel_strike", (ally, hostile)), ranks), 1.0
        )


def _fake_field(actor, *others):
    """A two-team battlefield over in-memory fakes."""
    roster = {str(entity.key): entity for entity in (actor, *others)}
    return Battlefield(
        {
            "monsters": frozenset({str(actor.key)}),
            "party": frozenset(str(entity.key) for entity in others),
        },
        roster,
    )


class ExecutionScopeTests(unittest.TestCase):
    """The round engine's real per-slot and per-round decision identity."""

    def setUp(self):
        self.actor = FakeEntity("actor", hp=100, max_hp=100)
        self.enemy = FakeEntity("enemy", hp=100, max_hp=100)
        self.observed = []

    def _field(self):
        return _fake_field(self.actor, self.enemy)

    def _recorder(self):
        def provider(entity, battlefield):
            self.observed.append(current_decision_scope())
            return None

        return provider

    def _upkeep(self):
        return (
            patch("world.rules.combat.rounds.tick_buffs", return_value=()),
            patch("world.rules.combat.rounds.decay_tick"),
        )

    @staticmethod
    def _shape(scopes):
        return [
            (item.session_id, item.round_index, item.actor_id, item.slot_index,
             item.context_mode)
            for item in scopes
        ]

    @covers_requirement("monster-ai-utility-selection::actual-execution-identity-distinguishes-every-decision")
    def test_every_action_slot_of_every_actor_has_its_own_scope(self):
        upkeep = self._upkeep()
        with (
            upkeep[0],
            upkeep[1],
            patch(
                "world.rules.combat.rounds.roll_initiative",
                return_value=["actor", "enemy"],
            ),
            patch(
                "world.rules.combat.rounds.evaluate_combat_modifiers",
                return_value={"actions_per_turn": 2},
            ),
            patch(
                "world.rules.combat.rounds.matched_combat_modifiers",
                return_value=[],
            ),
        ):
            run_round(
                self._field(),
                self._recorder(),
                decision_scope_base=ExecutionScopeBase("sess", 7),
            )
        self.assertEqual(
            self._shape(self.observed),
            [
                ("sess", 7, "key:actor", 0, "normal"),
                ("sess", 7, "key:actor", 1, "normal"),
                ("sess", 7, "key:enemy", 0, "normal"),
                ("sess", 7, "key:enemy", 1, "normal"),
            ],
        )

    @covers_requirement("monster-ai-utility-selection::actual-execution-identity-distinguishes-every-decision")
    def test_each_internal_overwhelm_round_has_its_own_round_index(self):
        upkeep = self._upkeep()
        with (
            upkeep[0],
            upkeep[1],
            patch(
                "world.rules.overwhelm.classify_overwhelm", return_value="monsters"
            ),
            patch("world.rules.overwhelm.combat.is_battle_over", return_value=False),
            patch(
                "world.rules.combat.rounds.roll_initiative",
                return_value=["actor"],
            ),
        ):
            resolve_overwhelm(
                self._field(),
                self._recorder(),
                max_rounds=3,
                decision_scope_base=ExecutionScopeBase("sess", 5),
            )
        self.assertEqual(
            self._shape(self.observed),
            [
                ("sess", 5, "key:actor", 0, "overwhelm"),
                ("sess", 6, "key:actor", 0, "overwhelm"),
                ("sess", 7, "key:actor", 0, "overwhelm"),
            ],
        )

    def test_a_bounded_encounter_numbers_its_own_rounds(self):
        upkeep = self._upkeep()
        with upkeep[0], upkeep[1]:
            run_battle(self._field(), self._recorder(), max_rounds=2)
        self.assertEqual(
            {(item.session_id, item.round_index) for item in self.observed},
            {("", 0), ("", 1)},
        )
        self.assertEqual(self.observed[0].slot_index, 0)

    def test_an_omitted_base_keeps_one_rounds_canonical_identity(self):
        upkeep = self._upkeep()
        with upkeep[0], upkeep[1], patch(
            "world.rules.combat.rounds.roll_initiative", return_value=["actor"]
        ):
            run_round(self._field(), self._recorder())
        self.assertEqual(
            self._shape(self.observed), [("", 0, "key:actor", 0, "normal")]
        )

    @covers_requirement("monster-ai-utility-selection::actual-execution-identity-distinguishes-every-decision")
    def test_a_provider_exception_restores_the_enclosing_scope(self):
        outer = ExecutionScopeBase("outer", 3).at_round(3)

        def provider(entity, battlefield):
            raise RuntimeError("boom")

        upkeep = self._upkeep()
        with upkeep[0], upkeep[1], patch(
            "world.rules.combat.rounds.roll_initiative", return_value=["actor"]
        ):
            with decision_scope(
                SimpleNamespace(
                    session_id="outer",
                    round_index=3,
                    actor_id="key:actor",
                    slot_index=0,
                    context_mode="normal",
                )
            ):
                with self.assertRaises(RuntimeError):
                    run_round(
                        self._field(),
                        provider,
                        decision_scope_base=ExecutionScopeBase("inner", 9),
                    )
                self.assertEqual(current_decision_scope().session_id, "outer")
        self.assertIsNone(current_decision_scope())
        self.assertEqual(outer.session_id, "outer")

    def test_nothing_installs_a_scope_outside_an_execution(self):
        self.assertIsNone(current_decision_scope())


class UtilityInspectionTests(SyntheticTuningMixin, EvenniaTestCase):
    """A direct two-argument inspection is canonical, repeatable and read-only."""

    def setUp(self):
        _scope(self)
        _suppress_innate_skills(self)
        super().setUp()
        self.open_tuning()
        self.room = create_object(Room, key="inspection arena")
        self.monster = self._monster_row("t_sel_inspector")
        self.opponent = _player("t_sel_inspected_foe")
        self.opponent.location = self.room
        self.opponent.traits.hp.base = 200
        self.opponent.traits.hp.current = 200

    def _monster_row(self, key, skills=(STRIKE.key,)):
        monster = construct_species_individual(SPECIES, VARIANT, key=key)
        monster.location = self.room
        monster.traits.hp.base = 200
        monster.traits.hp.current = 200
        monster.traits.mp.base = 100
        monster.traits.mp.current = 100
        monster.db.skills = {"active": list(skills), "passive": []}
        return monster

    def _field(self, *opponents, order=()):
        others = opponents or (self.opponent,)
        entries = [(self.monster, "foes")] + [(other, "party") for other in others]
        if order:
            entries = [entries[index] for index in order]
        roster = {str(entity.key): entity for entity, _team in entries}
        return Battlefield(
            {
                "foes": frozenset({str(self.monster.key)}),
                "party": frozenset(str(other.key) for other in others),
            },
            roster,
        )

    @covers_requirement("monster-ai-utility-selection::actual-execution-identity-distinguishes-every-decision")
    def test_a_direct_inspection_repeats_in_the_same_scope(self):
        before = _stored_attributes(self.monster)
        rows = ObjectDB.objects.count()
        field = self._field()
        first = monster_behaviour_policy(self.monster, field)
        second = monster_behaviour_policy(self.monster, field)
        self.assertIsNotNone(first)
        self.assertEqual(first.skill_key, second.skill_key)
        self.assertEqual(first.targets, second.targets)
        self.assertEqual(_stored_attributes(self.monster), before)
        self.assertEqual(ObjectDB.objects.count(), rows)
        self.assertIsNone(current_decision_scope())

    @covers_requirement("monster-ai-utility-selection::actual-execution-identity-distinguishes-every-decision")
    def test_the_inspection_identity_is_canonical_and_read_only(self):
        trace = []
        monster_behaviour_policy(self.monster, self._field(), trace=trace)
        self.assertEqual(len(trace), 1)
        recorded = trace[0]
        self.assertEqual(recorded.scope, ("", 0, "", 0, "normal"))
        self.assertTrue(recorded.inspected)
        self.assertEqual(
            recorded.seed,
            selection_seed(
                session_id="",
                round_index=0,
                actor_id=stable_actor_id(self.monster),
                slot_index=0,
                identity_fingerprint=recorded.snapshot_fingerprint,
            ),
        )
        self.assertEqual(recorded.algorithm_version, behaviour.AI_ALGORITHM_VERSION)
        self.assertEqual(recorded.configuration_fingerprint, self.tuning.fingerprint)

    def test_a_fresh_field_and_a_reordered_roster_keep_the_selection(self):
        first = monster_behaviour_policy(self.monster, self._field())
        second = monster_behaviour_policy(self.monster, self._field(order=(1, 0)))
        self.assertEqual(first.skill_key, second.skill_key)
        self.assertEqual(first.targets, second.targets)

    def test_a_blocked_actor_proposes_nothing_and_writes_nothing(self):
        apply_buff(self.monster, BLOCKER)
        before = _stored_attributes(self.monster)
        rows = ObjectDB.objects.count()
        with patch("world.rules.monster_behaviour.log_warn") as warning:
            self.assertIsNone(
                monster_behaviour_policy(self.monster, self._field())
            )
        warning.assert_not_called()
        self.assertEqual(_stored_attributes(self.monster), before)
        self.assertEqual(ObjectDB.objects.count(), rows)

    @covers_requirement("monster-ai-utility-selection::invalid-state-fallback-is-narrow-and-observable")
    def test_no_legal_candidate_is_a_no_action_boundary(self):
        monster = self._monster_row("t_sel_healer", skills=(HEAL_SELF.key,))
        with patch("world.rules.monster_behaviour.log_warn") as warning:
            request = monster_behaviour_policy(monster, self._field())
        self.assertIsNone(request)
        warning.assert_not_called()

    @covers_requirement("monster-ai-utility-selection::invalid-state-fallback-is-narrow-and-observable")
    def test_an_unsupported_candidate_set_is_a_no_action_boundary(self):
        monster = self._monster_row("t_sel_unmodelable", skills=(PURGED.key,))
        trace = []
        with patch("world.rules.monster_behaviour.log_warn") as warning:
            request = monster_behaviour_policy(monster, self._field(), trace=trace)
        self.assertIsNone(request)
        warning.assert_not_called()
        self.assertEqual(trace[0].selected, None)
        self.assertTrue(trace[0].omitted_estimates)

    @covers_requirement("monster-ai-utility-selection::selection-uses-stable-independent-softmax")
    def test_selection_dice_are_independent_of_the_combat_dice(self):
        random.seed(913)
        before = random.getstate()
        with patch(
            "world.rules.dice.roll_d100",
            side_effect=AssertionError("combat dice"),
        ):
            request = monster_behaviour_policy(self.monster, self._field())
        self.assertIsNotNone(request)
        self.assertEqual(random.getstate(), before)
        random.seed(31337)
        expected = [dice.roll_d100() for _ in range(3)]
        random.seed(31337)
        monster_behaviour_policy(self.monster, self._field())
        self.assertEqual([dice.roll_d100() for _ in range(3)], expected)

    @covers_requirement("monster-ai-utility-selection::actual-execution-identity-distinguishes-every-decision")
    def test_stable_actor_id_matches_the_snapshot_identity(self):
        self.assertEqual(
            stable_actor_id(self.monster), stable_identity(self.monster)
        )


class UtilityAdapterTests(SyntheticTuningMixin, EvenniaTestCase):
    """The session adapter's context-first selection through real settlement."""

    def setUp(self):
        _scope(self)
        _suppress_innate_skills(self)
        super().setUp()
        self.open_tuning()
        self.room = create_object(Room, key="adapter arena")
        self.player = _player("t_sel_player")
        self.player.location = self.room
        self.player.traits.hp.base = 400
        self.player.traits.hp.current = 400
        grant_lineage(self.player, [PLAYER_HIT.key])
        self.foe = _player("t_sel_second_foe")
        self.foe.location = self.room
        self.foe.traits.hp.base = 200
        self.foe.traits.hp.current = 200
        self.monster = construct_species_individual(SPECIES, VARIANT, key="t_sel_foe")
        self.monster.location = self.room
        self.monster.traits.hp.base = 300
        self.monster.traits.hp.current = 300
        self.monster.traits.mp.base = 100
        self.monster.traits.mp.current = 100
        self.monster.db.skills = {"active": [AREA.key], "passive": []}
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

    def _battlefield(self, *players):
        others = players or (self.player,)
        roster = {str(self.monster.key): self.monster}
        for player in others:
            roster[str(player.key)] = player
        return Battlefield(
            {
                "foes": frozenset({str(self.monster.key)}),
                "party": frozenset(str(player.key) for player in others),
            },
            roster,
        )

    @covers_requirement("monster-action-policy::monster-behaviour-policy-is-a-complete-drop-in-action-provider")
    @covers_requirement("monster-ai-utility-selection::production-adapters-preserve-decision-semantics")
    def test_the_adapter_preserves_the_shorthand_and_settles_committed_state(self):
        before_hp = _committed(self.player, "hp")
        before_mp = _committed(self.monster, "mp")
        request = _enemy_policy(
            self.monster, self._battlefield(self.player, self.foe), self.record
        )
        self.assertIsNotNone(request)
        self.assertEqual(request.targets, "all-enemies")
        self.assertEqual(request.scale, 1.0)
        with patch("world.rules.combat.damage.roll_d100", return_value=95):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success", result.detail)
        # Only legal recipients changed, and the change is committed.
        self.assertLess(_committed(self.player, "hp"), before_hp)
        self.assertLess(_committed(self.foe, "hp"), 200)
        self.assertEqual(_committed(self.monster, "mp"), before_mp - 4)
        self.assertEqual(_committed(self.monster, "hp"), 300)

    @covers_requirement("monster-ai-utility-selection::production-adapters-preserve-decision-semantics")
    def test_an_authored_non_default_scale_reaches_real_settlement(self):
        # The freeform entitlement is element-scoped: the castable row must name
        # the element whose mastery the actor owns, so it is a distinct key
        # registered for this test (a same-key rewrite would leave the registry
        # entry, and therefore the gate, on the original element).
        freeform = replace(
            AREA, key="t_sel_free_scale", element=_scoped_element(SYNTH_GLOW_ELEMENT)
        )
        self.monster.db.skills = {"active": [freeform.key], "passive": [MASTERY]}
        with patch.dict("world.skills.registry.SKILL_REGISTRY", {freeform.key: freeform}):
            request = _enemy_policy(
                self.monster,
                self._battlefield(self.player),
                self.record,
                scale=SCALE,
            )
            self.assertIsNotNone(request)
            self.assertEqual(request.scale, SCALE)
            self.assertEqual(request.targets, "all-enemies")
            allowed = round(4 * SCALE)
            with patch("world.rules.combat.damage.roll_d100", return_value=95):
                result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success", result.detail)
        self.assertEqual(_committed(self.monster, "mp"), 100 - allowed)

    @covers_requirement("monster-ai-utility-selection::production-adapters-preserve-decision-semantics")
    def test_a_real_session_round_settles_the_utility_action(self):
        engage(self.player, self.monster)
        before_mp = _committed(self.monster, "mp")
        clock = WorldClock()
        with (
            patch("world.rules.clock.get_world_clock", return_value=clock),
            patch("world.rules.combat.rounds.roll_initiative", return_value=[self.player.key, self.monster.key]),
            patch("world.rules.combat.rounds.roll_d100", return_value=95),
            patch("world.rules.combat.damage.roll_d100", return_value=95),
        ):
            result = submit_player_action(
                self.player, PLAYER_HIT.key, [self.monster]
            )
        self.assertNotEqual(result["outcome"], "rejected", result)
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)
        self.assertEqual(_committed(self.monster, "mp"), before_mp - 4)
        self.assertLess(_committed(self.monster, "hp"), 300)

    @covers_requirement("monster-ai-utility-selection::production-adapters-preserve-decision-semantics")
    def test_the_session_opening_round_numbers_its_decisions_from_the_session(self):
        # The end-to-end session opening path: the one ordinary round it
        # resolves provisions its decisions under the session's own identity,
        # numbered from the record's committed rounds, in the normal context
        # mode (no interactive entry compresses).
        engage(self.player, self.monster)
        session_id = read_session(self.player).session_id
        recorded = []
        real = decision_scope

        def recording(scope):
            recorded.append(
                (
                    scope.session_id,
                    scope.round_index,
                    scope.slot_index,
                    scope.context_mode,
                )
            )
            return real(scope)

        with (
            patch("world.rules.combat.rounds.decision_scope", recording),
            patch("world.rules.combat.rounds.roll_d100", return_value=95),
            patch("world.rules.combat.damage.roll_d100", return_value=95),
            patch("world.rules.clock.get_world_clock", return_value=WorldClock()),
        ):
            submit_opening_action(self.player, PLAYER_HIT.key, [self.monster])
        self.assertTrue(recorded)
        self.assertEqual({item[0] for item in recorded}, {session_id})
        self.assertEqual({item[1] for item in recorded}, {1})
        self.assertEqual({item[3] for item in recorded}, {"normal"})
        # These fixtures grant one action per turn, so the round resolved the
        # actor's first slot; the multi-slot numbering is pinned by
        # ExecutionScopeTests, which provisions several slots explicitly.
        self.assertEqual({item[2] for item in recorded}, {0})

    @covers_requirement("monster-ai-utility-selection::production-adapters-preserve-decision-semantics")
    def test_a_fault_after_the_utility_action_rolls_back_everything(self):
        # The utility action really writes (the monster pays its MP and damages
        # the party); a fault after those writes but before the outer commit
        # must roll the whole round back, with no AI-applied effect surviving.
        engage(self.player, self.monster)
        before_mp = _committed(self.monster, "mp")
        before_hp = _committed(self.player, "hp")
        with (
            patch(
                "world.rules.combat.rounds.roll_initiative",
                return_value=[self.player.key, self.monster.key],
            ),
            patch("world.rules.combat.rounds.roll_d100", return_value=95),
            patch("world.rules.combat.damage.roll_d100", return_value=95),
            patch("world.rules.clock.get_world_clock", return_value=WorldClock()),
            patch(
                "world.rules.combat_session.rounds._persist",
                side_effect=fail_on_round_persist("terminated"),
            ),
        ):
            with self.assertRaises(RuntimeError):
                submit_player_action(self.player, PLAYER_HIT.key, [self.monster])
        self.assertEqual(_committed(self.monster, "mp"), before_mp)
        self.assertEqual(_committed(self.player, "hp"), before_hp)
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)

    @covers_requirement("monster-ai-utility-selection::production-adapters-preserve-decision-semantics")
    def test_the_overwhelm_provider_settles_utility_decisions_too(self):
        request = ActionRequest(
            actor=self.player,
            skill_key=PLAYER_HIT.key,
            targets=[self.monster],
            context=BattlefieldActionContext(self._battlefield(self.player)),
        )
        provider = _overwhelm_provider(
            self.player, request, self._battlefield(self.player), self.record
        )
        before_mp = _committed(self.monster, "mp")
        with (
            patch("world.rules.combat.rounds.roll_d100", return_value=95),
            patch("world.rules.combat.damage.roll_d100", return_value=95),
            patch("world.rules.overwhelm.classify_overwhelm", return_value="foes"),
            patch("world.rules.overwhelm.combat.is_battle_over", return_value=False),
        ):
            resolve_overwhelm(
                self._battlefield(self.player),
                provider,
                max_rounds=2,
                decision_scope_base=ExecutionScopeBase(SESSION, 1),
            )
        self.assertLessEqual(_committed(self.monster, "mp"), before_mp - 4)


class InvalidStateTests(SyntheticTuningMixin, EvenniaTestCase):
    """Only the typed invalid runtime AI state is reported and resolved."""

    def setUp(self):
        _scope(self)
        super().setUp()
        self.open_tuning()
        self.room = create_object(Room, key="invalid arena")
        self.opponent = _player("t_sel_invalid_foe")
        self.opponent.location = self.room
        self.opponent.traits.hp.base = 300
        self.opponent.traits.hp.current = 300

    def _monster_row(self, key, *, species=SPECIES, variant=VARIANT):
        monster = (
            construct_species_individual(species, variant, key=key)
            if species is not None
            else _monster(key)
        )
        monster.location = self.room
        monster.traits.hp.base = 300
        monster.traits.hp.current = 300
        monster.traits.mp.base = 100
        monster.traits.mp.current = 100
        monster.db.skills = {"active": [STRIKE.key], "passive": []}
        return monster

    def _field(self, monster):
        return Battlefield(
            {
                "foes": frozenset({str(monster.key)}),
                "party": frozenset({str(self.opponent.key)}),
            },
            {str(monster.key): monster, str(self.opponent.key): self.opponent},
        )

    @covers_requirement("monster-ai-utility-selection::invalid-state-fallback-is-narrow-and-observable")
    def test_the_default_configured_behaviour_is_the_legacy_fallback(self):
        self.assertIs(invalid_state_fallback(), InvalidStateFallback.LEGACY)
        self.assertIs(
            InvalidStateFallback.NONE.value, "none"
        )

    @covers_requirement("monster-behaviour-profile::mode-selection-honors-actual-variant-and-behavior-binding")
    def test_an_unusable_stored_binding_warns_and_falls_back(self):
        monster = self._monster_row("t_sel_junk")
        monster.db.behaviour_tree = 7
        with patch("world.rules.monster_behaviour.log_warn") as warning:
            request = monster_behaviour_policy(monster, self._field(monster))
        self.assertIsNotNone(request)
        warning.assert_called_once()
        event, = warning.call_args.args
        context = warning.call_args.kwargs["context"]
        self.assertEqual(event, "monster_ai_invalid_state")
        self.assertEqual(context["reason"], "invalid_binding")
        self.assertEqual(context["char"], str(monster.pk))
        self.assertEqual(context["action"], "legacy")
        self.assertIsInstance(warning.call_args.kwargs["exc"], ValueError)
        # The stored binding is never rewritten by the fallback.
        self.assertEqual(monster.db.behaviour_tree, 7)

    @covers_requirement("monster-ai-utility-selection::invalid-state-fallback-is-narrow-and-observable")
    def test_the_diagnostic_setting_returns_no_action_instead(self):
        monster = self._monster_row("t_sel_diagnostic")
        monster.db.behaviour_tree = 7
        with override_settings(MONSTER_AI_INVALID_STATE_FALLBACK="none"), patch(
            "world.rules.monster_behaviour.log_warn"
        ) as warning:
            request = monster_behaviour_policy(monster, self._field(monster))
        self.assertIsNone(request)
        warning.assert_called_once()
        self.assertEqual(warning.call_args.kwargs["context"]["action"], "none")

    @covers_requirement("monster-ai-utility-selection::invalid-state-fallback-is-narrow-and-observable")
    def test_utility_without_an_identity_warns_and_falls_back(self):
        monster = self._monster_row("t_sel_tier_only", species=None)
        with patch("world.rules.monster_behaviour.log_warn") as warning:
            request = monster_behaviour_policy(monster, self._field(monster))
        self.assertIsNotNone(request)
        self.assertEqual(
            warning.call_args.kwargs["context"]["reason"], "invalid_identity"
        )

    @covers_requirement("monster-ai-utility-selection::invalid-state-fallback-is-narrow-and-observable")
    def test_utility_without_intelligence_warns_and_falls_back(self):
        monster = self._monster_row("t_sel_unvalued")
        monster.db.behaviour_tree = OTHER_ARCHETYPE
        book = _rulebook(
            archetypes={
                ARCHETYPE: _archetype(mode="legacy"),
                OTHER_ARCHETYPE: _archetype(mode="utility"),
            },
            modes={},
            intelligence={},
        )
        profiles = behaviour._load_behaviour_profiles(book, tiers={TIER})
        tuning = behaviour._load_ai_tuning(
            book, profiles=profiles, species=_SPECIES_ROWS, variants=_VARIANT_ROWS
        )
        with (
            patch.multiple(
                behaviour,
                MONSTER_BEHAVIOUR_YAML=book,
                BEHAVIOUR_PROFILES=profiles,
                MONSTER_AI_TUNING=tuning,
            ),
            patch("world.rules.monster_behaviour.log_warn") as warning,
        ):
            request = monster_behaviour_policy(monster, self._field(monster))
            self.assertIsNotNone(request)
            self.assertEqual(
                warning.call_args.kwargs["context"]["reason"],
                "missing_intelligence",
            )

    @covers_requirement("monster-ai-utility-selection::invalid-state-fallback-is-narrow-and-observable")
    def test_a_database_error_keeps_its_own_boundary(self):
        monster = self._monster_row("t_sel_db")
        with patch(
            "world.rules.monster_ai.estimate_candidates",
            side_effect=RuntimeError("database connection lost"),
        ), patch("world.rules.monster_behaviour.log_warn") as warning:
            with self.assertRaises(RuntimeError):
                monster_behaviour_policy(monster, self._field(monster))
        warning.assert_not_called()

    @covers_requirement("monster-ai-utility-selection::invalid-state-fallback-is-narrow-and-observable")
    def test_a_typed_invalid_score_warns_and_falls_back(self):
        monster = self._monster_row("t_sel_corrupt")
        with patch(
            "world.rules.monster_ai.utility.attack_utility",
            side_effect=MonsterAIStateError("a utility term is not finite"),
        ), patch("world.rules.monster_behaviour.log_warn") as warning:
            request = monster_behaviour_policy(monster, self._field(monster))
        self.assertIsNotNone(request)
        self.assertEqual(
            warning.call_args.kwargs["exc"].__class__, MonsterAIStateError
        )


class TraceTests(SyntheticTuningMixin, EvenniaTestCase):
    """The opt-in trace is normalized, JSON-safe and complete."""

    def setUp(self):
        _scope(self)
        super().setUp()
        self.open_tuning()
        self.room = create_object(Room, key="trace arena")
        self.monster = construct_species_individual(SPECIES, VARIANT, key="t_sel_traced")
        self.monster.location = self.room
        self.monster.traits.mp.base = 100
        self.monster.traits.mp.current = 100
        self.monster.db.skills = {"active": [STRIKE.key, AREA.key], "passive": []}
        self.opponent = _player("t_sel_traced_foe")
        self.opponent.location = self.room
        self.opponent.traits.hp.base = 300
        self.opponent.traits.hp.current = 300

    def _field(self):
        return Battlefield(
            {
                "foes": frozenset({str(self.monster.key)}),
                "party": frozenset({str(self.opponent.key)}),
            },
            {
                str(self.monster.key): self.monster,
                str(self.opponent.key): self.opponent,
            },
        )

    @covers_requirement("monster-ai-utility-selection::invalid-state-fallback-is-narrow-and-observable")
    def test_the_trace_records_the_decision_and_round_trips_as_json(self):
        trace = []
        request = monster_behaviour_policy(self.monster, self._field(), trace=trace)
        self.assertIsNotNone(request)
        self.assertEqual(len(trace), 1)
        recorded = trace[0]
        self.assertEqual(recorded.candidates, len(recorded.plans))
        self.assertEqual(recorded.selected.skill_key, request.skill_key)
        self.assertEqual(recorded.omitted_estimates, ())
        self.assertTrue(recorded.plans)
        for plan in recorded.plans:
            self.assertTrue(0.0 <= plan.preference <= 1.0)
            self.assertTrue(plan.limits == () or all(plan.limits))
        payload = recorded.to_payload()
        self.assertEqual(loads(json_dumps(payload)), payload)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trace.json"
            write_trace_report(path, recorded)
            self.assertEqual(loads(path.read_text(encoding="utf-8")), payload)
        summary = recorded.summary_context()
        self.assertEqual(summary["selected"], request.skill_key)
        self.assertEqual(summary["plans"], len(recorded.plans))

    @covers_requirement("monster-ai-utility-selection::invalid-state-fallback-is-narrow-and-observable")
    def test_the_trace_has_a_bounded_facade_summary_only(self):
        trace = []
        monster_behaviour_policy(self.monster, self._field(), trace=trace)
        summary = trace[0].summary_context()
        self.assertEqual(
            set(summary),
            {
                "session", "round", "slot", "char", "mode",
                "inspected", "candidates", "plans", "selected",
            },
        )
        for value in summary.values():
            self.assertLessEqual(len(str(value)), 200)

    @covers_requirement("monster-ai-utility-selection::invalid-state-fallback-is-narrow-and-observable")
    def test_a_no_action_decision_is_traced_as_well(self):
        _suppress_innate_skills(self)
        self.monster.db.skills = {"active": [HEAL_SELF.key], "passive": []}
        trace = []
        self.assertIsNone(
            monster_behaviour_policy(self.monster, self._field(), trace=trace)
        )
        self.assertEqual(trace[0].candidates, 0)
        self.assertIsNone(trace[0].selected)


class LegacyRetentionTests(SyntheticTuningMixin, EvenniaTestCase):
    """The legacy body, its dice and the resolver's authority are unchanged."""

    def setUp(self):
        _scope(self)
        super().setUp()
        self.open_tuning(modes={VARIANT: "legacy"})
        self.room = create_object(Room, key="legacy arena")
        self.opponent = _player("t_sel_legacy_foe")
        self.opponent.location = self.room
        self.opponent.traits.hp.base = 300
        self.opponent.traits.hp.current = 300
        self.monster = construct_species_individual(SPECIES, VARIANT, key="t_sel_legacy")
        self.monster.location = self.room
        self.monster.traits.hp.base = 300
        self.monster.traits.hp.current = 300
        self.monster.traits.mp.base = 100
        self.monster.traits.mp.current = 100
        self.monster.db.skills = {"active": [STRIKE.key], "passive": []}

    def _field(self, *opponents):
        others = opponents or (self.opponent,)
        roster = {str(self.monster.key): self.monster}
        for other in others:
            roster[str(other.key)] = other
        return Battlefield(
            {
                "foes": frozenset({str(self.monster.key)}),
                "party": frozenset(str(other.key) for other in others),
            },
            roster,
        )

    @covers_requirement("monster-action-policy::no-llm-or-generative-layer-involvement-anywhere-in-monster-decision-making")
    def test_a_legacy_variant_keeps_the_legacy_body_and_one_dice_draw(self):
        tie = _player("t_sel_legacy_tie")
        tie.location = self.room
        tie.traits.hp.base = 300
        tie.traits.hp.current = 300
        field = self._field(self.opponent, tie)
        with patch(
            "world.rules.monster_behaviour.dice.roll_d100", return_value=1
        ) as roller:
            request = monster_behaviour_policy(self.monster, field)
        roller.assert_called_once_with()
        self.assertEqual(request.skill_key, STRIKE.key)
        self.assertEqual([target.key for target in request.targets], [tie.key])
        with patch(
            "world.rules.monster_behaviour.dice.roll_d100", return_value=1
        ) as replay:
            self.assertEqual(
                monster_behaviour_policy(self.monster, field).targets,
                request.targets,
            )
        replay.assert_called_once_with()

    @covers_requirement("monster-action-policy::no-llm-or-generative-layer-involvement-anywhere-in-monster-decision-making")
    def test_a_decision_completes_with_network_access_disabled(self):
        field = self._field()
        with (
            patch("socket.socket.connect", side_effect=AssertionError("no network")),
            patch("socket.create_connection", side_effect=AssertionError("no network")),
        ):
            self.open_tuning()
            utility = monster_behaviour_policy(self.monster, field)
            self.assertIsNotNone(utility)
        with (
            patch("socket.socket.connect", side_effect=AssertionError("no network")),
            patch("socket.create_connection", side_effect=AssertionError("no network")),
        ):
            self.open_tuning(modes={VARIANT: "legacy"})
            legacy = monster_behaviour_policy(self.monster, field)
        self.assertIsNotNone(legacy)

    @covers_requirement("monster-action-policy::target-selection-differs-by-archetype-and-is-deterministic-under-a-fixed-seed")
    def test_the_legacy_body_still_consumes_no_selection_rng(self):
        random.seed(4242)
        before = random.getstate()
        monster_behaviour_policy(self.monster, self._field())
        self.assertEqual(random.getstate(), before)

    @covers_requirement("monster-action-policy::monster-behaviour-policy-is-a-complete-drop-in-action-provider")
    @covers_requirement("monster-ai-utility-selection::invalid-state-fallback-is-narrow-and-observable")
    def test_a_late_rejection_is_never_reselected(self):
        field = self._field()
        selections = []
        original = select_candidate

        def counting(*args, **kwargs):
            selections.append(1)
            return original(*args, **kwargs)

        self.open_tuning()
        with patch("world.rules.monster_ai.selection.select_candidate", counting):
            request = monster_behaviour_policy(self.monster, field)
        self.assertEqual(len(selections), 1)
        with patch(
            "world.rules.combat.rounds.ActionResolver.resolve",
            return_value=SimpleNamespace(outcome="rejected", detail="target gone"),
        ):
            rejected = ActionResolver.resolve(request)
        self.assertEqual(rejected.outcome, "rejected")
        self.assertEqual(len(selections), 1)

    @covers_requirement("monster-action-policy::a-monster-with-zero-actions-per-turn-is-skipped-by-the-existing-gate-with-no")
    def test_the_zero_action_gate_never_invokes_the_provider(self):
        field = self._field()
        with (
            patch(
                "world.rules.combat.rounds.roll_initiative",
                return_value=[str(self.monster.key)],
            ),
            patch(
                "world.rules.combat.rounds.evaluate_combat_modifiers",
                return_value={"actions_per_turn": 0},
            ),
            patch("world.rules.combat.rounds.tick_buffs", return_value=()),
            patch("world.rules.combat.rounds.decay_tick"),
            patch.object(behaviour, "monster_behaviour_policy") as policy,
        ):
            logs = run_round(field, policy)
        policy.assert_not_called()
        self.assertEqual(logs[0].entries[0].kind, "action_skipped")
        # The direct read-only inspection the zero-action case permits still
        # writes nothing.
        before = _stored_attributes(self.monster)
        monster_behaviour_policy(self.monster, field)
        self.assertEqual(_stored_attributes(self.monster), before)
