"""Semantically legal, deduplicated damage candidates under a hard budget.

One monster decision asks this module which attack plans actually exist. The
producer reads the owned active hostile damage skills, expands each into the
skill's own authored target shape (one plan per valid SINGLE target, the
bounded legal group set of an AREA or mixed-audience skill, the implicit
SELF/NONE binding), applies the two mandatory single-target restrictions (the
``lamb_seal`` narrowing and the displaced-target removal) *before* any scoring,
validates every plan through the shared settlement legality, deduplicates by
canonical identity, and examines at most one authored candidate budget's worth
of proposals.

The rules that decide legality are never restated here. ``validate_plan`` is
the same seam the decision inputs expose and it runs settlement's own ordered
gates. This module adds only what settlement does not answer:

- which proposals exist at all (the skill's authored shape and audiences);
- the unrepresentable-plan exclusions -- a harm the damage model cannot
  resolve, or a plan whose damage reaches no hostile recipient -- so a plan the
  AI cannot model never enters scoring while supported alternatives stay
  eligible;
- the canonical identity (skill, scale and the sorted stable identifiers of
  the plan's own recipients), so two representations of one action cannot be
  sampled twice and the retained representation stays executable;
- the deterministic bounded enumeration: deduplicated proposals, a family ring
  started at a scope-derived offset, and no selection or combat RNG draw.

Proposal work is bounded because an invalid candidate can never cause another
iteration: the round-robin stops as soon as the examined-proposal budget is
spent. A skill that is unusable for this decision contributes one availability
observation instead of an unbounded search, and that observation is a
diagnostic rather than an examined proposal, so it cannot starve a legal
family. An empty legal set is not an error and not a mandate to attack: the
decision simply has no candidate and the caller's no-action boundary applies.

The producer never writes state. It reads through one decision-local
:class:`~world.rules.monster_ai.snapshot.DecisionReads` (created here when the
caller supplies none, so enumeration never reads live state once per plan) and
hands live entities only to the shared pure gates.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from typing import Any, Callable

from world.lore.elements import ELEMENT_REGISTRY
from world.rules.action import (
    RejectReason,
    RejectedAction,
    plan_effect_audiences,
    resist_contest,
)
from world.rules.action_preview import preview_skill
from world.rules.buffs import BUFF_DEFINITIONS, has_positional_marker
from world.rules.monster_ai.legality import validate_plan
from world.rules.monster_ai.models import (
    DecisionSnapshot,
    PlannedAction,
    PlanVerdict,
    stable_identity,
)
from world.rules.monster_ai.snapshot import DecisionReads
from world.rules.monster_behaviour import (
    MAX_CANDIDATE_BUDGET,
    MIN_CANDIDATE_BUDGET,
    MONSTER_AI_TUNING,
)
from world.rules.spell_conditions import is_strike_class
from world.rules.targeting import Relation, expand_target_shorthand
from world.skills.effects import (
    BuffApplyEffect,
    DamageEffect,
    EffectAudience,
    PairEventEffect,
    PleasureEffect,
    RiteBlessingEffect,
    SelfBuffApplyEffect,
    SexualCounterEffect,
)
from world.skills.registry import FactionConstraint, SkillDef, SkillKind, TargetSpec
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY

#: The authored initial candidate budget (the rulebook's ``candidate_budget``).
DEFAULT_CANDIDATE_BUDGET = MONSTER_AI_TUNING.candidate_budget
#: The canonical combat buff the single-target seal restriction keys on. The
#: legacy decision body names the same key; the bearer's own climaxes lift it
#: (church design section 5.7).
SEAL_BUFF_KEY = "lamb_seal"

#: The semantic plan kinds one skill can contribute, in canonical family order:
#: one skill's one plan shape is the family the round-robin allocates across.
KIND_HOSTILE = "group:hostile"
KIND_FRIENDLY = "group:friendly"
KIND_COMPLETE = "group:complete"
KIND_SINGLE = "single"
KIND_IMPLICIT = "implicit"
_FAMILY_KINDS: tuple[str, ...] = (
    KIND_HOSTILE,
    KIND_FRIENDLY,
    KIND_COMPLETE,
    KIND_SINGLE,
    KIND_IMPLICIT,
)
#: The family kinds whose one skill contributes several representations of the
#: same action, so their submissions may collapse onto one audience
#: combination. The implicit binding and every SINGLE target keep their
#: submitted identity: a single plan's target *is* what settlement gates.
_GROUP_KINDS: frozenset[str] = frozenset((KIND_HOSTILE, KIND_FRIENDLY, KIND_COMPLETE))

#: The approved AREA shorthand whose expansion is exactly each group kind.
_GROUP_SHORTHANDS = {
    KIND_HOSTILE: "all-enemies",
    KIND_FRIENDLY: "all-allies",
    KIND_COMPLETE: "all",
}

#: The reason an examined plan the shared gates allow is still unusable: the
#: AI cannot resolve its effects into a supported hostile damage outcome.
_UNREPRESENTABLE = RejectReason.EFFECT_RESOLUTION_FAILED

#: The parsed effects whose payload names a buff definition the registry must
#: carry before the plan can mount anything.
_BUFF_REFERENCE_EFFECTS = (
    BuffApplyEffect,
    RiteBlessingEffect,
    SelfBuffApplyEffect,
)

#: The parsed effects whose payload names a sexual act definition the registry
#: must carry before the plan can resolve anything.
_ACT_REFERENCE_EFFECTS = (
    PairEventEffect,
    PleasureEffect,
    SexualCounterEffect,
)

#: The reason an examined, legal plan was removed by the mandatory single-target
#: restriction rather than refused by the shared gates.
MANDATORY_RESTRICTION = "mandatory_single_target_restriction"

#: One cached legality verdict per distinct proposed action.
_VerdictKey = tuple[str, float, str | None, tuple[str, ...]]


@dataclass
class _Budget:
    """One decision's shared examination budget and the slots it spent.

    The mandatory-filter capability search and the family ring draw from the
    same budget, and every plan examined by either is one entry of the one
    examination ledger, so the bound in the specification covers all of the
    decision's examination work rather than one phase of it.
    """

    limit: int
    spent: int = 0

    def take(self) -> bool:
        """Consume one examination slot; ``False`` when the budget is spent."""
        if self.spent >= self.limit:
            return False
        self.spent += 1
        return True


@dataclass(frozen=True, slots=True)
class CandidateIdentity:
    """The canonical identity one candidate is deduplicated by.

    ``skill_key`` and ``scale`` name the action, and ``target_ids`` are the
    sorted stable identifiers of the explicit recipient set the plan resolves
    to, after any shorthand expansion. Two representations of one action (a
    shorthand and the equivalent explicit roster) therefore share one identity
    and can never be sampled twice, while a non-default scale stays a distinct
    candidate.
    """

    skill_key: str
    scale: float
    target_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Candidate:
    """One legal, deduplicated candidate and the request it is submitted as.

    ``plan`` keeps the runtime representation: the authored AREA shorthand is
    preserved rather than converted into characters, and the authored scale is
    preserved rather than normalized away, so whatever the later selector picks
    stays executable exactly as validated.

    ``recipients`` is the plan's submitted recipient set and ``routed`` its
    per-effect recipient routing -- the shared audience planner's own answer,
    materialized as tuples here so an estimator can project the same
    recipients settlement will without re-deriving (and possibly re-disagreeing
    with) the routing the producer already established. Both describe the plan
    of the same decision: they are live entities read once by the producer, and
    they are never persisted, never carried across decisions and never part of
    a candidate identity.
    """

    identity: CandidateIdentity
    plan: PlannedAction
    recipients: tuple[Any, ...] = ()
    routed: tuple[tuple[Any, ...], ...] | None = None


@dataclass(frozen=True, slots=True)
class CandidateRejection:
    """One examined proposal the shared legality (or the damage model) refused."""

    identity: CandidateIdentity
    reason: RejectReason
    detail: str | None


@dataclass(frozen=True, slots=True)
class CandidateExclusion:
    """One examined, legal plan the mandatory single-target restriction removed.

    An applicable seal narrows a hostile single-target base to one bearer and a
    displaced target is removed without a genuinely castable non-strike
    alternative. A plan the capability search examined against a target the
    restriction then removed is reported here rather than disappearing: it was
    a legitimate examination, and the restriction -- not the plan -- is why it
    is not a candidate.
    """

    identity: CandidateIdentity
    reason: str


@dataclass(frozen=True, slots=True)
class SkillObservation:
    """One owned damage skill that contributed no proposal, with its reason.

    A skill unusable for this decision -- unavailable skill-wide, or carrying a
    harm the damage model cannot resolve -- is observed once instead of being
    expanded into proposals no gate would accept.
    """

    skill_key: str
    reason: RejectReason
    detail: str | None


@dataclass(frozen=True, slots=True)
class CandidateSet:
    """One decision's bounded candidate enumeration.

    ``examined`` is the number of deduplicated proposals the decision actually
    examined -- the mandatory-filter capability search and the family ring
    together -- and never exceeds the budget. Every examined proposal is
    reported exactly once, as a candidate, a rejection or a mandatory-filter
    exclusion, so ``examined`` is their sum. ``exhausted`` is true when the
    budget stopped the examination with distinct proposals still unexamined;
    ``omitted_families`` and ``omitted_targets`` count what was left. A
    duplicate representation is not a proposal, so it can neither consume a
    slot nor report exhaustion.
    """

    candidates: tuple[Candidate, ...] = ()
    rejections: tuple[CandidateRejection, ...] = ()
    exclusions: tuple[CandidateExclusion, ...] = ()
    unavailable: tuple[SkillObservation, ...] = ()
    examined: int = 0
    exhausted: bool = False
    omitted_families: int = 0
    omitted_targets: int = 0

    @property
    def plans(self) -> tuple[PlannedAction, ...]:
        """Every legal candidate's runtime request, in ring order.

        The ring's own walk first, then the already-examined plans an exhausted
        budget left behind a blocked cursor, in ring order as well.
        """
        return tuple(candidate.plan for candidate in self.candidates)


@dataclass(frozen=True, slots=True)
class _Proposal:
    """One deduplicated proposal the family ring may examine.

    ``routed`` is the plan's per-effect recipient routing (``None`` when the
    shared audience planner refuses the plan outright). It is what decides both
    whether the plan reaches a hostile recipient and whether two submissions
    are actually the same audience combination.
    """

    family: tuple[str, str]
    skill: SkillDef
    plan: PlannedAction
    identity: CandidateIdentity
    recipients: tuple[Any, ...]
    routed: tuple[tuple[Any, ...], ...] | None


def _routed(
    actor: Any,
    context: Any,
    skill: SkillDef,
    recipients: tuple[Any, ...],
    reads: DecisionReads,
) -> tuple[tuple[Any, ...], ...] | None:
    """Return one plan's per-effect routed recipients, or ``None`` when refused.

    The shared audience planner is the one routing authority: a ``SELF``
    audience binds the actor, ``ALLIES``/``ENEMIES`` filter the plan's own
    recipients and an audience condition filters them further. A plan whose
    every routed audience is empty has no representable outcome at all, which
    the planner reports by refusing it.
    """
    try:
        return tuple(
            tuple(reached)
            for reached in plan_effect_audiences(
                actor, context, skill, list(recipients), readings=reads
            )
        )
    except RejectedAction:
        # observability: ignore R2: an empty routing is the unrepresentable
        # outcome this module reports through the plan's own legality
        return None


def _plan_key(plan: PlannedAction) -> _VerdictKey:
    """Return the deduplication key of one submitted action."""
    return (plan.skill_key, plan.scale, plan.shorthand, plan.target_ids)


def _proposal_key(proposal: _Proposal) -> _VerdictKey:
    """Return the deduplication key of one proposal's submitted action."""
    plan = proposal.plan
    return _plan_key(plan)


