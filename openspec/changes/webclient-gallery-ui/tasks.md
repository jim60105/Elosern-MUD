# Tasks: webclient-gallery-ui

## 1. Components (all render committed `gallery` payload only)

- [ ] 1.1 `components/GalleryPanel.vue`: header copy, subject rail, filter tabs
  from committed counts (tab filters by row status / `binding_present` /
  `is_default` facts), 最新優先 label, grid/list toggle (client-local), card
  grid with cover image via `face-rect.js` `faceObjectPosition()`, server chips,
  crown badge, pending spinner card, failed card; emits
  `select-subject` / `select-card` / action-intent events only.
- [ ] 1.2 `components/GalleryDetailRail.vue`: preview, badges, 綁定條件,
  當前狀態, 設為預設 / 編輯設定 / 刪除 (in-rail confirm step) / 生成新圖 CTA;
  capability-flag-gated affordances (monster: no binding editor).
- [ ] 1.3 `components/GalleryGenerateDrawer.vue`: five catalog checkboxes +
  已選 n / 5, 目前裝備摘要 strip (+ 從角色資料檢視 opening the character
  drawer), 補充提示詞 textarea with cosmetic n / 512 counter, 取消 / 開始生成;
  focus-trap + Escape parity.
- [ ] 1.4 `components/GalleryBindingDrawer.vue`: per-slot enable checkboxes;
  enabled slot displays ONLY the committed current value or 未裝備/empty state;
  目前綁定條件 summary; 規則重疊提醒 from `binding_warnings` with 查看 jump;
  取消 / 儲存綁定 (payload: enabled slot ids + committed image_id).
- [ ] 1.5 `components/GalleryFaceRectModal.vue` + pure
  `components/face-rect-edit.js` (drag/resize → normalized {x,y,w,h}, local
  clamp to positive area within [0,1]): 原始圖片 layer over the committed URL,
  圖片資訊 block, 方形裁切預覽（1:1） CSS cover crop of the same image,
  取消 / 儲存框選.
- [ ] 1.6 Static zh-TW copy constants exactly matching the mockups (full-width
  punctuation); no client-side chips/counts/overlap/sort logic by construction
  (grep-clean the family for recomputation).

## 2. Wiring

- [ ] 2.1 `AppClient.vue`: mount the family via the existing overlay host when
  the committed `gallery` panel is available; wire every intent to the single
  dispatch entry with the six committed action ids; non-success messages surface
  verbatim through the existing narrative error path.
- [ ] 2.2 Delete flows through the in-rail confirm before dispatch.

## 3. Tests (Vitest, deterministic)

- [ ] 3.1 `tests/components/` per component: renders every committed fact
  (chips, counts, crown, pending, failed, warnings) from a fixed payload
  fixture; dispatches the exact one action per intent; confirmation gates
  delete; oversized-input still dispatches raw text (server owns the bound);
  Escape/focus parity; no facts synthesized (payload-stripped fixtures render
  empty, never invented content).
- [ ] 3.2 `tests/app_client_gallery.test.js`: mount-on-availability, gate
  behavior while unavailable, verbatim rejection surfacing.

## 4. Showcase growth (same change)

- [ ] 4.1 Stories with deterministic offline fixtures:
  `Data/GalleryPanel`, `Data/GalleryDetailRail`, `Overlays/GalleryGenerateDrawer`,
  `Overlays/GalleryBindingDrawer`, `Overlays/GalleryFaceRectModal` (representative
  `args:` per story).
- [ ] 4.2 Append the five titles to `web/webclient-app/component-manifest.json`
  (frozen set re-frozen at the new complete set); `pnpm run showcase-coverage`
  green; no component mounts before its story exists.
