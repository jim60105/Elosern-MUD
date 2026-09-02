"""Deterministic post-activation writer for a character's persona prose fields.

This module is the single post-activation writer of a player character's four
editable persona prose fields (``background``, ``personality``, ``life_story``,
``habit``; whitelist constant ``PERSONA_EDITABLE_FIELDS``).
``update_persona_field`` validates the shared persona-field bound, creates the
import-card-shaped persona record when none exists, preserves every other
persona key (including keys outside the whitelist and unknown keys) while
writing or clearing exactly one field, and never touches traits, identity
attributes, or the world clock.

``update_background`` remains as a thin wrapper delegating with field
``"background"`` so existing callers keep working unchanged.

``PersonaStore`` remains read-only; persona records are written only by the
import loader, the ``world.rules`` deterministic services (activation and this
module), or the scene-builder characterization seam.
"""

from typing import Any

from world.rules.character_creation import MAX_PERSONA_FIELD_LENGTH

# The import-card persona record shape (world.imports loader contract): the six
# keys every PersonaStore consumer reads. Non-prose keys are stored as empty
# containers; the prose keys are empty strings until a concept block or the
# dialogue author fills them.
PERSONA_IMPORT_CARD_KEYS = (
    "identity", "personality", "life_story", "habit", "appearance",
    "social_connection",
)

# The exact four-key whitelist of post-activation editable persona prose
# fields (persona-editing D1). ``identity``/``appearance``/``social_connection``
# stay excluded; the structured keys are never editable through this surface.
PERSONA_EDITABLE_FIELDS = frozenset(
    {"background", "personality", "life_story", "habit"}
)


def update_persona_field(
    character: Any, field: Any, text: str | None
) -> str | None:
    """Set or clear one character's persona prose ``field``.

    ``field`` must be a member of ``PERSONA_EDITABLE_FIELDS``. ``text`` is
    trimmed and bounded to ``MAX_PERSONA_FIELD_LENGTH``; ``None`` or a blank
    value explicitly clears the field by removing the key. When the character
    has no persona record, the import-card-shaped record is created first
    (a clear without a record stays a no-op and creates nothing). Every other
    persona key (including unknown keys) is preserved. Returns the persisted
    text (``None`` when cleared).
    """
    if not isinstance(field, str) or field not in PERSONA_EDITABLE_FIELDS:
        raise ValueError(
            f"field must be one of {sorted(PERSONA_EDITABLE_FIELDS)}"
        )
    if text is not None:
        if not isinstance(text, str):
            raise ValueError(f"{field} must be text")
        text = text.strip()
        if len(text) > MAX_PERSONA_FIELD_LENGTH:
            raise ValueError(
                f"{field} exceeds the {MAX_PERSONA_FIELD_LENGTH}-character "
                "length cap"
            )
    record = _read_persona(character)
    if record is None:
        if not text:
            return None
        record = {
            "identity": {},
            "personality": "",
            "life_story": "",
            "habit": "",
            "appearance": {},
            "social_connection": {},
        }
    if text:
        record[field] = text
    else:
        record.pop(field, None)
    character.attributes.add("persona", record)
    return text or None


def update_background(character: Any, text: str | None) -> str | None:
    """Set or clear one character's persona ``background`` field.

    Thin wrapper delegating to ``update_persona_field(character, "background",
    text)``; behaviour is identical to the pre-generalisation writer for
    current callers.
    """
    return update_persona_field(character, "background", text)


def _read_persona(character: Any) -> dict[str, Any] | None:
    from collections.abc import Mapping

    record = character.attributes.get("persona")
    if isinstance(record, Mapping):
        return dict(record)
    return None


__all__ = [
    "PERSONA_EDITABLE_FIELDS",
    "PERSONA_IMPORT_CARD_KEYS",
    "update_background",
    "update_persona_field",
]
