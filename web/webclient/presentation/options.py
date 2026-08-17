"""Shared suggestion-section bounds and validator for the v5 ``context_actions`` panel.

The ``suggestions`` envelope is a per-status closed schema: ``generating`` and
``unavailable`` carry exactly ``status``; ``ready`` and ``degraded`` carry
``status`` and ``cards``. This module owns the shared option caps (mirroring
the generative schema caps in ``world.ai.action_options``), the canonical
affordance payload validators (also used by the exploration form's affordance
entries), and the wire shape gate ``validate_suggestions`` used by
``combat_panel.py`` and mirrored in ``protocol.js``.

The validator is a strict *shape* gate: it checks envelope kinds, action codes
against ``ACTION_CODE_ALLOWLIST``, label/hint/params bounds, per-status counts,
and the freeform binding shape. It does NOT re-run leak gates, enrichment, or
canonical replacement — a wire card is already the output of the generative
layer's ladder (design D-2).
"""

from typing import Any

from web.webclient.actions.exploration_actions import (
    ExplorationActionError,
    validate_engage_payload,
    validate_look_payload,
    validate_move_payload,
    validate_party_invite_payload,
    validate_party_leave_payload,
    validate_talk_scripted_payload,
    validate_wait_payload,
)
from web.webclient.presentation.affordances import ACTION_CODE_ALLOWLIST
from web.webclient.presentation.protocol import (
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_exact_fields,
    _require_int,
    _require_str,
    _validate_identifier,
    _code_points,
)

# The four transport states of the suggestions envelope (never cached).
OPTIONS_STATUSES = ("generating", "ready", "degraded", "unavailable")

# The two card kinds of the hybrid card vocabulary.
OPTIONS_CARD_KINDS = ("known_action", "freeform")

# Card-count and card-shape caps (mirror of the generative schema caps).
MAX_OPTION_CARDS = 5
MAX_OPTION_LABEL = 24
MAX_OPTION_HINT = 60
MAX_OPTION_PARAMS = 4

# The freeform pin: a freeform card is exactly this action code.
FREEFORM_ACTION_CODE = "explore.talk_freeform"

# The room-survey param form of explore.look (the only boolean allowed).
_ROOM_SURVEY_PARAMS = {"room": True}

# Validators the exploration form reuses for the canonical params of every
# non-freeform action (the freeform binding shape is validated separately).
_ACTION_PAYLOAD_VALIDATORS = {
    "explore.move": validate_move_payload,
    "explore.look": validate_look_payload,
    "explore.talk_scripted": validate_talk_scripted_payload,
    "explore.party_invite": validate_party_invite_payload,
    "explore.party_leave": validate_party_leave_payload,
    "explore.engage": validate_engage_payload,
    "explore.wait": validate_wait_payload,
}


def _contains_cjk(label: str) -> bool:
    """Whether the label contains at least one CJK Unified Ideograph."""
    return any("\u4e00" <= char <= "\u9fff" for char in label)


def _validate_affordance_params(action_id: str, params: Any) -> dict[str, Any]:
    """Validate the canonical params of one exploration affordance entry.

    Every non-freeform action's params are run through its registered action
    validator so the wire payload is byte-for-byte what the dispatcher
    accepts; the freeform entry's ``{"npc_id": int}`` binding shape is the
    single exception (no registered validator produces it without ``speech``).
    """
    if action_id == "explore.talk_freeform":
        _require_exact_fields(params, "freeform params", {"npc_id"}, {})
        return {"npc_id": _require_int(params, "npc_id", minimum=1, maximum=MAX_SAFE_INTEGER)}
    validator = _ACTION_PAYLOAD_VALIDATORS[action_id]
    try:
        return validator(params)
    except ExplorationActionError as error:
        raise ProtocolValidationError(str(error)) from error


