# npc-title-import-pipeline — Design

## Context

已核准設計 `docs/superpowers/specs/2026-09-03-npc-identity-titles-design.md` 是唯一事實來源；本文件只解釋 §5（作者供給面的 import 兩列）＋§6（import 錯誤處理）＋§7（import 測試）落地時的技術取捨，不重述設計已定案的決策，也不擴張其範圍。

現況（本 change 動工前）：

- `CHARACTER_SCHEMA_V1`（`world/imports/schema.py`）必填 17 欄，`key` 的字元集／長度規則從 `world/art/subjects.py` 的共用常量推導出 `ENTITY_KEY_PATTERN_V1`；schema 自身的 `"title": "CHARACTER_SCHEMA_V1"` 是 JSON Schema 的**文件標題關鍵字**，與本 change 要新增的 `properties.title` 分屬不同層級，不衝突但容易誤讀。
- `world/imports/validate.py` 分兩階段：結構階段（jsonschema ＋ digit-only 保留區）→ 有 rejection 就 early return → 語意階段（lineage 正規化、key 契約、race/subrace、stats band、affinity、skills）。整個模組**零 DB 存取**，離線 CLI `uv run --locked -m world.imports.validate <files>` 因此是純檔案檢查，`test_reference_example.py` 也用純 `unittest.TestCase`。
- `_flag_duplicate_keys` 已做**批次內** character／world-entry key 重複檢查（`fix-import-key-validity` D2），對既有 DB 則完全不查。
- `world/imports/loader.py` 在一個 `transaction.atomic()` 內逐筆 `create_object(typeclass, key=record["key"])`，全批任一筆失敗即整批回滾；`display_name` 欄位**被驗證但從未被 loader 使用**，NPC 的姓名事實上就是 `key`。
- loader／validate 兩檔目前**一行 log 都沒有**，也未匯入 `world.observability`；`tools/observability_freeze.json` 是空清單（遷移已完成，全 repo 受管）。
- `NPC` 與 `LLMNPC` 同住 `typeclasses/npcs.py`（`LLMNPC(NPC)`）；`Monster` 繼承 `LivingEntity`，不是 NPC。
- 前置 change `npc-title-identity-core` 交付 `world/rules/npc_identity.py`：`validate_npc_title`（strip → 1..32 code points → 拒空白／控制字元／`|`，回傳 strip 後字串）、`npc_title_value`、`npc_display_name`，以及 `NPC.npc_title` 的 `AttributeProperty`。該模組 module scope 只有 stdlib，無 typeclass、無 Evennia、無 logger 匯入。

## Goals / Non-Goals

**Goals:**

- 讓 JSON 匯入成為第一條把 `npc_title` 寫進資料庫的路徑，且沿用既有 all-or-nothing 語義：任一筆的稱號違規＝整批零實體落庫。
- 把設計 §3.2 不變式 2（姓名全世界唯一）在匯入面補完：批次內（既有）＋對既有 NPC（新增）。
- 稱號取值規則只有一個實作：`validate_npc_title`。schema 只承載型別與上界常量，不複製字元集 regex。
- 讓匯入的提交／拒絕在 log 裡留下可重建的時間線（AGENTS.md「正常路徑留痕」）。
- 保持離線 CLI 為零 DB 依賴的純檔案檢查。

**Non-Goals:**

- blueprint `npc_req`、`SHOP_REGISTRY`／`GUILD_RANK_REGISTRY`、`guild_economy`／`guild_exams` 生成路徑與其 boundary event（change 3）。
- 核心組合器、typeclass 屬性宣告、顯示路由（change 1，本 change 只消費）。
- SceneBuilder 具名佔用者同步：那是 runtime 生成面，設計 §3.2 明文沿用既有冪等語義（同名即同一人），不是作者供給面，本 change 不碰。
- NPC 姓名的產生方式（namegen 系列 change）：本 change 只規定姓名進 DB 前必須唯一。
- 讓 `display_name` 變成 NPC 的顯示姓名（見 D7）。
- 任何相容層、`schema_version` 2、資料遷移（未發布、零使用者）。

## Decisions

### D1. `title` 的規則分工：schema 管型別與上界常量，字元集規則由驗證器獨佔

