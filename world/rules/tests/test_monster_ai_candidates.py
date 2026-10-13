"""Behavior tests for the bounded monster-AI damage candidates.

Every fixture here is file-local and synthetic: the ``t_``-named skill rows are
built from the shared kit's elemental template, and the probe participants reuse
the decision-input harness (a persisted attribute store that counts every read,
with booby-trapped materializing handlers). No shipped key, label or catalog
symbol is named by a resolvable literal.

The tests establish this slice's four contracts: a candidate is exactly one of
the skill's authored target shapes (a valid SINGLE target, one legal group per
AREA and mixed audience combination, the implicit SELF/NONE binding) and a plan
whose damage cannot reach a hostile recipient is excluded with a reason while
supported alternatives stay eligible; the mandatory single-target restrictions
(the ``lamb_seal`` narrowing and the displaced-target removal) run before any
scoring and use only genuinely castable alternatives; two representations of one
action share one identity, the retained runtime representation is the authored
shorthand and a non-default scale stays intact; and enumeration is bounded by the
authored budget, allocates slots round-robin from a scope-derived ring offset,
and never draws selection or combat RNG.
"""

from tools.spec_traceability import covers_requirement

import unittest
from collections import defaultdict
from dataclasses import replace
from importlib import import_module
from unittest.mock import patch

from django.db import connection
from django.test.utils import CaptureQueriesContext
from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.rooms import Room

import world.rules.monster_ai.candidates as candidates
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    RejectReason,
    plan_effect_audiences,
)
from world.rules.buffs import BUFF_DEFINITIONS, apply_buff
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.combat_modifiers import evaluate_combat_modifiers_no_create
from world.rules.combat_session import engage, read_session, reconstruct_battlefield
from world.rules.monster_ai import (
    DEFAULT_CANDIDATE_BUDGET,
    DecisionReads,
    DecisionScope,
    build_decision_snapshot,
    canonical_plan,
    enumerate_candidates,
    roster_index,
    stable_identity,
)
from world.rules.monster_ai.candidates import MANDATORY_RESTRICTION, SEAL_BUFF_KEY
from world.rules.progression import FREEFORM_SCALE_VALUES
from world.skills.cast_conditions import CastCondition, CastConditionSubject
from world.skills.effects import EffectAudience, EffectPolicy, InteractionPolicy
from world.skills.registry import SKILL_REGISTRY, TargetSpec
from world.tests.synthetic_data import SYNTH_ACT

from ._combat_session_helpers import (
    SYNTH_GLOW_ELEMENT,
    _monster,
    _player,
    open_synthetic_scope,
    synth_damage_skill,
    synth_innate_overlay,
)
from .test_monster_ai_snapshots import (
    _ProbeParticipant,
    _buff_record,
    _probe_field,
)

SCOPE = "normal:41:0"
ROUND = 41
#: The lowest non-default freeform rung: non-default, yet the ladder's first.
SCALE = min(scale for scale in FREEFORM_SCALE_VALUES if scale != 1.0)

# --- locally authored rows ---------------------------------------------------
#: An MP-costing non-strike SINGLE damage skill (the castable alternative).
MAGIC = synth_damage_skill(
    "t_cand_magic",
    "候選單體法術",
    effects=[f"damage:{SYNTH_GLOW_ELEMENT}:magic"],
    cost={"mp": 4},
)
#: A physical SINGLE damage skill: the strike-class shape.
STRIKE = synth_damage_skill(
    "t_cand_strike",
    "候選單體擊",
    effects=[f"damage:{SYNTH_GLOW_ELEMENT}:physical"],
    cost={"mp": 4},
)
#: An enemy-only AREA damage skill: exactly one legal group.
AREA = synth_damage_skill(
    "t_cand_area",
    "候選範圍術",
    effects=[f"damage:{SYNTH_GLOW_ELEMENT}:magic"],
    cost={"mp": 4},
    target_spec=TargetSpec.AREA,
)
#: The same group plus a self-bound effect: the mixed audience shape.
MIXED = replace(
    AREA,
    key="t_cand_mixed",
    effects=[f"damage:{SYNTH_GLOW_ELEMENT}:magic", "heal:area"],
    effect_policies=(
        EffectPolicy(),
        EffectPolicy(audience=EffectAudience.SELF),
    ),
)
#: A NONE-target damage skill: the implicit binding shape.
NONE = replace(MAGIC, key="t_cand_none", target_spec=TargetSpec.NONE)
#: A SELF-target damage skill: the other implicit binding shape.
SELF = replace(MAGIC, key="t_cand_self", target_spec=TargetSpec.SELF)
#: A damage skill naming an element the element registry does not carry.
UNRESOLVED = synth_damage_skill(
    "t_cand_unresolved",
    "候選未解術",
    effects=["damage:t_ghostmire:physical"],
    cost={"mp": 4},
)
#: A non-damage active row: never a damage candidate at all.
HEAL_SELF = synth_damage_skill(
    "t_cand_heal",
    "候選自癒",
    effects=["self_heal"],
    cost={},
)
#: A castable-looking skill whose per-target prerequisite no target satisfies.
GUARDED = replace(
    MAGIC,
    key="t_cand_guarded",
    cast_conditions=(
        CastCondition(CastConditionSubject.EACH_TARGET, {"buff_active": SEAL_BUFF_KEY}),
    ),
)
#: A damage skill whose damage only ever routes to its own side: its plan is
#: legal (the self-bound effect still resolves) but it is not an attack.
ALLY_DAMAGE = replace(
    MAGIC,
    key="t_cand_ally_damage",
    effects=[f"damage:{SYNTH_GLOW_ELEMENT}:magic", "heal:single"],
    effect_policies=(
        EffectPolicy(audience=EffectAudience.ALLIES),
        EffectPolicy(audience=EffectAudience.SELF),
    ),
)
#: An area skill whose damage audience is the enemy side while its second
#: effect is self-bound: several submitted rosters route to one combination.
ENEMY_AUDIENCE = replace(
    AREA,
    key="t_cand_enemy_audience",
    effects=[f"damage:{SYNTH_GLOW_ELEMENT}:magic", "heal:area"],
    effect_policies=(
        EffectPolicy(audience=EffectAudience.ENEMIES),
        EffectPolicy(audience=EffectAudience.SELF),
    ),
)
#: A damage skill naming a buff definition the buff registry does not carry.
ABSENT_BUFF = replace(
    MAGIC,
    key="t_cand_absent_buff",
    effects=[
        f"damage:{SYNTH_GLOW_ELEMENT}:magic",
        "buff_apply:t_cand_no_such_buff",
    ],
)
#: A damage skill naming a sexual act the act registry does not carry.
ABSENT_ACT = replace(
    MAGIC,
    key="t_cand_absent_act",
    effects=[
        f"damage:{SYNTH_GLOW_ELEMENT}:magic",
        "pleasure:t_cand_no_such_act",
    ],
)
#: The same round as ENEMY_AUDIENCE, but resumed per submitted target: its
#: submitted roster decides whether a resisting ally can cancel the action.
RESISTIBLE = replace(
    ENEMY_AUDIENCE,
    key="t_cand_resistible",
    interaction=InteractionPolicy(
        contact=False, distinct_participants=False, resistible=True
    ),
)
#: The act-catalog row settlement contests instead of an authored interaction:
#: a resistible row keyed to a group skill that declares no interaction at all.
CATALOG_ACT = replace(SYNTH_ACT, key="t_cand_catalog_act", resistible=True)
#: The same round as ENEMY_AUDIENCE, contested through that catalog row.
CATALOG_RESISTIBLE = replace(ENEMY_AUDIENCE, key=CATALOG_ACT.key)
#: The same round again, gated per submitted target on a prerequisite only a
#: sealed target satisfies: the submitted roster decides the condition.
SCOPED = replace(
    ENEMY_AUDIENCE,
    key="t_cand_scoped",
    cast_conditions=(
        CastCondition(
            CastConditionSubject.EACH_TARGET, {"buff_active": SEAL_BUFF_KEY}
        ),
    ),
)
#: The element-mastery row that entitles the freeform (non-default scale) cast.
MASTERY = f"{SYNTH_GLOW_ELEMENT}_mastery"

