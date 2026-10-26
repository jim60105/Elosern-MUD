"""Bounded general publication codec for eager snapshots and deltas.

A logical ``ui_snapshot``/``ui_update`` document is encoded exactly once into
canonical UTF-8 JSON. When it fits the applicable *intact* envelope allowance it
travels unchanged under its original command. Otherwise it travels as indexed
parts of that one canonical byte sequence, each part an exact
``ui_publication_part`` frame in the first positional transport argument:

    {protocol_version: 1, presentation_epoch, revision, publication_kind,
     transfer_id, part_index, part_count, total_bytes, chunks}
    (plus base_revision for a delta, forbidden for a snapshot)

``publication_kind`` is exactly ``snapshot`` or ``delta``. Every part of a
transfer repeats the same epoch/revision/kind/transfer/count/total (and base),
so the receiver can prove header/body agreement before adoption. ``chunks``
holds at most sixteen standard padded RFC 4648 base64 strings; every non-final
string decodes to exactly :data:`PUBLICATION_CHUNK_BYTES` raw bytes and the
final string to the exact remainder. Nothing is truncated: a publication above
the finite logical ceiling fails preflight instead.

The generic 65,536-byte frame ceiling is unchanged and every part envelope is
checked against it, but the *reassembled* logical document is validated against
the logical schema, its panel-local limits and the finite aggregate ceiling; the
single-frame byte ceiling is not reapplied to it. The available-dialogue intact
allowance (98,304-byte whole envelope, 24,576-byte dialogue panel, 65,536-byte
dialogue-removed envelope) stays an intact-frame allowance: it never becomes a
logical aggregate cap. Specialized on-demand map bodies keep their own protocol
and are never wrapped in general parts.

The shared resource limits are named identically in this module and in
``web/static/webclient/js/elosern/protocol/constants.js``:

===========================  ==========================================
``PUBLICATION_MAX_BYTES``    16,777,216 logical bytes before fragmentation
``PUBLICATION_PART_BYTES``   24,576 raw bytes per part
``PUBLICATION_CHUNK_BYTES``  1,536 raw bytes per base64 chunk
``PUBLICATION_MAX_CHUNKS``   16 chunks per part
``PUBLICATION_MAX_PARTS``    683 parts (derived from the two ceilings)
``PUBLICATION_ASSEMBLY_TIMEOUT_MS``  30,000 ms receiver assembly lifetime
``PUBLICATION_MAX_ASSEMBLIES``       1 live general transfer per transport
===========================  ==========================================

The last two are receiver policy declarations on this sender slice; the browser
assembly owner enforces them. The browser assembler and wire decoder live in
``web/static/webclient/js/elosern/protocol/``.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import re
from collections.abc import Mapping
from typing import Any, Callable

from web.webclient.presentation.protocol import (
    DIALOGUE_PANEL,
    DIALOGUE_PANEL_MAX_BYTES,
    JSONSafetyError,
    MAX_SAFE_INTEGER,
    MAX_STRING_CODE_POINTS,
    UI_PUBLICATION_PART,
    UI_SNAPSHOT,
    UI_UPDATE,
    ProtocolValidationError,
    _validate_correlation_id,
    _validate_epoch,
    _validate_identifier,
    _validate_message,
    _validate_revision,
    carries_available_dialogue,
    check_envelope,
    check_envelope_bytes,
    check_json_safety,
    json_byte_size,
    validate_ui_snapshot,
    validate_ui_update,
)
from web.webclient.presentation.publication import PreparedFrame

#: Logical publication bytes (canonical UTF-8 JSON) before fragmentation.
PUBLICATION_MAX_BYTES = 16_777_216
#: Raw bytes carried by one part.
PUBLICATION_PART_BYTES = 24_576
#: Raw bytes decoded from one base64 chunk.
PUBLICATION_CHUNK_BYTES = 1_536
#: Base64 chunks per part.
PUBLICATION_MAX_CHUNKS = 16
#: Parts per logical publication, derived from the two byte ceilings.
PUBLICATION_MAX_PARTS = 683
#: Receiver assembly lifetime from the first accepted part.
PUBLICATION_ASSEMBLY_TIMEOUT_MS = 30_000
#: Live general-publication assemblies per active transport.
PUBLICATION_MAX_ASSEMBLIES = 1

#: The closed publication-kind vocabulary.
PUBLICATION_KINDS = ("snapshot", "delta")
#: ASCII characters of one base64 chunk (the generic string cap exactly).
PUBLICATION_CHUNK_CHARS = PUBLICATION_CHUNK_BYTES * 4 // 3
#: Lowercase hex characters of one transfer identity (128 random bits).
TRANSFER_ID_LENGTH = 32

_TRANSFER_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_PUBLICATION_MESSAGES = {UI_SNAPSHOT: "snapshot", UI_UPDATE: "delta"}
_PART_FIELDS = frozenset(
    {
        "protocol_version",
        "presentation_epoch",
        "revision",
        "publication_kind",
        "transfer_id",
        "part_index",
        "part_count",
        "total_bytes",
        "chunks",
    }
)

assert PUBLICATION_MAX_PARTS == -(-PUBLICATION_MAX_BYTES // PUBLICATION_PART_BYTES)
assert PUBLICATION_MAX_CHUNKS == PUBLICATION_PART_BYTES // PUBLICATION_CHUNK_BYTES
assert PUBLICATION_PART_BYTES % PUBLICATION_CHUNK_BYTES == 0
assert PUBLICATION_CHUNK_CHARS == MAX_STRING_CODE_POINTS


class PublicationCodecError(ProtocolValidationError):
    """A logical publication or one of its prepared frames violates the codec."""


#: One eager panel's exact available-form validator and its schema version.
PanelValidators = Mapping[str, "tuple[Callable[[Any], Any], int]"]


def canonical_bytes(payload: Any) -> bytes:
    """Canonical UTF-8 JSON: sorted keys, no whitespace, non-ASCII kept."""
    return json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def new_transfer_id() -> str:
    """Return one transfer identity: 32 lowercase hex characters from 128 bits."""
    return os.urandom(16).hex()


def _part_bytes(index: int, count: int, total_bytes: int) -> int:
    if index < count - 1:
        return PUBLICATION_PART_BYTES
    return total_bytes - PUBLICATION_PART_BYTES * (count - 1)


def _chunk_bytes(index: int, count: int, part_bytes: int) -> int:
    if index < count - 1:
        return PUBLICATION_CHUNK_BYTES
    return part_bytes - PUBLICATION_CHUNK_BYTES * (count - 1)


def _part_ints(header: Mapping[str, Any]) -> tuple[int, int, int]:
    """Validate and return ``(part_count, total_bytes, part_index)``."""
    total_bytes = header["total_bytes"]
    if isinstance(total_bytes, bool) or not isinstance(total_bytes, int):
        raise PublicationCodecError("total_bytes must be an integer")
    if not 1 <= total_bytes <= PUBLICATION_MAX_BYTES:
        raise PublicationCodecError(
            f"total_bytes must be within 1..{PUBLICATION_MAX_BYTES}"
        )
    part_count = header["part_count"]
    if isinstance(part_count, bool) or not isinstance(part_count, int):
        raise PublicationCodecError("part_count must be an integer")
    if not 1 <= part_count <= PUBLICATION_MAX_PARTS:
        raise PublicationCodecError(
            f"part_count must be within 1..{PUBLICATION_MAX_PARTS}"
        )
    if part_count != -(-total_bytes // PUBLICATION_PART_BYTES):
        raise PublicationCodecError(
            "part_count must equal ceil(total_bytes / part size)"
        )
    part_index = header["part_index"]
    if isinstance(part_index, bool) or not isinstance(part_index, int):
        raise PublicationCodecError("part_index must be an integer")
    if not 0 <= part_index < part_count:
        raise PublicationCodecError("part_index must be within 0..part_count-1")
    return part_count, total_bytes, part_index


def encode_publication_parts(
    canonical: bytes,
    *,
    presentation_epoch: str,
    revision: int,
    publication_kind: str,
    base_revision: int | None = None,
    transfer_id: str | None = None,
) -> list[dict[str, Any]]:
    """Split already-canonical logical bytes into exact part frames.

    This is the pure splitter: the caller owns canonical bytes that already
    passed logical validation (or, in a focused boundary test, synthetic bytes
    of the same shape). Every returned envelope is checked against the
    unchanged generic frame ceiling before it is returned.
    """
    if not isinstance(canonical, (bytes, bytearray)):
        raise PublicationCodecError("canonical publication must be bytes")
    canonical = bytes(canonical)
    total_bytes = len(canonical)
    if not 1 <= total_bytes <= PUBLICATION_MAX_BYTES:
        raise PublicationCodecError(
            f"logical publication must be 1..{PUBLICATION_MAX_BYTES} bytes"
        )
    epoch = _validate_epoch(presentation_epoch)
    target = _validate_revision(revision, "revision", minimum=1)
    if publication_kind not in PUBLICATION_KINDS:
        raise PublicationCodecError(f"publication_kind must be one of {PUBLICATION_KINDS}")
    if publication_kind == "delta":
        if base_revision is None:
            raise PublicationCodecError("a delta part requires base_revision")
        base = _validate_revision(base_revision, "base_revision", minimum=1)
        if base >= target:
            raise PublicationCodecError("base_revision must be older than revision")
    else:
        if base_revision is not None:
            raise PublicationCodecError("a snapshot part forbids base_revision")
        base = None
    transfer = transfer_id if transfer_id is not None else new_transfer_id()
    if not isinstance(transfer, str) or not _TRANSFER_ID_RE.fullmatch(transfer):
        raise PublicationCodecError(
            "transfer_id must be 32 lowercase hexadecimal characters"
        )

    part_count = -(-total_bytes // PUBLICATION_PART_BYTES)
    parts: list[dict[str, Any]] = []
    for index in range(part_count):
        start = index * PUBLICATION_PART_BYTES
        raw = canonical[start : start + PUBLICATION_PART_BYTES]
        chunk_count = -(-len(raw) // PUBLICATION_CHUNK_BYTES)
        chunks = [
            base64.b64encode(
                raw[chunk * PUBLICATION_CHUNK_BYTES : (chunk + 1) * PUBLICATION_CHUNK_BYTES]
            ).decode("ascii")
            for chunk in range(chunk_count)
        ]
        envelope: dict[str, Any] = {
            "protocol_version": 1,
            "presentation_epoch": epoch,
            "revision": target,
            "publication_kind": publication_kind,
            "transfer_id": transfer,
            "part_index": index,
            "part_count": part_count,
            "total_bytes": total_bytes,
            "chunks": chunks,
        }
        if base is not None:
            envelope["base_revision"] = base
        check_envelope(envelope)
        parts.append(envelope)
    return parts


def validate_publication_part(value: Any) -> tuple[dict[str, Any], bytes]:
    """Validate one part frame; return its normalized header and raw bytes."""
    if not isinstance(value, dict):
        raise PublicationCodecError("a publication part must be a JSON object")
    missing = _PART_FIELDS - set(value)
    if missing:
        raise PublicationCodecError(
            f"a publication part is missing required fields {sorted(missing)}"
        )
    unknown = set(value) - _PART_FIELDS - {"base_revision"}
    if unknown:
        raise PublicationCodecError(
            f"a publication part has unknown fields {sorted(unknown)}"
        )
    check_envelope(value)
    version = value["protocol_version"]
    if isinstance(version, bool) or not isinstance(version, int):
        raise PublicationCodecError("protocol_version must be an integer")
    if version != 1:
        raise PublicationCodecError("unsupported protocol_version")
    epoch = _validate_epoch(value["presentation_epoch"])
    revision = _validate_revision(value["revision"], "revision", minimum=1)
    kind = value["publication_kind"]
    if kind not in PUBLICATION_KINDS:
        raise PublicationCodecError(
            f"publication_kind must be one of {PUBLICATION_KINDS}"
        )
    transfer = value["transfer_id"]
    if not isinstance(transfer, str) or not _TRANSFER_ID_RE.fullmatch(transfer):
        raise PublicationCodecError(
            "transfer_id must be 32 lowercase hexadecimal characters"
        )
    if kind == "delta":
        if "base_revision" not in value:
            raise PublicationCodecError("a delta part requires base_revision")
        base = _validate_revision(value["base_revision"], "base_revision", minimum=1)
        if base >= revision:
            raise PublicationCodecError("base_revision must be older than revision")
    else:
        if "base_revision" in value:
            raise PublicationCodecError("a snapshot part forbids base_revision")
        base = None
    part_count, total_bytes, part_index = _part_ints(value)
    chunks = value["chunks"]
    if not isinstance(chunks, list):
        raise PublicationCodecError("chunks must be a JSON array")
    part_bytes = _part_bytes(part_index, part_count, total_bytes)
    if len(chunks) != -(-part_bytes // PUBLICATION_CHUNK_BYTES):
        raise PublicationCodecError("chunks must equal ceil(part bytes / chunk size)")
    if not 1 <= len(chunks) <= PUBLICATION_MAX_CHUNKS:
        raise PublicationCodecError(
            f"chunks must hold 1..{PUBLICATION_MAX_CHUNKS} strings"
        )
    raw = bytearray()
    for index, chunk in enumerate(chunks):
        if not isinstance(chunk, str) or not 4 <= len(chunk) <= PUBLICATION_CHUNK_CHARS:
            raise PublicationCodecError(
                f"chunk {index} must be 4..{PUBLICATION_CHUNK_CHARS} base64 characters"
            )
        try:
            decoded = base64.b64decode(chunk, validate=True)
        except (binascii.Error, ValueError) as error:
            raise PublicationCodecError(f"chunk {index} is not canonical base64") from error
        if base64.b64encode(decoded).decode("ascii") != chunk:
            raise PublicationCodecError(f"chunk {index} is not canonical base64")
        if len(decoded) != _chunk_bytes(index, len(chunks), part_bytes):
            raise PublicationCodecError(f"chunk {index} size does not match its index")
        raw.extend(decoded)
    header = {
        "protocol_version": 1,
        "presentation_epoch": epoch,
        "revision": revision,
        "publication_kind": kind,
        "transfer_id": transfer,
        "part_index": part_index,
        "part_count": part_count,
        "total_bytes": total_bytes,
    }
    if base is not None:
        header["base_revision"] = base
    return header, bytes(raw)


def _validate_unavailable_panel(
    name: str, payload: Mapping[str, Any], schema_version: int
) -> None:
    """Validate the exact common unavailable form of one registered panel."""
    if set(payload) != {"schema_version", "available", "reason"}:
        raise PublicationCodecError(
            f"unavailable panel {name!r} must hold exactly schema_version, available and reason"
        )
    version = payload["schema_version"]
    if isinstance(version, bool) or version != schema_version:
        raise PublicationCodecError(
            f"unavailable panel {name!r} must carry schema_version {schema_version}"
        )
    if payload["available"] is not False:
        raise PublicationCodecError(f"unavailable panel {name!r} must set available false")
    reason = payload["reason"]
    if not isinstance(reason, Mapping) or not {"code", "message"} <= set(reason):
        raise PublicationCodecError(
            f"unavailable panel {name!r} reason must carry code and message"
        )
    if set(reason) - {"code", "message", "correlation_id"}:
        raise PublicationCodecError(f"unavailable panel {name!r} reason has unknown fields")
    _validate_identifier(reason["code"], f"{name} reason.code")
    _validate_message(reason["message"], f"{name} reason.message")
    if "correlation_id" in reason:
        _validate_correlation_id(reason["correlation_id"])


def validate_publication_panels(
    panels: Mapping[str, Any], panel_validators: PanelValidators | None
) -> None:
    """Validate every supplied panel that has a registered schema validator.

    A production registry supplies its eager panels' own validators, so a
    supplied candidate cannot bypass its panel schema. The exact common
    ``available: false`` form is validated here as well, never fed to an
    available-form validator. A validator failure is never swallowed.
    """
    if not panel_validators:
        return
    for name, payload in panels.items():
        registered = panel_validators.get(name)
        if registered is None:
            continue
        validator, schema_version = registered
        try:
            if isinstance(payload, Mapping) and payload.get("available") is False:
                _validate_unavailable_panel(name, payload, schema_version)
            else:
                validator(payload)
        except ProtocolValidationError as error:
            raise PublicationCodecError(
                f"panel {name!r} violates its registered schema: {error}"
            ) from error


def _check_dialogue_panel_cap(logical: Mapping[str, Any]) -> None:
    """Reject an over-bound dialogue panel; it never becomes fragmentation."""
    if not carries_available_dialogue(logical):
        return
    dialogue = logical["panels"][DIALOGUE_PANEL]
    size = json_byte_size(dialogue)
    if size > DIALOGUE_PANEL_MAX_BYTES:
        raise PublicationCodecError(
            f"dialogue panel exceeds {DIALOGUE_PANEL_MAX_BYTES} canonical bytes"
        )


def _logical_panels(logical: Mapping[str, Any]) -> Mapping[str, Any]:
    from web.webclient.presentation.map_panels import MAP_PANEL_SCHEMAS

    panels = logical["panels"]
    on_demand = sorted(set(MAP_PANEL_SCHEMAS) & set(panels))
    if on_demand:
        raise PublicationCodecError(
            f"general publication never wraps on-demand map panels {on_demand}"
        )
    return panels


def encode_publication(
    message_name: str,
    logical: Mapping[str, Any],
    *,
    panel_validators: PanelValidators | None = None,
) -> tuple[PreparedFrame, ...]:
    """Encode one eager logical publication into its exact transport frames.

    The logical document is validated (global structure, exact envelope schema,
    registered panel schemas and their local byte limits, then the finite
    aggregate ceiling) before any frame exists. It stays intact when the
    applicable envelope allowance accepts it; otherwise the single canonical
    byte sequence is split into bounded parts. ``ui_snapshot`` and ``ui_update``
    are the only accepted commands.
    """
    kind = _PUBLICATION_MESSAGES.get(message_name)
    if kind is None:
        raise PublicationCodecError(
            f"{message_name!r} is not a general publication command"
        )
    if not isinstance(logical, Mapping):
        raise PublicationCodecError("a logical publication must be a JSON object")
    check_json_safety(logical)
    if kind == "snapshot":
        validate_ui_snapshot(logical)
    else:
        validate_ui_update(logical)
    panels = _logical_panels(logical)
    validate_publication_panels(panels, panel_validators)
    _check_dialogue_panel_cap(logical)

    canonical = canonical_bytes(logical)
    if len(canonical) > PUBLICATION_MAX_BYTES:
        raise PublicationCodecError(
            f"logical publication exceeds {PUBLICATION_MAX_BYTES} canonical bytes"
        )
    try:
        check_envelope_bytes(logical, len(canonical))
    except JSONSafetyError:
        # A schema-valid logical document over its intact allowance fragments;
        # the frame ceiling itself is never raised.
        parts = encode_publication_parts(
            canonical,
            presentation_epoch=logical["presentation_epoch"],
            revision=logical["revision"],
            publication_kind=kind,
            base_revision=logical.get("base_revision"),
        )
        return tuple(PreparedFrame(UI_PUBLICATION_PART, part) for part in parts)
    return (PreparedFrame(message_name, logical, canonical),)


__all__ = [
    "PUBLICATION_ASSEMBLY_TIMEOUT_MS",
    "PUBLICATION_CHUNK_BYTES",
    "PUBLICATION_CHUNK_CHARS",
    "PUBLICATION_KINDS",
    "PUBLICATION_MAX_ASSEMBLIES",
    "PUBLICATION_MAX_BYTES",
    "PUBLICATION_MAX_CHUNKS",
    "PUBLICATION_MAX_PARTS",
    "PUBLICATION_PART_BYTES",
    "PublicationCodecError",
    "PanelValidators",
    "TRANSFER_ID_LENGTH",
    "canonical_bytes",
    "encode_publication",
    "encode_publication_parts",
    "new_transfer_id",
    "validate_publication_panels",
    "validate_publication_part",
]
