"""Exact service action payload validators and narrow adapters.

The seven production service actions are ``guild.register``,
``guild.quest_accept``, ``guild.quest_abandon``, ``guild.quest_turnin``,
``guild.exam_request``, ``shop.buy``, and ``shop.sell``. Each validator enforces
an exact bounded payload shape; each adapter re-resolves the local
``GuildStaff`` / ``Merchant`` host (the exam request re-resolves its counter
and qualified host through the shared request coordinator) and every referenced
identity against current canonical state, calls only the listed public
deterministic APIs, and never assigns ``.db`` attributes, traits, registration,
rank, merit, quest log, wallet, inventory, merchant stock, or location
directly. No payload accepts an actor, host, branch, session, price, stock, or
wallet field; a party member reference appears only in the exact member field
its owning capability defines (``inventory.use`` and
``inventory.toggle_equip`` ``actor_id``, ``shop.buy`` ``recipient_id``,
``shop.sell`` ``seller_id``), and no action routes through the text command
parser.
"""

from typing import Any

from typeclasses.components import GuildStaff, Merchant
from web.webclient.presentation.protocol import MAX_SAFE_INTEGER
from world.quests.runtime import (
    QuestAlreadyActive,
    QuestDataError,
    QuestNotFound,
    QuestTargetsUnavailable,
    QuestTransitionError,
    set_quest_tracked,
)
from world.rules.combat_session import SessionReason
from world.rules.economy import TradeError, buy, sell
from world.rules.equipment_effects import toggle_equipment_message
from world.rules.event_log import render_plain_text
from world.rules.guild import (
    GuildDataError,
    GuildError,
    GuildServiceError,
    RewardClaimError,
    register_adventurer,
    resolve_local_service_host,
    turn_in_quest,
)
from world.rules.guild_exam_request import OUTCOME_SCHEDULE, request_guild_exam
from world.rules.guild_exams import GuildExamError
from world.rules.guild_offers import (
    BoardAccessError,
    GuildOfferError,
    accept_guild_offer,
    abandon_guild_quest,
)
from world.rules.npc_identity import npc_display_name
from world.rules.npc_schedules import interaction_reason
from world.rules.party_inventory import toggle_member_equipment, use_member_item
from world.rules.party_scope import (
    PURPOSE_ACT,
    PartyScopeError,
    authorize_member,
    party_in_combat,
    resolve_commander,
)
from world.rules.player_messages import session_reason_message
from world.rules.service_messages import (
    exam_schedule_message,
    exam_started_message,
    rejection_code,
    rejection_message,
)

# Wire limits (equal to or below the protocol identifier bound).
MAX_KEY_CODE_POINTS = 64
MAX_RANK_KEY_CODE_POINTS = 8
MAX_QUANTITY = 1000
MIN_QUANTITY = 1

# Stable panels each admitted service action may publish. Every quest write
# seam publishes the ``objectives`` panel beside its paired ``services`` rows
# (webclient-align-06: the tracker island must never lag the quest log).
AFFECTED_REGISTER = ("status", "services")
AFFECTED_ACCEPT = ("services", "objectives", "quest_log")
AFFECTED_ABANDON = ("services", "objectives", "quest_log")
AFFECTED_TURNIN = ("status", "services", "objectives", "quest_log")
AFFECTED_EXAM = ("status", "services", "context_actions")
# Planned attendance writes nothing; republishing the unchanged services
# panel settles the request without a full snapshot.
AFFECTED_EXAM_SCHEDULE = ("services",)
AFFECTED_TRADE = ("status", "services", "objectives", "quest_log")
AFFECTED_TRACK = ("services", "objectives", "quest_log")


class ServiceActionError(ValueError):
    """A service action payload violates its exact bounded schema."""


