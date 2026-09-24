## MODIFIED Requirements

### Requirement: The narrative palette is generated with a contrast floor and honors reduced motion
The project SHALL ship a generated stylesheet defining `.color-000` through `.color-255` and `.bgcolor-000` through `.bgcolor-255` covering the 16 ANSI entries, the 6×6×6 color cube on the standard component levels `0x00, 0x5f, 0x87, 0xaf, 0xd7, 0xff`, and the 24-step grayscale ramp. Foreground entries SHALL pass a deterministic contrast floor against the theme's ink background: while an entry's WCAG contrast ratio against the page background is below 3.0, it SHALL be blended 10% toward the theme's paper foreground, for at most 9 steps. Background entries SHALL use the unmodified palette value. The stylesheet SHALL be produced by a pure generator, and a repository test SHALL regenerate it and compare it byte-for-byte with the committed file. The `blink` class SHALL be neutralized to a non-animated indicator under `prefers-reduced-motion: reduce`, and also whenever the client's effective motion level is `reduced` or `off` (`webclient-contextual-hud` "The motion level is a client-local preference that governs every client animation"). The narrative surface SHALL use a monospace-first font stack while preserving `white-space: pre-wrap`, so server-rendered ASCII and box-drawing map art keeps its column alignment and its leading indentation.

#### Scenario: Every emitted color class is legible on the ink background
- **WHEN** the generated palette is evaluated against the theme background
- **THEN** every `.color-NNN` rule meets at least a 3.0 contrast ratio, and no class that `parse_html` can emit is missing from the stylesheet

#### Scenario: The committed palette cannot drift from its generator
- **WHEN** the repository palette test runs
- **THEN** regenerating the stylesheet reproduces the committed file byte-for-byte

#### Scenario: Reduced motion suppresses blinking output
- **WHEN** the browser reports `prefers-reduced-motion: reduce` and the server emits blinking text
- **THEN** the text is marked by a static non-animated indicator and no animation runs

#### Scenario: A stored reduced or off level suppresses blinking output
- **WHEN** the operating system does not request reduced motion, the stored motion level is `reduced` or `off`, and the server emits blinking text
- **THEN** the text is marked by the same static non-animated indicator and no animation runs

#### Scenario: Server map art within the pane width keeps its alignment
- **WHEN** a room description containing an ASCII or box-drawing map whose rows fit the narrative pane's content width is rendered
- **THEN** its rows align in columns and its leading indentation is preserved

#### Scenario: A row wider than the pane soft-wraps rather than clipping or scrolling the page
- **WHEN** a rendered row is wider than the narrative pane's content width
- **THEN** it soft-wraps inside the pane, the continuation is not required to stay column-aligned, no content is clipped, and the page itself does not scroll horizontally
