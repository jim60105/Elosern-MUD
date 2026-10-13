## MODIFIED Requirements

### Requirement: Compass behavior is verified in the live client at two viewports
The compass SHALL be verified by `agent-browser` in the live client at 1451×790 and 1920×1080, where the pad fits the band height minus padding without scrolling the command panel.

#### Scenario: The pad fits at both viewports
- **WHEN** the live client shows an exploration room at 1451×790 and at 1920×1080
- **THEN** the compass pad, the 建議 pill, and the shared readout are fully visible with no horizontal overflow and the command panel's box is unchanged

#### Scenario: Hover, click, and a hold-walk behave as specified in the wilderness
- **WHEN** the wilderness room is explored with hover, a click, and a held direction
- **THEN** each behaves as the pad, click, and walk requirements state
