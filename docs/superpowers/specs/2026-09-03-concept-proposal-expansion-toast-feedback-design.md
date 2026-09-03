# 概念提案五欄擴充與動作回饋 Toast 基礎設施 — 設計文件

**日期：** 2026-09-03
**狀態：** Approved（待讀者對本文件做最終審閱）
**範圍：** `world/ai/character_creation.py`、`prompts/character_creation.yaml`、`web/webclient/actions/creation_actions.py`、`web/webclient/presentation/creation.py`、`web/static/webclient/js/elosern/protocol.js`、`web/webclient-app/`（`stores/elosern.js`、`components/CreationOverlay.vue`、新元件 `ToastQueue.vue`、AppClient/AppShell 掛載、frozen 契約測試、Storybook showcase）、`commands/character_creation.py`（Telnet concept 流預設值）、`docs/superpowers/specs/2026-09-02-concept-transient-fill-persona-design.md`（年龄決策修訂）、主規格 `webclient-character-creation-ui`、`character-creation-ux`，新能力 `webclient-action-feedback`。

本文件是後續 OpenSpec change（暫名 `extend-concept-proposal-and-add-toast-feedback`）的實作依據，並在年龄決策上修訂 `retool-concept-transient-fill` 設計（2026-09-02）的對應條款。

---

## 1. 問題陳述

玩家以概念「一個貓人少女，有豐富的背景設定，性格極端」走 webclient 創角流程，回報六項問題。查證後的根因如下（全部為實測事實）。

其一，按下 `button.creation-concept-apply` 後畫面跳回預設頁籤（第一頁籤）。機制：概念完成時伺服器重發 `creation` 面板（draft 為 null），store 的 `rebuildCreationDock`（`stores/elosern.js`）因簽名變動把 dock view 重置為 `root`，`CreationOverlay.vue` 的 stage watcher 據此把 mode 踢回 `preset`。且送出到完成之間零回饋——按鈕無 disabled、無 loading 態。

其二，LLM 完成後的提示（`proposalNotice`）渲染在頁籤列正下方並附「開啟表單」按鈕，位置與存在意義都被玩家否定。

其三至其六，自訂表單的名字、背景、元素親和為空白，年齡與外觀年齡停在 18。根因不是丟失，而是 LLM 藍圖契約根本不產生這五欄：`world/ai/character_creation.py` 的 `CharacterProposal` 與 `prompts/character_creation.yaml` 只含 `{race_key, subrace_key, allocations, suggested_skills, persona{personality, life_story, habit}}`，提示詞明文禁止年齡並禁止契約外鍵；前端 `applyProposal()` 如實只映射既有欄位。年齡 18 是前端 `ref(18)` 預設值。

結論：問題 1–2 是導航與回饋的 UX 缺陷；問題 3–6 是提案契約的範圍缺陷，需端到端擴充五欄。

## 2. 設計原則

1. **提案即暫態填入器**的既有定位不變（2026-09-02 設計 §2.2）：概念零持久寫入，提案經 session 瞬態槽送達、填入表單。本期只擴大填入的欄位集合。
2. **伺服端正規化、不棄回覆**：提案通過結構驗證後，界外值一律就地夾取／截斷／剔除，永不因單一欄位界外而降級整份提案。玩家要求「LLM 回年齡 < 18 時直接覆寫為 18，不棄回覆、不告知 LLM」——夾取因此是 guardrail validator 的語義的一部分，不是重試語義。
3. **單一把關點**：五欄的正規化只在 `world/ai/character_creation.py` 的語義驗證器做一處，webclient 與 Telnet 兩條 surface 消費同一份已正規化的 `CharacterProposal`，規則不重複。
4. **Toast 是客戶端動作回饋通道**：其狀態是純客戶端本地狀態（送出中／完成／失敗的回執），本就不需要後端 OOB 讀取模型。遊戲事件 toast（升級／任務／解鎖／金錢）仍待未來的 `event-log` 讀模型，屆時直接插入同一佇列——本期只留介面不做事件匯流排（範圍決策，玩家已確認）。
5. **提示詞最小化原則**：要求 LLM 正常提出年齡與親和，不在提示詞裡敘述成年約束——成年把關完全由伺服端夾取承擔，降低 LLM 工作複雜度。

## 3. Toast 基礎設施（D1）

### 3.1 Store 切片

`stores/elosern.js` 新增 toast 佇列狀態，與既有 `view` 切片同路徑發布：

- 條目形狀 `{ id, title, sub?, tone }`，`tone ∈ {"info", "crit"}`，`id` 為單調遞增整數。
- 寫入介面：`pushToast({ title, sub?, tone })`；`dismissToast(id)`；自動消失由計時器驅動（預設 5200 ms，對齊 redesign 草稿）。
- 佇列上限 4，超出時最舊條目立即出列（FIFO）。
- 條目內容全為客戶端組字或伺服端訊息逐字（非成功結果的 `message` 原樣作 `title`），不進入敘事feed、不持久化。

