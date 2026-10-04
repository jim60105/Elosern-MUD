"""Value-only guarded letter proposals, with a restricted remote channel."""

import json
from dataclasses import dataclass

from twisted.internet import defer

from world.ai.guardrail import GuardrailHooks, GuardrailRegistrationError, guarded_call
from world.ai.schemas import ChatRequestDescriptor
from world.ai.schemas.registry import DuplicateSchemaError, _OUTPUT_SCHEMAS, register_output_schema


CORRESPONDENCE_SCHEMA = {
    "type": "object",
    "required": ["body", "effect"],
    "additionalProperties": False,
    "properties": {
        "body": {"type": "string", "minLength": 1, "maxLength": 2000},
        "effect": {
            "oneOf": [
                {"type": "object", "required": ["kind"], "additionalProperties": False,
                 "properties": {"kind": {"const": "none"}}},
                {"type": "object", "required": ["kind", "delta"], "additionalProperties": False,
                 "properties": {"kind": {"const": "adjust_relation"},
                                "delta": {"type": "integer", "minimum": 0, "maximum": 10}}},
            ],
        },
    },
}


@dataclass(frozen=True)
class LetterReply:
    """Detached proposal; no live object, mutable intent, or writer authority."""

    body: str
    relation_delta: int | None = None


def _fallback():
    return None


def validate_reply(parsed):
    """Channel-specific semantic bound, separate from face-to-face intents."""
    body = parsed.get("body", "") if isinstance(parsed, dict) else ""
    if not isinstance(body, str) or not body.strip() or not any("\u4e00" <= c <= "\u9fff" for c in body):
        return ["Letter body must contain nonempty Traditional Chinese prose."]
    return []


_HOOKS = GuardrailHooks("correspondence", _fallback, {"letter_body": validate_reply})


def register_correspondence():
    """Install the dedicated channel guardrail idempotently."""
    try:
        _HOOKS.install()
        if _OUTPUT_SCHEMAS.get("correspondence") is not CORRESPONDENCE_SCHEMA:
            register_output_schema("correspondence", CORRESPONDENCE_SCHEMA)
    except (GuardrailRegistrationError, DuplicateSchemaError):
        _HOOKS.uninstall_own()
        if _OUTPUT_SCHEMAS.get("correspondence") is CORRESPONDENCE_SCHEMA:
            del _OUTPUT_SCHEMAS["correspondence"]
        raise


@defer.inlineCallbacks
def generate_letter_reply(client, messages):
    """Return a frozen proposal or no response, never invented fallback text."""
    descriptor = ChatRequestDescriptor(messages=tuple(messages), schema_id="correspondence")
    text = yield guarded_call("correspondence", client, descriptor)
    if text is None:
        return None
    parsed = json.loads(text)
    return LetterReply(parsed["body"], parsed["effect"].get("delta"))
