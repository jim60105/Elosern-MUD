# retool-concept-fill-navigation — Design

## Context

`CreationOverlay.vue` 現狀（查證）：`mode` ref 為本地頁籤狀態（preset/custom/concept）；`applyProposal()` 只映射 race/subrace/allocations/persona；`watch(props.stage)` 以「stage 值變動」守門鏡設 mode；`syncFromDraft()` 的無 draft 分支以 `formTouched`＋stage 守門。store 側查證（rubber-duck finding 2）：`creationPanelSignature` 只序列化 presets／races／draft——**不含 proposal**，因此「proposal-only 面板重發導致簽名變動→root 重置」這條原始假設在靜態上走不通；踢頁籤的真實路徑（watcher 值變動、draft deep-watch、或 router settle 副作用）必須先以受 instrumentation 的瀏覽器重現釘死，修復選在 causally robust 的層。完成提示是頁籤列下方的 `proposalNotice` banner +「開啟表單」按鈕（`openCustomFromProposal()` 切 custom）。送出後無任何 in-flight 回饋。

上游：panel v3 的 `proposal` 槽已帶五個 optional 鍵（缺席＝鍵不存在）；ToastQueue 佇列（`add-action-feedback-toasts`）提供 `pushToast`。

約束：store 是 view 狀態唯一寫入者（Pinia D3）——但 overlay 的頁籤 `mode` 本就是 overlay 本地狀態（現狀即如此），導航修復選在 overlay 層做、store 只改「不動」的條件；revision 守門（重建不覆寫編輯、新套用必替換）不可破壞；傳輸層 single-mutation-in-flight 不動。

## Goals / Non-Goals

**Goals:**

- 五欄映射進表單；缺席欄位不動本地值。
- 概念頁籤大型載入態（spinner + 文案 + disabled），完成或失敗即清除。
- 完成自動跳 custom（僅「完成於概念頁籤」）；banner 退役。
- in-flight 期間頁籤釘住：載入態存活的整個窗口，任何 store 發布／draft 重同步都不得移動 `mode`。

**Non-Goals:**

- toast 佇列本體（owned by `add-action-feedback-toasts`）；Telnet 流（owned by `prefill-telnet-concept-from-proposal`）；生成層／wire（owned by 上游兩變更）。

## Decisions

### D1: 載入態是 overlay 本地狀態，錨在「送出→settled」窗口，比對用 `submittedRequestId`

`applyConcept()` 設 `conceptPending = true` 並送 action。清除路徑二選一先到：(a) `applyProposal()` 套用了大於已套用序號的新 revision；(b) 本次 request 的非成功 result——比對式明定为 `props.result.requestId === props.dispatch.submittedRequestId && props.result.outcome !== "success"`（傳輸層 single-mutation-in-flight 保證 pending 期間不可能有別的 request 成為 submitted；舊 result 快取重播因 requestId 不符而無效）。overlay 需新增 `:dispatch="store.view.dispatch"` 綁取既有 `submittedRequestId`（AppClient 一处新 prop；overlay 現行 emit 路徑拿不到 request id，rubber-duck finding 6）。spinner／文案／disabled 全掛 `conceptPending`。掛載時初值為假＝斷線／重掛自然清除（既有已接受代價：玩家重按）。

- 替代方案（下傳 store `dispatch.inFlight`）：被否——in-flight 是全域單調度狀態，任何 action 都會點亮它，語義比「概念送出中」寬；本地錨定窗更精確且少動 props 面。

### D2: 導航修復選在 overlay 的 in-flight 釘住；不動 `rebuildCreationDock`

原計畫在 `rebuildCreationDock` root-reset 分支前加「無 draft 且帶 proposal → skip」條件，查證後作廢：該分支只在 `panelSig` 變動時進入，而簽名按設計不含 proposal（stores/elosern.js `creationPanelSignature` 只序列化 presets/races/draft），條件在目標場景根本不會被評估，屬無效修復。本變更改為 overlay 層釘住：`conceptPending === true` 時 stage watcher 與 `syncFromDraft` 直接 early-return，不觸碰 `mode`；完成導航由 `applyProposal()` 明確執行（D3）。此修復與真實觸發路徑無關性成立——無論哪條 store 路徑發出導航信號，pending 窗口內頁籤不動。實作第一步（tasks 1.0）仍以 instrumentation 重現釘死實際踢回路徑並留檔，作為回歸測試的根據；「proposal-only 面板不重置 dock stage」仍是指定契約，由 panelSig 不含 proposal 的既有事實＋pin 測試釘住（store 零改動）。

- 替代方案（改 store：把 proposal 納入簽名並加 skip 條件）：被否——為修復一個靜態上不存在的重置路徑而動單一把關檔案，違反最小改動；且 A5 已獨佔 elosern.js 觸點，A3 零改動即消除同檔序列化。

### D3: 自動跳轉只在概念頁籤完成時發生；成功確認 toast 由表單層唯一寫入

`applyProposal()` 末尾：`mode.value === "concept" && conceptPending` 時 `setMode("custom")`，並經新 prop `pushToast`（AppClient 綁定 `:push-toast="store.pushToast"`，`add-action-feedback-toasts` 的佇列 API）推一條 info toast「概念提案已套用到自訂表單」。所有權契約（rubber-duck 發現 1）：**成功確認 toast 的唯一寫入者是表單層**——只有 `applyProposal()` 套用时點同時知道「落地成功＋導航脈絡」，revision＋`conceptPending` 雙守門天然單次；store 對成功結果刻意不推（原「store 推通用 info＋overlay 事後抑制」方案作廢：result commit 時同步推播無法追溯抑制，`creationOverlayPresenting` 也測不出「完成於概念頁」）。失敗 crit 归 store 切片（`handleActionResult`，inFlight 指紋去重）；失敗時表單只清載入態，overlay result 區照舊（「overlay 為 presenting surface」契約不動）。重連／重掛的 mount-time `applyProposal()` 不帶 `conceptPending`，自然不跳轉、不 toast。

### D4: 五欄映射的缺席語義與親和裁剪

缺席鍵 → 不動本地值（名字空、年齡 18、背景空、親和維持）；有值 → 覆寫。`affinity_elements` 寫入前先依新種族上限（race 已先套用）截斷、過濾未註冊鍵，複用既有 `affinityMax` trim 慣例。`age`/`apparent_age` 直接寫入 number model——生成層夾取使本地成年閘天然通過，但本地閘本體不動（雙層防禦）。

### D5: banner 全套退役

`proposalNotice` ref、banner DOM、`openCustomFromProposal()`、testid `creation-proposal-notice`／`creation-proposal-open` 刪除；引用它們的 Vitest／瀏覽器測試遷到「自動跳轉 + toast」斷言。審視提示（race 衝突 `reviewPrompt`）不動——那是 custom 頁籤內的常駐提示，與導航無關。