def _routed_signature(proposal: _Proposal) -> tuple[tuple[str, ...], ...] | None:
    """Return one plan's actual audience combination, or ``None`` when refused.

    Two submissions that route every effect to the same recipients are the same
    observable action, however different their submitted rosters are. A refused
    routing returns ``None`` so the caller falls back to the submitted identity
    and never collapses unrelated refused plans.
    """
    if proposal.routed is None:
        return None
    return tuple(
        tuple(sorted(stable_identity(target) for target in reached))
        for reached in proposal.routed
    )


def canonical_plan(candidates: CandidateSet) -> PlannedAction | None:
    """Return the one plan this bounded set hands on, or ``None``.

    The canonical head of the ring order is the decision's plan. An empty legal
    set returns ``None``: the decision proposes no action and never forces an
    attack or falls back to the legacy body. Scoring and sampling are a later
    slice that replaces (never duplicates) this head choice; the function
    exists so the no-action boundary is expressible and testable now.
    """
    if not candidates.candidates:
        return None
    return candidates.candidates[0].plan


def enumerate_candidates(
    snapshot: DecisionSnapshot,
    *,
    actor: Any,
    context: Any,
    roster: dict[str, Any],
    reads: DecisionReads | None = None,
    order: Sequence[str] = (),
    scale: float = 1.0,
    budget: int | None = None,
) -> CandidateSet:
    """Enumerate one decision's legal damage candidates under a hard budget.

    ``snapshot`` is the decision's frozen input and defines its scope; ``actor``,
    ``context`` and ``roster`` are the resolved execution context the plans are
    built and judged in; ``reads`` is that decision's read set (created here
    when omitted, so enumeration always reads once); ``order`` is the
    archetype's declared target ordering as stable identities, with stable
    identifiers breaking ties; ``scale`` is the authored cast magnitude every
    plan keeps; ``budget`` is the examined-proposal bound, the authored default
    when omitted.

    Every proposal is built from the decision's own participants, so a plan can
    never name a participant the decision did not decide about -- including
    through an AREA shorthand, whose expansion is retained only when it is
    exactly the decision-scoped group.
    """
    limit = DEFAULT_CANDIDATE_BUDGET if budget is None else _validated_budget(budget)
    magnitude = _validated_scale(scale)
    declared = _declared_order(order)
    reader = DecisionReads() if reads is None else reads
    pool = decision_pool(snapshot, actor, roster, context)
    hostile = hostile_domain(snapshot, pool)

    skills: list[SkillDef] = []
    unavailable: list[SkillObservation] = []
    for skill_key in sorted(reader.owned_keys(actor)):
        skill = reader.skill(skill_key)
        if not _is_hostile_damage(skill):
            continue
        if not _supports_every_harmful_effect(skill):
            unavailable.append(
                SkillObservation(
                    skill.key,
                    _UNREPRESENTABLE,
                    "a potentially harmful effect names an unregistered "
                    "element or definition",
                )
            )
            continue
        broad = preview_skill(actor, skill.key, context, None, magnitude, reader)
        if not broad.enabled:
            unavailable.append(SkillObservation(skill.key, broad.reason, broad.detail))
            continue
        skills.append(skill)

    verdicts: dict[_VerdictKey, PlanVerdict] = {}
    ledger: dict[_VerdictKey, Candidate | CandidateRejection] = {}
    budget_state = _Budget(limit)

    def verdict(skill: SkillDef, plan: PlannedAction) -> PlanVerdict:
        key = (skill.key, plan.scale, plan.shorthand, plan.target_ids)
        if key not in verdicts:
            verdicts[key] = validate_plan(
                snapshot,
                plan,
                actor=actor,
                context=context,
                roster=roster,
                reads=reader,
            )
        return verdicts[key]

    def outcome(proposal: _Proposal) -> Candidate | CandidateRejection:
        """One proposal's outcome, computed once per submitted action."""
        key = _proposal_key(proposal)
        if key not in ledger:
            ledger[key] = _examine(proposal, actor, context, verdict)
        return ledger[key]

    def admit(proposal: _Proposal) -> bool:
        """Charge one examination slot, unless the plan was already examined."""
        return _proposal_key(proposal) in ledger or budget_state.take()

    singles = [skill for skill in skills if skill.target_spec is TargetSpec.SINGLE]
    displaced = frozenset(
        stable_identity(entity)
        for entity in hostile
        if has_positional_marker(entity, active_keys=reader.buff_keys(entity))
    )
    sealed = tuple(
        sorted(
            (
                entity
                for entity in hostile
                if SEAL_BUFF_KEY in reader.buff_keys(entity)
            ),
            key=_canonical_seal_order,
        )
    )
    alternative, conclusive = _has_castable_nonstrike_alternative(
        singles,
        hostile,
        actor,
        context,
        reader,
        magnitude,
        outcome,
        admit,
    )

    families: dict[tuple[str, str], list[_Proposal]] = {}
    for skill in skills:
        proposals = _skill_proposals(
            skill,
            snapshot,
            pool,
            hostile,
            actor,
            context,
            reader,
            magnitude,
            declared,
            sealed,
            displaced,
            alternative,
        )
        for proposal in proposals:
            families.setdefault(proposal.family, []).append(proposal)

    distinct = _deduplicate(families)
    ring = _ring_order(distinct, snapshot)
    candidates, cursors = _allocate(distinct, ring, outcome, admit)
    # An examined, legal plan stays a candidate even when the budget ran out
    # before the ring reached its family: reporting it as a mandatory-filter
    # exclusion would blame a restriction that never removed it. The walk above
    # already collects every already-paid outcome its cursors can reach; this
    # fallback collects the paid plans a cursor hides, in ring order and without
    # examining anything fresh or advancing a cursor (an unaffordable proposal
    # at a cursor blocks the rest of its family, and that hole must keep
    # counting as unexamined).
    seen = {_plan_key(candidate.plan) for candidate in candidates}
    for family in ring:
        for proposal in distinct[family][cursors[family] :]:
            key = _proposal_key(proposal)
            examined = ledger.get(key)
            if isinstance(examined, Candidate) and key not in seen:
                seen.add(key)
                candidates += (examined,)

    proposed = {
        _proposal_key(proposal)
        for family in distinct
        for proposal in distinct[family]
    }
    rejections = tuple(
        item for item in ledger.values() if isinstance(item, CandidateRejection)
    )
    exclusions = tuple(
        CandidateExclusion(item.identity, MANDATORY_RESTRICTION)
        for item in ledger.values()
        if isinstance(item, Candidate)
        and _plan_key(item.plan) not in proposed
    )
    omitted = [
        proposal
        for family in _family_order(distinct)
        for position, proposal in enumerate(distinct[family])
        if position >= cursors.get(family, 0)
        and _proposal_key(proposal) not in ledger
    ]
    return CandidateSet(
        candidates=candidates,
        rejections=rejections,
        exclusions=exclusions,
        unavailable=tuple(unavailable),
        examined=len(ledger),
        exhausted=bool(omitted) or not conclusive,
        omitted_families=len({proposal.family for proposal in omitted}),
        omitted_targets=len(omitted),
    )


