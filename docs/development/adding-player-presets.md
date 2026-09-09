# 新增角色模板指南

本指南說明如何為 Elosern 加入一筆新的玩家角色模板，也就是 `world/lore/player_presets.py::PLAYER_PRESET_REGISTRY` 裡的一條 `PlayerPreset`。模板是帳號註冊階段玩家可以直接選用的開局角色：身份、配點、技能、行李與穿戴、人格、性傾向基線、偽裝數值與同行夥伴全部由這張卡宣告，啟動時由規則層照單執行。本文走一遍完整流程：資料位置、事前決定、逐段落卡、載入期驗證器、常見錯誤，以及哪些事該交給別的指南。

本文假設你已讀過：

- `world/lore/player_presets.py`（registry、資料類別結構與全部載入期驗證器）
- `world/rules/character_creation.py`（配點邊界解析 `resolve_starting_profile()` 與啟動流程）
- `openspec/specs/player-character-creation/spec.md`（建立路徑的現行契約）
- 已落地的範例：registry 現行八張卡，含互相宣告的雙胞胎 `yuka_darknight`／`yuna_darknight`

---

## 1. 背景：一張卡的資料住在一個 registry 裡

模板是 `PLAYER_PRESET_REGISTRY` 字典中的 frozen dataclass `PlayerPreset`，共二十個欄位，分屬九個資料域。卡寫進 registry 之後，Telnet 建立精靈、WebClient 建立面板與 NPC 夥伴建構器都讀同一張卡，沒有第二份作者副本。

| 資料域 | 欄位 | 內容 |
|---|---|---|
| 身份 | `key`、`display_name`、`age`、`apparent_age`、`race`、`subrace`、`sex` | registry 鍵、顯示名、實際與外表年齡、種族亞種、性別 |
| 配點 | `allocations`、`emphasis` | 七軸原始配點與一句話配點說明 |
| 技能 | `active_skills`、`passive_skills`、`skill_proficiency`、`affinity_elements` | 主動／被動技能鍵、宣告式練習 XP、開局親附屬性 |
| 物品與裝備 | `starting_items`、`starting_equipment` | 開局攜帶清單，以及其中開局就穿上的子集 |
| 人格 | `persona` | import-card 形狀的七鍵人格（見 §3 Step 2） |
| 性傾向基線 | `sexual_baseline` | 寫入 `entity.db.sexual` 的開局狀態，`None` 則沿用泛用預設 |
| 偽裝 | `disguised_stats` | 純顯示層的偽裝軸值，永不進入戰鬥與判定 |
| 夥伴 | `starting_companions` | 指向夥伴自己模板卡的同行宣告清單 |
| 頭像回退 | `fallback_key` | 無生成頭像時改用的內建回退圖鍵；選填，未宣告時走性別／年齡帶規則 |

`PlayerPreset` 在 `starting_items` 之後宣告了 `_: KW_ONLY` 標記（field-parity 設計 3.2）。`sex` 因此是**必填的關鍵字引數**，新卡漏寫它會在構造時直接 `TypeError`，不會靜默繼承 `DEFAULT_SEX`；`sex` 之後的所有欄位也只能用關鍵字傳入。registry 現行卡把 `key` 到 `emphasis` 八個欄位寫成位置引數，其餘一律關鍵字，沿用既有的寫法即可。

### 三條建立路徑，兩套數值語意

同一個角色有三種進入世界的方式，它們對「數值」的宣告方式不同，這是刻意的平衡決定，作者不要把差異看成遺漏。

| 路徑 | 數值宣告 | 驗證 | 文件 |
|---|---|---|---|
| 模板（本文） | `allocations`：七軸各 0～軸跨度，總和必須恰好等於該 race＋subrace 設定檔的預算 | lore CI 測試 `world/lore/tests/test_player_presets.py` 釘住每張卡的總和與跨度；啟動時 `_validate_allocations()` 再驗一次 | 本指南 |
| 自訂建立 | 同樣是 `allocations`，由玩家逐軸輸入 | `preflight_character_creation()` 即時驗證 | [角色建立與匯入](/gm/characters) 下半部 |
| JSON 匯入卡 | 絕對 `stats`（直接給最終值） | `CHARACTER_SCHEMA_V1` 結構與語意驗證 | [角色建立與匯入](/gm/characters) 上半部 |

