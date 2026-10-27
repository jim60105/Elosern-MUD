# 新增 NPC 指南

本指南說明如何為 Elosern 加入一個新的 NPC。同一個「非玩家活體」有四條進入世界的路徑，各自負責不同內容。JSON 匯入卡負責一次性內容人物，地點登錄表負責永久服務主人，任務場景具現化負責關卡人物，預設卡負責同行夥伴。本文走一遍選路、寫卡、裝配能力元件、接上劇本對話、排程、驗證的完整流程。

本文假設你已讀過：

- `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`（世界資料與確定性核心的邊界）
- [角色建立與匯入](/gm/characters)（JSON 卡欄位語意的現行契約）
- `world/imports/schema.py::CHARACTER_SCHEMA_V1`（結構驗證的唯一來源）
- `world/rules/npc_capabilities.py`（能力詞彙、驗證與組裝的唯一擁有者）

---

## 1. 背景：NPC 有四條建立路徑，語意各不相同

先選對路徑。四條路徑建的實體都是 `typeclasses/npcs.py` 的 `NPC` 家族，但它們的身份來源、數值來源、擺放者都不同，拿錯路徑的規則套另一條路徑是這類工作最常見的錯誤。

| 路徑 | 建立者 | 用途 | 型別 |
|---|---|---|---|
| JSON 匯入（本文） | `world/imports/loader.py::load_batch`／`instantiate_character` | 一次性內容人物（旅人、僱傭兵、劇情人物） | `NPC`（預設型別） |
| 地點登錄表服務主人 | `world/lore/settlements/places.py` 的 `host_*` 欄位，由 `world/rules/guild_economy.py::sync_service_content` 於啟動冪等建立 | 永久服務主人（店主、公會主管、店主兼對話、管事） | `NPC`（啟動同步建立，永不手動匯入） |
| 任務場景具現化 | `world/quests/scene_builder.py` 依 `world/lore/npc_tiers.py::NPC_TIER_REGISTRY` 的角色階級生成 | 任務階段場景人物 | `scene_npc` 原型（白名單限定） |
| 同行夥伴 | `world/rules/starting_companions.py::build_starting_companion` | 預設卡 `starting_companions` 宣告的夥伴 | `LLMNPC`（`invite` 只收 `LLMNPC`） |
| 已發表場景包相遇 | `world/quests/encounters.py::publish_scene_package` 發表不可變的場景包，`world/quests/encounter_activation.py::activate_scene_encounter` 在玩家實際所在的房間具現化 | 驗收任務前即可遇見的具名故事角色；任務完成、失敗或放棄後仍保留身分、人格與記憶 | `scene_llm_npc` 原型（白名單限定，型別為 `LLMNPC`） |

五條正式路徑在建立時皆會初始化完整的精簡角色卡（Compact Card），寫入版本 1 的人物設定與來源中繼資料。若透過 Evennia 建造者指令（`create` 或 `spawn`）建立 `NPC`，則會繞過所有初始化程式；這類非出貨來源物件未持有角色卡，在遊戲內的人物設定編輯器入口會顯示停用狀態（`npc_persona.unavailable`）。

已發表場景包的持久化屬於 `world/quests`：它是一個正式的 Django app（`world.quests.apps.QuestsConfig`，列於 `server/conf/settings.py` 的 `INSTALLED_APPS`），擁有不可變的 `ScenePackage` 已發表定義，以及角色綁定、相遇啟動、對話階段與委託授權等執行期資料表。資料庫唯一鍵是其契約的一部分：一個（場景包，角色）只綁定一個實際角色，一個（場景包，場景，玩家）只有一個啟動身分，因此重啟不會產生第二個角色。新增或調整資料表時，在 `world/quests/migrations/` 宣告遷移；已發表的 payload 永不改寫。

