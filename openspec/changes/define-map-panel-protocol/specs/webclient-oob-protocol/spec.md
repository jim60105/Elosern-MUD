# Spec Delta

## MODIFIED Requirements

### Requirement: Full snapshots and updates have registered replacement semantics
A version-1 `ui_snapshot` SHALL contain exactly `protocol_version`, `presentation_epoch`, `revision`, `mode`, `panels`, `layout_version`, and `server_time`. A `ui_update` SHALL contain the same exact top-level field set, with a nonempty registered subset in `panels`. Every included eager update panel SHALL completely replace its prior value. On-demand area_map/world_map bodies SHALL be omitted from eager snapshots and retained separately within the same epoch; explicit map delivery replaces their complete read models. New transport/puppet epochs SHALL clear both stores. No JSON Patch or unknown nested-state merge is allowed.

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
- **THEN** it includes the active mode, current server time, and layout version together with its epoch, new revision, and nonempty panel subset

#### Scenario: A dialogue-mode update always carries the dialogue panel
- **WHEN** an affected-panel update is published while the viewer's recomputed mode resolves to `dialogue` and its named subset omits the `dialogue` panel
- **THEN** the emitted update still carries a freshly rendered `dialogue` panel alongside the named subset, and the client never commits mode `dialogue` over a stale dialogue panel

#### Scenario: Top-level field value bounds are exact
- **WHEN** a snapshot or update envelope is validated
- **THEN** `protocol_version` SHALL be integer 1; `presentation_epoch` SHALL be exactly 22 URL-safe ASCII characters generated from 128 random bits; revisions SHALL be positive safe integers excluding booleans; `mode` — recomputed at publication time so the committed mode never diverges from the committed dialogue panel — SHALL be `creation`, `exploration`, `combat`, or `dialogue`; `layout_version` SHALL be in `1..65,535`; panel names SHALL be 1..64 lowercase identifier characters; and panel count SHALL not exceed 32

#### Scenario: Server time fields are exact and bounded
- **WHEN** a snapshot or update carries `server_time`
- **THEN** it SHALL contain exactly `year`, `season_index`, `season_label`, `day_in_season`, `hour`, `minute`, and `second`, bounded respectively to the safe non-negative integer range, `0..3`, 1..32 Unicode code points, `1..90`, `0..23`, `0..59`, and `0..59`
