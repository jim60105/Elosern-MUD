# Bounded general publication sender

## Context

B provides one content-aware coordinator; D defines logical snapshots/deltas. `_publish_with_maps` currently has map-only fragmentation, while ordinary full_snapshot fails check_envelope on aggregate size. Existing generic limits are 65536 canonical UTF-8 bytes, depth 12, 64 object fields, 320 list entries and 2048 Unicode code points per string. Available v3 dialogue has a finite scoped envelope/panel allowance; world_map has a distinct existing allowance.

## Goals / Non-Goals

Deliver the complete server encoder, mirrored constants and sender integration in one day. General publication transport applies to eager snapshots/deltas, including one large schema-valid panel. No panel-bound relaxation, compression, content digest or generic frame-cap increase. Specialized map-body protocol remains distinct.

## Decisions

### Exact general part wire

New server command `ui_publication_part`, one exact JSON object in first positional argument, no kwargs. REQUIRED fields are `{protocol_version:1, presentation_epoch:E, revision:R, publication_kind:K, transfer_id:X, part_index:I, part_count:C, total_bytes:N, chunks:S}`. K is exactly `snapshot` or `delta`. `base_revision:B` is required ONLY for delta and forbidden for snapshot. No mode/panels/time fields occur in the part header. X is exactly 32 lowercase hex characters generated from 128 random bits per logical publication. E/R/B use D's formats. I is zero-based. Every part has identical E/R/K/X/C/N/B. Reassembled logical fields must match E/R/B and K's logical message schema; this prevents header/body disagreement. No checksum field is introduced.

Authoritative constants, named identically in Python and browser `protocol/constants.js`, are `PUBLICATION_MAX_BYTES=16777216`, `PUBLICATION_PART_BYTES=24576`, `PUBLICATION_CHUNK_BYTES=1536`, `PUBLICATION_MAX_CHUNKS=16`, `PUBLICATION_MAX_PARTS=683`, `PUBLICATION_ASSEMBLY_TIMEOUT_MS=30000`, `PUBLICATION_MAX_ASSEMBLIES=1`.

Encode logical publication once using existing `json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")`, with nonfinite values rejected before encoding. N is that byte count, 1<=N<=16777216. C=ceil(N/24576), C<=683. Part i has raw size min(24576,N-i*24576). S is ceil(raw_size/1536) standard padded RFC4648 base64 strings, <=16; each nonfinal string decodes to exactly1536 bytes and is 2048 ASCII characters, final string decodes to the exact remainder. Reject whitespace, noncanonical padding and alternate encodings. Each part is checked by the unchanged generic frame safety/65536-byte ceiling. UTF-8 may split inside a code point; concatenate raw bytes and decode once with strict UTF-8 after all parts.

### Validation boundary

Add `presentation/publication_parts.py::{encode_publication,validate_publication_part}`. `encode_publication(message_name,logical) -> tuple[PreparedFrame,...]`; PreparedFrame has command, envelope and reusable canonical bytes where supported. It accepts ui_snapshot/ui_update eager logical documents only. Call logical schema validation and JSON safety measured from logical root, enforcing panel schemas and panel-local byte limits, then the finite aggregate 16MiB ceiling. Logical validation does NOT call generic `check_envelope` byte cap on the reassembled document. Split frame-envelope safety from logical schema checks explicitly; no catch-and-ignore of a panel schema failure.

If the existing intact-envelope check passes, emit the original intact command under its current applicable allowance. Otherwise fragment only a schema-valid logical document within the logical limit. Preserve the available-dialogue 98304 whole-envelope /24576 panel /65536 dialogue-removed allowance for INTACT envelopes; it must not become a logical aggregate cap after reassembly. Retain 24576 dialogue panel limit after assembly. Other explicit panel-local limits also remain. General part envelopes are always generic-limited, never use dialogue/world-map allowances.

`coordinator.py::publish/full_snapshot/panel_update` use this encoder for all eager logical publications and prevalidate the complete frame tuple before consuming a revision or calling session.msg. `_publish_with_maps` continues its specialized intact/world-map/area-map-body plan and uses the general codec for any eager companion logical publication. Never wrap specialized map-body parts inside general parts, never force-load on-demand maps. The whole combined action batch is planned before sending its first frame.

Oversize above the 16MiB ceiling, invalid panel or invalid part shape fails preflight with safe presentation failure. No truncation, giant string chunks, raising generic limits or sending a partial plan. Baseline changes only after all logical presentation frames return successfully under B. Part-send failure uses B's invalid-baseline rule. No new ACK.

### Exact targets and acceptance

Own protocol.py message registration and validator dispatch, publication_parts.py (new), publication.py PreparedFrame (B owns receipt), coordinator.py codec integration, browser constants.js declarations, `web/static/webclient/js/elosern/protocol.js` exports if required, and `presentation/tests/test_publication_parts.py` (new). A owns browser decoding, not this sender. This unreleased wire sequence is deployed together after A/R/F; no legacy-client shim.

Test N boundaries 24576/24577, 65536 envelope threshold with metadata accounted for, 16777216/16777217, exact683 parts, one oversized valid panel, CJK split and malformed nested schema despite valid bytes. Tests use synthetic registered data and exercise actual encoder/coordinator sends. For the large ceiling arithmetic test the encoder's byte splitter can receive synthetic prevalidated bytes directly at its pure helper; an end-to-end test must still use valid production panel schemas. Update protocol delivery docs and the whole modified main OOB message requirement through delta spec.

## Risks / Trade-offs

The logical ceiling is resource policy, with no workload measurement claim. Canonical bytes are owned once per publication; reuse for sizing/fragmentation without serializing for equality. Prepared envelopes may need the Evennia serializer again; do not invent raw socket I/O to avoid that unavoidable transport serialization.
