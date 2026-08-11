"""Deterministic verifier-and-applier for NPC dialogue intents (design §7.4).

This module is the deterministic engine's side of the dialogue contract: it
verifies an extracted ``intent`` against the world before applying it and
discards illegal or unverifiable intents while the speech is kept. It performs
verification and application only through existing deterministic APIs -- the
guild-exam trigger, the inventory-planning boundary, the sole-writer affinity
API, the party-membership module, the guild-offer surface, and the lore codex
sole writer.

Single-writer invariant: this module is part of the deterministic core and the
sole writer of any state this change causes; the generative reply layer never
imports this module or applies a state change itself.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from django.db import transaction

from world.rules.affinity import apply_affinity_change
from world.rules.equipment import InventoryError, plan_inventory_delta
from world.rules.guild_exams import GuildExamError, start_guild_exam
from world.rules.npc_schedules import interaction_reason
from world.rules.surfaces import (
    attribute_snapshot,
    restore_attribute_best_effort,
    restore_traits,
    snapshot_traits,
)

# No intent kind is forward-declared anymore: every whitelisted kind has a
# deterministic capability surface.
_FORWARD_DECLARED_KINDS: tuple[str, ...] = ()

_INVENTORY_SURFACE_KEYS = ("inventory", "quest_log")

_MAX_RELATION_DELTA = 10

_MAX_INTENT_KEY_LENGTH = 64

# Stable completion-gate marker (audit F22): an async exchange settled after
# the pair separated or the NPC stopped allowing ``talk``. The intent is
# skipped and callers surface ``STALE_CONTEXT_NOTE`` instead of applying
# anything; ``is_stale_context`` recognizes the outcome.
STALE_CONTEXT_REASON = "stale_context"

# Player-facing note appended by the dialogue seams when the completion gate
# fails; Traditional Chinese is the canonical game prose.
STALE_CONTEXT_NOTE = "對方已經離開／現在無法交談。"


@dataclass(frozen=True)
class IntentOutcome:
    """The deterministic result of attempting to apply one NPC intent.

    ``delta_used`` reports the actually applied affinity amount and is only
    filled by the ``adjust_relation`` path: a partial application reports
    ``applied=True`` with the applied amount, while a fully blocked or
    rejected delta reports ``applied=False`` with ``delta_used`` 0.
    """

    applied: bool
    reason: str | None = None
    delta_used: int | None = None


def intent_context_ok(npc: Any, player: Any) -> bool:
    """The canonical completion gate: co-location and talk-interactability.

    Returns ``True`` only while the pair is still in the same room and
    ``interaction_reason(npc, "talk")`` is ``None``. Evaluated at intent
    application time, so an async exchange that settled after the player or
    the NPC left the room, or after a schedule-driven move put the NPC into a
    ``busy``/``resting`` state, reads canonical state and fails the gate
    (audit F22).
    """
    if interaction_reason(npc, "talk") is not None:
        return False
    npc_location = getattr(npc, "location", None)
    player_location = getattr(player, "location", None)
    return npc_location is not None and npc_location is player_location


def is_stale_context(outcome: Any) -> bool:
    """True when an outcome is the completion gate's stale marker.

    The gate returns a plain :class:`IntentOutcome` (``applied=False`` with
    ``STALE_CONTEXT_REASON``); the helper also tolerates a ``None`` result
    (a blocked or degraded seam) so callers can classify a settled exchange
    without a kind check.
    """
    return (
        isinstance(outcome, IntentOutcome)
        and outcome.applied is False
        and outcome.reason == STALE_CONTEXT_REASON
    )


def apply_npc_intent(
    npc: Any,
    player: Any,
    intent: Any,
    *,
    context_ok: Callable[[Any, Any], bool] = intent_context_ok,
) -> IntentOutcome:
    """Verify then apply one extracted NPC intent through deterministic APIs.

    ``npc`` is the speaking NPC and ``player`` is the speaking player. The
    completion gate runs first: ``context_ok`` is evaluated against the
    **current** canonical state (co-location plus ``interaction_reason(npc,
    "talk")`` by default); a ``False`` result means the exchange's context
    went stale while the reply was in flight, so the intent is skipped with
    the stable ``STALE_CONTEXT_REASON`` outcome (recognizable via
    :func:`is_stale_context`) and the caller surfaces ``STALE_CONTEXT_NOTE``
    instead of applying anything. Per-kind domain checks stay untouched below
    the gate, so e.g. ``party_invite`` still runs ``join_party``'s own
    rechecks when the gate passes. The intent's kind is whitelisted upstream;
    here every kind is re-verified against the deterministic world. ``none``
    is an applied no-op. Illegal, unverifiable, or forward-declared intents
    return ``applied=False`` with a documented reason and change no state; the
    caller keeps the speech.
    """
    if not context_ok(npc, player):
        return IntentOutcome(False, STALE_CONTEXT_REASON)
    if not isinstance(intent, dict):
        return IntentOutcome(False, "intent is not a mapping")
    kind = intent.get("kind")
    if kind == "none":
        return IntentOutcome(True)
    if kind == "request_guild_exam":
        return _apply_guild_exam(npc, player, intent)
    if kind == "adjust_relation":
        return _apply_adjust_relation(npc, player, intent)
    if kind == "party_invite":
        return _apply_party_invite(npc, player, intent)
    if kind == "offer_quest":
        return _apply_offer_quest(npc, player, intent)
    if kind == "reveal_lore":
        return _apply_reveal_lore(npc, player, intent)
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


def _apply_adjust_relation(npc: Any, player: Any, intent: dict[str, Any]) -> IntentOutcome:
    payload = _payload_without_kind(intent)
    if set(payload) != {"delta"}:
        return IntentOutcome(False, "adjust_relation must carry exactly delta", delta_used=0)
    delta = payload["delta"]
    if (
        isinstance(delta, bool)
        or not isinstance(delta, int)
        or not (0 <= delta <= _MAX_RELATION_DELTA)
    ):
        return IntentOutcome(
            False,
            f"adjust_relation delta must be an integer in 0..{_MAX_RELATION_DELTA}",
            delta_used=0,
        )
    if delta == 0:
        # A zero delta is a rejected intent: skip the writer entirely so no
        # record is ever materialized (e.g. by the writer's lazy day-tick
        # reset) and no affinity state changes.
        return IntentOutcome(False, "affinity delta applied nothing", delta_used=0)
    outcome = apply_affinity_change(npc, player, "ai_dialogue", delta)
    if outcome.delta_used > 0:
        return IntentOutcome(True, delta_used=outcome.delta_used)
    if outcome.source_rejected:
        return IntentOutcome(
            False, "affinity write rejected the NPC or source", delta_used=0
        )
    if outcome.budget_capped:
        return IntentOutcome(False, "affinity daily budget exhausted", delta_used=0)
    return IntentOutcome(False, "affinity delta applied nothing", delta_used=0)


def _apply_party_invite(npc: Any, player: Any, intent: dict[str, Any]) -> IntentOutcome:
    """Route a ``party_invite`` intent through the party-membership module.

    ``accept: false`` is an applied no-op; ``accept: true`` delegates to
    ``join_party``, which rechecks the target, co-location, the absence of an
    existing binding, and the 4-companion bound. A join-gate rejection
    discards only the intent with the stable reason surfaced in
    ``IntentOutcome.reason`` so callers can render distinct feedback.
    """
    payload = _payload_without_kind(intent)
    if set(payload) != {"accept"}:
        return IntentOutcome(False, "party_invite must carry exactly accept")
    accept = payload["accept"]
    if not isinstance(accept, bool):
        return IntentOutcome(False, "party_invite accept must be a boolean")
    if not accept:
        return IntentOutcome(True, "party invite declined")
    from world.rules.party import PartyJoinError, join_party

    try:
        join_party(npc, player)
    except PartyJoinError as error:
        return IntentOutcome(False, error.reason)
    return IntentOutcome(True, "party joined")


def _apply_offer_quest(npc: Any, player: Any, intent: dict[str, Any]) -> IntentOutcome:
    """Assign a registered guild offer through the guild-offer surface.

    Payload is exactly ``{"quest_key": str}``. Verification order: the
    speaking NPC carries ``GuildStaff`` with a ``branch_key``; a
    ``GuildQuestOffer`` for ``quest_key`` is registered at that branch; and
    the player is a registered member whose canonical rank is within the
    offer's quest rank band (the same canonical eligibility ``list_guild_offers``
    applies, including the unregistered and rankless rejection paths).
    Duplicate-quest rejection is delegated to the quest runtime inside the
    atomic acceptance, whose quest-log and relations surfaces are restored on
    any failure -- a dialogue-assigned quest is economically and statefully
    identical to a board-accepted one.
    """
    payload = _payload_without_kind(intent)
    if set(payload) != {"quest_key"}:
        return IntentOutcome(False, "offer_quest must carry exactly quest_key")
    quest_key = payload["quest_key"]
    if not isinstance(quest_key, str) or not quest_key.strip():
        return IntentOutcome(False, "offer_quest quest_key must be a non-empty string")
    if len(quest_key) > _MAX_INTENT_KEY_LENGTH:
        return IntentOutcome(
            False,
            f"offer_quest quest_key must be at most {_MAX_INTENT_KEY_LENGTH} code points",
        )

    from typeclasses.components import GuildStaff
    from typeclasses.npcs import NPC

    if not isinstance(npc, NPC):
        return IntentOutcome(False, "offer_quest requires an NPC speaker")
    if not hasattr(npc, "components") or not npc.components.has(GuildStaff.name):
        return IntentOutcome(False, "offer_quest requires a GuildStaff speaker")
    guild_staff = npc.components.get(GuildStaff.get_component_slot())
    branch_key = guild_staff.branch_key
    if not isinstance(branch_key, str) or not branch_key:
        return IntentOutcome(False, "offer_quest requires a GuildStaff branch_key")

    from world.rules.guild import GuildDataError
    from world.rules.guild_offers import (
        BoardAccessError,
        GuildOfferNotFound,
        get_guild_offer,
        list_guild_offers,
    )

    try:
        get_guild_offer(quest_key, branch_key)
    except GuildOfferNotFound:
        return IntentOutcome(False, f"no guild offer {quest_key!r} at this branch")
    try:
        eligible = list_guild_offers(player, npc)
    except (BoardAccessError, GuildDataError) as error:
        return IntentOutcome(False, _reason_text(error))
    if not any(offer.definition_key == quest_key for offer in eligible):
        return IntentOutcome(False, f"quest {quest_key!r} is not rank-eligible")

    from world.quests.runtime import accept_quest
    from world.rules.affinity import AffinitySource

    quest_log_snapshot = attribute_snapshot(player, "quest_log")
    relations_snapshot = attribute_snapshot(npc, "relations_data")
    affinity_capped = False
    try:
        with transaction.atomic():
            accept_quest(player, quest_key)
            outcome = apply_affinity_change(npc, player, AffinitySource.GUILD, 1)
            if outcome.source_rejected:
                # Defensive: the verified NPC and GUILD source cannot be
                # rejected today; a future writer change must not turn a
                # rejection into a silently misreported "capped" quest.
                raise RuntimeError("affinity writer rejected the guild source")
            affinity_capped = outcome.delta_used == 0
    except Exception:
        restore_attribute_best_effort(player, "quest_log", quest_log_snapshot)
        restore_attribute_best_effort(npc, "relations_data", relations_snapshot)
        return IntentOutcome(False, "quest assignment failed and was rolled back")
    if affinity_capped:
        return IntentOutcome(True, "quest assigned; affinity credit capped")
    return IntentOutcome(True, "quest assigned")


def _apply_reveal_lore(npc: Any, player: Any, intent: dict[str, Any]) -> IntentOutcome:
    """Record one discovered lore entry through the codex sole writer.

    Payload is exactly ``{"category": str, "key": str}`` (bounded). The
    category must be in the codex's closed mapping and the key must resolve
    in that category's registry; the reveal then records the namespaced
    entry through ``record_lore_reveal`` and grants no affinity -- the speech
    is the reward. A repeat reveal is an applied no-op. Any payload,
    verification, or record failure discards only the intent.
    """
    payload = _payload_without_kind(intent)
    if set(payload) != {"category", "key"}:
        return IntentOutcome(False, "reveal_lore must carry exactly category and key")
    category = payload["category"]
    key = payload["key"]
    if not isinstance(category, str) or not category.strip():
        return IntentOutcome(False, "reveal_lore category must be a non-empty string")
    if not isinstance(key, str) or not key.strip():
        return IntentOutcome(False, "reveal_lore key must be a non-empty string")
    if len(category) > _MAX_INTENT_KEY_LENGTH or len(key) > _MAX_INTENT_KEY_LENGTH:
        return IntentOutcome(
            False,
            f"reveal_lore category and key must be at most "
            f"{_MAX_INTENT_KEY_LENGTH} code points",
        )

    from world.rules.lore_knowledge import (
        LoreCategoryError,
        LoreKeyError,
        LoreRecordError,
        record_lore_reveal,
    )

    try:
        record_lore_reveal(player, category, key)
    except (LoreCategoryError, LoreKeyError, LoreRecordError) as error:
        return IntentOutcome(False, _reason_text(error))
    except Exception:
        # Defensive: a genuine persistence failure must never bubble out of
        # the dialogue path -- it discards only the intent, keeps the speech,
        # and reports a safe diagnostic.
        return IntentOutcome(False, "lore reveal failed and was discarded")
    return IntentOutcome(True, "lore entry revealed")


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


def _reason_text(error: Exception) -> str:
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
