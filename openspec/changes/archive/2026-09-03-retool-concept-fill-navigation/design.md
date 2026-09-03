# retool-concept-fill-navigation — Design

## Context

`CreationOverlay.vue` 現狀（查證）：`mode` ref 為本地頁籤狀態（preset/custom/concept）；`applyProposal()` 只映射 race/subrace/allocations/persona；`watch(props.stage)` 以「stage 值變動」守門鏡設 mode；`syncFromDraft()` 的無 draft 分支以 `formTouched`＋stage 守門。store 側查證（rubber-duck finding 2）：`creationPanelSignature` 只序列化 presets／races／draft——**不含 proposal**，因此「proposal-only 面板重發導致簽名變動→root 重置」這條原始假設在靜態上走不通；踢頁籤的真實路徑（watcher 值變動、draft deep-watch、或 router settle 副作用）必須先以受 instrumentation 的瀏覽器重現釘死，修復選在 causally robust 的層。完成提示是頁籤列下方的 `proposalNotice` banner +「開啟表單」按鈕（`openCustomFromProposal()` 切 custom）。送出後無任何 in-flight 回饋。

上游：panel v3 的 `proposal` 槽已帶五個 optional 鍵（缺席＝鍵不存在）；ToastQueue 佇列（`add-action-feedback-toasts`）提供 `pushToast`。

tasks 1.0 復現結論（instrumented lifecycle 測試，`web/webclient-app/tests/overlays/concept_fill_navigation.test.js`；修復前 trace：`mount -> mode=preset | click concept tab -> mode=concept | click apply -> mode=preset`）：真實踢回路徑即 D2 路徑 (1)——`dispatchAction` 的 finally 同步 `publishView()` 在 `lastStage === null` 的掛載窗口內重發 `root` 值，stage watcher 的值變動守門被 null 初值放行，`mode` 寫成 preset，玩家於點擊瞬間被踢回第一頁籤且零回饋。路徑 (2)（result 結算使 dock view custom→root 的值變動補踢完成導航）由完成發布釘契約＋同檔生命週期測試覆蓋。

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

`applyConcept()` 的送出走兩個新 prop：`dispatch`（**回傳型函式**，AppClient 綁 wrapper＝`store.dispatchAction(action_id, payload)`，回傳 requestId 或 null）與 `dispatchState`（AppClient 綁 `store.view.dispatch`：`{inFlight, submittedRequestId}`）。有 `dispatch` prop 時**只有獲准（回傳非 null）才設 `conceptPending = true`**——被 single-mutation-in-flight 閘拒絕（回傳 null、不發布新 view）時本地載入態根本不會亮起，stuck-spinner 無從發生（rubber-duck blocking 1：閘拒絕不發布，watch 不到任何信號）。無 `dispatch` prop 的獨立掛載（Vitest／showcase）退回既有 `emit("action")` 路徑並設 pending，由測試自行驱动 commit。輸入框與按鈕的 disabled 掛 `conceptPending || dispatchState?.inFlight`（共享 in-flight 閘語意，指針端點擊前就不可重複提交）。

清除路徑（先到者生效）：(a) `applyProposal()` 套用了大於已套用序號的新 revision；(b) 本次 request 的非成功 result——比對式 `props.result?.requestId === props.dispatchState?.submittedRequestId && outcome ∈ {rejected,stale,error}`，**先守 `conceptPending && props.dispatchState` 再解引用**（獨立掛載只帶 result 不带 dispatchState 的既有測試不得拋錯，rubber-duck blocking 3）；(c) **全域閘釋放安全網**：`watch(props.dispatchState)` 在 pending 期間觀察到 `inFlight === null` 即結算載入態——涵蓋 sender 同步失敗（stores/elosern.js 的 catch 分支清 inFlight 並發布、但不發 result）、傳輸中斷（uncertain 路徑同樣清 inFlight）、以及 result 已結算而 proposal 槽遲到／缺席的異常排序。健康等待窗口內 `inFlight` 從獲准發布到 result 認可＋presentationRevision 追平之間持續非 null（查證：dispatcher 先發布承載 proposal 的 panel、才送 result；`releaseIfReady` 只在 committed revision 追平宣告後清閘），故安全網不會過早清除；即使極端排序下 (c) 先結算，後到的 proposal 仍依 D3 的完成導航契約填表與跳轉。掛載時初值為假＝斷線／重掛自然清除。

- 替代方案（只用 `view.dispatch.inFlight` 做 preflight 不回傳獲准結果）：被否——閘拒絕不發布，本地無從知道送出失敗；回傳型 dispatch 直接把獲准與否交還表單層。

### D2: 導航修復選在 overlay 的 in-flight 釘住；不動 `rebuildCreationDock`

