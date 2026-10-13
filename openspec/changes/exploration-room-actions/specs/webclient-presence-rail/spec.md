## REMOVED Requirements

### Requirement: The exploration dock roots at the compass and the presence rail and keeps the footer overview
**Reason**: The footer, the wait frame, and the suggestions frame are retired, and the exploration root is restated in `webclient-room-actions` ("The exploration screen roots at the compass, the rail, and room actions").
**Migration**: The footer scenarios moved to `webclient-room-actions` (the place-card 查看房間 and 等待 buttons and the 建議 pill); the child-frame scenarios became the wait card and suggestions card scenarios there; the remaining scenarios are covered by its empty-root and mode-change scenarios.

## RENAMED Requirements

- FROM: `### Requirement: Rail digits are claimed and never fall through to the footer`
- TO: `### Requirement: Rail digits are claimed by the rail and never fall through`

## MODIFIED Requirements

### Requirement: The presence rail shows people and objects on the stage floor
In exploration mode the stage SHALL render `PresenceRail` right-aligned on the stage floor, inset left of the right-hand island column: interact targets as gold medallions, other present entities as dashed muted medallions, then a separator and objects as steel lozenges, in `ExplorationMenu.presenceEntries` order, each with a name plate. It SHALL yield to the foe line-up in combat, hide during dialogue and under a centred card, and render nothing when empty.

#### Scenario: Entries follow the overview order
- **WHEN** the room has two interact targets, one bystander, and two objects
- **THEN** the rail shows two gold medallions, one dashed muted medallion, a separator, and two lozenges, each with its name plate, in that order

#### Scenario: A medallion shows the face crop or the initial
- **WHEN** an interact target's `portrait_ref` resolves in the art catalog
- **THEN** its medallion shows the face crop through the existing face-rect data

#### Scenario: A medallion without a portrait shows the initial
- **WHEN** an interact target has no `portrait_ref` or its catalog entry is unavailable
- **THEN** its medallion shows the first character of the target's name

#### Scenario: The rail is hidden outside exploration and under a card
- **WHEN** the mode is combat or dialogue, or a centred card is open
- **THEN** the rail is not visible and takes no focus

#### Scenario: An empty room renders no rail
- **WHEN** the room has no people and no objects
- **THEN** the rail renders no element and no placeholder

### Requirement: Rail digits are claimed by the rail and never fall through
While no card is open, digits 1–9 SHALL be claimed by the rail: a digit beyond the number of visible entries SHALL do nothing, and opening a card SHALL stop any compass walk.

#### Scenario: A digit beyond the rail count is a no-op
- **WHEN** the rail has two entries and the player presses `3`
- **THEN** no `ui_action` is emitted and no room action or dock row is activated

#### Scenario: Opening a card stops a walk
- **WHEN** a compass walk is running and the player presses a rail digit that opens a verb card
- **THEN** the walk stops
