# namegen-npc-flow — Tasks

前置：`npc-namegen-lore-registry`、`npc-namegen-rules-roller` 已落地（`world/lore/names.py`、`world/rules/namegen.py` 可用）。

## 1. Prompt 階段：靈感名注入

- [ ] 1.1 `world/prompts/registry.py`：`PromptSpec("scenario_director.system", "scenario_director.yaml")` 的 allowlist 改為 `("name_inspiration",)`
- [ ] 1.2 `prompts/scenario_director.yaml`：在既有 system 文字中加入命名指引句（建議填寫 `display_name`、風格可參考建議名、可依性別／背景調整；`display_name` 維持選填的措辭）與 `{name_inspiration}` token；文字仍受 4096 `max_length` 界內
- [ ] 1.3 `world/ai/scenario_director.py`：新增模組級常量靈感庫數量 N（=6）與私有 `_name_inspirations(bounded_context_text: str) -> str`——`seed = zlib.crc32(bounded_context_text.encode())`，擲 N 個 `roll_name_for_race(None, "", Random(seed))`（同一 `Random` 依序抽，組合成一段以、分隔的文字）；`build_scenario_prompt` 改呼叫 `render_prompt("scenario_director.system", name_inspiration=...)`；`from world.rules.namegen import roll_name_for_race`（named import、call-site 建 `Random`）。`SCENARIO_DIRECTOR_OUTPUT_SCHEMA`、`_VALIDATORS`、`_CONTEXT_KEYS`／`_bounded_context` 鍵集不動

## 2. Spawn 階段：兜底補名

- [ ] 2.1 `world/quests/scene_builder.py`：`_materialize_instance` 把 `record.definition_key`（＝`definition.key`）與 `record.stage_index` 沿 `_spawn_occupants(..., definition_key, stage_index)` → `_spawn_npc(..., definition_key, stage_index)` 顯式傳參（尾端 keyword 參數）
- [ ] 2.2 `_spawn_npc` 於 `_apply_characterization(...)` 之後：`if npc.db.display_name is None:` → `npc.db.display_name = roll_name_for_race(npc.race or None, npc.sex or None, Random(zlib.crc32(f"{definition_key}:{stage_index}:{role}".encode())))`，隨後發事件（2.3）。`_apply_characterization` 本體與 authored 名應用路徑不動；`_spawn_monster` 不動
- [ ] 2.3 觀察性：import 列改 `from world.observability import log_info, log_warn`；補名後發 `log_info("npc_name_fallback", context={"quest": <quest_id>, "definition_key": definition_key, "stage": stage_index, "role": role, "name": <rolled>})`（quest_id 經 `_spawn_occupants` 一併傳入或以參數鏈傳遞）

## 3. 邊界放行

- [ ] 3.1 `tests/test_ai_transport_contract.py`：`READ_ONLY_RULE_MODULES` 增 `"world.rules.namegen"`，註註釋（純函式、無 DB／Evennia import、無狀態寫入；來源 change：namegen-npc-flow design D6）

## 4. 測試

- [ ] 4.1 scene_builder 測（擴充 `world/quests/tests/test_scene_builder.py`，`EvenniaTest`）：(a) `display_name=None` 佔用者補名且以同 `definition.key:stage_index:role` 種子重放必得同名（對照直接呼叫 `roll_name_for_race` 的预期值）；(b) characterization 帶 `display_name`（含模擬「黑鬍」）時不覆寫、不擲名；(c) 無 characterization 的 generic 佔用者有名、race 取 tier 的 `race_key`、race 缺席時走隨機包仍產出合成名；(d) 回滾路径無殘留
- [ ] 4.2 observability 事件測（併入 4.1 module 或 `test_quests_observability.py` 風格）：補名路徑以 `patch("world.quests.scene_builder.log_info")` 斷言恰一條 `npc_name_fallback`、context 含 quest／definition_key／stage／role；authored 名路徑零事件
- [ ] 4.3 prompt 組裝測（擴充 `world/ai/tests/test_scenario_director_prompts.py`）：(a) system 訊息含靈感名（斷言渲染後含庫中至少一個名字與「僅供靈感」指引措辭）；(b) 同 context 兩次呼叫位元組相同（含庫）；(c) schema 必填性不動——`SCENARIO_DIRECTOR_OUTPUT_SCHEMA` 的 `npc_req.display_name` 仍為選填型別、不含 inspiration 名單；(d) validator 不變——不帶 `display_name` 與帶非庫名的 blueprint 仍照既有測試通過守欄
- [ ] 4.4 prompt-library 側測（`world/prompts/tests/`，依既有 loader 測試形態）：`scenario_director.system` allowlist 恰為 `name_inspiration`；shipped YAML 含 token 與指引句；`{name_inspiraton}` 錯字被 loader 拒絕
- [ ] 4.5 契約測試確認：`tests/test_ai_transport_contract.py` 全套通過（放行生效、其他 `world.rules` import 仍被拒）；prompt 組合零狀態寫入（`build_scenario_prompt` 前後 DB／registry 無變化的斷言，可入 4.3）

## 5. Shards 與 traceability

- [ ] 5.1 `.github/evennia-shards.json` 實查：本 change 只擴充既有 test module——`world.quests`（含 `world.quests.tests.*`）、`world.ai`、`world.prompts` 皆為 shard 4／5 的 package label、遞迴涵蓋新增測試函數；跑 `uv run --locked python -m unittest tests.test_evennia_test_optimization_contract` 中 owns-every-module 測試確認 manifest 零改動即綠（若實作期新開 top-level `test_*.py`，改該檔落點或顯式入 manifest 同 label shard）
- [ ] 5.2 每個新增／改動測試函數補 `@covers_requirement` 標註（`tools.spec_traceability`），capability 名對齊本 change delta：`scene-builder`、`scenario-director`、`prompt-library`；跑 `uv run --locked python -m tools.spec_traceability check` 修到綠

## 6. 收尾

- [ ] 6.1 `docs/game/commands.md` 確認不動（無新玩家命令）；不建相容層／遷移
- [ ] 6.2 `openspec validate namegen-npc-flow --strict` 通過
