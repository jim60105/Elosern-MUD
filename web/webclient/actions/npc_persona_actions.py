"""Exact ``npc.persona.read`` and ``npc.persona.update`` actions.

Author-editor transport for reading and atomic version-guarded replacing of
compact NPC character cards from the exploration/dialogue surface.
"""

from typing import Any

from typeclasses.npcs import NPC
from web.webclient.actions.exploration_actions import _present_by_id
from web.webclient.presentation.affordances import in_exploration_mode
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    MAX_SAFE_INTEGER,
    MAX_STRING_CODE_POINTS,
)
from world.lore.npc_card import (
    NPC_CARD_FIELDS,
    NpcCard,
    NpcCardError,
    normalize_card,
)
from world.rules.npc_persona import (
    UpdateOutcome,
    read_npc_persona,
    update_npc_persona,
)
from world.rules.possession import (
    POSSESSED_REFUSAL_MESSAGES,
    REASON_POSSESSED_TALK,
    is_possessed_actor,
)

# Panel invalidation: read has no affected panels beyond completion; update affects
# exploration so the entry affordance enabled state stays fresh.
AFFECTED_READ: tuple[str, ...] = ()
AFFECTED_UPDATE: tuple[str, ...] = ("exploration",)

# Stable rejection codes
CODE_NOT_ALLOWED = "npc_persona.not_allowed"
CODE_NO_TARGET = "npc_persona.no_target"
CODE_UNAVAILABLE = "npc_persona.unavailable"
CODE_VERSION_CONFLICT = "npc_persona.version_conflict"

# Traditional Chinese messages
MSG_NOT_ALLOWED_MODE = "你目前無法編輯 NPC 設定。"
MSG_NO_TARGET = "這裡沒有這個對象。"
MSG_UNAVAILABLE = "此角色的設定目前無法讀取或尚未初始化。"
MSG_STORAGE_UNAVAILABLE = "伺服器忙碌中，請稍後再試。"

_IDENTITY_KEYS = frozenset({"public", "hidden"})


class NpcPersonaActionError(ValueError):
    """An ``npc.persona.*`` action payload violates its exact schema."""


def validate_read_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact ``npc.persona.read`` payload.

    Must be exactly ``{"npc_id": <int>}``, where ``npc_id`` is a positive
    integer within safe integer bounds, and never a boolean.
    """
    if not isinstance(payload, dict):
        raise NpcPersonaActionError("payload must be a dict")
    if set(payload.keys()) != {"npc_id"}:
        raise NpcPersonaActionError("payload must contain exactly 'npc_id'")

    npc_id = payload["npc_id"]
    if type(npc_id) is not int or npc_id <= 0 or npc_id > MAX_SAFE_INTEGER:
        raise NpcPersonaActionError("npc_id must be a positive safe integer")

    return {"npc_id": npc_id}


def validate_update_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact ``npc.persona.update`` payload.

    Must contain exactly ``{"npc_id": <int>, "expected_persona_version": <int>, "persona": <dict>}``.
    Persona must contain exactly the 7 canonical keys, identity with exactly public and hidden,
    and all leaf values must be strings <= MAX_STRING_CODE_POINTS (2048).
    """
    if not isinstance(payload, dict):
        raise NpcPersonaActionError("payload must be a dict")
    if set(payload.keys()) != {"npc_id", "expected_persona_version", "persona"}:
        raise NpcPersonaActionError(
            "payload must contain exactly 'npc_id', 'expected_persona_version', and 'persona'"
        )

    npc_id = payload["npc_id"]
    if type(npc_id) is not int or npc_id <= 0 or npc_id > MAX_SAFE_INTEGER:
        raise NpcPersonaActionError("npc_id must be a positive safe integer")

    expected_version = payload["expected_persona_version"]
    if type(expected_version) is not int or expected_version <= 0 or expected_version > MAX_SAFE_INTEGER:
        raise NpcPersonaActionError("expected_persona_version must be a positive safe integer")

    persona = payload["persona"]
    if not isinstance(persona, dict):
        raise NpcPersonaActionError("persona must be a dict")
    if set(persona.keys()) != NPC_CARD_FIELDS:
        raise NpcPersonaActionError(f"persona keys must be exactly {sorted(NPC_CARD_FIELDS)}")

    # Check identity dictionary
    identity = persona["identity"]
    if not isinstance(identity, dict):
        raise NpcPersonaActionError("identity must be a dict")
    if set(identity.keys()) != _IDENTITY_KEYS:
        raise NpcPersonaActionError(f"identity keys must be exactly {sorted(_IDENTITY_KEYS)}")

    for id_key in ("public", "hidden"):
        val = identity[id_key]
        if not isinstance(val, str):
            raise NpcPersonaActionError(f"identity.{id_key} must be a string")
        if len(val) > MAX_STRING_CODE_POINTS:
            raise NpcPersonaActionError(f"identity.{id_key} exceeds maximum string length")

    # Check remaining top-level string leaves
    for key in NPC_CARD_FIELDS:
        if key == "identity":
            continue
        val = persona[key]
        if not isinstance(val, str):
            raise NpcPersonaActionError(f"{key} must be a string")
        if len(val) > MAX_STRING_CODE_POINTS:
            raise NpcPersonaActionError(f"{key} exceeds maximum string length")

    return {
        "npc_id": npc_id,
        "expected_persona_version": expected_version,
        "persona": persona,
    }