依據設計文件 `docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §13c 條款（KISS 原則），未使用的離線人物設定套件（Offline Persona Bundles）子系統已完整移除，不維護離線套件選擇器或相容別名；若未來有經正式核准之重啟需求，可由 Git 歷史紀錄復原。現行所有生產環境 NPC 皆透過上述五條完整卡片路徑建立。

對話行為是另一個正交的決定：

| 對話形態 | 條件 | 降級行為 |
|---|---|---|
| 劇本對話（`talk` 關鍵詞查表） | NPC 帶 `ScriptedDialogue` 元件，`dialogue_key` 指向 `world/lore/dialogue/` 已登錄的表 | 未知關鍵詞回覆無理解行；查得到的表永遠可用，完全離線可玩 |
| 生成對話（guarded LLM） | 型別是 `LLMNPC`；`at_talked_to` 走 `world/ai/npc_dialogue.py` 護欄管線 | 護欄降級時改說 `resolve_greeting(npc)` 的離線問候語（執行個體欄位優先，次為劇本／Profile）或沉默 |
| 生成階段對話（已發表場景包） | 角色帶 `ScriptedDialogue`，`dialogue_key` 形如 `scene_role:<package id>:<role id>`；`world/rules/dialogue.py` 的共享解析器重新解析目前階段，回傳完整 `AuthoredDialogue` 與效果關聯 | 完整場景、變體、條件、婉拒、接續與閱讀完全離線可用；階段一改變，舊情境、交付與通知範圍立即失效並刷新為當前階段 |

匯入器預設建 `NPC`（純劇本對話／無對話）。生成對話人物必須顯式傳 `typeclass=LLMNPC`。

---

## 2. 事前決定：寫卡之前要回答的五個問題

1. **這是永久服務主人嗎？** 是 → 走地點登錄表：在 `world/lore/settlements/places.py` 的 `PlaceDefinition` 宣告 `host_name`／`host_race`／`host_subrace`／`host_sex`／`host_profile_key` 與 `components`（直接能力宣告），啟動 `sync_service_content` 依登錄表推導名冊、find-or-create 主人並組裝能力。**不要**用匯入卡建永久主人。

   主人的身分是 **canonical authored identity**：名冊列（`ServiceHostRow.host_key`）與活體 NPC 身上的 `npc_profile_key` 取自同一個 `host_profile_key`。同步只憑這個鍵找人，**不再**看元件的排列順序、元件的 `service_id`、顯示名或位置；因此調換／增減能力、或改寫 `service_id`，都不會生出第二個人。同一個 host key 若被兩個活體 NPC 或兩列名冊同時宣稱，整批在寫入前就以具名完整性錯誤拒收；若該身分屬於常駐冒險者（`guild_adventurer_person_key`），同步也拒收、絕不接管。

   名冊對主人只做兩件事：一是把**受管能力集合**（六個能力詞彙：`guild_staff`／`guild_exam_reception`／`merchant`／`scripted_dialogue`／`quest_issuer`／`church_host`）收斂到宣告值——缺少的補上、宣告裡沒有的移除，六個詞彙以外的元件永不觸碰；二是只改寫**作者設定白名單**（各能力自己的 `service_id`／`shop_key`／`branch_key`／`dialogue_key`／`issuer_key`／`church`／`initial_arousal`，加上組裝唯一寫入的 `service_binding`／`anchor_room_id`）。商人的 `merchant_stock`／`last_restock_day`、位置、庫存、關係與其他遊戲狀態都屬於各自的擁有者，同步不會重置；主人的位置即使離開錨定房間也不會被搬回（place-bound 服務因此維持暫停）。

   整批（身分預檢 → 室內準備與**完整**房間解析 → 能力組裝 → 初次庫存 → 整列退役）在同一個交易內執行。房間解析必須全部成功：tag 對不到房間、對到多個房間、或對到非 Room 物件，都以具名完整性錯誤拒絕**整個**操作，不會略過單列，已準備的室內也一起回滾；任何一步失敗都回滾資料列，並還原重用主人的屬性／標籤／元件快取、清掉本批建立的實例、補回已執行退役所動到的隊伍／附身狀態。

   名冊列被整列移除時，才由 `content_source` 類別下的 `service_host` 標籤授權**整列退役**：只有「正常同步套用過該列」的主人帶有此標籤，且只有在其 canonical identity 不再被任何列宣告時才刪除；刪除走既有 `NPC.at_object_delete` 生命週期。沒有標籤的 NPC（不論帶著什麼舊屬性殘留或舊 `service_id`）永不被同步刪除，舊資料也永不構成任何查詢或刪除依據。
2. **需要什麼能力？** 能力就是**直接宣告**在該人物身上的元件，沒有職業藍圖、沒有展開、沒有隱含預設。每個能力一筆 `{type, kwargs, binding}`，同一型別只能一筆：

   | 能力型別 | 必填 kwargs | 選填 kwargs | 綁定 |
   |---|---|---|---|
   | `merchant` | `service_id`、`shop_key` | — | 必填 |
   | `guild_staff` | `service_id`、`branch_key` | — | 必填 |
   | `guild_exam_reception` | `service_id`、`branch_key` | — | 必填 |
   | `quest_issuer` | `service_id` | `issuer_key`（留空即 `npc:#<pk>`） | 必填 |
   | `scripted_dialogue` | `dialogue_key` | `service_id` | 選填（純敘事對話不綁定） |
   | `church_host` | `service_id`、`church`、`initial_arousal` | — | 必填 |

   綁定只有兩種寫法：`{"kind": "person"}`（服務跟著人走，不得帶錨定房間）與 `{"kind": "place", "anchor_room": "<房間 tag>"}`（tag 必須恰好解析到一個 Room）。`service_binding`／`anchor_room_id`／`merchant_stock`／`last_restock_day` 屬執行期欄位，作者資料一律不得填寫。地點主人宣告的每個能力都綁在**自己的房號**（`place.key`）；沒有能力的主人（`components=()`）也是合法宣告，同步只保留人、清空受管能力。

   多數出貨地點是常見組合：店主＝`merchant` + `scripted_dialogue`；公會主管＝`guild_staff` + `guild_exam_reception` + `scripted_dialogue`；純接待＝`scripted_dialogue`；主祭＝`scripted_dialogue` + `church_host`。這些組合本身就是各能力並列的結果，沒有可引用的職業列。

3. **需要劇本對話嗎？** 對話住在 `world/lore/dialogue/content/<profile_key>.yaml`，由載入器自動探索載入為不可變 `DIALOGUE_SNAPSHOT`。見 Step 3。
4. **需要日程嗎？** 排程詞彙住在 `world/rules/rulebook/npc_schedules.yaml`：狀態詞彙 `duty`／`resting`／`busy`，模板 `guard`／`storekeeper`／`resident`。匯入與能力宣告都不再附帶排程預設，需要排程時由程式呼叫 `world/rules/npc_schedules.py::set_npc_schedule`（`db.schedule` 的唯一寫入者）。
5. **數值來源在哪？** 設計文件與既有 rulebook。`stats` 是匯入卡路徑的字面基準值（永不預先乘技能倍率）；平衡數值由設計文件決定，卡作者不發明平衡表。
6. **這是出貨的服務主人、常駐冒險者或同行夥伴嗎？** 服務主人與常駐冒險者必須在 `world/lore/npc_profiles/` 所屬切片登錄 `NpcProfile`，並在地點或 `world/lore/guild_adventurers.py` 的人物列填入引用鍵；同行夥伴則在夥伴預設卡填寫延伸欄位。所有出貨來源都必須登記於名冊清單，見 §3.1。

---

## 3. Step by Step

### Step 0 — 核對登錄鍵

卡上點名的每個鍵都必須已登錄：`race`／`subrace`（`world/lore/races.py`）、`skills`／`passives`（`world/skills/registry.py`）、`inventory` 的物品鍵（`ITEM_REGISTRY`）、各能力的 `service_id` 與店號／分會鍵、`dialogue_key`（`DIALOGUE_ROWS`）、`host_profile_key`（`NPC_PROFILE_REGISTRY`）。CLI 驗證器全部比對，未知鍵直接拒收。

### Identity-qualified skill kits

