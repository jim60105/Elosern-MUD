## ADDED Requirements

### Requirement: Reading settings preview preferences without touching play
The settings surface SHALL offer a local reading sample: one fixed line of prose set in the message window's page face, page size and leading at the chosen prose scale, above both groups of settings controls, with a replay control. The sample SHALL type at the rate the message window would use for the chosen text speed and the effective motion level, so it SHALL show at once for `瞬間` and whenever the effective motion level is not `完整`, and it SHALL name that rule in a visible caption. It SHALL play once when the settings surface opens, SHALL restart once when the prose scale, the text speed or the motion level changes, SHALL play again only through replay, and SHALL NOT loop. Its whole line SHALL stay laid out while it types, so the sample never re-wraps or changes height mid-line, and assistive technology SHALL read the complete line rather than a partly typed one. Updating or replaying the sample SHALL NOT append narrative, send an action, change the live message window's page or reading position, consume or arm its auto-advance, or change gameplay. Closing the settings surface SHALL stop all preview work.

#### Scenario: Preference changes are visible locally
- **WHEN** the player changes the prose scale or the text speed
- **THEN** the sample restarts once at that preference while the live response position and narrative history remain unchanged and no action is sent

#### Scenario: Reduced motion shows the sample at once
- **WHEN** the effective motion level is `減少` or `關閉` and the player replays the sample at any text speed
- **THEN** the whole line is shown at once and the caption names the motion level as the reason

#### Scenario: Preview closes mid-type
- **WHEN** the player closes settings while the sample types
- **THEN** preview timers stop and no later preview content reaches the live reader

### Requirement: Settings switches preserve native accessible operation
Settings toggle controls SHALL be native checkboxes exposed as switches, named by their visible label and described by their help line, with a checked state marked by both the knob's position and the track's fill. Their labels and help SHALL render through the shared type tokens at or above the 12px chrome floor, they SHALL remain keyboard operable with Space, and they SHALL use the existing preference persistence path. The settings cards SHALL share equal column tracks while each takes its own content height.

#### Scenario: Keyboard toggles a preference
- **WHEN** the focused switch receives Space
- **THEN** exactly one preference change occurs and its new checked state is announced
