"""Exact schema-version-3 ``roster`` panel and presenter (webclient-character-roster).

Each row's ``portrait`` IS the complete canonical artwork descriptor
(``world.art.descriptors``) — the same one shape the art panel's catalog
entries carry, resolved by the same one production enumerator
(``world.art.presenter.describe_entity``) — so a roster row can never lose a
terminal, a reached fault or its independent generation truth to a field-copy
omission. It is validated by the one shared descriptor validator
(``web.webclient.presentation.artwork.validate_artwork``), and an old flat
portrait object fails the exact-key check rather than being adapted.

A character still pending creation carries the EMPTY canonical descriptor: no
image attempt (so no URL), no generated subject key and no terminal, because
activation is the only thing that establishes a portrait policy. Every
activated character's row is the full descriptor, whether or not any real
image resolves and regardless of which room the character stands in.

Discloses the account-level character roster read model: owned characters in
ascending identity order, each with its identity, display name, live puppet flag,
creation pending flag, and resolved portrait catalog entry. Also delivers
account capacity and switch-lock facts.

The panel is deliberately UNGATED on ``creation_pending``:
A player who abandons a character creation wizard mid-way must still be able
to switch back to another character on the account, which requires the roster
panel to remain available in creation mode as well as exploration, combat,
and dialogue.
"""

from typing import Any

from web.webclient.presentation.affordances import MAX_DISPLAY_NAME_CODE_POINTS
from web.webclient.presentation.artwork import validate_artwork
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_bool,
    _require_exact_fields,
    _require_int,
    _require_str,
    json_byte_size,
)
from web.webclient.presentation.registry import PanelUnavailableError
from world.art import descriptors
from world.art.presenter import describe_entity
from world.rules.account_roster import (
    MAX_ROSTER_ROWS,
    ROSTER_LOCK_REASON,
    AccountRosterError,
    build_account_roster,
)

ROSTER_SCHEMA_VERSION = 3

# Shared display-name code-point bound.
MAX_ROSTER_NAME = MAX_DISPLAY_NAME_CODE_POINTS

class RosterPanelError(ProtocolValidationError):
    """The available roster payload violates its exact bounded schema."""


def _validate_roster_portrait(value: Any) -> dict[str, Any]:
    """Validate one row's portrait: the complete canonical descriptor, verbatim.

    The same one shared descriptor validator the art catalog entries use, so
    the two surfaces cannot drift and a row that still carries the retired flat
    image fields fails the exact-key check rather than being adapted.
    """
    return validate_artwork(value)


def _validate_character_row(value: Any, index: int) -> dict[str, Any]:
    _require_exact_fields(
        value,
        f"roster character row {index}",
        {
            "identity",
            "name",
            "current",
            "pending",
            "portrait",
        },
        {},
    )
    identity = _require_int(
        value, "identity", minimum=1, maximum=MAX_SAFE_INTEGER
    )
    name = _require_str(value, "name", maximum=MAX_ROSTER_NAME)
    if not name.strip():
        raise RosterPanelError(f"character row {index} name must be non-empty")
    current = _require_bool(value, "current")
    pending = _require_bool(value, "pending")
    portrait = _validate_roster_portrait(value["portrait"])

    return {
        "identity": identity,
        "name": name,
        "current": current,
        "pending": pending,
        "portrait": portrait,
    }


