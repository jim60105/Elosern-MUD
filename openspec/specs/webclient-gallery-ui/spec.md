# webclient-gallery-ui Specification

## Purpose
The Vue client surface for the 角色肖像圖庫 (character portrait gallery): it
renders the committed `gallery` panel verbatim — subject rail, filter tabs,
card grid, detail rail, generate/binding drawers and the face-rect modal —
and mutates only through the single committed action-dispatch entry, so all
gallery facts stay server-owned while view state and drafts stay client-local.
The capability also pins the offline interactive Storybook storyboard that
documents the complete management journey.

## Requirements

### Requirement: The gallery surface renders only committed panel facts

The Vue application SHALL render the 角色肖像圖庫 management surface from the
committed `gallery` panel only: subject rail, filter-tab labels and counts,
card order, chips, crown (「目前預設」), pending spinner rows, failed rows
(「暫時無法生成，稍後再試」), card labels, equipment summary, binding conditions,
and overlap warnings SHALL come verbatim from the payload. The client SHALL NOT
compose chips or labels, compute filter counts or overlap rules, read
equipment state, or re-sort rows (list order is payload order; the tab FILTERS
by the committed row status/`binding_present`/`is_default` facts). Static chrome,
filter labels and the closed field/slot catalog are client vocabulary, and a
row's date is presented from its structured `created_at` only — never parsed
from a label — as a localized relative time (剛剛 within a minute either way,
then minutes, hours, days, months or years, past or future) with the exact
localized local date and time available to assistive technology and on hover;
a non-numeric, non-finite or out-of-calendar value reads 日期不詳 while the row
keeps its label and status. The relative time refreshes at most once per minute
while the surface is open, and its clock stops when the surface closes. A card
image's or card name's accessible name is the committed label followed by the
exact local instant, so rows sharing a label stay distinguishable; that
accessible name is the only string the client composes around a label. The
surface SHALL mount from the existing overlay host when the committed panel is
available and SHALL lock its mutation controls while the panel is unavailable.

#### Scenario: Tabs render the committed counts

- **WHEN** the committed filters are all 8, defaults 1, bound 3, pending 1, failed 1
- **THEN** the tab row shows 全部 (8) 預設 (1) 已綁定 (3) 生成中 (1) 失敗 (1) with no client arithmetic

#### Scenario: A failed row renders the committed failure line

- **WHEN** a row carries status `failed` with the committed zh-TW message
- **THEN** the card shows that message verbatim and no image element, and the panel remains fully usable

#### Scenario: Subject selection dispatches and waits for the panel

- **WHEN** a rail row is activated
- **THEN** exactly one `gallery.subject.select` dispatch carries that committed subject key, and the surface re-renders only when the new committed panel arrives

#### Scenario: Same-label cards stay distinguishable
- **WHEN** two cards share the label 「肖像」 and differ in `created_at`
- **THEN** each shows its own relative date, its exact local instant is available on hover and to
  assistive technology, its image's accessible name is 「肖像」 plus that instant, and no label is
  parsed or rewritten

#### Scenario: Impossible and future instants stay truthful
- **WHEN** a row's `created_at` is in the future, or is finite but outside the calendar
- **THEN** the future row reads a future-relative time, the impossible one reads 日期不詳, and both
  keep their label and status

#### Scenario: The date clock lives only while the gallery is open
- **WHEN** the gallery stays open for a minute and then closes
- **THEN** the relative dates refresh once and the minute clock is torn down with the surface

### Requirement: The detail rail presents the selected card and gates destructive intent

The 肖像詳情 rail SHALL show the selected card's preview (cover-cropped through
the shared `face-rect.js` mapping), committed badges, 綁定條件 rows, 當前狀態
line, and the affordances 設為預設 / 編輯設定 / 刪除 plus the 生成新圖 CTA.
Conditions SHALL appear only when committed warnings provide them; otherwise
their absence SHALL be explicit. The rail SHALL NOT claim that the default
image is currently resolved for display, because v1 supplies no such flag.
設為預設 SHALL dispatch `gallery.default.set` once; 刪除 SHALL require an
in-rail confirmation step before dispatching `gallery.card.delete` and SHALL
cancel without a dispatch. Monster-kind subjects SHALL render the delete/replace
shape truthfully from the committed capability flags (one-card 替換 semantics),
with binding affordances absent when `capabilities.supports_bindings` is false.

#### Scenario: Delete requires confirmation

- **WHEN** the player activates 刪除 and cancels the confirmation
- **THEN** no `ui_action` is dispatched and the card remains listed

#### Scenario: Monster cards hide binding affordances

- **WHEN** the selected subject's committed capabilities name no binding support
- **THEN** no 編輯設定 binding affordance is rendered for its card

