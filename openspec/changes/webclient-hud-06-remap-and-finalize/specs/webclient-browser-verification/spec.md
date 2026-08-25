## MODIFIED Requirements

### Requirement: The implementation-bound public contract is frozen before the shell is swapped
Before any change that relocates a browser-targeted identifier — a shell swap, a layout restructure, or
a surface migration — the implementation-bound client contract SHALL be enumerated and frozen: the
`window.Elosern.*` public façades, the keyboard / plugin key-event path, the DOM identifiers the managed
browser tests target, and the versioned layout-persistence keys. The freeze SHALL be a committed,
reviewed deliverable that is the binding input to the change that performs the relocation, and every
identifier the browser tests currently target SHALL be either preserved unchanged or re-mapped to a
stable `data-testid` hook per that frozen list. The deliverable SHALL be renewed — not superseded by a
second parallel document — whenever a later change relocates identifiers again, so exactly one frozen
list describes the current client.

#### Scenario: A frozen contract list exists before wiring
- **WHEN** the contract audit for a pending shell or layout change is complete
- **THEN** a committed list names each implementation-bound contract (façade, key path, targeted DOM id, persistence key) classified as preserve-via-bridge or delta, and is declared the input to the change that performs the relocation

#### Scenario: Browser-test targets are preserved or re-mapped per the list
- **WHEN** the shell or the layout is restructured
- **THEN** every identifier the managed Playwright suite currently targets is either preserved unchanged or re-mapped to a stable `data-testid`, per the frozen list

#### Scenario: The frozen list is renewed rather than duplicated
- **WHEN** a later change relocates browser-targeted identifiers again
- **THEN** the existing frozen deliverable is updated to describe the current client, and no second parallel contract list is introduced

### Requirement: Browser acceptance covers foundation recovery and layout behavior
Playwright SHALL verify required surface visibility at 1440x900 and 1280x720; that no stage anchor's rendered box intersects another anchor's at either supported viewport; that mode-gated surfaces are absent from the DOM and the tab order in the modes that hide them and present again in the modes that show them; command-line send and cancel behavior including focus retention after an ordinary send and focus restoration on Escape; pointer activation parity on the action dock; narrative rendering of converted server markup; that the complete narrative log is reachable in one action from the bounded caption; minimap containment within its HUD island; transport interruption and control locking; lower-revision adoption in a new epoch; rejection of delayed prior-epoch messages; known layout migration; unknown layout reset; presenter degradation; and protocol mismatch with preserved text input.

#### Scenario: Supported viewports pass the shell journey
- **WHEN** the acceptance journey runs at each supported desktop viewport
- **THEN** every required surface is visible, no stage anchor overlaps another, two consecutive commands are sent from the command line without any pointer interaction, and Escape restores action-dock focus

#### Scenario: Mode gating removes surfaces rather than dimming them
- **WHEN** the committed mode changes to one that hides a surface
- **THEN** that surface is absent from the DOM layout and from the tab order, and it becomes present again when the mode changes back

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
- **WHEN** the narrative holds more lines than the bounded caption displays
- **THEN** the acceptance journey opens the complete retained log in one action from the caption and closes it on Escape with focus restored

#### Scenario: The minimap stays inside its island
- **WHEN** the shell renders a seeded grid room's minimap at each supported viewport
- **THEN** every node marker is inside the map canvas, no two node markers overlap, and the legend and detail line remain visible within the island
