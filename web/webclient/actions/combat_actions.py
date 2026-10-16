"""Exact combat action payload validators and narrow adapters.

The three production gameplay actions registered by this delivery unit are
``combat.cast``, ``combat.flee``, and ``combat.forfeit``. Each validator enforces
an exact bounded payload shape; each adapter re-reads the actor's current active
session, re-resolves every referenced identity from its persisted participants,
runs the shared side-effect-free preview revalidation, calls only public
combat-session APIs, and never assigns ``.db`` attributes, traits, buffs,
sexual state, battlefield members, quests, location, wallet, or inventory
directly.

``combat.flee`` and ``combat.forfeit`` are party-level exits
(party-combat-confirmed-surrender §6): neither performs an individual allied
escape, and both reach the rules boundary's session/round/operation-bound
confirmation rather than an unconfirmed settlement.
"""

from typing import Any

from world.rules.action import RejectReason
from world.rules.action_preview import revalidate_submission
from world.rules.combat_result import emit_settlement, settle_to_oob_result
from world.rules.combat_session import (
    PARTY_EXIT_RETREAT,
    PARTY_EXIT_SURRENDER,
    CombatSessionError,
    SessionReason,
    confirm_party_exit,
    read_session,
    reconstruct_battlefield,
    request_party_exit,
    submit_player_action,
)
from world.rules.player_messages import (
    rejection_message,
    session_reason_message,
)
from world.rules.progression import FREEFORM_SCALE_VALUES
from world.skills.registry import SKILL_REGISTRY, TargetSpec

# Bounded wire limits for target references (equal or below protocol limits).
MAX_TARGET_IDS = 16
MAX_SESSION_ID_CODE_POINTS = 128

# The reserved skill key that may only use the dedicated flee action.
RESERVED_FLEE_KEY = "flee"

# Approved AREA shorthands accepted verbatim on the wire.
APPROVED_SHORTHANDS = frozenset({"all-enemies", "all-allies", "all"})


class CombatActionError(ValueError):
    """A combat action payload violates its exact bounded schema."""


