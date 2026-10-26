# webclient-publication-delivery Specification

## Purpose
Deliver complete eager snapshots and deltas within finite logical and per-frame bounds, including publications whose individual panel cannot fit one envelope.

## Requirements

### Requirement: General publication parts use exact bounded wire fields
General parts SHALL carry protocol_version, presentation_epoch, revision, publication_kind, transfer_id, part_index, part_count, total_bytes and chunks. Delta parts SHALL additionally require base_revision; snapshot parts SHALL forbid it. Unknown fields and inconsistent headers SHALL reject.

#### Scenario: Part header and logical document agree
- **WHEN** a complete transfer decodes to a logical publication
- **THEN** kind epoch target and delta base must match its headers before adoption

#### Scenario: No giant chunk string
- **WHEN** a part contains more than16 strings or any base64 string exceeds2048 ASCII characters
- **THEN** the generic frame validator rejects it even when total bytes are below65536

### Requirement: General delivery has finite shared resource limits
General publication UTF-8 JSON SHALL be <=16777216 bytes. Parts SHALL contain <=24576 raw bytes encoded in <=16 canonical base64 strings of <=1536 raw bytes each, with <=683 parts. The generic frame ceiling SHALL remain65536 bytes and existing schema/panel limits SHALL remain enforced.

#### Scenario: One panel cannot fit an envelope
- **WHEN** one schema-valid panel fits its local ceiling while its logical envelope exceeds the applicable intact allowance
- **THEN** the sender fragments the encoded logical bytes without splitting solely between panels

#### Scenario: Exact maximum and overflow
- **WHEN** logical bytes are16777216 or16777217
- **THEN** the maximum derives683 correctly sized parts and overflow fails before any frame send

#### Scenario: CJK crosses byte boundary
- **WHEN** a multibyte character crosses raw part boundaries
- **THEN** canonical bytes survive and decode to the exact original value after complete assembly

#### Scenario: Panel invalidity is not legalized
- **WHEN** a logical document fits16MiB but violates a panel string/list/schema/byte limit
- **THEN** preflight rejects it without fragmentation or revision consumption

### Requirement: All delivery frames are validated before publication
A sender SHALL validate the logical publication and every prepared frame before the first send, reuse its prepared representation where transport allows, and send an ordered complete batch before the associated result. General parts SHALL remain separate from specialized map-body routing.

#### Scenario: Later invalid frame prevents earlier send
- **WHEN** planning discovers an invalid later part in a combined eager/map batch
- **THEN** no frame from that batch is sent

#### Scenario: Scoped map allowances remain distinct
- **WHEN** an intact world_map or area_map body part uses its existing specialized protocol
- **THEN** general multipart does not wrap it or change its existing bounds or lifecycle

#### Scenario: Fresh oversized snapshot establishes baseline
- **WHEN** a complete eager snapshot exceeds the intact generic allowance but fits logical/panel bounds
- **THEN** the coordinator sends its prepared parts and installs the baseline only after all sends succeed
