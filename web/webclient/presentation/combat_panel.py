"""Exact schema-version-2 ``context_actions`` combat panel and presenter.

The presenter serializes the frozen combat view owned by
``world.rules.combat_view`` and validates its own output against the exact
bounded schema before returning it to the presentation registry. Outside a
valid active combat session it raises :class:`PanelUnavailableError` so the
registry emits the common unavailable form; it never fabricates exploration
actions.

The panel is read-only: it reconstructs the active session, reads participants
and active-skill previews, and never mutates traits, resources, buffs, sexual
state, battlefield, session, quest, location, or world time.
"""

from typing import Any

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_bool,
    _require_exact_fields,
    _require_int,
    _require_str,
    _validate_identifier,
    _validate_message,
)
from web.webclient.presentation.registry import PanelUnavailableError
from world.rules.combat_view import (
    MAX_DISPLAY_NAME_CODE_POINTS,
    MAX_PARTICIPANTS,
    MAX_REASON_MESSAGE_CODE_POINTS,
    MAX_SESSION_ID_CODE_POINTS,
    MAX_SKILLS,
    RECOVERY_SECONDARY_ACTIONS,
    ROOT_ACTIONS,
    SECONDARY_ACTIONS,
    CombatViewError,
    build_combat_view,
)

CONTEXT_ACTIONS_SCHEMA_VERSION = 2

# Stable panel-level bounds equal to or below the global protocol table.
MAX_SKILL_KEY = 64
MAX_LABEL = 128
MAX_DESCRIPTION = 512
MAX_COST_KEYS = 8
MAX_SKILL_TARGETS = MAX_PARTICIPANTS
MAX_SHORTHANDS = 3
MAX_TOKEN = 16
MAX_TEAM = 16
MAX_STATE = 16
MAX_ACTION_KEYS = 16
MAX_REASON_CODE = 64
MAX_PARTICIPANT_REF = 32

# Participant display-state values the panel emits.
PARTICIPANT_STATES = frozenset({"active", "fled", "knocked_out", "defeated"})
TEAMS = frozenset({"party", "foes"})
MODES = frozenset({"hostile", "guild_exam"})
SESSION_STATES = frozenset({"ready", "recovery"})
TARGET_SPECS = frozenset({"none", "self", "single", "area"})
ALLOWED_SHORTHANDS = frozenset({"all-enemies", "all-allies", "all"})


class ContextActionsError(ValueError):
    """The available combat panel violates its exact bounded schema."""


def _validate_token(value: Any) -> str:
    if not isinstance(value, str):
        raise ProtocolValidationError("participant token must be a string")
    if not (1 <= len(value) <= MAX_TOKEN):
        raise ProtocolValidationError("participant token exceeds its bound")
    if not value or not (value[0] in "ae" and value[1:].isdigit()):
        raise ProtocolValidationError("participant token must be aN or eN")
    return value


def _validate_session(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "combat session", {"session_id", "mode", "round", "state", "reason"}, {})
    session_id = _require_str(
        value, "session_id", maximum=MAX_SESSION_ID_CODE_POINTS
    )
    if not session_id.strip():
        raise ProtocolValidationError("session_id must be non-empty")
    mode = value["mode"]
    if mode not in MODES:
        raise ProtocolValidationError("session mode must be hostile or guild_exam")
    round_value = _require_int(value, "round", minimum=0, maximum=MAX_SAFE_INTEGER)
    state = value["state"]
    if state not in SESSION_STATES:
        raise ProtocolValidationError("session state must be ready or recovery")
    reason = value["reason"]
    if reason is None:
        if state != "ready":
            raise ProtocolValidationError("a recovery session requires a reason")
    else:
        _require_exact_fields(reason, "session reason", {"code", "message"}, {})
        _validate_identifier(reason["code"], "session reason code")
        _validate_message(reason["message"], "session reason message")
        if state != "recovery":
            raise ProtocolValidationError("a ready session must have a null reason")
    return {
        "session_id": session_id,
        "mode": mode,
        "round": round_value,
        "state": state,
        "reason": reason,
    }