### Requirement: The generate drawer maps checkboxes to the closed catalog and dispatches one request

納入生成的資料 SHALL render exactly the closed field catalog of
`art-gallery-prompt-fields` — 角色外貌描述 / 主手武器 / 副手武器 / 防具 / 飾品 —
rendered ONLY when the committed `capabilities.supports_field_selection` is
true (monster subjects render the drawer without any checkbox), with the
已選 n / 5 counter derived from the client-local checkbox set only. 目前裝備摘要 SHALL render the
committed `equipment_summary` (per-slot equipped display name or 未裝備; the
accessories count line). 補充提示詞 SHALL be a textarea whose n / 512 counter
is cosmetic; on submit the surface SHALL dispatch exactly one
`gallery.generate` with the selected catalog ids and the raw text, SHALL close
after its own successful result and declared presentation revision have both
committed, and SHALL surface any server
rejection message verbatim without inventing its own.

#### Scenario: Submit carries only catalog ids

- **WHEN** appearance and armor are ticked with free text entered
- **THEN** the dispatched payload's `fields` are exactly `["appearance", "armor"]` plus the text, with no item keys or equipment snapshot

#### Scenario: An oversized prompt is refused by the server line

- **WHEN** a submission is rejected for the prompt bound
- **THEN** the server's zh-TW message appears verbatim and the drawer keeps the player's input

### Requirement: The binding drawer enables slots only and renders overlap warnings verbatim

裝備條件設定 SHALL offer a per-slot enable checkbox over the committed slot
vocabulary; each enabled slot SHALL display ONLY the currently-equipped value
(or the empty-slot state) from `equipment_summary` — never a registry item
picker. 目前綁定條件 and 規則重疊提醒 SHALL render the committed
`binding_warnings` verbatim (other card name, its condition lines with 「任一」
accessory phrasing, 查看 jumping the rail selection client-side). 儲存綁定
SHALL dispatch exactly one `gallery.binding.save` carrying the enabled slot
ids and the card's committed `image_id` — never item keys.

#### Scenario: No item picker exists

- **WHEN** the player opens a per-slot dropdown
- **THEN** it lists only the committed current value or the empty-slot state, and the save payload carries slot ids only

#### Scenario: Overlap warnings come from the panel

- **WHEN** committed warnings list one other card with two condition lines
- **THEN** the drawer shows that card's name and lines verbatim with a 查看 control, and no matching logic runs client-side

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

### Requirement: Gallery mutations ride the single dispatch entry and its gates

Every gallery control SHALL dispatch through the application's single action
dispatch entry, honoring the existing connected / locked / one-in-flight
gates, SHALL submit at most once per activation, and SHALL release its local
pending state on the action result. Non-success results SHALL surface the
committed message exactly once through the existing narrative error path.

#### Scenario: A concurrent second mutation cannot dispatch

- **WHEN** a generate request is in flight and the player activates 設為預設
- **THEN** no second `ui_action` leaves the client while the gate is closed

### Requirement: The gallery surface is keyboard-first and never color-only

Cards, rail rows, tabs, checkboxes, drawer controls, and the modal SHALL be
keyboard-reachable with visible focus; the drawers and modal SHALL use the
shared focus trap with Escape-to-close and focus restoration parity with the
existing overlays; the crown, 生成中, and failed states SHALL carry explicit
text and not rely on color alone.

#### Scenario: Escape closes the modal without a dispatch

- **WHEN** the face-rect modal is focused and Escape is pressed
- **THEN** the modal closes, focus returns to its opener, and no action is dispatched

### Requirement: The gallery has an offline interactive storyboard
The gallery component Storybook families SHALL include an interactive storyboard
under Data/GalleryPanel covering browse, generation, pending and failure, binding, face editing,
stage transform editing/reset/save/rejection, default selection and delete confirmation.
A frame guide SHALL reference the four existing design images, state each transition and
recovery path and distinguish fixture publications from live behavior. The stage editor SHALL
reuse existing local assets without requiring a new reference image.

#### Scenario: The storyboard runs without game or AI services
- **WHEN** the player opens the built Storybook gallery storyboard offline
- **THEN** the real components expose every documented frame with deterministic fixtures and no game-server or AI-service requests

#### Scenario: Context changes invalidate an editor
- **WHEN** the selected subject changes, its card disappears or the panel becomes unavailable
- **THEN** stale drafts are discarded and cannot dispatch against the replacement context

#### Scenario: An unrelated pending job does not complete a submission
- **WHEN** another pending row is published before this editor's correlated result
- **THEN** the editor remains open and a rejected result preserves its draft

