"""Exact schema-version-1 ``roster`` panel and presenter (webclient-character-roster).

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
from web.webclient.presentation.art import (
    MAX_ALT,
    MAX_PLACEHOLDER_LABEL,
    MAX_STATUS,
    MAX_SUBJECT_KEY,
    PLACEHOLDER_KINDS,
    _placeholder_for,
)
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
from world.art.presenter import resolve_character
from world.rules.account_roster import (
    MAX_ROSTER_ROWS,
    ROSTER_LOCK_REASON,
    AccountRosterError,
    build_account_roster,
)

ROSTER_SCHEMA_VERSION = 1

# Shared display-name code-point bound.
MAX_ROSTER_NAME = MAX_DISPLAY_NAME_CODE_POINTS

PORTRAIT_STATUSES = frozenset({"missing", "pending", "failed", "done"})


class RosterPanelError(ProtocolValidationError):
    """The available roster payload violates its exact bounded schema."""


def _validate_roster_placeholder(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    _require_exact_fields(value, "roster placeholder", {"kind", "label"}, {})
    kind = value["kind"]
    if kind not in PLACEHOLDER_KINDS:
        raise RosterPanelError("placeholder kind is not a stable value")
    label = _require_str(value, "label", maximum=MAX_PLACEHOLDER_LABEL)
    if not label.strip():
        raise RosterPanelError("placeholder label must be non-empty")
    return {"kind": kind, "label": label}


def _validate_roster_portrait(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "roster portrait",
        {
            "subject_key",
            "status",
            "url",
            "aspect_ratio",
            "alt",
            "placeholder",
        },
        {},
    )
    subject_key = value["subject_key"]
    if subject_key is not None:
        subject_key = _require_str(value, "subject_key", maximum=MAX_SUBJECT_KEY)
        if not subject_key.strip():
            raise RosterPanelError("portrait subject_key must be non-empty")

    status = value["status"]
    if status is not None:
        status = _require_str(value, "status", maximum=MAX_STATUS)
        if status not in PORTRAIT_STATUSES:
            raise RosterPanelError("portrait status is not a stable value")

    url = value["url"]
    if url is not None:
        url = _require_str(value, "url", maximum=MAX_SUBJECT_KEY)
        if not url.startswith("/art/"):
            raise RosterPanelError("portrait url must be a same-origin media URL")

    aspect_ratio = value["aspect_ratio"]
    if aspect_ratio is not None:
        aspect_ratio = _require_str(value, "aspect_ratio", maximum=16)
        if aspect_ratio != "3:4":
            raise RosterPanelError("portrait aspect_ratio must be 3:4")

    alt = _require_str(value, "alt", maximum=MAX_ALT)
    if not alt.strip():
        raise RosterPanelError("portrait alt must be non-empty")

    placeholder = _validate_roster_placeholder(value["placeholder"])

    # Cross-field integrity checks mirroring art panel catalog entries.
    if url is not None and placeholder is not None:
        raise RosterPanelError("portrait cannot have both url and placeholder")
    if url is None and placeholder is None:
        raise RosterPanelError("portrait must have either url or placeholder")

    return {
        "subject_key": subject_key,
        "status": status,
        "url": url,
        "aspect_ratio": aspect_ratio,
        "alt": alt,
        "placeholder": placeholder,
    }


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
        if entity is None:
            resolved = {
                "kind": "unavailable",
                "label": "無法提供",
                "status": None,
                "url": None,
                "aspect_ratio": None,
                "alt": "無法提供",
                "subject_key": None,
            }
        else:
            resolved = resolve_character(entity)

        portrait = {
            "subject_key": resolved.get("subject_key"),
            "status": resolved.get("status"),
            "url": resolved.get("url"),
            "aspect_ratio": resolved.get("aspect_ratio"),
            "alt": resolved.get("alt") or "無法提供",
            "placeholder": _placeholder_for(resolved),
        }

        character_rows.append(
            {
                "identity": char_view.identity,
                "name": char_view.name,
                "current": char_view.current,
                "pending": char_view.pending,
                "portrait": portrait,
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
    "roster_presenter",
    "validate_roster",
]
