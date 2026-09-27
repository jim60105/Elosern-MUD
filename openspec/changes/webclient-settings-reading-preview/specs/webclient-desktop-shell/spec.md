## ADDED Requirements

### Requirement: Reading settings preview preferences without touching play
The settings surface SHALL offer a local sample reflecting the selected prose size and text speed, with a replay control. Updating or replaying it SHALL NOT append narrative, send an action, advance the live reader or change gameplay. Closing settings SHALL stop all preview work.

#### Scenario: Preference changes are visible locally
- **WHEN** the player changes scale or speed
- **THEN** the sample restarts once at that preference while the live response position and narrative history remain unchanged

#### Scenario: Preview closes mid-type
- **WHEN** the player closes settings while the sample types
- **THEN** preview timers stop and no later preview content reaches the live reader

### Requirement: Settings switches preserve native accessible operation
Settings toggle controls SHALL have clear checked state and readable labels/help at the shared type floor, remain keyboard operable with Space, and use the existing preference persistence path.

#### Scenario: Keyboard toggles a preference
- **WHEN** the focused switch receives Space
- **THEN** exactly one preference change occurs and its new checked state is announced
