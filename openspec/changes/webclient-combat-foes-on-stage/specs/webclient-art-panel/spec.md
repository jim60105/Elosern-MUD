## MODIFIED Requirements

### Requirement: Art panel browser acceptance is keyboard-first, accessible, and desktop-bounded
The scene full view SHALL open by click on the backdrop's scene control or Enter on that focused
control and SHALL close on Escape. Portrait catalog entries SHALL render only inside the framed-portrait
surfaces that consume them (the combat participant frame, the party strip and party drawer, the
stage actors that stand the dialogue host and the combat foes in the `actor-right` anchor, the interact
target avatars and dock target rows); the client SHALL render no
standalone portrait catalog strip and no per-portrait full-view control. The
scene label and alternative text SHALL remain visible as text outside the bitmap, alternative text
SHALL be meaningful, and no required information SHALL exist only inside an image. Server-authored
labels SHALL be inserted as text, not trusted HTML, and reduced-motion preference SHALL disable
nonessential transitions. The stage backdrop and the framed portraits SHALL remain usable at both
1440x900 and 1280x720 without the backdrop covering the scene label, the HUD islands, or required
status.

#### Scenario: Keyboard-only full view opens and closes
- **WHEN** the player focuses the scene control and presses Enter, then Escape
- **THEN** the full view opens on Enter and closes on Escape with focus restored

#### Scenario: Both supported viewports keep art usable
- **WHEN** the stage renders at 1440x900 and at 1280x720
- **THEN** the backdrop, the scene label and alternative text, the portrait presentation (including the stage actors), and the status text remain visible and non-overlapping

#### Scenario: Player-authored text is not executed as markup
- **WHEN** a display name or label contains HTML-like player text
- **THEN** the browser renders it as literal text and creates no element or script from it
