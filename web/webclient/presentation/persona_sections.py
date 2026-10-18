"""Shared persona-prose and intimate-state wire sections.

Both the ``character`` panel and the ``party_member`` panel publish the same
display-only prose and intimate vocabulary, so the exact validators and the
serializer live here once. ``character`` re-exports the public names it owned
before the extraction; the next change removes its sections without
duplicating validation.

The persona section is presentation data and is never used to infer any
mechanical value. The structural persona keys (``identity``, ``appearance``,
``social_connection``) never appear. The intimate section is ``null`` when the
entity has no sexual-state record at all.

Both validators accept an ``error`` class so each panel keeps raising its own
panel-specific subclass (``CharacterPanelError`` and
``PartyMemberPanelError``) while the shared shape rules stay in one place.
"""

from typing import Any

from web.webclient.presentation.protocol import (
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_exact_fields,
    _require_int,
    _require_str,
)
from world.lore.sexual_vocab import (
    AROUSAL_LEVELS,
    CLIMAX_PHASE_LEVELS,
    EXPOSURE_LEVELS,
    SHAME_LEVELS,
    WETNESS_LEVELS,
)
from world.rules.character_creation import (
    MAX_PERSONA_FIELD_LENGTH,
    PERSONA_PROSE_KEYS,
)

#: The display-only persona prose bound mirrors the persona-field cap
#: (``world.rules.character_creation.MAX_PERSONA_FIELD_LENGTH``); the parity
#: contract pins the JS validator to this same number.
MAX_PERSONA_FIELD_CODE_POINTS = MAX_PERSONA_FIELD_LENGTH
#: The exact four display-only persona prose keys, in drawer display order
#: (personality, life_story, habit, background). The panel sections and the JS
#: validator mirror this tuple.
PERSONA_PROSE_FIELDS = (*PERSONA_PROSE_KEYS, "background")
#: The intimate level words are bounded like every other wire label.
MAX_INTIMATE_LEVEL_CODE_POINTS = 128
#: The exact intimate section keys, in wire order.
INTIMATE_FIELDS = (
    "arousal",
    "wetness",
    "shame",
    "exposure",
    "climax_phase",
    "climax_today",
)


def serialize_persona(entity: Any) -> dict[str, Any]:
    """Serialize an entity's four persona prose fields (nullable).

    Non-string and blank values degrade to ``null``; a non-empty string is
    returned verbatim and the validator trims it. An entity without a persona
    record renders all-null, never a placeholder.
    """
    record = getattr(entity, "persona", {})
    persona: dict[str, Any] = {}
    for field in PERSONA_PROSE_FIELDS:
        value = record.get(field) if hasattr(record, "get") else None
        if value is not None and not isinstance(value, str):
            value = None
        if value is not None and not value.strip():
            value = None
        persona[field] = value
    return persona


def validate_persona(
    value: Any, *, error: type[ProtocolValidationError] = ProtocolValidationError
) -> dict[str, Any]:
    """Validate the display-only ``persona`` section of a panel payload."""
    _require_exact_fields(value, "persona", set(PERSONA_PROSE_FIELDS), {})
    cleaned: dict[str, Any] = {}
    for field in PERSONA_PROSE_FIELDS:
        entry = value[field]
        if entry is None:
            cleaned[field] = None
            continue
        if not isinstance(entry, str):
            raise ProtocolValidationError(f"persona.{field} must be text or null")
        text = entry.strip()
        if not text:
            cleaned[field] = None
            continue
        if sum(1 for _ in text) > MAX_PERSONA_FIELD_CODE_POINTS:
            raise error(f"persona.{field} exceeds its bound")
        cleaned[field] = text
    return cleaned


def _validate_intimate_level(
    value: Any,
    field: str,
    vocabulary: tuple[str, ...],
    *,
    error: type[ProtocolValidationError],
) -> str:
    level = _require_str(value, field, maximum=MAX_INTIMATE_LEVEL_CODE_POINTS)
    if level not in vocabulary:
        raise error(f"intimate.{field} is not a member of its fixed vocabulary")
    return level


def validate_intimate(
    value: Any, *, error: type[ProtocolValidationError] = ProtocolValidationError
) -> dict[str, Any] | None:
    """Validate the nullable ``intimate`` section of a panel payload."""
    if value is None:
        return None
    _require_exact_fields(value, "intimate", set(INTIMATE_FIELDS), {})
    return {
        "arousal": _validate_intimate_level(
            value, "arousal", AROUSAL_LEVELS, error=error
        ),
        "wetness": _validate_intimate_level(
            value, "wetness", WETNESS_LEVELS, error=error
        ),
        "shame": _validate_intimate_level(value, "shame", SHAME_LEVELS, error=error),
        "exposure": _validate_intimate_level(
            value, "exposure", EXPOSURE_LEVELS, error=error
        ),
        "climax_phase": _validate_intimate_level(
            value, "climax_phase", CLIMAX_PHASE_LEVELS, error=error
        ),
        "climax_today": _require_int(
            value, "climax_today", minimum=0, maximum=MAX_SAFE_INTEGER
        ),
    }


def serialize_intimate(view: Any) -> dict[str, Any] | None:
    """Serialize the read model's intimate view into the payload section."""
    if view is None:
        return None
    return {
        "arousal": view.arousal,
        "wetness": view.wetness,
        "shame": view.shame,
        "exposure": view.exposure,
        "climax_phase": view.climax_phase,
        "climax_today": view.climax_today,
    }


__all__ = [
    "INTIMATE_FIELDS",
    "MAX_INTIMATE_LEVEL_CODE_POINTS",
    "MAX_PERSONA_FIELD_CODE_POINTS",
    "PERSONA_PROSE_FIELDS",
    "serialize_intimate",
    "serialize_persona",
    "validate_intimate",
    "validate_persona",
]
