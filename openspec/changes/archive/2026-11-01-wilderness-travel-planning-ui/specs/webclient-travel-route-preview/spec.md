# Spec Delta

## Purpose

Add destination input, debounced current-only route queries and server-authored route/gauge previews. This capability defines observable browser travel behavior and its data boundaries.

## ADDED Requirements

### Requirement: Travel route queries are debounced and current-only
Destination preview SHALL debounce hover requests, supersede older intent through the single-flight dispatch gate and apply only results matching the current committed origin, map and preferences.

#### Scenario: Debounce and supersession
- **WHEN** hover changes before150ms and again during an in-flight query, then old/new results arrive
- **THEN** only the latest eligible request sends after the gate frees and only its matching result controls preview or error

#### Scenario: Invalidation and errors
- **WHEN** movement, time/member facts, preferences, window or epoch change, or each stable plan error arrives
- **THEN** stale previews/errors do not adopt, current errors clear preview and a surviving lock queries once from the new valid origin

### Requirement: Travel destinations and previews remain disclosed and accessible
Travel destination input SHALL lock only disclosed current-window cells, preserve neighbour-step priority and present supplied route stages and stop indices with equivalent keyboard access.

#### Scenario: Pointer and keyboard parity
- **WHEN** pointer or Shift-arrow cursor selects known, unknown, neighbour and party cells, followed by Enter/Escape
- **THEN** only eligible destinations lock, ordinary aim still steps and unknown/party inputs never manufacture a route

#### Scenario: Server-authored preview
- **WHEN** a synthetic plan includes every stage, nightfall, a voluntary stop and later steps
- **THEN** glyph/leg state follows supplied indices and durations, route fit preserves controls and no client route or eligibility is derived

#### Scenario: Terminal sleep has a defined display
- **WHEN** a valid plan includes an admitted forced_sleep terminal step
- **THEN** data retains that stage and the route/leg show a severe-style tick with a sleep cue and accessible label, including its count and duration