模板為何宣告**配點**而匯入卡宣告**絕對數值**？配點邊界與預算由 `resolve_starting_profile(race_key, subrace_key)` 完全從不可變 lore 推導：七軸上下界取自種族的 `vital_baseline`／`static_baseline`，亞種的 `vital_overrides` 可以覆寫邊界，預算則是各軸跨度總和除以二無條件捨去（`sum(span) // 2`）。卡宣告的是「花多少預算」，啟動時 `_resolve_values()` 才把配點換算成絕對值（下界加配點，再乘上亞種對三個物理軸的靜態修正；`magic_power` 可配但無修正，啟動後 `guild_merit` 釘 0）。若模板直接寫絕對值，種族魔力帶一改，卡的實際價值就悄悄漂移；宣告配點讓同設定檔的每張卡付出同一個預算，價值由規則層機械性保證。匯入卡走的是另一套機制：它是內容作者與 NPC 的路徑，沒有預算算術，`disguised_stats` 的鍵必須是 `stats` 子集之類的規則是匯入路徑專屬，模板路徑無法照抄（模板宣告配點，沒有絕對 `stats` 可比）。

---

## 2. 事前決定：寫卡之前要回答的四個問題

1. 種族與亞種選哪個？`race` 必須在 `RACE_REGISTRY`、`subrace` 必須在 `SUBRACE_REGISTRY` 且屬於該種族，每張模板卡都必須帶亞種（沒有「無亞種」卡）。先用 `resolve_starting_profile()` 看清這個配對的預算與邊界。
2. 配點怎麼分？預算由設定檔決定（人類設定檔目前是 224），七軸各在 0～跨度內取，總和不許差一。`allocations` 的 `magic_power` 項目就是該卡的開局魔力字面值（成長重設計 D-A5 已刪除種族平均取樣器），模板的魔力是作者寫的，不是隨機抽樣出來的。
3. 技能組碰不碰血脈前置？宣告的 kit 在啟動時由 `lineage_ownership_closure()` 補齊前置鏈、再由 `seed_lineage_proficiency()` 把未滿足的前置邊播到恰好達標。作者只需宣告核心技能，前置交給閉包；要改變某條邊的練習值，才需要 `skill_proficiency`。kit 裡若有 `requires_divine_arts` 的技能，種族必須 `can_use_divine_arts`，否則載入即爆。
4. 這張卡需不需要隱藏身分層與夥伴？`persona` 的 `identity` 有公開／隱秘兩層，隱秘層供 PersonaStore 渲染；`starting_companions` 的每筆指向夥伴**自己**的 registry 卡，所以夥伴得先作為一張可選卡存在（雙胞胎互宣告就是這個形）。

---

## 3. Step by Step

### Step 0 — 讀取邊界與預算

不要發明預算。先算出這個種族亞種設定檔的邊界：

```python
from world.rules.character_creation import resolve_starting_profile
profile = resolve_starting_profile("human", "human_commoner")
print(profile.budget)   # 目前人類為 224
print(profile.bounds)   # 七軸各 (下界, 上界)
```

`allocations` 的每一項是 `("軸名", 值)` 成對，值取 0～該軸跨度，七軸必須齊全。

### Step 1 — 寫入 `PLAYER_PRESET_REGISTRY` 一筆

在 `PLAYER_PRESET_REGISTRY` 直譯中加入一筆，範例是最小合法形狀：

```python
"new_hero": PlayerPreset(
    "new_hero", "新英雄", 20, 20, "human", "human_commoner",
    (("hp", 50), ("mp", 50), ("sp", 50), ("atk_phys", 10),
     ("agility", 10), ("defense", 11), ("magic_power", 43)),
    "生命力與魔力均衡的開局配點",
    active_skills=("light_sword_style",),
    passive_skills=("body_enhancement_basic",),
    starting_items=(("plain_sword", 1), ("leather_armor", 1)),
    sex="female",
),
```

`emphasis` 是給建立畫面顯示的一句配點說明。`age` 與 `apparent_age` 是兩個獨立宣告，精靈卡常用 180／24、222／24 這類實際與外表分離的寫法；CI 測試要求每個種族至少有一張卡。

