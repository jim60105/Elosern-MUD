# add-action-feedback-toasts — Tasks

實作順序即分組順序：store 切片 → 元件與掛載 → concept 觸發 → 凍結測試改寫與 manifest → 收尾。每組做完先跑該組 focused 測試再勾選；不跑 CI shard 指令。

## 1. Store toast 切片（stores/elosern.js）

- [x] 1.1 佇列狀態：`toasts` 陣列（客戶端本地，不入 reducer 提交快照）、單調 `id`、`pushToast({ title, sub?, tone })`（上限 4 FIFO）、`dismissToast(id)`、預設 5200 ms 自動出列（假時鐘可測）；`view` 切片暴露唯讀 `toasts`；epoch／transport 重置不清佇列（純本地）。
- [x] 1.2 Vitest：FIFO 上限、自動消失（fake timers）、點擊 dismiss、不持久化（無 storage 寫入斷言）、view 暴露形狀。

## 2. 元件與掛載（ToastQueue.vue / AppClient.vue）

- [x] 2.1 新元件 `web/webclient-app/components/ToastQueue.vue`：右上錨定堆疊、`.tt`/`.ts` 結構、`tone: "crit"` seal 紅左緣、點擊 `dismissToast`、入場動畫復用 `@keyframes elosern-toast-in`、reduced-motion 路徑沿用既有 motion 慣例；testid `feedback-toast-queue`／`feedback-toast-<id>`；純展示（零本地狀態）。
- [x] 2.2 `AppClient.vue` 根層掛載，z-index 高於 creation overlay；Storybook story（info／crit／含副標／滿佇列／空狀態，另含 `DismissOnClick` 互動 story 以可觀察 play 契約驗證點擊關閉；重設計草稿的滑過提示即 `cursor:pointer`，無 `:hover` 規則可演示——與 delta spec 要求一致：story＋manifest 條目＋showcase 閘通過）；`web/webclient-app/component-manifest.json` 增列。
- [x] 2.3 Vitest：crit/info class、點擊關閉回呼、疊層順序斷言（DOM 位置／z-index 約定）。

## 3. concept 觸發點（handleActionResult）

- [x] 3.1 `handleActionResult` 認得 `creation.concept` matched result：**僅非成功** → `pushToast({ title: 訊息逐字 or ACTION_RESULT_FALLBACK_MESSAGE, tone: "crit" })`（成功結果刻意不推——確認 toast 由 A3 的 `applyProposal()` 寫入）；同一 result 重複觀測不重複推播（沿用 `inFlight.handledResult` 指紋去重）；既有敘事單行與 overlay result 行為逐字不動；crit 與 feed 共享認可／去重單位與非成功判準，feed 的 overlay 抑制條件為 feed 專屬（D3 精確表述），toast 以本地 `inFlight.actionId` 縮窄至 concept（custom/preset 含 stale 例外天然排除）。
- [x] 3.2 Vitest：失敗一條 crit 逐字／無訊息走 fallback／重複觀測只一條／成功結果（含 overlay 掛載的 `concept_applied`）零 toast／非 concept 失敗零 toast／feed 無新增行／push 前後 reducer 快照不變（行為斷言：`view.revision` 不變、`sender.sent` 零增量、narrative 長度不變）＋localStorage 零寫入（vi spy）；`afterEach` 以 `store.$dispose()` 走 scope-dispose 清除全部待觸發計時器與佇列，並 `vi.useRealTimers()` 防跨案洩漏。
- [x] 3.3 Traceability（倉庫先例：Vitest 不在 `spec_traceability` 索引內，JS 要求經 Python 證據橋掛載，如 `test_vue_showcase_evidence.py`）：新增 `web/tests/browser/test_browser_action_feedback.py`（Playwright 受管瀏覽器驅動真實佇列：push/上限/關閉/concept 失敗 crit 旅程）。兩條 canonical ID 由標題 slug 固定派生（`webclient-action-feedback::the-client-owns-a-bounded-action-feedback-toast-queue`、`::the-concept-apply-surfaces-exactly-one-confirmation-or-one-failure-toast`），能力進入主規格索引（歸檔同步）前 `covers_requirement` 會以 unknown-requirement-id 使 check 報錯（tools/spec_traceability.py:262）——故標註在**歸檔同步同一步**套用（B1 先例，test_vue_showcase_evidence.py docstring 記錄同一程序），本期於模組 docstring 記錄映射表；Vitest 保留為快速迴歸層。

## 4. 凍結測試改寫與 showcase

- [x] 4.1 `web/webclient-app/tests/overlays/deferred_surfaces_absent.test.js`：`DEFERRED_TITLE_PATTERNS` 移除 `/Toasts?/i`（保留 EventLog／Party／Objectives）；延後清單的 toast 條目改名為「event-log 遊戲事件 toast queue」並保留 `toast-`／`event-log-` testid 禁令；新增斷言：`feedback-` 前綴存在；本地態不膨脹以行為斷言驗證（見 3.2），不做原始檔掃描。
- [x] 4.2 `npm test`、`npm run build`、`npm run build-storybook`、`npm run showcase-coverage`（manifest 重凍結含 ToastQueue）。
- [x] 4.3 `docs/development/webclient-vue-frozen-contract-audit.md` 對應章節同步（ToastQueue 條目 + 延後清單措辭）。

## 5. 收尾

- [x] 5.1 `uv run --locked python -m tools.spec_traceability check`；`openspec validate add-action-feedback-toasts --strict`；消極檢查為 **testid 屬性綁定掃描**（`data-testid="toast-`／反引號形式與 `data-testid="event-log-`／反引號形式——裸字串 `toast-` 命中 `feedback-toast-` 屬必然，不作判準）：命中僅限延後測試自身的陣列條目與註解。
- [x] 5.2 本地瀏覽器冒煙（受管本機、單 class 預算內）：創角概念失敗 → crit toast 在 overlay 之上可見、可點擊關閉、時到自動出列（套用旅程的成功確認 toast 由 A3 `retool-concept-fill-navigation` 落地時一併冒煙）；正式證據由 3.3 的 Python 橋 class 在 CI 產出。
