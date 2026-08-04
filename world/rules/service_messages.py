"""Stable service-rejection codes and Traditional Chinese messages.

Every deterministic service rejection produced by the guild, quest, shop, and
examination APIs maps to one stable ``code`` and one safe bounded Traditional
Chinese message here. The WebClient service adapters, the service read model's
disabled descriptors, and (by extension) the browser share this single mapping
so Telnet and the WebClient present identical prose and stable identifiers. An
unknown or unmapped rejection degrades to a bounded generic fallback that never
exposes a traceback or raw payload.
"""

from typing import Any

from world.quests.runtime import (
    QuestAlreadyActive,
    QuestDataError,
    QuestNotFound,
    QuestTransitionError,
)
from world.rules.economy import TradeError, TradeReason
from world.rules.guild import (
    GuildDataError,
    GuildServiceError,
    GuildError,
    RegistrationReason,
    RewardClaim,
    RewardClaimError,
)
from world.rules.guild_exams import ExamReason, GuildExamError
from world.rules.guild_offers import (
    BoardAccessError,
    GuildOfferError,
    GuildOfferNotFound,
)

# The bounded generic fallback; never carries a traceback or raw payload.
FALLBACK_CODE = "service_rejected"
FALLBACK_MESSAGE = "此操作目前無法完成。"

# Stable player-facing messages keyed by the stable reason code. Telnet
# command output and the browser service menus share these exact strings.
SERVICE_REASON_MESSAGES: dict[str, str] = {
    # Registration and guild data.
    "not_a_player": "這個角色不能使用這項服務。",
    "no_staff": "這裡沒有公會服務人員。",
    "ambiguous_staff": "這裡有多名公會服務人員。",
    "remote_staff": "公會服務人員不在這裡。",
    "already_registered": "你已經是冒險者了。",
    "malformed_registration": "公會資料有誤。",
    "guild_data_error": "公會資料有誤。",
    "guild_service_error": "公會服務目前無法使用。",
    # Board and quest acceptance.
    "board_access": "無法查看任務板或接取任務。",
    "offer_unknown": "找不到這個任務。",
    "offer_invalid": "這個任務無法接取。",
    "quest_not_found": "找不到這個任務。",
    "quest_data_error": "任務記錄有誤。",
    "quest_already_active": "這個任務已經在進行中了。",
    "quest_transition": "這個任務目前無法進行此操作。",
    # Reward claims.
    "unregistered": "你尚未註冊為冒險者。",
    "no_completed_record": "沒有可以回報的已完成任務。",
    "already_claimed": "這份獎勵已經領取過了。",
    "malformed_claims": "獎勵記錄有誤。",
    # Examination.
    "no_examiner": "這裡沒有考核官。",
    "ambiguous_examiner": "這裡有多名考核官。",
    "remote_examiner": "考核官不在這裡。",
    "wrong_branch": "這不是你的公會分部。",
    "not_next_rank": "只能參加下一階級的考核。",
    "below_threshold": "你的功績還不足以參加升階考核。",
    "active_combat": "你已經在戰鬥中了。",
    "duplicate_active": "已經有一場考核在進行中。",
    "unknown_profile": "考核資料有誤。",
    "malformed_record": "考核記錄有誤。",
    "already_settled": "這次考核已經結束了。",
    "not_settlable": "這次考核無法結算。",
    "unknown_exam": "找不到這次考核。",
    # Trade.
    "no_merchant": "這裡沒有商人。",
    "ambiguous_merchant": "這裡有多名商人。",
    "remote_merchant": "商人不在這裡。",
    "closed": "商店目前沒有營業。",
    "unknown_item": "商店不賣這個物品。",
    "not_offered": "商店沒有這個商品。",
    "unsellable": "這個物品無法販賣。",
    "bad_quantity": "數量必須是正整數。",
    "insufficient_funds": "你的銅幣不足。",
    "insufficient_stock": "商店庫存不足。",
    "insufficient_items": "你沒有足夠的這個物品。",
    "stock_overflow": "商店收購上限已滿。",
    "malformed_stock": "商店資料有誤。",
    "unknown_shop": "這間商店沒有設定。",
    # Read-model surface reasons (never carried as adapter results).
    "no_local_service_host": "這裡沒有對應的服務。",
    "ambiguous_service_host": "這裡有多個對應的服務人員。",
    "malformed_quest_log": "任務記錄有誤。",
    "malformed_equipment": "背包資料有誤。",
}

# Reason types whose enum member (``reason.args[0]``) names the exact code.
_ENUM_REASON_TYPES = (RegistrationReason, RewardClaim, ExamReason, TradeReason)
# Exception types whose ``args[0]`` may carry an enum member or a raw string.
_ARGS_REASON_TYPES = (GuildError, GuildExamError, TradeError, RewardClaimError)


def rejection_code(reason: Any) -> str:
    """Return the stable code for one deterministic rejection.

    ``reason`` may be the exception instance, the enum member carried in its
    ``args[0]``, or a raw stable code string. Any unknown input degrades to
    :data:`FALLBACK_CODE`.
    """
    if isinstance(reason, _ENUM_REASON_TYPES):
        return str(reason.value)
    if isinstance(reason, _ARGS_REASON_TYPES):
        inner = reason.args[0] if reason.args else None
        if isinstance(inner, _ENUM_REASON_TYPES):
            return str(inner.value)
        if isinstance(reason, RewardClaimError):
            return "malformed_claims"
        if isinstance(reason, TradeError):
            return "malformed_stock"
        if isinstance(reason, GuildExamError):
            return "guild_service_error"
        if isinstance(reason, GuildError):
            return "guild_service_error"
    if isinstance(reason, (GuildDataError,)):
        return "guild_data_error"
    if isinstance(reason, (GuildServiceError,)):
        return "guild_service_error"
    if isinstance(reason, (BoardAccessError,)):
        return "board_access"
    if isinstance(reason, (GuildOfferError,)):
        return "offer_invalid"
    if isinstance(reason, (GuildOfferNotFound,)):
        return "offer_unknown"
    if isinstance(reason, (QuestNotFound,)):
        return "quest_not_found"
    if isinstance(reason, (QuestDataError,)):
        return "quest_data_error"
    if isinstance(reason, (QuestAlreadyActive,)):
        return "quest_already_active"
    if isinstance(reason, (QuestTransitionError,)):
        return "quest_transition"
    if isinstance(reason, str) and reason in SERVICE_REASON_MESSAGES:
        return reason
    return FALLBACK_CODE


def rejection_message(reason: Any) -> str:
    """Return the safe Traditional Chinese message for a stable code."""
    return SERVICE_REASON_MESSAGES.get(rejection_code(reason), FALLBACK_MESSAGE)


def service_reason(reason: Any) -> tuple[str, str]:
    """Return the stable ``(code, message)`` pair for one rejection."""
    code = rejection_code(reason)
    return code, SERVICE_REASON_MESSAGES.get(code, FALLBACK_MESSAGE)


__all__ = [
    "FALLBACK_CODE",
    "FALLBACK_MESSAGE",
    "SERVICE_REASON_MESSAGES",
    "rejection_code",
    "rejection_message",
    "service_reason",
]
