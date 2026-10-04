"""Strict dream actions; generation runs without holding the UI action lock."""

from functools import partial

from web.webclient.presentation.protocol import ProtocolValidationError
from world.narrative.dream_session import MAX_RENDERED_INPUT_CHARS, MAX_SESSION_ID_LENGTH
from world.narrative.authoring import MAX_SUMMARY_CHARACTERS, DIRECTION_KEYS


def validate(action, payload):
    required = {"session_id", "revision"}
    allowed = required | ({"message_parts"} if action == "say" else {"direction"} if action in {"draft", "confirm"} else set())
    if not isinstance(payload, dict) or not required <= set(payload) or set(payload) - allowed:
        raise ProtocolValidationError("invalid dream payload fields")
    handle = payload["session_id"]
    revision = payload["revision"]
    if not isinstance(handle, str) or not 1 <= len(handle) <= MAX_SESSION_ID_LENGTH:
        raise ProtocolValidationError("invalid dream session")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise ProtocolValidationError("invalid dream revision")
    if action == "say":
        parts = payload.get("message_parts")
        if (not isinstance(parts, list) or not 1 <= len(parts) <= 2
                or any(not isinstance(part, str) or len(part) > 2000 for part in parts)
                or not "".join(parts).strip()):
            raise ProtocolValidationError("invalid bounded dream message parts")
        return {"session_id": handle, "revision": revision, "message": "".join(parts)}
    field = "direction"
    if field in allowed:
        text = payload.get(field, "")
        if isinstance(text, dict):
            if set(text) - DIRECTION_KEYS:
                raise ProtocolValidationError("unknown creative direction fields")
            return dict(payload)
        bound = MAX_RENDERED_INPUT_CHARS if action == "say" else MAX_SUMMARY_CHARACTERS
        if not isinstance(text, str) or len(text) > bound or (action == "say" and not text.strip()):
            raise ProtocolValidationError("invalid bounded dream text")
    return dict(payload)


def adapter(action, actor, payload, session=None):
    from server.dream_service import act
    deferred = act(actor, action, session=session, **payload)
    if action == "say" and not deferred.called:
        # Generation completion refreshes the panel separately. Returning now
        # keeps draft/confirm/awakening dispatchable while a model is pending.
        return {"outcome": "success", "code": "dream_pending",
                "message": "夢境回應生成中，你仍可儲存草稿或醒來。",
                "affected_panels": ("dream",)}
    return deferred


def register_actions(registry):
    from web.webclient.actions.registry import ActionSpec
    for action in ("say", "draft", "confirm", "awaken"):
        registry.register(ActionSpec(
            "dream." + action, partial(validate, action), partial(adapter, action), ("dream",),
        ))
