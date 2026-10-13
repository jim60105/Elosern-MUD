"""Bounded utility scores for one decision's legal candidates.

One monster decision asks this module which of its legal, estimated candidates
is worth taking. The score is exactly the authored one:

``U = w_damage * damage + w_preference * preference
     + i * (w_kill * finishing - w_cost * cost - w_waste * waste)``

with ``i = intelligence / 100``. The health terms are the estimator's own
signed, bounded features, so the damage term is positive for harm dealt to the
enemy side and negative for harm dealt to the actor's own side, and the
discipline term (finishing, cost, waste) scales with how clever the variant is:
intelligence buys no stats, no ownership, no legality and no power, it only
changes how the same legal options are valued.

``preference`` is the archetype's soft bias, and it is built from three bounded
stable ranks rather than from any authored magnitude:

- the **configured target**: each of the decision's applicable hostile
  participants is ranked under the profile's ``target_strategy`` metric, which
  is read from the snapshot (the literal stored hp for ``lowest_hp``, the
  four-stat effective sum scaled by maximum hp for
  ``highest_effective_power`` -- the same quantity
  :func:`world.rules.combat.effective_power` computes, projected here from the
  decision's own no-create reads instead of from live entities);
- the **owned-skill preference**: the profile's ``skill_choice``, as the
  canonical owned-key position for ``first_owned`` and as the mean per-plan
  nominal damage of the skill's supported candidates for
  ``highest_expected_damage``;
- the **area bias**: whether the plan's authored target shape is the one the
  profile prefers for this many living enemies.

Every one of the three is normalized over the distinct values actually present
in this decision, so a tie shares one rank and a decision with a single level
ranks every plan at the top. The plan's value is therefore always inside
``0..1``: preference can never dominate the projected damage, it only breaks
near-equal options along the archetype's declared taste.

Invalid estimates are never valued at zero: an unsupported outcome is an
omission the caller diagnoses, and a numerically corrupt projection is a typed
runtime state (:class:`MonsterAIStateError`) that the decision boundary reports
and handles through its configured invalid-state behaviour.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Any

from world.rules.monster_ai.candidates import (
    Candidate,
    CandidateIdentity,
    CandidateSet,
    decision_pool,
    hostile_domain,
)
from world.rules.monster_ai.estimation import (
    EstimateSet,
    EstimationLimit,
    InvalidEstimate,
    InvalidEstimateReason,
    PlanEstimate,
)
from world.rules.monster_ai.models import (
    DecisionSnapshot,
    ParticipantSnapshot,
    stable_identity,
)
from world.rules.targeting import Relation
from world.rules.traits import STATIC_KEYS
from world.skills.registry import TargetSpec


class MonsterAIStateError(ValueError):
    """A typed runtime AI state one decision cannot be selected from.

    Raised for a genuinely unusable decision state -- a utility archetype
    without weights or a resolved intelligence, a numerically corrupt
    projection, a non-finite score, a non-positive or non-finite temperature.
    The decision boundary reports exactly this type through the configured
    invalid-state behaviour; every other failure keeps its own boundary.
    """


#: The target rank of a plan whose projection reaches no hostile recipient.
#: A normalized rank's neutral middle, not its floor: such a plan is outside
#: the target bias's scope rather than the worst possible target.
NO_TARGET_PREFERENCE = 0.5


@dataclass(frozen=True, slots=True)
class ScoredCandidate:
    """One legal candidate, its utility score and the contributions behind it.

    Every field is a scalar or an immutable tuple, so a score can be inspected
    and reported without touching the candidate's live recipients or its plan's
    entities. ``limits`` is the estimator's own named approximation report for
    this candidate, carried forward so a trace or a diagnostic never has to
    re-estimate it.
    """

    candidate: Candidate
    score: float
    damage: float
    preference: float
    finishing: float
    cost: float
    waste: float
    limits: tuple[EstimationLimit, ...] = ()

    @property
    def identity(self) -> CandidateIdentity:
        """Return this candidate's canonical identity."""
        return self.candidate.identity

    @property
    def plan(self):
        """Return the runtime plan this candidate submits."""
        return self.candidate.plan