def _skill_proposals(
    skill: SkillDef,
    snapshot: DecisionSnapshot,
    pool: tuple[Any, ...],
    hostile: tuple[Any, ...],
    actor: Any,
    context: Any,
    reads: DecisionReads,
    scale: float,
    declared: tuple[str, ...],
    sealed: tuple[Any, ...],
    displaced: frozenset[str],
    alternative: bool,
) -> list[_Proposal]:
    """Return one skill's proposals for the decision's own target shapes."""
    if skill.target_spec is TargetSpec.SINGLE:
        return [
            _single_proposal(skill, target, actor, context, reads, scale)
            for target in _single_base(
                skill, hostile, declared, sealed, displaced, alternative
            )
        ]
    if skill.target_spec is TargetSpec.AREA:
        return _group_proposals(
            skill, snapshot, pool, actor, context, reads, scale, _is_mixed(skill)
        )
    recipients: tuple[Any, ...] = ()
    return [
        _Proposal(
            (skill.key, KIND_IMPLICIT),
            skill,
            PlannedAction(skill.key, scale),
            CandidateIdentity(skill.key, scale, ()),
            recipients,
            _routed(actor, context, skill, recipients, reads),
        )
    ]


def _single_proposal(
    skill: SkillDef,
    target: Any,
    actor: Any,
    context: Any,
    reads: DecisionReads,
    scale: float,
) -> _Proposal:
    """Return one single-target plan for one skill, with its own routing."""
    recipients = (target,)
    return _Proposal(
        (skill.key, KIND_SINGLE),
        skill,
        PlannedAction(skill.key, scale, target_ids=(stable_identity(target),)),
        CandidateIdentity(skill.key, scale, (stable_identity(target),)),
        recipients,
        _routed(actor, context, skill, recipients, reads),
    )