def validate_roster(payload: Any) -> dict[str, Any]:
    """Validate one exact available ``roster`` payload.

    Returns a normalized payload or raises :class:`RosterPanelError`. The common
    unavailable form is NOT accepted here; the registry handles it.
    """
    _require_exact_fields(
        payload,
        "roster panel",
        {
            "schema_version",
            "available",
            "characters",
            "max_characters",
            "can_create",
            "switch_locked",
            "lock_reason",
        },
        {},
    )
    schema_version = _require_int(
        payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER
    )
    if schema_version != ROSTER_SCHEMA_VERSION:
        raise RosterPanelError("unsupported roster schema_version")

    if not _require_bool(payload, "available"):
        raise RosterPanelError("available must be true for the roster form")

    characters_raw = payload["characters"]
    if not isinstance(characters_raw, list):
        raise RosterPanelError("characters must be a list")
    if len(characters_raw) > MAX_ROSTER_ROWS:
        raise RosterPanelError(
            f"characters list must hold at most {MAX_ROSTER_ROWS} entries"
        )

    last_identity = 0
    characters: list[dict[str, Any]] = []
    current_count = 0
    for idx, row in enumerate(characters_raw, start=1):
        validated_row = _validate_character_row(row, idx)
        ident = validated_row["identity"]
        if ident <= last_identity:
            raise RosterPanelError(
                f"character identities must be strictly ascending, got {ident} after {last_identity}"
            )
        last_identity = ident
        if validated_row["current"]:
            current_count += 1
        characters.append(validated_row)

    # Invariant: exactly one row must be current.
    if current_count != 1:
        raise RosterPanelError(
            f"roster characters must contain exactly one current character, found {current_count}"
        )

    max_characters = _require_int(
        payload, "max_characters", minimum=1, maximum=MAX_SAFE_INTEGER
    )
    can_create = _require_bool(payload, "can_create")
    switch_locked = _require_bool(payload, "switch_locked")

    # Strict reciprocal lock/reason rule.
    lock_reason = payload["lock_reason"]
    if switch_locked:
        if lock_reason != ROSTER_LOCK_REASON:
            raise RosterPanelError(
                f"lock_reason must be {ROSTER_LOCK_REASON!r} when switch_locked is True"
            )
    else:
        if lock_reason is not None:
            raise RosterPanelError("lock_reason must be None when switch_locked is False")

    result = {
        "schema_version": ROSTER_SCHEMA_VERSION,
        "available": True,
        "characters": characters,
        "max_characters": max_characters,
        "can_create": can_create,
        "switch_locked": switch_locked,
        "lock_reason": lock_reason,
    }

    # Closing byte-budget guard.
    if json_byte_size(result) > MAX_CANONICAL_JSON_BYTES:
        raise RosterPanelError("roster payload exceeds the OOB envelope limit")

    return result


def _row_portrait(entity: Any, identity: int, pending: bool) -> dict[str, Any]:
    """One roster row's complete canonical portrait descriptor.

    A creation-pending character carries the EMPTY canonical descriptor: it has
    no named portrait policy (activation is what writes one), so it exposes no
    image attempt, no generated subject key and no terminal — a truthful
    no-portrait row rather than a silhouette standing in for an uncreated
    character.

    Every other row is the subject's own complete descriptor from the one
    production enumerator, resolved regardless of room presence and regardless
    of whether any real image exists. An owned identity whose database row no
    longer resolves keeps its admitted position with the empty descriptor
    instead of failing the panel.
    """
    if pending or entity is None:
        return descriptors.descriptor(
            subject_id=str(int(identity)),
            generation_subject=None,
            generation_state=None,
            attempts=[],
            terminal_payload=None,
            retention_sources=[],
        )
    return describe_entity(entity)


def roster_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``roster`` panel for the puppeted session.

    Deliberately ungated on ``creation_pending`` so a player who abandoned a
    creation wizard mid-way can switch back to another character on the account.
    """
    from evennia.objects.models import ObjectDB

    actor = context.actor
    try:
        view = build_account_roster(actor)
    except AccountRosterError:
        raise PanelUnavailableError

    character_rows: list[dict[str, Any]] = []
    for char_view in view.characters:
        entity = ObjectDB.objects.filter(id=int(char_view.identity)).first()
        character_rows.append(
            {
                "identity": char_view.identity,
                "name": char_view.name,
                "current": char_view.current,
                "pending": char_view.pending,
                "portrait": _row_portrait(entity, char_view.identity, char_view.pending),
            }
        )

    return validate_roster(
        {
            "schema_version": ROSTER_SCHEMA_VERSION,
            "available": True,
            "characters": character_rows,
            "max_characters": view.max_characters,
            "can_create": view.can_create,
            "switch_locked": view.switch_locked,
            "lock_reason": view.lock_reason,
        }
    )


__all__ = [
    "MAX_ROSTER_NAME",
    "MAX_ROSTER_ROWS",
    "ROSTER_LOCK_REASON",
    "ROSTER_SCHEMA_VERSION",
    "RosterPanelError",
    "_row_portrait",
    "roster_presenter",
    "validate_roster",
]