def _require_int(value: Any, field: str, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CombatActionError(f"{field} must be an integer")
    if not minimum <= value <= maximum:
        raise CombatActionError(f"{field} must be within {minimum}..{maximum}")
    return value


def _validate_skill_key(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CombatActionError("skill_key must be a non-empty string")
    if sum(1 for _ in value) > 64:
        raise CombatActionError("skill_key exceeds its bound")
    return value


def _validate_session_id(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CombatActionError("session_id must be a non-empty string")
    if sum(1 for _ in value) > MAX_SESSION_ID_CODE_POINTS:
        raise CombatActionError("session_id exceeds its bound")
    return value


def _validate_scale(value: Any) -> float:
    """Validate the optional freeform ``scale`` field.

    The value must be a JSON number exactly equal to one member of the
    ``freeform_cast_scales`` table (every allowed value is exactly
    binary-representable, so float equality is safe); a boolean, a non-number,
    or a non-member number is rejected as a malformed payload.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CombatActionError("scale must be a number")
    scale = float(value)
    if scale not in FREEFORM_SCALE_VALUES:
        raise CombatActionError("scale must be a member of the freeform scale set")
    return scale


def validate_cast_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact TargetSpec-dependent ``combat.cast`` payload.

    Accepted forms:
    - NONE and SELF: ``{skill_key}`` only;
    - SINGLE: ``{skill_key, target_ids: [one positive int]}``;
    - AREA: ``{skill_key, target_ids: [one or more unique positive ints]}`` or
      ``{skill_key, target_shorthand: one approved shorthand}``, never both.

    Every form MAY additionally carry an optional ``scale`` field (one member
    of the freeform scale set, default ``1.0``) on every target form,
    including shorthands.
    """
    if not isinstance(payload, dict):
        raise CombatActionError("combat.cast payload must be an object")
    unknown = set(payload) - {
        "skill_key",
        "target_ids",
        "target_shorthand",
        "scale",
    }
    if unknown:
        raise CombatActionError(f"combat.cast has unknown fields {sorted(unknown)}")
    if "skill_key" not in payload:
        raise CombatActionError("combat.cast requires skill_key")
    skill_key = _validate_skill_key(payload["skill_key"])
    has_ids = "target_ids" in payload
    has_shorthand = "target_shorthand" in payload
    if has_ids and has_shorthand:
        raise CombatActionError("combat.cast target fields are mutually exclusive")
    scale = _validate_scale(payload.get("scale", 1.0))
    if skill_key == RESERVED_FLEE_KEY:
        raise CombatActionError("combat.cast must not be used for the reserved flee skill")
    skill = SKILL_REGISTRY.get(skill_key)
    if skill is None:
        raise CombatActionError("combat.cast references an unknown skill")
    target_spec = skill.target_spec

    target_ids: list[int] = []
    target_shorthand: str | None = None
    if has_shorthand:
        shorthand = payload["target_shorthand"]
        if not isinstance(shorthand, str) or shorthand not in APPROVED_SHORTHANDS:
            raise CombatActionError("combat.cast carries an unapproved shorthand")
        if target_spec is not TargetSpec.AREA:
            raise CombatActionError("combat.cast shorthand requires an area skill")
        target_shorthand = shorthand
    elif has_ids:
        ids = payload["target_ids"]
        if not isinstance(ids, list):
            raise CombatActionError("combat.cast target_ids must be a list")
        if not ids:
            raise CombatActionError("combat.cast target_ids must be non-empty")
        if len(ids) > MAX_TARGET_IDS:
            raise CombatActionError("combat.cast target_ids exceed their bound")
        seen: set[int] = set()
        for item in ids:
            value = _require_int(item, "target_ids item", minimum=1, maximum=9_007_199_254_740_991)
            if value in seen:
                raise CombatActionError("combat.cast target_ids must be unique")
            seen.add(value)
            target_ids.append(value)
        if target_spec is TargetSpec.NONE or target_spec is TargetSpec.SELF:
            raise CombatActionError("combat.cast NONE/SELF accepts no target field")
        if target_spec is TargetSpec.SINGLE and len(target_ids) != 1:
            raise CombatActionError("combat.cast SINGLE requires exactly one target")
    else:
        if target_spec is not TargetSpec.NONE and target_spec is not TargetSpec.SELF:
            raise CombatActionError("combat.cast requires a target for this skill")

    return {
        "skill_key": skill_key,
        "target_ids": tuple(target_ids),
        "target_shorthand": target_shorthand,
        "scale": scale,
    }


def validate_flee_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact empty ``combat.flee`` payload."""
    if not isinstance(payload, dict):
        raise CombatActionError("combat.flee payload must be an object")
    if payload:
        raise CombatActionError("combat.flee requires an empty payload")
    return {}


def validate_forfeit_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``combat.forfeit`` payload (one session ID guard)."""
    if not isinstance(payload, dict):
        raise CombatActionError("combat.forfeit payload must be an object")
    if set(payload) != {"session_id"}:
        raise CombatActionError("combat.forfeit requires exactly session_id")
    return {"session_id": _validate_session_id(payload["session_id"])}


def _participants_by_id(actor: Any) -> dict[int, Any]:
    """Re-resolve every participant of the actor's current session by dbref."""
    record = read_session(actor)
    if record is None:
        raise CombatSessionError(SessionReason.NO_ACTIVE_SESSION)
    battlefield = reconstruct_battlefield(actor, record)
    by_id: dict[int, Any] = {}
    for dbref in (*record.player_ids, *record.enemy_ids):
        entity = battlefield.roster.get(
            next(
                (
                    key
                    for key in battlefield.roster
                    if getattr(battlefield.roster[key], "pk", None) == dbref
                ),
                "",
            )
        )
        if entity is not None:
            by_id[int(dbref)] = entity
    return by_id


def _cast_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Resolve one ``combat.cast`` request and invoke the combat-session facade."""
    skill_key = payload["skill_key"]
    record = read_session(actor)
    if record is None:
        return _rejected_result(SessionReason.NO_ACTIVE_SESSION)
    battlefield = reconstruct_battlefield(actor, record)
    context = _context_for(battlefield, record)

    if payload["target_shorthand"] is not None:
        target_value: list[Any] | str = payload["target_shorthand"]
    else:
        by_id = _participants_by_id(actor)
        targets: list[Any] = []
        for identity in payload["target_ids"]:
            entity = by_id.get(identity)
            if entity is None:
                return _rejected_result(
                    SessionReason.UNKNOWN_SESSION_ID,
                    f"participant {identity} is not in this session",
                )
            targets.append(entity)
        target_value = targets

    preview = revalidate_submission(
        actor,
        skill_key,
        context,
        target_value,
        scale=payload["scale"],
    )
    if not preview.enabled:
        reason = preview.reason or RejectReason.UNKNOWN_SKILL
        return {
            "outcome": "rejected",
            "code": reason.value,
            "message": rejection_message(reason),
        }

    try:
        result = submit_player_action(
            actor,
            skill_key,
            target_value,
            scale=payload["scale"],
        )
    except CombatSessionError as error:
        return _rejected_result(error.args[0])
    emit_settlement(actor, result)
    return settle_to_oob_result(result)


def _flee_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Route the allied flee row to the confirmed party exit boundary.

    An allied personal flee no longer exists (§6): this route reaches the
    same party-scoped confirmation boundary the text aliases reach and can
    never perform an individual allied escape. It deliberately does not
    auto-confirm either — the dock's flee row is a single dispatch with no
    confirmation window, so confirming on its behalf would be an unconfirmed
    whole-party retreat. The window and its ``combat.exit_confirm`` payload
    belong to ``webclient-party-exit-confirmation``; until it ships, the row
    returns the boundary's deterministic rejection and nothing mutates.
    """
    del payload, session
    record = read_session(actor)
    if record is None:
        return _rejected_result(SessionReason.NO_ACTIVE_SESSION)
    try:
        request_party_exit(
            actor, record.session_id, record.round_revision, PARTY_EXIT_RETREAT
        )
    except CombatSessionError as error:
        return _rejected_result(error.args[0])
    return _rejected_result(SessionReason.PARTY_EXIT_UNAVAILABLE)


def _forfeit_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Confirm the actor's party surrender when the stale-guard matches.

    The mounted dock asks the player to confirm before this action is sent,
    and that window is the explicit human step; this adapter then reaches the
    rules boundary's own confirmation, requesting the session/round/operation
    bound token and confirming it in the same call, so an unconfirmed
    surrender never reaches the settlement and the admission serializes on the
    same session/revision a round uses. The exact-token wire step
    (``combat.exit_confirm``, which carries the token to the client) belongs to
    ``webclient-party-exit-confirmation``.
    """
    record = read_session(actor)
    if record is None:
        return _rejected_result(SessionReason.NO_ACTIVE_SESSION)
    if payload["session_id"] != record.session_id:
        return _rejected_result(
            SessionReason.UNKNOWN_SESSION_ID,
            "forfeit session_id does not match the active record",
        )
    try:
        prompt = request_party_exit(
            actor, record.session_id, record.round_revision, PARTY_EXIT_SURRENDER
        )
        result = confirm_party_exit(
            actor,
            prompt["session_id"],
            prompt["round_revision"],
            prompt["operation"],
            prompt["confirmation_token"],
        )
    except CombatSessionError as error:
        return _rejected_result(error.args[0])
    emit_settlement(actor, result)
    return settle_to_oob_result(result)


def _context_for(battlefield: Any, record: Any) -> Any:
    del record
    from world.rules.combat import BattlefieldActionContext

    return BattlefieldActionContext(battlefield)


def _rejected_result(reason: Any, detail: str = "") -> dict[str, Any]:
    del detail
    code = str(reason)
    return {
        "outcome": "rejected",
        "code": code,
        "message": session_reason_message(code),
    }
