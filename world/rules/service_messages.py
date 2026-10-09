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
from world.rules.equipment import EquipmentToggleReason
from world.rules.items import ItemUseReason
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
from world.rules.clock import WorldDateTime
from world.rules.npc_schedules import SCHEDULE_BLOCKED_REASON
from world.rules.service_gate import MESSAGE_OFF_ANCHOR

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
    # Shared anchoring-gate refusal; the prose is owned by service_gate.
    "service_unavailable": MESSAGE_OFF_ANCHOR,
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
    "quest_track_limit": "你最多只能同時追蹤三個任務。",
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
    "unqualified_examiner": "這裡沒有能主持這個階級考核的考官。",
    "participant_name_collision": "無法與同名的考官進行考核。",
    "examiner_engaged": "考官正在主持另一場考核。",
    "not_settlable": "這次考核無法結算。",
    "unknown_exam": "找不到這次考核。",
    "examiner_busy": "考官正忙著別的事，現在無法主持考核。",
    "schedule_blocked": SCHEDULE_BLOCKED_REASON,
    "attendance_unknown": "櫃台目前無法確認考官下次到公會的時間。",
    "top_rank": "你已是最高階級，沒有下一場升等考核。",
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
    # Personal item use and equipment toggle.
    "hp_full": "你的體力已經全滿。",
    "mp_full": "你的魔力已經全滿。",
    "no_debuffs": "你身上沒有需要淨化的負面狀態。",
    "sp_full": "你的體力值已經全滿。",
    "pleasure_full": "你的快感已經全滿。",
    "no_effect": "這個物品現在對你沒有可執行的效果。",
    "status_blocked": "你的裝備抵擋了這個狀態效果。",
    "nothing_to_remove": "你身上沒有可以移除的狀態。",
    "item_not_held": "你沒有攜帶這個物品。",
    "not_usable": "這個物品無法這樣使用。",
    "not_equipment": "這個物品無法裝備。",
    "guild_property": "公會保管的封印環不能自行穿脫。",
    "exam_kit_locked": "考核期間不能更換考官的裝備。",
    "not_alive": "你目前無法使用這個物品。",
    "combat_not_allowed": "戰鬥中無法使用這個物品。",
    "unknown_effect": "這個物品的效果尚未設定。",
    "no_target": "這個物品需要指定一個目標。",
    "target_invalid": "你的目標無法接受這個物品的效果。",
    "accessory_slots_full": "飾品欄已經滿了，最多同時佩戴五個。",
    "equipped_item": "已裝備的物品不能這樣賣出。",
    "malformed_inventory": "背包資料有誤。",
    "malformed_traits": "角色資料有誤。",
}

# Reason types whose enum member (``reason.args[0]``) names the exact code.
_ENUM_REASON_TYPES = (
    RegistrationReason,
    RewardClaim,
    ExamReason,
    TradeReason,
    EquipmentToggleReason,
    ItemUseReason,
)
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
        inner = reason.args[0] if reason.args else None
        if isinstance(inner, str) and inner in SERVICE_REASON_MESSAGES:
            return inner
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


def _calendar_stamp(tick: int, *, with_date: bool = True) -> str:
    moment = WorldDateTime.from_tick(tick)
    clock = f"{moment.hour:02d}:{moment.minute:02d}"
    if not with_date:
        return clock
    return f"{moment.season_name} {moment.day_in_season} 日 {clock}"


def format_planned_interval(start_tick: int, end_tick: int) -> str:
    """Format one planned ``[start, end)`` interval on the game calendar.

    The end repeats the calendar date only when it falls on another day, so
    a same-day window reads 「春季 3 日 09:00 至 12:00」.
    """
    start = WorldDateTime.from_tick(start_tick)
    end = WorldDateTime.from_tick(end_tick)
    same_day = (start.year, start.season_index, start.day_in_season) == (
        end.year, end.season_index, end.day_in_season
    )
    return f"{_calendar_stamp(start_tick)} 至 {_calendar_stamp(end_tick, with_date=not same_day)}"


def exam_schedule_message(host_name: str, target_rank: str, start_tick: int, end_tick: int) -> str:
    """The planned-attendance reply of an absent-host examination request.

    It names the host and the planned interval only: no private route, no
    saved booking, no reserved place.
    """
    return (
        f"{host_name} 目前不在公會。依櫃台登記的行程，{host_name} 預定於"
        f"{format_planned_interval(start_tick, end_tick)}在公會，可主持 {target_rank} 階升等考核。"
        "這只是預定時程，櫃台不會替你保留名額；屆時請再來申請考核。"
    )


def exam_started_message(target_rank: str) -> str:
    """The started-simulation reply shared by the command and the WebClient."""
    return (
        f"升階考核（{target_rank}）開始。這是模擬戰，"
        "雙方在開戰前與結束後都會恢復全部的體力、法力與精力。"
    )


__all__ = [
    "FALLBACK_CODE",
    "FALLBACK_MESSAGE",
    "SERVICE_REASON_MESSAGES",
    "exam_schedule_message",
    "exam_started_message",
    "format_planned_interval",
    "rejection_code",
    "rejection_message",
    "service_reason",
]
