"""Deterministic post-activation writer for a character's persona ``background``.

This module is the single post-activation writer of a player character's
persona ``background`` field (creation-persona-persistence D4). It validates
the shared persona-field bound, creates the import-card-shaped persona record
when none exists, preserves every existing persona key (including unknown keys)
while writing or clearing only ``background``, and never touches traits,
identity attributes, the three prose fields, or the world clock.

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


def update_background(character: Any, text: str | None) -> str | None:
    """Set or clear one character's persona ``background`` field.

    ``text`` is trimmed and bounded to ``MAX_PERSONA_FIELD_LENGTH``; ``None``
    or a blank value explicitly clears the field by removing the key. When the
    character has no persona record, the import-card-shaped record is created
    first. Every existing persona key (including unknown keys) is preserved.
    Returns the persisted background (``None`` when cleared).
    """
    if text is not None:
        if not isinstance(text, str):
            raise ValueError("background must be text")
        text = text.strip()
        if len(text) > MAX_PERSONA_FIELD_LENGTH:
            raise ValueError(
                f"background exceeds the {MAX_PERSONA_FIELD_LENGTH}-character length cap"
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
        record["background"] = text
    else:
        record.pop("background", None)
    character.attributes.add("persona", record)
    return text or None


def _read_persona(character: Any) -> dict[str, Any] | None:
    from collections.abc import Mapping

    record = character.attributes.get("persona")
    if isinstance(record, Mapping):
        return dict(record)
    return None


__all__ = [
    "PERSONA_IMPORT_CARD_KEYS",
    "update_background",
]
