# Delta spec: webclient-oob-protocol (webclient-align-10-dialogue-panel)

## MODIFIED Requirements

### Requirement: Full snapshots and updates have registered replacement semantics
A version-1 `ui_snapshot` SHALL contain exactly `protocol_version`, `presentation_epoch`, `revision`, `mode`, `panels`, `layout_version`, and `server_time`. A `ui_update` SHALL contain the same exact top-level field set, with a nonempty registered subset in `panels`. `protocol_version` SHALL be integer 1; epoch SHALL be exactly 22 URL-safe ASCII characters generated from 128 random bits; snapshot/update revisions SHALL be positive safe integers excluding booleans; mode SHALL be `creation`, `exploration`, `combat`, or `dialogue`; layout version SHALL be in `1..65,535`; panel names SHALL be 1..64 lowercase identifier characters; and panel count SHALL not exceed 32. `server_time` SHALL contain exactly `year`, `season_index`, `season_label`, `day_in_season`, `hour`, `minute`, and `second`, bounded respectively to the safe non-negative integer range, `0..3`, 1..32 Unicode code points, `1..90`, `0..23`, `0..59`, and `0..59`. Every included update panel SHALL completely replace the prior value; the protocol SHALL NOT use JSON Patch or merge unknown nested state. Because an update's `mode` is recomputed at publication time, the committed mode SHALL NOT diverge from the committed dialogue panel: a `ui_update` whose recomputed mode is `dialogue` SHALL name the `dialogue` panel in its subset, so the client can never hold a dialogue-mode presentation while its stored dialogue panel is stale.

#### Scenario: Full synchronization replaces the complete store
- **WHEN** the browser accepts a valid `ui_snapshot`
- **THEN** it atomically replaces every prior panel and the prior mode, layout version, and server-time display with the snapshot values

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
