# npc-title-import-pipeline — Tasks

**前置**：`npc-title-identity-core` 必須先落地（`world/rules/npc_identity.py` 的 `validate_npc_title`／`MAX_NPC_TITLE_CODE_POINTS` 與 `NPC.npc_title` 都由它提供），且其 delta 已 sync 進 `openspec/specs/npc-identity-titles/spec.md`。在那之前本 change 不可開工。

實作順序即分組順序：schema ＋語意檢查 → 參考卡與文件（讓既有測試回綠）→ loader 落庫 → 重名 gate → 觀測性 → 收尾。每組做完先跑該組 focused 測試再勾選；全程不跑 CI shard 指令、不跑格式化／lint 工具（觀測性 lint 除外，它是 gate 不是格式化工具）。

估時：單人一個工作日內。若超時，優先保住第 1／2／3／4 組（欄位、落庫、唯一性），把第 5 組（觀測性事件）獨立成後續 change 並在此檔記錄。

## 1. Schema 必填 `title` 與語意檢查

- [ ] 1.1 動工前全 repo 搜尋字面量 `"record_type"` 與 `example_record`，列出所有**手寫**角色卡 dict（不經 `world/imports/tests/helpers.py::example_record()` 的）。已知匯入套件測試全部走該 helper；若搜出手寫卡，在第 2 組補完範例檔後逐一補 `title`，並把清單記在本檔。
- [ ] 1.2 `world/imports/schema.py`：module scope `from world.rules.npc_identity import MAX_NPC_TITLE_CODE_POINTS`（`npc_identity` module scope 只有 stdlib，無 typeclass／Evennia 匯入，離線 CLI 不受影響）。若前置 change 把上界宣告成模組私有名，於本批把它改成公開常量，**不**在 `schema.py` 硬寫 32。
- [ ] 1.3 `CHARACTER_SCHEMA_V1`：`required` 列在 `display_name` 之後插入 `"title"`；`properties` 新增設計 D1 的 `title` 定義（僅 `type`/`minLength` ＋英文 description，description 文字提及 strip 後上界常量與 `validate_npc_title` 為完整規則的唯一執行者）。**不**加 `pattern`、**不**加 `maxLength`（raw 長度檢查會與驗證器的 strip 語義分歧，見設計 D1）。注意不要動到 schema 自身的文件標題鍵 `"title": "CHARACTER_SCHEMA_V1"`（同名不同層級）。
- [ ] 1.4 `world/imports/validate.py`：module scope 匯入 `validate_npc_title`，新增 `_check_npc_title(record)`（設計 D2：非 `str` 直接回 `[]`，其餘把 `ValueError` 轉 `Issue("title", str(error))`），在 `validate_character` 的語意階段接在 `_check_entity_key_contract` 之後。**不**匯入 `world.observability`（設計 D8）。
- [ ] 1.5 `world/imports/tests/test_schema.py` 增測：缺 `title` 拒且 issue 指名 `title`；`title` property 僅含 `type`/`minLength`（無 `pattern`、無 `maxLength`）、description 提到 `validate_npc_title` 與上界；`CHARACTER_SCHEMA_V1["title"]` 仍為 `"CHARACTER_SCHEMA_V1"`。
- [ ] 1.6 `world/imports/tests/test_validation_semantics.py` 增測：含 ASCII 空白／U+3000／控制字元／`|` 的 `title` 各自被語意階段拒且指名 `title`；`"南門守衛"` 零 rejection 零 warning；`" 南門守衛 "` 通過驗證（strip 由驗證器負責，落庫形式在第 3 組驗）；**驗證器等價案**：`" " * 40 + "衛"`（raw 超界、strip 後合法）經完整 `validate_character` 零 issue——結構階段不得先於驗證器擋下它。
- [ ] 1.7 Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.imports.tests.test_schema world.imports.tests.test_validation_semantics`。

## 2. 參考角色卡與 GM 文件

- [ ] 2.1 `world/imports/examples/example_character.json` 補 `title`（zh-TW、無空白、≤上界，例如 `"參考範例"`），欄位位置緊接 `display_name`。倉庫內只有這一個角色卡檔（設計 §5 寫 `examples/*.json`，實際單檔）。
- [ ] 2.2 `docs/gm/characters.md` 必填欄位表新增 `title` 一列：非空白單行純文字、1–`MAX_NPC_TITLE_CODE_POINTS` code points、不得含空白（含全形空格）／控制字元／`|`；註記「只對 NPC 匯入生效，`PlayerCharacter` 角色卡此欄為惰性」。
- [ ] 2.3 同檔補一句：NPC 在房間人物列與探索面板顯示的姓名來自 `key`（`display_name` 目前仍不被載入器使用），要顯示中文姓名就把 `key` 寫成中文。**不**順手改寫其他欄位敘述（`subrace` 的既有描述漂移留給後續 change，見 design 的 Open Questions）。
- [ ] 2.4 同檔內嵌 JSON 範例（`altoria_scout`）補 `title`。
- [ ] 2.5 同檔「驗證角色卡」章節補責任線（設計 D4）：CLI 檢查檔案本身與批次內一致性；**與資料庫既有 NPC 的重名由 `load_batch()` 在載入時整批把關**，CLI 不做這件事。
- [ ] 2.6 `world/imports/tests/test_reference_example.py` 增斷言：參考卡 `title` 存在、通過 `validate_npc_title`、整檔仍零 rejection 零 warning。
- [ ] 2.7 Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.imports.tests.test_reference_example world.imports.tests.test_age_gate world.imports.tests.test_record_dispatch world.imports.tests.test_degraded_banner`（確認補欄後既有測試回綠）。

## 3. Loader 落庫與非 NPC 型別規則

- [ ] 3.1 `world/imports/loader.py::_instantiate_validated_character`：在 `entity.sex = ...` 之後、trait 套用之前（或緊接身分欄位區）加入設計 D3 的寫入——`if isinstance(entity, NPC): entity.npc_title = validate_npc_title(record["title"])`，附英文註解說明「只有 NPC 宣告了這個 `AttributeProperty`，寫到別的 typeclass 只會產生重載即消失的實例屬性」。
- [ ] 3.2 `world/imports/tests/test_loader_trait_values.py` 增測：匯入帶稱號記錄後 `entity.npc_title` 等於該稱號；`" 南門守衛 "` 落庫為 `"南門守衛"`；以 `typeclass=PlayerCharacter` 匯入同一張卡時記錄仍必須帶合法 `title`，但實體上 `attributes.get("npc_title")` 為 `None`（無持久化）。
- [ ] 3.3 同檔增測：既有 verbatim 斷言（traits／persona／sexual／skills／equipment／inventory／affinity／age／portrait_policy）在新增欄位後全部不變。
- [ ] 3.4 端到端顯示串接測（放 `world/imports/tests/test_loader_trait_values.py` 或既有 appearance 測試模組，擇一，不新增測試檔）：匯入的 NPC 經 `npc_display_name` 得到「姓名　稱號」，未經任何顯示層改動。
- [ ] 3.5 Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.imports.tests.test_loader_trait_values`。

## 4. 對既有 NPC 的重名 gate

- [ ] 4.1 `world/imports/loader.py` 新增模組私有 `_flag_existing_npc_names(report)`（或等價形狀）：收集報告內 character records 的 `key`，以 `NPC.objects.filter_family(db_key__in=sorted(keys)).values_list("db_key", flat=True)` 查覆（設計 D5：`NPC.objects.filter` 是 typeclass-path 精確比對，會漏掉 `LLMNPC`），命中者在對應 `RecordReport.rejections` 追加 `Issue("key", ...)`，訊息為穩定英文 identifier。
- [ ] 4.2 `load_batch`：在 `transaction.atomic()` 內、任何 `_instantiate_validated_character` 之前呼叫該檢查；有命中即 `raise ImportRejected(report)`（交易回滾、零實體）。`instantiate_character` 單筆入口套用同一個檢查。**不**重用既有實體、不改名、不覆寫（設計 D6）。
- [ ] 4.3 `world/imports/tests/test_batch_all_or_nothing.py` 增測：先建一隻同名 `NPC`，再載入含該 key 的兩筆批次 → `ImportRejected`，報告中該筆帶 `key` rejection，另一筆也未建立；既有 NPC 的 key／`npc_title`／其他欄位不變。
- [ ] 4.4 同檔增測：既有實體是 `LLMNPC`（子類）時同樣被拒（釘住 `filter_family` 的家族覆蓋）；以 `typeclass=PlayerCharacter` 載入同樣被拒；既有同名者是 `PlayerCharacter`／`Monster`／房間／物件時**不**被此 gate 拒。
- [ ] 4.5 同檔增測：批次內重複 key 的既有拒絕行為不變，且與新 gate 並存（兩筆重複 key 且其中之一又撞既有 NPC 時仍整批拒）。
- [ ] 4.6 CLI 責任線測（`world/imports/tests/test_batch_all_or_nothing.py`）：撞名的記錄檔經 `validate_batch` 全綠、`main([...])` 回 0，但同一檔進 `load_batch` 被拒；`report.degraded_checks` 未新增任何條目。
- [ ] 4.7 Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.imports.tests.test_batch_all_or_nothing world.imports.tests.test_import_portrait_seam`。

## 5. 觀測性邊界事件

- [ ] 5.1 `world/imports/loader.py`：`from world.observability import log_info, log_warn`（具名匯入）。`load_batch` 提交後 `log_info("import_batch_committed", context={"records": len(entities), "typeclass": typeclass.__name__})`；兩個拒絕點各 `log_warn("import_batch_rejected", context={...,"reason": "validation" | "existing_npc_name"})`。context 只放計數／型別名／理由碼，不放稱號字串或玩家文案。
- [ ] 5.2 `world/imports/tests/test_batch_all_or_nothing.py` 增測：以 patch **呼叫端模組綁定**（`world.imports.loader.log_info`／`log_warn`，不 patch `world.observability.*`）斷言提交批次恰一條 info、兩種拒絕各帶對應 `reason`。
- [ ] 5.3 `uv run --locked python -m tools.observability_lint check` exit 0；確認 `world/imports/validate.py` 仍未匯入 facade（其兩個 `except` 區塊維持在 R2 作用域外），`tools/observability_freeze.json` 仍為空清單、未新增條目。

## 6. 登記、可追溯性與收尾

- [ ] 6.1 `.github/evennia-shards.json` 不需改動（本 change 不新增測試模組，全部加進既有模組）。以 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract` 確認契約仍綠。
- [ ] 6.2 依 `.agents/skills/openspec-sync-specs` 把本 change 的 delta 同步進 `openspec/specs/npc-identity-titles/spec.md`（該主規格由 `npc-title-identity-core` 先建立；本 change 只追加自己的 requirement，不改寫既有段落），再以 `uv run --locked python -m tools.spec_traceability list` 取 canonical requirement ID——ID 一律以工具輸出為準，不手工拼。
- [ ] 6.3 掛 `covers_requirement` 標註（參數必須是字面值 ID，`from tools.spec_traceability import covers_requirement`）：必填 `title` 欄位契約→1.5／1.6；loader 落庫與非 NPC 規則→3.2；既有 NPC 重名 gate→4.3／4.4；CLI 檔案作用域→4.6；參考卡與 GM 文件→2.6；邊界事件→5.2；既有匯入契約不變→3.3。跑 `uv run --locked python -m tools.spec_traceability check` 至零錯誤、本 change 的七條 requirement 全覆蓋。
- [ ] 6.4 消極檢查：`docs/game/commands.md`／`docs/game/command-reference.md` 零改動（無命令面變更），`tests/test_command_docs.py` 綠；未觸及 `world/rules/npc_identity.py`（前置 change 的檔案）、`typeclasses/`、`web/`；未觸及 `world/lore/names.py`／`world/rules/namegen.py`（namegen 系列 change 的檔案）；未新增任何相容層、`schema_version` 分支或遷移程式碼。
- [ ] 6.5 `openspec validate npc-title-import-pipeline --strict` 與 `openspec validate --all --strict` 皆通過；`git diff --check` 乾淨。
- [ ] 6.6 終局驗證一次：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --noinput --parallel 16 world.imports world.quests world.skills world.rules typeclasses`（涵蓋匯入本體，加上會呼叫 `instantiate_character` 的相鄰套件）。

## 7. 本 change 明確不做（延後，非遺漏）

以下項目屬設計文件範圍但由其他 change 承接，實作時不要順手做：

- blueprint `npc_req` 的 `display_name`／`title` 必填、`SHOP_REGISTRY` host 欄位、`GUILD_RANK_REGISTRY` examiner 欄位、`world/rules/guild_economy.py`／`guild_exams.py` 的生成路徑與其 boundary event（change 3）。
- SceneBuilder 具名佔用者同步的冪等語義（設計 §3.2 明文沿用既有行為，非作者供給面）。
- 讓 `display_name` 成為 NPC 的顯示姓名，或把它納入唯一性檢查（設計未授權，見 design D7）。
- 把匯入的稱號送進 LLM 系統訊息（需改 `prompts/npc_dialogue.yaml` 並重錄基準線；change 1 已把 `_npc_context()["title"]` 留為前置 seam）。
- 修正 `openspec/specs/import-validation` 與 `docs/gm/characters.md` 中「`subrace` 為選填」的既有漂移（與本 change 無因果關係）。
- `Monster` 稱號、玩家稱號系統任何改動、runtime 改稱號、多語言與顏色 markup（設計 §9 範圍外）。
