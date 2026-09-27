## MODIFIED Requirements

### Requirement: The narrative palette is generated with a contrast floor and honors reduced motion
The project SHALL ship a generated stylesheet defining `.color-000` through `.color-255` and `.bgcolor-000` through `.bgcolor-255` covering the 16 ANSI entries, the 6×6×6 color cube on the standard component levels `0x00, 0x5f, 0x87, 0xaf, 0xd7, 0xff`, and the 24-step grayscale ramp. Foreground entries SHALL use narrative tones rather than raw terminal colours: the twelve chromatic ANSI entries (`001`–`006` and `009`–`014`) SHALL take a fixed, authored table of muted tones that belongs to the client's ink-and-gold palette (the bright yellow entry SHALL equal the theme's gold accent `--gold-400`, and the bright red entry SHALL be a softened tone of its seal accent), the four achromatic ANSI entries and the grayscale ramp SHALL keep their palette values before contrast flooring, and every colour-cube entry SHALL have its HSL saturation capped at 0.62. At this mapping stage, before contrast flooring, chromatic cube hue SHALL remain within 2° of its source hue and lightness within 1/255, using inward integer rounding to keep saturation at most 0.62. After that mapping every foreground entry SHALL pass a deterministic contrast floor against the message band's ink reference `#141019` — while an entry's WCAG contrast ratio against that background is below 3.0, it SHALL be blended 10% toward the theme's paper foreground, for at most 9 steps — and no final foreground entry SHALL exceed an HSL saturation of 0.62. Contrast flooring MAY change hue and lightness. Background entries SHALL use the unmodified palette value. The stylesheet SHALL be produced by a pure generator, and a repository test SHALL regenerate it and compare it byte-for-byte with the committed file. The `blink` class SHALL be neutralized to a non-animated indicator under `prefers-reduced-motion: reduce`, and also whenever the client's effective motion level is `reduced` or `off` (`webclient-contextual-hud` "The motion level is a client-local preference that governs every client animation"). The narrative surface SHALL use a monospace-first font stack while preserving `white-space: pre-wrap`, so server-rendered ASCII and box-drawing map art keeps its column alignment and its leading indentation.

#### Scenario: Every emitted color class is legible on the ink background
- **WHEN** the generated palette is evaluated against the message band's ink background `#141019`
- **THEN** every `.color-NNN` rule meets at least a 3.0 contrast ratio, and no class that `parse_html` can emit is missing from the stylesheet

#### Scenario: Chromatic server colours read as narrative tones
- **WHEN** the server emits text in bright green, cyan, yellow, or red (`color-010`, `color-014`, `color-011`, `color-009`)
- **THEN** the text renders in the authored muted tone for that entry — bright yellow in the theme's gold accent — and not in the raw terminal colour

#### Scenario: No foreground entry is loud
- **WHEN** the generated palette's foreground entries are evaluated
- **THEN** every final entry's HSL saturation is at most 0.62, and every chromatic colour-cube entry keeps its source hue within 2° at the mapping stage before contrast flooring (which may shift hue)

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
