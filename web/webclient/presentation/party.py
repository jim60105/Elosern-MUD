"""Version-2 read-only ``party`` presentation panel.

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
``slots: []`` so the client renders the controlled figure alone instead of an
unavailable branch. Creation-pending and no-location puppets raise
:class:`PanelUnavailableError` and receive the registry-owned shared
unavailable form.

``portrait_ref`` is the art catalog key of the companion while the current
bounded art view ADMITS it (``world.rules.art_view.build_art_view`` — the one
membership owner), answered without any real-image gate: an admitted companion
whose only artwork is its own committed silhouette still carries the
reference, and the same snapshot's ``art.portrait_catalog`` entry carries its
complete canonical descriptor (its ordered source facts, its independent
recorded generation truth and its alpha terminal). A companion the current
view does not admit — a remote row in another room, one dropped by the
catalog cap, or a session whose art view cannot be built — stays the truthful
``null``, and the client renders its own placeholder from the row it already
carries. The client never builds a catalog key.

Bounds note: both HP fields accept zero and no ``hp_current <= hp_maximum``
cross-field rule is asserted — traits are truth, bounds only (the delta spec
overrides the proposal's "positive" wording; the combat participant row keeps
its own stricter cross assertion).
"""

import re
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
from world.rules.art_view import ArtViewError, build_art_view, portrait_catalog_key
from world.rules.npc_identity import npc_display_name
from world.rules.party import (
    PARTY_MAX_COMPANIONS,
    bound_owner_of,
    has_general_membership,
    live_companions,
    party_size,
    reasons_for,
)

PARTY_SCHEMA_VERSION = 2

#: The general-quota limit the panel reports as ``general_quota.limit``;
#: mirrors ``world.rules.party.PARTY_MAX_COMPANIONS`` so drift fails loudly.
PARTY_GENERAL_LIMIT = PARTY_MAX_COMPANIONS
#: Envelope safety bound on the ordered roster. The spec removes the old
#: four-row cap: temporary members sit beyond the general quota, so the panel
#: renders every effective row and never truncates on quota.
PARTY_MAX_SLOTS = 16
MAX_PARTY_PORTRAIT_REF = 32
MAX_PARTY_COMMISSION_LABEL = MAX_DISPLAY_NAME_CODE_POINTS


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


def _validate_commission_ref(value: Any) -> dict[str, Any]:
    """Validate one ordered temporary-commission reference on a party row.

    The reference carries the exact quest identity and protected-role reference
    with a player-permitted label; it never carries private planning data.
    """
    _require_exact_fields(
        value, "temporary commission", {"quest_id", "role_id", "label"}, {}
    )
    return {
        "quest_id": _bounded_name(
            _require_str(value, "quest_id", maximum=MAX_DISPLAY_NAME_CODE_POINTS),
            "commission quest_id",
        ),
        "role_id": _bounded_name(
            _require_str(value, "role_id", maximum=MAX_DISPLAY_NAME_CODE_POINTS),
            "commission role_id",
        ),
        "label": _bounded_name(
            _require_str(value, "label", maximum=MAX_PARTY_COMMISSION_LABEL),
            "commission label",
        ),
    }


def _validate_membership(value: Any) -> dict[str, Any]:
    """Validate one row's ``membership`` metadata: general flag plus reasons."""
    _require_exact_fields(
        value, "party membership", {"general", "temporary_commissions"}, {}
    )
    general = _require_bool(value, "general")
    refs = value["temporary_commissions"]
    if not isinstance(refs, list):
        raise PartyPanelError("temporary_commissions must be a list")
    commissions = [_validate_commission_ref(ref) for ref in refs]
    pairs = [(ref["quest_id"], ref["role_id"]) for ref in commissions]
    if len(set(pairs)) != len(pairs):
        raise PartyPanelError("temporary commission references must be unique")
    return {"general": general, "temporary_commissions": commissions}


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
            "membership",
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
    portrait_ref = value["portrait_ref"]
    if portrait_ref is not None and (
        not isinstance(portrait_ref, str)
        or not 1 <= len(portrait_ref) <= MAX_PARTY_PORTRAIT_REF
        or re.fullmatch(r"[0-9]+", portrait_ref) is None
    ):
        raise PartyPanelError("portrait_ref must be a bounded decimal string or null")
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
    membership = _validate_membership(value["membership"])
    return {
        "identity": identity,
        "display_name": display_name,
        "portrait_ref": portrait_ref,
        "hp_current": hp_current,
        "hp_maximum": hp_maximum,
        "bond_stage": bond_stage,
        "membership": membership,
    }


