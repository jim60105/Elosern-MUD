# Delta spec: webclient-gallery-ui (webclient-gallery-ui)

## ADDED Requirements

### Requirement: The gallery surface renders only committed panel facts

The Vue application SHALL render the 角色肖像圖庫 management surface from the
committed `gallery` panel only: subject rail, filter-tab labels and counts,
card order, chips, crown (「目前預設」), pending spinner rows, failed rows
(「暫時無法生成，稍後再試」), card labels, equipment summary, binding conditions,
and overlap warnings SHALL come verbatim from the payload. The client SHALL NOT
compose chips or labels, compute filter counts or overlap rules, read
equipment state, or re-sort rows (list order is payload order; the tab FILTERS
by the committed row status/`binding_present`/`is_default` facts). The
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

### Requirement: The detail rail presents the selected card and gates destructive intent

The 肖像詳情 rail SHALL show the selected card's preview (cover-cropped through
the shared `face-rect.js` mapping), committed badges, 綁定條件 rows, 當前狀態
line, and the affordances 設為預設 / 編輯設定 / 刪除 plus the 生成新圖 CTA.
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

納入生成的資料 SHALL render exactly the committed field vocabulary —
角色外貌描述 / 主手武器 / 副手武器 / 防具 / 飾品 — with the 已選 n / 5 counter
derived from the client-local checkbox set only. 目前裝備摘要 SHALL render the
committed `equipment_summary` (per-slot equipped display name or 未裝備; the
accessories count line). 補充提示詞 SHALL be a textarea whose n / 512 counter
is cosmetic; on submit the surface SHALL dispatch exactly one
`gallery.generate` with the selected catalog ids and the raw text, SHALL close
on the published panel showing the pending row, and SHALL surface any server
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

臉部框選 SHALL overlay a draggable/resizable rectangle on the card's committed
image, show the 圖片資訊 block from committed facts (card label, filename or
identifier, timestamp, pixel size when committed), and a 方形裁切預覽（1:1）
produced by cover-cropping the SAME image to the rect (no second image, no
upload of pixels). On 儲存框選 the rect SHALL normalize to `{x, y, w, h}` in
[0,1] with positive area (locally clamped only to prevent nonsense dispatches)
and dispatch exactly one `gallery.face_rect.update`. Escape/取消 discards
without a dispatch.

#### Scenario: The stored rect equals the modal's normalized rect

- **WHEN** a rect is saved
- **THEN** the dispatched face_rect matches the modal geometry within float tolerance and the payload carries no image data

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
