"""Deterministic authoring rules for NPC identity text.

Pure validation only — no state, no I/O, no logging, no display composition.
Every authored NPC title and name write path validates through the single
rules below; presentation surfaces render the plain authored name and never
read a title.

The NPC title is author-supplied, single-line plain text written once at
creation time by an authored path (import loader, blueprint materialization,
registry-backed host or examiner) and immutable at runtime. There is no
title-specific write API: the value only ever arrives through the creation
paths, each of which validates with :func:`validate_npc_title` before
assigning. Generic Evennia attribute access (``entity.db.npc_title = ...``)
is framework infrastructure, deliberately outside that guarantee; tests seed
malformed stored state through it, which is inert because no reader consumes
the attribute.
"""

import unicodedata
from collections.abc import Sequence
from typing import Any

# Upper bound, in code points, of the validator's stripped title form. Names
# are separately bounded by ``MAX_ENTITY_KEY_LENGTH`` (64), so an authored
# name always round-trips through the entity-key bound.
MAX_NPC_TITLE_CODE_POINTS = 32

# Upper bound, in code points, of the validator's stripped name form. It
# matches the entity-key bound the authored name becomes (MAX_ENTITY_KEY_LENGTH
# is 64), so a spawned NPC's key always round-trips through the name rule.
MAX_NPC_NAME_CODE_POINTS = 64


def live_key_taken_by_other(entity: Any) -> bool:
    """Read the entire persisted object namespace, excluding this entity."""
    from evennia.objects.models import ObjectDB

    return ObjectDB.objects.filter(db_key=entity.key).exclude(pk=entity.pk).exists()


class NPCTitleError(ValueError):
    """A proposed NPC title violates the single-line plain-text contract."""


class NPCNameError(ValueError):
    """A proposed NPC name violates the entity-key-safe text contract."""


def validate_npc_title(value: Any) -> str:
    """Normalize and validate an authored NPC title, returning the stripped form.

    Surrounding whitespace (of any kind, U+3000 included) is normalized away;
    every rejection decision is made on that stripped form. Raises
    :class:`NPCTitleError` with a stable English identifier for: a non-``str``
    value (``bool`` is not ``str``), an empty stripped form, a stripped form
    longer than :data:`MAX_NPC_TITLE_CODE_POINTS` code points, any internal
    whitespace (the full-width space U+3000 included, as it never appears in
    an authored single-line title), any control or non-printable character,
    and the Evennia markup delimiter ``|``.

    Check order and message style follow ``character_creation._validate_name``.
    """
    if not isinstance(value, str):
        raise NPCTitleError("npc title must be text")
    title = value.strip()
    if not title:
        raise NPCTitleError("npc title must be non-empty after stripping")
    if len(title) > MAX_NPC_TITLE_CODE_POINTS:
        raise NPCTitleError(
            f"npc title must be at most {MAX_NPC_TITLE_CODE_POINTS} code points"
        )
    if any(char.isspace() for char in title):
        raise NPCTitleError("npc title must not contain whitespace")
    if any(
        unicodedata.category(char).startswith("C") or not char.isprintable()
        for char in title
    ):
        raise NPCTitleError("npc title contains a control character")
    if "|" in title:
        raise NPCTitleError("npc title contains an Evennia markup delimiter")
    return title


def validate_npc_name(value: Any) -> str:
    """Normalize and validate an authored NPC name, returning the stripped form.

    The authored name is the NPC's entity key on every authored creation path
    (blueprint materialization, registry-backed host or examiner), so the rule
    is the title rule minus its strictest clause: surrounding whitespace (of
    any kind, U+3000 included) is normalized away and every rejection decision
    is made on the stripped form; a non-``str`` value, an empty stripped form,
    a stripped form longer than :data:`MAX_NPC_NAME_CODE_POINTS` code points,
    any control or non-printable character, and the Evennia markup delimiter
    ``|`` all raise :class:`NPCNameError` with a stable English identifier.

    Unlike :func:`validate_npc_title`, ordinary whitespace INSIDE the name is
    allowed (multi-word names are legal entity keys today; tightening them
    here would rewrite the pre-existing key contract for no identity-safety
    gain). The full-width space U+3000 is the one rejected whitespace: an
    authored name never carries it.
    """
    if not isinstance(value, str):
        raise NPCNameError("npc name must be text")
    name = value.strip()
    if not name:
        raise NPCNameError("npc name must be non-empty after stripping")
    if len(name) > MAX_NPC_NAME_CODE_POINTS:
        raise NPCNameError(
            f"npc name must be at most {MAX_NPC_NAME_CODE_POINTS} code points"
        )
    if "\u3000" in name:
        # Checked before the control scan: Python reports U+3000 as
        # non-printable (category Zs), and the full-width-space rejection
        # carries its own stable identifier instead of the generic
        # control-character one.
        raise NPCNameError("npc name contains the identity separator")
    if any(
        unicodedata.category(char).startswith("C") or not char.isprintable()
        for char in name
    ):
        raise NPCNameError("npc name contains a control character")
    if "|" in name:
        raise NPCNameError("npc name contains an Evennia markup delimiter")
    return name


def validate_unique_npc_names(entries: Sequence[tuple[str, str]]) -> None:
    """Reject authored NPC names that repeat across labeled registry rows.

    ``entries`` is a sequence of ``(label, name)`` pairs, one per authored NPC
    identity across the shop, guild-branch, and guild-rank registries (labels
    are registry-qualified keys for the error message). Names are compared in
    their already-validated (stripped) forms; any duplicate raises
    :class:`NPCNameError` naming both holders. Pure and stdlib-only so every
    owning lore module can run it at import time and tests can call it with
    explicit rows.
    """
    seen: dict[str, str] = {}
    for label, name in entries:
        if name in seen:
            raise NPCNameError(
                f"npc name {name!r} authored by {label} duplicates {seen[name]}"
            )
        seen[name] = label
