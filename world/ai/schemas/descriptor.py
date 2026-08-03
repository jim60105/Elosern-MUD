"""Layer-neutral per-call request descriptor for generative calls.

Both the client and the guardrail accept this descriptor so a guarded call can
carry the chat messages plus, optionally, an output jsonschema and a schema
identifier. Later layers (changes 18-21) supply their own output schemas
through this transmission contract without touching either module.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ChatRequestDescriptor:
    """One generative call's messages and optional structured-output contract."""

    messages: tuple[dict[str, str], ...] = field(default_factory=tuple)
    output_schema: Mapping[str, Any] | None = None
    schema_id: str | None = None

    def __post_init__(self) -> None:
        if not self.messages:
            raise ValueError("a request descriptor requires at least one message")
        for message in self.messages:
            if not isinstance(message, Mapping):
                raise ValueError("every message must be a role/content mapping")
            role = message.get("role")
            content = message.get("content")
            if not isinstance(role, str) or not isinstance(content, str):
                raise ValueError("every message must carry string role and content")
        if self.output_schema is not None and not isinstance(self.output_schema, Mapping):
            raise ValueError("output_schema must be a mapping when provided")
