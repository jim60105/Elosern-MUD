# retool-concept-fill-navigation

## Why

提案的五欄值到了 wire（`bump-creation-panel-proposal-v3`），但前端三件事還沒做：`CreationOverlay.applyProposal()` 不映射新欄位（名字／背景／年齡／親和仍空白）；按下「套用概念」到提案送達之間零回饋，且完成時 `rebuildCreationDock` 把 dock stage 重置為 root、stage watcher 把玩家從概念頁籤踢回預設頁籤（玩家回報的跳頁籤 bug）；完成提示是頁籤列下一條不顯眼的 banner。設計源頭：`docs/superpowers/specs/2026-09-03-concept-proposal-expansion-toast-feedback-design.md` §4。

## What Changes

- `applyProposal()` 增五欄映射：`display_name`→名字框、`background`→背景框、`age`/`apparent_age`→年齡框（生成層已夾取，必過本地成年閘）、`affinity_elements`→親和勾選（依新種族上限裁剪後寫入）；缺席欄位維持本地值。
- 概念頁籤大載入態：送出即顯示大型 spinner 與「概念生成中，請稍候…」，textarea 與按鈕 disabled；新的 proposal revision 送達或任何非成功 result 到達時清除。
- 完成後自動跳自訂頁籤：套用到新 revision 且玩家仍在概念頁籤時 `setMode("custom")`，並經 `add-action-feedback-toasts` 的 `pushToast` API 推一條 info 確認 toast（寫入者＝表單層；失敗 crit toast 由 store 切片寫入）；面板重建／重掛重填不自動跳轉、不推 toast。
- 退役 `proposalNotice` banner、「開啟表單」按鈕與 `openCustomFromProposal()`（含兩個 testid）。
- **修復踢回 bug（改於 overlay 層）**：查證 `creationPanelSignature` 不含 `proposal` 槽，「proposal 送達→簽名變動→dock root 重置」在靜態上不成立；store 不動。修復為 overlay 的 in-flight 釘住：`conceptPending` 存活期間 stage watcher 與 `syncFromDraft` 不得改 `mode`，並以 instrumentation 重現釘死實際踢回路徑後留回歸測試。

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `concept-transient-fill`: 「The browser form pre-fills from the proposal without submitting」一條改寫——填入欄位集合增五個暫態填入鍵；完成於概念頁籤時自動切自訂頁籤（取代「確認後切換＋banner」）；重建不自動跳轉。
- `webclient-character-creation-ui`: 「The creation dock is keyboard-first, form-capable, and confirmation-protected」一條改寫——概念送出呈大型載入態並凍結重複提交；無 draft 僅 proposal 的面板不重置 dock stage。

## Impact

- `web/webclient-app/components/CreationOverlay.vue`（applyProposal、載入態、導航釘住、banner 退役）、`AppClient.vue`（新增 `:dispatch="store.view.dispatch"` 失敗比對與 `:push-toast="store.pushToast"` 成功確認寫入兩條綁定）。store 不動。
- 測試：Vitest `creation_overlay` 案擴充（五欄映射、載入態進出、自動跳轉、重建不跳）、`web/webclient-app/tests/` dock 重置案；既有引用 `creation-proposal-notice`／`creation-proposal-open` 的測試同步退役；一個瀏覽器概念旅程 class（離線降級路徑驗證載入態清除）。
- 前置：`bump-creation-panel-proposal-v3`（wire 先有新鍵）、`add-action-feedback-toasts`（toast 佇列 API）。與 `prefill-telnet-concept-from-proposal` 檔案不相交，可平行。
