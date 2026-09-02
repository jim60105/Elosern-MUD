# add-persona-depth-dialogue-injection — Tasks

順序：renderer（PersonaStore）→ 欄位政策（npc_dialogue）→ 截斷／成本校驗。每組做完先跑該組 focused 測試再勾選。本變更與 A／B 檔案不相交，可平行執行。

## 1. PersonaStore 宽容渲染（world/rules/persona.py）

- [x] 1.1 實作宽容渲染器：非空字串照渲染；Mapping → 「子鍵：值」行（已知鍵群宣告順序：`identity`→public,hidden；`appearance`→height,weight,measurement,style,overview,attire,feature；未知子鍵排後、以原鍵名為標籤）；list/tuple → `- 項` 列點；更深巢狀以字串化收尾；數字／布林／None 跳過不拋錯。
- [x] 1.2 標籤映射擴充：`identity`→身分（Mapping 渲染 公開身分／隱秘身分 兩行、字串渲染單節 身分：…）、`appearance`→外觀、`social_connection`→人脈（以對象名為行鍵）；每節經 `_cap` 600、整塊經 block limit。
- [x] 1.3 `world/rules/tests/test_persona.py` 純邏輯案：巢狀 identity 兩行、字串 identity 單節、appearance 固定子鍵順序＋attire/feature、social_connection 對象名行、清單列點、未知形狀跳過、更深巢狀字串化收尾、單項截斷、整塊截斷、預設欄位集對字串值輸出不變、`public_view()` 剔除 hidden／字串 identity 原樣／記錄不被改動。同步重寫兩條舊契約迴歸鎖：`test_flatten_treats_non_string_fields_as_absent`（None／數字／布林仍跳過；清單／Mapping 改斷言渲染——本 delta 的 MODIFIED 契約）、`test_handler_has_no_write_api` 恰鍵集合納入 `public_view`。掛 `covers_requirement`（`persona-store::flatten-produces-one-bounded-labeled-prompt-block`；ID 隨 requirement 標題不變）。
- [x] 1.4 Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_persona`。

## 2. 注入欄位政策（world/ai/npc_dialogue.py 常數、typeclasses/npcs.py seam）

- [x] 2.1 `world/ai/npc_dialogue.py`：定義政策常數 `NPC_PERSONA_FIELDS`（全欄集 `("personality","life_story","habit","identity","appearance","social_connection")`）與 `PLAYER_PERSONA_FIELDS`（`("identity","appearance","social_connection")`）；`build_npc_dialogue_prompt` 簽名不動，空替換位元等值路徑不觸碰。
- [x] 2.2 `typeclasses/npcs.py::_persona_block()`：函式內區域匯入（對齊該檔 `world.ai.npc_dialogue` 既有慣例）後**直接引用常數**——NPC 塊 `self.persona.flatten(NPC_PERSONA_FIELDS)`；玩家塊 `character.persona.public_view().flatten(PLAYER_PERSONA_FIELDS)`（personality／life_story／habit／background 一律不在塊內）。
- [x] 2.3 測試（併入本組）：改寫 `typeclasses/tests/test_npc_dialogue.py::test_seam_injects_both_persona_blocks_and_never_mutates_the_records`（現行斷言 `player.persona == "性格：溫柔\n人生經歷：商人世家"` 為舊政策迴歸鎖，由本 delta 取代）——NPC 記錄含 identity{public,hidden}／appearance／social_connection，斷言 system 含 公開身分 與 隱秘身分 行；玩家記錄含全部欄位（含 background 與 identity{public,hidden}），斷言 `player.persona` 含 公開身分 值、外觀／人脈 標籤，且不含 隱秘身分 行、hidden 值、性格／人生經歷／習慣／背景 標籤或其值；兩記錄呼叫後不變。`test_seam_without_persona_injects_no_block_or_token` 與 `world/ai/tests/test_npc_dialogue_prompts.py` 的位元等值案原綠（無新建測試模組 → `.github/evennia-shards.json` 不動）。掛 `covers_requirement`（`persona-dialogue-injection` 兩條更新要求的 ID，維持現有標註）。
- [x] 2.4 Focused：`... evennia test --settings test_settings.py --keepdb world.ai`。

## 3. 校驗與收尾

- [x] 3.1 worst-case 尺寸檢查：最大 persona record（三 prose 600×3＋identity 兩層 600×2＋appearance 全子鍵＋長 social_connection 清單）渲染後 ≤ block limit（截斷路徑為預期行為時以斷言鎖截斷發生且確定性）。
- [x] 3.2 `uv run --locked python -m tools.spec_traceability check`；`openspec validate add-persona-depth-dialogue-injection --strict`。
- [x] 3.3 消極檢查：`rg "identity.hidden" world/ai/` 確認玩家側路徑無 hidden 引用；`rg "class PersonaStore" -A5 world/rules/persona.py` 確認寫入 API 仍為零（read-only handler 契約）。
- [ ] 3.4 終局：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --noinput --parallel 16 commands server typeclasses world` 一次（觸面在 world 與 typeclasses；commands/server 迴歸鎖住 look／persona_digest 預設路徑）。