def _single_base(
    skill: SkillDef,
    hostile: tuple[Any, ...],
    declared: tuple[str, ...],
    sealed: tuple[Any, ...],
    displaced: frozenset[str],
    alternative: bool,
) -> tuple[Any, ...]:
    """Return one hostile SINGLE damage skill's mandatory-filtered target base.

    Both mandatory restrictions run before any scoring: an applicable
    ``lamb_seal`` narrows the base to its bearers in canonical order, and
    without a genuinely castable non-strike hostile alternative the displaced
    targets are removed. With a seal, only the first remaining bearer is used.
    A strike-class skill always excludes displaced targets, even when another
    skill provides a legal non-strike alternative.
    """
    base = sealed if sealed else hostile
    if not alternative:
        base = tuple(
            entity for entity in base if stable_identity(entity) not in displaced
        )
    if sealed:
        base = base[:1]
    if is_strike_class(skill):
        base = tuple(
            entity for entity in base if stable_identity(entity) not in displaced
        )
    if sealed:
        return base
    ranks = {identity: index for index, identity in enumerate(declared)}
    return tuple(
        sorted(
            base,
            key=lambda entity: (
                ranks.get(stable_identity(entity), len(ranks)),
                stable_identity(entity),
            ),
        )
    )


def _group_proposals(
    skill: SkillDef,
    snapshot: DecisionSnapshot,
    pool: tuple[Any, ...],
    actor: Any,
    context: Any,
    reads: DecisionReads,
    scale: float,
    mixed: bool,
) -> list[_Proposal]:
    """Return one AREA skill's bounded semantic group proposals.

    An enemy-only skill contributes exactly one legal group (the hostile one);
    a mixed skill contributes the bounded hostile, friendly and complete groups
    its target policies permit. Each group's runtime representation is the
    approved AREA shorthand exactly when that shorthand expands to precisely
    the group -- never when it would reach a participant outside the decision
    -- and the group's own explicit identities otherwise.
    """
    kinds = (
        (KIND_HOSTILE, KIND_FRIENDLY, KIND_COMPLETE) if mixed else (KIND_HOSTILE,)
    )
    proposals: list[_Proposal] = []
    for kind in kinds:
        members = group_members(kind, snapshot, pool)
        if not members:
            continue
        proposals.append(
            _Proposal(
                (skill.key, kind),
                skill,
                _group_plan(kind, members, skill, actor, context, scale),
                CandidateIdentity(
                    skill.key,
                    scale,
                    tuple(sorted(stable_identity(entity) for entity in members)),
                ),
                members,
                _routed(actor, context, skill, members, reads),
            )
        )
    return proposals


