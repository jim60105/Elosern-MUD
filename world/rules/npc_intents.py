"""Deterministic verifier-and-applier for NPC dialogue intents (design §7.4).

This module is the deterministic engine's side of the dialogue contract: it
verifies an extracted ``intent`` against the world before applying it and
discards illegal or unverifiable intents while the speech is kept. It performs
verification and application only through existing deterministic APIs -- the
guild-exam trigger and the inventory-planning boundary -- and never constructs
or mutates state itself. ``offer_quest``, ``adjust_relation``, and
``reveal_lore`` are whitelisted by the schema but rejected here behind
forward-declared seams until their deterministic capability surfaces exist.

Single-writer invariant: this module is part of the deterministic core and the
sole writer of any state this change causes; the generative reply layer never
imports this module or applies a state change itself.
"""

from dataclasses import dataclass
from typing import Any

from django.db import transaction

from world.rules.equipment import InventoryError, plan_inventory_delta
from world.rules.guild_exams import GuildExamError, start_guild_exam
from world.rules.surfaces import (
    attribute_snapshot,
    restore_attribute_best_effort,
    restore_traits,
    snapshot_traits,
)

_FORWARD_DECLARED_KINDS = ("offer_quest", "adjust_relation", "reveal_lore")

_INVENTORY_SURFACE_KEYS = ("inventory", "quest_log")


@dataclass(frozen=True)
class IntentOutcome:
    """The deterministic result of attempting to apply one NPC intent."""

    applied: bool
    reason: str | None = None


def apply_npc_intent(npc: Any, player: Any, intent: Any) -> IntentOutcome:
    """Verify then apply one extracted NPC intent through deterministic APIs.

    ``npc`` is the speaking NPC and ``player`` is the speaking player. The
    intent's kind is whitelisted upstream; here every kind is re-verified
    against the deterministic world. ``none`` is an applied no-op. Illegal,
    unverifiable, or forward-declared intents return ``applied=False`` with a
    documented reason and change no state; the caller keeps the speech.
    """
    if not isinstance(intent, dict):
        return IntentOutcome(False, "intent is not a mapping")
    kind = intent.get("kind")
    if kind == "none":
        return IntentOutcome(True)
    if kind == "request_guild_exam":
        return _apply_guild_exam(npc, player, intent)
    if kind in ("give_item", "take_item"):
        return _apply_item_transfer(kind, npc, player, intent)
    if kind in _FORWARD_DECLARED_KINDS:
        return IntentOutcome(
            False,
            f"{kind} is whitelisted but has no deterministic capability surface yet",
        )
    return IntentOutcome(False, f"unknown intent kind {kind!r}")


def _payload_without_kind(intent: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in intent.items() if key != "kind"}


def _apply_guild_exam(npc: Any, player: Any, intent: dict[str, Any]) -> IntentOutcome:
    payload = _payload_without_kind(intent)
    if set(payload) != {"target_rank"}:
        return IntentOutcome(False, "request_guild_exam must carry exactly target_rank")
    target_rank = payload["target_rank"]
    if not isinstance(target_rank, str) or not target_rank.strip():
        return IntentOutcome(False, "request_guild_exam target_rank must be a non-empty string")
    try:
        start_guild_exam(
            actor=player,
            examiner=npc,
            target_rank=target_rank,
            requested_by="npc_intent",
        )
    except GuildExamError as error:
        return IntentOutcome(False, _reason_text(error))
    return IntentOutcome(True)


def _reason_text(error: GuildExamError) -> str:
    if error.args:
        first = error.args[0]
        if isinstance(first, str):
            return first
        return str(first)
    return str(error)


def _apply_item_transfer(
    kind: str, npc: Any, player: Any, intent: dict[str, Any]
) -> IntentOutcome:
    payload = _payload_without_kind(intent)
    if set(payload) != {"item_key", "qty"}:
        return IntentOutcome(False, f"{kind} must carry exactly item_key and qty")
    item_key = payload["item_key"]
    qty = payload["qty"]
    if not isinstance(item_key, str) or not item_key.strip():
        return IntentOutcome(False, f"{kind} item_key must be a non-empty string")
    if isinstance(qty, bool) or not isinstance(qty, int) or qty < 1:
        return IntentOutcome(False, f"{kind} qty must be a positive integer")
    if kind == "give_item":
        return _transfer_items(giver=npc, receiver=player, item_key=item_key, qty=qty)
    return _transfer_items(giver=player, receiver=npc, item_key=item_key, qty=qty)


def _transfer_items(
    giver: Any, receiver: Any, item_key: str, qty: int
) -> IntentOutcome:
    """Transfer verified holdings between two entities atomically.

    Verifies the giver's ``db.inventory`` actually holds ``item_key`` × ``qty``
    *before* constructing the removal tuple (so a pathological ``qty`` can never
    allocate an unbounded tuple), precomputes both inventory plans, snapshots
    both entities' affected surfaces (inventory, quest log, traits, and the
    receiver's ACQUIRE pin state), applies both plans inside one outer
    transaction, and restores both entities' in-process caches on any failure so
    no partial transfer is observable.
    """
    holdings = giver.db.inventory or []
    if holdings.count(item_key) < qty:
        return IntentOutcome(False, f"giver does not hold {qty}x {item_key}")
    removals = (item_key,) * qty
    try:
        removal_plan = plan_inventory_delta(giver, removals=removals)
        addition_plan = plan_inventory_delta(receiver, additions=removals)
    except InventoryError as error:
        return IntentOutcome(False, str(error))

    giver_surfaces = _surface_snapshots(giver)
    receiver_surfaces = _surface_snapshots(receiver)
    pin_snapshots = _pin_snapshots(addition_plan)
    try:
        with transaction.atomic():
            _apply_plan(removal_plan)
            _apply_plan(addition_plan)
    except Exception:
        _restore_surface_snapshots(giver, giver_surfaces)
        _restore_surface_snapshots(receiver, receiver_surfaces)
        _restore_pin_snapshots(pin_snapshots)
        return IntentOutcome(False, "item transfer failed and was rolled back")
    return IntentOutcome(True)


def _apply_plan(plan: Any) -> None:
    """Commit one inventory plan's writes inside the caller's transaction.

    Mirrors ``apply_inventory_plan``'s inner writer without its own nested
    transaction or snapshot: the transfer primitive owns the outer transaction
    and the dual-entity snapshot/restore.
    """
    entity = plan.entity
    entity.db.inventory = list(plan.after)
    if plan.acquire is not None:
        from world.quests.transitions import apply_quest_log_delta

        apply_quest_log_delta(entity, list(plan.acquire[0]), plan.acquire[1])


def _surface_snapshots(entity: Any) -> dict[str, Any]:
    return {
        key: attribute_snapshot(entity, key)
        for key in _INVENTORY_SURFACE_KEYS
    } | {"traits": snapshot_traits(entity)}


def _restore_surface_snapshots(entity: Any, snapshots: dict[str, Any]) -> None:
    for key in _INVENTORY_SURFACE_KEYS:
        restore_attribute_best_effort(entity, key, snapshots[key])
    restore_traits(entity, snapshots["traits"])


def _pin_snapshots(plan: Any) -> list[tuple[Any, Any]]:
    from world.quests.transitions import snapshot_pin_reasons

    pins = plan.acquire[1] if plan.acquire is not None else ()
    return [(room, snapshot_pin_reasons(room)) for room, _, _ in pins]


def _restore_pin_snapshots(snapshots: list[tuple[Any, Any]]) -> None:
    from world.quests.transitions import restore_pin_reasons

    for room, snapshot in snapshots:
        restore_pin_reasons(room, snapshot)
