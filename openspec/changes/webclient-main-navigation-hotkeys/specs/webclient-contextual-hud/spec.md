# Spec Delta

## MODIFIED Requirements

### Requirement: The reference surfaces have no permanently visible home and are reached from the top navigation or the dock
The party window (whose tabs hold members, the bag and equipment, status, skills and lineage), the shop window, the quest board and the lore reference SHALL each render in exactly one place — its window or drawer — and SHALL NOT be present in the DOM while closed. The stage SHALL carry no permanently visible column of reference panels.

#### Scenario: Every reference surface is reachable in two actions
- **WHEN** a player seeks a reference surface from the top navigation bar or the dock's root frame
- **THEN** each drawer is opened either by the dock frame that owns its surface, or by a single labelled control inside a drawer that already presents the same read model, or by a surface this capability names elsewhere as an opener for it, and no reference surface requires more than two actions to reach

#### Scenario: Opening a drawer disturbs no dock contract
- **WHEN** a drawer opens
- **THEN** no dock root item, menu frame, menu key, or the meaning of Escape changes

#### Scenario: No reference surface is mounted while the drawers are closed
- **WHEN** the stage renders in exploration mode with every drawer closed
- **THEN** no party window, shop window, quest board or lore reference element exists in the DOM or in the tab order, and no reference column is rendered

#### Scenario: Every reference surface is reachable from the dock
- **WHEN** the player starts at the dock's root frame or the top navigation bar
- **THEN** each reference surface and party window tab is reached in at most two actions, and the narrative caption stays in the bottom band's message region

#### Scenario: An emptied right-hand stack costs nothing
- **WHEN** the stage renders at 1451x790 and 2560x1440 with every drawer closed
- **THEN** the top-right `map` anchor renders no reference panel, contributes no visible box and no tab stop, and no interactive stage anchor's rendered box intersects another's
