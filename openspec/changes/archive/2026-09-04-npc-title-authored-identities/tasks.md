# npc-title-authored-identities — Tasks

前置（已滿足，2026-09-04）：`npc-title-identity-core` 與 `npc-title-import-pipeline` 均已落地並
歸檔——`world/rules/npc_identity.py::validate_npc_title`、`MAX_NPC_TITLE_CODE_POINTS`、
`NPC.npc_title`、主規格 capability `npc-identity-titles`（17 條）都在 master 上。本 change 是
NPC-title 批次的最後一件。

## 0. Artifacts（先於程式碼；使用者核定 2026-09-04，design D11）

- [x] 0.1 新增 `specs/scene-builder/spec.md`：以 `## REMOVED Requirements` 撤除主規格兩條 crc32
  兜底補名 requirement（含 Reason／Migration，先例：archived `2026-08-13-overwhelm-log-attribution`）。
- [x] 0.2 `specs/scenario-director/spec.md`：補兩條 MODIFIED——prompt 規格（靈感庫保留、必填敘述
  取代「recommended but optional」、删「缺 display_name 照樣通過」scenario）與 compile 邊界規格
  （digest 欄位清單含必填 `title`、field-less scenario 改寫）。
- [x] 0.3 design D11／proposal 同步折入（REMOVED 範圍、prompt 文案改寫、設計文件作廢標註、
  前置落地狀態校正）。
- [x] 0.4 `docs/superpowers/specs/2026-09-03-npc-namegen-design.md`：§6.2 spawn 兜底段落明文標註
  由本 change 撤回（§2 決策表「NPC 整合」列與 §9 測試預期同步；§6.1 靈感庫不動）。設計文件勝出
  規則要求撤回必須明文。
- [x] 0.5 新增 `specs/prompt-library/spec.md`：MODIFIED `The scenario-director key is registered
  with the name-inspiration placeholder and carries the naming guidance`（出貨 YAML 指導句的
  「recommended, not required」措辭被必填推翻；rubber-duck 計畫審閱 BLOCKER 1）。

## 1. Shared name rule

- [x] 1.1 在 `world/rules/npc_identity.py` 新增 `MAX_NPC_NAME_CODE_POINTS = 64` 與
  `validate_npc_name(value) -> str`（design D3 規則：`str`、strip 後 1–64 code points、拒控制字元、
  拒 `|`、拒全形空格 U+3000、允許一般 ASCII 空白；回傳 strip 後正規形），module scope 維持 stdlib-only。
- [x] 1.2 在 `world/rules/tests/` 的 npc_identity 測試模組補 `validate_npc_name` 邊界測試
  （空、過長、控制字元、`|`、U+3000、含一般空白允許、strip 正規形）。
  Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests`

## 2. Registry authored identities (lore)

- [x] 2.1 `world/lore/shops.py`：`ShopDefinition` 新增**無預設值**必填欄 `host_name`／`host_title`，
  補齊 `altoria_general_store` 列的作者值（zh-TW 姓名＋職稱），模組尾端以延遲匯入的
  `validate_npc_name`／`validate_npc_title` 對純函式 row validator 跑載入驗證（違規 → 具名 `ValueError`）。
- [x] 2.2 `world/lore/guild.py`：`GuildRank` 新增必填 `examiner_name`／`examiner_title`（七列各補作者值），
  `GuildBranch` 新增必填 `host_name`／`host_title`（`guild_branch_altoria` 補作者值）；
  同檔 row validator＋載入驗證（design D9 先例：`world/lore/titles.py`）。
- [x] 2.3 實作跨 registry 作者姓名唯一性純檢查（shops＋guild branches＋ranks 三組姓名互不重複，
  違規具名 `ValueError`），由兩檔載入流程呼叫（design D9）。
- [x] 2.4 `world/lore/tests/test_guild.py` 與 shops 對應測試：缺欄 `TypeError`、違規值具名
  `ValueError`、跨 registry 重名拒、出貨 registries 載入-clean 斷言；確認 `world/lore/sync.py`
  的 `asdict` 鏡射自動帶新欄且冪等（`GUILD_RANK_REGISTRY` 已在鏡射清單；`SHOP_REGISTRY` 不在，不動）。
  Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.lore.tests.test_guild`

## 3. Guild service hosts (rules)

