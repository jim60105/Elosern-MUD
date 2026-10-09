# 新增 NPC 指南

本指南說明如何為 Elosern 加入一個新的 NPC。同一個「非玩家活體」有四條進入世界的路徑，各自負責不同內容。JSON 匯入卡負責一次性內容人物，地點登錄表負責永久服務主人，任務場景具現化負責關卡人物，預設卡負責同行夥伴。本文走一遍選路、寫卡、裝配能力元件、接上劇本對話、排程、驗證的完整流程。

本文假設你已讀過：

- `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`（世界資料與確定性核心的邊界）
- [角色建立與匯入](/gm/characters)（JSON 卡欄位語意的現行契約）
- `world/imports/schema.py::CHARACTER_SCHEMA_V1`（結構驗證的唯一來源）
- `world/rules/rulebook/professions.yaml`（職業藍圖的閉合詞彙）

---

## 1. 背景：NPC 有四條建立路徑，語意各不相同

先選對路徑。四條路徑建的實體都是 `typeclasses/npcs.py` 的 `NPC` 家族，但它們的身份來源、數值來源、擺放者都不同，拿錯路徑的規則套另一條路徑是這類工作最常見的錯誤。

| 路徑 | 建立者 | 用途 | 型別 |
|---|---|---|---|
| JSON 匯入（本文） | `world/imports/loader.py::load_batch`／`instantiate_character` | 一次性內容人物（旅人、僱傭兵、劇情人物） | `NPC`（預設型別） |
| 地點登錄表服務主人 | `world/lore/settlements/places.py` 的 `host_*` 欄位，由 `world/rules/guild_economy.py::sync_service_content` 於啟動冪等建立 | 永久服務主人（店主、公會主管、店主兼對話、管事） | `NPC`（啟動同步建立，永不手動匯入） |
| 任務場景具現化 | `world/quests/scene_builder.py` 依 `world/lore/npc_tiers.py::NPC_TIER_REGISTRY` 的角色階級生成 | 任務階段場景人物 | `scene_npc` 原型（白名單限定） |
| 同行夥伴 | `world/rules/starting_companions.py::build_starting_companion` | 預設卡 `starting_companions` 宣告的夥伴 | `LLMNPC`（`invite` 只收 `LLMNPC`） |

四條正式路徑在建立時皆會初始化完整的精簡角色卡（Compact Card），寫入版本 1 的人物設定與來源中繼資料。若透過 Evennia 建造者指令（`create` 或 `spawn`）建立 `NPC`，則會繞過所有初始化程式；這類非出貨來源物件未持有角色卡，在遊戲內的人物設定編輯器入口會顯示停用狀態（`npc_persona.unavailable`）。

