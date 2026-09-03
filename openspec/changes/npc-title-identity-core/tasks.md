# npc-title-identity-core — Tasks

實作順序即分組順序：確定性核心 → typeclass 屬性與顯示旗標 → 房間人物列與 echo 迴歸 → webclient 面板 → 緊湊列釘樁 → 登記與收尾。每組做完先跑該組 focused 測試再勾選；全程不跑 CI shard 指令、不跑格式化／lint 工具。

估時：單人一個工作日內。若某組超時，優先保住第 1／2／3 組（核心＋文字表面），把第 4 組（webclient）獨立成後續 change，並在此檔記錄。

## 1. 確定性核心 `world/rules/npc_identity.py`

- [x] 1.1 新建模組，英文 docstring 說明它是 NPC 全名的唯一組合點。模組私有常量 `_FULL_WIDTH_SPACE = "　"`（自持，**不**從 `world/rules/titles.py` 匯入）與 `MAX_NPC_TITLE_CODE_POINTS = 32`。module scope 不匯入任何 typeclass、不匯入 logger（本模組不產 log）。
- [x] 1.2 `validate_npc_title(value) -> str`：非 `str`（含 `bool`）、strip 後為空、strip 後 code points 不在 1..32、含任何 `str.isspace()` 字元（含 U+3000）、含控制字元（`unicodedata.category(...).startswith("C")` 或 `not char.isprintable()`）、含 `|` → 各自以穩定英文訊息 raise（沿用 `world/rules/character_creation.py::_validate_name` 的訊息風格與檢查順序）；通過回 strip 後字串。例外型別沿用專案慣例（`ValueError` 子類別，於本模組宣告具名例外）。
- [x] 1.3 `npc_title_value(entity) -> str`：函式內 `from typeclasses.npcs import NPC` 延遲匯入（先例 `world/rules/party.py::live_companion_ids`）；非 `NPC` 執行個體、缺屬性、非字串、strip 後為空 → `""`；否則回 strip 後字串。**渲染內容閘門**（實作期 rubber-duck 折入）：strip 後字串若違反驗證器的內容規則（內部空白、控制／不可列印字元、`|`）→ 一律 `""`，因為該存值不可能出自作者路徑、渲染它會把 Evennia markup 或分隔符含糊的識別放上螢幕；**長度刻意不在此閘門**——超長存值是文件中已由顯示邊界截斷的退化態（見 4.2 NB4），與內容腐損分屬兩類。稱號存取器 raise 時以具名收斂 safe-read 邊界退化為 `""`。純讀取，不觸發任何持久化。
- [x] 1.4 `npc_display_name(entity) -> str`：`title = npc_title_value(entity)`；`key = _plain_key(entity)`（具名 safe-read：`key` 缺失／存取器 raise／`__str__` raise → `""`）；有 title **且 key 可讀**回 `f"{key}{_FULL_WIDTH_SPACE}{title}"`，title 退化回 `key`，key 亦不可讀回 `""`（**永不**產出「　稱號」式開頭分隔符的含糊識別）。**永不 raise**：存值腐損以顯式取值檢查退化；存取器故障由兩個具名 safe-read 邊界收斂（實作期 rubber-duck 折入：宣稱永不 raise 卻不守存取器是說一套做一套）。本模組非 facade adopter，R2 規則本就不適用；每個 `except` 仍附 `# observability: ignore R2: <reason>` 註解自我文件。
- [x] 1.5 新測試模組 `world/rules/tests/test_npc_identity.py`：`validate_npc_title` 以 `unittest.TestCase` 純邏輯案覆蓋——合法值 strip round-trip、32／33 邊界、ASCII 空白、U+3000、控制字元、`|`、`None`／int／bool／`""`／全空白各自被拒。
- [x] 1.6 同模組 `EvenniaTest` 案：`npc_display_name` 對「塞提斯」＋「南門守衛」回 `"塞提斯　南門守衛"`（斷言分隔符為單一 U+3000）；未設稱號回純 `key`；玩家角色與 `Monster` 回純 `key` 且 `npc_title_value` 為 `""`；稱號存成非字串／全空白／缺屬性時回純 `key` 且不擲例外。
- [x] 1.7 Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_npc_identity`。

## 2. NPC typeclass：屬性、顯示旗標、看標題、prompt context

- [x] 2.1 `typeclasses/npcs.py::NPC` 宣告 `npc_title: str = AttributeProperty(default="", autocreate=False)`（autocreate=False 是實作揭示的必要細節：Evennia 6.1 的 `AttributeProperty` 預位 autocreate=True，**讀取**不存在的屬性會在 `__get__` 內 `__set__` 落庫，直接牴觸本 change「組合器純讀取、永不寫入」契約；先例 `PlayerCharacter.creation_draft`）。class docstring 補英文說明：建立時由作者路徑寫入、runtime 不可變（保證範圍＝無稱號專屬寫入 API，generic `.db` 存取屬框架基礎設施、明示在宣稱之外）、唯一驗證器是 `world.rules.npc_identity.validate_npc_title`。**不**新增任何 setter 或寫入 helper。
- [x] 2.2 `NPC.get_display_name(self, looker=None, *, full_identity=False, **kwargs)`：旗標為假 → `return super().get_display_name(looker, **kwargs)`（位元等值）；為真 → 函式內延遲匯入 `npc_display_name` 後回傳其結果。
- [x] 2.3 `NPC.return_appearance(self, looker, **kwargs)`：`kwargs.setdefault("full_identity", True)` 後委派 `super()`，讓 appearance template 的 `{name}` 槽取得全名（設計 D4）。不重寫 template、不動 `get_display_desc`／affinity／displayed-stats 既有疊加順序。
- [x] 2.4 `LLMNPC._npc_context()` 新增 `"title": npc_title_value(self)`（延遲匯入）；不動 `world/ai/npc_dialogue.py` 與 `prompts/npc_dialogue.yaml`（設計 D7）。
- [x] 2.5 `typeclasses/tests/test_npcs.py` 增測：未設稱號的新 NPC `npc_title == ""`；`get_display_name()` 與 `get_display_name(full_identity=False)` 對帶稱號 NPC 皆回純 `key`；`get_display_name(full_identity=True)` 回全名；對玩家角色與 `Monster` 傳入 `full_identity=True` 不擲例外且回純 `key`。
- [x] 2.6 結構性缺席案（同檔，仿 title-system 的無刪除面測試）：斷言 `NPC` 的公開介面不含 `set_npc_title` 一類寫入 helper，且 `commands/` 註冊的命令集中沒有任何改 NPC 稱號的命令（以命令 key／aliases 掃描斷言，非字串比對實作細節）。
- [x] 2.7 `typeclasses/tests/test_npc_dialogue.py` 增測：帶稱號 `LLMNPC` 的 `_npc_context()["title"]` 為該稱號、未設稱號為 `""`、呼叫前後 NPC 狀態不變；並以既有 prompt 建構案斷言系統訊息位元等值（新增鍵不改渲染）。
- [x] 2.8 Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb typeclasses.tests.test_npcs typeclasses.tests.test_npc_dialogue`。

