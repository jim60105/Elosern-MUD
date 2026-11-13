## ADDED Requirements

### Requirement: Expanding a group is one server round trip
An `expand-group` from the wall SHALL send exactly one `gallery.group.select` with that key through the gated dispatch entry; the wall SHALL keep the committed expansion until the next committed panel, marking the pressed heading busy meanwhile.

#### Scenario: The press waits for the commit
- **WHEN** the player expands collapsed place P1
- **THEN** one `gallery.group.select` with P1 is sent, P1's heading carries `aria-busy="true"`, and P1's subjects appear only when a panel with P1 expanded commits