查證釘死的真實踢回路徑（tasks 1.0 instrumentation 復現確認）：stage watcher 只在 **stage 值變動**時鏡設 `mode`，而 `view.creationView` 每次 `publishView()` 都是新物件——觸發一次值變動即可踢頁籤。兩條真實路徑：(1) 掛載時 `lastStage` 為 null、值守門不擋，第一次帶 stage 值的發布（例：`dispatchAction` 在 finally 同步 `publishView()`）就把 `root` 寫成 preset；(2) concept 送出的 result 結算 `pendingSaveRequestId` 時，dock view 由 custom 回落 root，值變動踢 concept→preset（Telnet 流玩家必經 custom stage 之故）。原 `rebuildCreationDock` 加 skip 條件的計畫照舊作廢（panelSig 不含 proposal，目標場景不評估）。修復為 overlay 層釘住：`conceptPending === true` 時 stage watcher 與 `syncFromDraft` 跳過**只有 `mode` 的寫入**（`lastStage` 追蹤與欄位同步照常，避免解除釘住後被過期值補踢）；完成導航由 `applyProposal()` 明確執行（D3）。「proposal-only 面板不重置 dock stage」仍是指定契約，由 panelSig 不含 proposal 的既有事實＋pin 測試釘住（store 零改動）。

- 替代方案（改 store：把 proposal 納入簽名並加 skip 條件）：被否——為修復一個靜態上不存在的重置路徑而動單一把關檔案，違反最小改動；且 A5 已獨佔 elosern.js 觸點，A3 零改動即消除同檔序列化。

### D3: 自動跳轉只在概念頁籤完成時發生；成功確認 toast 由表單層唯一寫入

`applyProposal()` 末尾：**新 revision 套用且 `mode.value === "concept"`** 時 `setMode("custom")`，並經新 prop `pushToast`（AppClient 綁定 `:push-toast="store.pushToast"`）推一條 info toast「概念提案已套用到自訂表單」。跳轉／toast 以「新 revision＋目前頁籤」守門（mount 重填落地於 preset，天然不跳不推；`conceptPending` 只做載入態結算，不做導航守門，避免 (c) 安全網先結算時吞掉合法完成導航）。所有權契約（rubber-duck 發現 1）：**成功確認 toast 的唯一寫入者是表單層**，revision＋頁籤雙守門天然單次；store 對成功結果刻意不推；失敗 crit 归 store 切片（`handleActionResult`，inFlight 指紋去重）；失敗時表單只清載入態，overlay result 區照舊。重連／重掛的 mount-time `applyProposal()` 不帶 pending 且落地非概念頁，自然不跳轉、不 toast。

**完成發布釘（completion-publish pin）**：同一筆完成 commit 可同時帶新 proposal、result 與 root stage 值；watcher 回調按註冊順序跑（proposal watcher 註冊在前、stage watcher 在後），若只有 in-flight 釘住，完成 commit 自己就能在 `applyProposal()` 跳完 custom 後把 mode 補踢回 preset（rubber-duck 複審 blocking 1：同一事件迴圈內競態）。故 `applyProposal()` 執行完成導航時記錄**該發布的 stage 物件識別**（`latchedStage = props.stage`）；stage watcher 與 `syncFromDraft` 的 mode 寫入只在「`props.stage` 仍是該被標記物件」時跳過——精確消耗完成發布自身的過期信號；之後任何**新發布**的 stage 值變動（鍵盤導航、Escape 回落、確認流）一律如常鏡設並解除標記，鍵盤優先導航不受影響（rubber-duck 複審 blocking 2：無界釘住會永久吞掉鍵盤路由鏡像）。指針頁籤按鈕的本身點擊本來就走 `setMode`，不在抑制範圍。

實作細節（復現測試鎖定的哨兵語意）：`latchedStage` 以 `undefined` 作「永不匹配」哨兵、且只記錄 truthy 的 stage 物件——`stage` prop 為 null（獨立掛載／非 creation 模式）時絕不會被誤認成已消耗之完成發布而擋掉 mount-time draft 續填（該競態由 `resumes a custom draft` 回歸測試釘住）。

### D4: 五欄映射的缺席語義與親和裁剪

缺席鍵 → 不動本地值（名字空、年齡 18、背景空）；有值 → 覆寫。`affinity_elements` **在場**時先過濾新種族（race 已先套用）的註冊鍵、再依 `affinityMax` 上限截斷後寫入；**缺席**時維持既有選擇不覆寫，但 race 寫入本身照舊觸發既有的 `affinityMax` trim 慣例（與玩家自行改種族同一路徑）——超過新種族上限的本地選擇必須被裁，否則 `affinityMax === 0` 的種族（精靈）下自訂送出會被伺服端親和閘駁回，表單陷入無法送出的死局（rubber-duck 複審 finding：此語義衝突明示於 delta spec，非默默違反 absent=untouched）。`age`/`apparent_age` 直接寫入 number model——生成層夾取使本地成年閘天然通過，但本地閘本體不動（雙層防禦）。

### D5: banner 全套退役

`proposalNotice` ref、banner DOM、`openCustomFromProposal()`、testid `creation-proposal-notice`／`creation-proposal-open` 刪除；引用它們的 Vitest／瀏覽器測試遷到「自動跳轉 + toast」斷言。審視提示（race 衝突 `reviewPrompt`）不動——那是 custom 頁籤內的常駐提示，與導航無關。
