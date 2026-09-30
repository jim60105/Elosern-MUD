## MODIFIED Requirements

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

### Requirement: The face-rect modal stores geometry over the original image

臉部框選 SHALL overlay a draggable/resizable rectangle on the card's committed
image, show the 圖片資訊 block from committed facts (card label, filename or
identifier, the exact local date and time of `created_at` (日期不詳 when impossible), pixel size when committed), and a 方形裁切預覽（1:1）
produced by cover-cropping the SAME image to the rect (no second image, no
upload of pixels). On 儲存框選 the rect SHALL normalize to `{x, y, w, h}` in
[0,1] with positive area (locally clamped only to prevent nonsense dispatches)
and dispatch exactly one `gallery.face_rect.update`. Escape/取消 discards
without a dispatch.

#### Scenario: The stored rect equals the modal's normalized rect

- **WHEN** a rect is saved
- **THEN** the dispatched face_rect matches the modal geometry within float tolerance and the payload carries no image data