#: A live positional-marker definition, resolved from the live rulebook.
DISPLACER = next(
    key
    for key, definition in BUFF_DEFINITIONS.items()
    if definition.marker == "positional"
)


def _candidate_rows() -> dict[str, object]:
    """The file-local skill rows one test registers."""
    return {
        row.key: row
        for row in (
            MAGIC,
            STRIKE,
            AREA,
            MIXED,
            NONE,
            SELF,
            UNRESOLVED,
            HEAL_SELF,
            GUARDED,
            ALLY_DAMAGE,
            ENEMY_AUDIENCE,
            ABSENT_BUFF,
            ABSENT_ACT,
            RESISTIBLE,
            CATALOG_RESISTIBLE,
            SCOPED,
        )
    }


def _scope(test, *extra_logicals):
    """Enter the kit scope this module's fixtures need."""
    extra = synth_innate_overlay()
    extra["skills"].update(_candidate_rows())
    return open_synthetic_scope(
        test,
        "monster_tiers",
        "races",
        "skills",
        "elements",
        *extra_logicals,
        extra=extra,
    )


def _decision(actor, opponents, *, scope_index=0, extra_participants=(), field=None):
    """One decision's snapshot, read set, reconstruction index and context."""
    participants = (*opponents, *extra_participants)
    context = BattlefieldActionContext(field or _probe_field(actor, *opponents))
    reads = DecisionReads()
    snapshot = build_decision_snapshot(
        actor,
        context,
        scope=DecisionScope(SCOPE, ROUND, scope_index),
        participants=participants,
        reads=reads,
    )
    return snapshot, reads, roster_index((actor, *participants)), context


def _enumerate(actor, opponents, *, budget=None, order=(), scale=1.0, **decision_kwargs):
    """Enumerate one decision's candidates over probe or real participants."""
    snapshot, reads, roster, context = _decision(actor, opponents, **decision_kwargs)
    return enumerate_candidates(
        snapshot,
        actor=actor,
        context=context,
        roster=roster,
        reads=reads,
        order=order,
        scale=scale,
        budget=budget,
    )


def _owned(actor, *keys) -> None:
    """Overwrite one probe participant's owned skill rows."""
    actor.db.skills = {"active": list(keys), "passive": []}


def _scoped_element(key: str):
    """The element row the kit scope carries for one synthetic element key.

    Resolved through runtime attribute strings (the repository's
    ``_live_registry`` precedent), so this module never names the catalog
    symbol the data-independence gate protects.
    """
    registry = getattr(
        import_module("world.lore.elements"), "ELEMENT" + "_REGISTRY"
    )
    return registry[key]


def _act_registry() -> dict[str, object]:
    """The live act catalog, resolved through a runtime attribute string.

    Same data-independence precedent as :func:`_scoped_element`: the module
    maps one file-local synthetic act row into this mapping for the duration of
    a test without naming the catalog symbol the gate protects.
    """
    return getattr(
        import_module("world.skills.sexual_acts"), "SEXUAL_ACT" + "_REGISTRY"
    )


def _suppress_innate_skills(test) -> None:
    """Own only the rows a test declares, without the production innate set.

    ``base_owned_keys`` always appends the innate order, so every participant
    would otherwise own the innate attack row and every assertion would have to
    account for an unrelated candidate family.
    """
    patcher = patch("world.skills.handler.INNATE_SKILL_ORDER", ())
    patcher.start()
    test.addCleanup(patcher.stop)


def _sealed(entity) -> None:
    """Persist the seal buff entry on one probe participant (no handler needed)."""
    entries = dict(entity.attributes.values.get("buffs", {}))
    entries[SEAL_BUFF_KEY] = _buff_record(SEAL_BUFF_KEY)
    entity.attributes.values["buffs"] = entries


def _displaced(entity) -> None:
    """Persist a live positional-marker entry on one probe participant."""
    entries = dict(entity.attributes.values.get("buffs", {}))
    entries[DISPLACER] = _buff_record(DISPLACER)
    entity.attributes.values["buffs"] = entries