Character import validation supplies the intended actor kind from the target
typeclass (`npc` by default, `player` for player targets) and the authored
`race`/`subrace`. It checks both declared skills/passives and prerequisite
closure additions through `record_identity_eligible`, without constructing
entities. An incompatible key produces an issue naming `skills` or `passives`
and the offending key before batch persistence. Monster-only ownership is
invalid in character imports. Registry-unavailable degraded reporting remains
unchanged. See [Identity eligibility](adding-spells.md#identity-eligibility)
for declaration semantics.

### Step 1 — 寫 JSON 角色卡

複製 `world/imports/examples/example_character.json`，欄位語意見[角色建立與匯入](/gm/characters)。NPC 特有的四條規則：

- **`key` 就是遊戲內顯示名。** 載入器以 `key` 建立 Evennia 物件，`display_name` 目前不被使用；要讓人物列顯示中文姓名，`key` 就寫中文。房間人物列、`看` 標題、探索面板、對話、隊伍與 GM 檢視一律只顯示這個純姓名。角色定位請寫在 `persona` 與描述文字裡，沒有獨立的 NPC 稱號欄位。
- **GM 檢視不代替玩家。** GM 執行期頁的「服務」區塊列出與遊戲相同的服務項目與開啟路徑，但沒有選定玩家角色，所以可用性一律顯示 `context_required`；「能力設定診斷」另外列出綁定、錨點、元件設定與對話來源關聯。兩者都唯讀，不會提供任何玩家權限，也不會把設定問題誤報成沒有服務。詳見 [GM 執行期狀態檢視](/development/gm-portal-runtime-inspection)。
- **`age`／`apparent_age` 各自獨立**，0–10000 整數（拒絕布林值）。常駐 host 與考官由 `NpcProfile` 作者宣告明確定案數值（`age` 與 `apparent_age` 必填），落庫與同步時優先使用 profile 定義的年齡；未指定 profile 或無作者年齡的路徑由 `ensure_npc_canonical_age` 獨立補 `NPC_DEFAULT_AGE`（18）。既有欄位值永不覆寫，重用與重啟時保留玩家編輯的 persona 與既有年齡。既有開發世界若需完整套用作者年齡，請依照 reset runbook 重設資料庫。
- **`persona` 必須是完整的精簡 NPC 角色卡**：恰好 `identity{public,hidden}`、`appearance`、`personality`、`speech_style`、`life_story`、`habit`、`social_connection` 七欄，全為純文字（`identity.hidden` 與 `social_connection` 可空，其餘必填）；沒有 `background`。契約由 `world/lore/npc_card.py::normalize_card` 唯一執行（單欄 600、身分段 600、整卡 2000 碼點；身分段與整卡都以渲染後的區塊計算，含「性格：」等標籤與換行，不只是欄位文字）。判斷依據是傳給 `validate_character`／載入器的目標型別（`issubclass(typeclass, NPC)`，預設即 NPC），絕不看記錄內容；`PlayerCharacter` 目標的 `persona` 仍不透明、原樣落庫。落庫走 `world/rules/npc_persona.py::initialize_npc_persona`，寫入正規化後的卡與版本 1 中繼資料（來源 `{"kind": "import", "record": <key>}`），與整批同一筆交易。
- **`disguised_stats` 非空時種族必須能用神之秘法**，同[新增角色模板指南](/development/adding-player-presets) §4 的不變式；`_check_disguised_stats_subset` 另要求偽裝鍵是 `stats` 子集。

服務 NPC 再加選填的職業三欄：

```json
{
  "key": "old_pike",
  "display_name": "老柏克",
  "age": 57,
  "apparent_age": 54,
  "race": "human",
  "subrace": "human_plains",
  "sex": "male",
  "stats": {"hp": 90, "mp": 20, "sp": 60},
  "components": [
    {
      "type": "scripted_dialogue",
      "kwargs": { "dialogue_key": "ferry_attendant" },
      "binding": { "kind": "place", "anchor_room": "riverside_ford" }
    }
  ],
  "...": "其餘必填欄見範例卡"
}
```

組裝語意（`world/imports/loader.py::_apply_capabilities`）：

- `components` 是獨立的直接宣告：沒有藍圖可以覆寫，也沒有職業可併用；同一型別只能一筆，順序不代表任何語意。
- 設定一律手寫，匯入器絕不憑空補值：`shop_key`（merchant）、`branch_key`（guild_staff／guild_exam_reception）、`dialogue_key`（scripted_dialogue）、`issuer_key`（quest_issuer，缺席時解析為 `npc:#<pk>`）。缺任何必填設定都整批具名拒收。
- 每個服務能力自己帶 `binding`。person 綁定不得帶錨定房間；place 綁定的 `anchor_room` 是 **room tag**，載入器在同一筆交易內解析：tag 解析不到房間、解析到多個房間、或落在非 Room 物件上，都整批拒收並點名記錄與 tag。
- 純敘事對話（`scripted_dialogue` 不帶 `binding`）只走既有的交談、共處與排程條件，不產生任何服務入口。
- 特質只由種族基準加卡上的字面 `stats` 組成，能力宣告不影響任何數值；`age`／`apparent_age` 仍各自限制在 0–10000。

### Step 2 — 驗證

```sh
uv run --locked -m world.imports.validate content/characters/old_pike.json
```

CLI 只檢查檔案本身與批次內一致性（含批次內重名）；**與資料庫既有 NPC 的重名由載入器把關**，CLI 不回報。批次全綠才進入載入。CLI 以 NPC 為目標，角色卡違規以 `persona.<欄位>` 加穩定原因碼（`missing_field`、`unknown_field`、`not_text`、`required_empty`、`leaf_too_long`、`identity_section_too_long`、`card_too_long`）回報；契約遇到第一個違規就停，一次只會看到一個角色卡問題。

### Step 3 — 劇本對話（需要時）

對話是作者身份，檔案放置於 `world/lore/dialogue/content/<profile_key>.yaml`，由 `load_dialogue_snapshot` 自動探索並載入為不可變 `DIALOGUE_SNAPSHOT`。新增一表：

```yaml
# world/lore/dialogue/content/<profile_key>.yaml
schema_version: 1
greeting: "老柏克靠在船篙旁：「要過河？講聲『過河』就知道價。」"
topics:
  - topic_id: "ferry_attendant.topic_01"
    keyword: "過河"
    label: "過河"
    fallback:
      scene_id: "ferry_attendant.topic_01_scene"
      revision: "r1"
      lines:
        - kind: "speech"
          speaker: "actor"
          text: "過河"
        - kind: "speech"
          speaker: "host"
          text: "「十銅板，綁好你的馬。」"
```

規則端 `world/rules/dialogue.py` 只是唯讀介面，`DIALOGUE_TABLE` 是唯讀包裝，`talk` 查不到鍵就回覆無理解行。`guild_staff` 表的 `回報` 關鍵詞是唯一例外，它經 `world/rules/guild.py` 解析可回報任務清單，屬規則行為，不要在自製表裡模仿。

#### YAML 靜態對話載入契約（`world/lore/dialogue/content/<profile_key>.yaml`）

靜態劇本對話支援由檔案系統自動探索，不需手動維護檔名索引或 Python 匯入清單：

1. **檔名即擁有者身分**：對話檔案必須放置於 `world/lore/dialogue/content/<NpcProfile.key>.yaml`。檔名主體（stem）必須等於已登錄的 `NpcProfile.key`。內容中嚴禁宣告任何顯式 `npc_id`、`profile_key`、`owner` 或 `dialogue_key` 欄位（違者整批拒收）。
2. **雙向完整性與原子載入**：啟動時由載入器比對現行地點／服務中解析出的規範綁定（`dialogue_key -> profile_key`；於後續 runtime 切換時接上正式啟動點）。每一個綁定必須恰好對應一個探索到的檔案；每一個探索到的檔案也必須對應已登錄的 Profile 與綁定。任一檔案損壞、格式錯誤、包含未解析參照或孤立綁定時，載入器將拋出 `DialogueSourceError` 並拒絕發布整個快照，絕不允許局部載入或靜默退化。
3. **嚴格安全載入**：對話 YAML 檔案大小上限為 262,144 位元組（256 KiB），必須為嚴格 UTF-8 編碼。禁止符號連結（symlink）、多文件串流（`---`）、別名與錨點（`*` 與 `&`）、合併鍵（`<<`）、重複鍵（任一巢狀層級皆禁止）及不安全的物件標籤。

#### 條件式話題（`requires`、`variants`、`unavailable`）

話題可宣告 `requires` 與變體 `when`（同一套凍結的 `Condition` 型別），以及 `unavailable`／`refusal`。作者只需遵守下列規則：

1. **參照鍵必須存在於許可目錄**：`world/rules/dialogue_references.py::static_dialogue_references()` 由既有正式註冊表組合出 `race`、`social_identity`、`item`、`skill`、`preset`、`profile`、`daypart`、`guild_rank`（`GUILD_RANK_REGISTRY` 的正式階級鍵）、`quest`（`world/quests/catalog.py` 的正式委託宣告）與 `affinity_stage`（`world/rules/rulebook/affinity.yaml` 的階段鍵）等家族。宣告未登錄的鍵（例如拼錯的種族、物品、技能、日段、階級、委託、好感階段或無法唯一對應公開名稱的 profile）會讓整個快照以 `DialogueSourceError` 拒收，錯誤會標明檔案、profile 與 dialogue_key。靜態對話只能引用正式委託宣告；套件內的編譯委託只透過該套件自己的 `package_quests` 範圍與目前套件身分取得許可，外來套件的委託鍵在靜態目錄與執行期都不授予任何資格。
2. **提示只看正式標籤**：鎖定話題顯示的需求提示由同一份目錄的公開標籤組成（種族／物品／技能／預設角色／地點主人或常駐冒險者名稱／時段用語／暴露程度用語／公會階級名稱／委託顯示名稱與生命週期用語／好感階段名稱），不讀取可編輯的顯示名稱或人物設定散文。好感提示只顯示階段名稱，永不顯示目前好感數值或門檻數字。`profile` 家族只收錄能唯一對應一個正式公開名稱的設定檔。
3. **未達條件時的對外行為**：`unavailable: "hidden"` 與未知話題完全相同——不洩漏標籤、提示或內文；`unavailable: "locked"` 必須提供 `refusal`，玩家按下後播放該婉拒場景，不給好感或其他效果。`predecessors` 由玩家已儲存的閱讀進度決定：任何一個前置話題尚未讀完，該話題就完全不出現（即使宣告為 `locked` 也一樣），因此接續話題絕不會在前提未讀時先洩漏標籤或內文。

   **純接續（`disclosure: "pure_chain"`）與資格話題（預設 `qualified`）的分工**：
   - 純接續話題不得宣告 `requires`，只以前置話題為條件；它是無效果（含好感）的公開內容，會隨主話題一次交付並附上伺服器簽發的完成憑證，玩家依前置順序讀完後才在畫面上逐一揭露。純接續只用來推進閱讀與揭露順序，永不授權獎勵或受保護資訊。
   - 資格話題可以宣告 `requires` 與前置話題，但一律由伺服器在選取當下重新判定；它不會被預先夾帶進任何交付組合，前置未讀完時連標籤都不顯示，讀完且條件成立後才出現。
   - 兩者都以「主人（而非被附身的身體）＋穩定 host_key ＋穩定 topic_id」記錄閱讀；實體 dbid 重建立、存檔重載或同一階段回歸都不會清除已完成的話題。已讀完的話題不會因變體、換幕或重新上鎖而再次變成未讀。
   - **未讀標記與解鎖通知**（authored-dialogue-unread-notices）：開放但尚未讀完的正式話題在選單列尾顯示金色菱形未讀標記；鎖定話題只顯示鎖頭。玩家第一次見到某個話題 ID（第一次交談，或生成角色新換到的階段）時，當下已開放的話題只標為未讀，不跳通知。先前觀察到是鎖定或隱藏的話題後來因狀態改變而開放時，伺服器會把它併入一批（最多 16 個）解鎖通知，等目前場景讀完回到選單才顯示一則不搶焦點的提示，同一批不會重播；重新上鎖再開放、換幕回歸或重新連線都不會再通知，但未讀標記會保留到讀完為止。沒有 `requires` 的純接續話題只因前置話題讀完而出現，不另外通知。作者不需要為此宣告任何欄位：只要話題 ID 穩定，通知與未讀標記就會自動正確運作；改名或重新編號話題 ID 會被視為全新的話題。
4. **變體選擇是確定的**：同一話題中合法且最高 `priority` 的變體會被選中，沒有命中時使用 `fallback`；已交付的場景在當前對話中不會因後續刷新而改變（重複的 `selection_id` 回傳已提交的交付）。宣告重複 `priority` 會被拒收。
5. **求值為唯讀，且進度條件讀主人**：種族、社會身分、攜帶物、技能與暴露程度只讀行動者本身；同行條件要求目前的主人綁定且在行動者所在地；公會階級、委託與報酬領取只讀支配該行動者的主人（`context.owner`）的正式註冊與任務記錄，被操控身體自己的階級或任務紀錄永不代替主人；好感條件只讀對話主人對該主人的關係階段。委託條件區分六種狀態：`not_accepted`（從未有任何符合紀錄）、`in_progress`、`completed`（無論是否已領取報酬）、`reward_claimed`（已完成且該任務 ID 在正式領取帳本中）、`failed`、`invalidated`；重複實例採存在性比對。整個流程不消耗物品、不建立時鐘或性狀態處理器、不寫入技能練習、不寫入任務或領取紀錄、不授予任何效果。無效的執行期狀態一律判為不合格並留下一筆 `dialogue_condition_integrity` 邊界事件。

### Step 3.1 — 人物設定切片、名冊清單與啟動門禁

出貨 NPC 的角色卡與台詞由切片管理，不散落在零星腳本：

1. **設定檔切片與引用**：地點服務主人與常駐冒險者的角色卡定義在 `world/lore/npc_profiles/` 領域切片中（例如 `altoria_lower.py`、`ciaran_homes_a.py`），匯集於 `NPC_PROFILE_REGISTRY`。地點透過 `PlaceDefinition.host_profile_key` 引用；常駐冒險者透過 `GuildAdventurer.profile_key` 引用。公會位階不再擁有考官身分欄位。系統禁止孤立設定檔，登錄於註冊表中的設定檔必須至少被一處地點或常駐冒險者引用。
2. **語音台詞分配規則**：
   - **劇本主人**：地點對話表的首句問候語（`greeting`）為唯一來源，設定檔內的 `voice.greeting` 保持 `None`，消除問候語雙頭維護的風險；設定檔必須填寫 `voice.misunderstood`（理解失敗回覆語）。
   - **常駐冒險者**：平常就是會說話的持久 NPC，設定檔必須同時填寫 `voice.greeting` 與 `voice.misunderstood`；主持考核只是他們的附加資格，不另外建立考官設定檔。
   - **同行夥伴**：夥伴預設卡（`PlayerPreset`）直接提供 `speech_style` 與 `greeting`（離線問候語），夥伴實例化時將問候語寫入執行個體專屬的 `db.npc_offline_greeting`。
3. **出貨名冊清單（Inventory）**：所有出貨來源（地點主人、對話表、常駐冒險者、同行夥伴、離線任務模板佔位者、匯入範例卡）必須登記在 `world/lore/npc_profiles/inventory.py` 的 `NPC_SOURCE_INVENTORY` 之中，並標記所屬內容切片。
4. **伺服器啟動驗證門禁**：伺服器開機程序包含 `npc_persona_roster_validation` 步驟，置於 `STARTUP_STEP_ORDER` 中 `state_reaction_rules` 之後、`sync_all` 之前。驗證函式 `validate_npc_roster()` 比對名冊雙向一致性、檢驗所有角色卡契約、確認每張對話表皆由單一服務主人應答，並檢查語音覆蓋完整度。任一處不合規範即觸發例外中止開機，阻止寫入不完整資料。

### Step 3.2 — 遊戲內編輯器與固定劇本不重產原則

作者在遊戲內可透過目標互動面板的「編輯人物設定」開啟編輯視窗，檢視或修改 NPC 執行期角色卡與離線問候語覆寫值：

1. **固定劇本不重產原則**：劇本對話（固定問候語、關鍵詞回應、服務說明）在創作時針對初始設定檔撰寫。在遊戲內編輯人物設定後，語言模型不會重新生成或改寫既有的劇本對話。關鍵詞回應與服務引導皆維持作者手寫原文；編輯器僅更新執行期精簡角色卡（供受護欄保護的生成對話使用）以及執行個體離線問候語覆寫欄位。
2. **權限與版本控制**：編輯器透過單一交易提交更新，寫入時檢查版本序號以防並發衝突。
3. **建造者旁路物件處理**：透過 Evennia 建造者指令建立的 NPC 因未經過正式初始化管線，未具備精簡卡，其編輯器入口會顯示停用狀態（`npc_persona.unavailable`）。

### Step 3.3 — 編輯審查紀錄與結構檢查

出貨 NPC 的人物設定、角色卡、語音與劇本台詞都是作者文字，好壞不是測試能斷言的事。因此這裡不用「預期台詞」的 fixture，專案改在 `docs/development/npc-editorial-review.md` 維護一份以實際來源為索引、帶日期的編輯審查帳本：伺服器實際推導出來的每一個來源（地點主人、對話表、常駐冒險者、同行夥伴、任務模板佔位者、匯入範例卡）都必須恰好有一筆紀錄，逐項寫下該來源實際擁有的面向，以及最後的處置。

檢查由純函式 `world/lore/npc_editorial_review.py` 執行，並由 `world/lore/tests/test_npc_editorial_review.py` 驅動：它把帳本與 `derive_shipped_sources()` 推導出來的真實來源集合雙向比對。缺少紀錄、殘留已退役來源的紀錄、日期格式錯誤、面向數量不符、面向空白或處置空白，都會具名報錯。這份帳本只證明覆蓋，不判斷文字品質，也不保證審查在之後的內容改動後仍然新鮮。

實務規則：

- 新增或改寫任何一個出貨 NPC 來源時，在同一次變更內補上或更新它那一筆紀錄；只改帳本裡的散文敘述不會影響任何檢查。
- 關鍵詞標籤的檢查只在一張表內生效：同表的標籤不得重複，但兩個主人可以合法共用同一組標籤，專案不再要求全域唯一的關鍵詞組。
- 測試不釘死任何一句問候語、關鍵詞回應、角色卡或語音文字，改寫既有台詞不會讓測試失敗。
- `LEDGER_FACES_BY_KIND`（`world/lore/npc_editorial_review.py`）是每個來源種類應審查面向的唯一宣告；某個種類多了新的文字面向時，連同那份宣告一起擴充。

### Step 3.4 — 生成場景包對話（夢境協作）

夢境協作產生的可交談角色不走 YAML，也不寫入任何來源目錄。它的不可變定義存放在 `world/quests` 的 `ScenePackage` 資料列中，由 `world/quests/encounters.py::publish_scene_package` 先驗證整包再寫入；`world/rules/dialogue_sources.py` 的共享提供者只讀取已發表且未取消的套件。角色不需要 `NpcProfile` 或靜態對話註冊。

**區域識別碼與命名空間。** 作者在階段內宣告 `topic_id`、`scene_id`、`variant_id` 與 `predecessors`，一律使用 `[a-z][a-z0-9_]{0,31}`。`world/lore/dialogue/codec.py` 會把它們與 `GeneratedDialogueIdentity(package_id, role_id, phase_id)` 組成穩定完整 ID：`g:` 加上 UTF-8 JSON 陣列的無補位 URL-safe base64（`[package_id, role_id, phase_id, local_id]`）。完整 ID 是 ASCII、上限 2048 位元組；靜態對話的 96 字元小寫規則不適用。`role_id` 與 `phase_id` 各上限 64 個字元，可以含非 ASCII 字元。同一階段內識別碼不得重複，前置只能指向同階段已宣告的話題，且不得成環；跨階段的前置會被視為懸空而拒收。

**效果關聯。** 階段可宣告選填的 `topic_effects`，每列恰好 `{topic_id, verb, reference}`。`verb` 目前只有 `offer_commission`；`reference` 必須等於該角色在本套件宣告的委託定義鍵。帶效果的話題必須同時宣告 `requires` 與 `refusal`，且不得是 `disclosure: "pure_chain"` 的公開接續。資格成立後仍可能在結算前被持有、地點、委託授權或既有委託狀態拒絕；拒絕時只播放 `refusal` 場景，不交付正式內容、不建立完成憑證、不給好感。效果與對話工作階段在同一個交易內提交，重播或重複選取最多套用一次。靜態 YAML 不支援 `topic_effects`。

**內容身分與舊格式。** 套件識別碼是把提案 JSON（含區域對話 ID）排序序列化後的雜湊，因此對話文字或宣告不同就是不同套件，不可能覆寫已發表的不可變內容。舊的 `response`、`effect_verb`、`effect_reference` 欄位已停用；只含舊格式的既有資料列在執行期解析不到來源，提供者回傳 `None` 並留下一筆 `dialogue_source_rejected` 邊界事件，不會轉換或部分交付。

**場景提示的輸入上限。** 夢境場景走專用的 `scenario_director.scene_system` 提示與 `ExtendedQuestBlueprint` 內嵌結構；使用者訊息保留完整規劃框，包含 `dialogue_references` 許可目錄。此路由的輸入上限是 65,536 UTF-8 位元組（`world/ai/scenario_director/blueprints.py::MAX_SCENE_CONTEXT_SIZE`），通用 `QuestBlueprint` 路由仍維持 12,000。以現行註冊表量測，完整標籤目錄的緊湊 JSON 為 16,109 位元組（profile 28、preset 8、daypart 4、race 3、social_identity 4、guild_rank 7、quest 10、item 123、skill 260、affinity_stage 7），其餘留給需求、來源摘要與指示。對話本身的位元組上限不變：單一場景 8,192、交付加公開接續 16,384、面板 24,576、帶對話的封包 98,304。

### Step 4 — 匯入

在受控的內容載入程式中呼叫：

```python
from pathlib import Path

from world.imports.loader import load_batch

npcs = load_batch([Path("content/characters/old_pike.json")])
```

`load_batch` 先整批驗證、在單一資料庫交易內建立全部角色，任一失敗整批回滾（連血脈自動播種的熟練度也不留）。兩條安全前提：

- **NPC 名稱唯一性只有 lookup-then-create 斷言，資料庫層沒有對應限制。** 可能共用 NPC key 空間的並發匯入必須在函式外串行（單一內容載入寫入者，一次一批）。
- 不要繞過驗證直接用 `create_object()` 建 NPC。

### Step 5 — 擺放

載入器**不負責位置**，交易提交後 NPC 沒有 location，由內容載入程式自行 `move_to` 指定房間（place-bound 元件的 `anchor_room` 記的是錨點事實，不會把人物搬過去）。啟動同步建的服務主人則由同步放進錨定房間內部，這是兩條路徑的又一處差異。

### Step 6 — 排程（需要時）

```python
from world.rules.npc_schedules import set_npc_schedule

set_npc_schedule(npc, {"schema_version": 1, "template": "resident"})
```

唯二合法儲存形狀是模板引用（`{"schema_version": 1, "template": <key>, "overrides": {...}}`，overrides 以條目索引字串為鍵）與完整自訂條目列表；狀態值只能取自頂層 `states` 詞彙，移動條目的 `target` 由執行期經 lore 登錄表解析。模板鍵未知→`ScheduleTemplateError`，任何形狀錯誤在寫入狀態前以具名 `ScheduleError` 子類別拒絕。

### Step 7 — 補測試與驗證

#### Daily and weekly schedule authoring

Templates in `npc_schedules.yaml` and full custom schedules accept optional
`cycle_days`, an integer equal to `1` or `7`, with `1` as the default. Boolean
values are rejected. Template references inherit the template cycle and cannot
declare `cycle_days`; entry overrides cannot change it either. Schema version
remains `1`.

Offsets must satisfy `0 <= tick_offset < cycle_days * configured_day_seconds`.
Cycles start at absolute world tick zero, including across seasons and years.
Assignment records the current effective tick without restarting the cycle;
reload preserves that tick. An occurrence exactly at assignment settles on the
next window, while earlier occurrences are excluded.

```python
set_npc_schedule(npc, {
    "schema_version": 1,
    "cycle_days": 7,
    "entries": [
        {"tick_offset": 172800, "kind": "state", "state": "busy"},
        {"tick_offset": 176400, "kind": "state", "state": "duty"},
    ],
})
```

`ParsedSchedule.cycle_seconds` derives the duration from clock configuration.
`due_occurrences(parsed, start_tick, end_tick)` is the shared pure arithmetic
API, returning occurrences ordered by absolute due tick and entry index.
Settlement additionally orders by persistent NPC identity and retains real Exit
traversal, failure isolation, and companion service silencing. It does not charge
the clock.

#### Planned service window reader

`world.rules.service_windows.read_next_planned_service_interval(npc, destination, current_tick=None)`
exposes read-only projection of planned NPC attendance intervals. Given a persistent
NPC and destination room (or anchor key), it returns a `PlannedServiceWindowResult`
carrying either `PlannedServiceInterval(start_tick, end_tick)` or a named unavailable
reason (e.g. `invalid_host`, `missing_world_clock`, `schedule_silenced`, `active_exam_hold`,
`missing_schedule`, `indeterminate_schedule`, `unconfirmable`).

Intervals are start-inclusive and end-exclusive `[start_tick, end_tick)`. The reader
never mutates clock, NPC attributes, locations, or examination records.

#### Examination schedule holds

`world.rules.exam_schedule_holds` owns the runtime APIs
`begin_exam_schedule_hold(npc, exam_id, start_tick)`,
`read_exam_schedule_hold(npc)` and
`release_exam_schedule_hold(npc, exam_id, through_tick)`. These APIs are complete
independently of examination activation. `start_guild_exam` begins the hold
inside its start transaction, a coherent cold-start recovery keeps it, and every
terminal or invalid-recovery settlement releases it through
`restore_exam_host` after the host's normal state is restored.

Mutation APIs require serialized calls from the deterministic game loop.
Worker/web threads must route requests through that boundary; these APIs do not
provide concurrent host locking. An active marker cannot carry a consumed cursor,
because release commits cursor and released status together.

Begin requires the current persisted world tick and a persistent NPC. The caller
allocates globally unique exam IDs; the single retained record remembers only the
latest completed identity. An identical active begin is idempotent. A different
active owner or reuse of the retained completed ID rejects without mutation.
`npc.db.exam_schedule_hold` stores schema version 1, host primary key, exam ID,
start tick, held-through tick, consumed-through `(due_tick, entry_index)` or
`None`, and a released flag. Do not author or directly edit this runtime record.

The registered schedule source checks service silencing first. An active hold
defers host movement and state while extending the held interval; unrelated NPC
ordering remains unchanged. An indeterminate hold protects the host without
routine writes. A read returns `known=False` with a named `exam_hold_*` reason
for corrupt or unreadable records, and known absence has `hold=None`.

Restore the normal host state before release. Release must cover the held
interval without exceeding the persisted world tick. It derives occurrences
from the authoritative schedule and traverses real Exits in due/index order
without advancing time. Locks, movement vetoes and per-entry skips remain in
force. Silenced release consumes the interval without movement/state changes.
Corrupt schedule storage rejects release and retains the pending hold. A retained
released record makes retries and the same-tick assignment boundary idempotent.

Release rolls back its storage, location and handler caches on failure.
An enclosing lifecycle transaction must call
`snapshot_exam_schedule_hold_surfaces(npc)` before any host writes and
`restore_exam_schedule_hold_surfaces(npc, snapshot)` after its own database
rollback. The clock source includes the hold marker in its existing surface
registry. Hold start/extension/release events are emitted on the outer commit.

依順序跑最小聚焦集：

```sh
MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb \
  world.imports.tests.test_loader_trait_values \
  world.imports.tests.test_batch_all_or_nothing \
  world.imports.tests.test_capability_imports \
  world.rules.tests.test_dialogue
uv run --locked python -m tools.spec_traceability check
```

出貨卡目錄契約測試若因新增出貨內容而釘值失敗，屬於**有意識更新**目錄契約，並非繞過障礙。

---

## 4. 載入期驗證器總表

| 檢查 | 觸發於 | 何時爆 |
|---|---|---|
| `CHARACTER_SCHEMA_V1` 結構（必填欄、`additionalProperties: False`、`age`/`apparent_age` 0–10000、`stats` 封閉欄位） | CLI 驗證／`load_batch` 驗證階段 | 整批具名拒收 |
| 已移除的 `title` 欄位（結構為 `additionalProperties: False`） | 結構驗證 | 整批拒收；不做任何轉換 |
| NPC 目標的 `persona` 精簡角色卡契約（`normalize_card`；`PlayerCharacter` 目標不檢查） | 語意驗證＋構造前第二道 fail-closed 閘 | 整批具名拒收（`persona.<欄位>`＋原因碼）；構造前攔下不留半成品 |
| 批次內重名 | CLI／驗證階段 | 整批拒收 |
| 與資料庫既有 NPC 重名 | `load_batch`／`instantiate_character` 載入時（`_flag_existing_npc_names`） | 整批拒收，reason=`existing_npc_name` |
| 未知 race／subrace／技能／物品、`magic_power` 超種族魔力帶、偽裝鍵非 `stats` 子集、無神性種族帶非空偽裝層 | 語意驗證 | 拒收（計量條超出合理帶僅警告） |
| 未知能力型別、重複型別、未知或執行期 kwargs、`components` 落在 `PlayerCharacter` | 語意驗證（`npc_capabilities`） | 整批具名拒收 |
| 元件缺作者身份 kwargs | 驗證＋載入雙閘（`ProfessionAssemblyError`） | `component <type> is missing authored identity kwargs <fields>` |
| `anchor_room` 無房間／多房間／非 Room | 載入（交易內解析） | `ValueError` 點名記錄與 tag |
| `dialogue_key` 未登錄（服務主人路徑） | `validate_service_hosts`（啟動載入） | `GuildConfigError` 點名地點與鍵 |
| 兩列名冊共用一個 `host_profile_key`（canonical 身分重複） | `validate_service_hosts`（啟動載入） | `GuildConfigError` 點名重複的 host_key |
| `ServiceHostRow.host_key` 空白或不等於 `profile_key` | `ServiceHostRow` 建構（`__post_init__`） | `GuildConfigError` |
| 兩個活體 NPC 宣稱同一 canonical 身分，或該身分屬於常駐冒險者 | `sync_service_content` 身分預檢（任何寫入之前） | `ServiceHostIntegrityError`，整批不寫 |
| 出貨名冊不一致、卡片損壞、問候語漂移、孤立設定檔 | `npc_persona_roster_validation`（伺服器啟動門禁，`sync_all` 之前） | `NpcRosterError` 具名列出所有違規項目並中止啟動 |
| 排程形狀／模板／狀態詞彙 | `set_npc_schedule`→`resolve_schedule` | 具名 `ScheduleError` 子類別，寫入前拒絕 |

---

## 5. 常見錯誤

| 錯誤 | 後果 |
|---|---|
| 用匯入卡建永久服務主人（店主、公會主管） | 匯入卡建的主人不帶 `content_source`／`service_host` 標籤，同步永不接管也不會刪除它，於是世上多了一個同名卻不受名冊管轄的人；永久主人只能宣告在 `places.py` |
| `key` 寫英文卻期待人物列顯示中文名 | 載入器用 `key` 建物件，`display_name` 不參與顯示；顯示名就是 `key` |
| 匯入卡仍帶著已移除的 `title` 欄位 | 結構驗證以未知欄位拒收；把角色定位寫進 `persona` 與描述即可 |
| place-bound 元件卻漏寫或寫錯 `anchor_room` | tag 解析不到唯一房間→整批拒收；person-bound（`quest_issuer`）反過來帶 anchor 也被拒 |
| merchant 職業不寫 `dialogue_key` | 藍圖覆蓋檢查具名拒收。無問候語的店主是 `merchant-dialogue` 移除的缺陷，永不作為預設 |
| 自創能力型別或綁定種類 | 兩者都是閉合詞彙；新能力屬規格驅動變更，見 §6 |
| 並發跑兩個 `load_batch` 共用 NPC key 空間 | 名稱唯一性是 lookup-then-create，普通交易不串行 missing-row 檢查，後果是雙建；內容載入必須單一寫入者串行 |
| 沿用舊的 `persona` 形狀（單行 `identity` 字串、`background` 欄、缺 `speech_style`） | NPC 匯入整批拒收，點名 `persona.<欄位>`；照參考範例卡寫滿七欄 |
| 為過測試而捏造卡上登錄鍵 | 未知鍵由驗證器具名拒收；測試該用受控合成資料（`world/tests/synthetic_data`），勿修改出貨卡 |
| 拿 `NPC` 型別期待 LLM 生成對話 | 生成管線掛在 `LLMNPC.at_talked_to`；`NPC` 只有劇本對話。匯入生成人物要顯式 `typeclass=LLMNPC` |
| 直接寫 `npc.db.schedule` | 唯一寫入者是 `set_npc_schedule`（它同時記生效 tick 與 `schedule` tag）；旁路寫入的排程沒有生效事實 |
| 以為 place 綁定的 `anchor_room` 會把人物搬進房間 | 錨點只是元件持久的事實；位置由載入程式 `move_to` 決定 |
| 以為同步會把離開錨定房間的主人搬回去 | 重用永不搬遷；place-bound 服務依錨點與位置判定為暫停，位置由移動／生命週期擁有者決定 |
| 手動把非受管元件掛到受管主人身上 | 六個能力詞彙以外的元件永不觸碰；六個詞彙內的元件則受名冊收斂，宣告裡沒有就會被移除 |

---

## 6. 什麼時候已超出這篇指南的範圍

### Persistent guild adventurers

`world/lore/guild_adventurers.py` owns normal person identities and separate
branch/rank qualifications. `world/rules/human_guild_hosts.py` validates and
assembles these people as `LLMNPC` instances. A person row carries no
capability declaration and assembly attaches none: occupation and
examination authority stay with the independent qualification table, never
with a capability component on the adventurer. Qualification selection
requires one exact branch/target binding and one persistent person dbref. It
never selects by display key or summons an absent person. Qualification alone
never attaches an examination-reception capability to the adventurer. Rank
rows carry no examiner identity and no temporary opponent factory exists;
examinations always fight the qualified persistent person.

Each normal person has a distinct profile, bounded canonical ages, both offline
voice replies, literal bases, registered military equipment, and complete sword
branches plus utility ownership. The shared lineage initializer supplies the
prerequisite ownership and minimal usable proficiency. Literal coastal inputs
are never adjusted a second time. Creation records `guild_adventurer_person_key`
and the official profile provenance; an occupied display key receives the new
object's primary-key suffix once. Repeated sync preserves location, persona,
equipment, schedule and active examination state without repair writes.

The three hostless `HOME` places are `altoria_hok_home`,
`altoria_cassandra_home` and `altoria_augustine_home`, all with distinct doors at
the existing `(4,3,capital_altoria)` guild frontage. Maps materialize reciprocal
Exits. The route is home → frontage → guild and the reciprocal return. Assembly
resolves the stable place/grid identities to `#<room-id>` template overrides;
room display names never become persisted schedule targets.

The schedule templates in `npc_schedules.yaml` own all visit times. Hok arrives
daily at 08:00 and 18:00, leaves at 12:00 and 20:00. Cassandra visits weekly day
index 1 from 10:00 to 16:00 (`122400..144000`); Augustine visits day index 4
(`381600..403200`). The home-to-frontage hop occurs 30 ticks before each arrival;
returning home occurs 30 ticks after guild departure. Weekly indices are anchored
at absolute tick zero. All three enter `duty` at 06:00 and `resting` at 22:00;
weekly templates repeat both entries on every day. Successful moves set `duty`.
Actual Exit locks still determine whether the person arrives.

#### Persistent examination lifecycle

`world.rules.guild_exams.start_guild_exam(actor, examiner, target_rank)` is the
only mutation-capable start. `examiner` is the qualified persistent person.
Command, WebClient (`guild.exam_request`) and NPC-intent adapters never call it
directly: they go through the presence-first coordinator
`world.rules.guild_exam_request.request_guild_exam(actor, target_rank, speaker=None,
requested_by=...)`. It resolves the target with
`resolve_exam_request_target`, which derives the branch from the single
co-located `GuildExamReception` counter (or the speaking counter), refuses a busy
counter (`schedule_blocked`), and selects the person from the qualification
binding. A speaking NPC that is neither the counter nor the qualified person
grants no authority. If the person is not standing in the counter's room, the
coordinator answers `exam_schedule` from
`world.rules.service_windows.read_next_planned_service_interval` (or rejects
`attendance_unknown` with the reader's named reason) without any merit check
or write; only a present host reaches `start_guild_exam`. Author each host's
schedule so its service-capable guild visit is a real Exit traversal into the
counter's room: that window is exactly what the counter quotes to players.

Before any write the start checks registration, the counter's shared service
gate and branch, host co-location, exact next rank, qualification, host
`service_guild` schedule state (`examiner_busy`), a `participant_name_collision` between candidate
and host keys, any engagement of the host in another exam or battle, canonical
host ages, true merit, and a real kit preflight. Then one transaction persists
`guild_exam_normal_state` (exam ID, start tick, normal equipment/inventory and
effects), issues and wears the target's military pair with an empty accessory
loadout, activates the restriction (which adds the guild limit accessory),
begins the schedule hold, fills both applicable pools, writes the exam record
and combat session, and grants the existing +1 guild affinity. Any failure
restores storage and caches through `snapshot_exam_host_surfaces` /
`restore_exam_host_surfaces`; the host is never created, renamed or deleted.

Every terminal outcome (pass, fail, flee, forfeit, round cap, invalid recovery)
calls `restore_exam_host(host, exam_id)` inside the settlement transaction: it
removes only this exam's restriction, restores the persisted normal outfit and
effects, refills full normal pools, and releases this exam's hold. Foreign or
unreadable restriction/hold state is left untouched with a warning. Cold-start
recovery resumes only when the exam record, session, restriction, normal-state
record and active hold all name the same exam and host and the participant keys
stay distinct; otherwise it settles FAIL once and restores the host.

The `persistent_adventurer` source inventory records one owner/profile/age pair
per person. Roster preflight validates source equality, orphan references and
both offline reply paths independently of the existing scripted-table rules.

加一張內容卡（新旅店老闆、新委託人、新劇情人物）照上面的流程做即可。以下超出「加資料」範圍：

- **永久服務主人**：改 `world/lore/settlements/places.py` 的地點宣告（`host_*`＋`components` 直接能力宣告），商店商品與時段見[新增物品指南](/development/adding-items) Step 4。
- **新能力型別、新能力綁定**：能力詞彙是閉合的，擴充會波及 `typeclasses/components.py`、`world/rules/npc_capabilities.py` 與對稱測試，請走 OpenSpec 流程（`openspec-propose`）。
- **新角色階級（`NPCTier`）或新場景人物原型**：任務場景人物的數值由 `race_key`＋`static_tier_key` 從 lore 表推導，新階級是 lore＋規格變更。
- **新對話關鍵詞行為**（與 `回報` 同類、會解析規則狀態的關鍵詞）：屬於規則行為，超出表格資料的範圍。
- **玩家角色**：見[新增角色模板指南](/development/adding-player-presets)。
