"""Exact version-1 ``party_member`` panel for the party window's 成員 tab.

The panel publishes the viewed member's member-tab facts as one exact,
read-only payload: the companion bond stage with stage pips, membership
(general flag plus ordered temporary commissions), the intimate state, and
server-authored action descriptors for possess or release, leave, and the NPC
persona editor. The commander section carries the four persona prose fields,
the intimate state and the commander's own persona-edit descriptor.

The panel follows the session's viewed member (``party.view_member``) and
falls back to the commander, exactly like the ``party`` panel's
``viewed_member_id``. It is available in exploration and combat; actions that
cannot run in the current mode or state carry their existing verdict and
bounded reason rather than disappearing, so the client never infers
availability.

Descriptors are ``{action_id, params, enabled, reason}``. ``reason`` is the
existing fixed Traditional Chinese verdict text, or ``null`` when enabled. The
companion's possession descriptor is ``explore.possess`` or, while the player
possesses that companion, ``explore.possess_release``. The commander's
persona-edit descriptor names ``character.persona.update`` — the action that
edits the commander's own prose — and is disabled while the player possesses a
companion, because that action would otherwise target the puppet rather than
the commander whose prose this panel displays.

The raw affinity value never leaves the rules layer: ``bond`` carries only the
stage name and its 1-based position in the rulebook's stage table.
"""

from typing import Any

from web.webclient.actions.character_actions import NOT_EXPLORING_MESSAGE
from web.webclient.presentation.affordances import in_exploration_mode
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.party import (
    PARTY_MAX_SLOTS,
    membership_section,
    validate_party_membership,
)
from web.webclient.presentation.party_view_selection import resolve_viewed_member
from web.webclient.presentation.persona_sections import (
    serialize_intimate,
    serialize_persona,
    validate_intimate,
    validate_persona,
)
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    MAX_MESSAGE_CODE_POINTS,
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_bool,
    _require_exact_fields,
    _require_int,
    _require_str,
    json_byte_size,
)
from web.webclient.presentation.registry import PanelUnavailableError
from world.rules.affinity import bond_stage_position
from world.rules.party import (
    ESCORT_BOUND_MESSAGE,
    HANDBACK_FIRST_MESSAGE,
    NOT_COMPANION_MESSAGE,
    bound_owner_of,
    has_general_membership,
    is_companion,
    reasons_for,
)
from world.rules.possession import (
    POSSESSED_REFUSAL_MESSAGES,
    POSSESSION_REJECTION_MESSAGES,
    REASON_POSSESSED_TALK,
    current_possession,
    is_possessed_actor,
    possession_verdict,
)
from world.rules.status_query import StatusQueryError, read_intimate_view

PARTY_MEMBER_SCHEMA_VERSION = 1
PARTY_MEMBER_KIND = "party_member"
PARTY_MEMBER_ROLE_COMMANDER = "commander"
PARTY_MEMBER_ROLE_COMPANION = "companion"
PARTY_MEMBER_ROLES = frozenset(
    {PARTY_MEMBER_ROLE_COMMANDER, PARTY_MEMBER_ROLE_COMPANION}
)

#: The exact action identifiers a descriptor may name.
ACTION_POSSESS = "explore.possess"
ACTION_POSSESS_RELEASE = "explore.possess_release"
ACTION_PARTY_LEAVE = "explore.party_leave"
ACTION_NPC_PERSONA = "npc.persona.read"
ACTION_COMMANDER_PERSONA = "character.persona.update"
#: The fixed companion action order (possession, leave, persona).
COMPANION_ACTION_ORDER = (ACTION_POSSESS, ACTION_PARTY_LEAVE, ACTION_NPC_PERSONA)
#: The possession slot carries either the possess or the release action.
POSSESSION_ACTION_IDS = frozenset({ACTION_POSSESS, ACTION_POSSESS_RELEASE})
#: The commander carries exactly the persona-edit descriptor.
COMMANDER_ACTION_ORDER = (ACTION_COMMANDER_PERSONA,)

#: The stage-name bound reuses the party panel's display-name ceiling.
MAX_BOND_STAGE_CODE_POINTS = 128
#: A disabled reason is one existing fixed verdict line; the action-result
#: transport already bounds every player-facing line at this same number.
MAX_REASON_CODE_POINTS = MAX_MESSAGE_CODE_POINTS
#: A person may hold at most every companion slot as a temporary commission.
MAX_COMMISSIONS = PARTY_MAX_SLOTS

