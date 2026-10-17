"""Exact party-combat action payload validators and guarded adapters.

The four production gameplay actions registered by this delivery unit are
``combat.actor_choices``, ``combat.command``, ``combat.exit_prompt`` and
``combat.exit_confirm``. Each validator enforces one exact bounded payload
shape; each adapter obtains the actor only from the authenticated session's
puppet, re-reads the actor's current active session through the public rules
boundary, reauthorizes every referenced subordinate actor through the shared
``authorize_combat_actor`` seam, and calls only public combat-session APIs. No
adapter assigns ``.db`` attributes, traits, buffs, sexual state, battlefield
members, quests, location, wallet or inventory directly.

``actor_id`` is a subordinate session-participant reference to an allied member
the authenticated commander is authorized to command; it is never account,
puppet or transport identity, and the rules boundary reauthorizes it. Session
IDs are a stale-guard only: they can never select a session.

``combat.exit_prompt`` and ``combat.exit_confirm`` are the two halves of the
party-scoped exit (party-combat-confirmed-surrender §6): the prompt returns the
commander/session/round/operation-bound confirmation token in the exact bounded
success data slot, and the confirmation replays that token at the rules
boundary. Neither performs an individual allied escape.
"""

from typing import Any

from world.rules.combat_result import (
    AFFECTED_PANELS,
    emit_settlement,
    settle_to_oob_result,
)
from world.rules.combat_session import (
    PARTY_EXIT_OPERATIONS,
    CombatSessionError,
    SessionReason,
    authorize_combat_actor,
    confirm_actor_command,
    confirm_party_exit,
    read_session,
    reconstruct_battlefield,
    request_party_exit,
)
from world.rules.player_messages import rejection_message, session_reason_message
from world.rules.progression import FREEFORM_SCALE_VALUES
from world.skills.registry import SKILL_REGISTRY, TargetSpec

# Bounded wire limits for references (equal or below protocol limits).
MAX_SESSION_ID_CODE_POINTS = 128
MAX_CONFIRMATION_TOKEN_CODE_POINTS = 128
MAX_TARGET_IDS = 16
MAX_ITEM_KEY_CODE_POINTS = 64
MAX_CONSEQUENCE_CODE_POINTS = 512
MAX_SAFE_INTEGER = 9_007_199_254_740_991

# The reserved skill key that may only use the party exit route.
RESERVED_FLEE_KEY = "flee"

# Approved AREA shorthands accepted verbatim on the wire.
APPROVED_SHORTHANDS = frozenset({"all-enemies", "all-allies", "all"})

# The closed command-kind and tactic vocabularies of the party command payload.
COMMAND_KINDS = ("skill", "item", "tactic")
TACTIC_KEYS = ("defend", "dodge", "taunt")

# The literal party scope of an exit prompt's bounded success data.
PARTY_EXIT_SCOPE = "party"

# Stable result codes owned by this adapter group.
CODE_ACTOR_CHOICES = "actor_choices"
CODE_DRAFT_SAVED = "draft_saved"
CODE_NEEDS_SELECTION = "needs_selection"
CODE_ALREADY_COMMITTED = "already_committed"
CODE_ROUND_COMMITTED = "round_committed"
CODE_COMBAT_TERMINAL = "combat_terminal"
CODE_PARTY_EXIT_PROMPT = "party_exit_prompt"
CODE_STALE_COMMAND = "stale_command"
CODE_REJECTED = "rejected"

MESSAGE_ACTOR_CHOICES = "已載入選擇成員的戰鬥指令。"
MESSAGE_DRAFT_SAVED = "指令已確認，等待其他成員。"
MESSAGE_NEEDS_SELECTION = "部分指令需要重新選擇。"
MESSAGE_ALREADY_COMMITTED = "這項操作已經結算。"
MESSAGE_PARTY_EXIT_PROMPT = "已開啟隊伍行動確認，請確認或取消。"
MESSAGE_REJECTED = "這項行動無法完成。"
MESSAGE_STALE = "戰鬥狀態已經改變，請重新操作。"

# The one exit-prompt data field set, in wire order.
PARTY_EXIT_PROMPT_FIELDS = (
    "operation",
    "confirmation_token",
    "scope",
    "consequence",
)

# The stale-guard reasons the rules boundary reports for a moved session, round
# revision or draft version. Every one of them is the same bounded stale result
# (design: "stale session/round/edit version is stale/stale_command").
STALE_SESSION_REASONS = frozenset(
    {
        str(SessionReason.STALE_ROUND_REVISION),
        str(SessionReason.UNKNOWN_SESSION_ID),
        "stale_draft_version",
        "stale_round_revision",
    }
)

