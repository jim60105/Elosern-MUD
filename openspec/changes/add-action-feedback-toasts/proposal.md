# add-action-feedback-toasts

## Why

WebClient 目前沒有 toast 系統：動作結果的非成功訊息在創角 overlay 掛載時只落在 overlay 自己的 result 區，玩家按下「套用概念」後既看不到成功確認、也沒有一處可掛「生成中／已完成」的高可見度回饋。`tokens.css` 的 `@keyframes elosern-toast-in` 是無人消費的孤兒動畫；redesign 設計稿（`docs/design/elosern-redesign/REDESIGN.md`）本來就把通知 toast 列為設計表面，當時因「無 `event-log` 讀取模型」被 roadmap 延後——但**動作回饋 toast 是純客戶端本地狀態，本就不需要後端讀取模型**。設計源頭：`docs/superpowers/specs/2026-09-03-concept-proposal-expansion-toast-feedback-design.md` §3。

## What Changes

- 新元件 `web/webclient-app/components/ToastQueue.vue`：右上錨定堆疊（對齊 redesign `.toasts` 規格），逐條含標題與可選副行，`tone: "crit"` 用 seal 紅左緣；點擊關閉；入場復用 `elosern-toast-in`；testid 前綴 `feedback-`。
- Pinia store（`stores/elosern.js`）新增 toast 佇列切片：條目 `{ id, title, sub?, tone }`、FIFO 上限 4（超出最舊立即出列）、預設 5200 ms 自動淡出、`pushToast`/`dismissToast` 寫入介面；不持久化、不進敘事 feed。
- 第一期觸發點僅 `creation.concept`，採單寫入者契約：非成功 → crit toast（伺服端訊息逐字作 title），由 store 在結果認可時寫入；成功 → info toast「概念提案已套用」，由 `retool-concept-fill-navigation` 的 `applyProposal()` 在套用提案時經 `pushToast` 寫入（store 不推成功 toast，無跨切片抑制協議）。既有敘事 feed 非成功單行語意（webclient-action-result-feedback）與 overlay result 區契約**不變**——toast 是疊加的可發現性，不取代任何既有通道。
- 凍結契約改寫（非稀釋）：`deferred_surfaces_absent.test.js` 的 toast 禁令重述為「禁的是無資料綁定的後端讀取模型 surface」；`feedback-` testid 合法、遊戲事件 toast（`toast-` 前綴 + event-log 綁定）在讀模型落地前仍禁；`DEFERRED_TITLE_PATTERNS` 移除 `/Toasts?/i`；`event-log-`／`companion-`／`objective-` 缺席斷言原樣保留。
- `ToastQueue.vue` 進 Storybook showcase 必需清單（manifest 重凍結）與 `docs/development/webclient-vue-frozen-contract-audit.md` 同步。**範圍決策（使用者已確認）**：遊戲事件 toast（升級／任務／解鎖／金錢）所需的伺服端事件匯流排與 `event-log` OOB panel 不在本期；佇列介面預留事件插入點。

## Capabilities

### New Capabilities

- `webclient-action-feedback`: 客戶端動作回饋 toast 佇列——條目形狀、FIFO 上限、自動消失、點擊關閉、tone 語彙、`creation.concept` 觸發契約、與既有敘事 feed／overlay result 通道的疊加（非取代）關係、遊戲事件通道的介面預留。

### Modified Capabilities

- `webclient-component-showcase`: 必需元件清單增 `ToastQueue`（含 story 與 fixture）；「延後表面缺席而非偽裝」條目改寫——動作回饋 toast 列為已落地表面，事件 toast 綁定讀模型的禁令改以 testid 前綴（`toast-`／`event-log-`）表述。

## Impact

- `web/webclient-app/components/ToastQueue.vue`（新）、`web/webclient-app/AppClient.vue`（掛載於 overlay 之上層）、`web/webclient-app/stores/elosern.js`（toast 切片 + `handleActionResult` 觸發點）、`web/webclient-app/styles/tokens.css`（復用既有 keyframes，預期零改動）、stories + showcase manifest、`tests/overlays/deferred_surfaces_absent.test.js`。
- 測試：Vitest ToastQueue 案（佇列上限／FIFO／自動消失／點擊關閉／concept 觸發）、掛載可見性案（overlay 之上 z-index）。
- 無伺服端改動、無 OOB 協定改動（`webclient-oob-protocol` 不變）。與 `extend-concept-proposal-fields`／`bump-creation-panel-proposal-v3`／`prefill-telnet-concept-from-proposal` 完全不相交，可平行；`retool-concept-fill-navigation` 依賴本變更為前置（共用 `pushToast` API；兩者皆觸及 `AppClient.vue` 但為不同區塊，A3 須於本變更落地後 rebase）。
