## MODIFIED Requirements

### Requirement: Browser acceptance covers foundation recovery and layout behavior
Playwright SHALL verify required shell visibility at 1440x900 and 1280x720; command-line focus, send, and cancel behavior — the input field present and typeable with no opening action, `/` moving focus into it without inserting a literal slash, focus retention after an ordinary send, and Escape sending nothing and restoring action-dock focus; the full-overlay contract — a labelled trigger opening exactly one overlay, a second trigger closing the first, and Escape closing the open overlay and restoring focus to its trigger; pointer activation parity on the action dock; narrative rendering of converted server markup; minimap containment within its pane; transport interruption and control locking; lower-revision adoption in a new epoch; rejection of delayed prior-epoch messages; known layout migration; unknown layout reset; presenter degradation; and protocol mismatch with preserved text input.

#### Scenario: Supported viewports pass the shell journey
- **WHEN** the acceptance journey runs at each supported desktop viewport
- **THEN** every required surface is visible, the command input field is present and typeable without any opening action, two consecutive commands are sent from it without any pointer interaction, and Escape restores action-dock focus

#### Scenario: The overlay journey opens, replaces, and returns focus
- **WHEN** the acceptance journey activates the map trigger, then the settings trigger, then presses Escape
- **THEN** exactly one overlay is present at each step, opening the second closes the first, and Escape closes the open overlay and returns focus to the trigger that opened it

#### Scenario: Reconnect behavior is exercised end to end
- **WHEN** the harness interrupts the active WebSocket and reconnects it
- **THEN** stale controls remain locked, the browser adopts the new epoch's lower-revision snapshot, and an injected delayed old-epoch message changes no state

#### Scenario: Incompatible protocol preserves text input
- **WHEN** the harness injects a snapshot with an unsupported protocol version
- **THEN** graphical actions disable while an ordinary text command can still be sent and rendered

#### Scenario: Narrative shows prose, not markup source
- **WHEN** the seeded actor looks at the room in the real client
- **THEN** the narrative contains the room's styled prose, contains no literal element or entity source characters, and the colored segments carry their palette classes

#### Scenario: The minimap stays inside its pane
- **WHEN** the shell renders a seeded grid room's minimap at each supported viewport
- **THEN** every node marker is inside the map canvas, no two node markers overlap, and the legend and detail line remain visible