def validate_party(payload: Any) -> dict[str, Any]:
    """Validate one exact available ``party`` payload.

    Returns a normalized payload or raises :class:`PartyPanelError`. The
    common unavailable form is NOT accepted here; the registry handles it.
    """
    _require_exact_fields(
        payload,
        "party panel",
        {"schema_version", "available", "slots", "general_quota"},
        {},
    )
    if _require_int(
        payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER
    ) != PARTY_SCHEMA_VERSION:
        raise PartyPanelError("unsupported party schema_version")
    if not _require_bool(payload, "available"):
        raise PartyPanelError("available must be true for the party form")
    slots = payload["slots"]
    if not isinstance(slots, list) or len(slots) > PARTY_MAX_SLOTS:
        raise PartyPanelError(
            f"slots must be a list of at most {PARTY_MAX_SLOTS} rows"
        )
    rows = [_validate_slot(row) for row in slots]
    identities = [row["identity"] for row in rows]
    if len(set(identities)) != len(identities):
        raise PartyPanelError("party slot identities must be unique")
    quota = payload["general_quota"]
    _require_exact_fields(quota, "general quota", {"used", "limit"}, {})
    used = _require_int(quota, "used", minimum=0, maximum=MAX_SAFE_INTEGER)
    limit = _require_int(quota, "limit", minimum=0, maximum=MAX_SAFE_INTEGER)
    if used > limit:
        raise PartyPanelError("general quota used exceeds the limit")
    result = {
        "schema_version": PARTY_SCHEMA_VERSION,
        "available": True,
        "general_quota": {"used": used, "limit": limit},
        "slots": rows,
    }
    # Envelope guarantee (the shared per-panel closing check): an over-limit
    # payload can only come from a producer bug and fails closed.
    if json_byte_size(result) > MAX_CANONICAL_JSON_BYTES:
        raise PartyPanelError("party payload exceeds the OOB envelope limit")
    return result


def _admitted_identities(actor: Any) -> frozenset[int] | None:
    """The current art view's admitted entity identities, or ``None``.

    Builds the membership owner once per presentation and reuses it for every
    row, so the panel and the art catalog are judged by exactly one rule.
    ``None`` means the committed art panel cannot supply a view at all; every
    reference then degrades to ``None`` and the party panel stays available.
    """
    try:
        return frozenset(int(view.identity) for view in build_art_view(actor).entities)
    except ArtViewError:
        return None


def _resolve_portrait_ref(npc: Any, members: frozenset[int] | None) -> str | None:
    """The companion's own art-catalog key while the view admits it, else ``None``.

    Membership is the ONE admission rule (``world.rules.art_view``), so this
    row and the art panel's catalog entry for the same companion can never
    disagree. The reference is emitted for every admitted companion whether or
    not real imagery resolves — the reference names a complete descriptor in
    the same committed snapshot, not a real image. Nothing here reads, creates
    or enqueues art state.
    """
    if members is None or int(npc.pk) not in members:
        return None
    return portrait_catalog_key(npc.pk)


def party_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``party`` panel for the authenticated puppet."""
    actor = context.actor
    if bool(getattr(actor, "creation_pending", False)):
        raise PanelUnavailableError
    if getattr(actor, "location", None) is None:
        raise PanelUnavailableError
    from typeclasses.npcs import NPC

    owner = bound_owner_of(actor) if isinstance(actor, NPC) else actor
    if owner is None:
        raise PanelUnavailableError

    from world.quests.definitions import QUEST_DEFINITION_REGISTRY
    from world.quests.runtime import read_records

    records = {record.quest_id: record for record in read_records(owner)}

    def _commission_label(quest_id: str) -> str:
        record = records.get(quest_id)
        if record is None:
            return quest_id
        definition = QUEST_DEFINITION_REGISTRY.get(record.definition_key)
        return (
            definition.display_name
            if definition is not None
            else record.definition_key
        )[:MAX_PARTY_COMMISSION_LABEL]

    slots: list[dict[str, Any]] = []
    # The committed art view's admission set, resolved once for the whole
    # roster: a companion the view does not admit is the truthful null.
    members = _admitted_identities(actor)
    # The complete ordered effective roster: temporary members sit beyond the
    # general quota, so no four-row slice truncates a valid roster.
    for npc in live_companions(owner):
        hp_current, hp_maximum = stored_gauge_pair(npc, "hp")
        commissions = [
            {
                "quest_id": quest_id,
                "role_id": role_id,
                "label": _commission_label(quest_id),
            }
            for quest_id, role_id in reasons_for(npc, owner)
        ]
        slots.append(
            {
                "identity": int(npc.pk),
                "display_name": npc_display_name(npc)[
                    :MAX_DISPLAY_NAME_CODE_POINTS
                ],
                "portrait_ref": _resolve_portrait_ref(npc, members),
                "hp_current": hp_current,
                "hp_maximum": hp_maximum,
                "bond_stage": npc.relations.stage_for(owner).name,
                "membership": {
                    "general": has_general_membership(npc, owner),
                    "temporary_commissions": commissions,
                },
            }
        )
    return validate_party(
        {
            "schema_version": PARTY_SCHEMA_VERSION,
            "available": True,
            "general_quota": {
                "used": party_size(owner),
                "limit": PARTY_GENERAL_LIMIT,
            },
            "slots": slots,
        }
    )


__all__ = [
    "PARTY_GENERAL_LIMIT",
    "PARTY_MAX_SLOTS",
    "PARTY_SCHEMA_VERSION",
    "PartyPanelError",
    "party_presenter",
    "validate_party",
]
