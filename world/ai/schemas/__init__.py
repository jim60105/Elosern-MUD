"""Schemas for generative-layer data.

The response envelope schema (client parse path + guardrail output validation),
the layer-neutral per-call request descriptor, and the output-schema registry
seam for later layer schemas (changes 18-21).
"""

from .descriptor import ChatRequestDescriptor
from .registry import (
    DuplicateSchemaError,
    UnknownSchemaError,
    get_output_schema,
    register_output_schema,
    resolve_output_schema,
)
from .response import (
    CHAT_COMPLETION_ENVELOPE_SCHEMA,
    validate_chat_completion_envelope,
)

__all__ = [
    "CHAT_COMPLETION_ENVELOPE_SCHEMA",
    "ChatRequestDescriptor",
    "DuplicateSchemaError",
    "UnknownSchemaError",
    "get_output_schema",
    "register_output_schema",
    "resolve_output_schema",
    "validate_chat_completion_envelope",
]
