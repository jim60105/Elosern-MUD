# npc-title-import-pipeline — Proposal

## Why

`npc-title-identity-core` 立起了 NPC 稱號的驗證器（`world/rules/npc_identity.py::validate_npc_title`）、`NPC.npc_title` 屬性與三個顯示表面，但**沒有任何寫入點**——所有 NPC 的稱號都還是預設 `""`，房間人物列與探索面板一律退化成純姓名。已核准設計 `docs/superpowers/specs/2026-09-03-npc-identity-titles-design.md` §5 指定的第一個作者供給面就是 JSON 匯入：角色卡是目前唯一有文件、有 CLI、有 all-or-nothing 語義的 NPC 建立管道（`docs/gm/characters.md`）。本 change 把稱號接進這條管道，並補上設計 §3.2 不變式 2 在作者面缺的那一半——姓名全世界唯一。

## What Changes

- `CHARACTER_SCHEMA_V1`（`world/imports/schema.py`）新增**必填** `title`：`{"type": "string", "minLength": 1, "maxLength": MAX_NPC_TITLE_CODE_POINTS}`，上界常量直接從 `world.rules.npc_identity` 匯入（沿用 `key` 從 `world/art/subjects.py` 取常量的既有慣例）。字元集規則（空白／控制字元／`|`）**不**在 schema 複製一份 regex，由語意層唯一驗證器 `validate_npc_title` 執行。**BREAKING**（對現有角色卡）：直接改 v1，無相容層、無遷移、無 `schema_version` 2（未發布、零使用者）。
- `world/imports/validate.py` 新增語意檢查 `_check_npc_title`：把 `validate_npc_title` 的例外轉成 record 級 `Issue("title", ...)`，訊息為穩定英文 identifier，與既有 `Issue` 診斷同形；`validate.py` 不新增任何 DB 存取，離線 CLI 維持純檔案檢查。
- `world/imports/loader.py::_instantiate_validated_character` 在驗證後寫 `entity.npc_title = validate_npc_title(record["title"])`（fail-closed 的第二道，且回傳的是 strip 後的正規形）。**只在 `isinstance(entity, NPC)` 時寫**：`npc_title` 是 `NPC` 上的 `AttributeProperty`，寫到 `PlayerCharacter` 上只會產生一個重載即消失的普通實例屬性（靜默資料遺失）。
- 姓名全世界唯一（設計 §3.2 不變式 2 的 import 面）：批次內重複 `key` 既有檢查不動（`_flag_duplicate_keys`），新增**對既有 DB NPC 的重名檢查**，落點在 `loader.py`（不在 `validate.py`）。命中即整批拒絕、零實體落庫，診斷掛在該筆 record 上（`ImportRejected.report` 與既有 `render_report` 形狀不變）。
- 明確定義碰撞語義：匯入記錄的 `key` 撞上既有 NPC（含 `LLMNPC` 等子類）→ **fail closed 整批拒**，不重用、不改名、不覆寫；撞上既有玩家角色、房間或物件 → 不因此拒（本不變式只約束 NPC 姓名）；批次目標型別是 `PlayerCharacter` 時同樣套用（世界上不會有兩個實體回應同一個 NPC 姓名）。
- `world/imports/examples/example_character.json` 補 `title`；`docs/gm/characters.md` 的必填欄位表、內嵌 JSON 範例與驗證章節同步（補一句：離線 CLI 不檢查與 DB 既有 NPC 的重名，該檢查在 `load_batch()` 執行）。
- 觀測性：`loader.py` 新增兩個邊界事件 `import_batch_committed`（info）與 `import_batch_rejected`（warn），走 `world.observability` facade。設計 §8 說「import loader 已有 `action_commit` 類語義」——實際上 `world/imports/loader.py` 目前一行 log 都沒有，這是目錄（觀測性設計 §4.2）在持久化提交邊界留下的真實缺口，由本 change 補上。`validate.py` **不**匯入 facade（它的兩個既有 `except` 區塊會因此進入 R2 作用域）。
- 無玩家命令新增／改名／改語法 → `docs/game/commands.md`、`docs/game/command-reference.md` 不動。

## Capabilities

### New Capabilities

（無。）

### Modified Capabilities

- `npc-identity-titles`（由 `npc-title-identity-core` 建立、尚未 sync 進 `openspec/specs/`）：本 change 以 delta 對**同一個 capability** 追加設計 §5／§6 的作者供給 requirement——匯入記錄的必填 `title` 欄位契約、loader 的落庫規則與非 NPC 型別的不寫入規則、匯入面的姓名全世界唯一（批次內＋對既有 NPC）與整批拒絕診斷、參考角色卡與 GM 文件的欄位同步，以及匯入提交／拒絕的邊界事件。change 1 已宣告的核心與顯示 requirement 一條都不重述、不改寫。

  `import-schema`／`import-validation`／`import-loader`／`import-reference-example` 四個既有 capability 的 requirement 原文**不需修改**：它們沒有任何一條窮舉 `CHARACTER_SCHEMA_V1` 的必填欄位集合，也沒有一條規定「例外只有既有欄位」；新增欄位不推翻其中任何一句。`import-reference-example` 要求參考卡零 rejection、零 warning——補上 `title` 正是維持該條為真的動作。因此新行為由 `npc-identity-titles` 自行宣告，並附「既有匯入契約原文不動」的迴歸 scenario（先例：change 1 對 `localized-appearance`／`webclient-exploration-menu` 的處理）。

## Impact

- 修改：`world/imports/schema.py`（`title` property ＋ required 列）、`world/imports/validate.py`（`_check_npc_title` 語意檢查）、`world/imports/loader.py`（稱號落庫、既有 NPC 重名 gate、兩個 boundary event）、`world/imports/examples/example_character.json`、`docs/gm/characters.md`。
- 測試觸面（全部加進既有模組，**不新增測試檔** → `.github/evennia-shards.json` 不動）：`world/imports/tests/test_schema.py`、`test_validation_semantics.py`、`test_loader_trait_values.py`、`test_batch_all_or_nothing.py`、`test_reference_example.py`。
- 連帶修正：任何**不經** `world/imports/tests/helpers.py::example_record()` 而以字面 dict 組角色卡的既有測試會因必填 `title` 轉紅，需補欄（實作第一步即全 repo 搜尋確認；目前已知的匯入測試全部走 `example_record()`，其他套件的 `instantiate_character` 呼叫端亦然）。
- 觀測性：`world/imports/loader.py` 成為 facade adopter（該檔無 `except` 區塊，R2 零影響）；`tools/observability_freeze.json` 為空清單、不動。
- 依賴：**嚴格前置 `npc-title-identity-core`**。本 change 匯入的 `validate_npc_title`／`MAX_NPC_TITLE_CODE_POINTS` 與寫入的 `NPC.npc_title` 都由它定義；主規格 capability `npc-identity-titles` 也必須先由它 sync 進 `openspec/specs/`，本 change 的 `covers_requirement` 標註才有 canonical ID 可取。
- 與 change 3（blueprint `npc_req`、`SHOP_REGISTRY`／`GUILD_RANK_REGISTRY` 作者供給）**檔案零交集**：本 change 只動 `world/imports/`；change 3 動 `world/ai/director_templates.py`、`world/quests/`、`world/rules/guild_economy.py`／`guild_exams.py`。兩者只在同一份 delta spec 檔上相鄰（各自追加 requirement 區塊）。
- 與進行中的 namegen 系列（`world/lore/names.py`、`world/rules/namegen.py`、creation UI）檔案零交集：本 change 不規定姓名從何而來，只規定作者供給的姓名進 DB 前必須唯一。
