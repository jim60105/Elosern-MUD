## MODIFIED Requirements

### Requirement: Browser acceptance covers foundation recovery and layout behavior
Playwright SHALL verify required surface visibility at 1440x900 and 1280x720; that no stage anchor's rendered box intersects another stage anchor's rendered box at either supported viewport; that mode-gated surfaces are hidden with `display:none` (never dimmed) in the modes that hide them — so they leave the accessibility tree and the tab order — and are present again in the modes that show them; command-line expand, send, and cancel behavior — the command line collapsed on load with its ⌨ toggle visible, `/` expanding it and moving focus into the input field without inserting a literal slash, an ordinary send clearing the field, collapsing the line, and restoring action-dock focus, a rejected send keeping the text and the open line, and Escape sending nothing, collapsing the line, and restoring action-dock focus; the dialogue stage — at 1920x1080, a keyboard-only journey that moves, opens a conversation from the scene overview, reads the paged line, activates a choice from the choice list over the stage, sends free-form speech through the borrowed command line, opens `↦ 移動…` and returns with Escape, and ends the conversation, with the command region collapsed and both stage actors present throughout the conversation and focus never on the document body; the full-overlay contract — a labelled trigger opening exactly one overlay, a second trigger closing the first, and Escape closing the open overlay and restoring focus to its trigger; pointer activation parity on the action dock; narrative rendering of converted server markup; that the complete narrative log is reachable in one action from the message window's `日誌` control; minimap containment within its HUD island; transport interruption and control locking; lower-revision adoption in a new epoch; rejection of delayed prior-epoch messages; known layout migration; unknown layout reset; presenter degradation; and protocol mismatch with preserved text input.

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
- **WHEN** the shell renders a seeded grid room's minimap at each supported viewport
- **THEN** every node marker is inside the map canvas, no two node markers overlap, and the island renders no legend

#### Scenario: The dialogue stage journey completes by keyboard
- **WHEN** the acceptance journey at 1920x1080 moves with an exit chip, opens a scripted host's conversation with 交談, reads every page with Enter, presses `1`, reads the reply, activates `⌨ 自由對話` and sends a line, activates `↦ 移動…` and presses Escape, and activates `✕ 結束對話`
- **THEN** the browser submits exactly `explore.move`, `explore.talk_open`, `explore.talk_scripted`, `explore.talk_freeform`, and `explore.dialogue_leave` in that order, the command region is hidden and both stage actors are rendered from the conversation's first commit to its end, the choice list is absent whenever a page is typing or unread, and `document.activeElement` is never the body