### 3.2 元件與掛載

- 新元件 `components/ToastQueue.vue`：右上錨定堆疊，逐條渲染 `.tt`（標題）與可選 `.ts`（副行），`tone: "crit"` 用 seal 紅左緣色（redesign `.toast.crit` 樣式）；點擊關閉；入場動畫復用 `tokens.css` 的孤兒 `@keyframes elosern-toast-in`（自此有消費者）。
- 掛載層級：`AppClient.vue`（或 AppShell 等價層）根節點、z-index 高於 creation overlay——創角期間的 toast 必須可見。
- testid 前綴 `feedback-`（`feedback-toast-<id>`、佇列 `feedback-toast-queue`）。

### 3.3 觸發點（本期）

1. `creation.concept` 成功（結果 code `concept_applied`）：info toast「概念提案已套用」。
2. `creation.concept` 非成功（rejected／stale／error）：crit toast，title 為伺服端訊息逐字（如 LLM 離線的「概念服務目前無法使用」類訊息）。overlay 自身的 result 區照舊顯示（overlay 仍是 presenting surface 契約不變）。
3. 佇列介面預留：未來 `event-log` 讀模型落地時，由 store 的 reducer 路徑把遊戲事件推入同一佇列，元件零改動。

### 3.4 凍結契約的改寫（不是迴避）

`deferred_surfaces_absent.test.js` 對 toast 的禁令源於 roadmap 當時「無 `event-log` panel」的範圍決定（2026-08-25 roadmap 設計表格「Event toasts — not backed」），並非架構禁忌。本期把它改寫為兩層：

- 保留的本質不變量：任何元件不得渲染無資料來源的後端讀取模型欄位（原 testid 清單中 `event-log-`、`companion-`、`objective-` 表面維持缺席斷言）。
- 動作回饋 toast 改列「已落地 surface」：`feedback-` testid 合法；`DEFERRED_TITLE_PATTERNS` 移除 `/Toasts?/i`（保留 EventLog／Party／Objectives）；遊戲事件 toast 的 testid（`toast-` 前綴＋event-log 資料綁定）在讀模型落地前仍禁止——被禁的是無資料綁定的假資料，不是元件本身。
- `ToastQueue.vue` 進 Storybook showcase 必需清單（manifest 重凍結）與 `webclient-vue-frozen-contract-audit.md` 對應章節同步。

## 4. 概念頁籤的等待態與導航（D2）

### 4.1 送出中的大載入態

- `CreationOverlay.vue` 新增本地 `conceptPending` 狀態：`applyConcept()` 送出時設真；概念頁籤區塊進入載入態——概念 textarea 與「套用概念」按鈕 `disabled`，區塊中央顯示大 spinner 與「概念生成中，請稍候…」（本地文案）。
- 清除條件（二者其一先到）：新的 proposal revision 送達（`applyProposal()` 套用路徑）；或本次 request 的任何非成功 result（rejected／stale／error）。重複點擊由 disabled 抵擋，傳輸層的 single-mutation-in-flight 仍是底線防線。
- 重新整理／斷線使 in-flight 失蹤時，`conceptPending` 由 result 缺席自然過期：overlay 掛載時重置（本地 ref 初值即假，天然正確）。

### 4.2 完成後自動跳自訂頁籤

- `applyProposal()` 成功套用新 revision 後：`setMode("custom")`，玩家直接看見填好的表單；同時推 info toast。
- 移除 `proposalNotice` banner、其「開啟表單」按鈕與 `openCustomFromProposal()`（用戶判定無意義）；`creation-proposal-notice`／`creation-proposal-open` testid 同場退役。
- 重連重建場景（面板帶未消費 proposal 重掛）：照舊填入表單，但不自動跳轉、不重複 toast——跳轉只屬於「本次點擊的完成時刻」。

### 4.3 stage 踢回根因修復

`rebuildCreationDock`（`stores/elosern.js:1564-1583`）的 root 重置分支增加條件：**面板 draft 為 null 且帶未消費 `proposal` 槽時不重置 dock view**。提案送達从此不動導航；導航由 overlay 完成態明確負責（§4.2）。既有分支（preset draft→presets confirm、custom draft→custom、其餘→root）逐字不動，Telnet 與 confirm 流不受影響。

## 5. 提案契約五欄擴充（D3）

### 5.1 新增欄位與生成語義

`CharacterProposal` 新增五個可缺席欄位（缺席＝前端維持本地預設，即現行為）：

