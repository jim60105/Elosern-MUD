# npc-title-authored-identities — Proposal

## Why

`npc-title-identity-core` 立起了驗證器、`NPC.npc_title` 與三個顯示表面，`npc-title-import-pipeline` 讓 JSON 角色卡成為第一條寫入路徑。但玩家在遊戲裡真正會遇到的 NPC 幾乎都不是匯入來的：公會長與雜貨店老闆現在的 `key` 是 ASCII service id `altoria_guild_master`／`altoria_merchant`，晉級考官叫 `guild-examiner-F-12`，任務場景的佔用者叫「林間小徑的盜匪」——三條路徑都沒有作者供給的姓名，更沒有稱號。已核准設計 `docs/superpowers/specs/2026-09-03-npc-identity-titles-design.md` §5 的後三列（blueprint `npc_req`、`SHOP_REGISTRY`、`GUILD_RANK_REGISTRY`）就是要把這些**建立時就存在於世界**的 NPC 交回作者手上：姓名與稱號由 registry 與 blueprint 明文供給，缺一即拒絕建立（設計 §6）。本 change 是三件套的最後一件，完成後設計 §3.2 不變式 1（每隻 NPC 必有姓名＋稱號）在所有生產路徑上都成立。

## What Changes

- **blueprint `npc_req`**：`display_name` 由選填改**必填**、新增**必填** `title`。兩者都在共用規則來源 `world/quests/characterization.py::characterize_errors` 內執行（`title` 委派 change 1 的 `validate_npc_title`，`display_name` 委派本 change 新增的 `validate_npc_name`），因此 `world/ai/scenario_director.py` 的提案 guardrail 與 `world/quests/compile.py` 的編譯邊界**同一份規則、同一組拒絕決策**。AI 提案缺欄即在驗證層被拒並重試，永不落庫；`world/ai/director_templates.py` 的離線模板池同樣受檢。**BREAKING**（對既有 blueprint 與已存的生成任務內容）。
- **blueprint 的姓名成為 NPC 的 `key`**：`world/quests/scene_builder.py::_spawn_npc` 不再以 `f"{場景}的{role}"` 造名，改用作者供給的 `display_name` 當 `key`，並寫入 `npc_title`；缺任一欄即 `SceneBuilderSpawnError`、整個場景 materialization 回滾（fail closed，設計 §3.2 不變式 1）。這是本 change 與匯入面的差異：角色卡有自己的 `key` 欄位，`npc_req` 沒有，作者供給的姓名只能是 `display_name`。
- **blueprint 面的姓名唯一性**（設計 §3.2 不變式 2 的第三個作者面）：**整份 blueprint 內任何兩筆 `npc_req` 不得同名**（同 stage 與跨 stage 皆拒）。SceneBuilder 的佔用者每次 materialization 新生、無跨 stage 身分複用，跨 stage 同名會造出兩隻同 `key` 活體；同一角色跨場景登場由共用 `stable_key`（頭像身分）承載，不由同 `key` 承載（rubber-duck 複審後收緊，原跨 stage 例外方案已否決，design D4）。
- **`SHOP_REGISTRY` 與公會分會 registry**：`ShopDefinition` 新增 `host_name`／`host_title`，`GuildBranch` 新增 `host_name`／`host_title`（設計 §5 只寫了 `SHOP_REGISTRY`，但 `_sync_service_host` 造的兩隻 host 其中一隻是公會分會 host，沒有 shop row——見 design 的現況校正）。`world/rules/guild_economy.py` 建立 host 時以作者姓名為 `key`、寫入稱號；**冪等重用改以元件 `service_id` 為錨**，既存 host 永不改名、**sync 永不補寫稱號**（runtime 寫稱號即違反建立時不可變；rubber-duck 複審後收緊）。前功能時代的 ASCII-key host 由一個**一次性 cleanup** 丟棄（未發布、零使用者、clean cutover，非遷移），下次同步即以完整作者身分重建。
- **`GUILD_RANK_REGISTRY`**：`GuildRank` 新增 `examiner_name`／`examiner_title`（七個階級各一位具名考官）。`world/rules/guild_exams.py::_spawn_opponent`（設計寫的是 `settle_exam_outcome`，實際建立點在這裡）改用作者姓名為 `key`＋寫入稱號，取代 `key=f"guild-examiner-{rank}"`。既有的「每次 spawn 專屬唯一 key」保證改成**條件式**：作者姓名被其他實體佔用時才附加 `-{pk}` 去衝突，戰場 roster 與 skip-safety 註冊表（皆以 `str(entity.key)` 為鍵）的不碰撞保證原封不動。
- **registry 載入 fail closed**（設計 §6）：`world/lore/shops.py` 與 `world/lore/guild.py` 在 module 載入時驗證自己的作者欄位（缺欄＝dataclass `TypeError`；違規值＝具名 `ValueError`），並檢查三份 registry 之間的作者姓名互不重複。先例：`world/lore/titles.py` 於 module 載入時驗證出貨 rows、`world/lore/wilderness_entry.py` 的 `validate_wilderness_entries()`。
- **觀測性**（設計 §8）：`guild_economy` 的 host 建立與 `guild_exams` 的考官建立各補一個 `log_info` 邊界事件，`context` 依設計帶 `char`／`shop`／`rank`。
- 無玩家命令新增／改名／改語法 → `docs/game/commands.md`、`docs/game/command-reference.md` 不動。無相容層、無資料遷移（未發布、零使用者）。
- **生產 NPC 路徑清單與 onboarding 豁免**（design D7a）：非測試碼的全部 `create_object(NPC, ...)` 落點共五處——loader（change 2）、SceneBuilder／guild host／考官（本 change）、`world/rules/onboarding.py::sync_guard_npc`。南門守衛屬於**即將整體移除的新手教學**，為註定刪除的 NPC 造 registry 是死抽象：本 change **刻意豁免**它（AGENTS.md：deliberate skip is preferable to a fake implementation），過渡期該守衛以純姓名呈現；移除 onboarding 的 change 落地時豁免自然消失。change 1 的生產者清單迴歸案讓清單與程式碼同步。

