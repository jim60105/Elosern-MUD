"""Exact ``character.persona.update`` adapter for the four persona prose fields.

One action edits exactly one whitelisted persona prose field with the payload
``{field, text}``: ``field`` is a member of ``PERSONA_EDITABLE_FIELDS`` and
``text`` is trimming-bounded (1..600 code points) or ``null`` (clear). The
validator enforces the exact bounded shape; the adapter calls only the
deterministic ``world.rules.persona_edit`` writer and never assigns attributes
directly. The adapter admits the session's own activated puppet in exploration
mode (the shared ``in_exploration_mode`` gate covers both creation-pending and
active combat) and mirrors the Telnet persona command family's Traditional
Chinese lines (``commands/persona.py``) so both faces speak one vocabulary.
A successful update declares the ``character`` panel as affected so the
completion publication re-renders the drawer immediately.
"""

from typing import Any

from web.webclient.presentation.affordances import in_exploration_mode
from world.rules.character_creation import MAX_PERSONA_FIELD_LENGTH
from world.rules.persona_edit import PERSONA_EDITABLE_FIELDS, update_persona_field

# Stable rejection codes and the Traditional Chinese lines shared with the
# telnet persona command family (commands/background.py / commands/persona.py
# messages over the same field labels).
NOT_EXPLORING_CODE = "not_exploring"
NOT_EXPLORING_MESSAGE = "你目前無法編輯角色資料。"
REJECTED_CODE = "persona_field_rejected"
REJECTED_MESSAGE = "無法更新該資料。"

# The persona prose keys in display order with their zh-TW labels (the same
# labels the drawer sections and the Telnet family use).
PERSONA_FIELD_LABELS: dict[str, str] = {
    "personality": "個性",
    "life_story": "生平",
    "habit": "習慣",
    "background": "背景",
}

# A successful update re-renders the character drawer's persona sections.
AFFECTED_CHARACTER = ("character",)


class CharacterActionError(ValueError):
    """A ``character.persona.update`` payload violates its exact schema."""


def validate_character_persona_update_payload(
    payload: dict[str, Any]
) -> dict[str, Any]:
    """Validate the exact ``character.persona.update`` payload.

    Requires exactly ``field`` (a whitelisted persona prose key) and ``text``
    (``null`` to clear, or a string whose trimmed form is 1..600 code points).
    A blank string is rejected — clearing is expressed with ``null``.
    """
    if not isinstance(payload, dict):
        raise CharacterActionError(
            "character.persona.update payload must be an object"
        )
    if set(payload) != {"field", "text"}:
        raise CharacterActionError("character.persona.update requires exactly field/text")
    field = payload["field"]
    if field not in PERSONA_EDITABLE_FIELDS:
        raise CharacterActionError("field must be a whitelisted persona field")
    text = payload["text"]
    if text is None:
        return {"field": field, "text": None}
    if not isinstance(text, str):
        raise CharacterActionError("text must be a string or null")
    trimmed = text.strip()
    if not 1 <= sum(1 for _ in trimmed) <= MAX_PERSONA_FIELD_LENGTH:
        raise CharacterActionError(
            f"text must trim to 1..{MAX_PERSONA_FIELD_LENGTH} code points"
        )
    return {"field": field, "text": trimmed}


def _persona_message(field: str, persisted: str | None) -> str:
    """Compose the shared zh-TW confirmation line for one field update."""
    label = PERSONA_FIELD_LABELS[field]
    if persisted:
        return f"已設定{label}：{persisted}"
    return f"已清除{label}。"


def _character_persona_update_adapter(
    actor: Any, payload: dict[str, Any], session: Any = None
) -> dict[str, Any]:
    """Write exactly one persona prose field through the rules writer.

    The actor is the session's own puppet (resolved by the dispatcher); the
    shared exploration-mode gate refuses creation-pending and in-combat
    actors. A clearing write over a field the character never set is a
    confirmed no-op success. Any service-side rejection maps to the single
    stable code and writes nothing.
    """
    del session
    if not in_exploration_mode(actor):
        return {
            "outcome": "rejected",
            "code": NOT_EXPLORING_CODE,
            "message": NOT_EXPLORING_MESSAGE,
        }
    try:
        persisted = update_persona_field(actor, payload["field"], payload["text"])
    except ValueError:
        return {
            "outcome": "rejected",
            "code": REJECTED_CODE,
            "message": REJECTED_MESSAGE,
        }
    message = _persona_message(payload["field"], persisted)
    actor.msg(message)
    return {
        "outcome": "success",
        "code": "persona_updated",
        "message": message,
        "affected_panels": AFFECTED_CHARACTER,
    }


__all__ = [
    "AFFECTED_CHARACTER",
    "NOT_EXPLORING_CODE",
    "NOT_EXPLORING_MESSAGE",
    "PERSONA_FIELD_LABELS",
    "REJECTED_CODE",
    "REJECTED_MESSAGE",
    "CharacterActionError",
    "validate_character_persona_update_payload",
]
