"""Version-1 read-only ``party`` presentation panel (webclient-align-04).

The presenter serializes the player's live companions into the exact
``{schema_version, available, slots}`` shape: row vocabulary is the existing
NPC wire shape (``identity``, ``display_name``, ``portrait_ref``, flat
``hp_current``/``hp_maximum``) shared with the exploration interact-target
and combat participant rows, so the combat HUD can join the two panels by
``identity``. Bond disclosure is the canonical stage NAME only — the raw
affinity number never reaches the wire (design: 數值隱藏七階羈絆).

The payload is read-only by construction: membership comes from
``world.rules.party.live_companions`` (stale dbids, non-NPC entries, and
backref mismatches are already filtered there), HP comes from the companion's
TRUE stored traits through the shared ``stored_gauge_pair`` rules helper
(never ``disguised_stats`` — display disguise must not leak into party
truth), and the bond stage comes from the rulebook-backed
``npc.relations.stage_for`` reader. An empty party is an available panel with
``slots: []`` so the client renders its dashed invite slot instead of an
unavailable branch. Creation-pending and no-location puppets raise
:class:`PanelUnavailableError` and receive the registry-owned shared
unavailable form.

Bounds note: both HP fields accept zero and no ``hp_current <= hp_maximum``
cross-field rule is asserted — traits are truth, bounds only (the delta spec
overrides the proposal's "positive" wording; the combat participant row keeps
its own stricter cross assertion).
"""

from typing import Any

from web.webclient.presentation.affordances import MAX_DISPLAY_NAME_CODE_POINTS
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
from world.rules.action import stored_gauge_pair
from world.rules.npc_identity import npc_display_name

PARTY_SCHEMA_VERSION = 1

# Mirrors ``world.rules.party.PARTY_MAX_COMPANIONS``; the row cap is pinned in
# the spec so drift between the rules bound and the wire bound fails loudly.
PARTY_MAX_ROWS = 4


class PartyPanelError(ProtocolValidationError):
    """The available party payload violates its exact bounded schema."""


def _reject_lone_surrogates(value: str, field: str) -> str:
    """Reject strings carrying unpaired UTF-16 surrogate code points.

    A Python ``str`` can store ``U+D800..U+DFFF`` values, but they are not
    valid JSON text and cannot be encoded as UTF-8, so a corrupt stored name
    would otherwise escape the closing byte check as a raw
    ``UnicodeEncodeError``. Rejected as an explicit schema violation, and the
    UMD mirror rejects the same payloads (final rubber-duck parity round).
    """
    for char in value:
        if 0xD800 <= ord(char) <= 0xDFFF:
            raise PartyPanelError(f"{field} contains an unpaired surrogate code point")
    return value


def _bounded_name(value: str, field: str) -> str:
    if not value:
        raise PartyPanelError(f"{field} must be non-empty")
    return _reject_lone_surrogates(value, field)


def _validate_slot(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "party slot",
        {
            "identity",
            "display_name",
            "portrait_ref",
            "hp_current",
            "hp_maximum",
            "bond_stage",
        },
        {},
    )
    identity = _require_int(
        value, "identity", minimum=1, maximum=MAX_SAFE_INTEGER
    )
    display_name = _bounded_name(
        _require_str(value, "display_name", maximum=MAX_DISPLAY_NAME_CODE_POINTS),
        "slot display_name",
    )
    if value["portrait_ref"] is not None:
        raise PartyPanelError("portrait_ref must be null in this schema version")
    # Bounds only — zero HP is legal (a knocked-out companion's stored gauge)
    # and the current/maximum ordering is trait truth, never a validator rule.
    hp_current = _require_int(
        value, "hp_current", minimum=0, maximum=MAX_SAFE_INTEGER
    )
    hp_maximum = _require_int(
        value, "hp_maximum", minimum=0, maximum=MAX_SAFE_INTEGER
    )
    bond_stage = _bounded_name(
        _require_str(value, "bond_stage", maximum=MAX_DISPLAY_NAME_CODE_POINTS),
        "slot bond_stage",
    )
    return {
        "identity": identity,
        "display_name": display_name,
        "portrait_ref": None,
        "hp_current": hp_current,
        "hp_maximum": hp_maximum,
        "bond_stage": bond_stage,
    }


def validate_party(payload: Any) -> dict[str, Any]:
    """Validate one exact available ``party`` payload.

    Returns a normalized payload or raises :class:`PartyPanelError`. The
    common unavailable form is NOT accepted here; the registry handles it.
    """
    _require_exact_fields(
        payload, "party panel", {"schema_version", "available", "slots"}, {}
    )
    if _require_int(
        payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER
    ) != PARTY_SCHEMA_VERSION:
        raise PartyPanelError("unsupported party schema_version")
    if not _require_bool(payload, "available"):
        raise PartyPanelError("available must be true for the party form")
    slots = payload["slots"]
    if not isinstance(slots, list) or len(slots) > PARTY_MAX_ROWS:
        raise PartyPanelError(
            f"slots must be a list of at most {PARTY_MAX_ROWS} rows"
        )
    rows = [_validate_slot(row) for row in slots]
    identities = [row["identity"] for row in rows]
    if len(set(identities)) != len(identities):
        raise PartyPanelError("party slot identities must be unique")
    result = {
        "schema_version": PARTY_SCHEMA_VERSION,
        "available": True,
        "slots": rows,
    }
    # Envelope guarantee (the shared per-panel closing check): an over-limit
    # payload can only come from a producer bug and fails closed.
    if json_byte_size(result) > MAX_CANONICAL_JSON_BYTES:
        raise PartyPanelError("party payload exceeds the OOB envelope limit")
    return result


def party_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``party`` panel for the authenticated puppet."""
    actor = context.actor
    if bool(getattr(actor, "creation_pending", False)):
        raise PanelUnavailableError
    if getattr(actor, "location", None) is None:
        raise PanelUnavailableError
    from world.rules.party import live_companions

    slots: list[dict[str, Any]] = []
    for npc in live_companions(actor)[:PARTY_MAX_ROWS]:
        hp_current, hp_maximum = stored_gauge_pair(npc, "hp")
        slots.append(
            {
                "identity": int(npc.pk),
                "display_name": npc_display_name(npc)[
                    :MAX_DISPLAY_NAME_CODE_POINTS
                ],
                "portrait_ref": None,
                "hp_current": hp_current,
                "hp_maximum": hp_maximum,
                "bond_stage": npc.relations.stage_for(actor).name,
            }
        )
    return validate_party(
        {
            "schema_version": PARTY_SCHEMA_VERSION,
            "available": True,
            "slots": slots,
        }
    )


__all__ = [
    "PARTY_MAX_ROWS",
    "PARTY_SCHEMA_VERSION",
    "PartyPanelError",
    "party_presenter",
    "validate_party",
]
