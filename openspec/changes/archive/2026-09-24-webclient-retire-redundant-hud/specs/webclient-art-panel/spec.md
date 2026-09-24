## MODIFIED Requirements

### Requirement: Art panel browser acceptance is keyboard-first, accessible, and desktop-bounded
The scene full view SHALL open by click on the backdrop's scene control or Enter on that focused
control and SHALL close on Escape. Portrait catalog entries SHALL render only inside the framed-portrait
surfaces that consume them (the combat participant frame, the party strip and party drawer, the
dialogue host avatar, the interact target avatars and dock target rows); the client SHALL render no
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
- **THEN** the backdrop, the scene label and alternative text, the portrait presentation, and the status text remain visible and non-overlapping

#### Scenario: Player-authored text is not executed as markup
- **WHEN** a display name or label contains HTML-like player text
- **THEN** the browser renders it as literal text and creates no element or script from it

### Requirement: The browser maps each framed portrait's carried face rectangle to a centered cover crop through one shared pure function
Each framed-portrait surface named below SHALL crop its cover-fitted portrait images through one
shared pure mapping from the committed entry's normalized `face_rect` to a CSS `object-position`
percentage pair, exported by `web/webclient-app/components/face-rect.js`, so the server's authored
composition stays centered in a frame of any aspect ratio. Under cover fit the mapping SHALL align
the image's p% point with the
frame's p% point, which centers the rectangle's center. The mapping SHALL return the centered
`50% 50%` pair — never a throw and never an off-frame percentage — for a `null` or `undefined`
rectangle and for any rectangle with a non-finite field, a field outside `[0, 1]`, an `x + w` greater
than 1, a `y + h` greater than 1, or a non-positive `w` or `h`, so one corrupt card cannot blank a
portrait surface. A URL-bearing entry whose rectangle is missing or malformed SHALL still render its
image with that centered crop; only a placeholder entry (a null URL) SHALL render its labelled
placeholder with no image element. Each framed-portrait surface — the combat participant frame, the
party strip and party drawer, the dialogue host avatar in the narrative feed, the interact target
avatars and the dock's target rows, and the top-bar character switcher — SHALL apply the mapping to
that entry's rectangle. Scene backdrops consume scene media, not portrait
entries, and are outside this requirement.

#### Scenario: A well-formed rectangle centers its face region
- **WHEN** a framed portrait renders a catalog entry whose rectangle is `{x: 0.25, y: 0.06, w: 0.5, h: 0.5}`
- **THEN** the image element's `object-position` is the pair that centers that rectangle's center (vertically the 31% line for this rectangle), and the image keeps its cover fit

#### Scenario: A malformed rectangle degrades to the centered crop
- **WHEN** the mapping receives `null`, a non-finite field, a field outside `[0, 1]`, a rectangle crossing either normalized edge, or a non-positive width or height
- **THEN** it returns the centered `50% 50%` pair, a URL-bearing surface renders that image with the centered crop, and a null-URL placeholder entry renders its labelled placeholder with no image element

#### Scenario: Every framed portrait honors the carried rectangle
- **WHEN** the same catalog entry is rendered by the combat participant frame, the party strip and the party drawer, the dialogue host avatar, an interact target avatar, a dock target row, and the character switcher
- **THEN** each cover-cropped image applies the shared mapping to that entry's rectangle rather than a fixed center crop