def _validate_suggestion_params(action_code: str, kind: str, params: Any) -> dict[str, Any]:
    """Validate one card's params: canonical payload or the freeform binding.

    A ``known_action`` card's params are the matching canonical affordance's
    validator-normalized payload (1..4 keys; safe integers and bounded strings
    plus the literal boolean ``true`` for the ``explore.look`` room-survey
    form; any other boolean is rejected). A ``freeform`` card's params are
    exactly the ``{"npc_id": positive int}`` binding.
    """
    if not isinstance(params, dict):
        raise ProtocolValidationError("suggestion params must be a JSON object")
    if not 1 <= len(params) <= MAX_OPTION_PARAMS:
        raise ProtocolValidationError("suggestion params exceed their bound")
    if kind == "freeform":
        return _validate_affordance_params(action_code, params)
    for key, value in params.items():
        if isinstance(value, bool):
            if action_code == "explore.look" and params == _ROOM_SURVEY_PARAMS:
                continue
            raise ProtocolValidationError(
                "suggestion params carry an unsupported boolean"
            )
        if isinstance(value, int) and not isinstance(value, bool):
            if not 0 <= value <= MAX_SAFE_INTEGER:
                raise ProtocolValidationError("suggestion params integer is out of bounds")
            continue
        if isinstance(value, str):
            if _code_points(value) > 512:
                raise ProtocolValidationError("suggestion params string exceeds its bound")
            continue
        raise ProtocolValidationError("suggestion params carry an unsupported value type")
    return _validate_affordance_params(action_code, params)


def _validate_suggestion_card(value: Any) -> dict[str, Any]:
    """Validate one exact suggestion card."""
    _require_exact_fields(
        value,
        "suggestion card",
        {"kind", "action_code", "label", "params"},
        {"hint": "optional"},
    )
    kind = value["kind"]
    if kind not in OPTIONS_CARD_KINDS:
        raise ProtocolValidationError("suggestion card kind is not a stable value")
    action_code = _validate_identifier(value["action_code"], "action_code")
    if action_code not in ACTION_CODE_ALLOWLIST:
        raise ProtocolValidationError("action_code is not a registered exploration action")
    if (kind == "freeform") != (action_code == FREEFORM_ACTION_CODE):
        raise ProtocolValidationError(
            "freeform cards must carry exactly explore.talk_freeform"
        )
    label = _require_str(value, "label", maximum=MAX_OPTION_LABEL)
    if not 1 <= _code_points(label) <= MAX_OPTION_LABEL:
        raise ProtocolValidationError("suggestion label must be 1..24 code points")
    if not _contains_cjk(label):
        raise ProtocolValidationError("suggestion label must contain a CJK code point")
    params = _validate_suggestion_params(action_code, kind, value["params"])
    hint = None
    if "hint" in value and value["hint"] is not None:
        hint = _require_str(value, "hint", maximum=MAX_OPTION_HINT)
    return {
        "kind": kind,
        "action_code": action_code,
        "label": label,
        "params": params,
        "hint": hint,
    }


def validate_suggestions(value: Any) -> dict[str, Any]:
    """Validate one exact ``suggestions`` envelope, returning a normalized dict.

    Status decides the exact key set: ``generating``/``unavailable`` carry
    only ``status``; ``ready``/``degraded`` carry both. Counts: ``ready`` sets
    are 3..5, ``degraded`` sets 0..5. Any violation raises
    :class:`ProtocolValidationError`.
    """
    if not isinstance(value, dict):
        raise ProtocolValidationError("suggestions must be a JSON object")
    status = value.get("status")
    if status not in OPTIONS_STATUSES:
        raise ProtocolValidationError("suggestions status is not a stable value")
    if status in ("generating", "unavailable"):
        _require_exact_fields(value, "suggestions", {"status"}, {})
        return {"status": status}
    _require_exact_fields(value, "suggestions", {"status", "cards"}, {})
    cards = value["cards"]
    if not isinstance(cards, list):
        raise ProtocolValidationError("suggestions cards must be an array")
    minimum = 3 if status == "ready" else 0
    if not minimum <= len(cards) <= MAX_OPTION_CARDS:
        raise ProtocolValidationError(
            f"suggestions cards must number {minimum}..{MAX_OPTION_CARDS}"
        )
    card_views = [_validate_suggestion_card(card) for card in cards]
    return {"status": status, "cards": card_views}


__all__ = [
    "FREEFORM_ACTION_CODE",
    "MAX_OPTION_CARDS",
    "MAX_OPTION_HINT",
    "MAX_OPTION_LABEL",
    "MAX_OPTION_PARAMS",
    "OPTIONS_CARD_KINDS",
    "OPTIONS_STATUSES",
    "validate_suggestions",
]