## 3. 房間人物列、看標題與 echo 迴歸

- [x] 3.1 `typeclasses/objects.py::ObjectParent.get_display_characters`：改以合併形式帶旗標 `char.get_display_name(looker, **{**kwargs, "full_identity": True})`（設計 D3；直接寫關鍵字會在 `return_appearance` 注入旗標後撞 duplicate-keyword `TypeError`）。行為對非 NPC 角色不變。
- [x] 3.2 `typeclasses/tests/test_appearance.py` 增測：房間人物列對帶稱號 NPC 顯示 `姓名　稱號`，同列的玩家與 `Monster` 顯示純姓名；`看 <NPC>` 標題顯示全名，且文字 `看`、`at_look` seam、webclient `explore.look` 三路輸出彼此相同（沿用該檔既有三路徑比對慣例；比對沿用同一 target 與 looker、比較回傳的 appearance 字串，各自新建物件會因 pk 序列不相等而誤紅）；顯式 `return_appearance(looker, full_identity=False)` 標題維持純姓名（D4 宣稱的呼叫端覆寫面）；既有 zh-tw 框架、affinity 行與 displayed-stats 區塊斷言保持綠燈。
- [x] 3.3 同檔（或 `commands/tests/` 中對應既有模組）增 echo 迴歸案：帶稱號 NPC 的移動進出訊息、`說`／`耳語` echo、給予／拾取 echo、`world/rules/party.py::FOLLOW_LOST_MESSAGE` 跟丟通知，全部只出現純姓名，且與同一隻 NPC 未設稱號時的輸出位元等值。
- [x] 3.4 「看一隻身上帶著角色的 NPC」路徑實測（`return_appearance` 注入旗標後再進 `get_display_characters`），確認無 duplicate-keyword `TypeError`。
- [x] 3.5 Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb typeclasses.tests.test_appearance`，再跑第 3.3 條所在模組的 label。

## 4. Webclient 探索面板

- [x] 4.1 `web/webclient/presentation/exploration.py` 新增模組私有 `_bounded_entity_name(obj)`：`npc_display_name(obj)[:MAX_DISPLAY_NAME_CODE_POINTS]`（截斷語義與既有 `_bounded_display_name` 一致，不拋例外）。在 `_look_entities` 與 `_interact_targets` 兩處的 `display_name` 改用它；`look.room`、`move` 列、`_look_objects`／`_look_entries` 續用 `_bounded_display_name`，共用 helper 本身不動（設計 D5）。
- [x] 4.2 `web/webclient/presentation/tests/test_exploration_panel.py` 增測：帶稱號 NPC 的 `look.entities` 列與 `interact` 目標列 `display_name` 皆為 `姓名　稱號`；同房間的房間列、`move` 列與 `look.objects` 列位元等值於改動前；未設稱號與稱號欄損壞時面板仍 available 且 payload 通過驗證（純姓名）；**過長損壞稱號**（如經 `.db` 存入 200 code points）時兩類列的 `display_name` 仍被截斷至 ≤128 並通過驗證（`_bounded_entity_name` 的截斷是損壞態的邊界防線，不只為合法值存在）。
- [x] 4.3 界內核算迴歸案：64 code points 姓名 ＋ 32 code points 稱號合成後 97 ≤ 128，payload 通過 `validate_exploration`，`schema_version`、欄位集合與上界常量皆未變。
- [x] 4.4 Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_exploration_panel`。前端零改動（面板只換字串來源，Vue／wire 形狀不變），不跑 npm gates。

