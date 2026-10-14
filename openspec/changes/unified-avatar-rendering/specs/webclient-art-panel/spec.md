# Spec Delta

## MODIFIED Requirements

### Requirement: Small avatar thumbnails zoom-crop their portrait image to the carried face rectangle through one shared pure function
The small-avatar set — the top-bar character switcher's collapsed-pill thumbnail, its popover's
per-row thumbnails, and the party drawer's per-companion avatar image — SHALL crop a URL-bearing
portrait through one shared pure mapping exported by `web/webclient-app/components/face-rect.js`:
enlarge the image to `1/w` × `1/h` of the frame, anchored at `-x/w`/`-y/h` of the frame, so the
face rectangle (extents w, h) substantially fills the frame.

#### Scenario: A well-formed rectangle fills a small avatar frame
- **WHEN** the switcher pill thumbnail, a switcher popover row thumbnail, or a party drawer avatar renders a URL-bearing entry whose rectangle is `{x: 0.3, y: 0.1, w: 0.4, h: 0.4}`
- **THEN** the image element is sized to 250% of the frame's width and height and anchored at offsets `-75%`/`-25%` of the frame, so the rectangle's region covers the frame box and the frame clips the rest

#### Scenario: A horizontally off-center rectangle anchors correctly
- **WHEN** a small avatar renders an entry whose rectangle is `{x: 0.6, y: 0.1, w: 0.2, h: 0.2}` (a rect whose center is right of the image center — the case a symmetric fixture cannot mask)
- **THEN** the image element is sized to 500%/500% and anchored at `-300%`/`-50%` of the frame, placing the right-shifted rectangle — not the image center — over the frame

#### Scenario: Every small-avatar surface shares the zoom mapping
- **WHEN** the same URL-bearing entry with a well-formed rectangle is rendered by the switcher pill thumbnail, a switcher popover row thumbnail, and a party drawer avatar
- **THEN** all three apply the shared zoom mapping to that entry's rectangle, and a nonidentity `stage` triple on the entry changes none of them

#### Scenario: A null or malformed rectangle falls back to the centered crop
- **WHEN** any surface in the small-avatar set receives null, `undefined`, a non-finite field, an out-of-bounds field, an edge-crossing rectangle, or non-positive width/height
- **THEN** the image renders with no zoom properties — the centered `50% 50%` cover crop — and nothing throws

#### Scenario: A placeholder entry renders no image
- **WHEN** a switcher row or party drawer avatar carries a null-URL placeholder entry, whatever its rectangle field says
- **THEN** the existing labelled or glyph placeholder renders with no image element, identical to the pre-change behavior

#### Scenario: A whole-image rectangle zooms to identity
- **WHEN** a small avatar renders an entry whose rectangle is `{x: 0, y: 0, w: 1, h: 1}`
- **THEN** the mapping produces 100% sizing at zero offsets and the frame shows the same centered cover crop as before

#### Scenario: A degenerate skinny rectangle clamps at the cap
- **WHEN** a small avatar renders an entry whose rectangle has a width or height below 1/8 of the image (e.g. `{x: 0.49, y: 0.49, w: 0.02, h: 0.02}`)
- **THEN** the enlargement clamps to 800% on that axis, the anchor offset is derived from the clamped factor (e.g. `-392%`/`-392%`), and nothing throws

#### Scenario: A legacy non-square rectangle still fills without blanking
- **WHEN** the zoom renders a legacy or hand-authored non-square rectangle
- **THEN** the same enlarge-and-anchor composition fills the frame from the rectangle while
  cropping a bounded sliver on the overflowing axis, and never blanks the image — the exact window
  holds for the pixel-square rectangle the authoring path enforces

#### Scenario: The zoom validates with the shared well-formedness set
- **WHEN** the zoom mapping validates a rectangle
- **THEN** it uses exactly the same well-formedness set as the recenters-only mapping — rejecting
  `null`, `undefined`, non-finite fields, fields outside `[0, 1]`, `x + w` or `y + h` greater than
  1, and non-positive `w` or `h` — and for any rejected rectangle it produces no zoom properties,
  leaving the image to render the same centered `50% 50%` cover crop it rendered before this
  requirement

#### Scenario: Placeholder avatars and stage are untouched
- **WHEN** a small avatar receives a placeholder entry (a null URL), or an entry carrying `stage`
- **THEN** the placeholder renders its existing label or glyph placeholder with no image element,
  unchanged, and the mapping ignores `stage`

#### Scenario: The zoom is presentation-only
- **WHEN** the client zoom-crops a portrait
- **THEN** the server stores rectangles verbatim and does not crop, resize, or derive any second
  image

#### Scenario: Shared avatar loading uses the actual successful candidate
- **WHEN** the first image fails and a different source succeeds
- **THEN** all avatar surfaces use that successful source face rectangle, ignore stage placement and retain reached faults

#### Scenario: Name fallback never requests alpha resources
- **WHEN** no real avatar image succeeds
- **THEN** the first trimmed-name grapheme or neutral empty-name symbol renders without a silhouette request

