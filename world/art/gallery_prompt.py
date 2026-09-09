"""The closed gallery prompt-field catalog, its validation, and its fragments.

Change ``gallery-prompt-composition`` admits ONE composable character
description: a caller selects zero or more fields from the closed catalog
below, and each selected field contributes exactly one data block to the
``art.character_description`` render. The selection is normalized to the
declared order and stored verbatim on the settled card's
``requested_fields``, so a card always reports which data blocks produced it.

- ``appearance`` reuses the existing ``_appearance_fragment`` persona read
  (owned by ``world/art/subjects.py``; this module only names it here).
- ``weapon_main``, ``weapon_off``, ``armor``, and ``accessories`` contribute
  the equipped items' registry ``ItemPresentation`` visual text, read
  read-only through the gallery snapshot reader and the immutable
  ``world/lore/items.py`` registry. An empty slot, an item key absent from
  the registry, and malformed equipment storage contribute nothing and never
  raise; no mechanic, stat, price, rarity, or non-presentation registry
  field ever reaches the prompt, and no equipment state is ever written.

Free-form ``custom_prompt`` text is validated here — type, code-point bound,
control characters (line and paragraph separators included) — and
whitespace-normalized to a single line. The caller appends it through the
``{custom}`` prompt-library slot; every section's surrounding text stays in
the prompt library, never in Python constants.

The module is import-disciplined like the rest of the deterministic art
path: no ``world.ai``, ``ollama``, ``llm_client``, or
``world.art.connectivity`` import, and no write to any entity state. The
``world.art.gallery`` snapshot reader is imported lazily inside
``equipment_fragment`` because ``gallery.py`` imports ``world.art.subjects``
at module level and ``subjects.py`` imports this module.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import unicodedata

from world.lore.items import ITEM_REGISTRY

# The one closed, ordered gallery-field catalog. The declared order IS the
# composition order: a request's contributions are always assembled in this
# order regardless of how the caller listed its selection, and the normalized
# selection recorded on the card follows it. The equipment tail mirrors
# ``world/art/gallery.py::SLOT_ORDER`` so slot and field vocabularies agree.
GALLERY_PROMPT_FIELDS: tuple[str, ...] = (
    "appearance",
    "weapon_main",
    "weapon_off",
    "armor",
    "accessories",
)

# The four equipment field ids, in declared order.
EQUIPMENT_FIELDS: tuple[str, ...] = GALLERY_PROMPT_FIELDS[1:]

# The declared code-point bound on free-form custom prompt text. Registry
# summaries are bounded at 128 code points each; the free-text field gets its
# own explicit bound so no unbounded request can reach the pipeline.
CUSTOM_PROMPT_MAX = 512


class GalleryPromptError(ValueError):
    """Raised for every field-catalog or free-text violation at the seam."""


def _is_selection_container(value: object) -> bool:
    """True for a genuine sequence selection (not a str/bytes/Mapping).

    A plain string is iterable, so accepting it would silently validate its
    characters as field ids; the rejected shapes are strings, byte blobs, and
    mappings. Any other iterable (list, tuple, Evennia's ``_SaverList``) is a
    legal container whose elements still face the per-id rules below.
    """
    if isinstance(value, (str, bytes, bytearray)) or isinstance(value, Mapping):
        return False
    return isinstance(value, Iterable)


def validate_fields(fields: object) -> tuple[str, ...]:
    """Return the selection normalized to the declared catalog order.

    Rejects a non-selection container, a non-string id, an id absent from the
    closed catalog, and a duplicated id — each with the typed
    ``GalleryPromptError`` — before any caller renders or writes anything. An
    empty selection is legal (a description of the base identity alone).
    """
    if not _is_selection_container(fields):
        raise GalleryPromptError(
            "field selection must be a sequence of field-id strings"
        )
    selected: set[str] = set()
    for field in fields:
        if not isinstance(field, str) or not field:
            raise GalleryPromptError(f"field id must be a non-empty string, got {field!r}")
        if field not in GALLERY_PROMPT_FIELDS:
            raise GalleryPromptError(f"unknown gallery prompt field {field!r}")
        if field in selected:
            raise GalleryPromptError(f"duplicate gallery prompt field {field!r}")
        selected.add(field)
    return tuple(field for field in GALLERY_PROMPT_FIELDS if field in selected)


def _has_control_character(text: str) -> bool:
    """True for any Cc/Cf/Cs/Co/Cn character or non-space separator.

    ``str.isprintable()`` already rejects every ``C*`` category and the line
    (U+2028) and paragraph (U+2029) separators; the explicit category test
    keeps the guarantee independent of that implementation detail. Ordinary
    spaces (category Zs) stay legal and are folded by normalization.
    """
    return any(
        not char.isprintable() or unicodedata.category(char)[0] == "C"
        for char in text
    )


def validate_custom_prompt(text: object) -> str:
    """Return the accepted free text as one normalized single line.

    Rejects non-text, text over the declared code-point bound, and text
    carrying any control character (including line and paragraph separators)
    with the typed ``GalleryPromptError``. Accepted text is whitespace-
    normalized to a single line and otherwise kept verbatim; an empty or
    whitespace-only value is a legal no-op.
    """
    if not isinstance(text, str):
        raise GalleryPromptError("custom_prompt must be text")
    if len(text) > CUSTOM_PROMPT_MAX:
        raise GalleryPromptError(
            f"custom_prompt must be at most {CUSTOM_PROMPT_MAX} code points"
        )
    if _has_control_character(text):
        raise GalleryPromptError("custom_prompt must not contain control characters")
    return " ".join(text.split())


def equipment_fragment(entity, fields: object) -> str:
    """The selected equipment slots' registry presentation text as one fragment.

    Reads the entity's four-slot snapshot through the tolerant, write-free
    ``world/art/gallery.py::snapshot_for`` (malformed storage closes to the
    empty snapshot) and looks each item key up in the immutable
    ``ITEM_REGISTRY``, contributing exactly its ``presentation.summary_zh``.
    Slots contribute in the declared catalog order; accessories (already
    sorted by the snapshot reader) are re-sorted defensively so the fragment
    can never depend on storage iteration order. An empty slot, an
    unregistered key, and malformed storage contribute nothing and never
    raise. The fragment carries its own leading newline — the same
    self-framed convention as ``_appearance_fragment`` — so an empty
    contribution leaves the template sentence byte-identical.
    """
    from world.art import gallery as gallery_api

    snapshot = gallery_api.snapshot_for(entity)
    selected = set(fields or ())
    lines: list[str] = []
    for slot in EQUIPMENT_FIELDS:
        if slot not in selected:
            continue
        value = snapshot.get(slot)
        if not value:
            continue
        if slot == "accessories":
            keys = sorted(value)
        else:
            keys = (value,)
        for key in keys:
            definition = ITEM_REGISTRY.get(key)
            if definition is None:
                continue
            lines.append(definition.presentation.summary_zh)
    if not lines:
        return ""
    return "\n" + "\n".join(lines)