### Step 2 — 人格七鍵

`persona` 是 `PresetPersona`，作者寫七個鍵：`identity`（`PresetIdentity` 的公開／隱秘兩層）、`personality`、`life_story`、`habit`、`appearance`（`PresetAppearance` 的七個外觀子鍵）、`social_connection`（`(名字, 關係)` 成對元組）、`background`。所有值都可留空，讓一張卡能增量撰寫。啟動落庫由 `to_record()` 單點展開成 import-card record：六個 `PERSONA_IMPORT_CARD_KEYS`（identity、personality、life_story、habit、appearance、social_connection）永遠存在，未撰寫的散文欄是空字串、結構欄是空字典；空白的 identity 層從 identity 子樹省略、空白的外觀子鍵省略，`background` 則只在非空時才進 record。

兩個長度上限要分清。persona 的散文欄（含 identity 兩層、外觀子鍵、`social_connection` 的兩側）上限 600 碼點（`MAX_PERSONA_FIELD_LENGTH`），由 `world/rules/character_creation.py` 在自身匯入時掃 registry 執行。而建立面板的模板卡描述元把 `background` 卡住 256 碼點（`MAX_BACKGROUND_CODE_POINTS`），repo 契約測試 `tests/test_creation_parity_contract.py` 釘住每張出貨卡的 `persona.background` 不超卡界。寫滿 600 的背景過得了 rules 掃描、過不了卡契約，先照 256 寫。

### Step 3 — 宣告技能組與練習 XP

`active_skills`／`passive_skills` 只寫技能鍵，啟動時閉包自動補前置；宣告的 `skill_proficiency` 條目是 `(技能鍵, 練習 XP)` 成對，**宣告值永遠壓過播種值**，即使它故意留白一條前置邊（與匯入記錄的顯式條目同一優先序）。條目也可以點名 kit 閉包之外的技能，啟動會照匯入路徑的做法原樣持久化。值必須是有限非負數、`bool` 不算數字、同一技能不得重複。

### Step 4 — 開局物品與穿戴子集

`starting_items` 是 `(物品鍵, 數量)` 成對，鍵必須在 `ITEM_REGISTRY`、數量為正整數、同鍵不得重複（多份用數量表達）。`starting_equipment` 宣告其中**開局就穿上**的子集，每個鍵必須同時出現在 `starting_items`（背包是持有事實的唯一來源），且必須是有槽位的登錄裝備。啟動用 `world/rules/equipment.py::toggle_equipment`（裝備唯一寫入者）逐件切換，因此重複鍵會穿了又脫、單例槽（主副武器、護甲）同槽兩件會互相覆寫、飾品超過 5 件上限，這三種事故全部改在載入期攔截，不要留到啟動。

### Step 5 — 性傾向基線與偽裝層

`sexual_baseline` 選填，`None` 時不寫任何狀態，`SexualState` 繼續沿用泛用預設基線。有宣告時是 `PresetSexualBaseline`：`arousal`、`virgin`（真 bool）、`sensitivity`（`(部位, 等級)` 成對）必填；`wetness`、`shame`、`exposure`、`climax_phase` 選填，留空的會被 `to_record()` 省略、由建構器落到詞彙表最低階。各等級值必須是 `world/lore/sexual_vocab.py` 對應詞彙元組的成員，部位要在 `BODY_PARTS` 加泛用部位 `軀體` 之內。必填的 `arousal` 不容許空字串，只有四個選填欄可以留空。

`disguised_stats` 是 `(軸名, 值)` 成對的純顯示層，值必須是恰好的 `int`（`bool` 拒絕）。軸名刻意不設白名單（`CHARACTER_SCHEMA_V1` 對該欄也只約束整數值），同鍵重複會被拒，因為 `dict()` 會靜默丟掉先寫的那筆。

### Step 5.5 — 頭像回退鍵（選填）