- [x] 3.1 `world/rules/guild_economy.py::_sync_service_host` 改為 design D7 形狀：以元件
  `service_id` 錨找既有 host（`_host_by_service_id`，走 NPC family 掃描，與
  `_initialize_merchant_stock` 同形）；缺則 `create_object(NPC, key=validate_npc_name(host_name))`
  ＋ `host.npc_title = validate_npc_title(host_title)`；既存永不改名、**永不補寫稱號**
  （runtime 寫稱號即違反不可變契約，design D7 第 3 條）；其餘
  既有更新語義（location／race／成年身分／補元件）原封不動。
- [x] 3.1b 一次性 legacy cleanup：刪除前功能時代以 `altoria_guild_master`／`altoria_merchant`
  為 `key` 且無稱號的 host（下一次同步即以完整作者身分重建）。放在啟動同步的一次性分支或明確的
  dev-only cleanup 指令，不新增任何持續運行的遷移路徑（未發布、零使用者、clean cutover）。
- [x] 3.2 呼叫端（shop host 與 guild-branch host 兩條同步線）從 `SHOP_REGISTRY.host_name/host_title`
  與 `GuildBranch.host_name/host_title` 供給參數；`log_info("guild_service_host_created", ...)`
  僅實際建立時發（context：`char`、`shop`、`service`；design D10）。
- [x] 3.3 `world/rules/tests/test_guild_config.py`／`test_guild_economy_sync.py`：首建帶作者姓名＋稱號、
  re-sync 不重複不改名（模擬 registry 改名）、**稱號永不被 sync 改寫**（對既存無稱號 host
  斷言 sync 後仍為空）、建立事件僅一次、legacy cleanup 刪除舊 host 且下次同步重建完整身分
  （patch `world.rules.guild_economy.log_info`）。
  Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_guild_economy_sync`
- [x] 3.4 rulebook 清-cut（rubber-duck 計畫審閱 MAJOR）：`world/rules/rulebook/affinity.yaml:42`
  `cap_breaks` 選擇器 `npc_key: altoria_guild_master` 改為新作者公會 host 姓名（它是活選擇器，
  非死字面）；`world/rules/tests/test_affinity_config.py` 與 `test_cap_break_turnin.py` 的字面
  基準／fixture 同批；`world/rules/tests/test_dialogue.py:307` 以 db_key 找 host 的既有斷言改走
  service 錨或新姓名。
  Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_affinity_config world.rules.tests.test_cap_break_turnin`

## 4. Exam examiners (rules)

- [x] 4.1 `world/rules/guild_exams.py::_spawn_opponent`：`key` 改用 `rank.examiner_name`＋
  `opponent.npc_title = validate_npc_title(rank.examiner_title)`；design D8 條件式去衝突
  （任何其他實體已持有同名才附 `-{pk}`）；`log_info("guild_exam_opponent_created", ...)`
  （context：`char`、`rank`）。