## 5. 緊湊列釘樁與目標解析

- [x] 5.1 `world/rules/tests/test_combat_view.py` 增斷言：帶稱號 NPC 的 participant `display_name` 為純 `key`（無 U+3000、無稱號）。實作零改動。
- [x] 5.2 `world/rules/tests/test_art_view.py` 與 `world/rules/tests/test_service_view.py` 各增同型斷言：頭像目錄條目與公會／商店 host 列為純 `key`。實作零改動。
- [x] 5.3 目標解析案（放在既有 party／talk 指令測試模組）：帶稱號 NPC 仍以純姓名被搜尋命中；以合成全名字串搜尋不命中該 NPC；`aliases` 未被寫入稱號。
- [x] 5.4 Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_combat_view world.rules.tests.test_art_view world.rules.tests.test_service_view`。

## 6. 登記、可追溯性與收尾

- [x] 6.1 `.github/evennia-shards.json`：新增 `world.rules.tests.test_npc_identity` 一列到持有 `world.rules.tests.*` 的對應 shard（依既有字母序插入），其餘均為既有模組故不動。以 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract` 驗證恰好一主。
- [ ] 6.2 **批次整合契約（三件 change 共用，rubber-duck 複審後定案）**：`openspec/specs/npc-identity-titles/spec.md` 只有單一寫入者——批次最後落地的那個 change（建議批次順序下為 `npc-title-authored-identities`）。三件一起走時，本 change **不自行 sync delta、不掛 covers_requirement、不跑覆蓋 check**；本檔 6.3 的錨定測試映射表是整合步驟的依據。僅當本 change 單獨實作／歸檔時，才依 `.agents/skills/openspec-sync-specs` 同步 delta 並以 `uv run --locked python -m tools.spec_traceability list` 取 canonical ID 後執行 6.3。
- [ ] 6.3 掛 `covers_requirement` 標註（參數必須是字面值 ID，`from tools.spec_traceability import covers_requirement`；ID 於 sync 後取）：驗證器→1.5；組合器→1.6；屬性與無寫入面→2.5／2.6；opt-in 顯示路由→3.2／3.3；webclient 面板→4.2；緊湊列→5.1／5.2；prompt context→2.7；目標解析→5.3；既有契約不變→3.2 的框架迴歸案。單獨執行時跑 `uv run --locked python -m tools.spec_traceability check` 至零錯誤、九條 requirement 全覆蓋。
- [x] 6.4 消極檢查：確認 `world/rules/npc_identity.py` 無 `world.observability` 匯入、無 module-scope typeclass 匯入，且每個 `except` 都是帶理由註解的具名 safe-read 邊界（實作期 rubber-duck 折入後，「無 except 區塊」改為「except 僅限 safe-read 邊界且皆附理由」）；確認 `world/rules/titles.py` 與 `openspec/specs/title-system/spec.md` 零改動；確認 `docs/game/commands.md`／`docs/game/command-reference.md` 零改動（無命令面變更）；確認未觸及 `world/lore/names.py`／`world/rules/namegen.py`（namegen 系列 change 的檔案）。
- [x] 6.4b ~~生產者清單迴歸案~~ **已撤除**（rubber-duck 複審判定文字掃描是假保衛，撤除優於假實作：`world/imports/loader.py:65` 以 `create_object(typeclass, ...)` 變數派發，任何 `create_object(NPC` 形態的正則都掃不到它，別名匯入／包裝 helper／字串 typeclass 路徑同理；掃不到的防線比沒有防線更糟）。fail-closed 保證的真實承重點＝change 2／3 各建立點對 `validate_npc_title` 的顯式呼叫與其測試；生產者清單（loader／scene_builder／guild_economy／guild_exams／onboarding 豁免）維持為設計文件的**人工維護清單**，新建立路徑由評審對帳。
- [x] 6.5 `openspec validate npc-title-identity-core --strict` 與 `git diff --check` 皆通過。
- [x] 6.6 終局驗證一次：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --noinput --parallel 16 typeclasses world web.webclient commands`（觸面涵蓋 typeclass 顯示、rules 核心、面板與指令 echo 迴歸）。

## 7. 本 change 明確不做（延後，非遺漏）

以下項目屬設計文件範圍但由後續 change 承接，實作時不要順手做：

- 稱號真正進入 LLM 系統訊息：需要 `prompts/npc_dialogue.yaml` 新增 `{title}` 佔位符（或改由 `{name}` 槽承載全名）並重錄 prompt 基準線。在有作者稱號可用之前無可觀察效果，故只留 `_npc_context()["title"]` 這個前置 seam（設計 D7）。
- `CHARACTER_SCHEMA_V1` 的必填 `title`、`world/imports/loader.py` 寫入、批次姓名唯一性與整批拒絕語義、`world/imports/examples/*.json` 補欄（change 2）。
- blueprint `npc_req` 的 `display_name`／`title` 必填、`SHOP_REGISTRY` host 欄位、`GUILD_RANK_REGISTRY` examiner 欄位、`guild_economy`／`guild_exams` 生成路徑與其 boundary log 事件（change 3）。
- `Monster` 稱號、玩家稱號系統任何改動、runtime 改稱號、多語言與顏色 markup（設計 §9 範圍外）。
