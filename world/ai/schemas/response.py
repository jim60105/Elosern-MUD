"""Chat-completion response envelope schema for the OpenAI-compatible client.

This validates the *envelope* the endpoint returns (``choices[0].message.content``)
so the client parse path and guardrail output validation share one contract.
Layer output schemas (rank, reward, archetype, prototype) are owned by changes
18-21 and are deliberately absent here.
"""

from __future__ import annotations

from typing import Any

from jsonschema import Draft7Validator

CHAT_COMPLETION_ENVELOPE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["choices"],
    "properties": {
        "choices": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["message"],
                "properties": {
                    "message": {
                        "type": "object",
                        "required": ["content"],
                        "properties": {
                            "content": {"type": "string"},
                        },
                    },
                },
            },
        },
    },
}

_ENVELOPE_VALIDATOR = Draft7Validator(CHAT_COMPLETION_ENVELOPE_SCHEMA)


def validate_chat_completion_envelope(payload: Any) -> list[str]:
    """Return validation error messages for a chat-completion envelope."""
    return [error.message for error in _ENVELOPE_VALIDATOR.iter_errors(payload)]