# Fixed persona-editor verdict lines (shared with the exploration affordance
# and the npc.persona.read action).
NPC_PERSONA_NOT_ALLOWED_MESSAGE = "你目前無法編輯 NPC 設定。"
NPC_PERSONA_NO_TARGET_MESSAGE = "這裡沒有這個對象。"
NPC_PERSONA_UNAVAILABLE_MESSAGE = "此角色的設定目前無法編輯或尚未初始化。"


class PartyMemberPanelError(ProtocolValidationError):
    """The available ``party_member`` payload violates its exact bounded schema."""


def _validate_bond(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "bond", {"stage", "step", "steps"}, {})
    stage = _require_str(value, "stage", maximum=MAX_BOND_STAGE_CODE_POINTS)
    if not stage.strip():
        raise PartyMemberPanelError("bond.stage must be non-empty")
    steps = _require_int(value, "steps", minimum=1, maximum=MAX_SAFE_INTEGER)
    step = _require_int(value, "step", minimum=1, maximum=steps)
    return {"stage": stage, "step": step, "steps": steps}


def _validate_descriptor(
    value: Any, *, action_ids: frozenset[str], params: dict[str, Any]
) -> dict[str, Any]:
    label = "|".join(sorted(action_ids))
    _require_exact_fields(
        value, f"{label} descriptor", {"action_id", "params", "enabled", "reason"}, {}
    )
    action_id = value["action_id"]
    if action_id not in action_ids:
        raise PartyMemberPanelError(
            f"descriptor action_id must be one of {sorted(action_ids)}"
        )
    _require_exact_fields(
        value["params"], f"{label} params", set(params), {}
    )
    for field, expected in params.items():
        actual = value["params"][field]
        if isinstance(expected, bool) or not isinstance(expected, int):
            raise PartyMemberPanelError(f"invalid expected param {field!r}")
        if (
            isinstance(actual, bool)
            or not isinstance(actual, int)
            or actual != expected
        ):
            raise PartyMemberPanelError(
                f"{label} params.{field} must name the viewed member"
            )
    enabled = _require_bool(value, "enabled")
    reason = value["reason"]
    if reason is not None:
        reason = _require_str(value, "reason", maximum=MAX_REASON_CODE_POINTS)
        if not reason.strip():
            raise PartyMemberPanelError("reason must be non-empty when set")
    if enabled and reason is not None:
        raise PartyMemberPanelError("an enabled descriptor carries no reason")
    if not enabled and reason is None:
        raise PartyMemberPanelError("a disabled descriptor carries its reason")
    return {
        "action_id": action_id,
        "params": dict(params),
        "enabled": enabled,
        "reason": reason,
    }


def _validate_actions(
    value: Any, *, member_id: int, order: tuple[str, ...]
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) != len(order):
        raise PartyMemberPanelError(
            f"actions must hold exactly {len(order)} descriptors"
        )
    descriptors = []
    for index, action_id in enumerate(order):
        params = (
            {} if action_id == ACTION_COMMANDER_PERSONA else {"npc_id": member_id}
        )
        action_ids = (
            POSSESSION_ACTION_IDS
            if action_id == ACTION_POSSESS
            else frozenset({action_id})
        )
        descriptors.append(
            _validate_descriptor(value[index], action_ids=action_ids, params=params)
        )
    return descriptors


def _validate_companion(value: Any, member_id: int) -> dict[str, Any]:
    _require_exact_fields(
        value, "companion", {"bond", "membership", "intimate", "actions"}, {}
    )
    bond = _validate_bond(value["bond"])
    membership = validate_party_membership(value["membership"])
    if len(membership["temporary_commissions"]) > MAX_COMMISSIONS:
        raise PartyMemberPanelError("companion carries too many temporary commissions")
    intimate = validate_intimate(value["intimate"], error=PartyMemberPanelError)
    actions = _validate_actions(
        value["actions"], member_id=member_id, order=COMPANION_ACTION_ORDER
    )
    return {
        "bond": bond,
        "membership": membership,
        "intimate": intimate,
        "actions": actions,
    }


def _validate_commander(value: Any, member_id: int) -> dict[str, Any]:
    _require_exact_fields(value, "commander", {"persona", "intimate", "actions"}, {})
    persona = validate_persona(value["persona"], error=PartyMemberPanelError)
    intimate = validate_intimate(value["intimate"], error=PartyMemberPanelError)
    actions = _validate_actions(
        value["actions"], member_id=member_id, order=COMMANDER_ACTION_ORDER
    )
    return {"persona": persona, "intimate": intimate, "actions": actions}