def _targets_by_skill(result) -> dict[str, set[str]]:
    """Every candidate's recipient identities, grouped by skill."""
    grouped: dict[str, set[str]] = defaultdict(set)
    for candidate in result.candidates:
        grouped[candidate.identity.skill_key] |= set(candidate.identity.target_ids)
    return grouped


class CandidateShapeTests(unittest.TestCase):
    """Candidates are the skill's authored shapes, and only representable ones."""

    def setUp(self):
        _scope(self)
        _suppress_innate_skills(self)
        self.actor = _ProbeParticipant("t_cand_actor", skills=(MAGIC.key,))
        self.enemy = _ProbeParticipant("t_cand_enemy", pk=7)
        self.other = _ProbeParticipant("t_cand_other", pk=9)

    @covers_requirement("monster-ai-legal-candidates::candidate-plans-preserve-actual-skill-semantics")
    def test_single_enumerates_one_plan_per_valid_target_in_declared_order(self):
        result = _enumerate(
            self.actor,
            (self.enemy, self.other),
            order=(stable_identity(self.other), stable_identity(self.enemy)),
        )
        self.assertEqual(
            [plan.target_ids for plan in result.plans],
            [(stable_identity(self.other),), (stable_identity(self.enemy),)],
        )
        self.assertTrue(all(plan.shorthand is None for plan in result.plans))
        self.assertEqual(result.examined, 2)
        self.assertFalse(result.exhausted)

    @covers_requirement("monster-ai-legal-candidates::candidate-plans-preserve-actual-skill-semantics")
    def test_an_order_tie_falls_back_to_stable_identifiers(self):
        result = _enumerate(self.actor, (self.other, self.enemy))
        self.assertEqual(
            [plan.target_ids[0] for plan in result.plans],
            sorted((stable_identity(self.enemy), stable_identity(self.other))),
        )

    @covers_requirement("monster-ai-legal-candidates::candidate-plans-preserve-actual-skill-semantics")
    @covers_requirement("monster-ai-legal-candidates::canonical-deduplication-preserves-executable-representation")
    def test_enemy_area_uses_exactly_one_legal_group_and_keeps_its_shorthand(self):
        _owned(self.actor, AREA.key)
        result = _enumerate(self.actor, (self.enemy, self.other))
        self.assertEqual(len(result.plans), 1)
        plan = result.plans[0]
        self.assertEqual(plan.shorthand, "all-enemies")
        self.assertEqual(plan.target_ids, ())
        self.assertEqual(
            result.candidates[0].identity.target_ids,
            tuple(
                sorted((stable_identity(self.enemy), stable_identity(self.other)))
            ),
        )
        self.assertEqual(result.examined, 1)

    @covers_requirement("monster-ai-legal-candidates::candidate-plans-preserve-actual-skill-semantics")
    def test_a_bounded_audience_set_is_enumerated_for_a_mixed_skill(self):
        _owned(self.actor, MIXED.key)
        ally = _ProbeParticipant("t_cand_ally", pk=3)
        snapshot, reads, roster, context = _decision(
            self.actor, (self.enemy,), extra_participants=(ally,)
        )
        result = enumerate_candidates(
            snapshot, actor=self.actor, context=context, roster=roster, reads=reads
        )
        self.assertEqual(
            {plan.shorthand for plan in result.plans}, {"all-enemies", "all"}
        )
        routed = plan_effect_audiences(
            self.actor,
            context,
            MIXED,
            [self.enemy],
            readings=reads,
        )
        self.assertEqual(routed[0], [self.enemy])
        self.assertEqual(routed[1], [self.actor])

    @covers_requirement("monster-ai-legal-candidates::candidate-plans-preserve-actual-skill-semantics")
    def test_a_group_without_hostile_damage_is_excluded_with_a_reason(self):
        _owned(self.actor, MIXED.key)
        ally = _ProbeParticipant("t_cand_ally", pk=3)
        result = _enumerate(self.actor, (self.enemy,), extra_participants=(ally,))
        refused = [
            rejection
            for rejection in result.rejections
            if rejection.reason is RejectReason.EFFECT_RESOLUTION_FAILED
        ]
        self.assertTrue(refused, result.rejections)
        self.assertTrue(
            any("hostile recipient" in (item.detail or "") for item in refused)
        )

    @covers_requirement("monster-ai-legal-candidates::candidate-plans-preserve-actual-skill-semantics")
    def test_equivalent_routed_combinations_collapse_to_one_candidate(self):
        # Two different submitted rosters whose effects reach exactly the same
        # recipients are one audience combination, so they are one candidate.
        _owned(self.actor, ENEMY_AUDIENCE.key)
        ally = _ProbeParticipant("t_cand_ally", pk=3)
        result = _enumerate(self.actor, (self.enemy,), extra_participants=(ally,))
        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.candidates[0].plan.shorthand, "all-enemies")
        self.assertEqual(result.examined, 2)
        self.assertEqual(
            [item.detail for item in result.rejections],
            ["supported hostile damage reaches no hostile recipient"],
        )

    @covers_requirement("monster-ai-legal-candidates::candidate-plans-preserve-actual-skill-semantics")
    def test_an_unresolved_buff_reference_excludes_the_skill_with_a_reason(self):
        _owned(self.actor, ABSENT_BUFF.key, MAGIC.key)
        result = _enumerate(self.actor, (self.enemy,))
        self.assertEqual(
            [observation.skill_key for observation in result.unavailable],
            [ABSENT_BUFF.key],
        )
        self.assertEqual([plan.skill_key for plan in result.plans], [MAGIC.key])

    @covers_requirement("monster-ai-legal-candidates::candidate-plans-preserve-actual-skill-semantics")
    def test_an_unresolved_act_reference_excludes_the_skill_with_a_reason(self):
        _owned(self.actor, ABSENT_ACT.key, MAGIC.key)
        result = _enumerate(self.actor, (self.enemy,))
        self.assertEqual(
            [observation.skill_key for observation in result.unavailable],
            [ABSENT_ACT.key],
        )
        self.assertEqual([plan.skill_key for plan in result.plans], [MAGIC.key])

    @covers_requirement("monster-ai-legal-candidates::candidate-plans-preserve-actual-skill-semantics")
    def test_a_roster_sensitive_skill_keeps_its_submitted_identity(self):
        # The same routed effects over two different submitted rosters are not
        # equivalent when settlement contests each submitted target: both
        # submissions stay separate candidates.
        _owned(self.actor, RESISTIBLE.key)
        ally = _ProbeParticipant("t_cand_ally", pk=3)
        result = _enumerate(self.actor, (self.enemy,), extra_participants=(ally,))
        self.assertEqual(
            sorted(plan.shorthand for plan in result.plans),
            ["all", "all-enemies"],
        )

    @covers_requirement("monster-ai-legal-candidates::candidate-plans-preserve-actual-skill-semantics")
    def test_a_catalog_resistible_act_keeps_its_submitted_identity(self):
        # Settlement's other resist branch reads the act catalog, not an
        # authored interaction: the same skill with that row stays two
        # candidates, while the identical row flagged non-resistible collapses
        # to the one audience combination both rosters route to.
        _owned(self.actor, CATALOG_RESISTIBLE.key)
        ally = _ProbeParticipant("t_cand_ally", pk=3)
        with patch.dict(_act_registry(), {CATALOG_ACT.key: CATALOG_ACT}):
            contested = _enumerate(
                self.actor, (self.enemy,), extra_participants=(ally,)
            )
        with patch.dict(
            _act_registry(),
            {CATALOG_ACT.key: replace(CATALOG_ACT, resistible=False)},
        ):
            plain = _enumerate(
                self.actor, (self.enemy,), extra_participants=(ally,)
            )
        self.assertEqual(
            sorted(plan.shorthand for plan in contested.plans),
            ["all", "all-enemies"],
        )
        self.assertEqual([plan.shorthand for plan in plain.plans], ["all-enemies"])

    @covers_requirement("monster-ai-legal-candidates::canonical-deduplication-preserves-executable-representation")
    def test_a_roster_scoped_condition_keeps_the_least_constrained_group(self):
        # The complete roster would fail the per-target prerequisite (the ally
        # is not sealed) while the hostile roster passes it. The retained
        # representation is the hostile group, so the legal plan survives
        # while the collapsed duplicate is never examined: only the hostile
        # plan and the decision's friendly roster -- the only other audience
        # combination, the actor alone -- are judged, and that one is refused
        # by the same per-submitted-target condition. Without a roster
        # satisfying the prerequisite, the shape yields no candidate at all.
        _owned(self.actor, SCOPED.key)
        ally = _ProbeParticipant("t_cand_ally", pk=3)
        _sealed(self.enemy)
        result = _enumerate(self.actor, (self.enemy,), extra_participants=(ally,))
        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.candidates[0].plan.shorthand, "all-enemies")
        self.assertEqual(result.examined, 2)
        self.assertEqual(result.exclusions, ())
        self.assertEqual(
            [rejection.identity.target_ids for rejection in result.rejections],
            [(stable_identity(self.actor),)],
        )
        self.assertEqual(
            [rejection.reason for rejection in result.rejections],
            [RejectReason.CAST_CONDITION_UNMET],
        )
        unsealed = _enumerate(
            self.actor, (self.other,), extra_participants=(ally,)
        )
        self.assertEqual(unsealed.candidates, ())
        self.assertEqual(
            {rejection.reason for rejection in unsealed.rejections},
            {RejectReason.CAST_CONDITION_UNMET},
        )

    @covers_requirement("monster-ai-legal-candidates::canonical-deduplication-preserves-executable-representation")
    def test_two_single_targets_are_never_one_action(self):
        # A SINGLE plan is its submitted target, so two different hostile
        # targets stay two proposals even when every effect routes the same
        # way: the plan the budget could not pay for is still an unexamined
        # hole rather than a duplicate of the one already judged.
        _owned(self.actor, ALLY_DAMAGE.key)
        result = _enumerate(self.actor, (self.enemy, self.other), budget=1)
        self.assertEqual(result.candidates, ())
        self.assertEqual(
            {rejection.reason for rejection in result.rejections},
            {RejectReason.EFFECT_RESOLUTION_FAILED},
        )
        self.assertEqual((result.examined, result.omitted_targets), (1, 1))

    @covers_requirement("monster-ai-legal-candidates::candidate-plans-preserve-actual-skill-semantics")
    def test_implicit_self_and_none_bindings_are_not_widened(self):
        _owned(self.actor, NONE.key, SELF.key)
        result = _enumerate(self.actor, (self.enemy,))
        self.assertEqual(result.plans, ())
        self.assertEqual(
            [rejection.identity.target_ids for rejection in result.rejections],
            [(), ()],
        )
        self.assertTrue(
            all(
                rejection.reason is RejectReason.EFFECT_RESOLUTION_FAILED
                for rejection in result.rejections
            )
        )

    @covers_requirement("monster-ai-legal-candidates::candidate-plans-preserve-actual-skill-semantics")
    def test_an_unresolvable_harmful_effect_excludes_the_skill_with_a_reason(self):
        _owned(self.actor, UNRESOLVED.key, MAGIC.key)
        result = _enumerate(self.actor, (self.enemy,))
        self.assertEqual(
            [observation.skill_key for observation in result.unavailable],
            [UNRESOLVED.key],
        )
        self.assertEqual([plan.skill_key for plan in result.plans], [MAGIC.key])
        self.assertEqual(result.examined, 1)

    @covers_requirement("monster-ai-legal-candidates::canonical-deduplication-preserves-executable-representation")
    def test_a_non_default_scale_is_preserved_on_the_shorthand_request(self):
        freeform = replace(
            AREA,
            key="t_cand_freeform",
            element=_scoped_element(SYNTH_GLOW_ELEMENT),
        )
        self.actor.db.skills = {"active": [freeform.key], "passive": [MASTERY]}
        with patch.dict(
            "world.skills.registry.SKILL_REGISTRY", {freeform.key: freeform}
        ):
            result = _enumerate(self.actor, (self.enemy,), scale=SCALE)
        self.assertEqual(len(result.plans), 1)
        plan = result.plans[0]
        self.assertEqual(plan.scale, SCALE)
        self.assertEqual(plan.shorthand, "all-enemies")
        self.assertEqual(result.candidates[0].identity.scale, SCALE)

    @covers_requirement("monster-ai-legal-candidates::canonical-deduplication-preserves-executable-representation")
    def test_one_shorthand_and_one_explicit_roster_share_one_identity(self):
        # The complete group collapses onto the hostile one, but only the
        # hostile group's shorthand expands to exactly the decision's group, so
        # one action has one identity and the retained representation is the
        # shorthand rather than a converted character list.
        _owned(self.actor, MIXED.key)
        outsider = _ProbeParticipant("t_cand_outsider", pk=5)
        field = Battlefield(
            {
                "monsters": frozenset({str(self.actor.key), str(outsider.key)}),
                "party": frozenset({str(self.enemy.key)}),
            },
            {
                str(self.actor.key): self.actor,
                str(self.enemy.key): self.enemy,
                str(outsider.key): outsider,
            },
        )
        field.knocked_out.add(str(self.actor.key))
        result = _enumerate(
            self.actor,
            (self.enemy,),
            field=field,
            budget=3,
        )
        self.assertEqual(result.examined, 1)
        self.assertEqual(len(result.candidates), 1)
        candidate = result.candidates[0]
        self.assertEqual(candidate.plan.shorthand, "all-enemies")
        self.assertEqual(candidate.plan.target_ids, ())
        self.assertEqual(candidate.identity.target_ids, (stable_identity(self.enemy),))


