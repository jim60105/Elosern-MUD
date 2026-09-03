# add-action-feedback-toasts — Design

## Context

現狀（實讀）：SPA 無 toast 元件。非成功動作結果的訊息在 `stores/elosern.js` 的 `handleActionResult` 於 `!creationOverlayPresenting(rs)` 時走敘事 feed 單行（`webclient-action-result-feedback` D-A/D-B）；創角 overlay 掛載時由 overlay 自己的 `creation-result-message` 區顯示。`tokens.css` 已定義 `@keyframes elosern-toast-in`（`tokens.css:182`）但零消費者。`deferred_surfaces_absent.test.js` 把 `toast-`/`event-log-` testid 與 `/\bToasts?\b/i` 標題模式列為「無後端讀取模型支撐的延後表面」而禁止。

result 物件按 `protocol.js` 契約自帶 `request_id`/`outcome`/`code`/`message`/`epoch`，store 另有 `lastSubmittedRequestId`（view 已暴露為 `dispatch.submittedRequestId`）——「同 request」比對可判定（rubber-duck 發現 6 的實證）。

設計出處 §3 定位：動作回饋 toast 是**純客戶端本地狀態**（動作的送出／完成／失敗回執），不需要後端 OOB 讀取模型——與被禁止的「event-log 遊戲事件 toast」是兩回事。本變更落地前者、改寫後者的禁令表述、為後者留插入點。

約束：Pinia store 是 view 狀態唯一寫入者（D3）；敘事 feed 非成功單行與 overlay result 區契約不動（toast 疊加、不取代）；元件只渲染 OOB panel／文字流／客戶端本地狀態——toast 內容屬客戶端本地（組字或伺服端訊息逐字），合法。

## Goals / Non-Goals

**Goals:**

- 通用 `ToastQueue.vue` + store toast 切片（FIFO 上限 4、自動消失、點擊關閉、tone）。
- `creation.concept` 失敗 crit toast 第一期觸發（成功確認 toast 歸 `retool-concept-fill-navigation` 的表單層，見 D3）。
- 凍結測試改寫：`feedback-` 合法、事件 toast（讀模型綁定）仍禁；showcase manifest 重凍結含 `ToastQueue`。

**Non-Goals:**

- 遊戲事件 toast 的伺服端事件匯流排與 `event-log` OOB panel（使用者已確認本期不做）；把既有敘事 feed 非成功通道遷移到 toast（保留雙通道）；`creation.concept` 之外 action 的結果觸發點擴充（僅 concept）。

## Decisions

### D1: 佇列是 store 切片，元件被動渲染

`stores/elosern.js` 維護 `toasts` 陣列（客戶端本地，不入 `reducer` 提交快照、不持久化）與 `pushToast`/`dismissToast`；`view` 切片暴露唯讀 `toasts`。自動消失用 `setTimeout`（store 驅動便於無 UI 測試——測試直接呼叫 `pushToast` 後跑假時鐘斷言出列）。上限 4、FIFO、`tone ∈ {"info","crit"}`。

- 替代方案（元件本地佇列 + provide/inject）：被否——違反「store 是 view 狀態唯一寫入者」；多處 `pushToast` 需求（overlay、store 內部結果處理）需要單一入口。

### D2: 掛載層級在 overlay 之上

`ToastQueue` 掛 `AppClient.vue` 根層、z-index 高於 creation overlay——創角期間 toast（本變更第一期主場景）必須可見，否則「套用概念」回饋仍被 overlay 遮擋，問題不解。

### D3: 失敗 crit toast 放 store；成功 info toast 歸表單層（單寫入者契約）

**寫入者所有權（rubber-duck 發現 1）**：

