# add-persona-depth-dialogue-injection — Design

## Context

`world/rules/persona.py` 的 `PersonaStore` 是 import-card persona record 上的唯讀 handler；`flatten(fields=...)` 目前只渲染非空字串欄位，容器值（Mapping／list）視同缺席。persona 驗證維持 verbatim opaque（`import-schema` 不動），因此 `identity / appearance / social_connection` 早已「存得進」，但無任何渲染或注入消費者。

角色表（`tmp/story_settings/character/`，五張表結構一致）定義了這三鍵的巢狀意圖：`identity` 為 `{public, hidden}` 雙層；`appearance` 為固定子鍵（height/weight/measurement/style/overview）加 `attire`（場景→服裝映射）與 `feature`（配件清單）；`social_connection` 為「對象名 → {relationship, …}」字典。匯入範例把巢狀結構壓成字串，兩種寫法現存。

`world/ai/npc_dialogue.py` 現行注入：NPC 自身 persona 經 `flatten()`（預設三欄）進 system message 的 `{persona}`；玩家 persona 經 `player_persona` 參數進 user payload 的 `player.persona`。無 persona 時的位元等值（byte-identical）契約已鎖測。

約束：`world/ai/` 永不寫入；no-leak validator（per-call bounded secret set）已存在；`PersonaStore` 建構子已參數化上下限；import 驗證不可收緊。

## Goals / Non-Goals

**Goals:**

- 三鍵的第一個消費者：NPC 對話 prompt。
- 寬容渲染：字串／Mapping／list 皆可渲染，未知形狀跳過，絕不拋錯。
- 對稱欄位政策：NPC 看得到自己全部（含 hidden），NPC 眼中的玩家止於外觀、公開身分、人脈。

**Non-Goals:**

- 三鍵的編輯 UI 與面板呈現（§10 排除）。
- import 驗證器形狀化（維持 verbatim opaque）。
- 敘事者層的 `identity.hidden` 玩家側消費（留給未來變更）。

## Decisions

### D1: 寬容渲染器住進 PersonaStore，形狀契約留在文件層

`PersonaStore` 新增欄位渲染器：
- 非空字串 → 照現行渲染。
- Mapping → 「子鍵：值」行序列（遞迴一層；更深嵌套以字串化收尾），子鍵順序為宣告順序（已知鍵群 `identity`→`public`,`hidden`；`appearance`→`height,weight,measurement,style,overview,attire,feature`），未知鍵群內鍵排後。
- list/tuple → 列點（`- 項`）序列。
- 其他形狀（數字、布林、None）→ 跳過該欄／該子鍵，不拋錯。

欄位标签映射：`personality`→性格、`life_story`→人生經歷、`habit`→習慣、`background`→背景、`identity`→身分（渲染時子鍵映射 公開身分／隱秘身分）、`appearance`→外觀、`social_connection`→人脈。單項受 600 字 `_cap`、整塊受 block limit——截斷在渲染後字串上做，行為與現行一致。

- 替代方案（pydantic-style 驗證器）：違背 verbatim opaque 契約，且匯入範例的字串寫法會被自己拒收。否。
- 替代方案（渲染器住 `world/ai/`）：prompt 組裝层不該管 record 形狀；PersonaStore 本就是 record 渲染的單一位置。

### D2: 預設欄位集不動，深度欄位由呼叫端點名

`flatten()` 預設仍三欄（NPC dialogue 的既有位元等值契約不被本變更動到）。新增欄位集由呼叫端覆寫——呼叫端即 `typeclasses/npcs.py` 的 `_persona_block()`（現行 `self.persona.flatten(), character.persona.flatten()`），它是全倉庫對話路徑唯一的 flatten 選點：NPC 自身注入用全欄集 `("personality","life_story","habit","identity","appearance","social_connection")`；玩家注入用恰 `("identity","appearance","social_connection")` 的深度欄位集且 `identity` 以 public-only 視圖進入——玩家自己的個性、生平、習慣與 background 三欄敘事文字＋背景一律不進 NPC prompt（§11.4：NPC 眼中的玩家僅止於外觀、公開身分、人脈）。位元等值的範圍：預設欄位集下「值為字串」的記錄輸出逐字不變（現存全部記錄皆字串值）；容器值的散文字段開始渲染屬寬容契約的刻意改變，連帶現形於 look 顯示與 `option_proposal_service` 的 `persona_digest`。

- 玩家側 `identity` 的 public-only 實作：`PersonaStore` 提供 `public_view()`——回傳一個新的 `PersonaStore`，背後是一層淺拷貝 record，其中 `identity` 若為 Mapping 則僅保留 `public` 子鍵（字串 identity 原樣保留，無 hidden 可言），其餘鍵照原；非 Mapping record 原樣帶入（flatten 仍得 `None`）。渲染走同一寬容規則。呼叫端語意為 `store.public_view().flatten(...)`；「玩家塊永不含 identity.hidden」由 record 拷貝層保證，絕不事後文字清洗。此方法為純讀取（無寫入 API），但 `test_handler_has_no_write_api` 的恰鍵集合須同步納入 `public_view`。

### D3: 注入政策以欄位集常數鎖在 npc_dialogue、由 seam 匯入使用

NPC 系統訊息：全欄 persona 進 `{persona}`（含 hidden）——角色自己的秘密交給角色自己的 LLM 是角色扮演的本意；數值與機密洩漏由既有 no-leak validator 把關，政策不變。玩家 persona 進 `player.persona`：僅 public 視圖的 `identity`／`appearance`／`social_connection` 三欄，`identity.hidden` 與三欄敘事文字及 background 全數排除。無 persona 玩家的 payload 位元等值場景不動。欄位集常數 `NPC_PERSONA_FIELDS`／`PLAYER_PERSONA_FIELDS` 定義於 `world/ai/npc_dialogue.py`（政策唯一所有人），由 `typeclasses/npcs.py::_persona_block()` 函式內區域匯入後**直接引用常數**（勿複製 tuple，讓 seam 行為測試鎖住單一政策來源）；匯入位置遵循該檔既有 `world.ai.npc_dialogue` 函式內區域匯入慣例。

### D4: block limit 風險以呼叫端覆寫緩解

玩家塊變大可能觸發 2000 字 block limit 截斷。`PersonaStore` 建構子已參數化；對話路徑必要時按 surface 傳入較寬 block limit（此為實作自由，非協定）。token 成本上升屬已接受代價（§11.7）。

## Risks / Trade-offs

- [巢狀渲染把 secret 鍵名（hidden）以標籤帶入 NPC 可見文本] → 政策上 NPC 看得到自己的 hidden 是本意；玩家側 public_view 在 record 拷貝層排除，斷言鎖死。
- [更深嵌套或未知鍵群輸出過長文本] → 單項 `_cap` 600 + 整塊 block limit 雙層截斷，寬容跳過未知形狀。
- [字串 identity 的匯入範例與巢狀角色表渲染分歧] → 兩形狀皆為一級公民：字串→單節 身分：…；Mapping→公開身分／隱秘身分 兩節。測試各鎖一例。
- [預設欄位集改動會破壞既有位元等值場景] → D2 明確預設不動；位元等值測試必須原綠。 範圍註記：字串值的既有記錄逐字不變；容器值散文開始渲染是寬容契約的刻意結果（現存無此形狀記錄）。