```python
from world.rules.npc_identity import MAX_NPC_TITLE_CODE_POINTS
...
"title": {
    "type": "string",
    "minLength": 1,
    "description": (
        "REQUIRED single-line plain-text NPC title (南門守衛, 雜貨店老闆). The "
        "full rule set -- stripped 1-32 code points, no whitespace (including "
        "U+3000), no control characters, no '|' -- is enforced semantically by "
        "world.rules.npc_identity.validate_npc_title, the single validator "
        "every NPC-title write path shares."
    ),
},
```

`title` 進 `required` 列（依既有欄位順序插在 `display_name` 之後）。

理由：`key` 的 pattern 之所以在 schema 複製一份，是因為它要在結構階段就擋掉會污染 `|` 分隔序列化的字元；`title` 沒有這個急迫性，而稱號的完整規則（含 strip 後上界）是 change 1 明文宣告的「單一驗證器」不變式——在 schema 再寫任何一份規則（regex 或 `maxLength`）等於製造第二個真相。特別地，`maxLength` 檢查**未 strip 的原字串**而驗證器檢查 strip 後的形，兩者對 `" " * 40 + "衛"` 這類值會給出相反決定（schema 拒、驗證器正規化為 `"衛"` 收）——老實講這是規則分歧，不是「都是拒絕就好」：驗證器收的值被結構層擋掉，就違反「驗證器是唯一規則」契約。因此 schema 只宣告 `type`／`minLength`／`required` 與一段描述規則的英文 `description`（上界數字寫在 description 文字裡供讀者參照，不作關鍵字執行），長度與字元集一律交語意階段的 `validate_npc_title`。

替代方案：(a) schema 保留 `maxLength` 以維持「schema 自身可讀」——已被否決（rubber-duck 複審 findings）：可讀性由 description 承擔，關鍵字只留與驗證器無歧義的 `type`/`minLength`。(b) 在 schema 複製字元集 pattern——同違反單一驗證器不變式。

驗證等價契約：任何 `validate_npc_title` 接受的線格式值，結構階段必須放行；被拒的值必須產出指名 `title` 的 record-level `Issue`（無論拒絕來自哪個階段）。測試直接以驗證器的正規化語義為準。

若 `npc-title-identity-core` 落地時把上界寫成模組私有名（`_MAX_...`），本 change 在同一批把它改為公開常量，**不**在 `schema.py` 複寫 32。

### D2. 語意檢查 `_check_npc_title` 掛在語意階段，例外轉 `Issue`

```python
def _check_npc_title(record: dict[str, Any]) -> list[Issue]:
    title = record.get("title")
    if not isinstance(title, str):
        return []          # 結構階段已擋；沿用既有檢查的 guard 風格
    try:
        validate_npc_title(title)
    except ValueError as error:
        return [Issue("title", str(error))]
    return []
```

掛在 `validate_character` 語意階段（`_check_entity_key_contract` 之後）。缺欄／非字串／空字串／超長由結構階段擋並 early return；字元集違規由此條指名 `title` 拒。

理由：完全對齊既有的兩階段慣例——結構管形狀、語意管跨系統規則；`validate_npc_title` 的訊息本身就是穩定英文 identifier（change 1 規格要求），直接 `str(error)` 進 `Issue.message` 即滿足 `import-validation`「每個 issue 指名 record／欄位／理由」。

`except ValueError` 是「捕捉後轉診斷」而非吞掉：這是 R2 的第三種形態嗎？不是——R2 只約束**已匯入 facade 的檔案**，而 `validate.py` 依 D8 刻意不匯入 facade。即使未來它匯入了，本區塊也不是無痕吞掉（診斷回傳給呼叫端並導致整批拒絕），屆時補 `# observability: ignore R2:` 註解即可。

替代方案：讓 `validate_npc_title` 回傳 `(ok, message)` 而非 raise——被否決：change 1 的 requirement 已定死它「失敗即 raise」，改簽名等於改前置 change 的契約。

### D3. loader 寫入用驗證器回傳值，且只對 `NPC` 執行個體寫

```python
if isinstance(entity, NPC):
    # ``npc_title`` is declared as an AttributeProperty on ``NPC`` only;
    # assigning it on a PlayerCharacter would create a plain instance
    # attribute that never survives a reload (silent data loss).
    entity.npc_title = validate_npc_title(record["title"])
```

