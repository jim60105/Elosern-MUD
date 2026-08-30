"""Exact schema-version-1 ``lineage`` panel and presenter (skill-lineage-panel).

The presenter serializes the pure ``world.rules.lineage_query`` read model for
the authenticated puppet. It reads no raw persistent records itself and mutates
nothing. Malformed proficiency data fails the panel closed through the common
unavailable form — no fabricated node values.

Wire caps (design DD3, mirrored by the JS validator): at most
``MAX_CHAINS`` chains of at most ``MAX_NODES_PER_CHAIN`` nodes, with bounded
text lengths. Truncation follows one fixed declared order: drop trailing
chains to the chain cap, then trailing nodes to the per-chain cap, then
further trailing chains until the payload fits the OOB envelope.
``completed_count``/``total_count`` always describe the FULL untruncated view,
and chain ``meter``/``consumed`` keep their full-chain values.
"""

from math import isfinite
from typing import Any

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_bool,
    _require_exact_fields,
    _require_int,
    _require_str,
    _validate_identifier,
    json_byte_size,
)
from web.webclient.presentation.registry import PanelUnavailableError
from world.rules.lineage_query import LineageQueryError, build_lineage_view

LINEAGE_SCHEMA_VERSION = 1

# Exact shared bounds -- must stay equal in the JS validator.
MAX_CHAINS = 16
MAX_NODES_PER_CHAIN = 32
MAX_KEY_CODE_POINTS = 64
# Cross-referenced with world/rules/lineage_query.LINEAGE_TEXT_WIRE_MAX: the
# read model clamps rendered 「需「label Lv.N」」 text to this bound before it
# reaches the validator, so a legal 128-code-point registry label can never
# push the whole panel into the unavailable form (rubber-duck R2-1).
MAX_TEXT_CODE_POINTS = 128


class LineagePanelError(ProtocolValidationError):
    """The available lineage payload violates its exact bounded schema."""


