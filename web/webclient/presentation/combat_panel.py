"""Exact schema-version-7 ``context_actions`` panel and presenter.

The presenter serializes the frozen combat view owned by
``world.rules.combat_view`` and validates its own output against the exact
bounded schema before returning it to the presentation registry. Inside a
valid active combat session it emits the combat available form:
schema_version, available, kind, session, participants, root_actions,
secondary_actions, actors, choices, draft, suggestions.
In exploration mode it emits the exploration available form carrying the canonical
affordance vocabulary and the state-backed suggestions envelope.
Outside both modes it raises :class:`PanelUnavailableError`.
"""

from typing import Any

from web.webclient.presentation.affordances import (
    ACTION_CODE_ALLOWLIST,
    SURFACES,
    AffordanceView,
    default_cards,
    exploration_affordances,
    in_exploration_mode,
)
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import log_unavailable
from web.webclient.presentation.options import (
    OPTIONS_STATUSES,
    _validate_affordance_params,
    validate_suggestions,
)
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_bool,
    _require_exact_fields,
    _require_int,
    _require_str,
    _validate_identifier,
    _validate_message,
    json_byte_size,
)
from web.webclient.presentation.registry import PanelUnavailableError
from world.rules.combat_view import (
    MAX_ACTORS,
    MAX_DISPLAY_NAME_CODE_POINTS,
    MAX_ITEMS,
    MAX_ITEM_SUMMARY_CODE_POINTS,
    MAX_PARTICIPANT_CONDITION_LABEL,
    MAX_PARTICIPANT_CONDITIONS,
    MAX_PARTICIPANTS,
    MAX_REASON_MESSAGE_CODE_POINTS,
    MAX_SESSION_ID_CODE_POINTS,
    MAX_SKILLS,
    MAX_TACTICS,
    RECOVERY_SECONDARY_ACTIONS,
    ROOT_ACTIONS,
    SECONDARY_ACTIONS,
    CombatViewError,
    build_combat_view,
    group_skill_views,
)
from world.rules.progression import (
    FREEFORM_CAST_SCALES,
    scaled_mp_cost,
)
from world.rules.status_display import CONDITION_SEVERITIES
from world.skills.registry import SkillCategory

CONTEXT_ACTIONS_SCHEMA_VERSION = 7

MAX_CONTEXT_AFFORDANCES = 320
MAX_AFFORDANCE_LABEL = 128
MAX_AFFORDANCE_PARAM_KEYS = 8
MAX_AFFORDANCE_PARAM_STRING = 512

MAX_SKILL_KEY = 64
MAX_ITEM_KEY = 64
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
MAX_CONDITION_LABEL = MAX_PARTICIPANT_CONDITION_LABEL

PARTICIPANT_STATES = frozenset({"active", "fled", "knocked_out", "defeated"})
TEAMS = frozenset({"party", "foes"})
MODES = frozenset({"hostile", "guild_exam"})
SESSION_STATES = frozenset({"ready", "recovery"})
TARGET_SPECS = frozenset({"none", "self", "single", "area"})
ITEM_TARGET_SPECS = frozenset({"none", "self", "single"})
TACTIC_KEYS = frozenset({"defend", "dodge", "taunt"})
ALLOWED_SHORTHANDS = frozenset({"all-enemies", "all-allies", "all"})
_FREEFORM_SCALES = frozenset(scale for scale, _label in FREEFORM_CAST_SCALES)


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