兩個決定：

1. **寫驗證器的回傳值**而不是 `record["title"]`：回傳的是 strip 後的正規形，且這是建立點的 fail-closed 第二道（設計 §3.2 不變式 1「任一生產路徑缺欄即拒絕建立」）。`load_batch` 已先驗證，所以這條在正常流程恆不觸發；一旦有人繞過驗證直接呼叫 `_instantiate_validated_character`，它會 raise 並讓外層交易回滾，而不是把髒值落庫。驗證器是純函式且冪等，「照驗證過的內容建構」的既有原則不受影響。
2. **只對 `NPC` 執行個體寫**：loader 的 `typeclass` 參數容許 `PlayerCharacter`（`import-loader` 既有 requirement）。稱號欄位在 `PlayerCharacter` 上沒有 `AttributeProperty` 描述子，賦值只會落在 Python 執行個體上、重載即消失。與其靜默遺失，不如明文不寫——設計 §3.2 不變式 4 本來就規定玩家在任何顯示路徑退化為純姓名。角色卡仍必填 `title`（schema 沒有、也無法有「目標型別」這個判別依據；`typeclass` 是 loader 的呼叫參數，不是記錄內容），玩家角色卡的 `title` 是惰性欄位，並以測試釘住「匯入 `PlayerCharacter` 後不存在 `npc_title` 屬性」。

替代方案：對非 NPC 改寫 `entity.db.npc_title`——被否決：那會在玩家身上種一個 change 1 宣告「只有 NPC 有」的屬性，且無任何讀取者。

### D4. 對既有 NPC 的重名檢查放 `loader.py`，不放 `validate.py`

`load_batch` 在 `transaction.atomic()` 內、建立任何實體之前執行；命中即把 `Issue("key", ...)` 追加到對應的 `RecordReport`，然後 `raise ImportRejected(report)`。`instantiate_character`（單筆公開入口）套用同一個檢查。

理由：

- **CLI 純度**：`validate.py` 目前零 DB 存取，離線 CLI 是純檔案 linter，`test_reference_example.py` 用純 `unittest.TestCase`（無交易包覆）。把 DB 查詢塞進 `validate_batch` 會讓 CLI 需要可用資料庫、讓純邏輯測試開始碰 DB，違反 `docs/development/evennia-testing-guide.md` 的 fixture 選擇原則。
- **語義正確性**：檔案靜態檢查根本無法回答「這個名字現在有沒有人用」；只有在交易內查詢才有意義（TOCTOU）。
- **診斷同形**：rejection 掛在既有 `RecordReport.rejections` 上，`ImportRejected.report` 與 `render_report` 的形狀完全不變，呼叫端無須認識新的例外或新的報告型別。

因此形成一條明確的責任線，並寫進 `docs/gm/characters.md`：**CLI 驗證檔案本身與批次內的一致性；與資料庫既有 NPC 的重名由 `load_batch()` 在載入時整批把關。**

替代方案：(a) 在 `validate_batch` 加一個 `DegradedCheck`（「DB 重名檢查未執行」）——被否決：`DegradedCheck` 的語義是「這個檢查本該跑但跑不了」（例如 skill registry 缺席），而 CLI 的檔案作用域是**定義好的邊界**不是降級，每次執行都印一條 banner 只會讓真正的降級訊號失去意義。(b) 讓 `validate_batch` 收一個可選的 `existing_names` 參數由 loader 注入——被否決：把 DB 語義倒灌進純函式模組，還多一個只有一個呼叫端的參數。

### D5. 「既有 NPC」的查詢用 `filter_family`，並以子類別測試釘住

```python
existing = set(
    NPC.objects.filter_family(db_key__in=sorted(keys)).values_list("db_key", flat=True)
)
```

理由：Evennia 的 `TypeclassManager.filter` 會**強制加上 `db_typeclass_path=<本類路徑>`**（`evennia/typeclasses/managers.py`），所以 `NPC.objects.filter(db_key=...)` 精確比對 typeclass path，會**漏掉 `LLMNPC`**——而 LLMNPC 正是最可能與匯入 NPC 撞名的那一種。`filter_family` 才是「本類＋所有子類別」的正確 API。

