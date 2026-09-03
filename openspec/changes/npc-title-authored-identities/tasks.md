# npc-title-authored-identities — Tasks

前置：`npc-title-identity-core`（提供 `world/rules/npc_identity.py::validate_npc_title`、
`MAX_NPC_TITLE_CODE_POINTS`、`NPC.npc_title`）。與 `npc-title-import-pipeline` 無檔案交集，可平行。

## 1. Shared name rule

- [ ] 1.1 在 `world/rules/npc_identity.py` 新增 `MAX_NPC_NAME_CODE_POINTS = 64` 與
  `validate_npc_name(value) -> str`（design D3 規則：`str`、strip 後 1–64 code points、拒控制字元、
  拒 `|`、拒全形空格 U+3000、允許一般 ASCII 空白；回傳 strip 後正規形），module scope 維持 stdlib-only。
- [ ] 1.2 在 `world/rules/tests/` 的 npc_identity 測試模組補 `validate_npc_name` 邊界測試
  （空、過長、控制字元、`|`、U+3000、含一般空白允許、strip 正規形）。
  Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests`

## 2. Registry authored identities (lore)

- [ ] 2.1 `world/lore/shops.py`：`ShopDefinition` 新增**無預設值**必填欄 `host_name`／`host_title`，
  補齊 `altoria_general_store` 列的作者值（zh-TW 姓名＋職稱），模組尾端以延遲匯入的
  `validate_npc_name`／`validate_npc_title` 對純函式 row validator 跑載入驗證（違規 → 具名 `ValueError`）。
- [ ] 2.2 `world/lore/guild.py`：`GuildRank` 新增必填 `examiner_name`／`examiner_title`（七列各補作者值），
  `GuildBranch` 新增必填 `host_name`／`host_title`（`guild_branch_altoria` 補作者值）；
  同檔 row validator＋載入驗證（design D9 先例：`world/lore/titles.py`）。
- [ ] 2.3 實作跨 registry 作者姓名唯一性純檢查（shops＋guild branches＋ranks 三組姓名互不重複，
  違規具名 `ValueError`），由兩檔載入流程呼叫（design D9）。
- [ ] 2.4 `world/lore/tests/test_guild.py` 與 shops 對應測試：缺欄 `TypeError`、違規值具名
  `ValueError`、跨 registry 重名拒、出貨 registries 載入-clean 斷言；確認 `world/lore/sync.py`
  的 `asdict` 鏡射自動帶新欄且冪等（`GUILD_RANK_REGISTRY` 已在鏡射清單；`SHOP_REGISTRY` 不在，不動）。
  Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.lore.tests.test_guild`

## 3. Guild service hosts (rules)

- [ ] 3.1 `world/rules/guild_economy.py::_sync_service_host` 改為 design D7 形狀：以元件
  `service_id` 錨找既有 host（`_host_by_service_id`，走 NPC family 掃描，與
  `_initialize_merchant_stock` 同形）；缺則 `create_object(NPC, key=validate_npc_name(host_name))`
  ＋ `host.npc_title = validate_npc_title(host_title)`；既存永不改名、稱號僅空值補寫；其餘
  既有更新語義（location／race／成年身分／補元件）原封不動。
- [ ] 3.2 呼叫端（shop host 與 guild-branch host 兩條同步線）從 `SHOP_REGISTRY.host_name/host_title`
  與 `GuildBranch.host_name/host_title` 供給參數；`log_info("guild_service_host_created", ...)`
  僅實際建立時發（context：`char`、`shop`、`service`；design D10）。
- [ ] 3.3 `world/rules/tests/test_guild_config.py`／`test_guild_economy_sync.py`：首建帶作者姓名＋稱號、
  re-sync 不重複不改名（模擬 registry 改名）、空稱號補寫一次、非空不覆寫、建立事件僅一次
  （patch `world.rules.guild_economy.log_info`）。
  Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_guild_economy_sync`

## 4. Exam examiners (rules)

- [ ] 4.1 `world/rules/guild_exams.py::_spawn_opponent`：`key` 改用 `rank.examiner_name`＋
  `opponent.npc_title = validate_npc_title(rank.examiner_title)`；design D8 條件式去衝突
  （任何其他實體已持有同名才附 `-{pk}`）；`log_info("guild_exam_opponent_created", ...)`
  （context：`char`、`rank`）。
- [ ] 4.2 `world/rules/tests/test_guild_exams.py`：作者姓名優先、同名玩家佔用時後綴形且考試照常開始、
  兩場同階級並發 key 互異、稱號落庫、建立事件；反向了斷言舊 `guild-examiner-<rank>` 字面不再出現。
  Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_guild_exams`