依據設計文件 `docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §13c 條款（KISS 原則），未使用的離線人物設定套件（Offline Persona Bundles）子系統已完整移除，不維護離線套件選擇器或相容別名；若未來有經正式核准之重啟需求，可由 Git 歷史紀錄復原。現行所有生產環境 NPC 皆透過上述四條完整卡片路徑建立。

對話行為是另一個正交的決定：

| 對話形態 | 條件 | 降級行為 |
|---|---|---|
| 劇本對話（`talk` 關鍵詞查表） | NPC 帶 `ScriptedDialogue` 元件，`dialogue_key` 指向 `world/lore/dialogue/` 已登錄的表 | 未知關鍵詞回覆無理解行；查得到的表永遠可用，完全離線可玩 |
| 生成對話（guarded LLM） | 型別是 `LLMNPC`；`at_talked_to` 走 `world/ai/npc_dialogue.py` 護欄管線 | 護欄降級時改說 `resolve_greeting(npc)` 的離線問候語（執行個體欄位優先，次為劇本／Profile）或沉默 |

匯入器預設建 `NPC`（純劇本對話／無對話）。生成對話人物必須顯式傳 `typeclass=LLMNPC`。

---

## 2. 事前決定：寫卡之前要回答的五個問題

1. **這是永久服務主人嗎？** 是 → 走地點登錄表：在 `world/lore/settlements/places.py` 的 `PlaceDefinition` 宣告 `host_name`／`host_title`／`host_race`／`host_subrace`／`host_sex`／`profession`／服務 kwargs，啟動 `sync_service_content` 依登錄表推導名冊、find-or-create 主人並組裝元件。**不要**用匯入卡建永久主人。名冊收斂（`_converge_service_hosts`）以元件 `service_id` 為準，名冊沒授權的主人會被同步刪除。
2. **需要什麼能力？** 能力＝職業藍圖的元件組，`professions.yaml` 是目前的全部五列：

   | 職業列 | 元件組 | 綁定 | 用途 |
   |---|---|---|---|
   | `merchant` | `merchant` + `scripted_dialogue` | place | 會交易也會說話的店主；`dialogue_key` **必須**手寫，無問候語的店主屬作者錯誤 |
   | `guild_staff` | `guild_staff` + `guild_examiner` + `scripted_dialogue` | place | 公會主管（註冊＋考核＋回報） |
   | `guild_examiner` | `guild_examiner` + `scripted_dialogue` | place | 純考核官 |
   | `quest_issuer` | `quest_issuer` | person | 私人委託發包人；身分隨人走，**不得**釘房 |
   | `attendant` | `scripted_dialogue` | place | 對話即服務的管事（旅店老闆、衛兵隊長、教官）；職業在 `host_title` 與對話表裡，不另設列 |

3. **需要劇本對話嗎？** `dialogue_key` 必須是 `world/lore/dialogue/`（`altoria_{lower,middle,upper}.py`／`ciaran.py`／`guild.py` 依領域分檔）`DIALOGUE_ROWS` 已登錄的鍵；新對話要先加表列，見 Step 3。
4. **需要日程嗎？** 排程詞彙住在 `world/rules/rulebook/npc_schedules.yaml`：狀態詞彙 `duty`／`resting`／`busy`，模板 `guard`／`storekeeper`／`resident`。匯入卡的職業藍圖只在列帶 `schedule_template` 時自動套排程（現行出貨列全為 `null`），其餘情況由程式呼叫 `world/rules/npc_schedules.py::set_npc_schedule`（`db.schedule` 的唯一寫入者）。
5. **數值來源在哪？** 設計文件與既有 rulebook。`stats` 是匯入卡路徑的字面基準值（永不預先乘技能倍率）；平衡數值由設計文件決定，卡作者不發明平衡表。
6. **這是出貨的服務主人、考核官或同行夥伴嗎？** 服務主人與考核官必須在 `world/lore/npc_profiles/` 所屬切片登錄 `NpcProfile`，並在地點或公會位階填入引用鍵；同行夥伴則在夥伴預設卡填寫延伸欄位。所有出貨來源都必須登記於名冊清單，見 §3.1。

---

## 3. Step by Step

### Step 0 — 核對登錄鍵

卡上點名的每個鍵都必須已登錄：`race`／`subrace`（`world/lore/races.py`）、`skills`／`passives`（`world/skills/registry.py`）、`inventory` 的物品鍵（`ITEM_REGISTRY`）、`profession`（`professions.yaml`）、`dialogue_key`（`DIALOGUE_ROWS`）、`host_profile_key`（`NPC_PROFILE_REGISTRY`）。CLI 驗證器全部比對，未知鍵直接拒收。

### Step 1 — 寫 JSON 角色卡

複製 `world/imports/examples/example_character.json`，欄位語意見[角色建立與匯入](/gm/characters)。NPC 特有的五條規則：

- **`key` 就是遊戲內顯示名。** 載入器以 `key` 建立 Evennia 物件，`display_name` 目前不被使用；要讓人物列顯示中文姓名，`key` 就寫中文。房間人物列與探索面板把 `key` 與 `title` 以全形空格組成「姓名　稱號」。
- **`title` 對 NPC 必填**，規則是 `world/rules/npc_identity.validate_npc_title` 的單一 validator 契約：去首尾空白後 1–32 碼點、無任何空白（含 U+3000）、無控制字元、無 `|`。落庫的是驗證器回傳的正規形（已去空白）。
- **`age`／`apparent_age` 各自獨立**，0–10000 整數（拒絕布林值）。常駐 host 與考官由 `NpcProfile` 作者宣告明確定案數值（`age` 與 `apparent_age` 必填），落庫與同步時優先使用 profile 定義的年齡；未指定 profile 或無作者年齡的路徑由 `ensure_npc_canonical_age` 獨立補 `NPC_DEFAULT_AGE`（18）。既有欄位值永不覆寫，重用與重啟時保留玩家編輯的 persona 與既有年齡。既有開發世界若需完整套用作者年齡，請依照 reset runbook 重設資料庫。
- **`persona` 必須是完整的精簡 NPC 角色卡**：恰好 `identity{public,hidden}`、`appearance`、`personality`、`speech_style`、`life_story`、`habit`、`social_connection` 七欄，全為純文字（`identity.hidden` 與 `social_connection` 可空，其餘必填）；沒有 `background`。契約由 `world/lore/npc_card.py::normalize_card` 唯一執行（單欄 600、身分段 600、整卡 2000 碼點；身分段與整卡都以渲染後的區塊計算，含「性格：」等標籤與換行，而非僅欄位文字）。判斷依據是傳給 `validate_character`／載入器的目標型別（`issubclass(typeclass, NPC)`，預設即 NPC），絕不看記錄內容；`PlayerCharacter` 目標的 `persona` 仍不透明、原樣落庫。落庫走 `world/rules/npc_persona.py::initialize_npc_persona`，寫入正規化後的卡與版本 1 中繼資料（來源 `{"kind": "import", "record": <key>}`），與整批同一筆交易。
- **`disguised_stats` 非空時種族必須能用神之秘法**，同[新增角色模板指南](/development/adding-player-presets) §4 的不變式；`_check_disguised_stats_subset` 另要求偽裝鍵是 `stats` 子集。

服務 NPC 再加選填的職業三欄：

```json
{
  "key": "old_pike",
  "display_name": "老柏克",
  "title": "渡口管事",
  "age": 57,
  "apparent_age": 54,
  "race": "human",
  "subrace": "human_plains",
  "sex": "male",
  "stats": {"hp": 90, "mp": 20, "sp": 60},
  "profession": "attendant",
  "components": [
    { "type": "scripted_dialogue", "kwargs": { "dialogue_key": "ferry_attendant" } }
  ],
  "anchor_room": "riverside_ford",
  "...": "其餘必填欄見範例卡"
}
```

組裝語意（`world/imports/loader.py::_apply_profession`）：

- `components` 只能與 `profession` 併用；同型條目**完全取代**藍圖條目（kwargs 只取記錄值），藍圖未列的詞彙型別可按記錄順序附加。
- 身分辨識一律手寫，匯入器絕不憑空補值：`shop_key`（Merchant）、`branch_key`（GuildStaff/GuildExaminer）、`dialogue_key`（ScriptedDialogue）、`issuer_key`（QuestIssuer，缺席時解析為 `npc:#<pk>`）。解析後仍缺身份的規畫整批具名拒收。
- `anchor_room` 是錨定房間的 **room tag**，恰好等於「規畫含 place-bound 元件」時必填、含 person-bound 元件時 forbidden。載入器在同一筆交易內解析：tag 解析不到房間、或解析到多個房間、或 tag 落在非 Room 物件上，都整批拒收並點名記錄與 tag。
- 職業列的 `default_tier` 只在 `stats` 為空時作為特質基準；卡宣告任何字面數值時職業不影響特質。