def _validate_participant(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "participant",
        {
            "identity",
            "token",
            "display_name",
            "team",
            "state",
            "hp_current",
            "hp_maximum",
            "portrait_ref",
        },
        {},
    )
    identity = _require_int(value, "identity", minimum=1, maximum=MAX_SAFE_INTEGER)
    token = _validate_token(value["token"])
    display_name = _require_str(
        value, "display_name", maximum=MAX_DISPLAY_NAME_CODE_POINTS
    )
    if not display_name.strip():
        raise ProtocolValidationError("participant display_name must be non-empty")
    team = value["team"]
    if team not in TEAMS:
        raise ProtocolValidationError("participant team must be party or foes")
    state = value["state"]
    if state not in PARTICIPANT_STATES:
        raise ProtocolValidationError("participant state is not a stable value")
    hp_current = _require_int(value, "hp_current", minimum=0, maximum=MAX_SAFE_INTEGER)
    hp_maximum = _require_int(value, "hp_maximum", minimum=1, maximum=MAX_SAFE_INTEGER)
    if hp_current > hp_maximum:
        raise ProtocolValidationError("participant hp_current must not exceed maximum")
    portrait_ref = value["portrait_ref"]
    if portrait_ref is not None:
        if not isinstance(portrait_ref, str) or not portrait_ref.isdecimal():
            raise ProtocolValidationError(
                "portrait_ref must be an opaque decimal catalog key or null"
            )
        if len(portrait_ref) > MAX_PARTICIPANT_REF:
            raise ProtocolValidationError("portrait_ref exceeds its bound")
    return {
        "identity": identity,
        "token": token,
        "display_name": display_name,
        "team": team,
        "state": state,
        "hp_current": hp_current,
        "hp_maximum": hp_maximum,
        "portrait_ref": portrait_ref,
    }