def validate_party_member(payload: Any) -> dict[str, Any]:
    """Validate one exact available version-1 ``party_member`` payload."""
    _require_exact_fields(
        payload,
        "party_member panel",
        {
            "schema_version",
            "available",
            "kind",
            "member_id",
            "role",
            "companion",
            "commander",
        },
        {},
    )
    _require_int(
        payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER
    )
    if payload["schema_version"] != PARTY_MEMBER_SCHEMA_VERSION:
        raise PartyMemberPanelError("unsupported party_member schema_version")
    if payload["available"] is not True:
        raise PartyMemberPanelError("party_member panel must be available")
    if payload["kind"] != PARTY_MEMBER_KIND:
        raise PartyMemberPanelError("kind must be 'party_member'")
    member_id = _require_int(
        payload, "member_id", minimum=1, maximum=MAX_SAFE_INTEGER
    )
    role = payload["role"]
    if role not in PARTY_MEMBER_ROLES:
        raise PartyMemberPanelError("role must be commander or companion")
    companion_value = payload["companion"]
    commander_value = payload["commander"]
    if role == PARTY_MEMBER_ROLE_COMMANDER:
        if companion_value is not None:
            raise PartyMemberPanelError("a commander panel carries no companion section")
        if commander_value is None:
            raise PartyMemberPanelError("a commander panel requires its section")
        companion = None
        commander = _validate_commander(commander_value, member_id)
    else:
        if commander_value is not None:
            raise PartyMemberPanelError("a companion panel carries no commander section")
        if companion_value is None:
            raise PartyMemberPanelError("a companion panel requires its section")
        companion = _validate_companion(companion_value, member_id)
        commander = None
    result = {
        "schema_version": PARTY_MEMBER_SCHEMA_VERSION,
        "available": True,
        "kind": PARTY_MEMBER_KIND,
        "member_id": member_id,
        "role": role,
        "companion": companion,
        "commander": commander,
    }
    if json_byte_size(result) > MAX_CANONICAL_JSON_BYTES:
        raise PartyMemberPanelError("party_member payload exceeds the OOB envelope limit")
    return result


# ---------------------------------------------------------------------------
# Descriptor construction (existing read-only verdicts only).
# ---------------------------------------------------------------------------


def _descriptor(
    action_id: str, *, member_id: int | None, reason: str | None
) -> dict[str, Any]:
    params = {} if member_id is None else {"npc_id": member_id}
    return {
        "action_id": action_id,
        "params": params,
        "enabled": reason is None,
        "reason": reason,
    }


def _possession_descriptor(commander: Any, member: Any) -> dict[str, Any]:
    """The possess/release descriptor for the viewed companion."""
    member_id = int(member.pk)
    possession = current_possession(commander)
    if possession is not None and possession["npc_dbid"] == member_id:
        return _descriptor(ACTION_POSSESS_RELEASE, member_id=member_id, reason=None)
    verdict = possession_verdict(commander, member)
    if verdict is None:
        return _descriptor(ACTION_POSSESS, member_id=member_id, reason=None)
    return _descriptor(
        ACTION_POSSESS,
        member_id=member_id,
        reason=POSSESSION_REJECTION_MESSAGES.get(verdict, "無法附身。"),
    )


def _present_in_actor_room(actor: Any, member: Any) -> bool:
    """Whether the action adapters could re-resolve ``member`` from the puppet."""
    if member is actor:
        return getattr(actor, "location", None) is not None
    location = getattr(actor, "location", None)
    return (
        location is not None
        and getattr(member, "location", None) == location
        and bool(location.filter_visible([member], actor))
    )


def _leave_descriptor(actor: Any, commander: Any, member: Any) -> dict[str, Any]:
    """The leave descriptor, matching the ``explore.party_leave`` preflight.

    Presence is anchored at the acting puppet (the action re-resolves the
    target from its current room), while membership and the escort/handback
    gates are commander-scoped exactly like ``leave_party``.
    """
    member_id = int(member.pk)
    if not _present_in_actor_room(actor, member):
        return _descriptor(
            ACTION_PARTY_LEAVE, member_id=member_id, reason="這裡沒有這個對象。"
        )
    if not is_companion(member, commander):
        return _descriptor(
            ACTION_PARTY_LEAVE, member_id=member_id, reason=NOT_COMPANION_MESSAGE
        )
    reasons = reasons_for(member, commander)
    if not has_general_membership(member, commander) and reasons:
        return _descriptor(
            ACTION_PARTY_LEAVE,
            member_id=member_id,
            reason=ESCORT_BOUND_MESSAGE.format(
                quests="、".join(sorted({quest_id for quest_id, _ in reasons}))
            ),
        )
    possessed_by = getattr(getattr(member, "db", None), "possessed_by", None)
    if not reasons and possessed_by is not None and int(possessed_by) == int(commander.pk):
        return _descriptor(
            ACTION_PARTY_LEAVE, member_id=member_id, reason=HANDBACK_FIRST_MESSAGE
        )
    return _descriptor(ACTION_PARTY_LEAVE, member_id=member_id, reason=None)


