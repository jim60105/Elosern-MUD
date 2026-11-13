## ADDED Requirements

### Requirement: Collapsible group headings are buttons
When the committed groups include at least one collapsed group, every labelled group heading SHALL be a button carrying `aria-expanded`, and activating a collapsed group's heading SHALL emit `expand-group` once with its key. When no group is collapsed, headings SHALL stay plain headings.

#### Scenario: A collapsed heading expands on activation
- **WHEN** groups P2 (expanded) and P1 (collapsed) are committed and the player activates P1's heading
- **THEN** `expand-group` is emitted once with P1, P1's heading carries `aria-expanded="false"` and P2's `aria-expanded="true"`

#### Scenario: Tier headings stay plain
- **WHEN** every committed group is expanded
- **THEN** no heading is a button
