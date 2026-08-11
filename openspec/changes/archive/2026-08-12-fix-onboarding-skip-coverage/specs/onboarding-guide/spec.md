## ADDED Requirements

### Requirement: Deviation detection applies to every room type

The onboarding observer SHALL run on every successful player arrival into any room type (plain `Room`, `GridRoom`, `TerrainRoom`, `InstanceRoom`), so entering any room outside the guided corridor marks the guide skipped.

#### Scenario: Leaving the corridor into a plain room skips the guide

- **WHEN** a guided player enters a plain `Room` (e.g. Limbo) outside the corridor
- **THEN** `guide_progress.state` becomes `skipped` and no further guide prompts or arrival replays occur

#### Scenario: Leaving the corridor into an instance room skips the guide

- **WHEN** a guided player enters an `InstanceRoom` whose origin is outside the corridor
- **THEN** `guide_progress.state` becomes `skipped`

#### Scenario: Corridor arrivals and onboarded players are unaffected

- **WHEN** a guided player arrives in a `GridRoom` inside the corridor, or any onboarded player moves
- **THEN** observation is a no-op and existing guide progression is unchanged

#### Scenario: Wilderness traversal triggers the same observation

- **WHEN** a guided player enters wilderness terrain or takes an intra-wilderness step
- **THEN** the guide is marked skipped through the shared movement boundary
