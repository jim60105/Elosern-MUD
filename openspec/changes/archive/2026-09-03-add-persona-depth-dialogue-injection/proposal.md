# add-persona-depth-dialogue-injection

## Why

`identity / appearance / social_connection` 三個 persona 鍵源自角色表（`tmp/story_settings/character/`，五張表結構一致），現行倉庫零消費者——`PersonaStore.flatten` 的預設欄位集不含它們，寫得進、讀得出、但永遠進不了任何 LLM prompt。設計文件 `docs/superpowers/specs/2026-09-02-concept-transient-fill-persona-design.md` §11 為它們建立第一個消費者：NPC 對話注入。沒有這層，角色表的深度欄位在遊戲內等同不存在。設計源頭 §11.1–§11.7。

## What Changes

- `PersonaStore` 渲染採寬容策略：字面值照渲染、Mapping 渲染為「子鍵：值」行、清單渲染為列點、未知形狀跳過不拋錯——匯入範例的字串寫法與角色表的巢狀寫法於焉皆可渲染。
- `flatten` 新增渲染組與正體中文標籤：`identity`（巢狀時拆 公開身分／隱秘身分 兩節、字串時單節 身分）、`appearance`（外觀）、`social_connection`（人脈）。每一項受 600 字上限、整塊受 block limit 約束，沿用 `_cap` 截斷。欄位集參數維持呼叫端可覆寫。
- 注入欄位選取政策：NPC 自己的 persona 全欄進 system message（含 `identity.hidden`——角色自己的秘密交給角色自己的 LLM，數值洩漏由既有 no-leak validator 把關）；送入 NPC prompt 的玩家 persona 僅供 `identity.public`、`appearance`、`social_connection`，`identity` 先經 `PersonaStore.public_view()` 遞迴重建為深度剔除 hidden 的獨立快照再渲染——by construction 排除，絕不事後文字清洗。
- 三鍵維持排除於建立表單與編輯白名單（結構化欄位不適用單文字欄編輯模型）；本變更只開放「存得進、讀得出、進了 LLM prompt」。

## Capabilities

### Modified Capabilities
- `persona-store`: `flatten` 從「非字串欄位視同缺席」改寫為寬容巢狀渲染契約，並新增 identity/appearance/social_connection 渲染組。
- `persona-dialogue-injection`: NPC 自身 persona 與玩家 persona 兩條注入要求的欄位選取政策改寫。

## Impact

- `world/rules/persona.py`（`PersonaStore` 寬容渲染器、`public_view()` 與欄位集）、`world/ai/npc_dialogue.py`（注入政策欄位集常數 `NPC_PERSONA_FIELDS`／`PLAYER_PERSONA_FIELDS`）、`typeclasses/npcs.py`（`_persona_block` seam——`flatten` 的實際欄位選取呼叫點）。
- 預設欄位集的位元等值僅對「值為字串」的既有記錄保持不變（現存全部記錄皆為字串值）；匯入若曾把清單／巢狀值寫進 `personality`／`life_story`／`habit`，寬容渲染會使其在 look 顯示與 `option_proposal_service` 的 `persona_digest` 中開始出現——這是寬容契約的刻意改變，非回歸。
- 測試：`world/rules/tests/test_persona.py` 增巢狀／字串／清單／未知形狀渲染與截斷案；NPC 對話 prompt 案（NPC 塊含隱秘身分、玩家塊不含 `identity.hidden`、無 persona 玩家 payload 位元等值不動）。
- token 成本：玩家 persona 塊變大，2000 字 block limit 可能觸發截斷；緩解為呼叫端按 surface 覆寫上下限（建構子已參數化）。
- 無驗證器、無 import-schema 變動（persona 驗證維持 verbatim opaque）；與 A／B 檔案不相交，可完全平行。