def _group_plan(
    kind: str,
    members: tuple[Any, ...],
    skill: SkillDef,
    actor: Any,
    context: Any,
    scale: float,
) -> PlannedAction:
    """Return one group's runtime plan: the matching shorthand, else explicit ids."""
    shorthand = _GROUP_SHORTHANDS[kind]
    try:
        expanded = expand_target_shorthand(actor, context, shorthand)
    except RejectedAction:
        # observability: ignore R2: a shorthand that cannot expand (no
        # battlefield) is simply not a representation of this group
        expanded = None
    if expanded is not None and sorted(
        stable_identity(entity) for entity in expanded
    ) == sorted(stable_identity(entity) for entity in members):
        return PlannedAction(skill.key, scale, shorthand=shorthand)
    return PlannedAction(
        skill.key,
        scale,
        target_ids=tuple(sorted(stable_identity(entity) for entity in members)),
    )


def _has_castable_nonstrike_alternative(
    singles: list[SkillDef],
    hostile: tuple[Any, ...],
    actor: Any,
    context: Any,
    reads: DecisionReads,
    scale: float,
    outcome: Callable[[_Proposal], Candidate | CandidateRejection],
    admit: Callable[[_Proposal], bool],
) -> tuple[bool, bool]:
    """Return ``(alternative, conclusive)`` for the mandatory displacement rule.

    "Genuinely castable" means the same thing an accepted candidate means: the
    shared settlement gates accept the plan *and* its supported damage reaches a
    hostile recipient. A self-heal is not a damage skill at all, an uncastable
    magic skill has no accepted plan against a hostile target, and a plan whose
    damage never routes to an enemy is not an attack, so none of them satisfies
    the alternative-attack condition that keeps displaced targets reachable.

    The search draws from the decision's one examination budget, walks the
    targets round-robin across the relevant skills (so one skill with many
    targets cannot consume the allowance before another is looked at), and
    reports whether it finished. An unfinished search reports an alternative
    that may not exist: nothing is removed on an incomplete answer, while a
    displaced target is only removed when every candidate plan against the
    hostile domain was examined and none of them was an attack.

    The probed plans are the same objects the single-target families propose, so
    an examination is shared with the ring and never paid twice.
    """
    queues = [
        (
            skill,
            [
                _single_proposal(skill, target, actor, context, reads, scale)
                for target in hostile
            ],
        )
        for skill in singles
        if not is_strike_class(skill)
    ]
    for index in range(len(hostile)):
        for _skill, proposals in queues:
            if index >= len(proposals):
                continue
            proposal = proposals[index]
            if not admit(proposal):
                return True, False
            if isinstance(outcome(proposal), Candidate):
                return True, True
    return False, True


