"""Registry seam for caller-supplied per-call output schemas.

Changes 18-21 register their layer output schemas (rank, reward, archetype,
prototype) here by ``schema_id``. A descriptor may carry an inline
``output_schema`` or reference a registered id; the guardrail resolves either.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class UnknownSchemaError(KeyError):
    """Raised when a schema_id is not present in the output-schema registry."""


class DuplicateSchemaError(ValueError):
    """Raised when a schema_id is registered more than once."""


_OUTPUT_SCHEMAS: dict[str, Mapping[str, Any]] = {}


def register_output_schema(schema_id: str, schema: Mapping[str, Any]) -> None:
    """Register a named output jsonschema for later per-call use."""
    if not isinstance(schema_id, str) or not schema_id:
        raise ValueError("schema_id must be a non-empty string")
    if not isinstance(schema, Mapping):
        raise ValueError("schema must be a mapping")
    if schema_id in _OUTPUT_SCHEMAS:
        raise DuplicateSchemaError(schema_id)
    _OUTPUT_SCHEMAS[schema_id] = schema


def get_output_schema(schema_id: str) -> Mapping[str, Any]:
    """Return a registered output schema or raise ``UnknownSchemaError``."""
    try:
        return _OUTPUT_SCHEMAS[schema_id]
    except KeyError as exc:
        raise UnknownSchemaError(schema_id) from exc


def resolve_output_schema(
    output_schema: Mapping[str, Any] | None,
    schema_id: str | None,
) -> Mapping[str, Any] | None:
    """Resolve an inline schema, else a registered schema by id, else None."""
    if output_schema is not None:
        return output_schema
    if schema_id is not None:
        return get_output_schema(schema_id)
    return None