- [x] 4.2 `world/rules/tests/test_guild_exams.py`：作者姓名優先、同名玩家佔用時後綴形且考試照常開始、
  兩場同階級先後開考 key 互異（後 spawn 者的排除自身重查詢必須看到先前已提交的同名實體；佔用
  檢查與寫入同在 `start_guild_exam` 的 `transaction.atomic()` 內，無 check-then-create 視窗，
  design D8）、稱號落庫、建立事件；反向斷言舊 `guild-examiner-<rank>` 字面不再出現。
  Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_guild_exams`

## 5. Blueprint required identity fields (quests + ai)

- [x] 5.1 `world/quests/characterization.py`：`display_name` 必填、新增 `title` 必填（結構層維持
  `str | None`，必填由本驗證器執行，design D5）；規則以函式內延遲匯入委派
  `validate_npc_name`／`validate_npc_title`（design D3），`MAX_DISPLAY_NAME_LENGTH` 常數來源改指
  `MAX_NPC_NAME_CODE_POINTS`；`duplicate_display_name_errors` 對**整份 blueprint 的所有
  `npc_req`** 檢查姓名唯一（同 stage 與跨 stage 皆拒，design D4）；同批修訂模組 docstring 的純度契約。
- [x] 5.2 `world/quests/compile.py`：`StageNpcCharacterization.title`、canonical digest 帶 `title`、
  `_characterization_from_payload` 對缺 `title` 的 payload 具名 `QuestCompileError`（design D5/Risks）。
- [x] 5.3 `world/quests/scene_builder.py`：`_spawn_npc` 的 prototype `key` 改用作者 `display_name`
  （保留 `db.display_name` 寫入，design D2）；`_revalidate_characterization` 對缺
  characterization／`display_name`／`title` 一律 `SceneBuilderSpawnError` 回滾（design D6）；
  `_apply_characterization` 寫 `npc.npc_title`（驗證器回傳值）。**同批刪除（design D11）**：crc32
  兜底補名區塊、`_log_name_fallback`、`roll_name_for_race` 與 `partial`／`zlib` 等只服務該區塊的
  匯入。
- [x] 5.4 `world/ai/scenario_director.py`：輸出 jsonschema 宣告 `title`、payload round-trip 帶 `title`；
  `world/ai/director_templates.py` 模板 `npc_req` 補作者 `title`（黑鬍列）。
- [x] 5.4b **repo 根** `prompts/scenario_director.yaml`（不是 `world/prompts/`）：命名指導句改為
  「每個 `npc_req` 必須帶 `display_name` 與 `title`；以下名字僅供靈感，可直接採用或依性別、背景、
  語氣改寫」（`{name_inspiration}` 佔位符不動）；`world/prompts/tests/test_verbatim_shipment.py`
  （`_SCENARIO_DIRECTOR_SYSTEM` 字面基準）與 `test_loader.py`（`建議填寫 display_name` 斷言）同批。
- [x] 5.5 更新連帶轉紅的既有測試與基準線：全 repo 搜尋以字面 `npc_req` dict／`BlueprintNpcReq(...)`
  建測資而缺新欄的位置、斷言「XX的YY」場景 key、寫死 digest 的基準線（design Risks）。
  **刪除** `test_scene_builder.py` 的 crc32 補名測試群（backfill 斷言、`npc_name_fallback` 事件
  斷言、rollback-無殘留補名案；design D11）。
- [x] 5.6 `world/quests/tests/test_characterization.py`／`test_compile_blueprint.py`／
  `test_scene_builder.py`／`test_generated_quest_store.py` 與
  `world/ai/tests/test_scenario_director_validation.py`／`test_scenario_director_proposals.py`：
  缺欄拒（兩層同決策）、同 stage 與跨 stage 重名皆拒（含 characterization 全同的反向案）、
  digest 因 title 分異、
  還原缺 `title` 具名失敗、spawn `key`＋`npc_title` 落庫、偽造 requirement 缺欄回滾零殘留。
  Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.quests world.ai`

## 6. Spec bookkeeping

- [x] 6.1 `openspec validate npc-title-authored-identities --strict` 通過；
  `openspec validate --all --strict` 全綠（使用者自己的 change 除外）。
- [x] 6.2 sync 本 change 自己的 delta（前置兩件的 delta 已隨其歸檔 sync 完畢）：用
  `.agents/skills/openspec-sync-specs` 把 `npc-identity-titles`（7 ADDED）、
  `blueprint-portrait-policy`／`scenario-director`／`prompt-library`／`guild-rank-exams`／
  `sample-city-altoria`（MODIFIED）與 `scene-builder`（2 REMOVED）套進 `openspec/specs/`
  （MODIFIED/REMOVED 的 requirement 標題須與主規格逐字相符，sync 以標題對帳），
  然後以 `uv run --locked python -m tools.spec_traceability list` 取 canonical ID，
  將本 change requirement 的 `covers_requirement` 標註掛到第 1–5 組的錨定測試上，
  跑 `uv run --locked python -m tools.spec_traceability check` 至零錯誤。
- [x] 6.3 確認 `.github/evennia-shards.json` 不需變動（本 change 不新增測試模組）；
  `git diff --check` 乾淨。

## 7. 明確不做（延期，非遺漏）

- blueprint 姓名對三份 registry 作者姓名的跨面碰撞檢查、以及對資料庫既有 NPC 的查覆
  （design D4 已知缺口）。
- `world/rules/onboarding.py::sync_guard_npc` 的守衛補名／補稱號——**刻意豁免**：該守衛屬於即將
  整體移除的新手教學，為註定刪除的 NPC 造 registry 是死抽象（design D7a）。守衛在過渡期以純姓名
  呈現；移除 onboarding 的 change 落地時豁免自然消失。
- LLM 系統訊息模板（`prompts/npc_dialogue.yaml`）加 `{title}` 佔位符（由 change 1 的後續承接）。
