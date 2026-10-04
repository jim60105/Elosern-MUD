## MODIFIED Requirements

### Requirement: The browser maps each framed portrait's carried face rectangle to a centered cover crop through one shared pure function
Each framed-portrait surface named below SHALL crop its cover-fitted portrait images through one
shared pure mapping from the committed entry's normalized `face_rect` to a CSS `object-position`
percentage pair, exported by `web/webclient-app/components/face-rect.js`, so the server's authored
composition stays centered in a frame of any aspect ratio. Under cover fit the mapping SHALL align
the image's p% point with the frame's p% point, which centers the rectangle's center.
The mapping SHALL return the centered `50% 50%` pair — never a throw and never an off-frame
percentage — for a `null` or `undefined` rectangle and for any rectangle with a non-finite field,
a field outside `[0, 1]`, an `x + w` greater than 1, a `y + h` greater than 1, or a non-positive
`w` or `h`, so one corrupt card cannot blank a portrait surface. A URL-bearing entry whose rectangle
is missing or malformed SHALL still render its image with that centered crop; only a placeholder
entry (a null URL) SHALL render its labelled placeholder with no image element.
The small-avatar set — the top-bar character switcher's thumbnails and the party drawer's avatar
thumbnails — additionally obeys the dedicated small-avatar zoom-crop requirement below, which
refines this rule for those surfaces by enlarging the crop around the same rectangle while keeping
the identical validation set and the identical centered-crop fallback; every other surface named
here keeps the recenters-only treatment verbatim. Each avatar surface — the combat participant
frame, the party strip and the party drawer's avatar thumbnails, the dialogue host avatar in the
narrative feed, the interact target avatars and the dock's target rows, and the top-bar character
switcher — SHALL apply the mapping to that entry's rectangle and SHALL ignore stage. The drawer's
full-figure art slot uses the separate stage render contract and is excluded from this cover rule.
Scene backdrops consume scene media, not portrait entries, and are outside this requirement.

#### Scenario: A well-formed rectangle centers its face region
- **WHEN** a framed portrait renders a catalog entry whose rectangle is `{x: 0.25, y: 0.06, w: 0.5, h: 0.5}`
- **THEN** the image element's object-position centers that rectangle's center (vertically the 31% line), and the image keeps its cover fit

#### Scenario: A malformed rectangle degrades to the centered crop
- **WHEN** the mapping receives null, a non-finite field, an out-of-bounds field, an edge-crossing rectangle or non-positive width/height
- **THEN** it returns centered `50% 50%`, a URL-bearing surface renders that centered cover crop and a null-URL placeholder renders its label without an image

#### Scenario: Every framed portrait honors the carried rectangle
- **WHEN** the same entry is rendered by the combat participant frame, party strip, party drawer avatar thumbnails, dialogue host avatar, interact target avatar, dock target row and character switcher
- **THEN** each cover-cropped image applies the shared mapping to its face rectangle, even when the entry carries a nonidentity stage triple

#### Scenario: The surfaces outside the recenters-only list are unchanged by this split
- **WHEN** a gallery card, the gallery detail rail preview, or a ReferenceArtwork cover-mode image renders an entry with a well-formed rectangle
- **THEN** it still renders the recenters-only `object-position` treatment exactly as before — the small-avatar zoom-crop requirement names it in neither its surface set nor its fallbacks

## ADDED Requirements

### Requirement: Small avatar thumbnails zoom-crop their portrait image to the carried face rectangle through one shared pure function
The small-avatar set — the top-bar character switcher's collapsed-pill thumbnail, the switcher
popover's per-row thumbnails, and the party drawer's per-companion avatar image — SHALL render a
URL-bearing portrait entry by cropping and zooming so the entry's marked face rectangle
substantially fills the frame: through one shared pure mapping exported by
`web/webclient-app/components/face-rect.js`, the image element SHALL be enlarged to `1/w` × `1/h`
of the frame's size (w, h the rectangle's normalized extents) and anchored inside the frame —
which clips the overflow — by the offsets `-x/w` and `-y/h` of the frame's width and height, so
the rectangle's region of the image maps onto the frame's full box. The enlargement factor SHALL
be clamped to 8× per axis, and the anchor offsets SHALL be derived from the clamped factors so the
rectangle window stays coherent under the clamp. The mapping SHALL validate the rectangle with
exactly the same well-formedness set as the recenters-only mapping — rejecting `null`,
`undefined`, non-finite fields, fields outside `[0, 1]`, `x + w` or `y + h` greater than 1, and
non-positive `w` or `h` — and for any rejected rectangle it SHALL produce no zoom properties,
leaving the image to render the same centered `50% 50%` cover crop it rendered before this
requirement. A placeholder entry (a null URL) SHALL render its existing label or glyph placeholder
with no image element, unchanged. The mapping SHALL ignore `stage`. The zoom is presentation-only:
the server stores rectangles verbatim and SHALL NOT crop, resize, or derive any second image.

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