| 欄位 | 型別 | 提示詞指示 | 伺服端正規化（安全網） |
|---|---|---|---|
| `display_name` | `str` | 為角色取正體中文名字 | 去首尾空白；超 `MAX_NAME_CODE_POINTS` 截斷；正規化後為空 → 缺席 |
| `age` | `int` | 提出角色年齡（**不敘述成年約束**） | 非整數 → 缺席；`< 18` → 覆寫 18；`> 10000` → 覆寫 10000 |
| `apparent_age` | `int` | 同上（外表年齡） | 同 `age` |
| `background` | `str` | 精簡背景故事（繁體中文） | 去首尾空白；超 `MAX_PERSONA_FIELD_LENGTH`(600) 截斷；空 → 缺席 |
| `affinity_elements` | `tuple[str, ...]` | **依所選種族的親附上限選取，精靈不得選取**（上限寫進 `race_catalog`，見 §5.2） | 剔除未知鍵 → 去重 → 依 `max_affinity_elements(race_key)` 截斷；`race_key == "elf"` → 清空；清空後為空tuple |

- 夾取／截斷全部發生在既有語義驗證器的**正規化阶段**：驗證器回傳正規化後的值，guardrail 不改 retry 語義、不向 LLM 回報夾取。
- 結構輸出 schema（`CHARACTER_CREATION_OUTPUT_SCHEMA`）把五鍵列為 optional；`_validate_shape` 的 unknown-key 黑名單同步放行五鍵。
- 「不棄回覆」邊界：既有整體性失敗條件（persona 恰三鍵、allocations 七軸預算總和、race/subrace registry 成員資格）不變——那些是結構完整性；五欄界外值是單欄缺陷，一律正規化而非失敗。

### 5.2 提示詞（`prompts/character_creation.yaml`）

藍圖契約 JSON 樣板擴為：

```
{"race_key": …, "subrace_key": …, "allocations": {…}, "suggested_skills": […],
 "display_name": "角色名字", "age": 0, "apparent_age": 0,
 "background": "精簡背景", "affinity_elements": ["元素鍵值"],
 "persona": {"personality": …, "life_story": …, "habit": …}}
```

- 移除「不得替玩家決定年齡——年齡一律由玩家自己輸入」「不得加入年齡欄位」兩句（2026-09-02 設計「年齡由玩家」條款的翻案點，本文件為其修訂記錄）。
- `race_catalog` 每個種族條目附帶 `親附上限：N`（由 `max_affinity_elements` registry 派生，不寫死），並指示「affinity_elements 的數量不得超過所選種族的親附上限；精靈留空」。
- `background` 指示控制在 600 字內；名字指示為正體中文、簡短。
- 提示詞不提「成年」「18」等約束——成年把關是伺服端夾取的職責（原則 5）。

### 5.3 線路（creation panel schema v2 → v3）

- `proposal` 槽新增五個 optional 鍵：`display_name`、`age`、`apparent_age`、`background`、`affinity_elements`（正規化後缺席的欄位不上線）。
- `schema_version` 2 → 3。三處鏡像驗證器同批改寫：`web/webclient/presentation/creation.py`、`web/static/webclient/js/elosern/protocol.js`、（Vue 端消費即 `CreationOverlay.vue`，無獨立驗證器）。
- 信封最壞情況：五欄增量（名字 ≤64 cp、背景 600 cp、兩個 int、八元素鍵）疊加既有 persona 三欄 1.8 KB，對 `MAX_CANONICAL_JSON_BYTES = 65536` 仍餘裕充足，worst-case 測試重鎖。

### 5.4 前端映射（`CreationOverlay.vue`）

`applyProposal()` 於既有 race/subrace/allocations/persona 映射後追加：

- `display_name` → `name.value`（缺席 → `""`，維持使用者親打）。
- `background` → `background.value`。
- `age`／`apparent_age` → `age.value`／`apparentAge.value`（已經伺服端夾取，必 ≥ 18；本地成年閘自然通過）。
- `affinity_elements` → 先過新種族上限（`applyProposal` 既有 trim 路徑），再寫入 `affinitySelected` Set；缺席 → 維持現有選取。
- 重新套用（新 revision）一律替換五欄，與 persona 三欄同語義；表單重建（同 revision 重發布）不覆寫玩家編輯——既有 revision 守門直接涵蓋。

### 5.5 Telnet `character concept` 流

- 提案有名字時以其為提示預設值（Enter 接受、輸入即覆寫）；`age`／`apparent_age` 同理。成年閘照舊（正規化後必過）。
- 提案的 `background`／`affinity_elements` 在啟動時直接作為暫態填入值（與 webclient 表單同語義）。
- 命令語法與命令文件（`docs/game/commands.md`、`docs/game/command-reference.md`）同步。

### 5.6 退役清單

