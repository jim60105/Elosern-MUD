# retool-concept-fill-navigation Tasks

## 1. 重現並釘死踢回路徑 + overlay in-flight 釘住

- [x] 1.0 用 instrumentation（watcher 日誌 + `mode` 寫入點追蹤）在瀏覽器重現「概念送出→完成」旅程，記錄實際把 `mode` 踢離 `concept` 的信號與來源（stage watcher 值變動／draft deep-watch／router settle）；結論寫進 design.md Context 作為修復與回歸測試依據。
- [x] 1.1 `CreationOverlay.vue`：stage watcher 與 `syncFromDraft()` 在 `conceptPending === true` 時 early-return，不觸碰 `mode`（導航釘住）；`stores/elosern.js` 不動（panelSig 按設計不含 proposal，root-reset 分支在目標場景不被評估）。

## 2. applyProposal 五欄映射與載入態

- [x] 2.1 `applyProposal()` 補映射 `display_name`/`background`/`age`/`apparent_age`/`affinity_elements`（> revision 才填、缺席不動、affinity 依新種族 `affinityCaps` 裁剪）；persona 三欄既有映射不動。
- [x] 2.2 `applyConcept()`：新 props `dispatch`（回傳型函式）＋`dispatchState`＋`pushToast`；獲准（回傳非 null）才設 `conceptPending`；清除＝(a) 新 revision 套用／(b) 守門後比對 `result.requestId === dispatchState.submittedRequestId && outcome ∈ {rejected,stale,error}`／(c) `watch(dispatchState)` 觀察 `inFlight === null` 的安全網結算；概念頁 large-loading 區塊（spinner＋「概念生成中，請稍候…」＋textarea/按鈕 disabled 掛 `conceptPending || dispatchState?.inFlight`）；`AppClient.vue` 新增 `:dispatch`（dispatchAction wrapper）、`:dispatch-state="store.view.dispatch"`、`:push-toast="store.pushToast"` 綁定。
- [x] 2.3 完成跳轉＋發布釘：concept 頁 fresh apply（新 revision＋mode==="concept"）→ `setMode("custom")`、記 `latchedStage = props.stage`，並經 `pushToast` 推一條 info 確認 toast（唯一寫入者＝表單套用路徑；store 對成功靜默）；stage watcher／`syncFromDraft` 只在 `props.stage === latchedStage` 時跳過 mode 寫入，新發布一律如常並解除標記；mount-time 重填不跳轉、不推 toast。
- [x] 2.4 退役 `proposalNotice`／「開啟表單」按鈕／`openCustomFromProposal()`／testid `creation-proposal-notice`、`creation-proposal-open`。

## 3. 測試與驗證

- [x] 3.1 Vitest（`web/webclient-app/tests/`）：五欄映射（含缺席不動、affinity 裁剪、僅 > revision 觸發）、載入態進出（成功清除＋跳轉＋恰一條 info toast、非成功清除＋crit toast 來自 store 切片、舊 request 快取 result 不清除、無 dispatch prop 掛非成功 result 不拋錯）、dispatch 獲准守門（回傳 null 不進載入態）、(c) 安全網結算（inFlight 轉 null 清除載入態）、in-flight 釘住（pending 時 stage 值變動不改 mode）、完成發布原子釘（同一 setProps 帶 proposal+result+root stage → settle 後仍在 custom）、proposal-only 面板重發 stage 不變（store 契約）、banner 消失。
- [x] 3.2 既有引用 `creation-proposal-notice`／`creation-proposal-open` 的測試遷移或刪除；`showcase-coverage` 清單同步（如引用）。
- [x] 3.3 瀏覽器 class：概念旅程端到端（送載入態 → 完成 → 自訂頁含名字/年齡/背景/親和；依 1.0 釘死的機制補一條「完成後停留/跳轉符合契約」的生命週期回歸測試）。
- [x] 3.4 `npm test` 綠；`uv run --locked python -m tools.spec_traceability check` 綠；`openspec validate retool-concept-fill-navigation --strict` 綠。