### Step 2 — 驗證

```sh
uv run --locked -m world.imports.validate content/characters/old_pike.json
```

CLI 只檢查檔案本身與批次內一致性（含批次內重名）；**與資料庫既有 NPC 的重名由載入器把關**，CLI 不回報。批次全綠才進入載入。CLI 以 NPC 為目標，角色卡違規以 `persona.<欄位>` 加穩定原因碼（`missing_field`、`unknown_field`、`not_text`、`required_empty`、`leaf_too_long`、`identity_section_too_long`、`card_too_long`）回報；契約遇到第一個違規就停，一次只會看到一個角色卡問題。

### Step 3 — 劇本對話（需要時）

對話是作者身份，表列住在 lore 封裝 `world/lore/dialogue/` 的領域分檔（`altoria_{lower,middle,upper}.py`、`ciaran.py`、`guild.py`），由 `__init__.py` 組出不可變 `DIALOGUE_ROWS`。新增一表：

```python
# world/lore/dialogue/<domain>.py（領域名為範例；實際放進對應領域分檔）
ROWS = {
    "ferry_attendant": DialogueDefinition(
        greeting="老柏克靠在船篙旁：「要過河？講聲『過河』就知道價。」",
        responses=(
            KeywordResponse("過河", "「十銅板，綁好你的馬。」"),
            KeywordResponse("渡口", "「上游鬧匪，船現在只走下游。」"),
        ),
    ),
}
```

