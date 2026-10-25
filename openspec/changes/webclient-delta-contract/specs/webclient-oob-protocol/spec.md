# Spec Delta

## MODIFIED Requirements

### Requirement: Full snapshots and updates have registered replacement semantics
A version-1 ui_snapshot SHALL retain its seven exact metadata/panel fields. A ui_update SHALL add exact base_revision and removed_panels fields, permitting empty panels. Included panels SHALL replace complete values; removed eager names SHALL be explicit and disjoint. Snapshots SHALL replace all eager membership while retaining same-epoch on-demand maps. No JSON Patch is used.

#### Scenario: Full synchronization replaces the complete store
- **WHEN** the browser accepts a valid `ui_snapshot`
- **THEN** it atomically replaces every eager panel and the prior mode, layout version and server-time display, preserves separate on-demand maps in the same epoch, and clears all maps on a new epoch

#### Scenario: A panel update is a full replacement
- **WHEN** the browser accepts a newer `ui_update` containing the `status` panel
- **THEN** the new status object completely replaces the previous status object without retaining omitted nested fields

#### Scenario: Unknown panel names are rejected
- **WHEN** a snapshot or update contains a panel name absent from the registered panel allowlist
- **THEN** the client rejects that presentation message and does not render or merge the unknown panel

#### Scenario: Update metadata is complete
- **WHEN** the server emits a valid `ui_update`
- **THEN** it includes the active mode, current server time, and layout version together with its epoch, new revision, and a possibly empty panel subset plus exact base_revision and removed_panels

#### Scenario: A dialogue-mode update compares a fresh dialogue candidate
- **WHEN** an affected-panel update is published while the viewer's recomputed mode resolves to `dialogue` and its named subset omits the `dialogue` panel
- **THEN** the server freshly renders dialogue as a candidate, includes it when changed, and the client validates mode/dialogue consistency against the whole staged committed state even when equal dialogue is omitted

#### Scenario: Top-level field value bounds are exact
- **WHEN** a snapshot or update envelope is validated
- **THEN** `protocol_version` SHALL be integer 1; `presentation_epoch` SHALL be exactly 22 URL-safe ASCII characters generated from 128 random bits; revisions SHALL be positive safe integers excluding booleans; `mode` — recomputed at publication time so the committed mode never diverges from the committed dialogue panel — SHALL be `creation`, `exploration`, `combat`, or `dialogue`; `layout_version` SHALL be in `1..65,535`; panel names SHALL be 1..64 lowercase identifier characters; and panel count SHALL not exceed 32

#### Scenario: Server time fields are exact and bounded
- **WHEN** a snapshot or update carries `server_time`
- **THEN** it SHALL contain exactly `year`, `season_index`, `season_label`, `day_in_season`, `hour`, `minute`, and `second`, bounded respectively to the safe non-negative integer range, `0..3`, 1..32 Unicode code points, `1..90`, `0..23`, `0..59`, and `0..59`

## ADDED Requirements

### Requirement: Deltas require the exact committed baseline
For the live transport and epoch, a delta SHALL require base_revision equal to the committed revision and a newer target. All replacements, removals and metadata SHALL validate before one atomic commit and notification. Deltas SHALL NOT establish initial state.

#### Scenario: Missing predecessor preserves committed state
- **WHEN** the browser at revision7 receives a valid delta with base6 and target8
- **THEN** it rejects base_mismatch, preserves revision7 panels/mode/time and locks mutations for complete recovery

#### Scenario: Initial delta cannot establish epoch
- **WHEN** an awaiting browser receives a delta with no complete snapshot baseline
- **THEN** it adopts nothing and cannot establish an epoch

#### Scenario: Newer target can skip unused integers
- **WHEN** the committed revision is7 and a valid delta has base7 and target10
- **THEN** the browser commits10 once; admission does not invent a predecessor9

#### Scenario: Staged failure rolls back every field
- **WHEN** one replacement or mode/dialogue relation fails validation alongside valid replacements and metadata
- **THEN** no staged panel, removal, mode, time or revision becomes observable

#### Scenario: On-demand map revision follows exact base
- **WHEN** a specialized map transfer repeats base7 and target8 across its existing map-body parts
- **THEN** no partial map changes revision7 and only complete validated map adoption commits8

### Requirement: Removal unavailable and metadata-only updates remain distinct
A delta SHALL allow empty replacements, explicit duplicate-free registered eager removals and complete metadata. Removed names SHALL be disjoint from replacements and exclude on-demand maps. Unavailable values SHALL replace panels rather than delete them.

#### Scenario: Three distinct eager operations
- **WHEN** a delta replaces status with unavailable, removes a registered eager panel and omits another
- **THEN** status remains present as unavailable, the removed key is absent and the omitted panel is unchanged

#### Scenario: Invalid removals reject atomically
- **WHEN** removals contain an unknown name, map name, duplicate or replacement overlap
- **THEN** both validators reject the entire delta

#### Scenario: Metadata-only adoption
- **WHEN** a delta has empty panels/removals with changed server time or mode consistent with staged panels
- **THEN** the browser atomically commits metadata and revision without deleting existing panels
