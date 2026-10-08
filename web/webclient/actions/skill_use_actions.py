"""Exact SkillBook use payload validators and narrow adapters.

``explore.skill_preview`` selects one owned active skill (and an optional
scale) for the session's on-demand ``skill_use`` panel; it is presentation
work only and never rolls, spends, awards practice, touches the world clock,
or creates a combat session. ``explore.cast`` performs one field cast through
the deterministic ``world.rules.field_cast.cast_in_field`` entry after
re-resolving every submitted identity from the actor's current co-located
candidates. Neither action routes through the text command parser, and no
payload accepts an actor, context, cost, shorthand, or roster field.
"""

from typing import Any

from web.webclient.presentation.protocol import MAX_SAFE_INTEGER
from world.rules.progression import FREEFORM_SCALE_VALUES

MAX_SKILL_KEY_CODE_POINTS = 64
MAX_TARGET_IDS = 64

# The reserved skill that keeps its own graphical route (combat.flee).
RESERVED_FLEE_KEY = "flee"

# Panels: the preview publishes the one panel it changes; a cast changes
# time, resources, proficiency, mode, and more, so its completion (accepted,
# rejected, or failed) always publishes a full canonical snapshot.
AFFECTED_PREVIEW = ("skill_use",)
AFFECTED_CAST: tuple[str, ...] = ()

# Stable adapter-boundary rejections (the domain owns every other reason).
_NOT_EXPLORATION = ("not_in_exploration", "只有在戰鬥外才能從技能書施放。")
_TARGET_GONE = ("target_not_present", "目標不在這裡。")
_MONSTER_NEEDS_OPENING = (
    "monster_requires_opening",
    "對魔物施放會開啟戰鬥，請改用開戰選項。",
)


class SkillUseActionError(ValueError):
    """A SkillBook use payload violates its exact bounded schema."""


def _skill_key(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not value
        or sum(1 for _ in value) > MAX_SKILL_KEY_CODE_POINTS
        or any(character.isspace() for character in value)
    ):
        raise SkillUseActionError("skill_key must be a bounded key")
    return value