## Capabilities

### New Capabilities

（無。）

### Modified Capabilities

- `npc-identity-titles`（由 `npc-title-identity-core` 建立、`npc-title-import-pipeline` 追加，皆尚未 sync 進 `openspec/specs/`）：本 change 以 delta 對**同一個 capability** 追加設計 §5／§6 的作者供給 requirement——blueprint `npc_req` 的必填姓名／稱號與 blueprint 面唯一性、SceneBuilder 以作者姓名為 `key` 並落庫稱號、兩份 registry 的作者欄位與載入 fail-closed、guild host 與考官的建立與冪等重用規則，以及兩個邊界事件。change 1 的 9 條與 change 2 的 7 條 requirement 一條都不重述、不改寫；本 change 的 requirement 標題一律以「blueprint」「registry」「guild」「exam」等作者面詞開頭，與前兩者零重疊。
- `blueprint-portrait-policy`：五條 requirement 的原文直接被推翻——「四個欄位**全部選填**」「無欄位的 blueprint 逐位元不變地 round-trip」「無欄位時編譯出與今日完全相同的 requirements 形狀」在 `display_name`／`title` 必填後不再為真。本 change 以 `## MODIFIED Requirements` 重述這五條（含共用規則來源與模板池兩條）。
- `scenario-director`：`Blueprint validation accepts and bounds the optional npc characterization fields` 的「Entries without the optional fields SHALL validate unchanged」被推翻，重述為必填兩欄＋選填其餘。
- `guild-rank-exams`：`Exam opponents use collision-free unique display keys` 要求「每次 spawn 的 key 都帶專屬唯一成分」，與作者供給姓名直接衝突，重述為「作者姓名優先、被佔用時才以 `-{pk}` 去衝突」，兩條既有 scenario 的保證維持不變。
- `sample-city-altoria`：`Guild service hosts carry adult identity` 的 scenario 以 `altoria_guild_master`／`altoria_merchant` 指稱被建立的 NPC；改名後這兩個字串是 service id 而非 NPC 姓名，重述該 scenario 的指稱方式（requirement 的成年不變式本身不動）。

