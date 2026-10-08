"""Exact schema-version-1 ``skill_use`` panel and presenter.

The panel is the on-demand SkillBook use preview (change
``skillbook-authoritative-casting`` D1/D2): one owned active skill at one
selected scale, with its server-computed adjusted cost, its ordinary explicit
field targets, and its separate monster openings (each disclosing that the
cast starts combat, and an AREA opening its whole current line-up). The
selection comes only from the copied ``PresentationContext.skill_use`` pair of
the current transport-and-puppet epoch; without one, outside exploration, or
when the skill is no longer an owned active skill, the registry emits the
common unavailable form.

The presenter is read-only: ``world.rules.field_cast.preview_field_skill``
never rolls, stages effects, spends resources, awards practice, creates or
advances the world clock, or persists a combat session. Lists are never
truncated: a room exceeding the bounds renders the unavailable form instead.
"""

from typing import Any

from web.webclient.presentation.combat_panel import (
    TARGET_SPECS,
    _validate_disabled_reason,
    validate_freeform_scales,
)
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_bool,
    _require_exact_fields,
    _require_str,
    _validate_identifier,
)
from web.webclient.presentation.registry import PanelUnavailableError
from world.rules.player_messages import rejection_message, session_reason_message
from world.rules.progression import FREEFORM_SCALE_VALUES
from world.skills.registry import SKILL_REGISTRY

SKILL_USE_SCHEMA_VERSION = 1

MAX_SKILL_KEY = 64
MAX_LABEL = 128
MAX_DESCRIPTION = 512
MAX_COST_KEYS = 8
MAX_CHOICES = 64

# Display names of the resources a skill may spend (the shared HUD labels).
_RESOURCE_LABELS = {"hp": "HP", "mp": "MP", "sp": "SP"}

# The fallback reason when no candidate exists at all for a SINGLE/AREA skill.
_NO_TARGET_REASON = {"code": "no_field_targets", "message": "附近沒有可施放的對象。"}


class SkillUseError(ProtocolValidationError):
    """The available skill_use panel violates its exact bounded schema."""


# ---------------------------------------------------------------------------
# Validation.
# ---------------------------------------------------------------------------