def _validate_disabled_reason(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    _require_exact_fields(value, "disabled_reason", {"code", "message"}, {})
    _validate_identifier(value["code"], "disabled_reason code")
    message = _validate_message(value["message"], "disabled_reason message")
    if len(value["code"]) > MAX_REASON_CODE:
        raise ProtocolValidationError("disabled_reason code exceeds its bound")
    return {"code": value["code"], "message": message}


def _validate_skill(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "skill",
        {
            "key",
            "label",
            "description",
            "cost",
            "target_spec",
            "element",
            "enabled",
            "disabled_reason",
            "targets",
            "shorthands",
        },
        {},
    )
    key = _validate_identifier(value["key"], "skill key")
    if len(key) > MAX_SKILL_KEY:
        raise ProtocolValidationError("skill key exceeds its bound")
    label = _require_str(value, "label", maximum=MAX_LABEL)
    if not label.strip():
        raise ProtocolValidationError("skill label must be non-empty")
    description = _require_str(value, "description", maximum=MAX_DESCRIPTION)
    if not description.strip():
        raise ProtocolValidationError("skill description must be non-empty")
    cost = value["cost"]
    if not isinstance(cost, dict) or len(cost) > MAX_COST_KEYS:
        raise ProtocolValidationError("skill cost must be a bounded object")
    for resource, amount in cost.items():
        _validate_identifier(resource, "cost resource key")
        if isinstance(amount, bool) or not isinstance(amount, int):
            raise ProtocolValidationError("skill cost amount must be an integer")
        if amount < 0 or amount > MAX_SAFE_INTEGER:
            raise ProtocolValidationError("skill cost amount is out of bounds")
    target_spec = value["target_spec"]
    if target_spec not in TARGET_SPECS:
        raise ProtocolValidationError("skill target_spec is not a stable value")
    element = value["element"]
    if element is not None:
        _validate_identifier(element, "skill element")
    enabled = _require_bool(value, "enabled")
    disabled_reason = _validate_disabled_reason(value["disabled_reason"])
    if not enabled and disabled_reason is None:
        raise ProtocolValidationError("a disabled skill requires a disabled_reason")
    if enabled and disabled_reason is not None:
        raise ProtocolValidationError("an enabled skill must not carry a disabled_reason")
    targets = value["targets"]
    if not isinstance(targets, list) or len(targets) > MAX_SKILL_TARGETS:
        raise ProtocolValidationError("skill targets exceed their bound")
    seen: set[int] = set()
    for target in targets:
        if isinstance(target, bool) or not isinstance(target, int) or target <= 0:
            raise ProtocolValidationError("skill targets must be positive integers")
        if target in seen:
            raise ProtocolValidationError("skill targets must be unique")
        seen.add(target)
    shorthands = value["shorthands"]
    if not isinstance(shorthands, list) or len(shorthands) > MAX_SHORTHANDS:
        raise ProtocolValidationError("skill shorthands exceed their bound")
    if set(shorthands) - ALLOWED_SHORTHANDS:
        raise ProtocolValidationError("skill carries an unapproved shorthand")
    if len(set(shorthands)) != len(shorthands):
        raise ProtocolValidationError("skill shorthands must be unique")
    if target_spec != "area" and shorthands:
        raise ProtocolValidationError("only area skills may carry shorthands")
    return {
        "key": key,
        "label": label,
        "description": description,
        "cost": dict(cost),
        "target_spec": target_spec,
        "element": element,
        "enabled": enabled,
        "disabled_reason": disabled_reason,
        "targets": list(targets),
        "shorthands": list(shorthands),
    }


def validate_context_actions(payload: Any) -> dict[str, Any]:
    """Validate one exact available ``context_actions`` payload.

    Returns a normalized payload or raises :class:`ContextActionsError`. The
    common unavailable form is NOT accepted here; the registry handles it.
    """
    _require_exact_fields(
        payload,
        "context_actions panel",
        {
            "schema_version",
            "available",
            "kind",
            "session",
            "participants",
            "root_actions",
            "secondary_actions",
            "skills",
        },
        {},
    )
    if _require_int(
        payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER
    ) != CONTEXT_ACTIONS_SCHEMA_VERSION:
        raise ContextActionsError("unsupported context_actions schema_version")
    if not _require_bool(payload, "available"):
        raise ContextActionsError("available must be true for the combat form")
    if payload["kind"] != "combat":
        raise ContextActionsError("combat panel kind must be combat")
    session = _validate_session(payload["session"])
    participants = payload["participants"]
    if not isinstance(participants, list) or len(participants) > MAX_PARTICIPANTS:
        raise ContextActionsError("participants exceed their bound")
    participant_views = [_validate_participant(item) for item in participants]

    def _validate_actions(value: Any, name: str) -> list[str]:
        if not isinstance(value, list) or len(value) > MAX_ACTION_KEYS:
            raise ContextActionsError(f"{name} exceed their bound")
        seen: set[str] = set()
        for key in value:
            validated = _validate_identifier(key, f"{name} key")
            if validated in seen:
                raise ContextActionsError(f"{name} must be unique")
            seen.add(validated)
        return list(value)

    root_actions = _validate_actions(payload["root_actions"], "root_actions")
    secondary_actions = _validate_actions(
        payload["secondary_actions"], "secondary_actions"
    )
    if session["state"] == "ready":
        if set(root_actions) != set(ROOT_ACTIONS) or list(root_actions) != list(ROOT_ACTIONS):
            raise ContextActionsError("ready session must expose the exact root actions")
        if list(secondary_actions) != list(SECONDARY_ACTIONS):
            raise ContextActionsError("ready session must expose confirmed Forfeit")
    else:
        if root_actions:
            raise ContextActionsError("recovery session exposes no cast or flee action")
        if list(secondary_actions) != list(RECOVERY_SECONDARY_ACTIONS):
            raise ContextActionsError("recovery session must retain confirmed Forfeit")

    skills = payload["skills"]
    if not isinstance(skills, list) or len(skills) > MAX_SKILLS:
        raise ContextActionsError("skills exceed their bound")
    skill_views = [_validate_skill(item) for item in skills]
    identity_set = {participant["identity"] for participant in participant_views}
    for skill in skill_views:
        for target in skill["targets"]:
            if target not in identity_set:
                raise ContextActionsError(
                    "skill targets must reference a presented participant"
                )
    if len({skill["key"] for skill in skill_views}) != len(skill_views):
        raise ContextActionsError("skill keys must be unique")

    return {
        "schema_version": CONTEXT_ACTIONS_SCHEMA_VERSION,
        "available": True,
        "kind": "combat",
        "session": session,
        "participants": participant_views,
        "root_actions": root_actions,
        "secondary_actions": secondary_actions,
        "skills": skill_views,
    }


def context_actions_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available combat panel for the authenticated puppet."""
    actor = context.actor
    try:
        view = build_combat_view(actor)
    except CombatViewError:
        raise PanelUnavailableError

    if view.recovery:
        session = {
            "session_id": view.session.session_id,
            "mode": view.session.mode,
            "round": view.session.round,
            "state": "recovery",
            "reason": {
                "code": view.session.reason[0],
                "message": view.session.reason[1],
            },
        }
        payload = {
            "schema_version": CONTEXT_ACTIONS_SCHEMA_VERSION,
            "available": True,
            "kind": "combat",
            "session": session,
            "participants": [],
            "root_actions": [],
            "secondary_actions": list(RECOVERY_SECONDARY_ACTIONS),
            "skills": [],
        }
        return validate_context_actions(payload)

    participants = [
        {
            "identity": participant.identity,
            "token": participant.token,
            "display_name": participant.display_name,
            "team": participant.team,
            "state": participant.state,
            "hp_current": participant.hp_current,
            "hp_maximum": participant.hp_maximum,
            "portrait_ref": participant.portrait_ref,
        }
        for participant in view.participants
    ]
    skills = [
        {
            "key": skill.key,
            "label": skill.label,
            "description": skill.description,
            "cost": dict(skill.cost),
            "target_spec": skill.target_spec,
            "element": skill.element,
            "enabled": skill.enabled,
            "disabled_reason": (
                None
                if skill.reason_code is None
                else {"code": skill.reason_code, "message": skill.reason_message}
            ),
            "targets": list(skill.valid_target_ids),
            "shorthands": list(skill.shorthands),
        }
        for skill in view.skills
    ]
    payload = {
        "schema_version": CONTEXT_ACTIONS_SCHEMA_VERSION,
        "available": True,
        "kind": "combat",
        "session": {
            "session_id": view.session.session_id,
            "mode": view.session.mode,
            "round": view.session.round,
            "state": "ready",
            "reason": None,
        },
        "participants": participants,
        "root_actions": list(ROOT_ACTIONS),
        "secondary_actions": list(SECONDARY_ACTIONS),
        "skills": skills,
    }
    return validate_context_actions(payload)