def _is_hostile_damage(skill: SkillDef | None) -> bool:
    """Return whether one skill is a candidate-owned active hostile damage skill.

    ``SELF_ONLY`` is excluded because such a skill cannot name a hostile
    recipient at all; ``ANY`` and ``ENEMY`` both can.
    """
    return (
        skill is not None
        and skill.kind is SkillKind.ACTIVE
        and skill.faction_constraint
        in (FactionConstraint.ANY, FactionConstraint.ENEMY)
        and any(isinstance(effect, DamageEffect) for effect in skill.parsed_effects)
    )


def _is_mixed(skill: SkillDef) -> bool:
    """Return whether a skill routes any effect to a friendly or self audience.

    An enemy-only skill has exactly one legal group; a skill whose audiences
    also reach allies or the actor is enumerated over the bounded
    friendly/hostile/complete groups its target policies permit.
    """
    return any(
        policy.audience in (EffectAudience.ALLIES, EffectAudience.SELF)
        for policy in skill.effect_policies
    )


def decision_pool(
    snapshot: DecisionSnapshot,
    actor: Any,
    roster: dict[str, Any],
    context: Any,
) -> tuple[Any, ...]:
    """Return the live participants this decision actually covers.

    The actor plus every participant the snapshot names that the reconstruction
    roster still carries, minus the battlefield's knocked-out members -- the
    same expression the shared shorthand expansion applies, so a group and its
    shorthand always describe the same combatants. It is the decision's own
    participant domain, shared with effect estimation so both read the same
    eligible set.
    """
    battlefield = getattr(context, "battlefield", None)
    knocked_out = frozenset(getattr(battlefield, "knocked_out", ()))
    pool: list[Any] = []
    seen: set[str] = set()
    for participant in (snapshot.actor, *snapshot.participants):
        if participant.identity in seen:
            continue
        seen.add(participant.identity)
        entity = roster.get(participant.identity)
        if entity is None or str(getattr(entity, "key", "")) in knocked_out:
            continue
        if entity is not actor and participant.identity == snapshot.actor.identity:
            continue
        pool.append(entity)
    return tuple(pool)


def _relation(snapshot: DecisionSnapshot, entity: Any) -> Relation | None:
    """Return one participant's snapshot relation, or ``None`` when unknown."""
    participant = snapshot.participant(stable_identity(entity))
    return None if participant is None else participant.relation


def _applicable(snapshot: DecisionSnapshot, entity: Any) -> bool:
    """Return whether the snapshot's own facts place one participant as a target."""
    participant = snapshot.participant(stable_identity(entity))
    return bool(
        participant is not None
        and participant.alive
        and participant.present
        and participant.in_range
    )


def hostile_domain(snapshot: DecisionSnapshot, pool: tuple[Any, ...]) -> tuple[Any, ...]:
    """Return the decision's applicable hostile participants in stable order."""
    return tuple(
        sorted(
            (
                entity
                for entity in pool
                if _relation(snapshot, entity) is Relation.ENEMY
                and _applicable(snapshot, entity)
            ),
            key=stable_identity,
        )
    )


def group_members(
    kind: str, snapshot: DecisionSnapshot, pool: tuple[Any, ...]
) -> tuple[Any, ...]:
    """Return one group kind's applicable members in stable order."""
    if kind == KIND_HOSTILE:
        wanted = (Relation.ENEMY,)
    elif kind == KIND_FRIENDLY:
        wanted = (Relation.SELF, Relation.ALLY)
    else:
        wanted = (Relation.ENEMY, Relation.ALLY, Relation.SELF)
    return tuple(
        sorted(
            (
                entity
                for entity in pool
                if _relation(snapshot, entity) in wanted
                and _applicable(snapshot, entity)
            ),
            key=stable_identity,
        )
    )


def _canonical_seal_order(entity: Any) -> tuple[int, int, str]:
    """Return one seal bearer's canonical order key (player first, then pk)."""
    from typeclasses.characters import PlayerCharacter

    return (
        0 if isinstance(entity, PlayerCharacter) else 1,
        int(getattr(entity, "pk", 0) or 0),
        stable_identity(entity),
    )


def _deduplicate(
    families: dict[tuple[str, str], list[_Proposal]],
) -> dict[tuple[str, str], list[_Proposal]]:
    """Drop duplicate representations before any slot is allocated.

    Two proposals are the same candidate when they submit the same skill and
    scale for the same actual audience combination, which is the per-effect
    routing the shared audience planner derives -- so two different submitted
    rosters that reach the same recipients (an ``all`` group over an enemy-only
    roster, or an audience-filtered subset) collapse to one sampling identity.
    The retained proposal keeps its own submitted identity and runtime
    representation; only the authored AREA shorthand is preferred, so a
    duplicate can never increase sampling probability and no ring offset can
    decide which representation survives. Proposals whose routing the planner
    refuses collapse by submitted identity instead, never with each other.
    """
    ordered = [
        (family, proposal)
        for family in _family_order(families)
        for proposal in families[family]
    ]
    best: dict[Any, _Proposal] = {}
    for _family, proposal in ordered:
        key = _collapse_key(proposal)
        current = best.get(key)
        if current is None or _representation_rank(proposal) < _representation_rank(current):
            best[key] = proposal
    surviving: dict[tuple[str, str], list[_Proposal]] = {}
    for family, proposal in ordered:
        if best[_collapse_key(proposal)] is proposal:
            surviving.setdefault(family, []).append(proposal)
    return surviving