def _require_non_empty_string(value: Any, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ServiceActionError(f"{field} must be a non-empty string")
    if sum(1 for _ in value) > maximum:
        raise ServiceActionError(f"{field} exceeds its bound")
    return value


def _require_quantity(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ServiceActionError("quantity must be an integer")
    if not MIN_QUANTITY <= value <= MAX_QUANTITY:
        raise ServiceActionError(f"quantity must be within {MIN_QUANTITY}..{MAX_QUANTITY}")
    return value


def _exact_single_field(payload: dict[str, Any], field: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ServiceActionError("payload must be an object")
    unknown = set(payload) - {field}
    if unknown:
        raise ServiceActionError(f"payload has unknown fields {sorted(unknown)}")
    if field not in payload:
        raise ServiceActionError(f"payload requires {field}")
    return payload


def validate_guild_register_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact empty ``guild.register`` payload."""
    if not isinstance(payload, dict):
        raise ServiceActionError("guild.register payload must be an object")
    if payload:
        raise ServiceActionError("guild.register requires an empty payload")
    return {}


def validate_quest_accept_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``guild.quest_accept`` payload (one definition key)."""
    body = _exact_single_field(payload, "definition_key")
    return {"definition_key": _require_non_empty_string(
        body["definition_key"], "definition_key", MAX_KEY_CODE_POINTS
    )}


def validate_quest_abandon_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``guild.quest_abandon`` payload (one quest ID)."""
    body = _exact_single_field(payload, "quest_id")
    return {"quest_id": _require_non_empty_string(
        body["quest_id"], "quest_id", MAX_KEY_CODE_POINTS
    )}


def validate_quest_turnin_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``guild.quest_turnin`` payload (one quest ID)."""
    body = _exact_single_field(payload, "quest_id")
    return {"quest_id": _require_non_empty_string(
        body["quest_id"], "quest_id", MAX_KEY_CODE_POINTS
    )}


def validate_quest_track_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``guild.quest_track`` payload (quest ID plus flag)."""
    if not isinstance(payload, dict):
        raise ServiceActionError("payload must be an object")
    if set(payload) != {"quest_id", "tracked"}:
        raise ServiceActionError("guild.quest_track accepts exactly quest_id and tracked")
    quest_id = _require_non_empty_string(payload["quest_id"], "quest_id", MAX_KEY_CODE_POINTS)
    tracked = payload["tracked"]
    if not isinstance(tracked, bool):
        raise ServiceActionError("tracked must be a boolean")
    return {"quest_id": quest_id, "tracked": tracked}


def validate_exam_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``guild.exam_request`` payload (one next-rank key).

    Host, branch, clock and threshold fields are unknown fields and reject
    here, before the request coordinator runs.
    """
    body = _exact_single_field(payload, "target_rank")
    return {"target_rank": _require_non_empty_string(
        body["target_rank"], "target_rank", MAX_RANK_KEY_CODE_POINTS
    )}


def _validate_trade_payload(
    payload: dict[str, Any], action_id: str, member_field: str
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ServiceActionError(f"{action_id} payload must be an object")
    if set(payload) != {"item_key", "quantity", member_field}:
        raise ServiceActionError(
            f"{action_id} requires exactly item_key, quantity and {member_field}"
        )
    return {
        "item_key": _require_non_empty_string(
            payload["item_key"], "item_key", MAX_KEY_CODE_POINTS
        ),
        "quantity": _require_quantity(payload["quantity"]),
        member_field: _require_member_identifier(
            payload[member_field], member_field
        ),
    }


def validate_buy_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``shop.buy`` payload (item, quantity, recipient)."""
    return _validate_trade_payload(payload, "shop.buy", "recipient_id")


def validate_sell_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``shop.sell`` payload (item, quantity, seller)."""
    return _validate_trade_payload(payload, "shop.sell", "seller_id")


def _require_key_identifier(value: Any, field: str, maximum: int) -> str:
    """Require a whitespace-free bounded key.

    The typed `使用`/`use` command takes its key as the first
    whitespace-delimited token and `裝備`/`equip` resolves its whole item
    argument as a registry key or a held display name, while the browser's
    input echo prints the key verbatim — a whitespace-bearing key would echo a
    line whose keyboard replay resolves a DIFFERENT item. Reject at the action
    boundary instead (complete-ui-command-echo D1).
    """
    text = _require_non_empty_string(value, field, maximum)
    if any(character.isspace() for character in text):
        raise ServiceActionError(f"{field} must not contain whitespace")
    return text


def _require_member_identifier(value: Any, field: str = "actor_id") -> int:
    """Require one positive safe integer member identity.

    A bool is an int subclass, so it is excluded explicitly; a string, float,
    zero, negative, or out-of-range identity never reaches the party boundary.
    """
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= MAX_SAFE_INTEGER
    ):
        raise ServiceActionError(f"{field} must be a positive safe integer")
    return value


def validate_inventory_use_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``inventory.use`` payload (member, key, target).

    Accepted forms are exactly ``{actor_id, item_key}`` or
    ``{actor_id, item_key, target_key}``. ``actor_id`` names the member who
    uses the item from that member's own bag (reauthorized for the acting
    purpose in the adapter) and is never replaced by the commander.
    ``target_key`` names *whom* an effect reaches and never *what* the item
    does (add-item-effect-targeting): it is consumed only by an effect the
    rulebook already scoped to a single entity, and a token the adapter
    cannot resolve to a present entity — a group shorthand included — is the
    deterministic preflight's fail-closed rejection, never a silently
    ignored reach.
    """
    if not isinstance(payload, dict):
        raise ServiceActionError("payload must be an object")
    unknown = set(payload) - {"actor_id", "item_key", "target_key"}
    if unknown:
        raise ServiceActionError(f"payload has unknown fields {sorted(unknown)}")
    missing = {"actor_id", "item_key"} - set(payload)
    if missing:
        raise ServiceActionError(f"payload requires {sorted(missing)}")
    validated = {
        "actor_id": _require_member_identifier(payload["actor_id"]),
        "item_key": _require_key_identifier(
            payload["item_key"], "item_key", MAX_KEY_CODE_POINTS
        ),
    }
    if "target_key" in payload:
        validated["target_key"] = _require_key_identifier(
            payload["target_key"], "target_key", MAX_KEY_CODE_POINTS
        )
    return validated


def validate_inventory_toggle_equip_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``inventory.toggle_equip`` payload (member plus key).

    ``actor_id`` names the member whose equipment toggles and is reauthorized
    by the party member boundary in the adapter, never by the payload; the
    client still chooses no slot, effect, or quantity.
    """
    if not isinstance(payload, dict):
        raise ServiceActionError("payload must be an object")
    unknown = set(payload) - {"actor_id", "item_key"}
    if unknown:
        raise ServiceActionError(f"payload has unknown fields {sorted(unknown)}")
    missing = {"actor_id", "item_key"} - set(payload)
    if missing:
        raise ServiceActionError(f"payload requires {sorted(missing)}")
    return {
        "actor_id": _require_member_identifier(payload["actor_id"]),
        "item_key": _require_key_identifier(
            payload["item_key"], "item_key", MAX_KEY_CODE_POINTS
        ),
    }


# ---------------------------------------------------------------------------
# Adapter helpers.
# ---------------------------------------------------------------------------


def _resolve_local(actor: Any, component_class: type, absent: str, ambiguous: str):
    """Return ``(host, None)`` or ``(None, stable_reason)`` for one host class."""
    try:
        return resolve_local_service_host(actor, component_class), None
    except GuildServiceError as error:
        message = str(error.args[0]) if error.args else ""
        if message == "multiple local service hosts":
            return None, ambiguous
        return None, absent


def _rejected(reason: Any) -> dict[str, Any]:
    code = rejection_code(reason)
    return {"outcome": "rejected", "code": code, "message": rejection_message(reason)}


def _session_rejected(reason: Any) -> dict[str, Any]:
    code = str(reason)
    return {"outcome": "rejected", "code": code, "message": session_reason_message(code)}


def _schedule_rejected(host: Any, interaction_kind: str) -> dict[str, Any] | None:
    """Return the stable schedule-gate rejection for ``host``, or ``None``.

    Mirrors the Telnet surfaces: a schedule-blocked host (a busy or resting
    NPC) refuses the service with the gate's stable Traditional Chinese line
    under the stable ``schedule_blocked`` code, and no transaction occurs.
    """
    reason = interaction_reason(host, interaction_kind)
    if reason is None:
        return None
    return {"outcome": "rejected", "code": "schedule_blocked", "message": reason}


def _success(code: str, message: str, affected: tuple[str, ...]) -> dict[str, Any]:
    return {
        "outcome": "success",
        "code": code,
        "message": message,
        "affected_panels": affected,
    }


# ---------------------------------------------------------------------------
# Adapters.
# ---------------------------------------------------------------------------


def _guild_register_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Resolve the local staff host and register the actor at rank F."""
    del payload, session
    staff, reason = _resolve_local(actor, GuildStaff, "no_staff", "ambiguous_staff")
    if staff is None:
        return _rejected(reason)
    blocked = _schedule_rejected(staff, "service_guild")
    if blocked is not None:
        return blocked
    try:
        record = register_adventurer(actor, staff)
    except (GuildDataError, GuildError) as error:
        return _rejected(error)
    message = f"你已註冊為冒險者，階級 F。公會：{record['branch_key']}"
    actor.msg(message)
    for line in record.get("title_notifications", ()):
        actor.msg(line)
    return _success("registered", message, AFFECTED_REGISTER)


def _quest_accept_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Revalidate board eligibility and delegate acceptance to the quest runtime."""
    del session
    definition_key = payload["definition_key"]
    staff, reason = _resolve_local(actor, GuildStaff, "no_staff", "ambiguous_staff")
    if staff is None:
        return _rejected(reason)
    blocked = _schedule_rejected(staff, "service_guild")
    if blocked is not None:
        return blocked
    try:
        record = accept_guild_offer(actor, staff, definition_key)
    except (
        BoardAccessError,
        GuildOfferError,
        QuestDataError,
        QuestNotFound,
        QuestAlreadyActive,
        QuestTargetsUnavailable,
    ) as error:
        return _rejected(error)
    message = f"你接取了任務 {record.quest_id}。"
    actor.msg(message)
    return _success("accepted", message, AFFECTED_ACCEPT)


def _quest_abandon_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Delegate abandonment of the exact quest ID to the quest runtime."""
    del session
    quest_id = payload["quest_id"]
    staff, reason = _resolve_local(actor, GuildStaff, "no_staff", "ambiguous_staff")
    if staff is None:
        return _rejected(reason)
    blocked = _schedule_rejected(staff, "service_guild")
    if blocked is not None:
        return blocked
    try:
        record = abandon_guild_quest(actor, staff, quest_id)
    except (QuestNotFound, QuestDataError) as error:
        return _rejected(error)
    message = f"你放棄了任務 {record.quest_id}。"
    actor.msg(message)
    return _success("abandoned", message, AFFECTED_ABANDON)


def _quest_turnin_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Claim one completed quest reward exactly once through the local staff."""
    del session
    quest_id = payload["quest_id"]
    staff, reason = _resolve_local(actor, GuildStaff, "no_staff", "ambiguous_staff")
    if staff is None:
        return _rejected(reason)
    blocked = _schedule_rejected(staff, "service_guild")
    if blocked is not None:
        return blocked
    try:
        result = turn_in_quest(actor, staff, quest_id)
    except (RewardClaimError, GuildDataError, QuestDataError) as error:
        return _rejected(error)
    message = (
        f"你回報了任務 {result['quest_id']}，獲得 {result['copper']} 銅、"
        f"功績 {result['merit']} 與道具 {result['items']}。"
    )
    actor.msg(message)
    for line in result.get("title_notifications", ()):
        actor.msg(line)
    return _success("claimed", message, AFFECTED_TURNIN)


def _quest_track_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Flip the tracking flag on exactly one of the holder's own records.

    Host-independent by contract (webclient-align-06): tracking truth is
    player state, so NO staff host and NO schedule gate is consulted — the
    lifecycle operation itself is the only authority, and it validates the
    whole log before writing.
    """
    del session
    quest_id = payload["quest_id"]
    tracked = payload["tracked"]
    try:
        record = set_quest_tracked(actor, quest_id, tracked)
    except (QuestNotFound, QuestDataError, QuestTransitionError) as error:
        return _rejected(error)
    if tracked:
        message = f"你已開始追蹤任務 {record.quest_id}。"
    else:
        message = f"你已取消追蹤任務 {record.quest_id}。"
    actor.msg(message)
    return _success(
        "tracked" if tracked else "untracked", message, AFFECTED_TRACK
    )


def _exam_request_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Ask the shared coordinator for planned attendance or the exam start.

    The counter, branch, next-rank target and qualified persistent host are
    all derived server-side; merit and host presence never gate the request
    itself. ``exam_schedule`` is read-only planned information (no panel
    changes), ``exam_started`` hands the shell to combat.
    """
    del session
    target_rank = payload["target_rank"]
    try:
        outcome = request_guild_exam(actor, target_rank, requested_by="webclient")
    except GuildExamError as error:
        return _rejected(error)
    if outcome.kind == OUTCOME_SCHEDULE:
        message = exam_schedule_message(
            outcome.host_name, outcome.target_rank,
            outcome.interval.start_tick, outcome.interval.end_tick,
        )
        actor.msg(message)
        return _success("exam_schedule", message, AFFECTED_EXAM_SCHEDULE)
    message = exam_started_message(outcome.target_rank)
    actor.msg(message)
    return _success("exam_started", message, AFFECTED_EXAM)


def _buy_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Recheck the host, then buy for the named recipient from the party purse.

    The possessed refusal stays first. The recipient is reauthorized by the
    economy rule's party boundary (a forged, absent, or non-member id rejects
    with the shared party code and the commander never receives the goods in
    its place); the adapter itself never writes state.
    """
    del session
    from world.rules.possession import (
        POSSESSED_REFUSAL_MESSAGES,
        REASON_POSSESSED_SHOP,
        is_possessed_actor,
    )

    if is_possessed_actor(actor):
        return {
            "outcome": "rejected",
            "code": REASON_POSSESSED_SHOP,
            "message": POSSESSED_REFUSAL_MESSAGES[REASON_POSSESSED_SHOP],
        }
    item_key = payload["item_key"]
    quantity = payload["quantity"]
    merchant_host, reason = _resolve_local(
        actor, Merchant, "no_merchant", "ambiguous_merchant"
    )
    if merchant_host is None:
        return _rejected(reason)
    blocked = _schedule_rejected(merchant_host, "service_shop")
    if blocked is not None:
        return blocked
    try:
        result = buy(
            actor, merchant_host, item_key, quantity, payload["recipient_id"]
        )
    except PartyScopeError as error:
        return {
            "outcome": "rejected",
            "code": error.reason,
            "message": error.message,
        }
    except TradeError as error:
        return _rejected(error)
    message = (
        f"你買了 {result['quantity']} 個 {result['item_key']}，"
        f"花費 {result['total_copper']} 銅，剩餘 {result['wallet']} 銅。"
    )
    actor.msg(message)
    return _success("bought", message, AFFECTED_TRADE)


def _sell_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Recheck the host, then sell the named seller's unequipped items.

    The possessed refusal stays first. The seller is reauthorized by the
    economy rule's party boundary; the unchanged sell price is credited to
    the party purse, and the adapter itself never writes state.
    """
    del session
    from world.rules.possession import (
        POSSESSED_REFUSAL_MESSAGES,
        REASON_POSSESSED_SHOP,
        is_possessed_actor,
    )

    if is_possessed_actor(actor):
        return {
            "outcome": "rejected",
            "code": REASON_POSSESSED_SHOP,
            "message": POSSESSED_REFUSAL_MESSAGES[REASON_POSSESSED_SHOP],
        }
    item_key = payload["item_key"]
    quantity = payload["quantity"]
    merchant_host, reason = _resolve_local(
        actor, Merchant, "no_merchant", "ambiguous_merchant"
    )
    if merchant_host is None:
        return _rejected(reason)
    blocked = _schedule_rejected(merchant_host, "service_shop")
    if blocked is not None:
        return blocked
    try:
        result = sell(
            actor, merchant_host, item_key, quantity, payload["seller_id"]
        )
    except PartyScopeError as error:
        return {
            "outcome": "rejected",
            "code": error.reason,
            "message": error.message,
        }
    except TradeError as error:
        return _rejected(error)
    message = (
        f"你賣了 {result['quantity']} 個 {result['item_key']}，"
        f"獲得 {result['total_copper']} 銅，目前 {result['wallet']} 銅。"
    )
    actor.msg(message)
    return _success("sold", message, AFFECTED_TRADE)


def _resolve_inventory_target(actor: Any, target_key: str) -> Any:
    """Resolve one ``target_key`` to a present entity for item targeting.

    Only the exploration path reaches this helper: during an active combat
    session ``inventory.use`` rejects before any resolution, because a party
    session's item selections are actor-scoped draft entries saved through the
    guarded ``combat.command`` path. ``actor`` is the member who uses the item
    (never the commander behind it), so the world view is that member's
    current location's contents — the same room the party boundary already
    proved it shares with the commander. An unresolvable token — an unknown
    key or a group shorthand — travels on as the raw string, where the
    deterministic preflight's fail-closed target guard rejects it with the
    stable invalid-target reason: the client can never select a reach the
    rulebook did not grant.
    """
    location = getattr(actor, "location", None)
    if location is not None:
        for obj in location.contents:
            if getattr(obj, "key", None) == target_key:
                return obj
    return target_key


def _inventory_use_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Reauthorize one member and delegate its item use to the member rule.

    During an active combat session the request rejects before any member or
    target resolution: a party session's items are actor-scoped draft entries,
    so only the guarded ``combat.command`` path may save one member's item
    selection. In exploration ``actor_id`` is reauthorized for the acting
    purpose, so a forged, absent, or knocked-out member rejects with the shared
    party code and the authenticated actor is never used in its place; the item
    is then consumed from that member's own bag, SELF effects bind to it, and
    the canonical six-second cost settles the present party. Success always
    publishes a full snapshot (empty affected-panel set).

    An optional ``target_key`` names whom a single-scope effect reaches; it is
    resolved relative to the member's own room, never changes what the item
    does, and a self-scoped item ignores it exactly as the rulebook's scopes
    dictate.
    """
    del session
    if party_in_combat(actor):
        # Deliberately before target resolution: an in-combat request must not
        # resolve, consume, mutate or advance anything. The party-wide check
        # also covers a session persisted under the actor's commander.
        return _session_rejected(SessionReason.COMBAT_ITEM_COMMAND_REQUIRED)
    item_key = payload["item_key"]
    try:
        member = authorize_member(
            resolve_commander(actor),
            payload["actor_id"],
            PURPOSE_ACT,
            anchor=actor,
        )
        target = (
            _resolve_inventory_target(member, payload["target_key"])
            if "target_key" in payload
            else None
        )
        outcome = use_member_item(actor, payload["actor_id"], item_key, target=target)
    except PartyScopeError as error:
        return {
            "outcome": "rejected",
            "code": error.reason,
            "message": error.message,
        }
    result = outcome.settlement.result
    if result.outcome != "success":
        return _rejected(result.reason)
    message = render_plain_text(result.event_log)
    actor.msg(message)
    return _success("item_used", message, ())


def _inventory_toggle_equip_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Delegate one member's ownership-aware equipment toggle (a free action).

    ``actor_id`` is reauthorized by the party member boundary: a forged or
    absent member reference rejects with the shared party code and the
    commander is never toggled in its place. The toggle stays free in
    exploration and in combat, and its existing draft-preview invalidation
    applies to the re-equipped member.
    """
    del session
    item_key = payload["item_key"]
    try:
        outcome = toggle_member_equipment(actor, payload["actor_id"], item_key)
    except PartyScopeError as error:
        return {
            "outcome": "rejected",
            "code": error.reason,
            "message": error.message,
        }
    result = outcome.result
    if result.outcome != "success":
        return _rejected(result.reason)
    subject = "你" if outcome.member is actor else npc_display_name(outcome.member)
    message = toggle_equipment_message(result, item_key, subject)
    actor.msg(message)
    return _success("equipment_toggled", message, ())


__all__ = [
    "ServiceActionError",
    "validate_buy_payload",
    "validate_exam_request_payload",
    "validate_guild_register_payload",
    "validate_inventory_toggle_equip_payload",
    "validate_inventory_use_payload",
    "validate_quest_abandon_payload",
    "validate_quest_accept_payload",
    "validate_quest_track_payload",
    "validate_quest_turnin_payload",
    "validate_sell_payload",
]