規則端 `world/rules/dialogue.py` 只是唯讀介面，`DIALOGUE_TABLE` 是唯讀包裝，`talk` 查不到鍵就回覆無理解行。`guild_staff` 表的 `回報` 關鍵詞是唯一例外，它經 `world/rules/guild.py` 解析可回報任務清單，屬規則行為，不要在自製表裡模仿。

### Step 3.1 — 人物設定切片、名冊清單與啟動門禁

出貨 NPC 的角色卡與台詞由切片管理，不散落在零星腳本：

1. **設定檔切片與引用**：地點服務主人與考核官的角色卡定義在 `world/lore/npc_profiles/` 領域切片中（例如 `altoria_lower.py`、`ciaran_homes_a.py`），匯集於 `NPC_PROFILE_REGISTRY`。地點透過 `PlaceDefinition.host_profile_key` 引用；公會位階透過 `GuildRank.examiner_profile_key` 引用。系統禁止孤立設定檔，登錄於註冊表中的設定檔必須至少被一處地點或考核官引用。
2. **語音台詞分配規則**：
   - **劇本主人**：地點對話表的首句問候語（`greeting`）為唯一來源，設定檔內的 `voice.greeting` 保持 `None`，消除問候語雙頭維護的風險；設定檔必須填寫 `voice.misunderstood`（理解失敗回覆語）。
   - **考核官**：純戰鬥考核對象不具備對話能力，其設定檔內的 `voice.greeting` 與 `voice.misunderstood` 皆設定為 `None`。
   - **同行夥伴**：夥伴預設卡（`PlayerPreset`）直接提供 `speech_style` 與 `greeting`（離線問候語），夥伴實例化時將問候語寫入執行個體專屬的 `db.npc_offline_greeting`。
3. **出貨名冊清單（Inventory）**：所有出貨來源（地點主人、對話表、公會考核官、同行夥伴、離線任務模板佔位者、匯入範例卡）必須登記在 `world/lore/npc_profiles/inventory.py` 的 `NPC_SOURCE_INVENTORY` 之中，並標記所屬內容切片。
4. **伺服器啟動驗證門禁**：伺服器開機程序包含 `npc_persona_roster_validation` 步驟，置於 `STARTUP_STEP_ORDER` 中 `state_reaction_rules` 之後、`sync_all` 之前。驗證函式 `validate_npc_roster()` 比對名冊雙向一致性、檢驗所有角色卡契約、確認每張對話表皆由單一服務主人應答，並檢查語音覆蓋完整度。任一處不合規範即觸發例外中止開機，阻止寫入不完整資料。