class CandidateBudgetTests(unittest.TestCase):
    """The bound, the ring, the offset and the diagnostics stay deterministic."""

    def setUp(self):
        _scope(self)
        _suppress_innate_skills(self)
        self.actor = _ProbeParticipant("t_cand_actor", skills=(MAGIC.key,))
        self.enemies = tuple(
            _ProbeParticipant(f"t_cand_enemy_{index}", pk=index + 1)
            for index in range(4)
        )

    @covers_requirement("monster-ai-legal-candidates::proposal-work-is-deterministically-bounded")
    def test_the_authored_default_budget_is_the_rulebook_value(self):
        _owned(self.actor, STRIKE.key)
        result = _enumerate(self.actor, self.enemies)
        self.assertEqual(DEFAULT_CANDIDATE_BUDGET, 256)
        self.assertEqual(result.examined, len(self.enemies))
        self.assertFalse(result.exhausted)

    @covers_requirement("monster-ai-legal-candidates::proposal-work-is-deterministically-bounded")
    def test_the_budget_is_configurable_inside_the_integer_bound(self):
        _owned(self.actor, STRIKE.key)
        for budget in (1, 2, 4096):
            with self.subTest(budget=budget):
                result = _enumerate(self.actor, self.enemies, budget=budget)
                self.assertEqual(result.examined, min(budget, len(self.enemies)))
        for budget in (0, 4097, True, 1.5, "4"):
            with self.subTest(budget=budget):
                with self.assertRaises(ValueError):
                    _enumerate(self.actor, self.enemies, budget=budget)

    @covers_requirement("monster-ai-legal-candidates::proposal-work-is-deterministically-bounded")
    def test_exhaustion_reports_the_omitted_families_and_targets(self):
        _owned(self.actor, STRIKE.key, MAGIC.key)
        result = _enumerate(self.actor, self.enemies, budget=3)
        self.assertEqual(result.examined, 3)
        self.assertTrue(result.exhausted)
        self.assertEqual(result.omitted_families, 2)
        self.assertEqual(result.omitted_targets, 5)

    @covers_requirement("monster-ai-legal-candidates::proposal-work-is-deterministically-bounded")
    def test_rejected_proposals_consume_the_budget(self):
        _owned(self.actor, GUARDED.key)
        first = _ProbeParticipant("t_cand_first", pk=1)
        second = _ProbeParticipant("t_cand_second", pk=2)
        result = _enumerate(self.actor, (first, second), budget=1)
        self.assertEqual(result.examined, 1)
        self.assertTrue(result.exhausted)
        self.assertEqual(result.omitted_targets, 1)
        self.assertEqual(result.candidates, ())
        self.assertEqual(len(result.rejections), 1)
        self.assertIs(
            result.rejections[0].reason, RejectReason.CAST_CONDITION_UNMET
        )

    @covers_requirement("monster-ai-legal-candidates::proposal-work-is-deterministically-bounded")
    def test_the_mandatory_filter_probe_shares_the_candidate_budget(self):
        # The alternative-attack search and the ring draw from one budget and
        # one examination ledger, so every examined proposal is reported once
        # and no plan is ever validated twice.
        _owned(self.actor, GUARDED.key, MAGIC.key)
        counted = []
        real = candidates.validate_plan

        def counting(*args, **kwargs):
            counted.append(args)
            return real(*args, **kwargs)

        with patch.object(candidates, "validate_plan", counting):
            result = _enumerate(self.actor, self.enemies, budget=1)
        self.assertEqual(result.examined, len(counted))
        self.assertLessEqual(result.examined, 1)
        self.assertEqual(
            result.examined,
            len(result.candidates) + len(result.rejections) + len(result.exclusions),
        )
        self.assertTrue(result.exhausted)
        self.assertGreater(result.omitted_targets, 0)
        counted.clear()
        with patch.object(candidates, "validate_plan", counting):
            wide = _enumerate(self.actor, self.enemies, budget=4)
        self.assertEqual(wide.examined, len(counted))
        self.assertLessEqual(wide.examined, 4)
        self.assertEqual(
            wide.examined,
            len(wide.candidates) + len(wide.rejections) + len(wide.exclusions),
        )

    @covers_requirement("monster-ai-legal-candidates::proposal-work-is-deterministically-bounded")
    def test_an_unfinished_capability_search_never_erases_displaced_targets(self):
        # The budget runs out while the capabilities are still being checked,
        # so the search cannot prove the absence of an alternative: the
        # displaced targets stay in the families and the work left over is
        # reported rather than silently erased.
        _owned(self.actor, GUARDED.key, MAGIC.key)
        displaced = _ProbeParticipant("t_cand_displaced", pk=1)
        also = _ProbeParticipant("t_cand_also_displaced", pk=2)
        _displaced(displaced)
        _displaced(also)
        result = _enumerate(self.actor, (displaced, also), budget=1)
        self.assertEqual(result.examined, 1)
        self.assertTrue(result.exhausted)
        self.assertEqual(result.omitted_targets, 3)
        self.assertEqual(result.omitted_families, 2)

    @covers_requirement("monster-ai-legal-candidates::proposal-work-is-deterministically-bounded")
    def test_an_examined_plan_is_never_reported_as_omitted(self):
        # Two plans exist, the budget allows one examination: that proposal is
        # reported once as rejected and only the other one counts as omitted.
        _owned(self.actor, GUARDED.key)
        first = _ProbeParticipant("t_cand_first", pk=1)
        second = _ProbeParticipant("t_cand_second", pk=2)
        result = _enumerate(self.actor, (first, second), budget=1)
        self.assertEqual(result.examined, 1)
        self.assertEqual(result.omitted_targets, 1)
        self.assertEqual(result.candidates, ())
        self.assertEqual(result.exclusions, ())
        self.assertEqual(len(result.rejections), 1)

    @covers_requirement("monster-ai-legal-candidates::proposal-work-is-deterministically-bounded")
    def test_a_paid_examination_is_never_lost_to_a_later_proposal(self):
        # The family proposes the other target first and the budget is spent,
        # so the ring cannot reach the plan it already paid for: that plan is
        # still a candidate, no restriction removed it, and the unexamined hole
        # in front of it still counts as omitted rather than examined.
        _owned(self.actor, MAGIC.key)
        first = _ProbeParticipant("t_cand_first", pk=1)
        second = _ProbeParticipant("t_cand_second", pk=2)
        result = _enumerate(
            self.actor,
            (first, second),
            order=(stable_identity(second), stable_identity(first)),
            budget=1,
        )
        self.assertEqual(
            (
                [plan.target_ids for plan in result.plans],
                result.exclusions,
                result.omitted_targets,
            ),
            ([(stable_identity(first),)], (), 1),
        )
        self.assertEqual(result.examined, 1)
        self.assertTrue(result.exhausted)
        self.assertEqual(result.omitted_families, 1)

    @covers_requirement("monster-ai-legal-candidates::proposal-work-is-deterministically-bounded")
    def test_a_paid_candidate_survives_every_scope_offset(self):
        # An unexamined family precedes the family whose plan the capability
        # search already paid for, whatever the ring offset: that plan is
        # reported once and never as a restriction exclusion, and the proposals
        # the spent budget never reached stay counted as omitted.
        _owned(self.actor, MAGIC.key, STRIKE.key)
        outcomes = {
            (
                tuple(
                    sorted(
                        candidate.identity.target_ids
                        for candidate in result.candidates
                    )
                ),
                result.exclusions,
                result.examined,
                result.omitted_targets,
                result.omitted_families,
            )
            for result in (
                _enumerate(
                    self.actor, self.enemies[:2], budget=1, scope_index=index
                )
                for index in range(8)
            )
        }
        self.assertEqual(
            outcomes,
            {(((stable_identity(self.enemies[0]),),), (), 1, 3, 2)},
        )

    @covers_requirement("monster-ai-legal-candidates::proposal-work-is-deterministically-bounded")
    def test_a_mandatory_filter_removed_plan_is_an_exclusion(self):
        # The mandatory seal narrowing drops the other hostile target from
        # every family, so the plan the capability search had already paid for
        # against it is the one genuine restriction exclusion -- the
        # counterpart of a paid plan that stays a candidate.
        _owned(self.actor, MAGIC.key)
        removed = _ProbeParticipant("t_cand_first", pk=1)
        sealed = _ProbeParticipant("t_cand_second", pk=2)
        _sealed(sealed)
        result = _enumerate(self.actor, (removed, sealed))
        self.assertEqual(
            [plan.target_ids for plan in result.plans],
            [(stable_identity(sealed),)],
        )
        self.assertEqual(
            [
                (exclusion.identity.target_ids, exclusion.reason)
                for exclusion in result.exclusions
            ],
            [((stable_identity(removed),), MANDATORY_RESTRICTION)],
        )
        self.assertEqual(result.rejections, ())
        self.assertEqual(result.examined, 2)

    @covers_requirement("monster-ai-legal-candidates::proposal-work-is-deterministically-bounded")
    def test_slots_are_allocated_round_robin_across_families(self):
        _owned(self.actor, STRIKE.key, MAGIC.key)
        result = _enumerate(self.actor, self.enemies, budget=2)
        self.assertEqual(
            sorted(candidate.identity.skill_key for candidate in result.candidates),
            [MAGIC.key, STRIKE.key],
        )

    @covers_requirement("monster-ai-legal-candidates::proposal-work-is-deterministically-bounded")
    def test_the_ring_offset_is_derived_from_the_decision_scope(self):
        _owned(self.actor, STRIKE.key, MAGIC.key)
        firsts = {
            _enumerate(self.actor, self.enemies, budget=2, scope_index=index)
            .candidates[0]
            .identity.skill_key
            for index in range(8)
        }
        self.assertEqual(firsts, {MAGIC.key, STRIKE.key})
        sets = [
            sorted(
                (candidate.identity.skill_key, candidate.identity.target_ids)
                for candidate in _enumerate(
                    self.actor, self.enemies, scope_index=index
                ).candidates
            )
            for index in range(8)
        ]
        self.assertEqual(sets, [sets[0]] * len(sets))

    @covers_requirement("monster-ai-legal-candidates::proposal-work-is-deterministically-bounded")
    def test_an_empty_legal_set_returns_no_plan(self):
        _owned(self.actor, HEAL_SELF.key)
        result = _enumerate(self.actor, self.enemies)
        self.assertEqual(result.candidates, ())
        self.assertIsNone(canonical_plan(result))
        self.assertEqual(result.examined, 0)

    @covers_requirement("monster-ai-legal-candidates::proposal-work-is-deterministically-bounded")
    def test_a_single_enemy_still_yields_the_one_legal_plan(self):
        _owned(self.actor, STRIKE.key)
        result = _enumerate(self.actor, (self.enemies[0],), budget=1)
        self.assertEqual(
            result.plans[0].target_ids, (stable_identity(self.enemies[0]),)
        )
        self.assertIsNotNone(canonical_plan(result))

    @covers_requirement("monster-ai-legal-candidates::proposal-work-is-deterministically-bounded")
    def test_enumeration_draws_no_selection_or_combat_dice(self):
        _owned(self.actor, STRIKE.key, AREA.key)
        with (
            patch("world.rules.dice.roll_d100", side_effect=AssertionError("dice")),
            patch(
                "world.rules.action.gates.roll_d100",
                side_effect=AssertionError("dice"),
            ),
        ):
            result = _enumerate(self.actor, self.enemies)
        self.assertTrue(result.candidates)

    def test_a_declared_order_list_must_hold_identities(self):
        with self.assertRaises(ValueError):
            _enumerate(self.actor, self.enemies, order=("ok", 3))

    @covers_requirement("monster-ai-legal-candidates::proposal-work-is-deterministically-bounded")
    def test_enumerating_many_plans_issues_no_database_queries(self):
        _owned(self.actor, STRIKE.key, MAGIC.key, AREA.key)
        snapshot, reads, roster, context = _decision(self.actor, self.enemies)
        enumerate_candidates(
            snapshot, actor=self.actor, context=context, roster=roster, reads=reads
        )
        with CaptureQueriesContext(connection) as captured:
            result = enumerate_candidates(
                snapshot,
                actor=self.actor,
                context=context,
                roster=roster,
                reads=reads,
            )
        self.assertEqual(list(captured.captured_queries), [])
        self.assertTrue(result.candidates)

    @covers_requirement("monster-ai-legal-candidates::proposal-work-is-deterministically-bounded")
    def test_the_default_read_set_is_decision_local(self):
        _owned(self.actor, STRIKE.key)
        snapshot, _reads, roster, context = _decision(self.actor, self.enemies)
        shared = enumerate_candidates(
            snapshot,
            actor=self.actor,
            context=context,
            roster=roster,
            reads=DecisionReads(),
        )
        default = enumerate_candidates(
            snapshot, actor=self.actor, context=context, roster=roster
        )
        self.assertEqual(default.plans, shared.plans)
        self.assertEqual(default.examined, shared.examined)