`filter_family` 以 `cls.__subclasses__()` 展開，只看得到**已被匯入**的子類別。目前 `NPC` 的唯一子類別 `LLMNPC` 與 `NPC` 同住 `typeclasses/npcs.py`，而 loader 在 module scope 就 `from typeclasses.npcs import NPC`，所以家族恆完整。這個保證是「同檔宣告」帶來的，不是巧合可依賴的——因此加一條迴歸測試：建立一隻同名 `LLMNPC`，匯入必須被拒。未來若有人把 NPC 子類別搬到別的模組而未匯入，這條測試會紅。

比較對象：`evennia.search_object(key, exact=True)` 也會回傳 typeclass 執行個體，但它同時比對 aliases，會把「別名撞名」也變成拒絕理由——那是本 change 未定義、也不該偷渡的語義。

### D6. 碰撞語義：fail closed，不重用、不改名、不覆寫

匯入記錄的 `key` 等於某隻既有 NPC（含子類別）的 `key` → 該筆 record 得到一條指名 `key` 的 rejection，整批拒絕、零實體落庫。**不**重用既有實體、**不**自動改名、**不**覆寫既有 NPC 的任何欄位。

不在此規則內（明文不拒）：撞上既有 `PlayerCharacter`、`Monster`、房間或物件的 key。設計 §3.2 的不變式是「NPC 姓名全世界唯一」，把它擴張成「跨所有實體型別唯一」會在沒有設計授權的情況下改變既有匯入行為。

與 runtime 面的對照（設計 §3.2 明文）：SceneBuilder 具名佔用者與 guild host／examiner 走的是**冪等重用**（同名即同一人）；作者面走的是**fail closed**。兩者不矛盾——差別在於作者面的重名是內容錯誤（兩張角色卡搶同一個名字），runtime 面的同名是同一個世界固定角色的再次同步。

批次目標型別是 `PlayerCharacter` 時同樣套用此 gate：世界上不會有兩個實體回應同一個 NPC 姓名，無論新來的那個是什麼型別。

### D7. 匯入面的「姓名」就是 `key`；`display_name` 維持惰性（設計文字校正）

設計 §3.2／§5 說的「姓名」，在匯入面對應的是 `record["key"]`：loader 以 `create_object(typeclass, key=record["key"])` 建立實體，`NPC.get_display_name` 回的是 `self.name`（即 `key`），設計 §4.2 的界內核算也寫「姓名 ≤64 code points（既有角色名上界）」——正是 `MAX_ENTITY_KEY_LENGTH`。因此唯一性檢查與全名組合的姓名側都以 `key` 為準。

`display_name` 是 `CHARACTER_SCHEMA_V1` 必填但 loader 從不讀取的欄位（`docs/gm/characters.md` 已明文記載這個現況）。本 change **不**把它接成顯示姓名：那會改動 `key` 契約以外的第二個身分欄位、影響 portrait stable key 與搜尋目標，屬於設計未授權的範圍擴張。作者要讓 NPC 在房間列顯示「塞提斯　南門守衛」，就把 `key` 寫成 `塞提斯`（既有 key 字元集完全允許中文）。這一點寫進 GM 文件的欄位表。

### D8. 觀測性：兩個邊界事件只加在 `loader.py`，`validate.py` 不採用 facade

```python
from world.observability import log_info, log_warn
...
log_warn("import_batch_rejected", context={"records": ..., "rejected": ..., "reason": "validation" | "existing_npc_name"})
log_info("import_batch_committed", context={"records": ..., "typeclass": typeclass.__name__})
```

理由：設計 §8 寫「import loader 已有 `action_commit` 類語義不變」，但實際上 `world/imports/loader.py` 目前完全沒有 log。匯入提交是不折不扣的持久狀態邊界（AGENTS.md：新增或修改任何持久狀態變更必須依目錄留 info 事件；觀測性設計 §4.2），而本 change 正在修改這條路徑並新增一個拒絕理由——不補等於讓「整批被拒、一個實體都沒建」這件事在 log 裡完全不可見。這是設計相對於現況的**缺口補正**，不是範圍擴張。

