# npc-namegen-rules-roller — Proposal

## Why

語料層 change（`npc-namegen-lore-registry`）把 vendored 姓名語料凍結成 `NAME_PACK_REGISTRY`／`NAME_PACK_BY_RACE`，但目前沒有任何程式碼能從中「擲出一個名字」：角色創建骰子與 NPC 補名兩個消費端（`namegen-creation-ui`、`namegen-npc-flow`）都只差這一個規則層。設計源頭 `docs/superpowers/specs/2026-09-03-npc-namegen-design.md` §4 把擲名規則收成 `world/rules/namegen.py` 的兩個純函式——無 DB、無 Evennia import、RNG 一律由呼叫端注入，是擲名的唯一實作點。本 change 只蓋規則層；接線屬後續 change。

## What Changes

- 新增 `world/rules/namegen.py` 純函式模組：
  - `roll_name(pack_key, sex, rng) -> str`：依 `pack_key` 取包、依 `sex` 選池（`female`→f、`male`→m、`other`→u 池優先、空字串或 `None`→以 `rng` 隨機挑一池），回傳經 lore 層 `compose_display_name` 合成的「名・姓」譯名。
  - `roll_name_for_race(race_key, sex, rng) -> str`：先經 `NAME_PACK_BY_RACE` 解析包；`race_key` 為 `None` 或無映射時，以 `rng` 隨機挑一個**有 `race_key` 綁定**的包（`fantasy-dwarf`／`fantasy-halfling` 不參與隨機兜底）。
- 錯誤語意：未知 `pack_key` → 直接 `KeyError`（呼叫端是程式內常量，不吞）；過濾後池為空 → 退回該包全池，產生器絕不死掉。
- 可重放性由呼叫端負責：函式一律吃注入的 `random.Random`，內部永不自建 RNG。雙策略（UI 骰用模組級無種子 `Random()`、NPC 側用 `Random(crc32(f"{definition.key}:{stage}:{role}"))`，設計 §4）由兩個消費端 change 各自落地，本 change 只保證「同 `rng` 狀態必得同名」的純函式契約。
- 新增 `world/rules/tests/test_namegen.py`（`unittest.TestCase`）：固定種子重放、sex→池映射、`other`→u 池優先、空池退回、未知包 `KeyError`、隨機兜底只用有綁定的包。
- 新增 test module 需顯式加入 `.github/evennia-shards.json`（`world.rules` 側三個 shard 全用顯式模組 label，無 package label 可遞迴涵蓋，與 lore change 的情境相反）。
- 無玩家命令、無 wire／前端變動；`docs/game/commands.md` 不動。無相容層（未發布、零使用者）。

## Capabilities

### New Capabilities
- `npc-name-generation`: 規則層擲名——`roll_name` 的 sex→池映射與「名・姓」合成輸出、`roll_name_for_race` 的種族解析與「只用有綁定包」隨機兜底、`KeyError`／空池退回的錯誤語意，以及「函式吃注入 `rng`、同狀態必得同名」的可重放契約（雙 RNG 策略由呼叫端種子保證）。

### Modified Capabilities

（無。）本 change 只讀 `namegen-corpus-registry` 定義的 registry 契約，不改其任何 requirement；`lore-registries`、`lore-startup-sync`、`entity-sex-vocabulary` 的既有條款均不受觸及（sex 詞彙以呼叫端傳入字串值消費，`namegen.py` 不改寫 `world/lore/sex.py`）。

## Impact

- 新增 `world/rules/namegen.py`、`world/rules/tests/test_namegen.py`；修改 `.github/evennia-shards.json`（shard 2 `rules-b` 的 labels 增一列）。
- **依賴順序**：必須在 `npc-namegen-lore-registry` 實作落地後始可動工——本 change import 其 `NAME_PACK_REGISTRY`／`NAME_PACK_BY_RACE`／`compose_display_name`（`NAME_SEPARATOR` 經 helper 間接使用，`namegen.py` 不自帶分隔符常量）與 `NamePart`／`NamePack` 欄位契約（`given` 鍵恰 `m`／`f`／`u`、`race_key: str | None`）。下游 `namegen-creation-ui`（無種子骰）與 `namegen-npc-flow`（crc32 種子＋`action_commit` 事件）都在本 change 之後，各自持有任何 RNG 策略與觀察性。
- 依賴方向符合單向契約：`rules/namegen` 只讀 `lore`，無 DB、無 Evennia import，不寫任何狀態（`world/ai/` 無關）。
- 語料零變動：`third_party/fantasy-namegen/` 不動，不重新抓上游。