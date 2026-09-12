# Proposal: webclient-gallery-ui

## Why

The gallery panel payload and the six management actions complete the
server side of the 角色肖像圖庫管理頁, but no Vue surface exists: the mockups
(`docs/design/elosern-redesign2/角色肖像圖庫管理頁-*.webp`) show a gallery main
page with filter tabs / sort / grid-list toggle and a 肖像詳情 rail, a
生成新圖 drawer, a 裝備綁定 drawer, and a 臉部框選 modal. Design §12.4's
frontend gap closes only when the committed panel is rendered and the committed
actions are dispatched — under the committed contract that the client renders
panels verbatim and emits only user-intent dispatches.

## What Changes

- New Vue surface family mounted as a full drawer/overlay from the existing
  dock/overlay host, driven ONLY by the committed `gallery` panel:
  - `GalleryPanel` — header (角色肖像圖庫 copy from the payload), subject rail
    (puppet first, active-party companions already ordered server-side),
    filter tabs 全部/預設/已綁定/生成中/失敗 rendered from the committed counts,
    最新優先 sort label + grid/list toggle (client-local view state only, like
    art focus), card grid: cover image cropped through the shared
    `face-rect.js` mapping, server chips, 目前預設 crown badge, spinner card
    for pending rows, failed card carrying 「暫時無法生成，稍後再試」.
  - `GalleryDetailRail` — 肖像詳情: preview, committed badges, 綁定條件 rows,
    當前狀態 line, 設為預設 / 編輯設定 / 刪除 affordances, 生成新圖 CTA; the
    affordances open the drawers below and dispatch only committed actions.
  - `GalleryGenerateDrawer` — 納入生成的資料 checkboxes over the committed
    catalog (角色外貌描述/主手武器/副手武器/防具/飾品 with 已選 n / 5 derived from
    the committed field list), 目前裝備摘要 strip from `equipment_summary`
    (from角色資料檢視 links the character drawer), 補充提示詞 textarea with the
    512 code-point counter (client-local character count only; the server owns
    rejection), 取消 / 開始生成.
  - `GalleryBindingDrawer` — per-slot enable checkboxes over the committed
    slot vocabulary, per-slot display restricted to the currently-equipped
    value or the empty-slot state (never an item picker — payload carries slot
    ids only), 目前綁定條件 summary, 規則重疊提醒 panel rendered verbatim from
    `binding_warnings` with 查看 jump (selects that card client-side), 取消 /
    儲存綁定.
  - `GalleryFaceRectModal` — draggable/resizable rect over the ORIGINAL image
    (the card's committed URL), 圖片資訊 block from committed facts, 方形裁切
    預覽（1:1） client-side crop preview of the same image, 取消 / 儲存框選
    dispatching `gallery.face_rect.update`; the rect maps to the payload's
    normalized x/y/w/h form client-side, validated locally only to prevent
    nonsense dispatches (the server re-validates verbatim).
  - Deletion is confirmation-gated in the rail before dispatching
    `gallery.card.delete`.
- All five mutations dispatch through the single existing dispatch entry with
  its connected/locked/one-in-flight gates; the client renders server rejections
  verbatim (existing non-success-message requirement) and NEVER synthesizes
  gallery facts (no client-side chips, counts, overlap rules, sort by
  anything, or equipment reading).
- Vitest coverage per component (render-from-payload, dispatch-on-intent,
  verbatim rejection, keyboard/Escape/focus-trap parity with existing drawers),
  plus Storybook stories with offline fixtures for every new component.
- Governed manifest growth: the new component families are appended to the
  frozen `web/webclient-app/component-manifest.json` required set as this
  change's own named scope, and `AppClient.vue` mounts the family on the
  committed panel's availability.

## Capabilities

### New Capabilities

- `webclient-gallery-ui`: the Vue gallery surface — verbatim-render contract,
  per-component behavior (tabs, cards, rail, drawers, face-rect modal,
  confirm-gated delete), client-local view state boundaries, dispatch-only
  mutation, zh-TW copy vocabulary matching the mockups, and accessibility.

### Modified Capabilities

- `webclient-component-showcase`: the frozen required-component manifest grows
  by the named gallery families through this change's governed-growth clause;
  every new family ships stories with offline deterministic data.

## Impact

- New components under `web/webclient-app/components/` (Gallery*.vue plus the
  face-rect drag logic as a pure JS lib beside `face-rect.js`), Vitest files
  under `tests/components/`, stories under `stories/`,
  `component-manifest.json` appended, `AppClient.vue` wiring +
  `tests/app_client_gallery.test.js`.
- No Python, no protocol, no action changes — consumes `webclient-gallery-panel`
  and `webclient-gallery-actions` payloads/actions by committed name.
- Storybook static build + showcase-coverage gate stay green via the manifest
  append in the same change.

## Batch:

- depends-on: webclient-gallery-panel, webclient-gallery-actions
- Code-conflict notes: owns `web/webclient-app/**` (components, tests, stories,
  `component-manifest.json`, `AppClient.vue`) — disjoint from both backend
  changes. Reads (never edits) `web/static/webclient/js/elosern/protocol.js`
  mirrored bounds.
