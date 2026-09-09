# webclient-contextual-hud delta

## RENAMED Requirements

- FROM: `### Requirement: The reference surfaces have no permanently visible home and are reached from the dock`
- TO: `### Requirement: The reference surfaces have no permanently visible home and are reached from the top navigation or the dock`

## MODIFIED Requirements

### Requirement: The reference surfaces have no permanently visible home and are reached from the top navigation or the dock
The skill book, the bag and equipment, the shop, the quest board, the lore reference and the character
status SHALL each render in exactly one place — its drawer — and SHALL NOT be present in the DOM while
that drawer is closed. The stage SHALL carry no permanently visible column of reference panels.

Each drawer SHALL be opened either by the dock frame that owns its surface, or by a single labelled
control inside a drawer that already presents the same read model, or by a surface this capability
names elsewhere as an opener for it. No reference surface SHALL require more than two actions from
the top navigation bar or the dock's root frame to reach. Opening a drawer SHALL NOT change any dock root item, any menu frame, any
menu key, or the meaning of Escape.

#### Scenario: No reference surface is mounted while the drawers are closed
- **WHEN** the stage renders in exploration mode with every drawer closed
- **THEN** no skill book, bag, shop, quest board, lore reference or character-status element exists in the DOM or in the tab order, and no reference column is rendered

#### Scenario: Every reference surface is reachable from the dock
- **WHEN** the player starts at the dock's root frame or the top navigation bar
- **THEN** each of the six reference surfaces is reached in at most two actions, and the narrative caption remains the visual centre of the stage

#### Scenario: An emptied right-hand stack costs nothing
- **WHEN** the stage renders at 1440x900 and 1280x720 with every drawer closed
- **THEN** the right-hand HUD anchor renders no reference panel, contributes no visible box and no tab stop, and no stage anchor's rendered box intersects another's