### Step 3.2 — 遊戲內編輯器與固定劇本不重產原則

作者在遊戲內可透過目標互動面板的「編輯人物設定」開啟編輯視窗，檢視或修改 NPC 執行期角色卡與離線問候語覆寫值：

1. **固定劇本不重產原則**：劇本對話（固定問候語、關鍵詞回應、服務說明）在創作時針對初始設定檔撰寫。在遊戲內編輯人物設定後，語言模型不會重新生成或改寫既有的劇本對話。關鍵詞回應與服務引導皆維持作者手寫原文；編輯器僅更新執行期精簡角色卡（供受護欄保護的生成對話使用）以及執行個體離線問候語覆寫欄位。
2. **權限與版本控制**：編輯器透過單一交易提交更新，寫入時檢查版本序號以防並發衝突。
3. **建造者旁路物件處理**：透過 Evennia 建造者指令建立的 NPC 因未經過正式初始化管線，未具備精簡卡，其編輯器入口會顯示停用狀態（`npc_persona.unavailable`）。

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

#### Examination schedule holds

`world.rules.exam_schedule_holds` owns the runtime APIs
`begin_exam_schedule_hold(npc, exam_id, start_tick)`,
`read_exam_schedule_hold(npc)` and
`release_exam_schedule_hold(npc, exam_id, through_tick)`. These APIs are complete
independently of production examination activation. The persistent lifecycle
change owns that activation and the availability-reader change owns query use.

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
  world.imports.tests.test_profession_assembly_loader \
  world.rules.tests.test_dialogue