### Requirement: Stage transforms affect full figures and never avatar cover crops
Stage and drawer full-figure portraits SHALL render contain/bottom-aligned with bottom-center origin, applying frame-relative translation followed by scale in the declared transform list. Missing/null stage SHALL render identity. Positive y SHALL move down; offsets SHALL remain independent of scale. The ground anchor SHALL stay fixed, the figure shadow SHALL follow the figure and existing overflow-visible behavior SHALL remain. Stage edits SHALL be immediate and SHALL NOT change the portrait source key or trigger crossfade. Gallery/detail cards, roster avatars and party-strip cover crops SHALL remain face-rect driven. Existing inline stage placeholders SHALL remain unchanged.

#### Scenario: A child stays on the same ground line
- **WHEN** stage scale changes from 1.0 to 0.6 with x and y zero
- **THEN** the full figure scales around 50% 100%, its feet anchor and ground ellipse remain fixed, and no new source crossfade occurs

#### Scenario: Translation uses frame dimensions at every scale
- **WHEN** x is 0.1 and y is -0.2 at scales 0.6 and 2.0 in the same frame
- **THEN** both render offsets of 10% frame width and -20% frame height; custom properties carry the exact triple and enlarged figures are not newly clipped

#### Scenario: Null stage and cover crop remain unchanged
- **WHEN** stage is missing/null or a nonidentity triple is supplied to a cover-mode avatar
- **THEN** stage mode normalizes missing/null to identity and cover mode uses the same faceObjectPosition with no stage transform

### Requirement: The stage editor previews a local triple against a static adult reference
The selected completed card SHALL expose 比例調整 opening a dedicated accessible modal with a fixed 3:4 preview and paired range/number controls 比例 [0.2, 2.0], 水平/垂直 [-0.5, 0.5], all step 0.01. Controls SHALL synchronize and clamp locally; drag SHALL map captured pointer deltas to preview-frame fractions, preserving scale and clamping offsets. 重設 SHALL locally restore identity. The current card SHALL use the same contain/bottom transform as live stage. Its adult reference SHALL be a static, noninteractive, aria-hidden CSS mask of existing /art/defaults/man.webp, fill #17191f, contain/bottom-centered with no stroke/text/ground ellipse, identity scale and left translation of half its own displayed width. Both feet lines SHALL coincide. Preview edits/reset SHALL send no request and create no image.

#### Scenario: Slider and number edits synchronize
- **WHEN** scale range changes to 0.6 and horizontal number changes to 0.1
- **THEN** both control pairs and the local preview agree, with no network action

#### Scenario: Drag uses frame fractions and clamps
- **WHEN** the captured pointer moves 30px right and 40px up in a 300px by 400px frame
- **THEN** x increases 0.1, y decreases 0.1, scale is unchanged and repeated movement cannot exceed either offset bound

#### Scenario: Reset does not save
- **WHEN** 重設 is activated on a nonidentity draft
- **THEN** local values become `{scale: 1.0, x: 0.0, y: 0.0}` and no action is dispatched

#### Scenario: Adult comparison stays static
- **WHEN** scale and offsets of the current card change in a 3:4 preview containing the 9:16 reference
- **THEN** the reference remains bottom-aligned at scale 1.0, approximately 75% of frame width and translated left by half that displayed width, with no editable transform dependency

### Requirement: Stage saves reuse correlated lifecycle and accessible gallery chrome
Save SHALL be disabled until the current image loads and while mutation admission is disabled/pending. Image failure SHALL leave the adult reference and truthful error text, with save disabled. 儲存調整 SHALL submit exactly one stage triple through gallery.stage.update using the committed subject/card identity. Only its own successful result and committed presentation revision SHALL close the editor; rejection SHALL retain the draft and offer the log link. Context invalidation SHALL discard stale drafts. Dialog semantics, shared focus trap, visible gold focus, Escape/cancel/scrim close and opener restore SHALL match gallery editors. Numeric keyboard controls SHALL cover drag functionality. Ink/gold/serif chrome and scaled geometry SHALL follow existing tokens; motion preferences SHALL be respected without interpolating figure transforms or using red for normal selection.

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

### Requirement: Stage transform stories document visual and state behavior offline
The offline showcase SHALL include the new modal family registered in the frozen component manifest, stage-transform states in Core/ReferenceArtwork and a gallery storyboard editing/save/rejection journey. Stories SHALL use deterministic existing local assets, preserve the ink/gold/serif diorama and instrument styling, and distinguish fixture publication from live behavior. Identity, child scale, offset/boundary, loading, failed-load, pending/disabled, rejection, keyboard focus and reduced-motion states SHALL be represented without game or AI services.

#### Scenario: Showcase covers the complete editor offline
- **WHEN** Storybook is built and showcase coverage runs with no game or AI server
- **THEN** the registered modal and stage artwork stories exist, the documented states are reachable and the new required family passes manifest coverage without removing existing requirements
