"""Read-only persona handler over an entity's verbatim persona record.

``PersonaStore`` reads the opaque persona dict stored verbatim on
``entity.db.persona`` by ``world/imports/loader.py`` (the only writer) and
exposes keyed retrieval plus bounded prompt-block flattening over the
``personality``, ``life_story``, and ``habit`` fields. The handler carries no
write API, imports no state-mutating module, and never touches traits,
attributes beyond the single persona record, or the world clock. A missing,
malformed, or content-free record always degrades to ``None`` rather than
raising, so a persona can never break a look or a conversation.
"""

from collections.abc import Mapping
from typing import Any

# Hard bounds for LLM-bound persona text, following the project's ``_cap_string``
# idiom for deterministic truncation with an explicit marker. Callers may
# override both bounds and the flattened field set at the call site.
FIELD_LIMIT = 600
BLOCK_LIMIT = 2000

_TRUNCATION_MARKER = "…"

# Canonical Traditional Chinese labels for the three flattened fields. Unknown
# fields fall back to their raw key as the label.
_FIELD_LABELS = {
    "personality": "性格：",
    "life_story": "人生經歷：",
    "habit": "習慣：",
}


class PersonaStore:
    """Read-only handler over an entity's verbatim persona record.

    Reads resolve against ``entity.db.persona`` and never persist anything; the
    import loader remains the only writer.
    """

    def __init__(
        self,
        entity: Any,
        *,
        field_limit: int = FIELD_LIMIT,
        block_limit: int = BLOCK_LIMIT,
    ) -> None:
        for name, limit in (("field_limit", field_limit), ("block_limit", block_limit)):
            if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
                raise ValueError(f"{name} must be a positive integer")
        self._entity = entity
        self._field_limit = field_limit
        self._block_limit = block_limit

    def _cap(self, value: str) -> str:
        if len(value) <= self._field_limit:
            return value
        return value[: self._field_limit - len(_TRUNCATION_MARKER)] + _TRUNCATION_MARKER

    def get(self, field: str) -> Any | None:
        """Return ``field``'s stored value verbatim, or ``None`` when absent.

        A missing record, a non-mapping record, or a missing key all return
        ``None``; this never raises. Evennia materializes stored dicts as
        mapping wrappers, so any mapping counts as a record.
        """
        record = self._entity.db.persona
        if not isinstance(record, Mapping):
            return None
        return record.get(field)

    def flatten(
        self, fields: tuple[str, ...] = ("personality", "life_story", "habit")
    ) -> str | None:
        """Return one labeled prompt block for the present fields, or ``None``.

        Each present non-empty string field produces a labeled section in the
        declared field order (e.g. ``性格：…`` / ``人生經歷：…`` / ``習慣：…``),
        each field string capped and the combined block capped at a total
        bound. A missing record, a non-mapping record, or a record with none
        of the requested fields yields ``None``; this never raises.
        """
        sections = []
        for field in fields:
            value = self.get(field)
            if not isinstance(value, str) or not value:
                continue
            label = _FIELD_LABELS.get(field, f"{field}：")
            sections.append(f"{label}{self._cap(value)}")
        if not sections:
            return None
        block = "\n".join(sections)
        if len(block) <= self._block_limit:
            return block
        return block[: self._block_limit - len(_TRUNCATION_MARKER)] + _TRUNCATION_MARKER
