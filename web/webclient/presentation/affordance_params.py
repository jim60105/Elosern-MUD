"""Validator-normalized params for the shared exploration affordance vocabulary.

Every non-freeform action's wire ``params`` are run through its registered
dispatcher payload validator, so an affordance entry carries byte-for-byte the
payload its adapter accepts. The freeform entry's ``{"npc_id": int}`` binding
shape is the single exception: no registered validator produces it without
``speech``, which only the composed dispatch payload supplies.

``combat_panel.py`` validates the ``context_actions`` exploration form's
affordance entries through this table, and ``exploration.py`` normalizes a
delivery descriptor's params through it.
"""

from typing import Any

from web.webclient.actions.exploration_actions import (
    ExplorationActionError,
    validate_deliver_payload,
    validate_dialogue_complete_payload,
    validate_engage_payload,
    validate_look_payload,
    validate_move_payload,
    validate_party_invite_payload,
    validate_party_leave_payload,
    validate_possess_payload,
    validate_possess_release_payload,
    validate_talk_open_payload,
    validate_talk_scripted_descriptor,
    validate_wait_payload,
)
from web.webclient.presentation.protocol import (
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_exact_fields,
    _require_int,
)

# The freeform pin: the only vocabulary entry whose params are a bare binding.
FREEFORM_ACTION_CODE = "explore.talk_freeform"

# Validators the exploration form reuses for the canonical params of every
# non-freeform action (the freeform binding shape is validated separately).
_ACTION_PAYLOAD_VALIDATORS = {
    "explore.move": validate_move_payload,
    "explore.look": validate_look_payload,
    "explore.talk_open": validate_talk_open_payload,
    "explore.talk_scripted": validate_talk_scripted_descriptor,
    "explore.dialogue_complete": validate_dialogue_complete_payload,
    "explore.party_invite": validate_party_invite_payload,
    "explore.party_leave": validate_party_leave_payload,
    "explore.engage": validate_engage_payload,
    "explore.wait": validate_wait_payload,
    "explore.possess": validate_possess_payload,
    "explore.possess_release": validate_possess_release_payload,
    "explore.deliver": validate_deliver_payload,
}


def validate_affordance_params(action_id: str, params: Any) -> dict[str, Any]:
    """Validate the canonical params of one exploration affordance entry.

    Every non-freeform action's params are run through its registered action
    validator so the wire payload is byte-for-byte what the dispatcher
    accepts; the freeform entry's ``{"npc_id": int}`` binding shape is the
    single exception (no registered validator produces it without ``speech``).
    """
    if action_id == FREEFORM_ACTION_CODE:
        _require_exact_fields(params, "freeform params", {"npc_id"}, {})
        return {"npc_id": _require_int(params, "npc_id", minimum=1, maximum=MAX_SAFE_INTEGER)}
    validator = _ACTION_PAYLOAD_VALIDATORS.get(action_id)
    if validator is None:
        raise ProtocolValidationError(
            f"unregistered action code for payload validation: {action_id}"
        )
    try:
        return validator(params)
    except ExplorationActionError as error:
        raise ProtocolValidationError(str(error)) from error


__all__ = [
    "FREEFORM_ACTION_CODE",
    "validate_affordance_params",
]
