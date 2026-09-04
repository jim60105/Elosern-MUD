"""Exact service action payload validators and narrow adapters.

The seven production service actions are ``guild.register``,
``guild.quest_accept``, ``guild.quest_abandon``, ``guild.quest_turnin``,
``guild.exam_start``, ``shop.buy``, and ``shop.sell``. Each validator enforces
an exact bounded payload shape; each adapter re-resolves the local
``GuildStaff`` / ``GuildExaminer`` / ``Merchant`` host and every referenced
identity against current canonical state, calls only the listed public
deterministic APIs, and never assigns ``.db`` attributes, traits, registration,
rank, merit, quest log, wallet, inventory, merchant stock, or location
directly. No payload accepts an actor, host, branch, session, price, stock, or
wallet field, and no action routes through the text command parser.
"""

from typing import Any

from typeclasses.components import GuildExaminer, GuildStaff, Merchant
from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.items import ITEM_REGISTRY
from world.quests.runtime import (
    QuestAlreadyActive,
    QuestDataError,
    QuestNotFound,
    QuestTransitionError,
    set_quest_tracked,
)
from world.rules.combat_result import emit_settlement, settle_to_oob_result
from world.rules.combat_session import (
    CombatSessionError,
    is_in_active_session,
    submit_player_item_use,
)
from world.rules.economy import TradeError, buy, sell
from world.rules.equipment import registry_key_for_object, toggle_equipment
from world.rules.equipment_effects import equipment_adjustment_text
from world.rules.event_log import render_plain_text
from world.rules.guild import (
    GuildDataError,
    GuildError,
    GuildServiceError,
    RewardClaimError,
    parse_guild_registration,
    register_adventurer,
    resolve_local_service_host,
    turn_in_quest,
)
from world.rules.guild_exams import GuildExamError, start_guild_exam
from world.rules.guild_offers import (
    BoardAccessError,
    GuildOfferError,
    accept_guild_offer,
    abandon_guild_quest,
)
from world.rules.items import use_item
from world.rules.npc_schedules import interaction_reason
from world.rules.player_messages import session_reason_message
from world.rules.service_messages import rejection_code, rejection_message

# Wire limits (equal to or below the protocol identifier bound).
MAX_KEY_CODE_POINTS = 64
MAX_RANK_KEY_CODE_POINTS = 8
MAX_QUANTITY = 1000
MIN_QUANTITY = 1

# Stable panels each admitted service action may publish. Every quest write
# seam publishes the ``objectives`` panel beside its paired ``services`` rows
# (webclient-align-06: the tracker island must never lag the quest log).
AFFECTED_REGISTER = ("status", "services")
AFFECTED_ACCEPT = ("services", "objectives")
AFFECTED_ABANDON = ("services", "objectives")
AFFECTED_TURNIN = ("status", "services", "objectives")
AFFECTED_EXAM = ("status", "services", "context_actions")
AFFECTED_TRADE = ("status", "services")
AFFECTED_TRACK = ("services", "objectives")


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


def validate_exam_start_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``guild.exam_start`` payload (one next-rank key)."""
    body = _exact_single_field(payload, "target_rank")
    return {"target_rank": _require_non_empty_string(
        body["target_rank"], "target_rank", MAX_RANK_KEY_CODE_POINTS
    )}


def _validate_trade_payload(payload: dict[str, Any], action_id: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ServiceActionError(f"{action_id} payload must be an object")
    if set(payload) != {"item_key", "quantity"}:
        raise ServiceActionError(f"{action_id} requires exactly item_key and quantity")
    return {
        "item_key": _require_non_empty_string(
            payload["item_key"], "item_key", MAX_KEY_CODE_POINTS
        ),
        "quantity": _require_quantity(payload["quantity"]),
    }


def validate_buy_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``shop.buy`` payload (item key plus quantity)."""
    return _validate_trade_payload(payload, "shop.buy")


def validate_sell_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``shop.sell`` payload (item key plus quantity)."""
    return _validate_trade_payload(payload, "shop.sell")


def _require_key_identifier(value: Any, field: str, maximum: int) -> str:
    """Require a whitespace-free bounded key.

    The typed `使用`/`use` and `裝備`/`equip` commands parse the key as their
    first whitespace-delimited token, and the browser's input echo prints the
    key verbatim — a whitespace-bearing key would echo a line whose keyboard
    replay resolves a DIFFERENT key. Reject at the action boundary instead
    (complete-ui-command-echo D1).
    """
    text = _require_non_empty_string(value, field, maximum)
    if any(character.isspace() for character in text):
        raise ServiceActionError(f"{field} must not contain whitespace")
    return text


def _validate_inventory_item_payload(payload: dict[str, Any]) -> dict[str, Any]:
    body = _exact_single_field(payload, "item_key")
    return {"item_key": _require_key_identifier(
        body["item_key"], "item_key", MAX_KEY_CODE_POINTS
    )}


def validate_inventory_use_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``inventory.use`` payload (one item key)."""
    return _validate_inventory_item_payload(payload)