`fallback_key` 宣告這張模板的角色在**尚無生成頭像**時改顯示哪張內建回退圖。值是閉合詞彙表的成員——`man`、`woman`、`boy`、`girl`、`elder`、`monster_anon` 六鍵之一（常數住在 `world/art/fallback_keys.py`）——其餘一律留 `None`：玩家模板未設定時，解析器依存放的性別與外表年齡落到 child／adult／elder 年齡帶，`female`／`male` 直取該帶的性別鍵，其他性別以 subject 鍵雜湊到該帶的有序圖池（怪物不受模板影響，未宣告時一律 `monster_anon`）。這層純粹是顯示層回退，一旦該角色有了生成頭像卡片，頭像解析永遠優先於回退圖。詞彙表由 `_validate_preset_fallback_keys` 在 lore 匯入時逐卡檢查（見 §4），typo 直接在載入期爆。

### Step 6 — 宣告同行夥伴

`starting_companions` 每筆是 `StartingCompanion(preset_key, affinity, relationship)`：`preset_key` 點名夥伴自己的卡（夥伴的數值、技能、物品、人格全部來自那張卡），`affinity` 是啟動綁定播進關係記錄的值，`relationship` 是寫進夥伴人格 `social_connection` 的關係標籤。同一張卡不得宣告自己、不得重複點名同一夥伴；數量與數值邊界（見 §4）在 rules 層掃。

### Step 7 — 補測試與驗證

新卡會自動進建立畫面（`build_preset_cards()` 讀 registry），通常零程式碼。但 `world/lore/tests/test_player_presets.py` 釘住了目錄現況：種族覆蓋、恰好八張卡的名單與鍵順序、每張卡的核准開局裝載。加卡時要**有意識地更新**這些釘值，它們是目錄契約，不是要繞過的障礙。依序跑最小聚焦集：

```sh
MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb \
  world.lore.tests.test_player_presets \
  world.rules.tests.test_character_creation \
  world.rules.tests.test_starting_companions
uv run --locked python -m tools.spec_traceability check
```

---

## 4. 載入期驗證器總表

宣告錯誤一律在載入期爆，不拖到玩家啟動。三個觸發點要分清：`world.lore.player_presets` 自身匯入跑十一個驗證器；`world/rules/character_creation.py` 與 `world/rules/starting_companions.py` 在**各自模組**匯入時掃 registry，讀的是 lore 看不見的 rules 常數（lore 不得匯入 rules，這是 field-parity 設計 3.1 定的責任線），後者另由伺服器啟動的同步步驟顯式執行。所有錯誤訊息都以 `preset <key!r>` 開頭點名肇事卡。

| 驗證器 | 觸發於 | 何時爆 | 錯誤訊息（節錄） |
|---|---|---|---|
| `_validate_preset_skill_kits` | lore 匯入 | 未知技能、主動被動錯類、神術技能落在無神性種族 | `declares unknown skill`／`the registry classifies it as`／`on a race without divine affinity` |
| `_validate_preset_identities` | lore 匯入 | 未知種族／亞種、亞種不屬於該種族 | `declares unknown race`／`belonging to race ... not ...` |
| `_validate_preset_affinity_elements` | lore 匯入 | 未知屬性、重複屬性、精靈宣告非空親附集 | `declares unknown affinity element`／`elf preset ... must declare an empty affinity set` |
| `_validate_preset_starting_items` | lore 匯入 | 條目形狀壞、未知物品、同鍵重複、數量非正整數 | `malformed starting-item entry`／`declares unknown item`／`declares duplicate item`／`non-positive quantity` |
| `_validate_preset_starting_equipment` | lore 匯入 | 穿戴鍵不在 `starting_items`、重複、非裝備、單例槽相衝、飾品逾 5 | `absent from its starting_items`／`that is not equipment`／`claiming the same ... slot`／`more than 5 starting accessories` |
| `_validate_preset_sex` | lore 匯入 | `sex` 不在 `SEX_VALUES`（`female`／`male`／`other`） | `declares unknown sex` |
| `_validate_preset_personas` | lore 匯入 | 散文欄非文字、identity／appearance 型別壞、`social_connection` 非成對文字、關係名重複 | `persona.<欄> that is not text`／`is not a PresetIdentity`／`not a (name, relationship) pair` |
| `_validate_preset_skill_proficiency` | lore 匯入 | 未知技能、重複條目、值非有限非負數（`bool` 拒） | `proficiency for unknown skill`／`duplicate proficiency`／`non-numeric or negative proficiency` |
| `_validate_preset_disguised_stats` | lore 匯入 | 條目形狀壞、軸名非文字、同鍵重複、值非恰好 `int` | `malformed disguised_stats entry`／`duplicate disguised_stats key`／`non-integer disguise value` |
| `_validate_preset_sexual_baselines` | lore 匯入 | 非 `PresetSexualBaseline`、`virgin` 非真 bool、等級越出詞彙表（僅四個選填欄可空）、部位未知或重複 | `outside its vocabulary`／`unknown body part` |
| `_validate_preset_starting_companions` | lore 匯入 | 非 `StartingCompanion`、夥伴卡未登錄、宣告自己、同夥伴重複 | `that is not registered`／`declares itself as its own companion`／`more than once` |
| `_validate_preset_fallback_keys` | lore 匯入 | `fallback_key` 不在閉合詞彙表（六鍵之外且非 `None`） | `declares fallback key ... outside the closed fallback vocabulary` |
| `_validate_preset_persona_lengths` | `character_creation` 匯入 | persona record 任何字串超過 600 碼點 | `exceeds the 600-character length cap` |
| `_validate_preset_companion_bounds` | `starting_companions` 匯入 | 夥伴數超過 `PARTY_MAX_COMPANIONS`（4）、`affinity` 不在 1～`NATURAL_CAP`（99）或為 bool、`relationship` 超過 600 | `more than the party cap 4`／`outside 1..99`／`persona length cap` |