- 本切片只寫**非成功**結果的 crit toast。`handleActionResult` 認得 `creation.concept` 的 matched result（`inFlight.handledResult` 指紋去重）：非成功 → `pushToast(crit, 伺服端訊息逐字 or 雙鍵 fallback)`；同一 result 重複觀測不重複推。
- **成功**確認 toast 由 `retool-concept-fill-navigation` 的 `CreationOverlay.applyProposal()` 在套用新 revision 且載入態（`conceptPending`）存活時經 `pushToast` 寫入——只有套用时點同時知道「落地成功＋導航脈絡」，revision 守門天然冪等、天然單次。
- 原「store 推通用成功 info＋overlay 事後抑制」方案作廢：store 在 result commit 時同步推播，overlay 無法追溯抑制；`creationOverlayPresenting` 只測面板掛載，測不出「完成於概念頁」。兩條 toast 各自單點寫入、零抑制協議。
- 邊界（已接受）：成功結果送達但表單从未套用（overlay 未掛載）時無成功 toast——成功語境（提案填入表單）確實未發生，feed/result 區通道不受影響。
- **觸發集恆等式**：crit toast 的觸發集與 feed-line 的觸發集逐字相同（同去重、同非成功判準），差別僅在呈现層。`creation.custom`／`creation.preset` 的 `stale` 例外維持 feed-only（確認面板為自有結果 surface），toast 同樣排除——兩通道由同一分支決定，不容各寫各的判準。

- 替代方案（store 寫全部成功／失敗 toast）：被否——需要跨切片抑制協議與「完成於概念頁」判定，兩者在 store 層都拿不到可靠信號。

### D4: 凍結測試改寫的精確表述

`deferred_surfaces_absent.test.js`：移除 `/\bToasts?\b/i`（`DEFERRED_TITLE_PATTERNS`）；`toast-` testid 前綴保留於延後清單（語意縮窄為「綁定 event-log 讀模型的遊戲事件 toast」）；新增斷言 `feedback-` 前綴必須存在且只綁定客戶端本地佇列（無 OOB 讀取模型欄位）。showcase 主規格改寫：必需清單增 `ToastQueue`；「event-log Toasts surface」延後條目保留、但補一句「客戶端動作回饋 toast（`feedback-`）非該延後表面」以消歧義。

### D5: 孤兒 keyframes 收編

`elosern-toast-in` 由 `ToastQueue` 消費；`prefers-reduced-motion` 路徑沿用既有 motion token 慣例（動畫可關）。預期 `tokens.css` 零改動（僅新增消費者）。

### D6: 防膨脹契約用行為斷言驗證

toast 佇列與計數器皆為 store-local 純顯示態——不進 `getState()`（快照不含）、不入 localStorage、不觸發任何 action dispatch。驗證走行為斷言：push/dismiss 前後 `getState()` 深度相等、localStorage 無寫入（vi spy）、快照鍵集合不變；不用原始檔掃描（掃描斷言證偽於重命名而非證實於行為，rubber-duck 發現 7）。

## Risks / Trade-offs

- [雙通道訊息重複（feed 單行 + crit toast）] → 刻意設計：toast 是額外的可發現性層，feed 契約不動；去重只在各自通道內。
- [store Timer 在卸載後回調] → `dismissToast`/epoch 重置路徑一律 `clearTimeout`；Vitest 假時鐘驗證無殭屍出列。
- [A3 同檔改動衝突] → 落地順序 A5 先、A3 後；A3 實作者 rebase 後才動 `rebuildCreationDock` 區塊。

## Migration Plan

新元件＋新 store 切片，無資料遷移；回滾＝移除掛載與觸發呼叫。

## Open Questions

（無。）

## 跨變更介面

| 物件 | 擁有者 | 消費者 |
|---|---|---|
| `pushToast/dismissToast`（佇列 API） | add-action-feedback-toasts（store） | StageHud 計數器、ToastQueue.vue、CreationOverlay（成功確認 toast 經 `pushToast`） |
| 概念成功確認 toast（唯一寫入點） | retool-concept-fill-navigation（`applyProposal()`） | ToastQueue 渲染 |
| 概念失敗 crit toast（唯一寫入點） | add-action-feedback-toasts（`handleActionResult`） | ToastQueue 渲染 |
| `creation.view.stage`（「完成於概念頁」判定） | 現有 store | CreationOverlay（A3 導航） |
| `toastIn` 動畫 keyframe | bump（tokens.css） | ToastQueue.vue |
