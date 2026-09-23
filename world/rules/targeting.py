"""Combat-agnostic target validation for deterministic actions.

The resolver consumes a definition-owned ``TargetRequirement`` value — the
target shape, the faction constraint, and the forbid-self rule — and knows
nothing about what produced it. Skills reach the pipeline through
``requirement_for(skill)``; any other definition that can describe the
same three rules (for example a usable item's declared scope) constructs a
requirement directly and reuses the identical presence/alive/range/faction
pipeline without owning or fabricating a skill. No validator, resolver, or
context method in this module inspects the identity, category, or effect list
of whatever produced the requirement.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from world.skills.registry import FactionConstraint, SkillCategory, SkillDef, TargetSpec


# The approved deterministic AREA shorthands accepted in combat.
AREA_SHORTHANDS = ("all-enemies", "all-allies", "all")


@dataclass(frozen=True)
class TargetRequirement:
    """The definition-supplied targeting rule the shared resolver consumes.

    One frozen value object carries the three rules that always travel
    together: the target shape (``spec``), the faction constraint
    (``faction``, default ``ANY``), and the self-target prohibition
    (``forbid_self``, default ``False``). The definition being acted on
    produces it — ``requirement_for(skill)`` for skills, direct
    construction for any other caller — never the calling request. The item
    scopes of the approved item-effect model map onto the four distinct
    shapes covering five scopes: ``SELF``/``SELF_ONLY``, ``SINGLE``/``ANY``,
    ``SINGLE``/``ANY`` with ``forbid_self``, and the three group scopes'
    shared ``AREA``/``ANY``.
    """

    spec: TargetSpec
    faction: FactionConstraint = FactionConstraint.ANY
    forbid_self: bool = False


def requirement_for(skill: SkillDef) -> TargetRequirement:
    """The targeting rule one skill definition states.

    ``forbid_self`` states the definition's own prohibition on targeting the
    actor — every ``SEXUAL_ACT`` skill and sexual-ministry ``HOLY_RITE``
    (``group="聖禮"``) declares it (their SINGLE-target acts are two-participant
    by construction), and the resolver merely enforces the flag it is given.
    The derivation lives on the rules side so the definition module never
    depends on this one; the resolver still consumes the plain value, never
    the definition.
    """
    return TargetRequirement(
        skill.target_spec,
        skill.faction_constraint,
        forbid_self=(
            skill.category is SkillCategory.SEXUAL_ACT
            or (skill.category is SkillCategory.HOLY_RITE and skill.group == "聖禮")
        ),
    )


class Relation(StrEnum):
    """An action context's relation between two entities."""

    SELF = "self"
    ALLY = "ally"
    ENEMY = "enemy"


@runtime_checkable
class ActionContext(Protocol):
    """Caller-supplied world view used by the shared targeting pipeline."""

    battlefield: Any | None
    event_context: dict[str, Any]

    def is_present(self, actor: Any, target: Any) -> bool: ...

    def relation_to(self, actor: Any, target: Any) -> Relation: ...

    def is_in_range(self, actor: Any, target: Any) -> bool: ...


class BattlefieldActionContext(ActionContext, Protocol):
    """Protocol target for change 9's roster, teams, and range implementation."""


class RoomActionContext:
    """Out-of-combat context where every co-located non-self entity is allied.

    The ``event_context`` the caller supplies is copied, then
    ``event_context["room"]`` is injected unconditionally, bound to the
    constructed context's room — effect handlers and presenters reading
    ``event_context`` can deterministically discover the out-of-combat
    location without a new handler surface (``observers_present`` reads it
    for the room-occupancy presence check). A caller-supplied ``"room"`` key
    was meaningless before the injection and is replaced, never duplicated.
    """

    battlefield = None

    def __init__(
        self,
        room: Any,
        event_context: dict[str, Any] | None = None,
    ):
        self.room = room
        self.event_context = {} if event_context is None else dict(event_context)
        self.event_context["room"] = self.room

    def is_present(self, actor: Any, target: Any) -> bool:
        return target is actor or (
            self.room is not None
            and actor.location is self.room
            and target.location is self.room
        )

    def relation_to(self, actor: Any, target: Any) -> Relation:
        return Relation.SELF if target is actor else Relation.ALLY

    def is_in_range(self, actor: Any, target: Any) -> bool:
        return True


def validate_faction(
    relation: Relation,
    constraint: FactionConstraint,
) -> bool:
    """Return whether a relation satisfies a skill-owned constraint.

    Only the self-only rule is enforced: ``ANY`` (the only constraint shipped
    attack and recovery skills may declare) accepts every relation, while
    ``SELF_ONLY`` accepts only the actor. The legacy ``ALLY``/``ENEMY``
    constraint values are accepted by this function for completeness but no
    shipped skill declares them (fix-friendly-fire-reachability D1).
    """
    if constraint is FactionConstraint.SELF_ONLY:
        return relation is Relation.SELF
    return True


def _rejection(reason: str, detail: str):
    from world.rules.action import RejectReason, RejectedAction

    raise RejectedAction(RejectReason(reason), detail)


def _validate_presence(
    actor: Any,
    context: ActionContext,
    requirement: TargetRequirement,
    target: Any,
) -> None:
    if not context.is_present(actor, target):
        _rejection("target_not_present", getattr(target, "key", repr(target)))


