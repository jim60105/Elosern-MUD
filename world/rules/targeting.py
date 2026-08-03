"""Combat-agnostic target validation for deterministic actions."""

from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from world.skills.registry import FactionConstraint, SkillDef, TargetSpec


# The approved deterministic AREA shorthands accepted in combat.
AREA_SHORTHANDS = ("all-enemies", "all-allies", "all")


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

    def is_in_range(self, actor: Any, target: Any, skill: SkillDef) -> bool: ...


class BattlefieldActionContext(ActionContext, Protocol):
    """Protocol target for change 9's roster, teams, and range implementation."""


class RoomActionContext:
    """Out-of-combat context where every co-located non-self entity is allied."""

    battlefield = None

    def __init__(
        self,
        room: Any,
        event_context: dict[str, Any] | None = None,
    ):
        self.room = room
        self.event_context = {} if event_context is None else dict(event_context)

    def is_present(self, actor: Any, target: Any) -> bool:
        return target is actor or (
            self.room is not None
            and actor.location is self.room
            and target.location is self.room
        )

    def relation_to(self, actor: Any, target: Any) -> Relation:
        return Relation.SELF if target is actor else Relation.ALLY

    def is_in_range(self, actor: Any, target: Any, skill: SkillDef) -> bool:
        return True


def validate_faction(
    relation: Relation,
    constraint: FactionConstraint,
) -> bool:
    """Return whether a relation satisfies a skill-owned constraint."""
    return {
        FactionConstraint.ANY: True,
        FactionConstraint.SELF_ONLY: relation is Relation.SELF,
        FactionConstraint.ALLY: relation in {Relation.SELF, Relation.ALLY},
        FactionConstraint.ENEMY: relation is Relation.ENEMY,
    }[constraint]


def _rejection(reason: str, detail: str):
    from world.rules.action import RejectReason, RejectedAction

    raise RejectedAction(RejectReason(reason), detail)


def _validate_presence(request: Any, target: Any, skill: SkillDef) -> None:
    if not request.context.is_present(request.actor, target):
        _rejection("target_not_present", getattr(target, "key", repr(target)))


def _validate_alive(request: Any, target: Any, skill: SkillDef) -> None:
    try:
        from world.rules.action import _stored_trait_value

        alive = _stored_trait_value(target.traits.hp) > 0
    except (AttributeError, KeyError):
        alive = False
    if not alive:
        _rejection("target_dead", getattr(target, "key", repr(target)))


def _validate_range(request: Any, target: Any, skill: SkillDef) -> None:
    if not request.context.is_in_range(request.actor, target, skill):
        _rejection("target_out_of_range", getattr(target, "key", repr(target)))


def _validate_faction(request: Any, target: Any, skill: SkillDef) -> None:
    relation = request.context.relation_to(request.actor, target)
    if not validate_faction(relation, skill.faction_constraint):
        _rejection("target_faction_forbidden", getattr(target, "key", repr(target)))


_VALIDATORS = (
    _validate_presence,
    _validate_alive,
    _validate_range,
    _validate_faction,
)


def _validate_candidate(request: Any, target: Any, skill: SkillDef) -> None:
    for validator in _VALIDATORS:
        validator(request, target, skill)


def candidate_rejection(
    request: Any,
    target: Any,
    skill: SkillDef,
) -> tuple[Any, str] | None:
    """Return the first ordered validation failure for one target, or ``None``.

    Runs the identical presence, alive, range, and faction validators in the
    same order as final target resolution so read-only preview and revalidation
    never drift from execution.
    """
    from world.rules.action import RejectedAction

    for validator in _VALIDATORS:
        try:
            validator(request, target, skill)
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
    request: Any,
    skill: SkillDef,
    candidates: list[Any],
) -> list[Any]:
    """Validate target cardinality and candidates in the required order.

    Target-shape validation runs before candidate validation. NONE accepts no
    candidates; SELF accepts normalized empty input or exactly the actor;
    SINGLE requires exactly one explicit candidate; AREA requires a nonempty
    unique list (empty or duplicate explicit input is malformed).
    """
    if skill.target_spec is TargetSpec.NONE:
        if candidates:
            _rejection("target_spec_mismatch", "none-target skill accepts no targets")
        return []
    if skill.target_spec is TargetSpec.SELF:
        if not candidates:
            candidates = [request.actor]
        if len(candidates) != 1 or candidates[0] is not request.actor:
            _rejection("target_spec_mismatch", "self-target skill requires the actor")
    elif skill.target_spec is TargetSpec.SINGLE:
        if len(candidates) != 1:
            _rejection("target_spec_mismatch", "single-target skill requires one target")
    elif skill.target_spec is TargetSpec.AREA:
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

    if skill.target_spec is not TargetSpec.AREA:
        for target in candidates:
            _validate_candidate(request, target, skill)
        return list(candidates)

    valid = []
    for target in candidates:
        try:
            _validate_candidate(request, target, skill)
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
    if shorthand == "all":
        return roster
    wanted = (
        {Relation.ENEMY}
        if shorthand == "all-enemies"
        else {Relation.SELF, Relation.ALLY}
    )
    return [
        target
        for target in roster
        if context.relation_to(actor, target) in wanted
    ]
