## MODIFIED Requirements

### Requirement: Art panel browser acceptance is keyboard-first, accessible, and desktop-bounded
The scene full view SHALL open by click on the backdrop's scene control or Enter on that focused
control and SHALL close on Escape. The scene label and alternative text SHALL remain visible as
text outside the bitmap, alternative text SHALL be meaningful, and no required information SHALL
exist only inside an image.

#### Scenario: Keyboard-only full view opens and closes
- **WHEN** the player focuses the scene control and presses Enter, then Escape
- **THEN** the full view opens on Enter and closes on Escape with focus restored

#### Scenario: Both supported viewports keep art usable
- **WHEN** the stage renders at 1451x790 and at 2560x1440
- **THEN** the backdrop, the scene label and alternative text, the portrait presentation (including the stage actors), and the status text remain visible and non-overlapping

#### Scenario: Player-authored text is not executed as markup
- **WHEN** a display name or label contains HTML-like player text
- **THEN** the browser renders it as literal text and creates no element or script from it

#### Scenario: Catalog entries render only inside consuming surfaces
- **WHEN** the browser renders portrait catalog entries
- **THEN** they render only inside the framed-portrait surfaces that consume them — the party strip and
  party drawer, the stage actors that stand the dialogue host, the combat party and the combat
  foes, the interact target avatars and dock
  target rows
- **AND** the client renders no standalone portrait catalog strip and no per-portrait full-view
  control

#### Scenario: Labels are text and motion is reducible
- **WHEN** server-authored labels render and the player prefers reduced motion
- **THEN** labels are inserted as text, not trusted HTML, and reduced-motion preference disables
  nonessential transitions

#### Scenario: Both viewports keep the stage usable
- **WHEN** the stage renders at 1451x790 and at 2560x1440
- **THEN** the stage backdrop and the framed portraits remain usable without the backdrop
  covering the scene label, the HUD islands, or required status

### Requirement: The browser maps each framed portrait's carried face rectangle to a centered cover crop through one shared pure function
Each framed-portrait surface named below SHALL crop its cover-fitted portrait images through one
shared pure mapping from the committed entry's normalized `face_rect` to a CSS `object-position`
percentage pair, exported by `web/webclient-app/components/face-rect.js`, so the server's authored
composition stays centered in a frame of any aspect ratio. Under cover fit the mapping SHALL align
the image's p% point with the frame's p% point, which centers the rectangle's center.

#### Scenario: A well-formed rectangle centers its face region
- **WHEN** a framed portrait renders a catalog entry whose rectangle is `{x: 0.25, y: 0.06, w: 0.5, h: 0.5}`
- **THEN** the image element's object-position centers that rectangle's center (vertically the 31% line), and the image keeps its cover fit

#### Scenario: A malformed rectangle degrades to the centered crop
- **WHEN** the mapping receives null, a non-finite field, an out-of-bounds field, an edge-crossing rectangle or non-positive width/height
- **THEN** it returns centered `50% 50%`, a URL-bearing surface renders that centered cover crop and a null-URL placeholder renders its label without an image

#### Scenario: Every framed portrait honors the carried rectangle
- **WHEN** the same entry is rendered by the party strip, party drawer avatar thumbnails, dialogue host avatar, interact target avatar, dock target row and character switcher
- **THEN** each cover-cropped image applies the shared mapping to its face rectangle, even when the entry carries a nonidentity stage triple

#### Scenario: The surfaces outside the recenters-only list are unchanged by this split
- **WHEN** a gallery card, the gallery detail rail preview, or a ReferenceArtwork cover-mode image renders an entry with a well-formed rectangle
- **THEN** it still renders the recenters-only `object-position` treatment exactly as before — the small-avatar zoom-crop requirement names it in neither its surface set nor its fallbacks

#### Scenario: A malformed rectangle returns the centered pair
- **WHEN** the mapping receives a `null` or `undefined` rectangle, or any rectangle with a
  non-finite field, a field outside `[0, 1]`, an `x + w` greater than 1, a `y + h` greater than 1,
  or a non-positive `w` or `h`
- **THEN** it returns the centered `50% 50%` pair — never a throw and never an off-frame
  percentage — so one corrupt card cannot blank a portrait surface

#### Scenario: Malformed-rectangle entries still render truthfully
- **WHEN** a URL-bearing entry's rectangle is missing or malformed, or an entry is a placeholder
  (a null URL)
- **THEN** the URL-bearing entry still renders its image with the centered crop, and only the
  placeholder entry renders its labelled placeholder with no image element

#### Scenario: The small-avatar set is refined by its dedicated requirement
- **WHEN** the small-avatar set — the top-bar character switcher's thumbnails and the party
  drawer's avatar thumbnails — crops a portrait
- **THEN** it additionally obeys the dedicated small-avatar zoom-crop requirement, which refines
  this rule for those surfaces by enlarging the crop around the same rectangle while keeping the
  identical validation set and the identical centered-crop fallback
- **AND** every other surface named here keeps the recenters-only treatment verbatim

#### Scenario: Avatar surfaces apply the mapping and ignore stage
- **WHEN** each avatar surface — the party strip and the party
  drawer's avatar thumbnails, the dialogue host avatar in the narrative feed, the interact target
  avatars and the dock's target rows, and the top-bar character switcher — renders an entry
- **THEN** it applies the mapping to that entry's rectangle and ignores stage

#### Scenario: The excluded surfaces stay outside the cover rule
- **WHEN** the drawer's full-figure art slot renders, or a scene backdrop renders
- **THEN** the drawer slot uses the separate stage render contract and is excluded from this cover
  rule, and scene backdrops — consuming scene media, not portrait entries — are outside this
  requirement
