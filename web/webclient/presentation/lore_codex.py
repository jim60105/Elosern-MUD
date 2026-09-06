"""Exact schema-version-1 ``lore_codex`` panel, presenter, and validator.

The presenter serializes the player's discovered lore codex into an exact,
bounded read model grouped by the eight ``CODE_CATEGORIES`` in mapping order.
Each entry carries its key, display title, and canonical rendered card fields
straight from :func:`lore_card`.

Non-disclosure is absolute: undiscovered entries do not appear, counts count
only discovered entries, and empty categories disclose nothing about registry
capacity. An entry whose registry key vanished is omitted from the payload
without resetting the stored record or making the panel unavailable. A corrupt
stored record (``LoreRecordError`` from the reader) degrades the whole panel
to the registry-owned common unavailable form.

The presenter is host-independent and read-only: no room, NPC, host, schedule,
or state mutation is consulted. Bounds are mirrored by the client validator in
``web/static/webclient/js/elosern/protocol.js`` and guarded by a dual-direction
parity test.
"""

from typing import Any

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_bool,
    _require_exact_fields,
    _require_int,
    _require_str,
    _validate_identifier,
    json_byte_size,
)
from web.webclient.presentation.registry import PanelUnavailableError
from world.rules.lore_knowledge import (
    CATEGORY_LABELS,
    CODE_CATEGORIES,
    LoreCategoryError,
    LoreKeyError,
    LoreRecordError,
    list_discovered,
    lore_card,
)

LORE_CODEX_SCHEMA_VERSION = 1

# Exact shared bounds -- must stay equal in the JS validator.
LORE_CODEX_MAX_ENTRIES_PER_CATEGORY = 32
LORE_CODEX_MAX_TOTAL_ENTRIES = 256
LORE_CODEX_MAX_CARD_FIELDS = 8
LORE_CODEX_MAX_KEY_CODE_POINTS = 64
LORE_CODEX_MAX_TITLE_CODE_POINTS = 64
LORE_CODEX_MAX_LABEL_CODE_POINTS = 32
LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS = 64
LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS = 1024

# The eight codex categories in CODE_CATEGORIES mapping order.
LORE_CODEX_CATEGORIES = tuple(CODE_CATEGORIES.keys())


class LoreCodexPanelError(ProtocolValidationError):
    """The available lore_codex payload violates its exact bounded schema."""


def _reject_lone_surrogates(value: str, field: str) -> str:
    """Reject strings carrying unpaired UTF-16 surrogate code points."""
    for char in value:
        if 0xD800 <= ord(char) <= 0xDFFF:
            raise LoreCodexPanelError(f"{field} contains an unpaired surrogate code point")
    return value


def _validate_card_field(value: Any, index: int) -> dict[str, str]:
    label = f"card field[{index}]"
    _require_exact_fields(value, label, {"name", "value"}, {})
    name = _require_str(value, "name", maximum=LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS)
    if not name.strip():
        raise LoreCodexPanelError(f"{label} name must be non-empty")
    _reject_lone_surrogates(name, f"{label} name")

    val = _require_str(value, "value", maximum=LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS)
    _reject_lone_surrogates(val, f"{label} value")
    return {"name": name, "value": val}


def _validate_entry(value: Any, index: int) -> dict[str, Any]:
    label = f"lore codex entry[{index}]"
    _require_exact_fields(value, label, {"key", "title", "card"}, {})
    raw_key = _validate_identifier(value["key"], f"{label} key")
    if len(raw_key) > LORE_CODEX_MAX_KEY_CODE_POINTS:
        raise LoreCodexPanelError(f"{label} key exceeds its bound")
    _reject_lone_surrogates(raw_key, f"{label} key")

    title = _require_str(value, "title", maximum=LORE_CODEX_MAX_TITLE_CODE_POINTS)
    if not title.strip():
        raise LoreCodexPanelError(f"{label} title must be non-empty")
    _reject_lone_surrogates(title, f"{label} title")

    card = value["card"]
    if not isinstance(card, list):
        raise LoreCodexPanelError(f"{label} card must be a list")
    if len(card) > LORE_CODEX_MAX_CARD_FIELDS:
        raise LoreCodexPanelError(
            f"{label} card must hold at most {LORE_CODEX_MAX_CARD_FIELDS} fields"
        )
    validated_card = [_validate_card_field(field, idx) for idx, field in enumerate(card)]
    return {"key": raw_key, "title": title, "card": validated_card}