def _require_identity(value: Any, name: str) -> int:
    """Validate one bare identity inside a list (never a payload field lookup)."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProtocolValidationError(f"{name} must be an integer")
    if value < 1 or value > MAX_SAFE_INTEGER:
        raise ProtocolValidationError(f"{name} is out of bounds")
    return value


def _validate_session(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "combat session",
        {"session_id", "mode", "round", "round_revision", "state", "reason"},
        {},
    )
    session_id = _require_str(
        value, "session_id", maximum=MAX_SESSION_ID_CODE_POINTS
    )
    if not session_id.strip():
        raise ProtocolValidationError("session_id must be non-empty")
    mode = value["mode"]
    if mode not in MODES:
        raise ProtocolValidationError("session mode must be hostile or guild_exam")
    round_value = _require_int(value, "round", minimum=0, maximum=MAX_SAFE_INTEGER)
    round_revision = _require_int(
        value, "round_revision", minimum=0, maximum=MAX_SAFE_INTEGER
    )
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
        "round_revision": round_revision,
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
            "conditions",
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
    conditions = _validate_participant_conditions(value["conditions"])
    return {
        "identity": identity,
        "token": token,
        "display_name": display_name,
        "team": team,
        "state": state,
        "hp_current": hp_current,
        "hp_maximum": hp_maximum,
        "portrait_ref": portrait_ref,
        "conditions": conditions,
    }


def _validate_participant_conditions(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or len(value) > MAX_PARTICIPANT_CONDITIONS:
        raise ProtocolValidationError(
            f"participant conditions must be a list of at most {MAX_PARTICIPANT_CONDITIONS} rows"
        )
    rows: list[dict[str, str]] = []
    for row in value:
        _require_exact_fields(row, "participant condition", {"code", "label", "severity"}, {})
        code = _validate_identifier(row["code"], "participant condition code")
        label = _require_str(row, "label", maximum=MAX_CONDITION_LABEL)
        if not label.strip():
            raise ProtocolValidationError("participant condition label must be non-empty")
        if row["severity"] not in CONDITION_SEVERITIES:
            raise ProtocolValidationError("participant condition severity is not a stable severity")
        rows.append({"code": code, "label": label, "severity": row["severity"]})
    return rows


def _validate_disabled_reason(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    _require_exact_fields(value, "disabled_reason", {"code", "message"}, {})
    _validate_identifier(value["code"], "disabled_reason code")
    message = _validate_message(value["message"], "disabled_reason message")
    if len(value["code"]) > MAX_REASON_CODE:
        raise ProtocolValidationError("disabled_reason code exceeds its bound")
    return {"code": value["code"], "message": message}


def validate_freeform_scales(value: Any, base_mp: int | None) -> list[dict[str, Any]]:
    if value is None:
        return []
    if base_mp is None or base_mp <= 0:
        raise ProtocolValidationError(
            "a skill without an mp cost cannot carry freeform_scales"
        )
    if not isinstance(value, list) or not value:
        raise ProtocolValidationError(
            "freeform_scales must be a non-empty array when present"
        )
    if len(value) > len(FREEFORM_CAST_SCALES):
        raise ProtocolValidationError(
            "freeform_scales may not exceed the canonical scale table"
        )
    entries: list[dict[str, Any]] = []
    for index, entry in enumerate(value):
        _require_exact_fields(entry, "freeform_scales entry", {"scale", "label", "mp_cost"}, {})
        scale = entry["scale"]
        if isinstance(scale, bool) or not isinstance(scale, (int, float)):
            raise ProtocolValidationError("freeform_scales scale must be numeric")
        scale = float(scale)
        expected_scale, expected_label = FREEFORM_CAST_SCALES[index]
        if scale != expected_scale:
            raise ProtocolValidationError(
                "freeform_scales must be strictly ascending over the allowed set"
            )
        label = _require_str(entry, "label", maximum=8)
        if label != expected_label:
            raise ProtocolValidationError(
                "freeform_scales label must be the canonical label of its scale"
            )
        mp_cost = _require_int(
            entry, "mp_cost", minimum=1, maximum=MAX_SAFE_INTEGER
        )
        if mp_cost != scaled_mp_cost(base_mp, scale):
            raise ProtocolValidationError(
                "freeform_scales mp_cost is inconsistent with the scaled base cost"
            )
        entries.append({"scale": scale, "label": label, "mp_cost": mp_cost})
    return entries


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
            "hostile",
            "beneficial",
        },
        {"freeform_scales": "optional"},
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
    hostile = _require_bool(value, "hostile")
    beneficial = _require_bool(value, "beneficial")
    normalized = {
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
        "hostile": hostile,
        "beneficial": beneficial,
    }
    scales = validate_freeform_scales(
        value.get("freeform_scales"),
        cost.get("mp") if isinstance(cost.get("mp"), int) else None,
    )
    if scales:
        normalized["freeform_scales"] = scales
    return normalized


CATEGORY_KEYS = frozenset(category.value for category in SkillCategory)


def _validate_skill_group(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "skill group", {"group", "label", "skills"}, {})
    group = value["group"]
    label = value["label"]
    if group is None:
        if label is not None:
            raise ProtocolValidationError(
                "a null group key requires a null label"
            )
    else:
        group = _require_str(value, "group", maximum=MAX_SKILL_KEY)
        if not group.strip():
            raise ProtocolValidationError(
                "a non-null group key requires a non-empty label"
            )
        if not isinstance(label, str) or not label.strip():
            raise ProtocolValidationError(
                "a non-null group key requires a non-empty label"
            )
    skills = value["skills"]
    if not isinstance(skills, list) or not skills:
        raise ProtocolValidationError("skill group skills must be non-empty")
    return {
        "group": group,
        "label": label,
        "skills": [_validate_skill(item) for item in skills],
    }


def _validate_category_group(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value, "category group", {"category", "label", "groups"}, {}
    )
    category = _validate_identifier(value["category"], "category key")
    if category not in CATEGORY_KEYS:
        raise ProtocolValidationError("category key is not a registered category")
    label = _require_str(value, "label", maximum=MAX_LABEL)
    if not label.strip():
        raise ProtocolValidationError("category label must be non-empty")
    groups = value["groups"]
    if not isinstance(groups, list) or not groups:
        raise ProtocolValidationError("category groups must be non-empty")
    return {
        "category": category,
        "label": label,
        "groups": [_validate_skill_group(item) for item in groups],
    }


def _validate_item_choice(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "item choice",
        {
            "item_key",
            "label",
            "summary",
            "quantity",
            "enabled",
            "reason",
            "target_spec",
            "targets",
            "hostile",
            "beneficial",
        },
        {},
    )
    item_key = _require_str(value, "item_key", maximum=MAX_ITEM_KEY)
    if not item_key.strip():
        raise ProtocolValidationError("item_key must be non-empty")
    label = _require_str(value, "label", maximum=MAX_LABEL)
    if not label.strip():
        raise ProtocolValidationError("item label must be non-empty")
    summary = _require_str(value, "summary", maximum=MAX_ITEM_SUMMARY_CODE_POINTS)
    quantity = _require_int(value, "quantity", minimum=0, maximum=MAX_SAFE_INTEGER)
    enabled = _require_bool(value, "enabled")
    reason = _validate_disabled_reason(value["reason"])
    if not enabled and reason is None:
        raise ProtocolValidationError("a disabled item requires a reason")
    if enabled and reason is not None:
        raise ProtocolValidationError("an enabled item must not carry a reason")
    target_spec = value["target_spec"]
    if target_spec not in ITEM_TARGET_SPECS:
        raise ProtocolValidationError("item target_spec is not a stable value")
    targets = value["targets"]
    if not isinstance(targets, list) or len(targets) > MAX_PARTICIPANTS:
        raise ProtocolValidationError("item targets exceed participant bound")
    seen: set[int] = set()
    for target in targets:
        if isinstance(target, bool) or not isinstance(target, int) or target <= 0:
            raise ProtocolValidationError("item targets must be positive integers")
        if target in seen:
            raise ProtocolValidationError("item targets must be unique")
        seen.add(target)
    hostile = _require_bool(value, "hostile")
    beneficial = _require_bool(value, "beneficial")
    return {
        "item_key": item_key,
        "label": label,
        "summary": summary,
        "quantity": quantity,
        "enabled": enabled,
        "reason": reason,
        "target_spec": target_spec,
        "targets": list(targets),
        "hostile": hostile,
        "beneficial": beneficial,
    }


def _validate_tactic_choice(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "tactic choice",
        {"key", "label", "enabled", "reason", "targets"},
        {},
    )
    key = value["key"]
    if key not in TACTIC_KEYS:
        raise ProtocolValidationError("tactic key is not defend, dodge, or taunt")
    label = _require_str(value, "label", maximum=MAX_LABEL)
    if not label.strip():
        raise ProtocolValidationError("tactic label must be non-empty")
    enabled = _require_bool(value, "enabled")
    reason = _validate_disabled_reason(value["reason"])
    if not enabled and reason is None:
        raise ProtocolValidationError("a disabled tactic requires a reason")
    if enabled and reason is not None:
        raise ProtocolValidationError("an enabled tactic must not carry a reason")
    targets = value["targets"]
    if not isinstance(targets, list) or len(targets) > MAX_PARTICIPANTS:
        raise ProtocolValidationError("tactic targets exceed participant bound")
    if key in {"defend", "dodge"} and targets:
        raise ProtocolValidationError(f"{key} tactic must have empty targets")
    seen: set[int] = set()
    for target in targets:
        if isinstance(target, bool) or not isinstance(target, int) or target <= 0:
            raise ProtocolValidationError("tactic targets must be positive integers")
        if target in seen:
            raise ProtocolValidationError("tactic targets must be unique")
        seen.add(target)
    return {
        "key": key,
        "label": label,
        "enabled": enabled,
        "reason": reason,
        "targets": list(targets),
    }


def _validate_actor_summary(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "actor summary", {"identity", "commandable", "reason"}, {})
    identity = _require_int(value, "identity", minimum=1, maximum=MAX_SAFE_INTEGER)
    commandable = _require_bool(value, "commandable")
    reason = _validate_disabled_reason(value["reason"])
    if commandable and reason is not None:
        raise ProtocolValidationError("a commandable actor must have a null reason")
    if not commandable and reason is None:
        raise ProtocolValidationError("a non-commandable actor requires a reason")
    return {
        "identity": identity,
        "commandable": commandable,
        "reason": reason,
    }


def _validate_choices(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "choices", {"actor_id", "skills", "items", "tactics"}, {})
    actor_id = _require_int(value, "actor_id", minimum=1, maximum=MAX_SAFE_INTEGER)
    skills = value["skills"]
    if not isinstance(skills, list) or len(skills) > len(SkillCategory):
        raise ProtocolValidationError("category groups exceed their bound")
    category_views = [_validate_category_group(item) for item in skills]
    skill_views = [
        skill
        for category in category_views
        for sub_group in category["groups"]
        for skill in sub_group["skills"]
    ]
    if len(skill_views) > MAX_SKILLS:
        raise ProtocolValidationError("flattened skill count exceeds their bound")
    if len({skill["key"] for skill in skill_views}) != len(skill_views):
        raise ProtocolValidationError("skill keys must be unique")

    items = value["items"]
    if not isinstance(items, list) or len(items) > MAX_ITEMS:
        raise ProtocolValidationError("item choices exceed bound")
    item_views = [_validate_item_choice(item) for item in items]
    if len({item["item_key"] for item in item_views}) != len(item_views):
        raise ProtocolValidationError("item keys must be unique")

    tactics = value["tactics"]
    if not isinstance(tactics, list) or len(tactics) > MAX_TACTICS:
        raise ProtocolValidationError("tactic choices exceed bound")
    tactic_views = [_validate_tactic_choice(item) for item in tactics]
    if len({tactic["key"] for tactic in tactic_views}) != len(tactic_views):
        raise ProtocolValidationError("tactic keys must be unique")

    return {
        "actor_id": actor_id,
        "skills": category_views,
        "items": item_views,
        "tactics": tactic_views,
    }


def _validate_draft_command(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "draft command", {"kind", "payload"}, {})
    kind = value["kind"]
    payload = value["payload"]
    if not isinstance(payload, dict):
        raise ProtocolValidationError("draft command payload must be a dict")
    if kind == "skill":
        _require_exact_fields(
            payload,
            "skill draft command payload",
            {"skill_key"},
            {
                "target_ids": "optional",
                "target_shorthand": "optional",
                "scale": "optional",
            },
        )
        key = _validate_identifier(payload["skill_key"], "skill_key")
        if key == "flee":
            raise ProtocolValidationError("flee is forbidden in draft entries")
        target_ids = payload.get("target_ids")
        target_shorthand = payload.get("target_shorthand")
        if target_ids is not None and target_shorthand is not None:
            raise ProtocolValidationError(
                "a skill draft command carries target_ids or target_shorthand, not both"
            )
        if target_ids is not None:
            if (
                not isinstance(target_ids, list)
                or not target_ids
                or len(target_ids) > MAX_SKILL_TARGETS
            ):
                raise ProtocolValidationError(
                    "skill draft target_ids exceed their bound"
                )
            seen_ids: set[int] = set()
            for target_id in target_ids:
                if isinstance(target_id, bool) or not isinstance(target_id, int) or target_id <= 0:
                    raise ProtocolValidationError(
                        "skill draft target_ids must be positive integers"
                    )
                if target_id in seen_ids:
                    raise ProtocolValidationError(
                        "skill draft target_ids must be unique"
                    )
                seen_ids.add(target_id)
        if target_shorthand is not None and target_shorthand not in ALLOWED_SHORTHANDS:
            raise ProtocolValidationError(
                "skill draft target_shorthand is not an approved shorthand"
            )
        scale = payload.get("scale")
        if scale is not None:
            if isinstance(scale, bool) or not isinstance(scale, (int, float)):
                raise ProtocolValidationError("skill draft scale must be numeric")
            if float(scale) not in _FREEFORM_SCALES:
                raise ProtocolValidationError("skill draft scale is not an approved scale")
    elif kind == "item":
        _require_exact_fields(
            payload,
            "item draft command payload",
            {"item_key"},
            {"target_id": "optional"},
        )
        item_key = _require_str(payload, "item_key", maximum=MAX_ITEM_KEY)
        if not item_key.strip():
            raise ProtocolValidationError("item_key must be non-empty")
        if payload.get("target_id") is not None:
            _require_int(payload, "target_id", minimum=1, maximum=MAX_SAFE_INTEGER)
    elif kind == "tactical":
        _require_exact_fields(
            payload,
            "tactical draft command payload",
            {"key"},
            {"target_id": "optional"},
        )
        tactical_key = payload["key"]
        if tactical_key not in TACTIC_KEYS:
            raise ProtocolValidationError("tactical draft key must be defend, dodge, or taunt")
        target_id = payload.get("target_id")
        if tactical_key == "taunt":
            if target_id is None:
                raise ProtocolValidationError("a taunt draft command requires a target_id")
            _require_int(payload, "target_id", minimum=1, maximum=MAX_SAFE_INTEGER)
        elif target_id is not None:
            raise ProtocolValidationError(f"{tactical_key} must have no target_id")
    else:
        raise ProtocolValidationError(f"unknown draft command kind {kind}")
    return {"kind": kind, "payload": dict(payload)}


def _validate_draft_entry(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "draft entry", {"actor_id", "command"}, {})
    actor_id = _require_int(value, "actor_id", minimum=1, maximum=MAX_SAFE_INTEGER)
    command = _validate_draft_command(value["command"])
    return {"actor_id": actor_id, "command": command}


def _validate_reselection_reason(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "reselection reason", {"actor_id", "reason"}, {})
    actor_id = _require_int(value, "actor_id", minimum=1, maximum=MAX_SAFE_INTEGER)
    reason = _validate_disabled_reason(value["reason"])
    if reason is None:
        raise ProtocolValidationError("reselection reason cannot be null")
    return {"actor_id": actor_id, "reason": reason}


def _validate_draft_progress(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "draft progress",
        {
            "round_revision",
            "draft_version",
            "required_actor_ids",
            "entries",
            "needs_selection_ids",
            "reselection_reasons",
        },
        {},
    )
    round_revision = _require_int(
        value, "round_revision", minimum=0, maximum=MAX_SAFE_INTEGER
    )
    draft_version = _require_int(
        value, "draft_version", minimum=0, maximum=MAX_SAFE_INTEGER
    )
    req_ids = value["required_actor_ids"]
    if not isinstance(req_ids, list) or len(req_ids) > MAX_ACTORS:
        raise ProtocolValidationError("required_actor_ids exceeds actor bound")
    seen_req = set()
    for aid in req_ids:
        _require_identity(aid, "required actor id")
        if aid in seen_req:
            raise ProtocolValidationError("required_actor_ids must be unique")
        seen_req.add(aid)

    entries = value["entries"]
    if not isinstance(entries, list) or len(entries) > MAX_ACTORS:
        raise ProtocolValidationError("draft entries exceed actor bound")
    seen_entries = set()
    entry_views = []
    for entry in entries:
        validated_entry = _validate_draft_entry(entry)
        eaid = validated_entry["actor_id"]
        if eaid not in seen_req:
            raise ProtocolValidationError("draft entry actor must be in required_actor_ids")
        if eaid in seen_entries:
            raise ProtocolValidationError("draft entries must have unique actor IDs")
        seen_entries.add(eaid)
        entry_views.append(validated_entry)

    needs_ids = value["needs_selection_ids"]
    if not isinstance(needs_ids, list) or len(needs_ids) > MAX_ACTORS:
        raise ProtocolValidationError("needs_selection_ids exceeds actor bound")
    seen_needs = set()
    for aid in needs_ids:
        _require_identity(aid, "needs selection actor id")
        if aid not in seen_req:
            raise ProtocolValidationError("needs_selection_ids actor must be in required_actor_ids")
        if aid in seen_needs:
            raise ProtocolValidationError("needs_selection_ids must be unique")
        seen_needs.add(aid)

    reasons = value["reselection_reasons"]
    if not isinstance(reasons, list) or len(reasons) > MAX_ACTORS:
        raise ProtocolValidationError("reselection_reasons exceeds actor bound")
    seen_reasons = set()
    reason_views = []
    for r in reasons:
        validated_r = _validate_reselection_reason(r)
        raid = validated_r["actor_id"]
        if raid not in seen_req:
            raise ProtocolValidationError("reselection reason actor must be in required_actor_ids")
        if raid not in seen_needs:
            raise ProtocolValidationError("reselection reason actor must be in needs_selection_ids")
        if raid in seen_reasons:
            raise ProtocolValidationError("reselection reasons must have unique actor IDs")
        seen_reasons.add(raid)
        reason_views.append(validated_r)

    return {
        "round_revision": round_revision,
        "draft_version": draft_version,
        "required_actor_ids": list(req_ids),
        "entries": entry_views,
        "needs_selection_ids": list(needs_ids),
        "reselection_reasons": reason_views,
    }


def _validate_affordance_view(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProtocolValidationError("affordance must be a JSON object")
    navigation = value.get("navigation")
    if not isinstance(navigation, bool):
        raise ProtocolValidationError("affordance navigation must be a boolean")
    label = _require_str(value, "label", maximum=MAX_AFFORDANCE_LABEL)
    if not label.strip():
        raise ProtocolValidationError("affordance label must be non-empty")
    enabled = _require_bool(value, "enabled")
    disabled_reason = _validate_disabled_reason(value["disabled_reason"])
    if disabled_reason is None:
        if not enabled:
            raise ProtocolValidationError("a disabled affordance requires a disabled_reason")
    elif enabled:
        raise ProtocolValidationError("an enabled affordance must not carry a disabled_reason")
    if navigation:
        _require_exact_fields(
            value,
            "navigation affordance",
            {"surface", "label", "navigation", "enabled", "disabled_reason"},
            {},
        )
        surface = value["surface"]
        if surface not in SURFACES:
            raise ProtocolValidationError("affordance surface is not a stable value")
        return {
            "surface": surface,
            "label": label,
            "navigation": True,
            "enabled": enabled,
            "disabled_reason": disabled_reason,
        }
    _require_exact_fields(
        value,
        "action affordance",
        {"action_id", "label", "params", "freeform", "navigation", "enabled", "disabled_reason"},
        {},
    )
    action_id = _validate_identifier(value["action_id"], "action_id")
    if action_id not in ACTION_CODE_ALLOWLIST:
        raise ProtocolValidationError("action_id is not a registered exploration action")
    freeform = value["freeform"]
    if not isinstance(freeform, bool):
        raise ProtocolValidationError("affordance freeform must be a boolean")
    if freeform != (action_id == "explore.talk_freeform"):
        raise ProtocolValidationError(
            "freeform must be true exactly for explore.talk_freeform"
        )
    params_value = value["params"]
    if not isinstance(params_value, dict):
        raise ProtocolValidationError("affordance params must be a JSON object")
    if len(params_value) > MAX_AFFORDANCE_PARAM_KEYS:
        raise ProtocolValidationError("affordance params exceed their bound")
    for key, child in params_value.items():
        if isinstance(child, str) and len(child) > MAX_AFFORDANCE_PARAM_STRING:
            raise ProtocolValidationError("affordance params string exceeds its bound")
    params = _validate_affordance_params(action_id, params_value)
    return {
        "action_id": action_id,
        "label": label,
        "params": params,
        "freeform": freeform,
        "navigation": False,
        "enabled": enabled,
        "disabled_reason": disabled_reason,
    }


def _validate_exploration_form(payload: Any) -> dict[str, Any]:
    _require_exact_fields(
        payload,
        "context_actions exploration form",
        {"schema_version", "available", "kind", "affordances", "suggestions"},
        {},
    )
    if _require_int(
        payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER
    ) != CONTEXT_ACTIONS_SCHEMA_VERSION:
        raise ContextActionsError("unsupported context_actions schema_version")
    if not _require_bool(payload, "available"):
        raise ContextActionsError("available must be true for the exploration form")
    if payload["kind"] != "exploration":
        raise ContextActionsError("exploration panel kind must be exploration")
    affordances = payload["affordances"]
    if not isinstance(affordances, list) or len(affordances) > MAX_CONTEXT_AFFORDANCES:
        raise ContextActionsError(
            f"affordances must be a list of at most {MAX_CONTEXT_AFFORDANCES} entries"
        )
    views = [_validate_affordance_view(entry) for entry in affordances]
    suggestions = validate_suggestions(payload["suggestions"])
    result = {
        "schema_version": CONTEXT_ACTIONS_SCHEMA_VERSION,
        "available": True,
        "kind": "exploration",
        "affordances": views,
        "suggestions": suggestions,
    }
    if json_byte_size(result) > MAX_CANONICAL_JSON_BYTES:
        raise ContextActionsError(
            "context_actions exploration form exceeds the OOB envelope limit"
        )
    return result


def validate_context_actions(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or "kind" not in payload:
        raise ContextActionsError("context_actions payload must carry a kind discriminator")
    if payload["kind"] == "exploration":
        return _validate_exploration_form(payload)
    if payload["kind"] != "combat":
        raise ContextActionsError("context_actions kind is not a stable value")

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
            "actors",
            "choices",
            "draft",
            "suggestions",
        },
        {},
    )
    if _require_int(
        payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER
    ) != CONTEXT_ACTIONS_SCHEMA_VERSION:
        raise ContextActionsError("unsupported context_actions schema_version")
    if not _require_bool(payload, "available"):
        raise ContextActionsError("available must be true for the combat form")

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

    actors_raw = payload["actors"]
    if not isinstance(actors_raw, list) or len(actors_raw) > MAX_ACTORS:
        raise ContextActionsError("actors exceed bound")
    seen_actors: set[int] = set()
    actor_views = []
    for a in actors_raw:
        va = _validate_actor_summary(a)
        if va["identity"] in seen_actors:
            raise ContextActionsError("actors must have unique identities")
        seen_actors.add(va["identity"])
        actor_views.append(va)

    if session["state"] == "ready":
        if set(root_actions) != set(ROOT_ACTIONS) or list(root_actions) != list(ROOT_ACTIONS):
            raise ContextActionsError("ready session must expose the exact root actions")
        if list(secondary_actions) != list(SECONDARY_ACTIONS):
            raise ContextActionsError("ready session must expose confirmed Surrender")
        if payload["choices"] is None:
            raise ContextActionsError("ready session must have choices")
        choices_view = _validate_choices(payload["choices"])
        if choices_view["actor_id"] not in seen_actors:
            raise ContextActionsError("choices actor_id must reference an actor summary")

        if payload["draft"] is None:
            raise ContextActionsError("ready session must have draft")
        draft_view = _validate_draft_progress(payload["draft"])
        if draft_view["round_revision"] != session["round_revision"]:
            raise ContextActionsError("draft round_revision must match session round_revision")

        identity_set = {p["identity"] for p in participant_views}
        for cat in choices_view["skills"]:
            for grp in cat["groups"]:
                for sk in grp["skills"]:
                    for tid in sk["targets"]:
                        if tid not in identity_set:
                            raise ContextActionsError("skill targets must reference a presented participant")
        for item in choices_view["items"]:
            for tid in item["targets"]:
                if tid not in identity_set:
                    raise ContextActionsError("item targets must reference a presented participant")
        for tactic in choices_view["tactics"]:
            for tid in tactic["targets"]:
                if tid not in identity_set:
                    raise ContextActionsError("tactic targets must reference a presented participant")

    else:
        if root_actions:
            raise ContextActionsError("recovery session exposes no root actions")
        if list(secondary_actions) != list(RECOVERY_SECONDARY_ACTIONS):
            raise ContextActionsError("recovery session must retain confirmed Surrender")
        if actor_views:
            raise ContextActionsError("recovery session actors must be empty")
        if payload["choices"] is not None:
            raise ContextActionsError("recovery session choices must be null")
        if payload["draft"] is not None:
            raise ContextActionsError("recovery session draft must be null")
        choices_view = None
        draft_view = None

    suggestions = validate_suggestions(payload["suggestions"])
    if suggestions != {"status": "unavailable"}:
        raise ContextActionsError("combat suggestions must be exactly unavailable")

    result = {
        "schema_version": CONTEXT_ACTIONS_SCHEMA_VERSION,
        "available": True,
        "kind": "combat",
        "session": session,
        "participants": participant_views,
        "root_actions": root_actions,
        "secondary_actions": secondary_actions,
        "actors": actor_views,
        "choices": choices_view,
        "draft": draft_view,
        "suggestions": suggestions,
    }
    if json_byte_size(result) > MAX_CANONICAL_JSON_BYTES:
        raise ContextActionsError("context_actions combat form exceeds the OOB envelope limit")
    return result


def _serialize_skill(skill: Any) -> dict[str, Any]:
    descriptor = {
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
        "hostile": skill.hostile,
        "beneficial": skill.beneficial,
    }
    if skill.freeform_scales:
        descriptor["freeform_scales"] = [
            {"scale": scale, "label": label, "mp_cost": mp_cost}
            for scale, label, mp_cost in skill.freeform_scales
        ]
    return descriptor


def _serialize_skills(skills: tuple[Any, ...]) -> list[dict[str, Any]]:
    categories: list[dict[str, Any]] = []
    for category in group_skill_views(skills):
        categories.append(
            {
                "category": category.category,
                "label": category.label,
                "groups": [
                    {
                        "group": sub_group.group,
                        "label": sub_group.label,
                        "skills": [
                            _serialize_skill(skill)
                            for skill in sub_group.skills
                        ],
                    }
                    for sub_group in category.groups
                ],
            }
        )
    return categories


def _serialize_choices(choices: Any) -> dict[str, Any] | None:
    if choices is None:
        return None
    skills_cat = []
    for cat in choices.skills:
        skills_cat.append(
            {
                "category": cat.category,
                "label": cat.label,
                "groups": [
                    {
                        "group": grp.group,
                        "label": grp.label,
                        "skills": [_serialize_skill(s) for s in grp.skills],
                    }
                    for grp in cat.groups
                ],
            }
        )
    items = [
        {
            "item_key": item.item_key,
            "label": item.label,
            "summary": item.summary,
            "quantity": item.quantity,
            "enabled": item.enabled,
            "reason": (
                None
                if item.reason is None
                else {"code": item.reason[0], "message": item.reason[1]}
            ),
            "target_spec": item.target_spec,
            "targets": list(item.targets),
            "hostile": item.hostile,
            "beneficial": item.beneficial,
        }
        for item in choices.items
    ]
    tactics = [
        {
            "key": tac.key,
            "label": tac.label,
            "enabled": tac.enabled,
            "reason": (
                None
                if tac.reason is None
                else {"code": tac.reason[0], "message": tac.reason[1]}
            ),
            "targets": list(tac.targets),
        }
        for tac in choices.tactics
    ]
    return {
        "actor_id": choices.actor_id,
        "skills": skills_cat,
        "items": items,
        "tactics": tactics,
    }


def _serialize_draft(draft: Any) -> dict[str, Any] | None:
    if draft is None:
        return None
    entries = [
        {"actor_id": e.actor_id, "command": dict(e.command)}
        for e in draft.entries
    ]
    reasons = [
        {
            "actor_id": r.actor_id,
            "reason": {"code": r.reason[0], "message": r.reason[1]},
        }
        for r in draft.reselection_reasons
    ]
    return {
        "round_revision": draft.round_revision,
        "draft_version": draft.draft_version,
        "required_actor_ids": list(draft.required_actor_ids),
        "entries": entries,
        "needs_selection_ids": list(draft.needs_selection_ids),
        "reselection_reasons": reasons,
    }


def _serialize_suggestions_card(entry: AffordanceView) -> dict[str, Any]:
    return {
        "kind": "freeform" if entry.freeform else "known_action",
        "action_code": entry.action_id,
        "label": entry.label,
        "params": dict(entry.params),
    }


def _suggestions_section(
    context: PresentationContext, affordances: tuple[AffordanceView, ...]
) -> dict[str, Any]:
    snapshot = context.options_state
    if snapshot is None or snapshot.status not in OPTIONS_STATUSES or snapshot.status == "unavailable":
        return {"status": "unavailable"}
    if context.options_fingerprint is None or snapshot.fingerprint != context.options_fingerprint:
        log_unavailable(
            "exploration suggestions",
            "snapshot fingerprint no longer matches the current situation",
        )
        return {"status": "unavailable"}
    if snapshot.status == "generating":
        return {"status": "generating"}
    if snapshot.status == "degraded":
        cards = [
            _serialize_suggestions_card(entry)
            for entry in default_cards(affordances, actor=context.actor)
        ]
        try:
            return validate_suggestions({"status": "degraded", "cards": cards})
        except ProtocolValidationError:
            log_unavailable(
                "exploration suggestions",
                "degraded derivation fails the v5 shape gate",
            )
            return {"status": "unavailable"}
    displayed = snapshot.displayed
    if displayed is None:
        log_unavailable(
            "exploration suggestions",
            "ready snapshot carries no displayed set",
        )
        return {"status": "unavailable"}
    cards = [card.as_dict() for card in displayed]
    try:
        return validate_suggestions({"status": "ready", "cards": cards})
    except ProtocolValidationError:
        log_unavailable(
            "exploration suggestions",
            "ready displayed set fails the v5 shape gate",
        )
        return {"status": "unavailable"}


def _exploration_payload(context: PresentationContext) -> dict[str, Any]:
    actor = context.actor
    if not in_exploration_mode(actor):
        raise PanelUnavailableError
    location = getattr(actor, "location", None)
    if location is None:
        raise PanelUnavailableError
    affordances = exploration_affordances(actor)
    payload = {
        "schema_version": CONTEXT_ACTIONS_SCHEMA_VERSION,
        "available": True,
        "kind": "exploration",
        "affordances": [entry.as_dict() for entry in affordances],
        "suggestions": _suggestions_section(context, affordances),
    }
    return validate_context_actions(payload)


def context_actions_presenter(context: PresentationContext) -> dict[str, Any]:
    actor = context.actor
    try:
        view = build_combat_view(actor)
    except CombatViewError:
        return _exploration_payload(context)

    if view.recovery:
        session = {
            "session_id": view.session.session_id,
            "mode": view.session.mode,
            "round": view.session.round,
            "round_revision": view.session.round_revision,
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
            "actors": [],
            "choices": None,
            "draft": None,
            "suggestions": {"status": "unavailable"},
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
            "conditions": [
                {"code": row.code, "label": row.label, "severity": row.severity}
                for row in participant.conditions
            ],
        }
        for participant in view.participants
    ]
    actors = [
        {
            "identity": a.identity,
            "commandable": a.commandable,
            "reason": (
                None
                if a.reason is None
                else {"code": a.reason[0], "message": a.reason[1]}
            ),
        }
        for a in view.actors
    ]

    payload = {
        "schema_version": CONTEXT_ACTIONS_SCHEMA_VERSION,
        "available": True,
        "kind": "combat",
        "session": {
            "session_id": view.session.session_id,
            "mode": view.session.mode,
            "round": view.session.round,
            "round_revision": view.session.round_revision,
            "state": "ready",
            "reason": None,
        },
        "participants": participants,
        "root_actions": list(ROOT_ACTIONS),
        "secondary_actions": list(SECONDARY_ACTIONS),
        "actors": actors,
        "choices": _serialize_choices(view.choices),
        "draft": _serialize_draft(view.draft),
        "suggestions": {"status": "unavailable"},
    }
    return validate_context_actions(payload)
