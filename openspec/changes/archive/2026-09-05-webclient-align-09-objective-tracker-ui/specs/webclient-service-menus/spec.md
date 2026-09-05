# Delta spec: webclient-service-menus (webclient-align-09-objective-tracker-ui)

Chain note: depends on webclient-align-06-quest-tracking-contract (committed
`tracked` row field + `guild.quest_track` action). This is the client browser half of
the original change 06.

## ADDED Requirements

### Requirement: The quest browser exposes the tracking toggle
The service quest browser SHALL render, on each quest-log row, a tracking control that dispatches
`guild.quest_track` for that row's `quest_id`: labelled and enabled as tracking for an
`in_progress` row whose `tracked` is false, as untracking for a row whose `tracked` is true, and
disabled with a stable reason otherwise. Keyboard and pointer activation SHALL submit the same
action identifier and payload through the same dispatch entry and gates. The control SHALL render
only from the committed row's `tracked` field, and the row's presented tracking state SHALL
change only when a commit carrying the new field lands.

#### Scenario: Tracking from the browser dispatches once
- **WHEN** the player activates a tracked-false active quest row's tracking control
- **THEN** exactly one `guild.quest_track` request with `{quest_id, tracked: true}` is submitted and the row flips only on the commit

#### Scenario: Completed rows offer no tracking
- **WHEN** a completed quest row renders
- **THEN** its tracking control is disabled with a stable reason and dispatches nothing
