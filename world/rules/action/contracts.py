"""Shared contracts for the atomic, deterministic skill-action pipeline.

Every module of the ``world.rules.action`` package imports its data types,
exception vocabulary, and handler registries from here; this module has no
intra-package imports so it can never form an import cycle.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable, Literal

from world.rules.event_log import EventLog
from world.rules.targeting import ActionContext


class RejectReason(StrEnum):
    """Stable rejection identifiers for every action-pipeline failure."""

    UNKNOWN_SKILL = "unknown_skill"
    SKILL_NOT_ACTIVE = "skill_not_active"
    SKILL_NOT_USABLE_OUT_OF_COMBAT = "skill_not_usable_out_of_combat"
    DAMAGE_REQUIRES_MONSTER_TARGET = "damage_requires_monster_target"
    INSUFFICIENT_RESOURCE = "insufficient_resource"
    TARGET_SPEC_MISMATCH = "target_spec_mismatch"
    TARGET_NOT_PRESENT = "target_not_present"
    TARGET_DEAD = "target_dead"
    TARGET_OUT_OF_RANGE = "target_out_of_range"
    TARGET_FACTION_FORBIDDEN = "target_faction_forbidden"
    NO_VALID_TARGETS_IN_AREA = "no_valid_targets_in_area"
    ACTION_FORBIDDEN = "action_forbidden"
    DIVINE_ARTS_FORBIDDEN = "divine_arts_forbidden"
    SCALED_CAST_FORBIDDEN = "scaled_cast_forbidden"
    CAST_CONDITION_UNMET = "cast_condition_unmet"
    UNKNOWN_EFFECT_ID = "unknown_effect_id"
    EFFECT_RESOLUTION_FAILED = "effect_resolution_failed"
    MISSING_EFFECT_CONTEXT = "missing_effect_context"
    RESOURCE_DEDUCTION_FAILED = "resource_deduction_failed"
    EVENT_LOG_CONSTRUCTION_FAILED = "event_log_construction_failed"
    TIME_COST_LOOKUP_FAILED = "time_cost_lookup_failed"
    UNSNAPSHOTTED_EFFECT_SURFACE = "unsnapshotted_effect_surface"
    COMMIT_FAILED = "commit_failed"
    RITE_NOT_ENROLLED = "rite_not_enrolled"
    RITE_COOLDOWN_ACTIVE = "rite_cooldown_active"
    RITE_OUTSIDE_VENUE = "rite_outside_venue"
    RITE_ALREADY_SHELTERED = "rite_already_sheltered"



class RejectedAction(Exception):
    """A pre-commit action rejection."""

    def __init__(self, reason: RejectReason, detail: str = ""):
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


class CommitFailed(Exception):
    """A commit rejection after state has been restored."""

    def __init__(self, reason: RejectReason, detail: str = ""):
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class ActionRequest:
    """One caller-neutral request to invoke a skill.

    ``scale`` is the optional freeform magnitude modifier (element-mastery-
    freeform-casting): ``1.0`` is the behavior-preserving default and is
    always allowed; any other value must pass the step-1 freeform gate.
    """

    actor: Any
    skill_key: str
    targets: list[Any] | Literal["all-enemies", "all-allies", "all"]
    context: ActionContext
    scale: float = 1.0


@dataclass(frozen=True)
class ActionResult:
    """Success or rejection returned without leaking pipeline exceptions."""

    outcome: Literal["success", "rejected"]
    event_log: EventLog | None
    time_cost_seconds: int | None
    reason: RejectReason | None
    detail: str | None
    # Player-facing notification lines staged by committed effects (e.g. the
    # title planner's grant toasts). Delivered only after the OUTER settlement
    # transaction commits — resolve() only returns them; callers emit.
    notifications: tuple[str, ...] = ()

    @classmethod
    def success(
        cls,
        event_log: EventLog,
        time_cost: int,
        notifications: tuple[str, ...] = (),
    ) -> "ActionResult":
        return cls("success", event_log, time_cost, None, None, notifications)

    @classmethod
    def rejected(
        cls,
        reason: RejectReason,
        detail: str = "",
    ) -> "ActionResult":
        return cls("rejected", None, None, reason, detail)


@dataclass(frozen=True)
class PendingEffect:
    """A state mutation staged for the single commit point."""

    entity: Any
    description: str
    surfaces: frozenset[str]
    apply: Callable[[], None]
    # A player-facing notification line delivered (by the outer settlement
    # boundary, never by the writer) only when this effect commits. ``None``
    # stages nothing.
    notify: str | None = None


class UnsnapshottedSurfaceError(Exception):
    """A handler declared state that the commit mechanism cannot restore."""


EffectHandler = Callable[
    [Any, list[Any], str, dict[str, Any], float],
    list[PendingEffect],
]
SNAPSHOTTED_SURFACES = frozenset(
    {
        "active_combat",
        "traits",
        "sexual",
        "buffs",
        "skill_grants",
        "progression",
        "titles",
        "battlefield",
        "quest_log",
        "instance_pin",
        "wallet",
        "inventory",
        "reward_claims",
        "action_evidence",
        "church",
    }
)
_EFFECT_HANDLERS: dict[str, EffectHandler] = {}
_EFFECT_HANDLER_SURFACES: dict[str, frozenset[str]] = {}
_EFFECT_HANDLER_REQUIRED_CONTEXT: dict[str, frozenset[str]] = {}
_EVENT_EFFECT_PLANNERS: dict[str, Callable[[ActionRequest, "EventLog"], list[PendingEffect]]] = {}
DEFAULT_CAST_SECONDS = 6
SKILL_TIME_OVERRIDES: dict[str, int] = {}


def register_event_effect_planner(
    name: str,
    planner: Callable[[ActionRequest, "EventLog"], list[PendingEffect]],
) -> None:
    """Register or replace one event-effect planner by name (idempotent).

    Planners derive additional ``PendingEffect`` values from a completed
    ``EventLog``; they never write while planning. Re-registering the same name
    replaces the earlier planner rather than duplicating progress on every
    server start.
    """
    _EVENT_EFFECT_PLANNERS[name] = planner


def register_effect_handler(
    prefix: str,
    handler: EffectHandler,
    surfaces: frozenset[str],
    requires_event_context: frozenset[str],
) -> None:
    """Register an effect prefix only when all mutations are restorable.

    ``requires_event_context`` SHALL name every ``event_context`` key the
    handler needs to resolve; an explicit (possibly empty) frozenset is
    required so no handler can silently skip the contract. Preflight and
    preview reject an action whose session context cannot supply every
    declared key, before any round cost.
    """
    unsupported = surfaces - SNAPSHOTTED_SURFACES
    if unsupported:
        raise UnsnapshottedSurfaceError(
            f"{prefix!r} declares unsupported surfaces {sorted(unsupported)}"
        )
    _EFFECT_HANDLERS[prefix] = handler
    _EFFECT_HANDLER_SURFACES[prefix] = surfaces
    _EFFECT_HANDLER_REQUIRED_CONTEXT[prefix] = frozenset(requires_event_context)


def _entity_key(entity: Any) -> str:
    return str(entity.key)


def _event_context(request: ActionRequest) -> dict[str, Any]:
    return getattr(request.context, "event_context", {})


def _effect_prefix(effect_id: str) -> str:
    return effect_id.partition(":")[0]


def parse_effect_key(effect_id: str) -> str:
    """Return the definition key after the ``<prefix>:`` channel of an effect id.

    The buff handlers reject a missing channel so a hand-written effect string
    cannot silently stage against no definition.
    """
    try:
        return effect_id.split(":", 1)[1]
    except IndexError as error:
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            effect_id,
        ) from error
