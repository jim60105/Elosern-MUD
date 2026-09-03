# remove-creation-overlay-close-control

## Why

角色創建 overlay 右上角的「✕ 關閉」是一個死控制項：`CreationOverlay.vue:611` 的 `@click="close"` 只做 `emit("close")`（:533-535），而應用端唯一的消費者 `AppClient.vue:990-1001` 只綁了 `@action`／`@request-reset`／`@cancel-confirm`，**沒有綁 `@close`**，事件無人接收，玩家按下去零反應（玩家回報）。

而且這個 overlay 的存在與否由伺服器擁有——`AppClient.vue:990` 以 `v-if="panelAvailable('creation')"` 掛載，對應 store 的 `creationOverlayPresenting`（`stores/elosern.js:985`）——創建模式背後沒有探索畫面，關掉只會露出空殼客戶端。所以「把 `@close` 接上」不是修法：那會造出一個真的能把玩家丟進無介面狀態的出口。既有 showcase 契約已寫明「無結果的控制項不得渲染」（`webclient-component-showcase` 的 full-overlays requirement），移除才是與契約一致的解。

## What Changes

- 刪除 `CreationOverlay.vue` 的關閉控制項：button markup（:607-615，含 testid `creation-overlay-close`）、`close()` 函式（:533-535）、`defineEmits` 中的 `"close"` 項（:51）。overlay 的 header 僅保留標題。
- 測試同步：`tests/overlays/creation_overlay.test.js` 的 `"the close button emits close"` 案刪除；`tests/overlays/deferred_surfaces_absent.test.js` 的創建 overlay 案改名並把關閉控制項的存在斷言**翻轉為不存在斷言**，把「創建面不提供前端關閉出口」釘成回歸測試。
- spec 契約補強：`webclient-component-showcase` 的 full-overlays requirement 明文寫入「創建 overlay 不渲染任何前端關閉／離開控制項」，附一條 scenario。

**非目標**（明確不做，理由見 design）：不接 `@close`、不新增 Escape 關閉路徑、不動 `AppClient.vue` 的掛載述詞、不動 `open` prop、不動任何 `creation.*` 動作或 store。

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `webclient-component-showcase`: 「The full overlays are complete, the deferred surfaces are absent, and the manifest is frozen」一條改寫——creation overlay 的段落補上「不渲染前端關閉／離開控制項；其呈現由伺服器擁有的 `creation` 面板述詞決定」，並新增一條 scenario 釘住無關閉控制項。

## Impact

- 程式碼：`web/webclient-app/components/CreationOverlay.vue` 單檔（markup + script）。**已查證無樣式需刪**：`.creation-overlay__close` 這個 class 只出現在 template（:609），SFC 的 `<style scoped>` 區塊（:889-1120，所有 `.creation-overlay__*` 版面規則的所在）沒有對應規則——按鈕的 chrome 全部來自 `styles/tokens.css` 的 `.ui-btn`，本地樣式只補版面（見 `:916-917` 註解）。`.creation-overlay__header`（`:901-907`）的 `justify-content: space-between` 在單一子元素下等同 `flex-start`，標題維持靠左，視覺不變。
- 測試：`web/webclient-app/tests/overlays/creation_overlay.test.js`、`web/webclient-app/tests/overlays/deferred_surfaces_absent.test.js`。**已查證** `web/tests/browser/` 的 Playwright 套件只選 `[data-testid="creation-overlay"]`，不碰關閉按鈕，故瀏覽器層零改動。
- Traceability：刻意改寫既有 requirement 而非新增一條——每條 main-spec requirement 都必須有 Python `@covers_requirement` 證據（現況 1195/1195 全覆蓋），而既有證據 `web/webclient/tests/test_vue_showcase_overlays_evidence.py::test_vitest_overlays_family_suite_passes` 直接執行 overlays vitest 套件，改寫既有條目即自動沿用覆蓋，不新增未覆蓋條目。
- 相依與衝突：無上游相依。與 `openspec/changes/` 中任何進行中變更不相交（目前僅有 `archive/`）。`CreationOverlay.vue` 是近期熱點檔（`0c5b57b`、`6d04c44`），但本變更只刪三處互不重疊的片段，可獨立進行。
- 玩家可見影響：創建畫面右上角不再有按鈕。**無功能損失**——該控制項從 `baa4788` 引入起就從未接線過。