def _validate_identity(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SkillUseError(f"{field} must be an integer")
    if not 1 <= value <= MAX_SAFE_INTEGER:
        raise SkillUseError(f"{field} must be a positive safe integer")
    return value


def _validate_reason_pair(enabled: bool, reason: Any, name: str) -> dict[str, Any] | None:
    normalized = _validate_disabled_reason(reason)
    if not enabled and normalized is None:
        raise SkillUseError(f"a disabled {name} requires a disabled_reason")
    if enabled and normalized is not None:
        raise SkillUseError(f"an enabled {name} must not carry a disabled_reason")
    return normalized


def _validate_label(payload: dict[str, Any], name: str) -> str:
    label = _require_str(payload, "label", maximum=MAX_LABEL)
    if not label.strip():
        raise SkillUseError(f"{name} label must be non-empty")
    return label


def _validate_choices(value: Any, name: str, *, opening: bool) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > MAX_CHOICES:
        raise SkillUseError(f"{name} must be a list of at most {MAX_CHOICES}")
    fields = {"identity", "label", "enabled", "disabled_reason"}
    if opening:
        fields = fields | {"target_ids"}
    seen: set[int] = set()
    normalized: list[dict[str, Any]] = []
    for entry in value:
        _require_exact_fields(entry, name, fields, {})
        identity = _validate_identity(entry["identity"], f"{name} identity")
        if identity in seen:
            raise SkillUseError(f"{name} identities must be unique")
        seen.add(identity)
        enabled = _require_bool(entry, "enabled")
        row = {
            "identity": identity,
            "label": _validate_label(entry, name),
            "enabled": enabled,
            "disabled_reason": _validate_reason_pair(
                enabled, entry["disabled_reason"], name
            ),
        }
        if opening:
            ids = entry["target_ids"]
            if not isinstance(ids, list) or not 1 <= len(ids) <= MAX_CHOICES:
                raise SkillUseError("opening target_ids must hold 1..64 identities")
            unique: set[int] = set()
            for item in ids:
                target_id = _validate_identity(item, "opening target id")
                if target_id in unique:
                    raise SkillUseError("opening target_ids must be unique")
                unique.add(target_id)
            if identity not in unique:
                raise SkillUseError("an opening's target_ids must include its anchor")
            row["target_ids"] = list(ids)
        normalized.append(row)
    return normalized


def validate_skill_use(payload: Any) -> dict[str, Any]:
    """Validate the exact available ``skill_use`` form and return a copy."""
    _require_exact_fields(
        payload,
        "skill_use",
        {"schema_version", "available", "kind", "skill", "scale"},
        {},
    )
    if payload["schema_version"] != SKILL_USE_SCHEMA_VERSION:
        raise SkillUseError("skill_use schema_version mismatch")
    if payload["available"] is not True or payload["kind"] != "skill_use":
        raise SkillUseError("skill_use available form discriminator mismatch")
    scale = payload["scale"]
    if isinstance(scale, bool) or not isinstance(scale, (int, float)):
        raise SkillUseError("skill_use scale must be numeric")
    scale = float(scale)
    if scale not in FREEFORM_SCALE_VALUES and scale != 1.0:
        raise SkillUseError("skill_use scale must be a member of the closed scale set")
    skill = payload["skill"]
    _require_exact_fields(
        skill,
        "skill_use skill",
        {
            "key",
            "label",
            "description",
            "target_spec",
            "usable_out_of_combat",
            "cost",
            "enabled",
            "disabled_reason",
            "targets",
            "openings",
        },
        {"freeform_scales": "optional"},
    )
    key = _validate_identifier(skill["key"], "skill key")
    if len(key) > MAX_SKILL_KEY:
        raise SkillUseError("skill key exceeds its bound")
    label = _validate_label(skill, "skill")
    description = _require_str(skill, "description", maximum=MAX_DESCRIPTION)
    if not description.strip():
        raise SkillUseError("skill description must be non-empty")
    target_spec = skill["target_spec"]
    if target_spec not in TARGET_SPECS:
        raise SkillUseError("skill target_spec is not a stable value")
    usable = _require_bool(skill, "usable_out_of_combat")
    cost = skill["cost"]
    if not isinstance(cost, dict) or len(cost) > MAX_COST_KEYS:
        raise SkillUseError("skill cost must be a bounded object")
    for resource, amount in cost.items():
        _validate_identifier(resource, "cost resource key")
        if isinstance(amount, bool) or not isinstance(amount, int):
            raise SkillUseError("skill cost amount must be an integer")
        if not 0 <= amount <= MAX_SAFE_INTEGER:
            raise SkillUseError("skill cost amount is out of bounds")
    enabled = _require_bool(skill, "enabled")
    disabled_reason = _validate_reason_pair(enabled, skill["disabled_reason"], "skill")
    targets = _validate_choices(skill["targets"], "target", opening=False)
    openings = _validate_choices(skill["openings"], "opening", opening=True)
    if target_spec == "none" and targets:
        raise SkillUseError("a NONE skill carries no targets")
    if target_spec == "self" and len(targets) != 1:
        raise SkillUseError("a SELF skill carries exactly the actor binding")
    if target_spec in ("none", "self") and openings:
        raise SkillUseError("NONE/SELF skills carry no monster openings")
    if {row["identity"] for row in targets} & {row["identity"] for row in openings}:
        raise SkillUseError("a monster opening is never an ordinary target")
    anchors = {row["identity"] for row in openings}
    for row in openings:
        if not set(row["target_ids"]) <= anchors:
            raise SkillUseError("an opening line-up must name advertised monsters")
        if target_spec == "single" and row["target_ids"] != [row["identity"]]:
            raise SkillUseError("a SINGLE opening engages its anchor alone")
    if target_spec in ("single", "area"):
        any_choice = any(row["enabled"] for row in (*targets, *openings))
        if enabled != any_choice:
            raise SkillUseError("skill enabled must equal the existence of a legal choice")
    elif target_spec == "self" and targets[0]["enabled"] != enabled:
        raise SkillUseError("a SELF binding must match the skill verdict")
    # The rung costs are computed from the registry base MP exactly as every
    # other panel advertises them; ``cost`` itself is the adjusted amount.
    registered = SKILL_REGISTRY.get(key)
    base_mp = registered.cost.get("mp") if registered is not None else None
    scales = validate_freeform_scales(skill.get("freeform_scales"), base_mp)
    # No rung-membership check on ``scale``: an unadvertised (forged or since
    # revoked) scale stays readable as a disabled preview carrying the
    # resolver's own scaled-cast reason.
    normalized_skill: dict[str, Any] = {
        "key": key,
        "label": label,
        "description": description,
        "target_spec": target_spec,
        "usable_out_of_combat": usable,
        "cost": dict(cost),
        "enabled": enabled,
        "disabled_reason": disabled_reason,
        "targets": targets,
        "openings": openings,
    }
    if scales:
        normalized_skill["freeform_scales"] = scales
    return {
        "schema_version": SKILL_USE_SCHEMA_VERSION,
        "available": True,
        "kind": "skill_use",
        "skill": normalized_skill,
        "scale": scale,
    }



# ---------------------------------------------------------------------------
# Presenter.
# ---------------------------------------------------------------------------


def _reason(choice: Any, cost: dict[str, int]) -> dict[str, str] | None:
    """The bounded ``{code, message}`` of one disabled preview choice."""
    if choice.enabled:
        return None
    if choice.session_reason is not None:
        return {
            "code": choice.session_reason,
            "message": session_reason_message(choice.session_reason),
        }
    reason = choice.reason
    if reason is None:
        return {"code": "unavailable", "message": "目前無法施放。"}
    message = rejection_message(reason)
    if reason.value == "insufficient_resource" and choice.detail in cost:
        resource = _RESOURCE_LABELS.get(choice.detail, choice.detail.upper())
        message = f"{resource} 不足：需要 {cost[choice.detail]}。"
    return {"code": reason.value, "message": message}


def _entity_name(entity: Any) -> str:
    from world.rules.npc_identity import npc_display_name

    name = npc_display_name(entity).strip() or "？"
    return name[:48]


def _disambiguated_names(entities: list[Any]) -> dict[int, str]:
    """Display names keyed by pk, with an ordinal suffix for shared names.

    Two co-located entities may share a display name; the wire identity is
    what a cast submits, but the player needs to tell the rows apart, so a
    repeated name gains a stable ``（n）`` ordinal in identity order.
    """
    names = {int(entity.pk): _entity_name(entity) for entity in entities}
    counts: dict[str, int] = {}
    for name in names.values():
        counts[name] = counts.get(name, 0) + 1
    seen: dict[str, int] = {}
    result: dict[int, str] = {}
    for pk in sorted(names):
        name = names[pk]
        if counts[name] > 1:
            seen[name] = seen.get(name, 0) + 1
            result[pk] = f"{name}（{seen[name]}）"
        else:
            result[pk] = name
    return result


def _opening_label(name: str, spec: str, line_up_size: int) -> str:
    """A short dock-row label that still discloses the consequence.

    SINGLE names the anchor and the fight; AREA names the anchor and states
    that the whole current line-up joins (never implying the anchor alone).
    """
    if spec == "area" and line_up_size > 1:
        return f"{name}等 {line_up_size} 名（全體開戰）"
    return f"{name}（開戰）"


def _skill_reason(preview: Any) -> dict[str, str] | None:
    """The skill-level reason: the first disabled verdict, choice, or opening."""
    if preview.verdict is not None:
        return _reason(preview.verdict, preview.cost)
    choices = [*preview.targets, *preview.openings]
    if any(choice.enabled for choice in choices):
        return None
    # Monster openings explain a damaging skill better than the ordinary rows
    # (which all carry the damage-requires-monster refusal).
    ordered = (
        [*preview.openings, *preview.targets]
        if preview.openings
        else list(preview.targets)
    )
    for choice in ordered:
        return _reason(choice, preview.cost)
    return dict(_NO_TARGET_REASON)


def skill_use_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``skill_use`` panel for the selection."""
    from web.webclient.presentation.affordances import in_exploration_mode
    from world.rules.field_cast import owned_active_skill, preview_field_skill
    from world.rules.progression import freeform_scale_entries_for

    actor = context.actor
    selection = context.skill_use
    if selection is None or actor is None or not in_exploration_mode(actor):
        raise PanelUnavailableError("no current skill use selection")
    skill_key, scale = selection
    skill = owned_active_skill(actor, skill_key)
    if skill is None:
        raise PanelUnavailableError("the selected skill is no longer usable")
    preview = preview_field_skill(actor, skill, scale)
    if preview.overflow:
        raise PanelUnavailableError("field candidates exceed the panel bound")
    spec = skill.target_spec.value
    names = _disambiguated_names(
        [choice.entity for choice in (*preview.targets, *preview.openings)]
    )
    targets = []
    for choice in preview.targets:
        pk = int(choice.entity.pk)
        label = names[pk]
        if choice.entity is actor:
            label = f"{label}（自己）"
        targets.append(
            {
                "identity": pk,
                "label": label[:MAX_LABEL],
                "enabled": choice.enabled,
                "disabled_reason": _reason(choice, preview.cost),
            }
        )
    openings = []
    for choice in preview.openings:
        pk = int(choice.entity.pk)
        line_up = [int(entity.pk) for entity in choice.line_up] or [pk]
        openings.append(
            {
                "identity": pk,
                "label": _opening_label(names[pk], spec, len(line_up))[:MAX_LABEL],
                "target_ids": line_up,
                "enabled": choice.enabled,
                "disabled_reason": _reason(choice, preview.cost),
            }
        )
    reason = _skill_reason(preview)
    payload_skill: dict[str, Any] = {
        "key": skill.key,
        "label": skill.label,
        "description": skill.description,
        "target_spec": spec,
        "usable_out_of_combat": bool(skill.usable_out_of_combat),
        "cost": dict(preview.cost),
        "enabled": reason is None,
        "disabled_reason": reason,
        "targets": targets,
        "openings": openings,
    }
    scales = freeform_scale_entries_for(actor, skill)
    if scales:
        payload_skill["freeform_scales"] = [
            {"scale": rung, "label": label, "mp_cost": mp_cost}
            for rung, label, mp_cost in scales
        ]
    return validate_skill_use(
        {
            "schema_version": SKILL_USE_SCHEMA_VERSION,
            "available": True,
            "kind": "skill_use",
            "skill": payload_skill,
            "scale": float(scale),
        }
    )
