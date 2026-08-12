# Delta Specs: Stale Skip-Safety Assertions and Art-Portrait Focus Race

## ADDED Requirements

### Requirement: Art-panel portrait keyboard journeys establish dock focus before key presses

A Playwright acceptance journey that asserts the client-local portrait focus
switching SHALL focus the action dock
(`document.getElementById('action-dock').focus()`) and wait for the combat
dock's mounted router frame (the first combat row `#combat-row-0`) before the
first key press, and SHALL wait for the basic-attack target menu frame
(`#combat-row-0` carrying a `target-` data-item-key) before asserting that the
portrait switched to the focused target. This guarantees the key event reaches
the KeyboardRouter — never the command-drawer field or an unfocused editable
target — and turns a swallowed key press into a precise diagnostic.

#### Scenario: Art-panel combat journey presses Enter with the dock focused

- **WHEN** an art-panel acceptance test engages combat, presses Enter to open
  the basic-attack target menu, and moves focus to the enemy target
- **THEN** the action dock was explicitly focused and the combat dock's first
  row was mounted before the Enter press, and the portrait switches to the
  focused enemy target's name without any focus packet

#### Scenario: Target menu mount is awaited before asserting the portrait

- **WHEN** the journey asserts that the portrait switched to the focused
  target
- **THEN** it first waits for the target menu frame (`#combat-row-0` carrying a
  `target-` data-item-key) and then for the focused row to carry the enemy
  target's key, so a swallowed key press fails with a precise diagnostic
  instead of a bare timeout