def _collapse_key(proposal: _Proposal) -> Any:
    """Return the key two proposals are the same candidate under.

    A group representation (hostile, friendly or complete, the AREA audiences
    one skill authors several times over) collapses onto the actual audience
    combination the planner routed, so two submitted group rosters that route
    every effect to the same recipients are one candidate. Every other
    proposal keeps its submitted identity: a refused routing is never
    collapsed, a SINGLE plan is gated on its own submitted target, a scaled
    request is a different action even over the same recipients, and a
    roster-sensitive skill settles on its submitted roster rather than on the
    routed recipients alone.

    Restricting the routing equivalence to group kinds is what makes the
    retained representation's legality establishable: the group kinds rank
    hostile before friendly before complete, and each later kind's submitted
    roster is a superset of an earlier one's, so the surviving representation
    of a collapsed class is its least constrained member.
    """
    if proposal.family[1] not in _GROUP_KINDS or _roster_sensitive(proposal.skill):
        return proposal.identity
    signature = _routed_signature(proposal)
    if signature is None:
        return proposal.identity
    return (proposal.identity.skill_key, proposal.identity.scale, signature)


def _roster_sensitive(skill: SkillDef) -> bool:
    """Return whether settlement gates one skill on its submitted roster.

    A resist contest runs once per non-actor submitted target, and a resisting
    target either has its own effects withheld or cancels the whole action, so
    two plans whose effects route to the same recipients can still settle
    differently when their submitted rosters differ; such actions keep their
    submitted identity and are never collapsed onto each other. The
    classification is settlement's own -- ``world.rules.action.resist_contest``
    reads the same catalog and generic branches the step-4b gate does -- rather
    than a second copy that could drift from it.
    """
    catalog_act, generic_resistible = resist_contest(skill)
    return catalog_act or generic_resistible


def _supports_every_harmful_effect(skill: SkillDef) -> bool:
    """Return whether every potentially harmful effect resolves to a definition.

    Two unresolvable harms make a skill unrepresentable for this slice: a damage
    effect naming an element the element registry does not carry can never
    settle (the cast-time parser raises on it), and an effect naming a buff or
    sexual-act definition the owning registry does not carry can never mount or
    resolve anything. Excluding the skill here keeps an unknown harmful outcome
    out of scoring instead of letting it fail at settlement; the outcome models
    themselves belong to ``monster-ai-damage-estimation``, which extends this
    boundary.
    """
    for effect in skill.parsed_effects:
        if isinstance(effect, DamageEffect) and (
            effect.element is not None and effect.element not in ELEMENT_REGISTRY
        ):
            return False
        if isinstance(effect, _BUFF_REFERENCE_EFFECTS) and (
            effect.buff_key not in BUFF_DEFINITIONS
        ):
            return False
        if isinstance(effect, _ACT_REFERENCE_EFFECTS) and (
            effect.act_key not in SEXUAL_ACT_REGISTRY
        ):
            return False
    return True


def _representation_rank(proposal: _Proposal) -> tuple[int, int, str]:
    """Return one proposal's representation preference.

    The family kind ranks first, so a collapsed class keeps its least
    constrained group: the hostile roster is a subset of the complete one and
    the friendly roster is too, so settlement's per-submitted-target gates
    cannot reject the retained representation while accepting a collapsed
    sibling. Within one kind the authored AREA shorthand wins over an
    equivalent explicit roster, and explicit identifiers order the remainder.
    """
    return (
        _FAMILY_KINDS.index(proposal.family[1]),
        0 if proposal.plan.shorthand is not None else 1,
        proposal.plan.shorthand or ",".join(proposal.identity.target_ids),
    )


def _family_order(
    families: dict[tuple[str, str], list[_Proposal]],
) -> list[tuple[str, str]]:
    """Return the canonical family order (skill, then semantic plan kind)."""
    return sorted(
        families,
        key=lambda family: (family[0], _FAMILY_KINDS.index(family[1])),
    )


def _ring_order(
    families: dict[tuple[str, str], list[_Proposal]],
    snapshot: DecisionSnapshot,
) -> list[tuple[str, str]]:
    """Return the canonical family order rotated by the scope's digest offset.

    A rotation visits every family exactly once per pass whatever the offset,
    so the ring decides only which family a spent budget reaches first. The
    offset is the execution scope's deterministic digest -- never a selection
    or combat RNG draw.
    """
    canonical = _family_order(families)
    if not canonical:
        return []
    offset = int(_scope_digest(snapshot), 16) % len(canonical)
    return canonical[offset:] + canonical[:offset]