def _require_number(value: Any, field: str, *, minimum: float, maximum: float) -> float:
    """Return a non-boolean, finite int/float within bounds."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProtocolValidationError(f"{field} must be a number")
    if isinstance(value, float) and not isfinite(value):
        raise ProtocolValidationError(f"{field} must be finite")
    if value < minimum or value > maximum:
        raise ProtocolValidationError(f"{field} is out of bounds")
    return value


def _validate_node(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "lineage node",
        {
            "skill_key",
            "display_name_zh",
            "owned",
            "usable",
            "level",
            "xp_into_level",
            "xp_to_next_level",
            "capped",
            "prereq_text_zh",
        },
        {},
    )
    skill_key = _validate_identifier(value["skill_key"], "skill_key")
    if len(skill_key) > MAX_KEY_CODE_POINTS:
        raise LineagePanelError("skill_key exceeds its bound")
    display_name = _require_str(
        value, "display_name_zh", maximum=MAX_TEXT_CODE_POINTS
    )
    if not display_name.strip():
        raise LineagePanelError("display_name_zh must be non-empty")
    prereq_text = _require_str(value, "prereq_text_zh", maximum=MAX_TEXT_CODE_POINTS)
    return {
        "skill_key": skill_key,
        "display_name_zh": display_name,
        "owned": _require_bool(value, "owned"),
        "usable": _require_bool(value, "usable"),
        "level": _require_int(value, "level", minimum=0, maximum=MAX_SAFE_INTEGER),
        "xp_into_level": _require_number(
            value["xp_into_level"], "xp_into_level", minimum=0, maximum=MAX_SAFE_INTEGER
        ),
        "xp_to_next_level": _require_number(
            value["xp_to_next_level"],
            "xp_to_next_level",
            minimum=0,
            maximum=MAX_SAFE_INTEGER,
        ),
        "capped": _require_bool(value, "capped"),
        "prereq_text_zh": prereq_text,
    }


def _validate_chain(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "lineage chain",
        {"root_skill_key", "element_or_style_zh", "consumed", "meter", "nodes"},
        {},
    )
    root_key = _validate_identifier(value["root_skill_key"], "root_skill_key")
    if len(root_key) > MAX_KEY_CODE_POINTS:
        raise LineagePanelError("root_skill_key exceeds its bound")
    label = _require_str(value, "element_or_style_zh", maximum=MAX_TEXT_CODE_POINTS)
    if not label.strip():
        raise LineagePanelError("element_or_style_zh must be non-empty")
    nodes = value["nodes"]
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= MAX_NODES_PER_CHAIN:
        raise LineagePanelError(f"nodes must be a list of 1..{MAX_NODES_PER_CHAIN} entries")
    node_views = [_validate_node(item) for item in nodes]
    if node_views[0]["skill_key"] != root_key:
        raise LineagePanelError(
            "truncated chains keep their head: nodes[0] must be the root"
        )
    return {
        "root_skill_key": root_key,
        "element_or_style_zh": label,
        "consumed": _require_bool(value, "consumed"),
        "meter": _require_number(value["meter"], "meter", minimum=0, maximum=1),
        "nodes": node_views,
    }


def validate_lineage(payload: Any) -> dict[str, Any]:
    """Validate one exact available ``lineage`` payload.

    Returns a normalized payload or raises :class:`LineagePanelError`. The
    common unavailable form is NOT accepted here; the registry handles it.
    """
    _require_exact_fields(
        payload,
        "lineage panel",
        {
            "schema_version",
            "available",
            "kind",
            "completed_count",
            "total_count",
            "chains",
        },
        {},
    )
    if _require_int(
        payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER
    ) != LINEAGE_SCHEMA_VERSION:
        raise LineagePanelError("unsupported lineage schema_version")
    if not _require_bool(payload, "available"):
        raise LineagePanelError("available must be true for the lineage form")
    if payload["kind"] != "lineage":
        raise LineagePanelError("lineage panel kind must be lineage")
    completed = _require_int(
        payload, "completed_count", minimum=0, maximum=MAX_SAFE_INTEGER
    )
    total = _require_int(payload, "total_count", minimum=0, maximum=MAX_SAFE_INTEGER)
    if completed > total:
        raise LineagePanelError("completed_count must not exceed total_count")
    chains = payload["chains"]
    if not isinstance(chains, list) or len(chains) > MAX_CHAINS:
        raise LineagePanelError(f"chains must be a list of at most {MAX_CHAINS} entries")
    chain_views = [_validate_chain(item) for item in chains]
    result = {
        "schema_version": LINEAGE_SCHEMA_VERSION,
        "available": True,
        "kind": "lineage",
        "completed_count": completed,
        "total_count": total,
        "chains": chain_views,
    }
    # Envelope guarantee: the presenter truncates until a real payload fits;
    # the validator enforces the serialized size directly, so a hand-built
    # all-ceilings payload fails closed rather than being emitted.
    if json_byte_size(result) > MAX_CANONICAL_JSON_BYTES:
        raise LineagePanelError("lineage payload exceeds the OOB envelope limit")
    return result


def _serialize_chain(chain: Any) -> dict[str, Any]:
    return {
        "root_skill_key": chain.root_skill_key,
        "element_or_style_zh": chain.element_or_style_zh,
        "consumed": chain.consumed,
        "meter": chain.meter,
        "nodes": [
            {
                "skill_key": node.skill_key,
                "display_name_zh": node.display_name_zh,
                "owned": node.owned,
                "usable": node.usable,
                "level": node.level,
                "xp_into_level": node.xp_into_level,
                "xp_to_next_level": node.xp_to_next_level,
                "capped": node.capped,
                "prereq_text_zh": node.prereq_text_zh,
            }
            for node in chain.nodes
        ],
    }


def lineage_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``lineage`` panel for the puppet.

    Truncation (declared order, design DD3): trailing chains to the chain cap,
    then trailing nodes to the per-chain cap, then further trailing chains
    until the serialized payload fits the envelope. Header counts and each
    chain's meter/consumed always come from the FULL view.
    """
    try:
        view = build_lineage_view(context.actor)
    except LineageQueryError:
        raise PanelUnavailableError from None
    serialized = [_serialize_chain(chain) for chain in view.chains]
    kept = min(len(serialized), MAX_CHAINS)
    while True:
        truncated = [
            {**chain, "nodes": chain["nodes"][:MAX_NODES_PER_CHAIN]}
            for chain in serialized[:kept]
        ]
        payload = {
            "schema_version": LINEAGE_SCHEMA_VERSION,
            "available": True,
            "kind": "lineage",
            "completed_count": view.completed_count,
            "total_count": view.total_count,
            "chains": truncated,
        }
        if json_byte_size(payload) <= MAX_CANONICAL_JSON_BYTES:
            break
        if kept <= 1:
            # A single caps-bounded chain cannot exceed the envelope; anything
            # else is a bug, and the panel fails closed rather than emitting.
            raise PanelUnavailableError from None
        kept -= 1
    return validate_lineage(payload)