## 5. Blueprint required identity fields (quests + ai)

- [ ] 5.1 `world/quests/characterization.py`：`display_name` 必填、新增 `title` 必填（結構層維持
  `str | None`，必填由本驗證器執行，design D5）；規則以函式內延遲匯入委派
  `validate_npc_name`／`validate_npc_title`（design D3），`MAX_DISPLAY_NAME_LENGTH` 常數來源改指
  `MAX_NPC_NAME_CODE_POINTS`；同 stage `display_name` 唯一、跨 stage 同名須 identity tuple
  （title＋其餘 characterization）全同（`duplicate_display_name_errors`，與
  `duplicate_stable_key_errors` 共用比較，design D4）；同批修訂模組 docstring 的純度契約。
- [ ] 5.2 `world/quests/compile.py`：`StageNpcCharacterization.title`、canonical digest 帶 `title`、
  `_characterization_from_payload` 對缺 `title` 的 payload 具名 `QuestCompileError`（design D5/Risks）。
- [ ] 5.3 `world/quests/scene_builder.py`：`_spawn_npc` 的 prototype `key` 改用作者 `display_name`
  （保留 `db.display_name` 寫入，design D2）；`_revalidate_characterization` 對缺
  characterization／`display_name`／`title` 一律 `SceneBuilderSpawnError` 回滾（design D6）；
  `_apply_characterization` 寫 `npc.npc_title`（驗證器回傳值）。
- [ ] 5.4 `world/ai/scenario_director.py`：輸出 jsonschema 宣告 `title`、payload round-trip 帶 `title`；
  `world/ai/director_templates.py` 模板 `npc_req` 補作者 `title`（黑鬍列）。
- [ ] 5.5 更新連帶轉紅的既有測試與基準線：全 repo 搜尋以字面 `npc_req` dict／`BlueprintNpcReq(...)`
  建測資而缺新欄的位置、斷言「XX的YY」場景 key、寫死 `ai_` 前綴 digest 的基準線（design Risks）。
- [ ] 5.6 `world/quests/tests/test_characterization.py`／`test_compile_blueprint.py`／
  `test_scene_builder.py`／`test_generated_quest_store.py` 與
  `world/ai/tests/test_scenario_director_validation.py`／`test_scenario_director_proposals.py`：
  缺欄拒（兩層同決策）、stage 內重名拒、跨 stage 同角允／異角拒、digest 因 title 分異、
  還原缺 `title` 具名失敗、spawn `key`＋`npc_title` 落庫、偽造 requirement 缺欄回滾零殘留。
  Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.quests world.ai`

## 6. Spec bookkeeping

- [ ] 6.1 `openspec validate npc-title-authored-identities --strict` 通過；
  `openspec validate --all --strict` 僅剩既有 namegen 空殼的兩筆失敗。
- [ ] 6.2 實作落地後依序 sync 三個前置／本 change 的 delta 進 `openspec/specs/`（順序：
  npc-title-identity-core → 本 change），以
  `uv run --locked python -m tools.spec_traceability list` 取 canonical ID，
  將本 change requirement 的 `covers_requirement` 標記掛到第 2–5 組的錨定測試上。
- [ ] 6.3 確認 `.github/evennia-shards.json` 不需變動（本 change 不新增測試模組）；
  `git diff --check` 乾淨。

## 7. 明確不做（延期，非遺漏）

- blueprint 姓名對三份 registry 作者姓名的跨面碰撞檢查、以及對資料庫既有 NPC 的查覆
  （design D4 已知缺口）。
- LLM 系統訊息模板（`prompts/npc_dialogue.yaml`）加 `{title}` 佔位符（由 change 1 的後續承接）。
- 既有開發資料庫舊 host 的改名（設計明文：既存 host 永不改名；要看到作者姓名請重建資料庫）。
