# webclient-art-panel delta

## ADDED Requirements

### Requirement: The browser maps every carried face rectangle to a centered cover crop through one shared pure function
The client SHALL crop every cover-fitted portrait through one shared pure mapping from the committed
entry's normalized `face_rect` to a CSS `object-position` percentage pair, exported by
`web/webclient-app/components/face-rect.js`, so the server's authored composition stays centered in a
frame of any aspect ratio. Under cover fit the mapping SHALL align the image's p% point with the
frame's p% point, which centers the rectangle's center. The mapping SHALL return the centered
`50% 50%` pair — never a throw and never an off-frame percentage — for a `null` or `undefined`
rectangle and for any rectangle with a non-finite field, a field outside `[0, 1]`, an `x + w` greater
than 1, a `y + h` greater than 1, or a non-positive `w` or `h`, so one corrupt card cannot blank a
portrait surface. Every surface that cover-crops a portrait entry — the combat participant frame, the
party strip and party drawer, the dialogue host avatar in the narrative feed, the interact target
avatars and the dock's target rows, and the top-bar character switcher — SHALL apply the mapping to
that entry's rectangle, and a surface with no rectangle (a placeholder entry) SHALL render its
placeholder, not an image.

#### Scenario: A well-formed rectangle centers its face region
- **WHEN** a framed portrait renders a catalog entry whose rectangle is `{x: 0.25, y: 0.06, w: 0.5, h: 0.5}`
- **THEN** the image element's `object-position` is the pair that centers that rectangle's center (vertically the 31% line for this rectangle), and the image keeps its cover fit

#### Scenario: A malformed rectangle degrades to the centered crop
- **WHEN** the mapping receives `null`, a non-finite field, a field outside `[0, 1]`, a rectangle crossing either normalized edge, or a non-positive width or height
- **THEN** it returns the centered `50% 50%` pair and the surface renders the image with a centered crop

#### Scenario: Every framed portrait honors the carried rectangle
- **WHEN** the same catalog entry is rendered by the combat participant frame, a party surface, the dialogue host avatar, an interact target avatar, a dock target row, and the character switcher
- **THEN** each cover-cropped image applies the shared mapping to that entry's rectangle rather than a fixed center crop

### Requirement: The reference artwork frame presents a portrait entry truthfully through cover fit and rect crop
The `World/ReferenceArtwork` component SHALL render a portrait catalog entry as one cover-fitted image
whose crop follows the entry's `face_rect`, with no invented frame: a `null` entry or a placeholder
entry (null URL) SHALL render the truthfully labelled placeholder and no image element; a media load
that fails SHALL degrade that frame to the labelled placeholder; and a subsequent entry whose URL
differs SHALL re-attempt and render the new image, so a repaired asset recovers without remounting the
surface. The component SHALL be manifest-listed in the re-frozen required set and covered by the
deterministic component-coverage gate.

#### Scenario: A resolved entry renders the cropped image
- **WHEN** the frame receives an entry carrying a media URL and a well-formed rectangle
- **THEN** it renders exactly that URL cover-fitted with the shared rect crop and no placeholder

#### Scenario: A placeholder entry renders no image
- **WHEN** the frame receives a null entry or an entry whose URL is null with a placeholder label
- **THEN** no image element exists in the frame and the placeholder's label is the rendered text

#### Scenario: A failed load degrades and a URL change recovers
- **WHEN** a rendered entry's image fires a load error, and the frame is later given an entry with a different URL
- **THEN** the failed load replaces the image with the labelled placeholder, and the changed URL renders a new image element carrying the replacement URL
