"""Exact schema-version-5 ``context_actions`` panel and presenter.

The presenter serializes the frozen combat view owned by
``world.rules.combat_view`` and validates its own output against the exact
bounded schema before returning it to the presentation registry. Inside a
valid active combat session it emits the combat available form (byte-identical
to schema version 4 apart from the version field and the ``suggestions``
envelope); in exploration mode it emits the exploration available form
carrying the canonical affordance vocabulary
(``web.webclient.presentation.affordances``) and the state-backed
``suggestions`` envelope; only outside both modes (creation-pending or absent
location) does it raise :class:`PanelUnavailableError` so the registry emits
the common unavailable form. It never fabricates combat fields outside a
combat session and never fabricates exploration actions inside one.

The panel is read-only: it reconstructs the active session, reads participants
and active-skill previews, and never mutates traits, resources, buffs, sexual
state, battlefield, session, quest, location, or world time.

The ``skills`` field is an ordered array of category groups (each optionally
containing element/line sub-groups); the individual skill descriptor object is
byte-identical to schema version 2.
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
    group_skill_views,
)
from world.rules.progression import (
    FREEFORM_CAST_SCALES,
    scaled_mp_cost,
)
from world.skills.registry import SkillCategory

CONTEXT_ACTIONS_SCHEMA_VERSION = 5

# The exploration form carries the complete canonical affordance vocabulary of
# a room. The bound derives from the shared vocabulary caps (<= 32 targets x
# <= 8 affordances per target, <= 16 scripted keyword pool entries per host,
# <= 12 exits, <= 32 look objects, <= 2 baseline, <= 2 navigation), so a legal
# room can never truncate the list.
MAX_CONTEXT_AFFORDANCES = 320

# Per-affordance-entry bounds of the exploration form.
MAX_AFFORDANCE_LABEL = 128
MAX_AFFORDANCE_PARAM_KEYS = 8
MAX_AFFORDANCE_PARAM_STRING = 512

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


def validate_freeform_scales(value: Any, base_mp: int | None) -> list[dict[str, Any]]:
    """Validate the optional ``freeform_scales`` array of one skill.

    When absent (the server omits the field for every non-eligible skill and
    every non-master) an empty list is returned. When present the array must
    cover exactly the actor's allowed scale set in ascending order, one entry
    per scale, each an exact object with the member numeric ``scale``, its
    canonical ``label`` (the label MUST pair with its scale), and the
    server-computed ``mp_cost`` equal to ``scaled_mp_cost(base_mp, scale)``.
    A skill without an ``mp`` cost can never carry the field.
    """
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
    if len(value) != len(FREEFORM_CAST_SCALES):
        raise ProtocolValidationError(
            "freeform_scales must cover exactly the allowed scale set"
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
    }
    scales = validate_freeform_scales(
        value.get("freeform_scales"),
        cost.get("mp") if isinstance(cost.get("mp"), int) else None,
    )
    if scales:
        normalized["freeform_scales"] = scales
    return normalized


# Stable presentation values the panel emits (mirror of the registry enum).
CATEGORY_KEYS = frozenset(category.value for category in SkillCategory)


def _validate_skill_group(value: Any) -> dict[str, Any]:
    """Validate one ``{group, label, skills}`` object of one category.

    ``group`` and ``label`` are co-nullable: a null group key requires a null
    label and vice versa. The ``skills`` array reuses the unchanged
    per-descriptor ``_validate_skill()`` validator, so every version-2
    descriptor check survives the envelope change verbatim.
    """
    _require_exact_fields(value, "skill group", {"group", "label", "skills"}, {})
    group = value["group"]
    label = value["label"]
    if group is None:
        if label is not None:
            raise ProtocolValidationError(
                "a null group key requires a null label"
            )
    else:
        # A bounded non-empty string, not an identifier: sexual-act sub-groups
        # are keyed by their Traditional Chinese line names (獨處, 羞恥, ...),
        # mirroring the character panel's group-key contract.
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
    """Validate one ``{category, label, groups}`` category-group object."""
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


def _validate_affordance_view(value: Any) -> dict[str, Any]:
    """Validate one discriminated ``AffordanceView`` wire entry."""
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
    """Validate one exact available exploration ``context_actions`` payload."""
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
    # Envelope guarantee (mirrors the version-1 exploration panel): a
    # conforming form must serialize within the OOB envelope limit. The list
    # bound is a ceiling, not a guarantee that any content fits, so an
    # over-limit payload fails closed rather than being emitted.
    if json_byte_size(result) > MAX_CANONICAL_JSON_BYTES:
        raise ContextActionsError(
            "context_actions exploration form exceeds the OOB envelope limit"
        )
    return result


def validate_context_actions(payload: Any) -> dict[str, Any]:
    """Validate one exact available ``context_actions`` payload.

    Returns a normalized payload or raises :class:`ContextActionsError`. The
    common unavailable form is NOT accepted here; the registry handles it.
    The available form dispatches on ``kind``: the combat branch keeps the
    exact version-3 field set, validation, and semantics; the exploration
    branch accepts exactly the schema-version-4 exploration form.
    """
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
            "skills",
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
    if not isinstance(skills, list) or len(skills) > len(SkillCategory):
        raise ContextActionsError("category groups exceed their bound")
    category_views = [_validate_category_group(item) for item in skills]
    skill_views = [
        skill
        for category in category_views
        for sub_group in category["groups"]
        for skill in sub_group["skills"]
    ]
    if len(skill_views) > MAX_SKILLS:
        raise ContextActionsError("flattened skill count exceeds their bound")
    identity_set = {participant["identity"] for participant in participant_views}
    for skill in skill_views:
        for target in skill["targets"]:
            if target not in identity_set:
                raise ContextActionsError(
                    "skill targets must reference a presented participant"
                )
    if len({skill["key"] for skill in skill_views}) != len(skill_views):
        raise ContextActionsError("skill keys must be unique")

    # Combat proposals are out of scope: the combat form always reports the
    # suggestions envelope as exactly unavailable.
    suggestions = validate_suggestions(payload["suggestions"])
    if suggestions != {"status": "unavailable"}:
        raise ContextActionsError("combat suggestions must be exactly unavailable")

    return {
        "schema_version": CONTEXT_ACTIONS_SCHEMA_VERSION,
        "available": True,
        "kind": "combat",
        "session": session,
        "participants": participant_views,
        "root_actions": root_actions,
        "secondary_actions": secondary_actions,
        "skills": category_views,
        "suggestions": suggestions,
    }


def _serialize_skill(skill: Any) -> dict[str, Any]:
    """Serialize one frozen skill descriptor into its exact JSON object."""
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
    }
    if skill.freeform_scales:
        descriptor["freeform_scales"] = [
            {"scale": scale, "label": label, "mp_cost": mp_cost}
            for scale, label, mp_cost in skill.freeform_scales
        ]
    return descriptor


def _serialize_skills(skills: tuple[Any, ...]) -> list[dict[str, Any]]:
    """Serialize the grouped category views into the nested JSON envelope."""
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


def _serialize_suggestions_card(entry: AffordanceView) -> dict[str, Any]:
    """Serialize one ``AffordanceView`` into a deterministic rule card.

    The degraded derivation reuses the canonical affordance payloads the AI
    prompt sees: the card kind pairs with the freeform flag, the action code
    is the entry's canonical code, and the params are the validator-normalized
    payload — so ``degraded`` cards are a strict subset of the same action
    space by construction.
    """
    return {
        "kind": "freeform" if entry.freeform else "known_action",
        "action_code": entry.action_id,
        "label": entry.label,
        "params": dict(entry.params),
    }


def _suggestions_section(
    context: PresentationContext, affordances: tuple[AffordanceView, ...]
) -> dict[str, Any]:
    """Assemble the exploration form's ``suggestions`` envelope (design D-3).

    State-backed rendering rules, in order: an absent or ``unavailable``
    snapshot is inert; every non-``unavailable`` snapshot must carry a
    fingerprint equal to the context's current exploration fingerprint (the
    shared freshness derivation) — a missing or mismatched fingerprint emits
    ``unavailable`` with a bounded diagnostic, never the stale cards, and this
    gate is read-only (scheduling stays with the lifecycle triggers);
    ``generating`` carries the status alone; ``ready`` re-serializes exactly
    the snapshot's displayed cards (a missing or shape-invalid displayed set
    degrades to ``unavailable`` with a bounded diagnostic, never fabricated
    cards); ``degraded`` derives rule cards from ``default_cards`` over the
    very affordance tuple just serialized into the form. ``ready``/``generating``
    never consult ``default_cards`` and ``degraded`` never consults snapshot
    cards.

    Both state-backed branches validate their derived cards through the v5
    shape gate before returning: the affordance vocabulary bounds entity
    display names at 128 code points without a CJK requirement, while the
    suggestion card contract bounds labels at 1..24 CJK code points, so an
    out-of-shape name (an ASCII or over-long display name) must degrade the
    section alone — never the whole panel.
    """
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
    """Return the exact available exploration form for the authenticated puppet."""
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
    """Return the exact available panel for the authenticated puppet.

    Inside a valid active combat session the combat form is emitted
    (byte-identical to schema version 4 apart from the version field and the
    ``suggestions`` envelope pinned to unavailable); in exploration mode the
    exploration available form carries the canonical affordance vocabulary
    and the state-backed suggestions envelope; outside both modes the registry
    emits the shared unavailable form.
    """
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
        }
        for participant in view.participants
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
        "skills": _serialize_skills(view.skills),
        "suggestions": {"status": "unavailable"},
    }
    return validate_context_actions(payload)