def normalized_ranks(
    values: Mapping[Any, float],
    *,
    higher_is_better: bool,
) -> dict[Any, float]:
    """Return each key's rank normalized onto ``0..1``, ties sharing a rank.

    The distinct values present decide the ranks, so a tie is one rank and a
    mapping whose entries all share one value ranks every key at the top: the
    rank says how good a choice is *relative to the choices this decision
    actually has*, never against an authored absolute scale.
    """
    for value in values.values():
        if not isfinite(value):
            raise MonsterAIStateError(f"a rank comparison read a non-finite value: {value!r}")
    distinct = sorted(set(values.values()), reverse=higher_is_better)
    if len(distinct) <= 1:
        return {key: 1.0 for key in values}
    positions = {value: index for index, value in enumerate(distinct)}
    span = len(distinct) - 1
    return {
        key: 1.0 - positions[value] / span for key, value in values.items()
    }


def attack_utility(
    *,
    damage: float,
    preference: float,
    finishing: float,
    cost: float,
    waste: float,
    weights: Any,
    intelligence: int,
) -> float:
    """Return the authored utility of one valued candidate.

    ``weights`` is the archetype's authored :class:`UtilityWeights` (every
    weight finite and non-negative, validated at startup); ``intelligence`` is
    the variant's resolved explicit 0..100 value. ``damage`` is the estimator's
    signed health feature, while ``finishing``, ``cost`` and ``waste`` are the
    positive magnitudes the formula subtracts or credits.
    """
    initiative = _unit_intelligence(intelligence)
    terms = (damage, preference, finishing, cost, waste)
    if not all(isfinite(term) for term in terms):
        raise MonsterAIStateError(f"a utility term is not finite: {terms!r}")
    if min(finishing, cost, waste) < 0:
        raise MonsterAIStateError(
            f"a discipline feature is negative: finishing={finishing!r} "
            f"cost={cost!r} waste={waste!r}"
        )
    score = (
        _weight(weights, "damage") * damage
        + _weight(weights, "preference") * preference
        + initiative
        * (
            _weight(weights, "kill") * finishing
            - _weight(weights, "cost") * cost
            - _weight(weights, "waste") * waste
        )
    )
    if not isfinite(score):
        raise MonsterAIStateError(f"a utility score is not finite: {score!r}")
    return score


def score_candidates(
    candidates: CandidateSet,
    estimates: EstimateSet,
    *,
    profile: Any,
    intelligence: int,
    actor: Any,
    context: Any,
    roster: Mapping[str, Any],
    snapshot: DecisionSnapshot,
) -> tuple[ScoredCandidate, ...]:
    """Score every supported candidate of one decision, in candidate order.

    ``estimates`` describes exactly the ``candidates`` set, in its own order;
    an estimate the model refused is not scored, so the result can be shorter
    than the candidate set. When *no* candidate can be valued because its
    projection was numerically corrupt, this raises the typed invalid state;
    when none can be valued only because their outcomes are unsupported, it
    returns an empty tuple -- an omission the caller reports, never a
    permission to fall back onto an option utility deliberately refused.
    """
    weights = getattr(profile, "utility_weights", None)
    if weights is None:
        raise MonsterAIStateError(
            "the utility archetype authors no weights"
        )
    if len(estimates.estimates) != len(candidates.candidates):
        raise ValueError("every candidate must have exactly one estimate")
    supported = tuple(
        (candidate, estimate)
        for candidate, estimate in zip(candidates.candidates, estimates.estimates)
        if isinstance(estimate, PlanEstimate)
    )
    if not supported:
        corrupt = [
            estimate
            for estimate in estimates.estimates
            if isinstance(estimate, InvalidEstimate)
            and estimate.reason is InvalidEstimateReason.NON_FINITE_FEATURE
        ]
        if corrupt:
            raise MonsterAIStateError(
                "every candidate's projection was numerically invalid: "
                + "; ".join(estimate.detail for estimate in corrupt)
            )
        return ()

    pool = decision_pool(snapshot, actor, roster, context)
    hostiles = hostile_domain(snapshot, pool)
    target_ranks = _target_ranks(snapshot, hostiles, profile.target_strategy)
    skill_ranks = _skill_ranks(snapshot, supported, profile.skill_choice)
    shape_ranks = _shape_ranks(
        snapshot,
        supported,
        prefer_area=bool(profile.prefer_area_when_multiple_enemies)
        and len(hostiles) > 1,
    )
    return tuple(
        _score(
            candidate,
            estimate,
            weights=weights,
            intelligence=intelligence,
            target_ranks=target_ranks,
            skill_ranks=skill_ranks,
            shape_ranks=shape_ranks,
        )
        for candidate, estimate in supported
    )