# The only success code whose bounded data slot this group may populate.
DATA_CARRYING_CODES = frozenset({CODE_PARTY_EXIT_PROMPT})

# The panels a draft edit, an actor query or an already-settled retry republishes:
# the combat menu is the one canonical panel whose progress they change.
DRAFT_PANELS = ("context_actions",)


class CombatActionError(ValueError):
    """A combat action payload violates its exact bounded schema."""


def _require_exact_fields(
    payload: Any,
    name: str,
    required: set[str],
    optional: set[str] = frozenset(),
) -> None:
    if not isinstance(payload, dict):
        raise CombatActionError(f"{name} must be a JSON object")
    unknown = set(payload) - required - set(optional)
    if unknown:
        raise CombatActionError(f"{name} has unknown fields {sorted(unknown)}")
    missing = required - set(payload)
    if missing:
        raise CombatActionError(f"{name} is missing required fields {sorted(missing)}")


def _require_int(value: Any, field: str, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CombatActionError(f"{field} must be an integer")
    if not minimum <= value <= maximum:
        raise CombatActionError(f"{field} must be within {minimum}..{maximum}")
    return value


def _validate_session_id(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CombatActionError("session_id must be a non-empty string")
    if sum(1 for _ in value) > MAX_SESSION_ID_CODE_POINTS:
        raise CombatActionError("session_id exceeds its bound")
    return value


def _validate_revision(value: Any, field: str, *, minimum: int) -> int:
    return _require_int(value, field, minimum=minimum, maximum=MAX_SAFE_INTEGER)


def _validate_actor_id(value: Any) -> int:
    return _require_int(value, "actor_id", minimum=1, maximum=MAX_SAFE_INTEGER)


def _validate_item_key(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise CombatActionError("item_key must be a non-empty string")
    if sum(1 for _ in value) > MAX_ITEM_KEY_CODE_POINTS:
        raise CombatActionError("item_key exceeds its bound")
    if any(char.isspace() for char in value):
        raise CombatActionError("item_key must not contain whitespace")
    return value


def _validate_skill_key(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CombatActionError("skill_key must be a non-empty string")
    if sum(1 for _ in value) > 64:
        raise CombatActionError("skill_key exceeds its bound")
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


def _validate_operation(value: Any) -> str:
    if not isinstance(value, str) or value not in PARTY_EXIT_OPERATIONS:
        raise CombatActionError(
            f"operation must be one of {tuple(PARTY_EXIT_OPERATIONS)}"
        )
    return value


def _validate_confirmation_token(value: Any) -> str:
    """Validate one confirmation token: 1..128 URL-safe ASCII characters."""
    if not isinstance(value, str) or not value:
        raise CombatActionError("confirmation_token must be a non-empty string")
    if sum(1 for _ in value) > MAX_CONFIRMATION_TOKEN_CODE_POINTS:
        raise CombatActionError("confirmation_token exceeds its bound")
    if not all(
        char.isascii() and (char.isalnum() or char in "-_") for char in value
    ):
        raise CombatActionError("confirmation_token is not URL-safe ASCII")
    return value


def _validate_skill_command(payload: Any) -> dict[str, Any]:
    """Validate one closed ``skill`` command payload against its TargetSpec.

    Accepted forms (the same TargetSpec-dependent shapes the v7 draft panel
    publishes):
    - NONE and SELF: ``{skill_key}`` only;
    - SINGLE: ``{skill_key, target_ids: [one positive int]}``;
    - AREA: ``{skill_key, target_ids: [one or more unique positive ints]}`` or
      ``{skill_key, target_shorthand: one approved shorthand}``, never both.

    Every form MAY additionally carry an optional ``scale`` field (one member
    of the freeform scale set, default ``1.0``), including shorthands.
    """
    _require_exact_fields(
        payload,
        "skill command payload",
        {"skill_key"},
        {"target_ids", "target_shorthand", "scale"},
    )
    skill_key = _validate_skill_key(payload["skill_key"])
    if skill_key == RESERVED_FLEE_KEY:
        raise CombatActionError(
            "the reserved flee skill resolves through the party exit route"
        )
    skill = SKILL_REGISTRY.get(skill_key)
    if skill is None:
        raise CombatActionError("skill command references an unknown skill")
    target_spec = skill.target_spec
    scale = _validate_scale(payload.get("scale", 1.0))
    has_ids = "target_ids" in payload
    has_shorthand = "target_shorthand" in payload
    if has_ids and has_shorthand:
        raise CombatActionError("skill command target fields are mutually exclusive")

    target_ids: list[int] = []
    target_shorthand: str | None = None
    if has_shorthand:
        shorthand = payload["target_shorthand"]
        if not isinstance(shorthand, str) or shorthand not in APPROVED_SHORTHANDS:
            raise CombatActionError("skill command carries an unapproved shorthand")
        if target_spec is not TargetSpec.AREA:
            raise CombatActionError("skill command shorthand requires an area skill")
        target_shorthand = shorthand
    elif has_ids:
        ids = payload["target_ids"]
        if not isinstance(ids, list):
            raise CombatActionError("skill command target_ids must be a list")
        if not ids:
            raise CombatActionError("skill command target_ids must be non-empty")
        if len(ids) > MAX_TARGET_IDS:
            raise CombatActionError("skill command target_ids exceed their bound")
        seen: set[int] = set()
        for item in ids:
            value = _require_int(
                item, "target_ids item", minimum=1, maximum=MAX_SAFE_INTEGER
            )
            if value in seen:
                raise CombatActionError("skill command target_ids must be unique")
            seen.add(value)
            target_ids.append(value)
        if target_spec is TargetSpec.NONE or target_spec is TargetSpec.SELF:
            raise CombatActionError("skill command accepts no target for this skill")
        if target_spec is TargetSpec.SINGLE and len(target_ids) != 1:
            raise CombatActionError("skill command SINGLE requires exactly one target")
    elif target_spec is not TargetSpec.NONE and target_spec is not TargetSpec.SELF:
        raise CombatActionError("skill command requires a target for this skill")

    return {
        "skill_key": skill_key,
        "target_ids": tuple(target_ids),
        "target_shorthand": target_shorthand,
        "scale": scale,
    }


def _validate_item_command(payload: Any) -> dict[str, Any]:
    """Validate one closed ``item`` command payload: key plus optional target."""
    _require_exact_fields(
        payload, "item command payload", {"item_key"}, {"target_id"}
    )
    item_key = _validate_item_key(payload["item_key"])
    target_id = (
        None
        if "target_id" not in payload
        else _require_int(
            payload["target_id"], "target_id", minimum=1, maximum=MAX_SAFE_INTEGER
        )
    )
    return {"item_key": item_key, "target_id": target_id}


def _validate_tactic_command(payload: Any) -> dict[str, Any]:
    """Validate one closed ``tactic`` command payload.

    ``defend`` and ``dodge`` carry no target at all; ``taunt`` carries exactly
    one positive target identity.
    """
    _require_exact_fields(payload, "tactic command payload", {"key"}, {"target_id"})
    key = payload["key"]
    if not isinstance(key, str) or key not in TACTIC_KEYS:
        raise CombatActionError(f"tactic key must be one of {TACTIC_KEYS}")
    if key == "taunt":
        if "target_id" not in payload:
            raise CombatActionError("a taunt command requires exactly one target_id")
        target_id = _require_int(
            payload["target_id"], "target_id", minimum=1, maximum=MAX_SAFE_INTEGER
        )
    else:
        if "target_id" in payload:
            raise CombatActionError(f"{key} must not carry a target_id")
        target_id = None
    return {"key": key, "target_id": target_id}


def _validate_command(value: Any) -> dict[str, Any]:
    """Validate the closed ``{kind, payload}`` party command union."""
    _require_exact_fields(value, "combat command", {"kind", "payload"})
    kind = value["kind"]
    if not isinstance(kind, str) or kind not in COMMAND_KINDS:
        raise CombatActionError(f"combat command kind must be one of {COMMAND_KINDS}")
    payload = value["payload"]
    if kind == "skill":
        normalized = _validate_skill_command(payload)
    elif kind == "item":
        normalized = _validate_item_command(payload)
    else:
        normalized = _validate_tactic_command(payload)
    return {"kind": kind, "payload": normalized}


def validate_actor_choices_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``combat.actor_choices`` payload (one actor query)."""
    _require_exact_fields(
        payload,
        "combat.actor_choices payload",
        {"session_id", "round_revision", "actor_id"},
    )
    return {
        "session_id": _validate_session_id(payload["session_id"]),
        "round_revision": _validate_revision(
            payload["round_revision"], "round_revision", minimum=1
        ),
        "actor_id": _validate_actor_id(payload["actor_id"]),
    }


def validate_command_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``combat.command`` payload (one member's command)."""
    _require_exact_fields(
        payload,
        "combat.command payload",
        {"session_id", "round_revision", "draft_version", "actor_id", "command"},
    )
    return {
        "session_id": _validate_session_id(payload["session_id"]),
        "round_revision": _validate_revision(
            payload["round_revision"], "round_revision", minimum=1
        ),
        "draft_version": _validate_revision(
            payload["draft_version"], "draft_version", minimum=0
        ),
        "actor_id": _validate_actor_id(payload["actor_id"]),
        "command": _validate_command(payload["command"]),
    }


def validate_exit_prompt_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``combat.exit_prompt`` payload."""
    _require_exact_fields(
        payload,
        "combat.exit_prompt payload",
        {"session_id", "round_revision", "operation"},
    )
    return {
        "session_id": _validate_session_id(payload["session_id"]),
        "round_revision": _validate_revision(
            payload["round_revision"], "round_revision", minimum=1
        ),
        "operation": _validate_operation(payload["operation"]),
    }


def validate_exit_confirm_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``combat.exit_confirm`` payload (prompt plus token)."""
    _require_exact_fields(
        payload,
        "combat.exit_confirm payload",
        {"session_id", "round_revision", "operation", "confirmation_token"},
    )
    return {
        "session_id": _validate_session_id(payload["session_id"]),
        "round_revision": _validate_revision(
            payload["round_revision"], "round_revision", minimum=1
        ),
        "operation": _validate_operation(payload["operation"]),
        "confirmation_token": _validate_confirmation_token(
            payload["confirmation_token"]
        ),
    }


def validate_party_exit_prompt_data(data: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact bounded success data of one exit prompt.

    The adapter-specific result validator of this group: exactly
    ``{operation, confirmation_token, scope, consequence}``, with the literal
    ``party`` scope, request-bounded operation/token values, and one
    server-authored 1..512 code-point consequence line. Session and round stay
    bound to the stored initiating request and token, so neither ever appears
    as a result-data state key.
    """
    _require_exact_fields(data, "party exit prompt data", set(PARTY_EXIT_PROMPT_FIELDS))
    scope = data["scope"]
    if scope != PARTY_EXIT_SCOPE:
        raise CombatActionError("party exit prompt scope must be 'party'")
    consequence = data["consequence"]
    if not isinstance(consequence, str) or not consequence:
        raise CombatActionError("party exit prompt consequence must be a non-empty string")
    if sum(1 for _ in consequence) > MAX_CONSEQUENCE_CODE_POINTS:
        raise CombatActionError("party exit prompt consequence exceeds its bound")
    return {
        "operation": _validate_operation(data["operation"]),
        "confirmation_token": _validate_confirmation_token(data["confirmation_token"]),
        "scope": PARTY_EXIT_SCOPE,
        "consequence": consequence,
    }


def _rules_command(command: dict[str, Any]) -> dict[str, Any]:
    """Translate one validated wire command into the rules-layer draft shape.

    The wire vocabulary (``target_ids``/``target_shorthand``, kind ``tactic``
    with ``key``) is the client-facing contract of the v7 party panel; the
    persisted draft keeps its own internal ``targets_or_shorthand`` /
    ``tactical`` / ``tactical_key`` spelling. Only the public
    ``confirm_actor_command`` entry is called, with the exact same command
    value the panel publishes back for the admitted entry.
    """
    kind = command["kind"]
    payload = command["payload"]
    if kind == "skill":
        shorthand = payload.get("target_shorthand")
        # An empty target list is the rules layer's input for a NONE/SELF
        # skill (the wire carries no target field at all).
        targets: Any = (
            shorthand
            if shorthand is not None
            else [int(target) for target in payload.get("target_ids", ())]
        )
        return {
            "kind": "skill",
            "payload": {
                "skill_key": payload["skill_key"],
                "targets_or_shorthand": targets,
                "scale": float(payload.get("scale", 1.0)),
            },
        }
    if kind == "item":
        return {
            "kind": "item",
            "payload": {
                "item_key": payload["item_key"],
                "target_id": payload.get("target_id"),
            },
        }
    return {
        "kind": "tactical",
        "payload": {
            "tactical_key": payload["key"],
            "target_id": payload.get("target_id"),
        },
    }


def _reason_code(reason: Any) -> str:
    """Return the bounded stable code of one rules rejection reason."""
    if reason is None:
        return CODE_REJECTED
    value = getattr(reason, "value", reason)
    return str(value)


def _reason_result(reason: Any) -> dict[str, Any]:
    """Map one rules rejection/stale reason to this group's exact result."""
    code = _reason_code(reason)
    if code in STALE_SESSION_REASONS:
        return {
            "outcome": "stale",
            "code": CODE_STALE_COMMAND,
            "message": MESSAGE_STALE,
        }
    if code == CODE_ALREADY_COMMITTED:
        return _success_result(CODE_ALREADY_COMMITTED, MESSAGE_ALREADY_COMMITTED, ())
    message = (
        rejection_message(reason)
        if hasattr(reason, "value")
        else session_reason_message(code)
    )
    return {"outcome": "rejected", "code": code, "message": message}


def _success_result(
    code: str,
    message: str,
    affected_panels: tuple[str, ...],
    *,
    data: dict[str, Any] | None = None,
    combat_round: Any = None,
) -> dict[str, Any]:
    """Build one exact success result of this group.

    Only the exit-prompt code may carry the bounded success data slot; a data
    payload on any other code is a programming error, so it fails closed here
    rather than at the wire boundary.
    """
    if data is not None and code not in DATA_CARRYING_CODES:
        raise CombatActionError(f"{code} must not carry result data")
    result: dict[str, Any] = {
        "outcome": "success",
        "code": code,
        "message": message,
        "affected_panels": affected_panels,
    }
    if data is not None:
        result["data"] = data
    if combat_round is not None:
        result["combat_round"] = combat_round
    return result


def _settlement_result(actor: Any, result: dict[str, Any]) -> dict[str, Any]:
    """Normalize one committed settlement into this group's exact result.

    The rules settlement is the only source of the internal ``round_record``
    slot: it rides both the continuing-round and the terminal branch, so the
    round that ends the fight still plays its beats. ``emit_settlement``
    delivers the committed narrative as ordinary text exactly once, and only
    for a newly committed settlement.
    """
    if result.get("outcome") == "rejected":
        return _reason_result(result.get("reason"))
    emit_settlement(actor, result)
    oob = settle_to_oob_result(result)
    code = CODE_ROUND_COMMITTED if oob["code"] == "round" else CODE_COMBAT_TERMINAL
    return _success_result(
        code,
        oob["message"],
        tuple(oob.get("affected_panels", ())),
        combat_round=oob.get("combat_round"),
    )


def _actor_choices_adapter(
    actor: Any, payload: dict[str, Any], session: Any = None
) -> dict[str, Any]:
    """Answer one read-only actor-choice query and select that member's menu.

    The query re-reads the actor's current session, resolves the named member
    from the reconstructed battlefield, and reauthorizes it through the shared
    party boundary: a syntactically valid identity the commander may not command
    rejects without any state change, and no error discloses another actor's
    state. Nothing is rolled, consumed advanced or persisted; the only write is
    the transport-owned presentation selection of this session's sequence.
    """
    from web.webclient.presentation.party_actor_selection import select_party_actor

    record = read_session(actor)
    if record is None:
        return _reason_result(SessionReason.NO_ACTIVE_SESSION)
    if (
        record.session_id != payload["session_id"]
        or record.round_revision != payload["round_revision"]
    ):
        return _reason_result(SessionReason.STALE_ROUND_REVISION)
    try:
        battlefield = reconstruct_battlefield(actor, record)
    except CombatSessionError as error:
        return _reason_result(error.args[0])
    target = next(
        (
            entity
            for entity in battlefield.roster.values()
            if getattr(entity, "pk", None) == payload["actor_id"]
        ),
        None,
    )
    if target is None:
        return _reason_result(SessionReason.FORBIDDEN_ACTOR)
    try:
        authorize_combat_actor(actor, target, record, battlefield)
    except CombatSessionError as error:
        return _reason_result(error.args[0])
    select_party_actor(
        session, actor, record.session_id, record.round_revision, payload["actor_id"]
    )
    return _success_result(CODE_ACTOR_CHOICES, MESSAGE_ACTOR_CHOICES, DRAFT_PANELS)


def _command_adapter(
    actor: Any, payload: dict[str, Any], session: Any = None
) -> dict[str, Any]:
    """Commit one member's command into the durable draft.

    The admission is delegated whole to ``confirm_actor_command``: it
    reauthorizes the referenced actor against the live record, revalidates the
    command's capability, ownership and targets, applies the
    session/round/draft-version compare-and-swap, saves the entry, and resolves
    the round at the completing confirmation. This adapter only maps the
    returned result into the exact wire variant; progress and reselection
    reasons always come from the canonical v7 draft panel, never from error
    data.
    """
    del session
    try:
        result = confirm_actor_command(
            actor,
            payload["session_id"],
            payload["round_revision"],
            payload["draft_version"],
            payload["actor_id"],
            _rules_command(payload["command"]),
        )
    except CombatSessionError as error:
        return _reason_result(error.args[0])

    outcome = result.get("outcome")
    if outcome == "draft":
        # An admitted edit that leaves the draft incomplete: a member still to
        # choose is normal progress, while a member-specific reselection reason
        # (or the late incomplete-draft race) needs a fresh choice.
        if result.get("reason") == "draft_incomplete" or result.get("reselection_reasons"):
            return {
                "outcome": "rejected",
                "code": CODE_NEEDS_SELECTION,
                "message": MESSAGE_NEEDS_SELECTION,
            }
        return _success_result(CODE_DRAFT_SAVED, MESSAGE_DRAFT_SAVED, DRAFT_PANELS)
    if outcome == "rejected":
        return _reason_result(result.get("reason"))
    return _settlement_result(actor, result)


def _exit_prompt_adapter(
    actor: Any, payload: dict[str, Any], session: Any = None
) -> dict[str, Any]:
    """Request one party exit prompt and return its exact bounded data.

    Runs no action and changes nothing: the rules boundary returns the party
    scope, the operation's server-authored consequences and one confirmation
    token bound to the authenticated commander, the session, the round revision
    and the operation. Session and round are bound to that stored request and
    token; they are never inserted into the result-data slot.
    """
    del session
    try:
        prompt = request_party_exit(
            actor,
            payload["session_id"],
            payload["round_revision"],
            payload["operation"],
        )
    except CombatSessionError as error:
        return _reason_result(error.args[0])
    data = validate_party_exit_prompt_data(
        {
            "operation": prompt["operation"],
            "confirmation_token": prompt["confirmation_token"],
            "scope": PARTY_EXIT_SCOPE,
            "consequence": "\n".join(prompt["consequences"]),
        }
    )
    return _success_result(
        CODE_PARTY_EXIT_PROMPT,
        MESSAGE_PARTY_EXIT_PROMPT,
        (),
        data=data,
    )


def _exit_confirm_adapter(
    actor: Any, payload: dict[str, Any], session: Any = None
) -> dict[str, Any]:
    """Confirm one party exit with its token at the rules boundary.

    The token is replayed to ``confirm_party_exit``, which verifies it against
    the authenticated commander, the session, the round revision and the
    operation before admitting exactly one operation; a stale, forged, replayed
    or competing confirmation can never reach another session or round. A
    confirmation retried after its settlement committed returns the boundary's
    own recorded settlement as the accepted-operation retry, without settling
    or narrating again.
    """
    del session
    try:
        result = confirm_party_exit(
            actor,
            payload["session_id"],
            payload["round_revision"],
            payload["operation"],
            payload["confirmation_token"],
        )
    except CombatSessionError as error:
        return _reason_result(error.args[0])
    if result.get("idempotent"):
        return _success_result(CODE_ALREADY_COMMITTED, MESSAGE_ALREADY_COMMITTED, ())
    return _settlement_result(actor, result)


__all__ = [
    "APPROVED_SHORTHANDS",
    "AFFECTED_PANELS",
    "CODE_ACTOR_CHOICES",
    "CODE_ALREADY_COMMITTED",
    "CODE_COMBAT_TERMINAL",
    "CODE_DRAFT_SAVED",
    "CODE_NEEDS_SELECTION",
    "CODE_PARTY_EXIT_PROMPT",
    "CODE_REJECTED",
    "CODE_ROUND_COMMITTED",
    "CODE_STALE_COMMAND",
    "CombatActionError",
    "DATA_CARRYING_CODES",
    "DRAFT_PANELS",
    "MESSAGE_DRAFT_SAVED",
    "PARTY_EXIT_PROMPT_FIELDS",
    "PARTY_EXIT_SCOPE",
    "RESERVED_FLEE_KEY",
    "STALE_SESSION_REASONS",
    "TACTIC_KEYS",
    "validate_actor_choices_payload",
    "validate_command_payload",
    "validate_exit_confirm_payload",
    "validate_exit_prompt_payload",
    "validate_party_exit_prompt_data",
]