- `proposalNotice` banner + `openCustomFromProposal()` + 兩個 testid（§4.2）。
- 提示詞的年齡禁令兩句（§5.2）。
- `_validate_shape` 錯誤訊息中「no age, no other numbers」措辭。

## 6. 錯誤處理矩陣

| 失敗點 | 行為 |
|---|---|
| LLM 回 `age < 18`（或 `apparent_age < 18`） | 覆寫 18，提案照常送達（不重試、不告知 LLM） |
| LLM 回超界年齡（> 10000） | 夾 10000 |
| LLM 回非整數年齡／null | 欄位缺席 → 前端維持預設 18 |
| LLM 回過量／精靈 affinity | 截斷／清空，提案照常送達 |
| LLM 回未知元素鍵 | 剔除後照常 |
| `display_name`／`background` 超界 | 截斷；全空白 → 缺席 |
| 結構性失敗（persona 缺鍵、allocations 超預算、假種族鍵） | 既有 retry → 降級 `concept_unavailable`（不变） |
| 概念進行中 LLM 離線／重試耗盡 | `concept_unavailable` 穩定拒絕 + crit toast + overlay result 區；載入態清除 |
| 載入中斷線 | 重連後 `conceptPending` 隨 overlay 重掛而清，玩家重按（既已接受代價） |
| 提案送達但玩家已手動跳頁籤 | revision 守門照常填入，跳轉只在「完成於概念頁籤時」才執行（mode 檢查） |

## 7. 測試與驗證

- 純邏輯（`unittest`）：guardrail 正規化矩陣——`age`/`apparent_age` 的 `<18`、`>10000`、非整數、缺席；`affinity` 的未知鍵、重複、超種族上限截斷、elf 清空；`display_name`/`background` 的截斷與空白缺席；worst-case 信封位元組。
- 整合（Evennia）：`creation.concept` adapter → panel v3 `proposal` 槽含五鍵；presenter 驗證器 v3；Telnet concept 預設值流。
- Node／Vitest：`protocol.js` 鏡像 v3 新案（缺席鍵、夾取值通過）；`CreationOverlay` 的五欄映射、自動跳 custom、載入態進出、重連不重複跳轉；`ToastQueue` 佇列上限／FIFO／自動消失／點擊關閉；`deferred_surfaces_absent` 改寫案（`feedback-` 合法、事件 toast 仍禁）。
- 瀏覽器（Playwright 單 class）：概念旅程——輸入概念 → 套用 → 載入態出現 → 自動跳自訂頁籤且名字/背景/年齡/親和已填 → toast 可見 → 儲存啟動。
- 契約：新能力 `webclient-action-feedback` 與 modified `webclient-character-creation-ui`、`character-creation-ux` 每條 requirement 掛 `covers_requirement`；`tools.spec_traceability check` 綠；新測試模組註冊 `.github/evennia-shards.json`；命令文件兩式同步、`tests/test_command_docs.py` 綠；Storybook showcase manifest 重凍結。

## 8. OpenSpec 衝擊

| 既有 capability | 動作 |
|---|---|
| `webclient-character-creation-ui` | modified（panel v3 proposal 槽、載入態、自動跳轉、stage-reset 條件、banner 退役） |
| `character-creation-ux` | modified（Telnet concept 預設值流；提示詞年齡翻案記錄） |
| `player-character-creation` | modified（提案欄位集合擴充語義） |
| 新能力 `webclient-action-feedback` | added（ToastQueue 佇列、tone、觸發契約、凍結測試改寫） |
| `webclient-oob-protocol` | 不變（proposal 槽在 `creation` panel 內，無新信封） |

單一 change 實作（`extend-concept-proposal-and-add-toast-feedback`），內部任務群順序：AI 契約與正規化 → actions/presenter v3 → protocol.js 鏡像 → store toast 切片 + ToastQueue 元件 → Vue 表單／載入態／導航 → Telnet → 凍結測試/showcase/文件 → traceability 登記。

## 9. 取捨與已接受代價

1. 年齡決策翻案：2026-09-02 設計「年齡一律玩家輸入」由本設計修訂——LLM 提議、伺服端夾 18 保底、玩家仍可改。換得概念功能對「貓人少女」這類概念給出完整表單預填。
2. 「不棄回覆」犧牲單欄語義把關（超量親和被截斷可能非玩家本意），換得提案送達率；玩家在表單上看見結果並可改。
3. 動作回饋 toast 先落地、遊戲事件 toast 待讀模型：佇列介面重複使用，但凍結測試本期即改寫（已於 §3.4 給出不稀釋不變量的表述）。
4. 五欄使提示詞與驗證器變大，但每處仍是既有精確模式（optional 鍵、鏡像驗證器、穩定正規化）的機械性擴充。