def _scale(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SkillUseActionError("scale must be a number")
    scale = float(value)
    if scale != 1.0 and scale not in FREEFORM_SCALE_VALUES:
        raise SkillUseActionError("scale must be a member of the freeform scale set")
    return scale


def _identity(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SkillUseActionError(f"{field} must be an integer")
    if not 1 <= value <= MAX_SAFE_INTEGER:
        raise SkillUseActionError(f"{field} must be a positive safe integer")
    return value


def validate_skill_preview_payload(payload: Any) -> dict[str, Any]:
    """Validate ``{skill_key[, scale]}`` for ``explore.skill_preview``."""
    if not isinstance(payload, dict):
        raise SkillUseActionError("explore.skill_preview payload must be an object")
    unknown = set(payload) - {"skill_key", "scale"}
    if unknown or "skill_key" not in payload:
        raise SkillUseActionError("explore.skill_preview requires skill_key and optional scale")
    return {
        "skill_key": _skill_key(payload["skill_key"]),
        "scale": _scale(payload.get("scale", 1.0)),
    }


def validate_field_cast_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact ``explore.cast`` payload.

    ``{skill_key[, scale]}`` plus at most one target form: ``target_ids`` (a
    non-empty unique list of at most 64 positive safe identities, in
    presenter order) or ``opening_target_id`` (one monster anchor). Target
    cardinality against the skill's TargetSpec is a domain rejection, not a
    schema failure, so a stale but well-formed request reads its real reason.
    """
    if not isinstance(payload, dict):
        raise SkillUseActionError("explore.cast payload must be an object")
    unknown = set(payload) - {"skill_key", "scale", "target_ids", "opening_target_id"}
    if unknown or "skill_key" not in payload:
        raise SkillUseActionError("explore.cast has unknown fields or no skill_key")
    if "target_ids" in payload and "opening_target_id" in payload:
        raise SkillUseActionError("explore.cast target forms are mutually exclusive")
    skill_key = _skill_key(payload["skill_key"])
    if skill_key == RESERVED_FLEE_KEY:
        raise SkillUseActionError("explore.cast never carries the reserved flee skill")
    normalized: dict[str, Any] = {
        "skill_key": skill_key,
        "scale": _scale(payload.get("scale", 1.0)),
        "target_ids": (),
        "opening_target_id": None,
    }
    if "target_ids" in payload:
        ids = payload["target_ids"]
        if not isinstance(ids, list) or not 1 <= len(ids) <= MAX_TARGET_IDS:
            raise SkillUseActionError("explore.cast target_ids must hold 1..64 identities")
        seen: set[int] = set()
        for item in ids:
            identity = _identity(item, "target_ids item")
            if identity in seen:
                raise SkillUseActionError("explore.cast target_ids must be unique")
            seen.add(identity)
        normalized["target_ids"] = tuple(ids)
    if "opening_target_id" in payload:
        normalized["opening_target_id"] = _identity(
            payload["opening_target_id"], "opening_target_id"
        )
    return normalized


def _rejected(code: str, message: str) -> dict[str, Any]:
    return {
        "outcome": "rejected",
        "code": code,
        "message": message,
        "affected_panels": AFFECTED_CAST,
    }


def _skill_preview_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Record the preview selection; the dispatcher publishes ``skill_use``."""
    from web.webclient.presentation.skill_use_selection import select_skill_use

    result = dict(select_skill_use(session, actor, payload["skill_key"], payload["scale"]))
    result["affected_panels"] = AFFECTED_PREVIEW
    return result


def _field_cast_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Re-resolve identities and cast through the shared field entry.

    The mode is rechecked first (an admitted stale field request after combat
    began never settles). Ordinary identities resolve only among the actor's
    current visible co-located field candidates; a monster in that list is
    refused (monster use requires the explicit anchor). The anchor resolves
    only among the current living co-located monsters — the same set the
    preview advertises. Every domain gate then reruns inside the entry.
    """
    from web.webclient.presentation.affordances import in_exploration_mode
    from web.webclient.presentation.skill_use_selection import retire_skill_use_selection
    from world.observability import log_warn
    from world.rules.combat_result import emit_settlement, settle_to_oob_result
    from world.rules.combat_session import CombatSessionError
    from world.rules.event_log import render_plain_text
    from world.rules.field_cast import (
        cast_in_field,
        field_candidate_entities,
        field_opening_anchors,
    )
    from world.rules.player_messages import rejection_message, session_reason_message
    from typeclasses.monsters import Monster

    if not in_exploration_mode(actor):
        return _rejected(*_NOT_EXPLORATION)
    skill_key = payload["skill_key"]
    scale = payload["scale"]
    targets: list[Any] = []
    anchor = None
    if payload["opening_target_id"] is not None:
        anchors = {int(monster.pk): monster for monster in field_opening_anchors(actor)}
        anchor = anchors.get(payload["opening_target_id"])
        if anchor is None:
            return _rejected(*_TARGET_GONE)
    elif payload["target_ids"]:
        candidates = {int(entity.pk): entity for entity in field_candidate_entities(actor)}
        # Only an advertised opening anchor earns the distinct message, so an
        # arbitrary id never reveals anything the preview did not disclose.
        anchors = {int(monster.pk) for monster in field_opening_anchors(actor)}
        for identity in payload["target_ids"]:
            entity = candidates.get(identity)
            if entity is None:
                if identity in anchors:
                    return _rejected(*_MONSTER_NEEDS_OPENING)
                return _rejected(*_TARGET_GONE)
            targets.append(entity)
        if len(targets) == 1 and isinstance(targets[0], Monster):
            # Never reached through ``field_candidate_entities`` (it excludes
            # every Monster); kept as an explicit browser-boundary guard so the
            # entry's trusted-text normalization never applies to OOB input.
            return _rejected(*_MONSTER_NEEDS_OPENING)
    try:
        outcome = cast_in_field(
            actor,
            skill_key,
            targets=targets,
            opening_target=anchor,
            scale=scale,
        )
    except CombatSessionError as error:
        reason = str(error.args[0]) if error.args else "malformed_session"
        log_warn(
            "field_cast_rejected",
            context={"char": actor.pk, "skill": skill_key, "reason": reason},
            exc=error,
        )
        return _rejected(reason, session_reason_message(reason))
    if outcome.route == "rejected":
        return _rejected(outcome.reason.value, rejection_message(outcome.reason))
    if outcome.route == "initiation":
        result = outcome.combat_result
        if result.get("outcome") == "rejected":
            oob = settle_to_oob_result(result)
            return _rejected(oob["code"], oob["message"])
        emit_settlement(actor, result)
        retire_skill_use_selection(session)
        oob = settle_to_oob_result(result)
        oob["affected_panels"] = AFFECTED_CAST
        # The dispatcher schedules exploration options only when the opening
        # ended the encounter at once (an internal flag, never wire data).
        oob["field_combat_terminal"] = result.get("outcome") not in ("round", "continue")
        return oob
    settlement = outcome.settlement
    if settlement.result.outcome != "success":
        reason = settlement.result.reason
        return _rejected(getattr(reason, "value", "rejected"), rejection_message(reason))
    actor.msg(render_plain_text(settlement.result.event_log))
    for line in settlement.notifications:
        actor.msg(line)
    retire_skill_use_selection(session)
    return {
        "outcome": "success",
        "code": "cast",
        "message": "施放完成。",
        "affected_panels": AFFECTED_CAST,
    }
