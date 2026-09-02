# add-persona-depth-dialogue-injection — Tasks

順序：renderer（PersonaStore）→ 欄位政策（npc_dialogue）→ 截斷／成本校驗。每組做完先跑該組 focused 測試再勾選。本變更與 A／B 檔案不相交，可平行執行。

## 1. PersonaStore 宽容渲染（world/rules/persona.py）

- [ ] 1.1 實作宽容渲染器：非空字串照渲染；Mapping → 「子鍵：值」行（已知鍵群宣告順序：`identity`→public,hidden；`appearance`→height,weight,measurement,style,overview,attire,feature；未知子鍵排後、以原鍵名為標籤）；list/tuple → `- 項` 列點；更深巢狀以字串化收尾；數字／布林／None 跳過不拋錯。
- [ ] 1.2 標籤映射擴充：`identity`→身分（Mapping 渲染 公開身分／隱秘身分 兩行、字串渲染單節 身分：…）、`appearance`→外觀、`social_connection`→人脈（以對象名為行鍵）；每節經 `_cap` 600、整塊經 block limit。
- [ ] 1.3 `world/rules/tests/test_persona.py` 純邏輯案：巢狀 identity 兩行、字串 identity 單節、appearance 固定子鍵順序＋attire/feature、social_connection 對象名行、清單列點、未知形狀跳過、更深巢狀字串化收尾、單項截斷、整塊截斷、預設欄位集輸出不變（既有案原綠）。掛 `covers_requirement`（`persona-store::flatten-produces-one-bounded-labeled-prompt-block` 更新後 ID 族；`tools.spec_traceability list` 取 canonical）。
- [ ] 1.4 Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_persona`。

## 2. 注入欄位政策（world/ai/npc_dialogue.py）

- [ ] 2.1 NPC 自身注入：`flatten` 呼叫改點名全欄集 `("personality","life_story","habit","identity","appearance","social_connection")`；空替換位元等值路徑不動。
- [ ] 2.2 玩家 public view：於 `PersonaStore`（或既有 record 讀取路徑）提供 public-only 視圖——`identity` 為 Mapping 時僅保留 `public` 子鍵的新 record 複製；字串 identity 原樣。呼叫端以該視圖 flatten 恰 `("identity","appearance","social_connection")` 欄位集構成 `player_persona`（personality／life_story／habit／background 一律不在塊內）。
- [ ] 2.3 測試（併入本組）：`world/ai/tests/`（或既有 npc_dialogue 測試模組）增——NPC 塊含 隱秘身分 與 公開身分 行、玩家塊含 公開身分 而無 隱秘身分 行與 hidden 值、玩家塊消極斷言無 性格／人生經歷／習慣／背景 標籤與三欄 prose 值且公開欄位存在、無 persona 玩家 payload 位元等值案原綠、無 persona NPC system message 位元等值案原綠。若新建測試模組則同變更註冊 `.github/evennia-shards.json` 並跑 `tests.test_evennia_test_optimization_contract`。掛 `covers_requirement`（`persona-dialogue-injection` 兩條更新要求的 ID）。
- [ ] 2.4 Focused：`... evennia test --settings test_settings.py --keepdb world.ai`。

## 3. 校驗與收尾

- [ ] 3.1 worst-case 尺寸檢查：最大 persona record（三 prose 600×3＋identity 兩層 600×2＋appearance 全子鍵＋長 social_connection 清單）渲染後 ≤ block limit（截斷路徑為預期行為時以斷言鎖截斷發生且確定性）。
- [ ] 3.2 `uv run --locked python -m tools.spec_traceability check`；`openspec validate add-persona-depth-dialogue-injection --strict`。
- [ ] 3.3 消極檢查：`rg "identity.hidden" world/ai/` 確認玩家側路徑無 hidden 引用；`rg "class PersonaStore" -A5 world/rules/persona.py` 確認寫入 API 仍為零（read-only handler 契約）。
- [ ] 3.4 終局：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --noinput --parallel 16 world` 一次（本變更全觸面在 world）。
