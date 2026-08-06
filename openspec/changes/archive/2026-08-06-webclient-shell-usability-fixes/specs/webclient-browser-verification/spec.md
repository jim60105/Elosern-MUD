## MODIFIED Requirements

### Requirement: DOM-independent client behavior has an executable Node test gate
Protocol validation/reduction, keyboard routing, the narrative markup tokenizer, and the local-map render model SHALL be implemented as DOM-independent JavaScript modules and SHALL have deterministic tests runnable with Node 24's built-in test runner. The suite SHALL cover exact schemas, atomic new-epoch adoption, active-epoch revision ordering, old-epoch rejection, panel replacement, focus movement, Escape stack behavior, command-drawer transition, disabled entries, repeated-Enter suppression, focus-by-key resolution and pointer-sourced confirmation, the narrative allowlist grammar with its degradation and bounds under hostile input, and the minimap lattice with its remembered-node split and its rank-compression fallback — all without adding an npm runtime dependency.

#### Scenario: Node suite verifies state and keyboard contracts
- **WHEN** `node --test web/static/webclient/js/tests/*.test.js` runs
- **THEN** all protocol reducer and keyboard-router behavior tests pass without a browser, remote request, package installation, or generated game data

#### Scenario: Node suite verifies markup and map models
- **WHEN** the same Node entry point runs
- **THEN** the narrative tokenizer's allowlist, degradation, and bounds and the local-map lattice model's placement and fallback are verified with no DOM, browser, or network access

### Requirement: Browser acceptance covers foundation recovery and layout behavior
Playwright SHALL verify required shell visibility at 1440x900 and 1280x720; drawer open, send, and cancel behavior including focus retention after an ordinary send and focus restoration on Escape; pointer activation parity on the action dock; narrative rendering of converted server markup; minimap containment within its pane; transport interruption and control locking; lower-revision adoption in a new epoch; rejection of delayed prior-epoch messages; known layout migration; unknown layout reset; presenter degradation; and protocol mismatch with preserved text input.

#### Scenario: Supported viewports pass the shell journey
- **WHEN** the acceptance journey runs at each supported desktop viewport
- **THEN** every required surface is visible, two consecutive commands are sent from the drawer without any pointer interaction, and Escape restores action-dock focus

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
