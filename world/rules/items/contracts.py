"""Item-use contracts: the closed vocabulary and frozen settlement dataclasses.

Part of the ``world.rules.items`` package (split out of the historical single
module): the named rejection reasons and the request/step/plan/preflight
dataclasses the side-effect-free preflight computes, plus the result and
settlement shapes the public facades return. Pure data — no writer reaches
into any other package module from here.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal

from world.rules.clock import ScheduledEvent
from world.rules.event_log import EventLog
from world.rules.item_effects import ItemEffect
from world.rules.items.journal import ItemTouchedJournal


class ItemUseError(ValueError):
    """An item-use settlement failed mid-application and was rolled back."""


class ItemUseReason(StrEnum):
    """Stable named rejection reasons for item-use preflight and settlement."""

    UNKNOWN_ITEM = "unknown_item"
    NOT_USABLE = "not_usable"
    ITEM_NOT_HELD = "item_not_held"
    HP_FULL = "hp_full"
    MP_FULL = "mp_full"
    NOT_ALIVE = "not_alive"
    NO_DEBUFFS = "no_debuffs"
    COMBAT_NOT_ALLOWED = "combat_not_allowed"
    UNKNOWN_EFFECT = "unknown_effect"
    ACTIVE_SESSION = "active_combat"
    MALFORMED_TRAITS = "malformed_traits"
    MALFORMED_INVENTORY = "malformed_inventory"
    SP_FULL = "sp_full"
    PLEASURE_FULL = "pleasure_full"
    NO_EFFECT = "no_effect"
    STATUS_BLOCKED = "status_blocked"
    NOTHING_TO_REMOVE = "nothing_to_remove"
    NO_TARGET = "no_target"
    TARGET_INVALID = "target_invalid"


@dataclass(frozen=True)
class ItemUseRequest:
    """The closed deterministic request to use one held item.

    ``target`` is the caller's single explicit choice for the whole use —
    consumed only by ``single``-scoped effects, never a sequence and never a
    group shorthand (design D1): an item's reach is fixed by the rulebook, so
    a list or shorthand would let the caller widen a single-scope item into
    an area item. Two single-scope effects share the one supplied target.
    """

    actor: Any
    item_key: str
    target: Any | None = None


@dataclass(frozen=True)
class ItemEffectStep:
    """One planned effect execution: what to run, on whom, with what payload.

    ``amount`` is the signed gauge delta actually applicable to the target's
    current state (never the configured magnitude) and is ``0`` for status
    steps. ``status_keys`` names the concrete status keys a status step
    touches — the applied key for an apply, the matched definition keys for
    a removal — and is empty for gauge steps.
    """

    effect: ItemEffect
    target: Any
    amount: int = 0
    status_keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class ItemUsePlan:
    """The complete, immutable settlement computed by a side-effect-free preflight.

    ``steps`` holds one step per EFFECTIVE declared effect in profile order
    (design §5.1); an item whose every effect is ineligible never produces a
    plan. ``mirror_pk`` is the single existing contained-object mirror
    selected for consumption (``None`` for a key-only holding), never a
    fabricated object.
    """

    actor: Any
    item_key: str
    consumable: bool
    steps: tuple[ItemEffectStep, ...]
    mirror_pk: int | None


@dataclass(frozen=True)
class ItemUsePreflight:
    """The outcome of one side-effect-free eligibility check."""

    allowed: bool
    reason: ItemUseReason | None = None
    detail: str | None = None
    plan: ItemUsePlan | None = None


@dataclass(frozen=True)
class ItemUseResult:
    """The result of one item-use resolution, shaped for round settlement."""

    outcome: Literal["success", "rejected"]
    event_log: EventLog | None = None
    time_cost_seconds: int = 0
    reason: ItemUseReason | None = None
    detail: str | None = None
    journal: ItemTouchedJournal | None = None


@dataclass(frozen=True)
class ItemUseSettlement:
    """The committed out-of-combat item use and its clock events."""

    result: ItemUseResult
    events: tuple[ScheduledEvent, ...] = ()