`validate.py` 刻意**不**匯入 facade：它有兩個把例外轉成 `Issue` 的 `except` 區塊，一旦成為 adopter 就進入 R2 作用域，得為兩個與本 change 無關的區塊補豁免註解——那是不相干的債務，留給下一個真正動到那些區塊的 change。

`context` 只放批次層級的計數與理由碼，不放稱號字串或玩家文案（event 與 context 皆英文；facade 對序列值會截斷）。

## Risks / Trade-offs

- **既有測試因必填 `title` 轉紅** → 匯入套件的角色卡固定走 `world/imports/tests/helpers.py::example_record()`（讀參考 JSON），補了範例檔就自動綠；其他套件（`world/quests`、`world/skills`、`world/rules`）呼叫 `instantiate_character` 的測試同樣走該 helper。實作第一步仍以全 repo 搜尋 `"record_type"` 字面量確認沒有手寫角色卡遺漏，並在 tasks 列為明確步驟。
- **`filter_family` 只看已匯入的子類別** → D5 的 `LLMNPC` 重名迴歸測試釘住；子類別與 `NPC` 同檔宣告使家族恆完整。
- **交易內多一次 DB 查詢** → 一次 `db_key__in` 查詢，key 集合等於批次大小（角色卡批次是個位數到數十）；相較每筆 `create_object` 的多次寫入可忽略。
- **`PlayerCharacter` 角色卡必填卻不落庫的稱號** → D3 明文＋測試釘住；GM 文件在欄位表註記「此欄只對 NPC 生效」。
- **CLI 與 `load_batch` 檢查面不同** → 刻意的責任線（D4），寫進 GM 文件的驗證章節；`load_batch` 內部仍會先跑完整 `validate_batch`，所以 CLI 通過的檔案在載入時只可能多出「與既有 NPC 重名」這一種新拒絕理由。
- **與 change 3 的 delta 檔相鄰** → 兩者都往 `specs/npc-identity-titles/spec.md` 追加 `## ADDED Requirements` 區塊，但各自在自己的 change 目錄下，主規格 sync 時才合併；requirement 標題不重疊（本 change 一律以「匯入／import」開頭）。
- **`title` 這個名字在 schema 檔裡有兩個意思** → `CHARACTER_SCHEMA_V1["title"]` 是 JSON Schema 的文件標題關鍵字，`properties.title` 才是角色卡欄位；在 property 的 description 首句寫明「REQUIRED ... NPC title」，並在測試中同時斷言兩者，避免日後誤刪。
- **觀測性 lint** → `loader.py` 成為 adopter；該檔無 `except` 區塊，R2 零影響，R3 由兩處呼叫都帶 `context` 滿足。測試若要斷言事件，依 AGENTS.md patch **呼叫端模組**的綁定（`world.imports.loader.log_info`），不 patch `world.observability.*`。

## Migration Plan

無資料遷移、無相容層（未發布、零使用者）。落地順序：schema ＋ 語意檢查 → 參考角色卡與文件（讓既有測試回綠）→ loader 落庫與重名 gate → 事件與測試 → 主規格 sync 與 `covers_requirement`。回退方式是整批 revert：本 change 不寫任何無法由重新匯入重建的狀態。

倉庫內唯一的角色卡是 `world/imports/examples/example_character.json`（設計 §5 寫的是 `examples/*.json`，實際只有這一個檔）；倉庫外的內容資料夾由 GM 依更新後的 `docs/gm/characters.md` 補 `title` 欄位，未補者在 CLI 與 `load_batch` 兩處都會以指名 `title` 的 rejection 立即失敗——fail closed，不會靜默匯入無稱號 NPC。

## Open Questions

無阻斷性問題。以下為刻意記錄的既有偏差，本 change **不**處理（不在設計授權範圍內，留給後續觸及該區的 change）：

- `openspec/specs/import-validation` 仍有「`subrace` 為選填、缺 subrace 不因此拒」的 scenario，而現況程式碼（`_check_race_subrace`）與 schema 都已把 `subrace` 列為必填並硬拒。這是既有主規格與實作的漂移，與本 change 無因果關係。
- `docs/gm/characters.md` 開頭寫「`subrace` 可省略」，同上。本 change 只在該檔補 `title` 相關內容，不順手改寫其他欄位敘述，以免混淆 review 範圍。
