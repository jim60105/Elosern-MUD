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
from world.rules.action import RejectReason, RejectedAction, plan_effect_audiences
from world.rules.action_preview import preview_skill
from world.rules.buffs import has_positional_marker
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
from world.skills.effects import DamageEffect, EffectAudience
from world.skills.registry import FactionConstraint, SkillDef, SkillKind, TargetSpec

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

#: The approved AREA shorthand whose expansion is exactly each group kind.
_GROUP_SHORTHANDS = {
    KIND_HOSTILE: "all-enemies",
    KIND_FRIENDLY: "all-allies",
    KIND_COMPLETE: "all",
}

#: The reason an examined plan the shared gates allow is still unusable: the
#: AI cannot resolve its effects into a supported hostile damage outcome.
_UNREPRESENTABLE = RejectReason.EFFECT_RESOLUTION_FAILED

#: One cached legality verdict per distinct proposed action.
_VerdictKey = tuple[str, float, str | None, tuple[str, ...]]


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
    """

    identity: CandidateIdentity
    plan: PlannedAction


@dataclass(frozen=True, slots=True)
class CandidateRejection:
    """One examined proposal the shared legality (or the damage model) refused."""

    identity: CandidateIdentity
    reason: RejectReason
    detail: str | None


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

    ``examined`` is the number of deduplicated proposals the family ring
    actually examined, rejected ones included, and never exceeds the budget.
    ``exhausted`` is true when the ring stopped at the bound with distinct
    proposals still unexamined; ``omitted_families`` and ``omitted_targets``
    count what was left. A duplicate representation is not a proposal, so it
    can neither consume a slot nor report exhaustion.
    """

    candidates: tuple[Candidate, ...] = ()
    rejections: tuple[CandidateRejection, ...] = ()
    unavailable: tuple[SkillObservation, ...] = ()
    examined: int = 0
    exhausted: bool = False
    omitted_families: int = 0
    omitted_targets: int = 0

    @property
    def plans(self) -> tuple[PlannedAction, ...]:
        """Every legal candidate's runtime request, in ring order."""
        return tuple(candidate.plan for candidate in self.candidates)


@dataclass(frozen=True, slots=True)
class _Proposal:
    """One deduplicated proposal the family ring may examine."""

    family: tuple[str, str]
    skill: SkillDef
    plan: PlannedAction
    identity: CandidateIdentity
    recipients: tuple[Any, ...]


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
    pool = _decision_pool(snapshot, actor, roster, context)
    hostile = _hostile_domain(snapshot, pool)

    skills: list[SkillDef] = []
    unavailable: list[SkillObservation] = []
    for skill_key in sorted(reader.owned_keys(actor)):
        skill = reader.skill(skill_key)
        if not _is_hostile_damage(skill):
            continue
        if not _resolves_every_harmful_effect(skill):
            unavailable.append(
                SkillObservation(
                    skill.key,
                    _UNREPRESENTABLE,
                    "a potentially harmful effect names an unregistered element",
                )
            )
            continue
        broad = preview_skill(actor, skill.key, context, None, magnitude, reader)
        if not broad.enabled:
            unavailable.append(SkillObservation(skill.key, broad.reason, broad.detail))
            continue
        skills.append(skill)

    verdicts: dict[_VerdictKey, PlanVerdict] = {}

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
    alternative = _has_castable_nonstrike_alternative(singles, hostile, magnitude, verdict)

    families: dict[tuple[str, str], list[_Proposal]] = {}
    for skill in skills:
        proposals = _skill_proposals(
            skill,
            snapshot,
            pool,
            hostile,
            actor,
            context,
            magnitude,
            declared,
            sealed,
            displaced,
            alternative,
        )
        for proposal in proposals:
            families.setdefault(proposal.family, []).append(proposal)

    distinct = _deduplicate(families)
    return _allocate(
        distinct, limit, snapshot, actor, context, roster, reader, verdict, unavailable
    )


def _skill_proposals(
    skill: SkillDef,
    snapshot: DecisionSnapshot,
    pool: tuple[Any, ...],
    hostile: tuple[Any, ...],
    actor: Any,
    context: Any,
    scale: float,
    declared: tuple[str, ...],
    sealed: tuple[Any, ...],
    displaced: frozenset[str],
    alternative: bool,
) -> list[_Proposal]:
    """Return one skill's proposals for the decision's own target shapes."""
    if skill.target_spec is TargetSpec.SINGLE:
        return [
            _Proposal(
                (skill.key, KIND_SINGLE),
                skill,
                PlannedAction(
                    skill.key, scale, target_ids=(stable_identity(target),)
                ),
                CandidateIdentity(skill.key, scale, (stable_identity(target),)),
                (target,),
            )
            for target in _single_base(
                skill, hostile, declared, sealed, displaced, alternative
            )
        ]
    if skill.target_spec is TargetSpec.AREA:
        return _group_proposals(
            skill, snapshot, pool, actor, context, scale, _is_mixed(skill)
        )
    return [
        _Proposal(
            (skill.key, KIND_IMPLICIT),
            skill,
            PlannedAction(skill.key, scale),
            CandidateIdentity(skill.key, scale, ()),
            (),
        )
    ]


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
        members = _group_members(kind, snapshot, pool)
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
    scale: float,
    verdict: Callable[[SkillDef, PlannedAction], PlanVerdict],
) -> bool:
    """Return whether a genuinely castable non-strike hostile alternative exists.

    "Genuinely castable" is a legal plan, not skill metadata: a self-heal is
    not a damage skill at all, and an uncastable magic skill has no legal plan
    against a hostile target, so neither satisfies the alternative-attack
    condition that keeps displaced targets reachable.
    """
    for skill in singles:
        if is_strike_class(skill):
            continue
        for target in hostile:
            plan = PlannedAction(
                skill.key, scale, target_ids=(stable_identity(target),)
            )
            if verdict(skill, plan).legal:
                return True
    return False


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