def _validate_alive(
    actor: Any,
    context: ActionContext,
    requirement: TargetRequirement,
    target: Any,
) -> None:
    try:
        from world.rules.action import _stored_trait_value

        alive = _stored_trait_value(target.traits.hp) > 0
    except (AttributeError, KeyError):
        alive = False
    if not alive:
        _rejection("target_dead", getattr(target, "key", repr(target)))


def _validate_range(
    actor: Any,
    context: ActionContext,
    requirement: TargetRequirement,
    target: Any,
) -> None:
    if not context.is_in_range(actor, target):
        _rejection("target_out_of_range", getattr(target, "key", repr(target)))


def _validate_faction(
    actor: Any,
    context: ActionContext,
    requirement: TargetRequirement,
    target: Any,
) -> None:
    relation = context.relation_to(actor, target)
    if not validate_faction(relation, requirement.faction):
        _rejection("target_faction_forbidden", getattr(target, "key", repr(target)))


_VALIDATORS = (
    _validate_presence,
    _validate_alive,
    _validate_range,
    _validate_faction,
)


def _validate_candidate(
    actor: Any,
    context: ActionContext,
    requirement: TargetRequirement,
    target: Any,
) -> None:
    for validator in _VALIDATORS:
        validator(actor, context, requirement, target)


def candidate_rejection(
    actor: Any,
    context: ActionContext,
    requirement: TargetRequirement,
    target: Any,
) -> tuple[Any, str] | None:
    """Return the first ordered validation failure for one target, or ``None``.

    Runs the identical presence, alive, range, and faction validators in the
    same order as final target resolution so read-only preview and revalidation
    never drift from execution.
    """
    from world.rules.action import RejectedAction

    for validator in _VALIDATORS:
        try:
            validator(actor, context, requirement, target)
        except RejectedAction as rejection:
            return rejection.reason, rejection.detail
    return None


def _target_identity(target: Any) -> tuple[str, int]:
    """Return a stable identity for one candidate object."""
    pk = getattr(target, "pk", None)
    if isinstance(pk, int):
        return ("pk", pk)
    return ("id", id(target))


def resolve_targets(
    actor: Any,
    context: ActionContext,
    requirement: TargetRequirement,
    candidates: list[Any],
) -> list[Any]:
    """Validate target cardinality and candidates in the required order.

    Target-shape validation runs before candidate validation. NONE accepts no
    candidates; SELF accepts normalized empty input or exactly the actor;
    SINGLE requires exactly one explicit candidate; AREA requires a nonempty
    unique list (empty or duplicate explicit input is malformed).
    """
    if requirement.spec is TargetSpec.NONE:
        if candidates:
            _rejection("target_spec_mismatch", "none-target skill accepts no targets")
        return []
    if requirement.spec is TargetSpec.SELF:
        if not candidates:
            candidates = [actor]
        if len(candidates) != 1 or candidates[0] is not actor:
            _rejection("target_spec_mismatch", "self-target skill requires the actor")
    elif requirement.spec is TargetSpec.SINGLE:
        if len(candidates) != 1:
            _rejection("target_spec_mismatch", "single-target skill requires one target")
        if requirement.forbid_self and candidates[0] is actor:
            # A requirement that forbids the actor as its own SINGLE target
            # states the prohibition itself (every sexual-act skill's
            # requirement does: a two-participant act credited with no
            # partner present would skew lifetime counters). The resolver
            # only enforces the flag it was given.
            _rejection(
                "target_spec_mismatch",
                "a sexual act targeting another entity requires a target other than the actor",
            )
    elif requirement.spec is TargetSpec.AREA:
        if not candidates:
            _rejection("no_valid_targets_in_area", "area skill has no candidates")
        seen: set[tuple[str, int]] = set()
        for target in candidates:
            identity = _target_identity(target)
            if identity in seen:
                _rejection(
                    "target_spec_mismatch",
                    "area skill cannot repeat a target identity",
                )
            seen.add(identity)

    if requirement.spec is not TargetSpec.AREA:
        for target in candidates:
            _validate_candidate(actor, context, requirement, target)
        return list(candidates)

    valid = []
    for target in candidates:
        try:
            _validate_candidate(actor, context, requirement, target)
        except Exception as error:
            from world.rules.action import RejectedAction

            if not isinstance(error, RejectedAction):
                raise
        else:
            valid.append(target)
    if not valid:
        _rejection("no_valid_targets_in_area", "all area candidates were invalid")
    return valid


def expand_target_shorthand(
    actor: Any,
    context: ActionContext,
    shorthand: str,
) -> list[Any]:
    """Expand battlefield roster sugar before normal validation."""
    battlefield = context.battlefield
    if battlefield is None:
        _rejection("target_spec_mismatch", f"{shorthand} requires a battlefield")
    if shorthand not in {"all-enemies", "all-allies", "all"}:
        _rejection("target_spec_mismatch", f"unknown shorthand {shorthand!r}")
    roster = list(battlefield.roster.values())
    # Knocked-out combatants are never selectable, through any shorthand
    # (party-combat D-2). The read is duck-typed so non-combat or fake
    # battlefields without the knockout state keep the pre-existing behavior.
    knocked_out = frozenset(getattr(battlefield, "knocked_out", ()))
    if shorthand == "all":
        return [
            target for target in roster if str(target.key) not in knocked_out
        ]
    wanted = (
        {Relation.ENEMY}
        if shorthand == "all-enemies"
        else {Relation.SELF, Relation.ALLY}
    )
    return [
        target
        for target in roster
        if context.relation_to(actor, target) in wanted
        and str(target.key) not in knocked_out
    ]
