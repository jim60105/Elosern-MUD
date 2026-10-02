# webclient-gallery-ui — delta for square-face-rect-contract

## MODIFIED Requirements

### Requirement: The face-rect modal stores geometry over the original image

臉部框選 SHALL overlay a draggable, square-locked rectangle on the card's committed image. The
rectangle's aspect on screen SHALL always be 1:1 in *pixels*: once the image's natural pixel size
(width, height) is known, dragging the resize handle and editing the 寬度/高度 numeric fields SHALL
keep the marked box square against that natural size, so the box the player sees is square and the
stored normalized rect satisfies `w × naturalWidth == h × naturalHeight` within float tolerance —
the two numeric fields therefore usually display different fractions on a non-square portrait
image. Dragging the box body moves it without resizing, clamped inside the image. The modal's
initial geometry SHALL be the fitted default square for the known natural size, or the shared
upper-half anchor while the natural size is unknown (before load), and SHALL be re-derived from
the player's current box once the image loads: center and vertical span preserved, width
re-squared against the real aspect and clamped inside the unit square. While the natural size is
unknown — image not yet loaded or load failed — the modal SHALL present the box and accept numeric
edits but SHALL disable 儲存框選 with a truthful hint, and SHALL NOT dispatch geometry squared
against a guessed aspect. The 圖片資訊 block SHALL show committed facts (card label, filename or
identifier, the exact local date and time of `created_at` (日期不詳 when impossible), pixel size
when committed), and the 方形裁切預覽（1:1） SHALL crop the SAME image to the marked rect with a
square crop — the preview frame's rendered box SHALL be square within one pixel — with no second
image and no upload of pixels. On 儲存框選 the rect SHALL normalize to `{x, y, w, h}` in [0,1]
with positive area (locally clamped only to prevent nonsense dispatches) and dispatch exactly one
`gallery.face_rect.update`. Escape/取消 discards without a dispatch.

#### Scenario: The stored rect equals the modal's normalized rect
- **WHEN** a rect is saved
- **THEN** the dispatched face_rect matches the modal geometry within float tolerance and the payload carries no image data

#### Scenario: Resize stays square on a non-square image
- **WHEN** the image's natural size is 768×1024 and the player drags the resize handle
- **THEN** at every intermediate position the dispatched-eligible rect satisfies
  `w × 768 == h × 1024` within float tolerance, and the on-screen box height equals its width
  within one pixel

#### Scenario: A numeric width edit re-derives the height
- **WHEN** the image's natural size is 768×1024 and the player sets 寬度 to 0.4
- **THEN** 高度 reads 0.3 (within float tolerance) so the marked box stays pixel-square

#### Scenario: A numeric height edit re-derives the width
- **WHEN** the image's natural size is 768×1024 and the player sets 高度 to 0.5
- **THEN** 寬度 reads 0.6667 (within float tolerance) and the box stays inside the unit square

#### Scenario: The preview is square
- **WHEN** any valid rect is marked on any image
- **THEN** the 方形裁切預覽（1:1） crop frame renders as a square within one pixel and shows
  exactly the marked region

#### Scenario: The initial box is the fitted square once the image loads
- **WHEN** the modal opens on a 768×1024 card image before and after load
- **THEN** before load the box shows the shared upper-half anchor, and after load the untouched
  box reads `{x: 0.25, y: 0.06, w: 0.5, h: 0.375}` — a square on screen and on the image

#### Scenario: Saving is gated on the real image size
- **WHEN** the card image has never loaded (or failed to load)
- **THEN** 儲存框選 is disabled with a zh-TW hint and no dispatch is possible, so no rect is ever
  squared against a guessed aspect

#### Scenario: Dragging moves without resizing
- **WHEN** the player drags the box body on a loaded 768×1024 image
- **THEN** `w` and `h` are unchanged and only `x`/`y` move, clamped so the rect stays inside the
  unit square
