# Design: webclient-gallery-ui

## D1 — Committed-panel-only rendering

Every string the surface shows except static chrome labels comes from the
committed `gallery` payload: chip lists, filter counts, card labels, crown,
failed/pending states, equipment summary, binding conditions, overlap warnings.
The client reads panels by key (established practice) and performs no
`schema_version` re-check beyond the protocol validator that already gates the
store. The zh-TW copy of the chrome (headers, button captions, drawer titles,
field labels, notes) is a static component vocabulary matching the mockups
verbatim: 角色肖像圖庫, 生成新圖, 全部/預設/已綁定/生成中/失敗, 最新優先, 肖像詳情,
設為預設, 編輯設定, 刪除, 納入生成的資料, 目前裝備摘要, 補充提示詞, 開始生成,
裝備綁定, 裝備條件設定, 目前綁定條件, 規則重疊提醒, 儲存綁定, 臉部框選, 原始圖片,
圖片資訊, 方形裁切預覽（1:1）, 儲存框選, 取消。Full-width punctuation as in the
mockups.

## D2 — Client-local view state is exactly three things

Filter-tab selection, grid/list view, and the open subject/card/editor
selection are client-local (the art-focus precedent). Order and counts always
come from the payload; the tab FILTERS the committed rows by the committed
row-status/fact fields (never by re-derived semantics: a row is 已綁定 iff
`binding_present`). Sort stays server order (newest-first); the 最新優先 control
is a committed-fact label, not a re-sort.

## D3 — One dispatch entry, intent only

Each control dispatches exactly one committed action: subject-select on a rail
row, `gallery.generate` from the drawer's submit, `gallery.default.set`,
`gallery.card.delete` (only after an in-rail confirmation step),
`gallery.binding.save` (enabled slot ids only), `gallery.face_rect.update`
(normalized rect). All through the single dispatch entry with its connected /
locked / one-in-flight gates; non-success results surface the server message
verbatim through the existing narrative path. No control composes a payload
field the panel didn't authorize (e.g. the binding drawer can only enable slots
the payload lists; the generate drawer's counter is cosmetic — the server owns
the 512 bound).

## D4 — Face-rect modal is geometry, not image processing

The modal overlays a draggable/resizable rect on the committed card URL image;
preview is the same `<img>` cover-cropped to 1:1 at the rect (pure CSS /
`face-rect.js` vocabulary). The rect normalizes to `{x, y, w, h}` in [0,1] on
dispatch. Local validation only enforces positive area and [0,1] containment to
avoid nonsense dispatches; the server re-validates verbatim and is the sole
authority (no crop is ever uploaded — D9).

## D5 — Failure states are rendered, not hidden

Pending rows render the spinner card with the committed 生成中 label; failed
rows render 「暫時無法生成，稍後再試」 with the committed code hidden behind an
accessible detail. AI-offline therefore shows exactly the mockup's failed-card
state. The 生成中 refresh needs no client polling: settled jobs push the panel
through the existing presentation publication path.

## D6 — Governed manifest growth

The showcase manifest is frozen; this change names its growth as its own scope
(the governed-redesign clause): required titles `Data/GalleryPanel`,
`Data/GalleryDetailRail`, `Overlays/GalleryGenerateDrawer`,
`Overlays/GalleryBindingDrawer`, `Overlays/GalleryFaceRectModal` are appended in
the same change that ships their stories, keeping `pnpm run showcase-coverage`
green. The family mounts in `AppClient.vue` on the committed panel's
availability via the existing overlay host.

## D7 — Accessibility and keyboard parity

Drawers/modal follow the existing focus-trap + Escape + restore-focus parity
(the CreationOverlay/MapOverlay precedent); cards and rail rows are
keyboard-actionable with visible focus; the crown and failure states never rely
on color alone (explicit text). Desktop-only, matching the app contract.