def _allocate(
    families: dict[tuple[str, str], list[_Proposal]],
    ring: list[tuple[str, str]],
    outcome: Callable[[_Proposal], Candidate | CandidateRejection],
    admit: Callable[[_Proposal], bool],
) -> tuple[tuple[Candidate, ...], dict[tuple[str, str], int]]:
    """Examine deduplicated proposals round-robin while the budget allows.

    ``ring`` is the family order the decision walks (see :func:`_ring_order`).
    Returns that walk's legal candidates in ring order and how far each family
    was walked, so the caller can report what the budget left unexamined. A
    proposal the mandatory-filter capability search already examined is admitted
    without charging another slot -- it is the same examination, and the ledger
    already reports it. A proposal the budget cannot pay for is skipped in
    place (its cursor stays put, so it is reported as unexamined) rather than
    ending the walk: a later family may still hold an examination that was
    already paid for. A paid plan behind such a hole is out of the walk's reach,
    because the cursor never leaves the first proposal a family cannot pay for;
    the caller collects that one without advancing any cursor.
    """
    cursors = dict.fromkeys(ring, 0)
    candidates: list[Candidate] = []
    while True:
        progressed = False
        for family in ring:
            position = cursors[family]
            if position >= len(families[family]):
                continue
            if not admit(families[family][position]):
                continue
            progressed = True
            cursors[family] = position + 1
            examined = outcome(families[family][position])
            if isinstance(examined, Candidate):
                candidates.append(examined)
        if not progressed:
            break
    return tuple(candidates), cursors


def _examine(
    proposal: _Proposal,
    actor: Any,
    context: Any,
    verdict: Callable[[SkillDef, PlannedAction], PlanVerdict],
) -> Candidate | CandidateRejection:
    """Validate one proposal and refuse a plan the damage model cannot represent."""
    result = verdict(proposal.skill, proposal.plan)
    if not result.legal:
        return CandidateRejection(proposal.identity, result.reason, result.detail)
    if not _reaches_hostile(actor, context, proposal.skill, proposal.routed):
        return CandidateRejection(
            proposal.identity,
            _UNREPRESENTABLE,
            "supported hostile damage reaches no hostile recipient",
        )
    return Candidate(
        proposal.identity,
        proposal.plan,
        recipients=proposal.recipients,
        routed=proposal.routed,
    )


def _reaches_hostile(
    actor: Any,
    context: Any,
    skill: SkillDef,
    routed: tuple[tuple[Any, ...], ...] | None,
) -> bool:
    """Return whether one plan delivers supported damage to a hostile recipient.

    The shared audience planner routes each declared effect over the plan's own
    recipients. A plan whose damage reaches no hostile -- because an audience
    condition filtered it out, or because the plan only ever reaches the actor
    or an ally -- is a plan the damage model cannot represent, so it is excluded
    rather than scored as if it dealt damage.
    """
    if routed is None:
        return False
    for effect, reached in zip(skill.parsed_effects, routed):
        if isinstance(effect, DamageEffect) and any(
            context.relation_to(actor, target) is Relation.ENEMY for target in reached
        ):
            return True
    return False


def _validated_budget(budget: Any) -> int:
    """Return one candidate budget inside the authored integer 1..4096 bound."""
    if isinstance(budget, bool) or not isinstance(budget, int):
        raise ValueError(f"candidate budget must be an integer, got {budget!r}")
    if not MIN_CANDIDATE_BUDGET <= budget <= MAX_CANDIDATE_BUDGET:
        raise ValueError(
            f"candidate budget must be {MIN_CANDIDATE_BUDGET}..{MAX_CANDIDATE_BUDGET}, "
            f"got {budget!r}"
        )
    return budget


def _validated_scale(scale: Any) -> float:
    """Return one authored cast magnitude, rejecting anything else."""
    if isinstance(scale, bool) or not isinstance(scale, (int, float)):
        raise ValueError(f"candidate scale must be a real number, got {scale!r}")
    magnitude = float(scale)
    if not isfinite(magnitude) or magnitude <= 0:
        raise ValueError(f"candidate scale must be positive and finite, got {scale!r}")
    return magnitude


def _declared_order(order: Iterable[str]) -> tuple[str, ...]:
    """Return the archetype's declared target ordering as stable identities."""
    if isinstance(order, (str, bytes)) or not isinstance(order, Sequence):
        raise ValueError(f"declared target order must be a sequence, got {order!r}")
    for identity in order:
        if not isinstance(identity, str):
            raise ValueError(
                f"declared target order must hold identities, got {identity!r}"
            )
    return tuple(order)


def _scope_digest(snapshot: DecisionSnapshot) -> str:
    """Return the execution scope's deterministic ring-offset digest.

    The actual scope (session, round and action slot) plus the actor's stable
    identity, hashed: never a Python ``hash()``, a display label or an object
    address, and never a draw from the selection or combat RNG.
    """
    scope = snapshot.scope
    payload = "\x1f".join(
        (
            scope.session_id,
            str(scope.round_index),
            str(scope.slot_index),
            snapshot.actor.identity,
        )
    )
    return sha256(payload.encode("utf-8")).hexdigest()
