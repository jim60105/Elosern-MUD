## MODIFIED Requirements

### Requirement: Browser acceptance covers foundation recovery and layout behavior
Playwright SHALL verify required surface visibility at 1451x790 and 2560x1440; that no stage anchor's rendered box intersects another stage anchor's rendered box at either acceptance viewport; and that mode-gated surfaces are hidden with `display:none` (never dimmed) in the modes that hide them — so they leave the accessibility tree and the tab order — and are present again in the modes that show them.

#### Scenario: Supported viewports pass the shell journey
- **WHEN** the acceptance journey runs at each supported desktop viewport
- **THEN** every required surface is visible, no stage anchor overlaps another, two consecutive commands are sent from the command line without any pointer interaction by opening it with `/` before each, each send collapses the line and restores action-dock focus, and Escape from an opened line restores action-dock focus

#### Scenario: The overlay journey opens, replaces, and returns focus
- **WHEN** the acceptance journey activates the map trigger, then the settings trigger, then presses Escape
- **THEN** exactly one overlay is present at each step, opening the second closes the first, and Escape closes the open overlay and returns focus to the trigger that opened it

#### Scenario: Mode gating hides surfaces with display:none
- **WHEN** the committed mode changes to one that hides a surface
- **THEN** that surface is hidden with `display:none`, absent from the accessibility tree and the tab order, and it becomes present and focusable again when the mode changes back

#### Scenario: Reconnect behavior is exercised end to end
- **WHEN** the harness interrupts the active WebSocket and reconnects it
- **THEN** stale controls remain locked, the browser adopts the new epoch's lower-revision snapshot, and an injected delayed old-epoch message changes no state

#### Scenario: Incompatible protocol preserves text input
- **WHEN** the harness injects a snapshot with an unsupported protocol version
- **THEN** graphical actions disable while an ordinary text command can still be sent and rendered

#### Scenario: Narrative shows prose, not markup source
- **WHEN** the seeded actor looks at the room in the real client
- **THEN** the narrative contains the room's styled prose, contains no literal element or entity source characters, and the colored segments carry their palette classes

#### Scenario: The complete log is reachable from the bounded caption
- **WHEN** the narrative holds more lines than the message window's page displays
- **THEN** the acceptance journey opens the complete retained log in one action from the window's `日誌` control and closes it on Escape with focus restored to that control

#### Scenario: The minimap stays inside its island
- **WHEN** the shell renders a seeded grid room's minimap at each acceptance viewport
- **THEN** every node marker is inside the map canvas, no two node markers overlap, and the island renders no legend

#### Scenario: The dialogue stage journey completes by keyboard
- **WHEN** the acceptance journey at 1451x790 opens a scripted host's conversation with 交談 from the host's verb card (opened from the presence rail), reads every page with Enter, presses `1`, reads the reply, activates `⌨ 自由對話` and sends a line, activates `↦ 移動…` and presses Escape, activates `✕ 結束對話`, and then aims and moves through the exit compass
- **THEN** the browser submits exactly `explore.talk_open`, `explore.talk_scripted`, `explore.talk_freeform`, `explore.dialogue_leave`, and `explore.move` in that order, the command region is hidden and both stage actors are rendered from the conversation's first commit to its end, the choice list is absent whenever a page is typing or unread, `document.activeElement` is never the body during the conversation, and focus is on the exit compass once it ends

#### Scenario: Command-line expand, send, and cancel are exercised
- **WHEN** the acceptance journey drives the command line
- **THEN** it verifies the line collapsed on load with its ⌨ toggle visible, `/` expanding it and moving focus into the input field without inserting a literal slash, an ordinary send clearing the field, collapsing the line, and restoring action-dock focus, a rejected send keeping the text and the open line, and Escape sending nothing, collapsing the line, and restoring action-dock focus

#### Scenario: Pointer activation parity on the action dock is verified
- **WHEN** the acceptance journey exercises the action dock
- **THEN** pointer activation parity with the keyboard path is verified

#### Scenario: Layout migration and degradation are verified
- **WHEN** the acceptance journey replays persisted client state
- **THEN** known layout migration, unknown layout reset, and presenter degradation are verified

#### Scenario: Protocol mismatch keeps text input working
- **WHEN** the acceptance journey faces a protocol mismatch
- **THEN** text input is preserved