uv run --locked python -m tools.spec_traceability check
```

出貨卡目錄契約測試若因新增出貨內容而釘值失敗，屬於**有意識更新**目錄契約，並非繞過障礙。

---

## 4. 載入期驗證器總表

| 檢查 | 觸發於 | 何時爆 |
|---|---|---|
| `CHARACTER_SCHEMA_V1` 結構（必填欄、`additionalProperties: False`、`age`/`apparent_age` 0–10000、`stats` 封閉欄位） | CLI 驗證／`load_batch` 驗證階段 | 整批具名拒收 |
| `title` 語意規則（單一 validator `validate_npc_title`） | 語意驗證＋構造前第二道 fail-closed 閘 | 拒收；構造前攔下不留半成品 |
| NPC 目標的 `persona` 精簡角色卡契約（`normalize_card`；`PlayerCharacter` 目標不檢查） | 語意驗證＋構造前第二道 fail-closed 閘 | 整批具名拒收（`persona.<欄位>`＋原因碼）；構造前攔下不留半成品 |
| 批次內重名 | CLI／驗證階段 | 整批拒收 |
| 與資料庫既有 NPC 重名 | `load_batch`／`instantiate_character` 載入時（`_flag_existing_npc_names`） | 整批拒收，reason=`existing_npc_name` |
| 未知 race／subrace／技能／物品、`magic_power` 超種族魔力帶、偽裝鍵非 `stats` 子集、無神性種族帶非空偽裝層 | 語意驗證 | 拒收（計量條超出合理帶僅警告） |
| 未知 `profession`、`profession` 落在 `PlayerCharacter`、`components` 脫離 `profession` | 語意驗證 | 整批具名拒收 |
| 元件缺作者身份 kwargs | 驗證＋載入雙閘（`ProfessionAssemblyError`） | `component <type> is missing authored identity kwargs <fields>` |
| `anchor_room` 無房間／多房間／非 Room | 載入（交易內解析） | `ValueError` 點名記錄與 tag |
| `dialogue_key` 未登錄（服務主人路徑） | `validate_service_hosts`（啟動載入） | `GuildConfigError` 點名地點與鍵 |
| 出貨名冊不一致、卡片損壞、問候語漂移、孤立設定檔 | `npc_persona_roster_validation`（伺服器啟動門禁，`sync_all` 之前） | `NpcRosterError` 具名列出所有違規項目並中止啟動 |
| 排程形狀／模板／狀態詞彙 | `set_npc_schedule`→`resolve_schedule` | 具名 `ScheduleError` 子類別，寫入前拒絕 |

---

## 5. 常見錯誤

| 錯誤 | 後果 |
|---|---|
| 用匯入卡建永久服務主人（店主、公會主管） | 啟動收斂以名冊為準，名冊未授權的主人會被同步刪除；永久主人只能宣告在 `places.py` |
| `key` 寫英文卻期待人物列顯示中文名 | 載入器用 `key` 建物件，`display_name` 不參與顯示；顯示名就是 `key` |
| `title` 帶空白、全形空格、`|` 或超過 32 碼點 | 語意驗證拒收；U+3000 是「姓名　稱號」合成器的專用分隔符，永不允許出現在名字或稱號裡 |
| place-bound 元件卻漏寫或寫錯 `anchor_room` | tag 解析不到唯一房間→整批拒收；person-bound（`quest_issuer`）反過來帶 anchor 也被拒 |
| merchant 職業不寫 `dialogue_key` | 藍圖覆蓋檢查具名拒收。無問候語的店主是 `merchant-dialogue` 移除的缺陷，永不作為預設 |
| 自創 `profession` 或元件型別 | 職業與元件型別都是閉合詞彙；新元件組屬規格驅動變更，見 §6 |
| 並發跑兩個 `load_batch` 共用 NPC key 空間 | 名稱唯一性是 lookup-then-create，普通交易不串行 missing-row 檢查，後果是雙建；內容載入必須單一寫入者串行 |
| 沿用舊的 `persona` 形狀（單行 `identity` 字串、`background` 欄、缺 `speech_style`） | NPC 匯入整批拒收，點名 `persona.<欄位>`；照參考範例卡寫滿七欄 |
| 為過測試而捏造卡上登錄鍵 | 未知鍵由驗證器具名拒收；測試該用受控合成資料（`world/tests/synthetic_data`），勿修改出貨卡 |
| 拿 `NPC` 型別期待 LLM 生成對話 | 生成管線掛在 `LLMNPC.at_talked_to`；`NPC` 只有劇本對話。匯入生成人物要顯式 `typeclass=LLMNPC` |
| 直接寫 `npc.db.schedule` | 唯一寫入者是 `set_npc_schedule`（它同時記生效 tick 與 `schedule` tag）；旁路寫入的排程沒有生效事實 |
| 以為 `anchor_room` 會把人物搬進房間 | 錨點只是元件持久的事實；位置由載入程式 `move_to` 決定 |

---

## 6. 什麼時候已超出這篇指南的範圍

加一張內容卡（新旅店老闆、新委託人、新劇情人物）照上面的流程做即可。以下超出「加資料」範圍：

- **永久服務主人**：改 `world/lore/settlements/places.py` 的地點宣告（`host_*`＋`profession`＋服務 kwargs），商店商品與時段見[新增物品指南](/development/adding-items) Step 4。
- **新職業列、新元件型別、新元件綁定**：職業是組裝期元件組的閉合詞彙，擴充會波及 `professions.yaml`、`typeclasses/components.py`、`world/rules/profession_config.py` 與對稱測試，請走 OpenSpec 流程（`openspec-propose`）。
- **新角色階級（`NPCTier`）或新場景人物原型**：任務場景人物的數值由 `race_key`＋`static_tier_key` 從 lore 表推導，新階級是 lore＋規格變更。
- **新對話關鍵詞行為**（與 `回報` 同類、會解析規則狀態的關鍵詞）：屬於規則行為，超出表格資料的範圍。
- **玩家角色**：見[新增角色模板指南](/development/adding-player-presets)。
