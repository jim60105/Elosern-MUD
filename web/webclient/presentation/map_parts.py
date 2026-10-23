"""Bounded atomic part codec for on-demand map panels.

A logical ``area_map``/``world_map`` body may exceed one existing OOB frame
(65,536 canonical bytes, 320-item lists). It then travels as indexed parts
(OpenSpec change define-map-panel-protocol): every part is an ordinary
``ui_update`` frame whose ``panels`` hold exactly that map panel in the part
wire variant

    {"schema_version": 1, "available": true,
     "part": {"transfer_id", "index", "count", "byte_length", "chunk"}}

``chunk`` is standard padded base64 of one slice of the canonical UTF-8 JSON
of the logical body. Slices are fixed-size: every part except the last holds
exactly :data:`MAP_PART_RAW_BYTES` raw bytes, so ``count`` is
``ceil(byte_length / MAP_PART_RAW_BYTES)``. All parts of a transfer share one
transfer ID, epoch, revision and frame metadata; the browser adopts the body
only after the complete byte sequence decodes and validates.

This is map-panel delivery only, not a general streaming API. The browser
assembler lives in ``web/static/webclient/js/elosern/protocol/map_parts.js``.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
from typing import Any

from web.webclient.presentation.map_panels import (
    MAP_MAX_BYTES,
    MAP_PANEL_SCHEMAS,
    MapPanelError,
    validate_map_panel,
)
from web.webclient.presentation.protocol import (
    MAX_STRING_CODE_POINTS,
    new_presentation_epoch,
)

MAP_PART_SCHEMA_VERSION = 1
#: Raw bytes per part; base64 inflates them to exactly the generic string cap.
MAP_PART_RAW_BYTES = 1_536
MAP_PART_CHUNK_CHARS = 2_048
TRANSFER_ID_LENGTH = 22
_TRANSFER_ID_RE = re.compile(r"^[A-Za-z0-9_-]{22}$")

assert MAP_PART_CHUNK_CHARS == MAP_PART_RAW_BYTES * 4 // 3 <= MAX_STRING_CODE_POINTS


def max_parts(panel: str) -> int:
    """The finite part-count ceiling of one map panel's transfer."""
    return -(-MAP_MAX_BYTES[panel] // MAP_PART_RAW_BYTES)


def canonical_bytes(payload: Any) -> bytes:
    """Canonical UTF-8 JSON (sorted keys, no whitespace, non-ASCII kept)."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _expected_chunk_bytes(index: int, count: int, byte_length: int) -> int:
    if index < count - 1:
        return MAP_PART_RAW_BYTES
    return byte_length - MAP_PART_RAW_BYTES * (count - 1)


def encode_map_parts(panel: str, payload: Any, *, transfer_id: str | None = None) -> list[dict[str, Any]]:
    """Validate a logical map body and split it into exact part panel values."""
    raw = canonical_bytes(validate_map_panel(panel, payload))
    if len(raw) > MAP_MAX_BYTES[panel]:
        raise MapPanelError(f"{panel} exceeds {MAP_MAX_BYTES[panel]} canonical bytes")
    transfer = transfer_id or new_presentation_epoch()
    if not _TRANSFER_ID_RE.fullmatch(transfer):
        raise MapPanelError("transfer_id must be 22 URL-safe ASCII characters")
    count = -(-len(raw) // MAP_PART_RAW_BYTES)
    return [
        {
            "schema_version": MAP_PART_SCHEMA_VERSION,
            "available": True,
            "part": {
                "transfer_id": transfer,
                "index": index,
                "count": count,
                "byte_length": len(raw),
                "chunk": base64.b64encode(
                    raw[index * MAP_PART_RAW_BYTES : (index + 1) * MAP_PART_RAW_BYTES]
                ).decode("ascii"),
            },
        }
        for index in range(count)
    ]


def _part_int(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise MapPanelError(f"{name} must be an integer within {minimum}..{maximum}")
    return value


def validate_map_part(panel: str, value: Any) -> tuple[dict[str, Any], bytes]:
    """Validate one part wire value; return its normalized header and raw bytes."""
    if panel not in MAP_PANEL_SCHEMAS:
        raise MapPanelError(f"{panel!r} is not an on-demand map panel")
    if not isinstance(value, dict) or set(value) != {"schema_version", "available", "part"}:
        raise MapPanelError("a map part must hold exactly schema_version, available and part")
    if isinstance(value["schema_version"], bool) or value["schema_version"] != MAP_PART_SCHEMA_VERSION:
        raise MapPanelError("unsupported map part schema_version")
    if value["available"] is not True:
        raise MapPanelError("a map part must be available")
    part = value["part"]
    if not isinstance(part, dict) or set(part) != {"transfer_id", "index", "count", "byte_length", "chunk"}:
        raise MapPanelError("part must hold exactly transfer_id, index, count, byte_length and chunk")
    transfer = part["transfer_id"]
    if not isinstance(transfer, str) or not _TRANSFER_ID_RE.fullmatch(transfer):
        raise MapPanelError("transfer_id must be 22 URL-safe ASCII characters")
    byte_length = _part_int(part["byte_length"], "byte_length", 1, MAP_MAX_BYTES[panel])
    count = _part_int(part["count"], "count", 1, max_parts(panel))
    if count != -(-byte_length // MAP_PART_RAW_BYTES):
        raise MapPanelError("count must equal ceil(byte_length / part size)")
    index = _part_int(part["index"], "index", 0, count - 1)
    chunk = part["chunk"]
    if not isinstance(chunk, str) or not 4 <= len(chunk) <= MAP_PART_CHUNK_CHARS:
        raise MapPanelError("chunk must be 4..2048 base64 characters")
    try:
        raw = base64.b64decode(chunk, validate=True)
    except (binascii.Error, ValueError) as error:
        raise MapPanelError("chunk is not canonical base64") from error
    if base64.b64encode(raw).decode("ascii") != chunk:
        raise MapPanelError("chunk is not canonical base64")
    if len(raw) != _expected_chunk_bytes(index, count, byte_length):
        raise MapPanelError("chunk size does not match its index")
    header = {"transfer_id": transfer, "index": index, "count": count, "byte_length": byte_length}
    return header, raw


def decode_map_parts(panel: str, parts: list[Any]) -> dict[str, Any]:
    """Reassemble a complete ordered transfer and validate the logical body."""
    if not parts:
        raise MapPanelError("a transfer needs at least one part")
    decoded = [validate_map_part(panel, value) for value in parts]
    first = decoded[0][0]
    if len(decoded) != first["count"]:
        raise MapPanelError("a transfer must hold exactly count parts")
    for position, (header, _) in enumerate(decoded):
        if header["index"] != position or any(
            header[key] != first[key] for key in ("transfer_id", "count", "byte_length")
        ):
            raise MapPanelError("parts must be one ordered transfer")
    raw = b"".join(chunk for _, chunk in decoded)
    if len(raw) != first["byte_length"]:
        raise MapPanelError("reassembled bytes do not match byte_length")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise MapPanelError("reassembled body is not UTF-8 JSON") from error
    return validate_map_panel(panel, payload)


__all__ = [
    "MAP_PART_CHUNK_CHARS",
    "MAP_PART_RAW_BYTES",
    "MAP_PART_SCHEMA_VERSION",
    "TRANSFER_ID_LENGTH",
    "canonical_bytes",
    "decode_map_parts",
    "encode_map_parts",
    "max_parts",
    "validate_map_part",
]
