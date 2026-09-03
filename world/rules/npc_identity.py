"""The single composition point for NPC full identity (npc-title-identity-core).

Deterministic core: pure validation and pure reads only — no state, no I/O,
and no logging. Every presentation surface that shows 「姓名　稱號」 delegates
here; the rule exists nowhere else.

The NPC title is author-supplied, single-line plain text written once at
creation time by an authored path (import loader, blueprint materialization,
registry-backed host or examiner) and immutable at runtime. There is no
title-specific write API: the value only ever arrives through the creation
paths, each of which validates with :func:`validate_npc_title` before
assigning. Generic Evennia attribute access (``entity.db.npc_title = ...``)
is framework infrastructure, deliberately outside that guarantee; tests seed
malformed stored state through it, and :func:`npc_display_name` degrades such
state — corrupt strings included (markup delimiters, internal whitespace,
control characters) — and even a title accessor that raises, to the plain
name instead of raising: a stored string is only rendered when it satisfies
the validator's content rules, so no display surface can ever emit Evennia
markup or an ambiguous identity from a damaged row. Length is deliberately
not part of that render filter: an overlong stored title stays a documented
degraded state that the display bounds truncate.
"""

import unicodedata
from typing import Any

# The full-width separator between the name and the title (「姓名　稱號」).
# Held here on purpose: the player title system (``world.rules.titles``) owns
# its own separator, and the two systems must never share an import edge
# (design §2 — zero coupling with the player title machinery).
_FULL_WIDTH_SPACE = "\u3000"

# Upper bound, in code points, of the validator's stripped title form. Names
# are separately bounded by ``MAX_ENTITY_KEY_LENGTH`` (64), so the composed
# identity stays inside the webclient display-name bound (128).
MAX_NPC_TITLE_CODE_POINTS = 32


class NPCTitleError(ValueError):
    """A proposed NPC title violates the single-line plain-text contract."""


def validate_npc_title(value: Any) -> str:
    """Normalize and validate an authored NPC title, returning the stripped form.

    Surrounding whitespace (of any kind, U+3000 included) is normalized away;
    every rejection decision is made on that stripped form. Raises
    :class:`NPCTitleError` with a stable English identifier for: a non-``str``
    value (``bool`` is not ``str``), an empty stripped form, a stripped form
    longer than :data:`MAX_NPC_TITLE_CODE_POINTS` code points, any internal
    whitespace (the composer reserves U+3000 as its separator), any control
    or non-printable character, and the Evennia markup delimiter ``|``.

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


def _title_is_plain_text(title: str) -> bool:
    """True when a stripped stored title is safe to render.

    Mirrors the validator's content rules (internal whitespace, control or
    non-printable characters, and the markup delimiter all fail) minus the
    length bound, which the render path deliberately tolerates: an overlong
    row is a documented degraded state the display bounds truncate, while
    rendering corrupt content would put markup or a separator-ambiguous
    identity on screen. Keep in sync with :func:`validate_npc_title`.
    """
    if any(char.isspace() for char in title):
        return False
    if any(
        unicodedata.category(char).startswith("C") or not char.isprintable()
        for char in title
    ):
        return False
    return "|" not in title


def _plain_key(entity: Any) -> str:
    """The entity's plain key, or ``""`` when even that read fails.

    A corrupt or custom ``key`` accessor must not take down a display
    surface either; the composer then returns an empty name, which every
    surface bounds and renders without error.
    """
    try:
        key = getattr(entity, "key", None)
    except Exception:  # observability: ignore R2: never-raise display reader; a corrupt key accessor degrades to an empty plain name instead of failing the surface
        return ""
    if key is None:
        return ""
    try:
        return str(key)
    except Exception:  # observability: ignore R2: never-raise display reader; a key whose __str__ raises degrades to an empty plain name
        return ""


def npc_title_value(entity: Any) -> str:
    """The entity's stored title, or ``""`` for everything else.

    ``""`` covers every degraded case: not an ``NPC`` (players and monsters
    never compose — design §3.2 invariant 4), a missing or empty title, an
    accessor that raises, stored content that is not a string, and a string
    whose stripped form violates the validator's content rules — such a row
    could never have come from an authored path, and rendering it would put
    Evennia markup or a separator-ambiguous identity on screen. Length is
    deliberately NOT filtered here: an overlong stored title composes and is
    truncated by the display bounds (design §3.4), unlike content corruption.
    The read is pure: the property is declared ``autocreate=False``, so
    touching it never persists a storage row.
    """
    # Deferred import: world/rules modules must not import typeclasses at
    # module scope (Evennia import order); same-file precedent is
    # ``world.rules.party.live_companion_ids``.
    from typeclasses.npcs import NPC

    if not isinstance(entity, NPC):
        return ""
    try:
        stored = entity.npc_title
    except Exception:  # observability: ignore R2: never-raise display reader; a broken accessor must degrade to the plain name on every surface rather than fail them
        return ""
    if not isinstance(stored, str):
        return ""
    title = stored.strip()
    return title if title and _title_is_plain_text(title) else ""


def npc_display_name(entity: Any) -> str:
    """Compose 「姓名　稱號」 when a title is present, else the plain key.

    Never raises and never writes: malformed stored state degrades to the
    plain key so one broken title field cannot make a presentation surface
    unavailable. Stored-value corruption is decided by explicit value tests;
    accessor failure is contained by the two narrow safe-read boundaries in
    :func:`npc_title_value` and :func:`_plain_key`. The module never logs, so
    each boundary carries a reasoned observability exemption comment.
    """
    title = npc_title_value(entity)
    key = _plain_key(entity)
    if not title:
        return key
    if not key:
        # A title alone would render 「　稱號」 — an identity whose leading
        # separator makes it ambiguous. No readable name means no composed
        # identity at all.
        return ""
    return f"{key}{_FULL_WIDTH_SPACE}{title}"