def _rejected(code: str, message: str, affected_panels: tuple[str, ...] = ()) -> dict[str, Any]:
    return {
        "outcome": "rejected",
        "code": code,
        "message": message,
        "affected_panels": affected_panels,
    }

_NPC_CARD_FIELD_NAMES: dict[str, str] = {
    "identity.public": "身分（公開）",
    "identity.hidden": "身分（秘密）",
    "identity": "身分",
    "appearance": "外觀",
    "personality": "性格",
    "speech_style": "說話風格",
    "life_story": "生平",
    "habit": "習慣",
    "social_connection": "人際關係",
}

def _card_error_message(code: str, field: str | None) -> str:
    field_name = _NPC_CARD_FIELD_NAMES.get(field or "", field or "欄位")
    if code == "required_empty":
        return f"{field_name}為必填欄位，不能為空。"
    if code == "leaf_too_long":
        return f"{field_name}長度超過上限。"
    if code == "identity_section_too_long":
        return "身分設定總長度超過上限。"
    if code == "card_too_long":
        return "角色設定總長度超過上限。"
    return "角色設定不符合規範。"


def _check_admission(actor: Any, npc_id: int) -> tuple[NPC | None, dict[str, Any] | None]:
    """Shared gate for admission order (D3): possession -> exploration mode -> target resolution."""
    if is_possessed_actor(actor):
        msg = POSSESSED_REFUSAL_MESSAGES.get(REASON_POSSESSED_TALK, MSG_NOT_ALLOWED_MODE)
        return None, _rejected(CODE_NOT_ALLOWED, msg)

    if not in_exploration_mode(actor):
        return None, _rejected(CODE_NOT_ALLOWED, MSG_NOT_ALLOWED_MODE)

    target = _present_by_id(actor, npc_id)
    if target is None or not isinstance(target, NPC):
        return None, _rejected(CODE_NO_TARGET, MSG_NO_TARGET)

    return target, None


def read_npc_persona_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Read an NPC's compact persona card (read-only snapshot, D3/D4)."""
    target, rejection = _check_admission(actor, payload["npc_id"])
    if rejection is not None:
        return rejection

    snapshot = read_npc_persona(target)
    if hasattr(snapshot, "reason"):  # NpcPersonaUnavailable
        return _rejected(CODE_UNAVAILABLE, MSG_UNAVAILABLE)

    data = {
        "npc_id": target.id,
        "display_name": target.key,
        "npc_title": getattr(target, "npc_title", None) or "",
        "persona_version": snapshot.version,
        "persona": snapshot.card.to_record(),
    }
    return {
        "outcome": "success",
        "code": "read",
        "message": "角色設定讀取成功。",
        "data": data,
        "affected_panels": AFFECTED_READ,
    }


def update_npc_persona_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Update an NPC's compact persona card under version check (D3/D4)."""
    del session
    target, rejection = _check_admission(actor, payload["npc_id"])
    if rejection is not None:
        return rejection

    try:
        normalized_card = normalize_card(payload["persona"])
    except NpcCardError as exc:
        code = f"npc_persona.{exc.code}"
        if exc.field:
            code = f"{code}.{exc.field}"
        return _rejected(code, _card_error_message(exc.code, exc.field))

    outcome: UpdateOutcome = update_npc_persona(
        target,
        payload["persona"],
        expected_version=payload["expected_persona_version"],
        actor=actor,
    )

    if outcome.status in ("updated", "unchanged"):
        data = {
            "npc_id": target.id,
            "display_name": target.key,
            "npc_title": getattr(target, "npc_title", None) or "",
            "persona_version": outcome.version,
            "persona": normalized_card.to_record(),
        }
        return {
            "outcome": "success",
            "code": outcome.status,
            "message": "角色設定更新成功。" if outcome.status == "updated" else "設定未變更。",
            "data": data,
            "affected_panels": AFFECTED_UPDATE,
        }

    if outcome.status == "version_conflict":
        msg = f"這位角色的設定已在其他地方更新（目前第 {outcome.version} 版），請重新載入後再編輯。"
        return _rejected(CODE_VERSION_CONFLICT, msg)

    if outcome.status == "invalid":
        err = outcome.error
        if err is not None:
            code = f"npc_persona.{err.code}"
            if err.field:
                code = f"{code}.{err.field}"
            msg = _card_error_message(err.code, err.field)
        else:
            code = f"npc_persona.{outcome.reason}"
            msg = "角色設定不符合規範。"
        return _rejected(code, msg)

    if outcome.status == "storage_unavailable":
        return _rejected(CODE_UNAVAILABLE, MSG_STORAGE_UNAVAILABLE)

    # status == "unavailable" (missing_meta, corrupt_meta, corrupt_card, etc.)
    return _rejected(CODE_UNAVAILABLE, MSG_UNAVAILABLE)


__all__ = [
    "CODE_NOT_ALLOWED",
    "CODE_NO_TARGET",
    "CODE_UNAVAILABLE",
    "CODE_VERSION_CONFLICT",
    "NpcPersonaActionError",
    "read_npc_persona_adapter",
    "update_npc_persona_adapter",
    "validate_read_payload",
    "validate_update_payload",
]