配點預算的精確性**不在**匯入期驗證器之列：`world/lore/tests/test_player_presets.py` 在 CI 釘住每張卡總和等於預算、逐軸不超跨度，啟動時 `_validate_allocations()` 會以 `allocations must sum exactly to <預算>` 拒收壞卡。卡摘要超過 256 碼點則由 `tests/test_creation_parity_contract.py` 在 repo 契約測試層抓。

---

## 5. 常見錯誤

| 錯誤 | 後果 |
|---|---|
| 精靈卡宣告非空 `affinity_elements` | lore 匯入即爆。精靈的親附永遠由亞種在啟動時播種，模板不得代宣告 |
| 神術技能落在無神性種族 | lore 匯入即爆；先確認 `can_use_divine_arts` |
| `allocations` 總和不等於預算 | 載入無事、CI 與啟動爆。這是配點制最容易踩的一條，Step 0 先算預算 |
| `starting_equipment` 的鍵不在 `starting_items` | lore 匯入即爆。背包是持有事實唯一來源，穿戴只能是子集 |
| persona 散文欄寫超過 600 碼點 | `world.rules.character_creation` 匯入即爆，訊息點名卡與欄 |
| `persona.background` 寫超過 256 碼點 | rules 掃描過得了、`tests/test_creation_parity_contract.py` 爆。卡契約界比 persona 散文界緊 |
| 同一物品在 `starting_items` 寫兩筆 | lore 匯入即爆，多份請用數量 |
| 兩件裝備宣告同一單例槽、或第六件飾品 | lore 匯入即爆（見 §4 `starting_equipment` 列） |
| `sex` 漏寫或企圖用位置引數傳 | 構造直接 `TypeError`（KW_ONLY 標記），這是 change 1 故意留的防呆 |
| 夥伴宣告指向自己或未登錄的鍵 | lore 匯入即爆；夥伴必須是 registry 裡另一張卡 |
| 拿匯入卡的規則套模板（例如要求 `disguised_stats` 的鍵是 `stats` 子集） | 模板路徑沒有絕對 `stats`，該規則是匯入路徑專屬；兩套語意見 §1 對照表 |

---

## 6. 什麼時候這不是一篇指南能帶你走完的事

加一張卡（新種族的代表角色、新開局裝載）照上面的流程做即可。以下三類工作超出模板本身的範圍，請改走對應指南：

- 卡片需要新的物品、新的裝備槽或新的效果鍵：見[新增物品指南](/development/adding-items)。
- 卡片需要新的魔法、新的技能或新的血脈前置邊：見[新增魔法指南](/development/adding-spells)。
- 要建立的不是玩家模板，而是 NPC 或測試資料用的絕對數值角色卡：見[角色建立與匯入](/gm/characters)。

要動驗證器本身（新邊界、新詞彙、新資料域）就屬於規格驅動變更，請走 OpenSpec 流程並同步 `player-character-creation` 相關主規格。
