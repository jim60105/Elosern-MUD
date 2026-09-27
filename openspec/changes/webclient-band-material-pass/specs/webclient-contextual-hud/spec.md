## ADDED Requirements

### Requirement: The bottom band separates material and focus without obscuring controls
The fixed bottom band SHALL provide a continuous ink-and-gold reading surface with a decorative stage seam and aligned message-control and shortcut rows. Page text, command rows and popovers SHALL never paint over these reserved controls. Only the active control SHALL carry the strongest focus treatment; the command field SHALL expose one clear focus frame.

#### Scenario: Popover text is isolated
- **WHEN** a verb popover opens over populated scene chips
- **THEN** no chip text shows through it, the target heading is stated once, and background chips cannot activate

#### Scenario: Dense command content is bounded
- **WHEN** a frame contains more rows than fit
- **THEN** its own row region scrolls while the legend and message controls remain visible on one baseline

#### Scenario: Motion is reduced
- **WHEN** the player changes command frames with reduced motion or off
- **THEN** reduced uses no 3D rotation or wipe and off commits immediately without losing focus