def _npc_persona_descriptor(actor: Any, member: Any) -> dict[str, Any]:
    """The companion's NPC persona-editor descriptor (read-only gate)."""
    from world.rules.npc_persona import is_card_available

    member_id = int(member.pk)
    if is_possessed_actor(actor):
        reason = POSSESSED_REFUSAL_MESSAGES[REASON_POSSESSED_TALK]
    elif not in_exploration_mode(actor):
        reason = NPC_PERSONA_NOT_ALLOWED_MESSAGE
    else:
        if not _present_in_actor_room(actor, member):
            reason = NPC_PERSONA_NO_TARGET_MESSAGE
        elif not is_card_available(member):
            reason = NPC_PERSONA_UNAVAILABLE_MESSAGE
        else:
            reason = None
    return _descriptor(ACTION_NPC_PERSONA, member_id=member_id, reason=reason)


def _commander_persona_descriptor(actor: Any) -> dict[str, Any]:
    """The commander's own persona-edit descriptor.

    ``character.persona.update`` edits the authenticated puppet's prose, so
    the descriptor is disabled while the player possesses a companion: the
    displayed prose belongs to the commander, never the puppet.
    """
    if is_possessed_actor(actor) or not in_exploration_mode(actor):
        reason = NOT_EXPLORING_MESSAGE
    else:
        reason = None
    return _descriptor(ACTION_COMMANDER_PERSONA, member_id=None, reason=reason)


def _commander_section(actor: Any, commander: Any) -> dict[str, Any]:
    return {
        "persona": serialize_persona(commander),
        "intimate": serialize_intimate(read_intimate_view(commander)),
        "actions": [_commander_persona_descriptor(actor)],
    }


def _companion_section(actor: Any, commander: Any, member: Any) -> dict[str, Any]:
    stage_name, step, steps = bond_stage_position(member, commander)
    return {
        "bond": {"stage": stage_name, "step": step, "steps": steps},
        "membership": membership_section(member, commander),
        "intimate": serialize_intimate(read_intimate_view(member)),
        "actions": [
            _possession_descriptor(commander, member),
            _leave_descriptor(actor, commander, member),
            _npc_persona_descriptor(actor, member),
        ],
    }


def party_member_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``party_member`` panel for the viewed member."""
    actor = context.actor
    if bool(getattr(actor, "creation_pending", False)):
        raise PanelUnavailableError
    if getattr(actor, "location", None) is None:
        raise PanelUnavailableError
    from typeclasses.npcs import NPC

    commander = bound_owner_of(actor) if isinstance(actor, NPC) else actor
    if commander is None:
        raise PanelUnavailableError
    member = resolve_viewed_member(context)
    if member is None:  # pragma: no cover - the commander resolved above
        raise PanelUnavailableError
    member_id = int(member.pk)
    try:
        if member_id == int(commander.pk):
            role = PARTY_MEMBER_ROLE_COMMANDER
            companion = None
            commander_section = _commander_section(actor, commander)
        else:
            role = PARTY_MEMBER_ROLE_COMPANION
            companion = _companion_section(actor, commander, member)
            commander_section = None
    except StatusQueryError:
        raise PanelUnavailableError
    return validate_party_member(
        {
            "schema_version": PARTY_MEMBER_SCHEMA_VERSION,
            "available": True,
            "kind": PARTY_MEMBER_KIND,
            "member_id": member_id,
            "role": role,
            "companion": companion,
            "commander": commander_section,
        }
    )


__all__ = [
    "ACTION_COMMANDER_PERSONA",
    "ACTION_NPC_PERSONA",
    "ACTION_PARTY_LEAVE",
    "ACTION_POSSESS",
    "ACTION_POSSESS_RELEASE",
    "COMPANION_ACTION_ORDER",
    "COMMANDER_ACTION_ORDER",
    "MAX_BOND_STAGE_CODE_POINTS",
    "MAX_REASON_CODE_POINTS",
    "PARTY_MEMBER_KIND",
    "PARTY_MEMBER_ROLES",
    "PARTY_MEMBER_ROLE_COMMANDER",
    "PARTY_MEMBER_ROLE_COMPANION",
    "PARTY_MEMBER_SCHEMA_VERSION",
    "PartyMemberPanelError",
    "party_member_presenter",
    "validate_party_member",
]
