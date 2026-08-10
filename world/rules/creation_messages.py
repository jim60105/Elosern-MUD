"""Stable character-creation rejection codes and Traditional Chinese messages.

Every deterministic creation rejection produced by
``world.rules.character_creation`` (``preflight_character_creation`` and
``activate_player_character``) and the creation-wizard draft service
(``world.rules.creation_wizard``) maps to one stable ``code`` and one safe
bounded Traditional Chinese message here. The WebClient creation adapters and
(by extension) the browser share this single mapping so Telnet and the
WebClient present identical prose and stable identifiers. An unknown or
unmapped rejection degrades to a bounded generic fallback that never exposes a
traceback or raw payload.
"""

from typing import Any

from world.rules.character_creation import CharacterCreationError

# The bounded generic fallback; never carries a traceback or raw payload.
FALLBACK_CODE = "creation_rejected"
FALLBACK_MESSAGE = "角色建立目前無法完成。"

# Stable player-facing messages keyed by the stable reason code. Telnet
# command output and the browser creation dock share these exact strings.
CREATION_REASON_MESSAGES: dict[str, str] = {
    "unknown_preset": "找不到這個預設角色。",
    "invalid_name": "角色姓名必須是 1–80 個可列印字元，且不含控制字元。",
    "markup_delimiter": "角色姓名不能包含特殊格式標記。",
    "underage_age": "實際年齡必須是至少 18 的整數。",
    "underage_apparent_age": "外表年齡必須是至少 18 的整數。",
    "unknown_race": "找不到這個種族。",
    "unknown_subrace": "找不到這個子種族。",
    "incompatible_subrace": "這個子種族不屬於所選種族。",
    "malformed_allocations": "配點必須包含全部六個起始軸。",
    "out_of_span_allocation": "配點超出該軸允許的範圍。",
    "off_budget_allocations": "配點總和必須恰好等於預算。",
    "already_complete": "角色建立已經完成。",
    "ownership_rejected": "無法為這個帳號建立角色。",
    "no_draft": "尚未儲存角色草稿。",
    "incomplete_draft": "角色草稿尚未完成。",
    "concept_unavailable": "生成不可用，請手動創角",
    "concept_stale": "構想草稿已被修改，請重新提交。",
    "malformed_request": "角色建立要求格式有誤。",
}

# Exact message fragments emitted by the deterministic service, mapped to
# stable codes. Ordered; the first matching fragment wins. Each fragment is
# a stable substring of one deterministic ``CharacterCreationError`` message.
_MESSAGE_CODE_MATCHES: tuple[tuple[str, str], ...] = (
    ("character is not owned by this account", "ownership_rejected"),
    ("character creation is already complete", "already_complete"),
    ("no creation draft saved", "no_draft"),
    ("creation draft is incomplete", "incomplete_draft"),
    ("unknown player preset", "unknown_preset"),
    ("creation mode must be 'preset' or 'custom'", "malformed_request"),
    ("display name contains an Evennia markup delimiter", "markup_delimiter"),
    ("display name contains a control character", "invalid_name"),
    ("display name must be text", "invalid_name"),
    ("display name must contain 1 to 80 characters", "invalid_name"),
    ("apparent_age must be an integer of at least 18", "underage_apparent_age"),
    ("age must be an integer of at least 18", "underage_age"),
    ("does not belong to race", "incompatible_subrace"),
    ("unknown subrace", "unknown_subrace"),
    ("subrace must be a registry key or omitted", "unknown_subrace"),
    ("unknown race", "unknown_race"),
    ("race must be a registry key", "unknown_race"),
    ("allocations must sum exactly to", "off_budget_allocations"),
    ("allocation for", "out_of_span_allocation"),
    ("allocations must contain exactly the six starting axes", "malformed_allocations"),
)


def rejection_code(reason: Any) -> str:
    """Return the stable code for one deterministic creation rejection.

    ``reason`` may be a :class:`CharacterCreationError` instance, a raw stable
    code string, or any object whose ``str`` carries a known deterministic
    message fragment. Any unknown input degrades to :data:`FALLBACK_CODE`.
    """
    if isinstance(reason, CharacterCreationError):
        message = str(reason.args[0]) if reason.args else ""
    else:
        message = str(reason)
    for fragment, code in _MESSAGE_CODE_MATCHES:
        if fragment in message:
            return code
    if isinstance(reason, str) and reason in CREATION_REASON_MESSAGES:
        return reason
    return FALLBACK_CODE


def rejection_message(reason: Any) -> str:
    """Return the safe Traditional Chinese message for a stable code."""
    return CREATION_REASON_MESSAGES.get(rejection_code(reason), FALLBACK_MESSAGE)


def creation_reason(reason: Any) -> tuple[str, str]:
    """Return the stable ``(code, message)`` pair for one rejection."""
    code = rejection_code(reason)
    return code, CREATION_REASON_MESSAGES.get(code, FALLBACK_MESSAGE)


__all__ = [
    "CREATION_REASON_MESSAGES",
    "FALLBACK_CODE",
    "FALLBACK_MESSAGE",
    "creation_reason",
    "rejection_code",
    "rejection_message",
]
