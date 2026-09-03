# remove-creation-overlay-close-control Tasks

## 1. 移除死控制項

- [ ] 1.1 `web/webclient-app/components/CreationOverlay.vue`：刪除 header 內的關閉 button（`:607-615`，含 `data-testid="creation-overlay-close"` 與 `.creation-overlay__close` class），header 只留 `creation-overlay__title`；`.creation-overlay__header` 的 flex 規則不動（單一子元素下 `space-between` 等同 `flex-start`）。
- [ ] 1.2 同檔：刪除 `close()` 函式（`:533-535`）與 `defineEmits` 中的 `"close"` 項（`:51`，改為 `["action", "request-reset", "cancel-confirm"]`）。
- [ ] 1.3 全域確認無殘留：`grep -rn "creation-overlay-close\|creation-overlay__close" web/ docs/ scripts/ .storybook/` 只應剩下 2.1／2.2 要改的測試檔；`AppClient.vue` 不動（本來就沒綁 `@close`）。

## 2. 測試同步（負向契約）

- [ ] 2.1 `web/webclient-app/tests/overlays/creation_overlay.test.js`：刪除 `"the close button emits close"` 案（`:498-503`）。`"open=false hides the overlay"` 案保留不動（`open` prop 依 design D4 保留）。
- [ ] 2.2 `web/webclient-app/tests/overlays/deferred_surfaces_absent.test.js`：把創建 overlay 案（`:394-402`）改名為表達意圖的形式（例：`"the creation overlay renders its own testids and no dismissal control"`），並把 `creation-overlay-close` 的存在斷言**翻轉為不存在斷言**；補一行註解說明理由（呈現由伺服器擁有的 `creation` 面板述詞決定，創建模式背後無畫面可回落，關閉控制項無結果）。
- [ ] 2.3 同檔（**必做，非選擇性**）：把 `:363` 的 `describe("H6 overlay reachability: every full overlay has a live trigger")` 改名，鏡射 delta spec 改名後的 scenario「live mount path」語彙。本變更一落地，「每個 overlay 都有 trigger」對創建 overlay 就是假的——而這個檔案正是釘住新契約的回歸守門，套件標題不得與同檔剛釘下的負向斷言自相矛盾。

## 3. 驗證

- [ ] 3.1 `npm test -- overlays` 綠（此即 `webclient-component-showcase` full-overlays requirement 的 Python 證據 `test_vue_showcase_overlays_evidence.py::test_vitest_overlays_family_suite_passes` 所執行的門檻）。
- [ ] 3.2 `npm test` 全套綠；`node scripts/component-coverage.mjs` 綠（manifest 與 story 標題不變，應無影響）。
- [ ] 3.3 Storybook 目視確認：`Overlays/CreationOverlay` 的 `Default`／`CustomDraft`／`ConceptMode` 三個 story，header 只剩標題、無跑版、無孤兒空白。
- [ ] 3.4 `uv run --locked python -m tools.spec_traceability check` 綠：requirement 標題未改，故歸檔前後的預期輸出皆為 **1195 requirements、0 uncovered、0 errors**，requirement 總數不變；`openspec validate remove-creation-overlay-close-control --strict` 綠。