def _score(
    candidate: Candidate,
    estimate: PlanEstimate,
    *,
    weights: Any,
    intelligence: int,
    target_ranks: Mapping[str, float],
    skill_ranks: Mapping[str, float],
    shape_ranks: Mapping[CandidateIdentity, float],
) -> ScoredCandidate:
    """Return one candidate's score from the three ranks and the estimate."""
    target = _plan_target_rank(estimate, target_ranks)
    preference = (
        target
        + skill_ranks[candidate.identity.skill_key]
        + shape_ranks[candidate.identity]
    ) / 3.0
    damage = estimate.damage.value
    score = attack_utility(
        damage=damage,
        preference=preference,
        finishing=estimate.finishing,
        cost=estimate.cost,
        waste=estimate.waste.magnitude,
        weights=weights,
        intelligence=intelligence,
    )
    return ScoredCandidate(
        candidate=candidate,
        score=score,
        damage=damage,
        preference=preference,
        finishing=estimate.finishing,
        cost=estimate.cost,
        waste=estimate.waste.magnitude,
        limits=estimate.limits,
    )


def _target_ranks(
    snapshot: DecisionSnapshot,
    hostiles: Sequence[Any],
    strategy: str,
) -> dict[str, float]:
    """Return every applicable hostile participant's rank under one strategy."""
    higher_is_better = _target_metric_higher_is_better(strategy)
    metrics: dict[str, float] = {}
    for entity in hostiles:
        identity = stable_identity(entity)
        participant = snapshot.participant(identity)
        if participant is None:
            raise MonsterAIStateError(
                f"an eligible hostile is missing from the decision snapshot: {identity}"
            )
        metrics[identity] = target_metric(participant, strategy)
    return normalized_ranks(metrics, higher_is_better=higher_is_better)


def target_metric(participant: ParticipantSnapshot, strategy: str) -> float:
    """Return one participant's value under the profile's target strategy.

    ``lowest_hp`` reads the decision's literal stored hp projection;
    ``highest_effective_power`` reads the four effective static traits scaled
    by the participant's maximum hp -- the same expression combat's
    ``effective_power()`` computes, capacity included, taken from the
    snapshot's own no-create projections so a decision never reads a live
    entity to rank a target.
    """
    if strategy == "lowest_hp":
        return _finite_trait(participant, "hp")
    if strategy == "highest_effective_power":
        return (
            sum(_finite_trait(participant, key, effective=True) for key in STATIC_KEYS)
            * _projected_max_hp(participant)
        )
    raise ValueError(f"unknown target strategy: {strategy!r}")


def _projected_max_hp(participant: ParticipantSnapshot) -> float:
    """Return one participant's maximum hp as combat's own reader reports it.

    ``world.rules.combat._max_hp`` clamps a stored maximum at zero and falls
    back to the stored current value when no maximum is readable; a corrupt
    gauge must therefore never invert a power comparison here either (a
    negative capacity would flip the metric's sign and reverse the ranks).
    """
    maximum = participant.resources.get("hp")
    if maximum is None:
        return max(_finite_trait(participant, "hp"), 0.0)
    return max(float(maximum[1]), 0.0)


def _target_metric_higher_is_better(strategy: str) -> bool:
    if strategy == "lowest_hp":
        return False
    if strategy == "highest_effective_power":
        return True
    raise ValueError(f"unknown target strategy: {strategy!r}")


def _finite_trait(
    participant: ParticipantSnapshot,
    key: str,
    *,
    effective: bool = False,
) -> float:
    """Return one projected trait value, refusing a non-finite one."""
    source = participant.effective_traits if effective else participant.traits
    value = float(source.get(key, 0.0))
    if not isfinite(value):
        raise MonsterAIStateError(
            f"participant {participant.identity} has a non-finite {key}: {value!r}"
        )
    return value


