# namegen-npc-flow

## Why

NPC 側目前沒有系統化姓名來源：LLM 沒填 `BlueprintNpcReq.display_name` 時名字就缺失，離線模板路徑僅有一個寫死的「黑鬍」，在線時名字風格又完全依賴模型自由發揮。前置 change 已交付語料層（`world/lore/names.py`）與規則層（`world/rules/namegen.py::roll_name`／`roll_name_for_race`），本 change 把擲名接進 NPC 生成流（設計源頭 `docs/superpowers/specs/2026-09-03-npc-namegen-design.md` §6）：prompt 階段給 LLM「僅供靈感」的建議名錨定語料風格，spawn 階段對缺失名做確定性兜底補名，保證每個場景 NPC 必然有名且同藍圖重放同名。

## What Changes

- **Prompt 階段（靈感名）**：`world/ai/scenario_director.py::build_scenario_prompt` 組裝 `scenario_director.system` 時，以 `roll_name_for_race(None, "", Random(crc32(序列化請求上下文)))` 擲一組固定數量的靈感名，經 `world/prompts/registry.py` 新增的 `name_inspiration` 佔位符注入；`prompts/scenario_director.yaml` 文字加上「僅供靈感、可依性別／背景改寫、建議填寫 `display_name`」的命名指引。**JSON schema 必填性不動（`display_name` 維持選填）、validator 不動。**
  - 注意：設計 §6.1 逐槽位種子 `crc32(f"{definition_key}:{stage}:{role}")` 在 prompt 時尚不可計算——請求時藍圖、stage、role 與 `QuestDefinition.key`（compile 期的內容摘要）皆尚未存在。工件採「脈絡種子靈感名庫」實現同一靈感意圖（見 design D1），spawn 側仍維持設計原式種子。
- **Spawn 階段（兜底補名）**：`world/quests/scene_builder.py::_apply_characterization()` 對沒有 authored `display_name` 的佔用者（含無 characterization 的 generic 佔用者）呼叫 `roll_name_for_race(race_key, sex, Random(crc32(f"{definition.key}:{stage_index}:{role}")))` 寫入 `npc.db.display_name`；`race_key`／`sex` 從 NPC 原型取（`npc.race`／`npc.sex`，取不到傳 `None` 走隨機包），補名處經 `world.observability` facade 發 info 事件（context 帶 quest／stage／role）。LLM（或模板「黑鬍」）已填的名字絕不覆寫，`world/ai/director_templates.py` 無需改動。
- `tests/test_ai_transport_contract.py` 的 `READ_ONLY_RULE_MODULES` 放行 `world.rules.namegen`（prompt 層唯讀規則，見 design D6）。
- 無新玩家命令；`docs/game/commands.md` 不動。無相容層、無遷移。

## Capabilities

### New Capabilities

（無——全部歸入既有 capability 的 delta。）

### Modified Capabilities

- `scenario-director`：`build_scenario_prompt` 的 system 訊息改為「prompt 庫文字 ＋ 確定性靈感名渲染」；同輸入仍必得位元組相同 prompt；`display_name` 選填性與語意驗證器完全不變。
- `prompt-library`：`scenario_director.system` 的佔位符白名單新增 `name_inspiration`，YAML 文字承載命名指引句；載入／渲染契約不變。
- `scene-builder`：佔用者落地路徑新增「無 authored 名時以 crc32 種子確定性補名＋觀察性事件」要求；既有 authored characterization（含「黑鬍」模板）應用路徑不變。

## Impact

- `world/ai/scenario_director.py`（靈感名銀行＋種子渲染）、`world/prompts/registry.py`（`scenario_director.system` allowlist）、`prompts/scenario_director.yaml`（命名指引＋`{name_inspiration}` token）、`world/quests/scene_builder.py`（`_materialize_instance`→`_spawn_occupants`→`_spawn_npc`→`_apply_characterization` 執行 `definition_key`／`stage_index`，兜底補名＋`log_info`）、`tests/test_ai_transport_contract.py`（唯讀規則放行）。
- 不動清單：`world/ai/director_templates.py`、`SCENARIO_DIRECTOR_OUTPUT_SCHEMA`、`_VALIDATORS`、`_bounded_context` 的脈絡鍵、`world/lore/names.py`、`world/rules/namegen.py`、`docs/game/commands.md`。
- 測試：擴充既有 module（`world/quests/tests/test_scene_builder*.py`、`world/ai/tests/test_scenario_director_prompts.py`、`world/prompts/tests/`），皆落在 `.github/evennia-shards.json` shard 4／5 既有 package label 遞迴涵蓋範圍內，manifest 不需改動（以 owns-every-module 契約測試驗證）。
- 依賴鏈：`npc-namegen-lore-registry`（NAME_PACK_REGISTRY）→ `npc-namegen-rules-roller`（roll_name／roll_name_for_race）→ 本 change。前置未落地時本 change import 即 fail-fast，屬正確順序依賴，不預寫防呆。
