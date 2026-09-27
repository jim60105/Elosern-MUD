## ADDED Requirements

### Requirement: The full log is framed without changing retained content
The full log SHALL use the shared reference header and readable prose measure, style existing input echoes as response separators without duplicating them, and retain every line in original order through the existing safe renderer. Opening SHALL still show the latest line before interaction.

#### Scenario: Echo is a section heading
- **WHEN** a retained response begins with a player input echo
- **THEN** that echo appears exactly once in its original position and its response lines remain unchanged

### Requirement: Log readers can return to latest without losing their place involuntarily
When the reader is above the end of the log, the full log SHALL offer a labelled return-to-latest control and SHALL NOT force-scroll on incoming lines. Activating the control SHALL reveal the latest retained line without advancing the message window.

#### Scenario: New text arrives during review
- **WHEN** the player has scrolled upward and a new response arrives
- **THEN** the viewed position remains stable and the return control reveals the new end only when activated