def _validate_category_group(value: Any, index: int, expected_key: str) -> dict[str, Any]:
    label = f"category group[{index}]"
    _require_exact_fields(value, label, {"key", "label", "count", "entries"}, {})
    key = _require_str(value, "key", maximum=LORE_CODEX_MAX_KEY_CODE_POINTS)
    if key != expected_key:
        raise LoreCodexPanelError(
            f"{label} key must be {expected_key!r}, got {key!r}"
        )

    cat_label = _require_str(value, "label", maximum=LORE_CODEX_MAX_LABEL_CODE_POINTS)
    if not cat_label.strip():
        raise LoreCodexPanelError(f"{label} label must be non-empty")
    _reject_lone_surrogates(cat_label, f"{label} label")

    entries = value["entries"]
    if not isinstance(entries, list):
        raise LoreCodexPanelError(f"{label} entries must be a list")
    if len(entries) > LORE_CODEX_MAX_ENTRIES_PER_CATEGORY:
        raise LoreCodexPanelError(
            f"{label} entries must hold at most {LORE_CODEX_MAX_ENTRIES_PER_CATEGORY} items"
        )

    count = _require_int(value, "count", minimum=0, maximum=MAX_SAFE_INTEGER)
    if count != len(entries):
        raise LoreCodexPanelError(
            f"{label} count ({count}) does not match entries length ({len(entries)})"
        )

    validated_entries = [_validate_entry(entry, idx) for idx, entry in enumerate(entries)]
    return {
        "key": key,
        "label": cat_label,
        "count": count,
        "entries": validated_entries,
    }


def validate_lore_codex(payload: Any) -> dict[str, Any]:
    """Validate one exact available ``lore_codex`` payload.

    Returns a normalized payload or raises :class:`LoreCodexPanelError`. The
    common unavailable form is NOT accepted here; the registry handles it.
    """
    _require_exact_fields(
        payload,
        "lore_codex panel",
        {"schema_version", "available", "categories", "discovered_total"},
        {},
    )
    if (
        _require_int(payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER)
        != LORE_CODEX_SCHEMA_VERSION
    ):
        raise LoreCodexPanelError("unsupported lore_codex schema_version")
    if not _require_bool(payload, "available"):
        raise LoreCodexPanelError("available must be true for the codex form")

    categories = payload["categories"]
    if not isinstance(categories, list) or len(categories) != len(LORE_CODEX_CATEGORIES):
        raise LoreCodexPanelError(
            f"categories must be a list of exactly {len(LORE_CODEX_CATEGORIES)} groups"
        )

    validated_categories = [
        _validate_category_group(group, idx, expected_key)
        for idx, (group, expected_key) in enumerate(zip(categories, LORE_CODEX_CATEGORIES))
    ]

    discovered_total = _require_int(
        payload, "discovered_total", minimum=0, maximum=MAX_SAFE_INTEGER
    )
    expected_total = sum(group["count"] for group in validated_categories)
    if discovered_total != expected_total:
        raise LoreCodexPanelError(
            f"discovered_total ({discovered_total}) does not equal sum of group counts ({expected_total})"
        )
    if discovered_total > LORE_CODEX_MAX_TOTAL_ENTRIES:
        raise LoreCodexPanelError(
            f"discovered_total exceeds the maximum of {LORE_CODEX_MAX_TOTAL_ENTRIES}"
        )

    result = {
        "schema_version": LORE_CODEX_SCHEMA_VERSION,
        "available": True,
        "categories": validated_categories,
        "discovered_total": discovered_total,
    }

    if json_byte_size(result) > MAX_CANONICAL_JSON_BYTES:
        raise LoreCodexPanelError("lore_codex payload exceeds the OOB envelope limit")
    return result


def lore_codex_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``lore_codex`` panel for the puppet.

    Host-independent and read-only: reads discovered entries through
    ``list_discovered(..., tolerant=True)`` and renders cards with
    ``lore_card``. Omits vanished entries; degrades to the unavailable form on
    corrupt records without resetting or rewriting stored data.
    """
    if context.actor is None:
        raise PanelUnavailableError

    try:
        discovered = list_discovered(context.actor, tolerant=True)
    except LoreRecordError:
        raise PanelUnavailableError from None

    by_category: dict[str, list[str]] = {cat: [] for cat in LORE_CODEX_CATEGORIES}
    for cat, key in discovered:
        if cat in by_category:
            by_category[cat].append(key)

    category_groups: list[dict[str, Any]] = []
    for cat_key in LORE_CODEX_CATEGORIES:
        entries: list[dict[str, Any]] = []
        for key in by_category[cat_key]:
            try:
                card = lore_card(cat_key, key)
            except (LoreCategoryError, LoreKeyError):
                continue
            title = card.get("display_name_zh") or card.get("key", key)
            card_fields = [{"name": name, "value": value} for name, value in card.items()]
            entries.append({"key": key, "title": title, "card": card_fields})
        category_groups.append(
            {
                "key": cat_key,
                "label": CATEGORY_LABELS[cat_key],
                "count": len(entries),
                "entries": entries,
            }
        )

    total = sum(group["count"] for group in category_groups)
    payload = {
        "schema_version": LORE_CODEX_SCHEMA_VERSION,
        "available": True,
        "categories": category_groups,
        "discovered_total": total,
    }
    return validate_lore_codex(payload)