`scene-builder` 的 requirement 原文**不需修改**：`Anti-hallucination` 一條已把 characterization 明列為「作者內容、非機械數字」，`The occupant spawn path exposes a post-commit portrait-eligibility seam` 一條只規定 portrait policy 與 `db.display_name` 的寫入（維持原樣，姓名同時成為 `key` 是新增行為，不推翻該句），`Materializing a stage ...` 只說「每筆 `npc_req` spawn 一隻 NPC」而未規定其 `key` 從何而來。新行為由 `npc-identity-titles` 自行宣告，並附「既有 scene-builder 契約原文不動」的迴歸 scenario（先例：change 1／change 2 的處理方式）。

## Impact

- 修改（lore）：`world/lore/shops.py`（`ShopDefinition` ＋2 欄＋載入驗證）、`world/lore/guild.py`（`GuildRank` ＋2 欄、`GuildBranch` ＋2 欄＋載入驗證與跨 registry 姓名唯一性）。`world/lore/sync.py` 不需改動（`asdict` 自動鏡射新欄位，`GUILD_RANK_REGISTRY` 已在鏡射清單內；`SHOP_REGISTRY` 本來就不在）。
- 修改（規則核心）：`world/rules/npc_identity.py`（本 change 追加 `validate_npc_name` 與 `MAX_NPC_NAME_CODE_POINTS`，其餘 change 1 的函式不動）、`world/rules/guild_economy.py`（host 建立／重用、邊界事件）、`world/rules/guild_exams.py`（考官建立、邊界事件）。
- 修改（blueprint 鏈）：`world/quests/characterization.py`（必填規則與姓名唯一性 helper）、`world/quests/compile.py`（`StageNpcCharacterization.title`、canonical digest、restore payload）、`world/quests/scene_builder.py`（`key` 來源、稱號落庫、fail-closed 重驗）、`world/ai/scenario_director.py`（jsonschema 與 payload round-trip 帶 `title`）、`world/ai/director_templates.py`（模板 `npc_req` 補 `title`）。
- 測試觸面（全部加進既有模組，**不新增測試檔** → `.github/evennia-shards.json` 不動）：`world/lore/tests/test_guild.py`、`world/rules/tests/test_guild_config.py`、`world/rules/tests/test_guild_economy_sync.py`、`world/rules/tests/test_guild_exams.py`、`world/quests/tests/test_characterization.py`、`test_compile_blueprint.py`、`test_scene_builder.py`、`test_generated_quest_store.py`、`world/ai/tests/test_scenario_director_validation.py`、`test_scenario_director_proposals.py`。
- 連帶轉紅：任何以字面 `npc_req` dict 或 `BlueprintNpcReq(...)` 組測試資料而未帶 `display_name`／`title` 的既有測試；任何斷言場景 NPC `key` 為「XX的YY」或考官 `key` 為 `guild-examiner-*` 的既有測試（已知：`world/rules/tests/test_guild_exams.py`、`world/quests/tests/test_scene_builder*.py`）。內容 digest 因 canonical 序列化多一個 `title` 欄位而改變，任何寫死 digest 的基準線需同批更新。
- 觀測性：`world/rules/guild_economy.py`／`guild_exams.py` 皆已是 facade adopter（兩檔已 `from world.observability import log_warn`），本 change 只增 `log_info`；`tools/observability_freeze.json` 為空清單、不動。
- 依賴：**嚴格前置 `npc-title-identity-core`**（`validate_npc_title`、`MAX_NPC_TITLE_CODE_POINTS`、`NPC.npc_title` 都由它定義）。主規格 capability 的 sync 採**批次整合契約**：三件一起走時由**本 change 作為批次收尾者**單次依序 sync 三件 delta（core → import → authored）、一次取 canonical ID、統一掛 `covers_requirement`（tasks 6.2）——這是三份提案中唯一的 main-spec 寫入點。與 `npc-title-import-pipeline` **檔案零交集**（該 change 只動 `world/imports/`；本 change 對 `npc_identity.py` 只做 append-only 的 `validate_npc_name` 新增，函式與常量加在檔尾），兩者可在 change 1 之後並行。
- 與進行中的 namegen 系列（`world/lore/names.py`、`world/rules/namegen.py`、creation UI）檔案零交集：本 change 不規定姓名如何產生，只規定 registry 與 blueprint 必須明文寫出姓名。
