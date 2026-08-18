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
from world.quests.runtime import (
    QuestAlreadyActive,
    QuestDataError,
    QuestNotFound,
)
from world.rules.economy import TradeError, buy, sell
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
from world.rules.npc_schedules import interaction_reason
from world.rules.service_messages import rejection_code, rejection_message

# Wire limits (equal to or below the protocol identifier bound).
MAX_KEY_CODE_POINTS = 64
MAX_RANK_KEY_CODE_POINTS = 8
MAX_QUANTITY = 1000
MIN_QUANTITY = 1

# Stable panels each admitted service action may publish.
AFFECTED_REGISTER = ("status", "services")
AFFECTED_ACCEPT = ("services",)
AFFECTED_ABANDON = ("services",)
AFFECTED_TURNIN = ("status", "services")
AFFECTED_EXAM = ("status", "services", "context_actions")
AFFECTED_TRADE = ("status", "services")


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
    if result.get("onboarding_completed"):
        actor.msg("你的第一個日子在這裡圓滿結束。冒險者，歡迎正式踏入伊洛瑟恩大陸。")
    return _success("claimed", message, AFFECTED_TURNIN)


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


__all__ = [
    "ServiceActionError",
    "validate_buy_payload",
    "validate_exam_start_payload",
    "validate_guild_register_payload",
    "validate_quest_abandon_payload",
    "validate_quest_accept_payload",
    "validate_quest_turnin_payload",
    "validate_sell_payload",
]
