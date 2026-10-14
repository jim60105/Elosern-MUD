# Spec Delta

## MODIFIED Requirements

### Requirement: The face-rect modal stores geometry over the original image

臉部框選 SHALL overlay a draggable, square-locked rectangle on the card's committed image. The
rectangle's aspect on screen SHALL always be 1:1 in *pixels*: once the image's natural pixel size
(width, height) is known, dragging the resize handle and editing the 寬度/高度 numeric fields SHALL
keep the marked box square against that natural size, so the stored normalized rect satisfies
`w × naturalWidth == h × naturalHeight` within float tolerance.

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

#### Scenario: The two numeric fields differ on a non-square image
- **WHEN** the marked box is square on a portrait whose natural size is non-square
- **THEN** the player sees a square box and the 寬度 and 高度 fields usually display different fractions

#### Scenario: The player's box is re-squared when the image loads
- **WHEN** the player has edited the box before the image's natural size becomes known and the image then loads
- **THEN** the geometry is re-derived from the player's current box: center and vertical span preserved, width re-squared against the real aspect and clamped inside the unit square

#### Scenario: Editing stays possible before the size is known
- **WHEN** the natural size is unknown because the image is not yet loaded or the load failed
- **THEN** the modal presents the box and accepts numeric edits while 儲存框選 is disabled with a truthful hint, so no geometry is ever dispatched squared against a guessed aspect

#### Scenario: The image-info block shows only committed facts
- **WHEN** the modal renders 圖片資訊
- **THEN** it shows the card label, filename or identifier, the exact local date and time of `created_at` (日期不詳 when impossible), and the pixel size when committed

#### Scenario: The preview crops the same image
- **WHEN** a rect is marked and the 方形裁切預覽（1:1） renders
- **THEN** it crops the SAME committed image to the marked rect with a square crop — the preview frame's rendered box square within one pixel — with no second image and no upload of pixels

#### Scenario: Saving normalizes and dispatches once
- **WHEN** the player activates 儲存框選
- **THEN** the rect normalizes to `{x, y, w, h}` in [0,1] with positive area (locally clamped only to prevent nonsense dispatches) and exactly one `gallery.face_rect.update` is dispatched

#### Scenario: Escape or 取消 discards without a dispatch
- **WHEN** the player presses Escape or activates 取消 in the modal
- **THEN** the edit is discarded and nothing is dispatched

#### Scenario: Failure removes original and cropped broken elements
- **WHEN** the exact original fails decode while a silhouette is available
- **THEN** the original and crop-preview image elements are removed; save remains disabled and the silhouette contributes no dimensions

#### Scenario: New original revision alone recovers saving
- **WHEN** a new exact original version loads with usable dimensions
- **THEN** saving can recover for that identity; unchanged rerender and stale callback cannot manufacture success

### Requirement: Stage saves reuse correlated lifecycle and accessible gallery chrome
Save SHALL require successful decode and usable dimensions of the exact original plus existing mutation admission. Original failure SHALL leave only a healthy adult ruler and local failure explanation; ruler failure SHALL be explicit. No substitute SHALL enable saving. Correlated success/revision, rejection-draft preservation and accessible editor chrome SHALL remain.

#### Scenario: Save waits for image load
- **WHEN** the image has not loaded or its load fails
- **THEN** save cannot submit and truthful loading/failure feedback is present; failure renders only the reference in the preview

#### Scenario: Save closes only on its correlated revision
- **WHEN** save emits one triple and an unrelated update or successful result arrives without its declared revision
- **THEN** the editor remains open and locked until its own success and revision both commit

#### Scenario: Rejection preserves editable intent
- **WHEN** the submitted action is rejected
- **THEN** the same local triple remains visible with textual rejection feedback and 查看伺服器訊息, and the player can edit again once unlocked

#### Scenario: Keyboard and cancel restore focus without writes
- **WHEN** the player tabs through the dialog, edits numbers and presses Escape or 取消
- **THEN** focus stays trapped until close, then returns to 比例調整 and no save is dispatched

#### Scenario: Non-card and stale contexts cannot save
- **WHEN** a row is pending/failed, or the selected subject changes, the card disappears or the panel becomes unavailable
- **THEN** no stage mutation can target that context and any stale editor draft is discarded

#### Scenario: The dialog matches gallery-editor accessibility chrome
- **WHEN** the stage editor dialog opens
- **THEN** its dialog semantics, shared focus trap, visible gold focus, Escape/cancel/scrim close and opener restore match the other gallery editors

#### Scenario: Keyboard covers the drag functionality
- **WHEN** the player edits the triple without dragging
- **THEN** the numeric keyboard controls cover everything the pointer drag can do

#### Scenario: Chrome and motion follow existing tokens
- **WHEN** the editor renders
- **THEN** ink/gold/serif chrome and scaled geometry follow existing tokens, and motion preferences are respected without interpolating figure transforms or using red for normal selection

#### Scenario: Adult reference never authorizes save
- **WHEN** the original fails but adult reference loads
- **THEN** no stage save can dispatch and the ruler dimensions never become subject dimensions

#### Scenario: A failed ruler is identified separately
- **WHEN** the original loads but the adult reference fails
- **THEN** the missing ruler has its own local accessible failure indication and the original remains the only possible save target

