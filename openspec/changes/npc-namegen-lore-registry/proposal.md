# npc-namegen-lore-registry — Proposal

## Why

遊戲目前沒有系統化的姓名來源：LLM 未填 `display_name` 時離線 NPC 無名可用，在線時名字風格又完全依賴模型自由發揮。設計源頭 `docs/superpowers/specs/2026-09-03-npc-namegen-design.md` §1、§3 把已 vendor 化的 CC BY 4.0 語料（`third_party/fantasy-namegen/`，1,274 個零件、translit 零缺漏已驗證）收進一個 import 時凍結的 lore registry，作為後續規則層擲名（`world/rules/namegen.py`）、角色創建骰子與 NPC 補名兩個消費端的唯一語料真相。本 change 只蓋語料層；擲名與接線屬後續 change。

## What Changes

- 新增 `world/lore/names.py`：module import 時以純函式解析 `third_party/fantasy-namegen/data/packs/` 五個 pack JSON 與 `data/translit/fantasy.json`，凍結成 `NAME_PACK_REGISTRY`（frozen `NamePart`／`NamePack` dataclass ＋ `MappingProxyType`，欄位依設計 §3）與 `NAME_PACK_BY_RACE`（human→fantasy-human、elf→fantasy-elf、beastfolk→fantasy-orc；dwarf／halfling 入 registry 但 `race_key=None`，不綁族）。
- import 時不變量三條，違反即 import 失敗（fail-fast）：translit 表覆蓋全部零件（缺詞清單入錯誤訊息）、每包 m／f／u 池非空且 `NAME_PACK_BY_RACE` 只指向已註冊包、最長「名・姓」合成通過 `world/rules/character_creation.py` 的 `_validate_name`。
- 姓名合成常量 `NAME_SEPARATOR = "・"`（U+30FB）與合成 helper（`given.zh・surname.zh`）放在此層，作為 registry 內唯一合成常量，供 rules 層（後續 change）呼叫；名字原文（`NamePart.text`）永不進入合成輸出。
- `world/lore/sync.py::_ALL_REGISTRIES` 增 `NAME_PACK_REGISTRY`（category `"name_packs"`），`sync_all()` 照既有鏡接管線冪等鏡射；`lore-startup-sync` main spec 原文不動（先例：anchor-placement、wilderness-terrain）。
- `Containerfile` `app-layout` stage 增 `COPY third_party/ /app/third_party/`：`names.py` import 時讀語料，執行期映像必須烘焙，否則容器每次啟動即炸；`tests/test_container_contract.py` 加收錄契約斷言。
- 新增 `world/lore/tests/test_names.py`：三不變量、合成格式常量、覆蓋計數斷言，以及鏡射冪等的 Evennia 級斷言。
- 無玩家命令、無 wire／前端變動；`docs/game/commands.md` 不動。無相容層（未發布、零使用者）。

## Capabilities

### New Capabilities
- `namegen-corpus-registry`: vendored 姓名語料的凍結承載——`NAME_PACK_REGISTRY`／`NAME_PACK_BY_RACE` 的形狀與種族綁定、import 時三條不變量（translit 全覆蓋、池非空＋映射合法、最長合成名過 `_validate_name`）、`・` 合成格式常量與 helper、經 `sync_all()` 的冪等 LoreRecord 鏡射，以及執行期映像對語料的烘焙契約。

### Modified Capabilities

（無。）`lore-registries` 的既有 requirement 各自綁定具體 registry 模組，不約束新 registry 的形態；`lore-startup-sync` 的首條 requirement 明文列舉的是「該 change 定義的十個 registry」，新增鏡射對象沿用 anchor-placement／wilderness-terrain 先例——由新 capability 自己宣告鏡射並附加「lore-startup-sync spec 原文不動」_scenario_，不構成對既有 requirement 的修改。

## Impact

- 新增 `world/lore/names.py`、`world/lore/tests/test_names.py`；修改 `world/lore/sync.py`（`_ALL_REGISTRIES` 一列）、`Containerfile`（app-layout 一條 COPY）、`tests/test_container_contract.py`（烘焙契約斷言）。
- `world/lore/names.py` 對 `world/rules/character_creation.py::_validate_name` 的依賴以驗證函式內延遲 import 落地（先例：`world/lore/titles.py` 對 rules 的延遲 import），避免 lore→rules 頂層依賴；實測該延遲 import 執行期仍拖 Django／Evennia 匯入鏈，本模組定為 settings-required（所有消費者都在 bootstrap 後的 Evennia 程序內 import，見 design D5）。
- 測試執行：`world.lore.tests.test_names` 落在 evennia shard 的 `world.lore` label 涵蓋範圍內，需經 `tests.test_evennia_test_optimization_contract` 驗證歸屬。
- Traceability 標註時機：`namegen-corpus-registry` 的 canonical ID 要到 archive sync 才進 main index，提前標註會被 `tools.spec_traceability check` 以 unknown-requirement-id 打回（先例：movement-settlement-atomicity 4.1、title-fixed-core V2）；本 change 的測試先不掛 `@covers_requirement`，post-sync 章節統一補。
- 語料零變動：`third_party/fantasy-namegen/` 已 vendor 完畢，本 change 不重新抓上游。
- 下游（不在本 change）：`world/rules/namegen.py`、`creation_wizard` 骰子、`scene_builder` 補名。