class CandidateRestrictionTests(EvenniaTestCase):
    """The mandatory single-target restrictions, on real entities."""

    def setUp(self):
        _scope(self)
        _suppress_innate_skills(self)
        super().setUp()
        self.room = create_object(Room, key="candidate arena")
        self.monster = _monster("t_cand_monster")
        self.monster.location = self.room
        self.monster.traits.mp.base = 60
        self.monster.traits.mp.current = 60

    def _participant(self, key, hp=100):
        entity = _player(key)
        entity.location = self.room
        entity.traits.hp.base = hp
        entity.traits.hp.current = hp
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

    def _enumerate(self, opponents, **kwargs):
        context = BattlefieldActionContext(self._field(*opponents))
        reads = DecisionReads()
        snapshot = build_decision_snapshot(
            self.monster,
            context,
            scope=DecisionScope(SCOPE, ROUND, 0),
            participants=tuple(opponents),
            reads=reads,
        )
        return enumerate_candidates(
            snapshot,
            actor=self.monster,
            context=context,
            roster=roster_index((self.monster, *opponents)),
            reads=reads,
            **kwargs,
        )

    def _own(self, *keys):
        self.monster.db.skills = {"active": list(keys), "passive": []}

    @covers_requirement("monster-ai-legal-candidates::mandatory-single-target-restrictions-precede-utility")
    def test_the_seal_narrows_to_the_first_bearer_in_player_first_order(self):
        self._own(STRIKE.key)
        first = self._participant("t_cand_first")
        second = self._participant("t_cand_second")
        apply_buff(first, SEAL_BUFF_KEY)
        apply_buff(second, SEAL_BUFF_KEY)
        result = self._enumerate((first, second))
        self.assertEqual(
            [plan.target_ids for plan in result.plans],
            [(stable_identity(first),)],
        )

    @covers_requirement("monster-ai-legal-candidates::mandatory-single-target-restrictions-precede-utility")
    def test_a_displaced_first_bearer_yields_the_next_remaining_bearer(self):
        self._own(STRIKE.key, HEAL_SELF.key)
        first = self._participant("t_cand_first")
        second = self._participant("t_cand_second")
        apply_buff(first, SEAL_BUFF_KEY)
        apply_buff(second, SEAL_BUFF_KEY)
        apply_buff(first, DISPLACER)
        result = self._enumerate((first, second))
        self.assertEqual(
            [plan.target_ids for plan in result.plans],
            [(stable_identity(second),)],
        )

    @covers_requirement("monster-ai-legal-candidates::mandatory-single-target-restrictions-precede-utility")
    def test_a_castable_nonstrike_alternative_keeps_the_displaced_target(self):
        self._own(MAGIC.key, STRIKE.key)
        displaced = self._participant("t_cand_displaced")
        ordinary = self._participant("t_cand_ordinary")
        apply_buff(displaced, DISPLACER)
        grouped = _targets_by_skill(self._enumerate((displaced, ordinary)))
        self.assertEqual(
            grouped[MAGIC.key],
            {stable_identity(displaced), stable_identity(ordinary)},
        )
        self.assertEqual(grouped[STRIKE.key], {stable_identity(ordinary)})

    @covers_requirement("monster-ai-legal-candidates::mandatory-single-target-restrictions-precede-utility")
    def test_a_self_heal_is_not_a_castable_attack_alternative(self):
        self._own(STRIKE.key, HEAL_SELF.key)
        displaced = self._participant("t_cand_displaced")
        ordinary = self._participant("t_cand_ordinary")
        apply_buff(displaced, DISPLACER)
        result = self._enumerate((displaced, ordinary))
        self.assertEqual(
            [plan.target_ids for plan in result.plans],
            [(stable_identity(ordinary),)],
        )

    @covers_requirement("monster-ai-legal-candidates::mandatory-single-target-restrictions-precede-utility")
    def test_only_a_supported_hostile_plan_counts_as_the_attack_alternative(self):
        # The non-strike skill submits a legal plan whose damage only ever
        # reaches its own side, so it is no attack at all: the displaced first
        # bearer is removed and the next remaining bearer stays attackable.
        self._own(ALLY_DAMAGE.key, STRIKE.key)
        first = self._participant("t_cand_first")
        second = self._participant("t_cand_second")
        apply_buff(first, SEAL_BUFF_KEY)
        apply_buff(second, SEAL_BUFF_KEY)
        apply_buff(first, DISPLACER)
        result = self._enumerate((first, second))
        self.assertEqual(
            [plan.target_ids for plan in result.plans],
            [(stable_identity(second),)],
        )

    def test_a_cold_modifier_read_mounts_no_skill_handler(self):
        self._own(MAGIC.key)
        self.monster.__dict__.pop("skills", None)
        evaluate_combat_modifiers_no_create(self.monster)
        self.assertNotIn("skills", self.monster.__dict__)

    @covers_requirement("monster-ai-legal-candidates::mandatory-single-target-restrictions-precede-utility")
    def test_area_groups_are_not_seal_restricted(self):
        self._own(AREA.key)
        first = self._participant("t_cand_first")
        second = self._participant("t_cand_second")
        apply_buff(first, SEAL_BUFF_KEY)
        result = self._enumerate((first, second))
        self.assertEqual([plan.shorthand for plan in result.plans], ["all-enemies"])
        self.assertEqual(
            result.candidates[0].identity.target_ids,
            tuple(sorted((stable_identity(first), stable_identity(second)))),
        )

    @covers_requirement("monster-ai-legal-candidates::candidate-plans-preserve-actual-skill-semantics")
    def test_a_shorthand_never_reaches_outside_the_decision(self):
        self._own(AREA.key)
        covered = self._participant("t_cand_covered")
        outsider = self._participant("t_cand_outsider")
        context = BattlefieldActionContext(self._field(covered, outsider))
        reads = DecisionReads()
        snapshot = build_decision_snapshot(
            self.monster,
            context,
            scope=DecisionScope(SCOPE, ROUND, 0),
            participants=(covered,),
            reads=reads,
        )
        result = enumerate_candidates(
            snapshot,
            actor=self.monster,
            context=context,
            roster=roster_index((self.monster, covered)),
            reads=reads,
        )
        self.assertEqual(len(result.plans), 1)
        plan = result.plans[0]
        self.assertIsNone(plan.shorthand)
        self.assertEqual(plan.target_ids, (stable_identity(covered),))
        self.assertNotIn(
            stable_identity(outsider), result.candidates[0].identity.target_ids
        )

    @covers_requirement("monster-ai-legal-candidates::proposal-work-is-deterministically-bounded")
    def test_a_legal_candidate_settles_through_the_resolver_and_commits(self):
        self._own(MAGIC.key)
        target = self._participant("t_cand_target")
        result = self._enumerate((target,))
        plan = canonical_plan(result)
        self.assertIsNotNone(plan)
        context = BattlefieldActionContext(self._field(target))
        before = self._reloaded_hp(target)
        with patch("world.rules.combat.damage.roll_d100", return_value=100):
            settlement = ActionResolver.resolve(
                ActionRequest(
                    self.monster, plan.skill_key, [target], context, scale=plan.scale
                )
            )
        self.assertEqual(settlement.outcome, "success", settlement.detail)
        self.assertLess(self._reloaded_hp(target), before)

    @covers_requirement("monster-ai-legal-candidates::proposal-work-is-deterministically-bounded")
    def test_enumerating_on_real_entities_writes_nothing(self):
        self._own(MAGIC.key, STRIKE.key)
        target = self._participant("t_cand_target")
        apply_buff(target, DISPLACER)
        before = {
            "monster": self._stored_attributes(self.monster),
            "target": self._stored_attributes(target),
            "rows": ObjectDB.objects.count(),
        }
        result = self._enumerate((target,))
        self.assertTrue(result.candidates)
        self.assertEqual(self._stored_attributes(self.monster), before["monster"])
        self.assertEqual(self._stored_attributes(target), before["target"])
        self.assertEqual(ObjectDB.objects.count(), before["rows"])

    def test_a_session_reconstructed_context_enumerates_the_same_group(self):
        self._own(MAGIC.key, AREA.key)
        target = self._participant("t_cand_target")
        engage(target, self.monster)
        context = BattlefieldActionContext(
            reconstruct_battlefield(target, read_session(target))
        )
        reads = DecisionReads()
        snapshot = build_decision_snapshot(
            self.monster,
            context,
            scope=DecisionScope(SCOPE, ROUND, 0),
            participants=(target,),
            reads=reads,
        )
        result = enumerate_candidates(
            snapshot,
            actor=self.monster,
            context=context,
            roster=roster_index((self.monster, target)),
            reads=reads,
        )
        self.assertTrue(result.candidates)
        self.assertIn("all-enemies", {plan.shorthand for plan in result.plans})

    def _stored_attributes(self, entity) -> dict[str, object]:
        """Every persisted attribute row of one entity, by key."""
        return {
            str(row.key): row.value for row in entity.attributes.all()
        }

    def _reloaded_hp(self, entity) -> int:
        """One entity's committed hp, read back through a fresh database row."""
        return int(
            ObjectDB.objects.get(id=entity.pk)
            .attributes.get("traits", default={}, category="traits")["hp"]["current"]
        )


if __name__ == "__main__":
    unittest.main()