def _resolves_every_harmful_effect(skill: SkillDef) -> bool:
    """Return whether every damage effect resolves against the live elements.

    A damage effect naming an element the element registry does not carry can
    never settle (the cast-time parser raises on it), so the skill is
    unrepresentable: excluding it here keeps an unknown harmful outcome out of
    scoring instead of letting it fail at settlement.
    """
    return all(
        effect.element is None or effect.element in ELEMENT_REGISTRY
        for effect in skill.parsed_effects
        if isinstance(effect, DamageEffect)
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


def _decision_pool(
    snapshot: DecisionSnapshot,
    actor: Any,
    roster: dict[str, Any],
    context: Any,
) -> tuple[Any, ...]:
    """Return the live participants this decision actually covers.

    The actor plus every participant the snapshot names that the reconstruction
    roster still carries, minus the battlefield's knocked-out members -- the
    same expression the shared shorthand expansion applies, so a group and its
    shorthand always describe the same combatants.
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


def _hostile_domain(snapshot: DecisionSnapshot, pool: tuple[Any, ...]) -> tuple[Any, ...]:
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


def _group_members(
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

    One identity keeps exactly one representation, preferring the authored AREA
    shorthand, so a duplicate can never increase sampling probability and no
    ring offset can decide which representation survives: the retained shape is
    chosen here, before allocation and independently of family rotation.
    """
    ordered = [
        (family, proposal)
        for family in _family_order(families)
        for proposal in families[family]
    ]
    best: dict[CandidateIdentity, _Proposal] = {}
    for _family, proposal in ordered:
        current = best.get(proposal.identity)
        if current is None or _representation_rank(proposal) < _representation_rank(current):
            best[proposal.identity] = proposal
    surviving: dict[tuple[str, str], list[_Proposal]] = {}
    for family, proposal in ordered:
        if best[proposal.identity] is proposal:
            surviving.setdefault(family, []).append(proposal)
    return surviving


def _representation_rank(proposal: _Proposal) -> tuple[int, int, str]:
    """Return one proposal's representation preference (shorthand first)."""
    return (
        0 if proposal.plan.shorthand is not None else 1,
        _FAMILY_KINDS.index(proposal.family[1]),
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


def _allocate(
    families: dict[tuple[str, str], list[_Proposal]],
    limit: int,
    snapshot: DecisionSnapshot,
    actor: Any,
    context: Any,
    roster: dict[str, Any],
    reads: DecisionReads,
    verdict: Callable[[SkillDef, PlannedAction], PlanVerdict],
    unavailable: list[SkillObservation],
) -> CandidateSet:
    """Examine deduplicated proposals round-robin until the budget is spent."""
    canonical = _family_order(families)
    if canonical:
        offset = int(_scope_digest(snapshot), 16) % len(canonical)
        ring = canonical[offset:] + canonical[:offset]
    else:
        ring = []
    cursors = dict.fromkeys(ring, 0)
    candidates: list[Candidate] = []
    rejections: list[CandidateRejection] = []
    examined = 0
    while examined < limit:
        progressed = False
        for family in ring:
            if examined >= limit:
                break
            position = cursors[family]
            if position >= len(families[family]):
                continue
            progressed = True
            cursors[family] = position + 1
            examined += 1
            outcome = _examine(
                families[family][position],
                actor,
                context,
                roster,
                reads,
                verdict,
            )
            if isinstance(outcome, Candidate):
                candidates.append(outcome)
            else:
                rejections.append(outcome)
        if not progressed:
            break
    omitted = [
        family for family in canonical if cursors[family] < len(families[family])
    ]
    return CandidateSet(
        candidates=tuple(candidates),
        rejections=tuple(rejections),
        unavailable=tuple(unavailable),
        examined=examined,
        exhausted=bool(omitted),
        omitted_families=len(omitted),
        omitted_targets=sum(
            len(families[family]) - cursors[family] for family in omitted
        ),
    )


def _examine(
    proposal: _Proposal,
    actor: Any,
    context: Any,
    roster: dict[str, Any],
    reads: DecisionReads,
    verdict: Callable[[SkillDef, PlannedAction], PlanVerdict],
) -> Candidate | CandidateRejection:
    """Validate one proposal and refuse a plan the damage model cannot represent."""
    result = verdict(proposal.skill, proposal.plan)
    if not result.legal:
        return CandidateRejection(proposal.identity, result.reason, result.detail)
    if not _reaches_hostile(actor, context, proposal.skill, proposal.recipients, reads):
        return CandidateRejection(
            proposal.identity,
            _UNREPRESENTABLE,
            "supported hostile damage reaches no hostile recipient",
        )
    return Candidate(proposal.identity, proposal.plan)


def _reaches_hostile(
    actor: Any,
    context: Any,
    skill: SkillDef,
    recipients: tuple[Any, ...],
    reads: DecisionReads,
) -> bool:
    """Return whether one plan delivers supported damage to a hostile recipient.

    The shared audience planner routes each declared effect over the plan's own
    recipients. A plan whose damage reaches no hostile -- because an audience
    condition filtered it out, or because the plan only ever reaches the actor
    or an ally -- is a plan the damage model cannot represent, so it is excluded
    rather than scored as if it dealt damage.
    """
    if not recipients:
        return False
    try:
        routed = plan_effect_audiences(
            actor, context, skill, list(recipients), readings=reads
        )
    except RejectedAction:
        # observability: ignore R2: every routed audience is empty, which is
        # exactly the unrepresentable plan this predicate reports
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