def _plan_target_rank(
    estimate: PlanEstimate,
    target_ranks: Mapping[str, float],
) -> float:
    """Return one plan's mean target rank over the hostile recipients it reaches.

    The estimate's own recipient projections decide which of the plan's
    recipients are hostile, so this reads the routing settlement will actually
    apply rather than the submitted roster. A plan whose projection reaches no
    hostile recipient carries no target preference at all: the neutral middle
    of the normalized scale, never its floor, because "this plan has no
    hostile target to prefer" is not the same claim as "its target is the
    worst available" and a decision must not invent the latter.
    """
    ranks = [
        target_ranks[recipient.identity]
        for recipient in estimate.recipients
        if recipient.relation is Relation.ENEMY and recipient.identity in target_ranks
    ]
    if not ranks:
        return NO_TARGET_PREFERENCE
    return sum(ranks) / len(ranks)


def _skill_ranks(
    snapshot: DecisionSnapshot,
    supported: Sequence[tuple[Candidate, PlanEstimate]],
    skill_choice: str,
) -> dict[str, float]:
    """Return every present skill's rank under the profile's skill choice.

    ``first_owned`` ranks by the actor's canonical owned-key position, so the
    earlier skill in the snapshot's own stable owned order wins.
    ``highest_expected_damage`` ranks by the skill's mean per-plan nominal
    damage, which is permutation-invariant: a skill offering several target or
    scale variants is not favoured just because it has more of them.
    """
    keys = tuple({candidate.identity.skill_key for candidate, _ in supported})
    if skill_choice == "first_owned":
        order = {
            skill.key: index for index, skill in enumerate(snapshot.owned_skills)
        }
        metrics = {
            key: -float(order.get(key, len(order))) for key in keys
        }
        return normalized_ranks(metrics, higher_is_better=True)
    if skill_choice == "highest_expected_damage":
        totals: dict[str, list[float]] = {key: [] for key in keys}
        for candidate, estimate in supported:
            totals[candidate.identity.skill_key].append(
                sum(recipient.nominal_damage for recipient in estimate.recipients)
            )
        metrics = {
            key: sum(values) / len(values) for key, values in totals.items() if values
        }
        return normalized_ranks(metrics, higher_is_better=True)
    raise ValueError(f"unknown skill choice: {skill_choice!r}")


def _shape_ranks(
    snapshot: DecisionSnapshot,
    supported: Sequence[tuple[Candidate, PlanEstimate]],
    *,
    prefer_area: bool,
) -> dict[CandidateIdentity, float]:
    """Return every candidate's rank under the profile's area preference.

    The plan's authored target shape is its skill's own target spec, so an
    AREA skill's groups rank above a single-target skill's plans exactly when
    the profile prefers area against this many living enemies, and a decision
    offering only one shape ranks every plan at the top.
    """
    specs = {skill.key: skill.target_spec for skill in snapshot.owned_skills}
    metrics: dict[CandidateIdentity, float] = {}
    for candidate, _estimate in supported:
        spec = specs.get(candidate.identity.skill_key)
        if spec is None:
            raise MonsterAIStateError(
                f"a candidate's skill is missing from the decision snapshot: "
                f"{candidate.identity.skill_key}"
            )
        is_area = spec is TargetSpec.AREA
        metrics[candidate.identity] = 1.0 if is_area == prefer_area else 0.0
    return normalized_ranks(metrics, higher_is_better=True)


def _unit_intelligence(intelligence: Any) -> float:
    """Return one resolved intelligence as the ``0..1`` tactical weight."""
    if (
        isinstance(intelligence, bool)
        or not isinstance(intelligence, int)
        or not 0 <= intelligence <= 100
    ):
        raise MonsterAIStateError(
            f"a utility decision needs a resolved 0..100 intelligence, got {intelligence!r}"
        )
    return intelligence / 100.0


def _weight(weights: Any, name: str) -> float:
    """Return one authored weight, refusing a missing or unusable value."""
    value = getattr(weights, name, None)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MonsterAIStateError(f"the utility weight {name!r} is not a number: {value!r}")
    value = float(value)
    if not isfinite(value) or value < 0:
        raise MonsterAIStateError(f"the utility weight {name!r} is unusable: {value!r}")
    return value
