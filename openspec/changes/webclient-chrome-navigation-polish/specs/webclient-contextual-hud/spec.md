## ADDED Requirements

### Requirement: Top navigation retains stable tool placement while respecting mode availability
The top navigation tool group SHALL retain a stable horizontal position across exploration and combat at a fixed viewport size. Mode-forbidden controls SHALL remain absent from rendering and keyboard navigation; reserved layout space SHALL NOT introduce an operable placeholder. Icon-only tools SHALL disclose their names visually on both hover and keyboard focus.

#### Scenario: Combat removes unavailable entries
- **WHEN** the committed mode changes from exploration to combat
- **THEN** unavailable entries leave the tab order and rendering while the tool cluster does not jump into their space

#### Scenario: Keyboard user identifies a tool
- **WHEN** a tool receives keyboard focus
- **THEN** its readable tooltip appears without stealing focus, and Escape dismisses the tooltip

### Requirement: Place identity has a readable hierarchy
The place card SHALL distinguish its location title from the complete world-time line, with aligned tabular numerals and no orphan leading separator. All time values SHALL remain server-authored.

#### Scenario: No prefix exists
- **WHEN** a time line has no preceding qualifier
- **THEN** it renders without a leading dash and retains every actual date/time value