def validate_inventory_toggle_equip_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``inventory.toggle_equip`` payload (one item key)."""
    return _validate_inventory_item_payload(payload)


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


def _exact_next_rank(rank_key: Any) -> str | None:
    """Return the exact next rank key for ``rank_key``, or ``None``."""
    if not isinstance(rank_key, str) or rank_key not in GUILD_RANK_REGISTRY:
        return None
    order = GUILD_RANK_REGISTRY[rank_key].order
    candidate = next(
        (member.key for member in GUILD_RANK_REGISTRY.values() if member.order == order + 1),
        None,
    )
    return candidate


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


def _exam_start_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Start the examination for the exact server-derived next rank only."""
    del session
    target_rank = payload["target_rank"]
    examiner, reason = _resolve_local(
        actor, GuildExaminer, "no_examiner", "ambiguous_examiner"
    )
    if examiner is None:
        return _rejected(reason)
    blocked = _schedule_rejected(examiner, "service_guild")
    if blocked is not None:
        return blocked
    if parse_guild_registration(actor) is None:
        return _rejected("unregistered")
    expected = _exact_next_rank(getattr(actor, "guild_rank", None))
    if expected is None or target_rank != expected:
        return _rejected("not_next_rank")
    try:
        record = start_guild_exam(actor, examiner, target_rank, requested_by="webclient")
    except GuildExamError as error:
        return _rejected(error)
    message = (
        f"升階考核（{record.target_rank}）開始。這是模擬戰，"
        "雙方在開戰前與結束後都會恢復全部的體力、法力與精力。"
    )
    actor.msg(message)
    return _success("exam_started", message, AFFECTED_EXAM)


def _buy_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Recheck open state, price, funds, and stock, then call ``economy.buy``."""
    del session
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
        result = buy(actor, merchant_host, item_key, quantity)
    except TradeError as error:
        return _rejected(error)
    message = (
        f"你買了 {result['quantity']} 個 {result['item_key']}，"
        f"花費 {result['total_copper']} 銅，剩餘 {result['wallet']} 銅。"
    )
    actor.msg(message)
    return _success("bought", message, AFFECTED_TRADE)


def _sell_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Recheck open state, held items, and stock cap, then call ``economy.sell``."""
    del session
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
        result = sell(actor, merchant_host, item_key, quantity)
    except TradeError as error:
        return _rejected(error)
    message = (
        f"你賣了 {result['quantity']} 個 {result['item_key']}，"
        f"獲得 {result['total_copper']} 銅，目前 {result['wallet']} 銅。"
    )
    actor.msg(message)
    return _success("sold", message, AFFECTED_TRADE)


def _item_display_name(item_key: str) -> str:
    definition = ITEM_REGISTRY.get(item_key)
    return definition.display_name_zh if definition is not None else item_key


def _inventory_use_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Resolve actor mode and delegate one item use to its deterministic facade.

    In an active combat session the request occupies one initiative-ordered
    round through ``submit_player_item_use``; out of combat it settles with
    its canonical six-second world cost through ``use_item``. Success always
    publishes a full snapshot (empty affected-panel set).
    """
    del session
    item_key = payload["item_key"]
    if is_in_active_session(actor):
        try:
            result = submit_player_item_use(actor, item_key)
        except CombatSessionError as error:
            return _session_rejected(error.args[0])
        if result["outcome"] == "rejected":
            return _rejected(result.get("reason"))
        emit_settlement(actor, result)
        settled = settle_to_oob_result(result)
        settled["affected_panels"] = ()
        return settled
    settlement = use_item(actor, item_key)
    result = settlement.result
    if result.outcome != "success":
        return _rejected(result.reason)
    message = render_plain_text(result.event_log)
    actor.msg(message)
    return _success("item_used", message, ())


def _inventory_toggle_equip_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Delegate one ownership-aware equipment toggle (a free action)."""
    del session
    item_key = payload["item_key"]
    result = toggle_equipment(actor, item_key)
    if result.outcome != "success":
        return _rejected(result.reason)
    display = _item_display_name(item_key)
    prose = equipment_adjustment_text(item_key)
    if result.action == "unequip-singleton":
        message = f"你卸下了 {display}。"
    elif result.action == "unequip-accessory":
        message = f"你除下了 {display}。"
    elif result.action == "equip-accessory":
        message = f"你佩戴了 {display}" + (f"（{prose}）" if prose else "") + "。"
    elif result.replaced_key is not None:
        replaced = _item_display_name(result.replaced_key)
        if prose:
            message = f"你裝備了 {display}（{prose}），原本的 {replaced} 已收回背包。"
        else:
            message = f"你裝備了 {display}，原本的 {replaced} 已收回背包。"
    else:
        message = f"你裝備了 {display}" + (f"（{prose}）" if prose else "") + "。"
    actor.msg(message)
    return _success("equipment_toggled", message, ())


__all__ = [
    "ServiceActionError",
    "validate_buy_payload",
    "validate_exam_start_payload",
    "validate_guild_register_payload",
    "validate_inventory_toggle_equip_payload",
    "validate_inventory_use_payload",
    "validate_quest_abandon_payload",
    "validate_quest_accept_payload",
    "validate_quest_track_payload",
    "validate_quest_turnin_payload",
    "validate_sell_payload",
]
