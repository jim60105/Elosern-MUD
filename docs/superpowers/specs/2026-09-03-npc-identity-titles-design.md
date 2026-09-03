# NPC 稱號身分設計（NPC Identity Titles Design）

日期：2026-09-03
狀態：已核准（待實作）

## 1. 問題陳述

每隻 NPC 目前只有一個姓名（`key`）。房間列表、探索面板、`看` 標題都只
顯示「塞提斯」，玩家無從一眼辨識其職業或異名。玩家的稱號系統
（`world/rules/titles.py`，稱號＋異名雙槽全銜）是專屬玩家的機制——NPC
不需要稱號清單、裝備槽或獲得途徑，只需要建立時一次賦予的一格純文字
稱號（職稱如「南門守衛」「雜貨店老闆」，或冒險者的異名）。

本設計為所有 NPC 新增這格稱號，並定義它在各個顯示表面的呈現規則。

## 2. 決策摘要

| 決策 | 選擇 | 理由 |
|---|---|---|
| 稱號儲存 | NPC 上的純文字屬性 `db.npc_title`（`AttributeProperty`），建立時寫入、之後不可變 | 使用者明確要求：無清單、無獲得途徑、純文字；與玩家 `title_collection`/`title_equipped` 零共用，玩家 title-system 完全不動 |
| 必要性 | 全部 NPC 必填，建立點 fail-closed | 使用者要求「所有 NPC 都要有稱號」；專案無正式用戶，無相容層成本 |
| 姓名唯一性 | NPC 姓名全世界唯一 | 使用者要求：不會發生全世界公會職員同名的狀態 |
| 作者供給 | 姓名＋稱號一律由作者供給（import 記錄、blueprint `npc_req`、lore registry 條目），不引入命名池 | 使用者選擇；避免自創取名算法與持久化已用名單的複雜度，符合 registry 為唯一事實來源的慣例 |
| 組合格式 | 「姓名　稱號」，全形空格分隔 | 與玩家全銜（`compose_title`）同一風格 |
| 顯示路由 | opt-in 顯示旗標：只有房間人物列表、`看` 標題、webclient 探索面板顯示全名；戰鬥面板、頭像目錄、商店 host 列等緊湊列維持純姓名 | 使用者要求緊湊列保持純姓名；全域覆寫 `get_display_name` 會污染移動/說話 echo 的過程文字，故排除 |
| 實作路線 | 確定性核心單一組合點 `world/rules/npc_identity.py`，各顯示產生器 opt-in 委派 | 組合規則只存在一處；未觸及的 surface 零改動 |

拒絕的替代方案：

- **方案 B（全名直接當 `key`）**：污染搜尋/指令目標（玩家必須打全名）、
  破壞 `key` 契約與 portrait stable-key 相關測試，且沒有獨立稱號欄位可供
  prompt/系統讀取。
- **方案 C（NPC 複用 `world/rules/titles.py` 的 collection/slot 機制）**：
  那套機器是為玩家提名、裝備、刪除流程造的；NPC 只需要一格不可變字串，
  複用是過度設計。
- **命名池＋確定性分配**（泛型 NPC 自動取名）：使用者選擇作者供給路線，
  不引入生成演算法、持久化已用名單與衝突重試。

## 3. 資料模型與不變式

### 3.1 `npc_title` 屬性

`NPC` typeclass 新增 `npc_title: str = AttributeProperty(default="")`。
寫入只發生在建立路徑（import loader、SceneBuilder 具名佔用者同步、guild
host／examiner 生成）；無任何 runtime 變更 API。

驗證規則（所有建立點共用的單一驗證器，住 `world/rules/npc_identity.py`）：

- 型別 `str`、strip 後非空；
- 長度 1–32 code points；
- 不得含任何空白字元（含全形空格，避免與全形分隔符混料）、控制字元、
  Evennia markup 分隔符 `|`。

### 3.2 不變式

1. **每隻 NPC 必有姓名＋稱號**：任一生產路徑缺任一欄位即拒絕建立
   （import 批次整批拒、blueprint 編譯拒、registry 載入拒）。
2. **姓名全世界唯一**：import 批次驗證（批次內重複＋對既有 DB NPC 查覆）、
   blueprint 編譯驗證、lore registry 載入驗證三個作者面都做重複檢查。
   runtime 生成沿用 SceneBuilder 既有具名佔用者的冪等同步語義（同名即
   同一人，不視為衝突）；guild host／examiner 走 registry 固定 key，天然
   冪等。
3. **稱號不可變**：無 setter、無命令、無 LLM 路徑可改（結構性缺席測試
   斷言，仿 title-system 的 fixed-title 無刪除面測試）。
4. 無稱號的實體（玩家、`Monster`）在任何顯示路徑退化為純姓名，永不渲染
   分隔符或佔位符。`Monster` 不是 NPC，不在本設計範圍。

## 4. 顯示路由

### 4.1 單一組合點

`world/rules/npc_identity.py`（`world/rules/`，確定性核心，唯一寫者邊界內）：

```python
def npc_title_value(entity) -> str: ...   # 讀 db.npc_title，非 NPC/缺值 → ""
def npc_display_name(entity) -> str: ...  # 「姓名　稱號」；無稱號 → 姓名
def validate_npc_title(value) -> str: ... # §3.1 規則，失敗 raise
```

全形空格「　」與 `world/rules/titles.py` 玩家合成規則同字元，但為規避
跨系統耦合而在本模組自持常數（單字元，非邏輯複製）。

### 4.2 全名表面（僅三個）

| 表面 | 落點 | 機制 |
|---|---|---|
| 文字房間人物列表 | `ObjectParent.get_display_characters` | 以 `full_identity=True` kwarg 呼叫 `char.get_display_name(looker, full_identity=True, **kwargs)`；`NPC.get_display_name` 僅在此旗標下委派 `npc_display_name`，其餘呼叫者（echo、`at_pre_move`/`at_post_move`、give/say 模板）不帶旗標→純姓名 |
| 文字 `看 <目標>` 標題 | look header 產生點（`at_look`/appearance 框架的 name slot） | 同上旗標 |
| Webclient 探索面板 | `web/webclient/presentation/exploration.py` 的 `_look_entities`、interact 目標列、`_look_entries` display slot | character 類實體（`ENTITY_KINDS` 的 `character`/`npc`）改用 `npc_display_name(obj)`；exits/rooms/objects 路徑不經此改動 |

邊界核算：姓名 ≤64 code points（既有角色名上界）、稱號 ≤32、全形空格 1
→ 全名 ≤97， exploration/panel 現有 128 code points 界內，所有 wire 驗證器
不動。

### 4.3 純姓名表面（明確不動）

- 戰鬥面板 participants 與文字 `戰鬥` 目標代號列（`world/rules/combat_view.py`
  讀 `entity.key`）；
- 頭像目錄（`world/rules/art_view.py`）；
- 公會/商店 host 列（`world/rules/service_view.py`）；
- `world/rules/party.py::FOLLOW_LOST_MESSAGE` 離隊跟丟通知；
- talk/invite 的「XX說：」echo、移動/說話 `{object}` 映射、拾取/丟棄 echo。

opt-in 旗標設計使 echo 路徑零污染：未帶旗標的 `get_display_name` 行為
byte-identical。

### 4.4 LLM prompt

`LLMNPC._npc_context()` 新增唯讀 `title` 欄位，讓交談中的 NPC 知道自己是
「南門守衛」。純讀取，不經任何寫者。

### 4.5 指令/搜尋目標

`talk`/`invite`/`leave`/`給` 等目標解析繼續只匹配 `key`（純姓名）。玩家
不需要在指令裡打稱號。

## 5. 作者供給面

| 供給面 | 改動 |
|---|---|
| `CHARACTER_SCHEMA_V1`（`world/imports/schema.py`） | 新增必填 `title`（套用 §3.1 規則；直接改 v1，無相容層） |
| `world/imports/loader.py::_instantiate_validated_character` | 驗證後寫 `entity.npc_title = record["title"]` |
| blueprint `npc_req`（`world/ai/director_templates.py` 的提案驗證、`world/quests` 編譯鏈） | `display_name` 由選填改必填、新增必填 `title`；模板任務走同一驗證 |
| `SHOP_REGISTRY` 條目 | 商店 host 補 authored `host_name` ＋ `host_title`；`world/rules/guild_economy.py` 建 host 時寫入（沿用既有 key 冪等重用邏輯：既存 host 不改名） |
| `GUILD_RANK_REGISTRY` | 各階級補 examiner `name` ＋ `title`；`world/rules/guild_exams.py::settle_exam_outcome` 的對手 NPC 改用 authored 姓名為 `key`＋寫入稱號（取代 `key=f"guild-examiner-{rank}"`） |
| `world/imports/examples/*.json` | 補 `title` 欄位 |

## 6. 錯誤處理

- Import：任一記錄缺 `title`/含非法 `title`/姓名重複 → 整批拒絕（既有
  all-or-nothing 語義），報告帶 record 級 named diagnostic。
- Blueprint：缺必填欄位 → 編譯前拒，理由為穩定 identifier；AI 提案同樣
  在驗證層被拒，Director 產出永不落庫半成品。
- Registry 載入：`SHOP_REGISTRY`/`GUILD_RANK_REGISTRY` 缺欄 → 載入 fail
  closed。
- 顯示：`npc_display_name` 對缺值/非 NPC 退化為純姓名，永不 raise（面板不因一格稱號欄缺損
  而整塊 unavailable）。

## 7. 測試

新主規格 capability `npc-identity-titles`，Requirement 配
`covers_requirement` 測試（`tools.spec_traceability` 流程）：

- schema：缺 `title` 拒、空/超長/含空白/含 `|` 拒、合法值 round-trip；
- loader：驗證記錄 → 實體 `npc_title` 落庫；批次內與對 DB 姓名重複各拒一批；
- 組合：「塞提斯　南門守衛」全形分隔；無稱號退化純姓名；稱號邊界 32；
- 顯示路由：房間人物列表含全名；移動/說話 echo 僅姓名；探索面板 entity
  列與 interact 列含全名；戰鬥面板 participants 與頭像目錄 view 斷言僅姓名；
- prompt：`_npc_context()["title"]` 為稱號；
- 結構性缺席：無任何 `npc_title` runtime setter/命令（仿 title-system
  無刪除面測試）；
- guild host/examiner：生成後帶 authored 姓名＋稱號、冪等重用不改名；
- blueprint：缺 `display_name`/`title` 拒、合法具名條目全流程通過。

玩家稱號系統（`title-system` spec）的測試與實作零改動。

## 8. 觀測性

依觀測性規範，新增邊界事件：import loader 已有 `action_commit` 類語義
不變；guild host 生成與 examiner 生成各補一個 `log_info` boundary event
（`context` 帶 `char`/`shop`/`rank`）。顯示組合為純讀取，不產 log。

## 9. 範圍外

- `Monster` 稱號（非 NPC）。
- 玩家稱號系統任何改動。
- NPC 稱號的 runtime 變更、多語言、顏色/markup。
- 命名池/自動取名（已明確拒絕）。

## 10. 提案拆解與實作批次順序（2026-09-03 提案落地）

設計以三個 OpenSpec change 交付（`openspec/changes/`），每件單人一個工作日內：

| # | Change | 範圍 | 主要落點 |
|---|---|---|---|
| 1 | `npc-title-identity-core` | 驗證器＋`NPC.npc_title`＋組合器＋opt-in 顯示路由（房間列／看標題／探索面板）＋緊湊列純姓名釘樁＋prompt `title` 欄位＋生產者清單迴歸案 | `world/rules/npc_identity.py`、`typeclasses/npcs.py`、`typeclasses/objects.py`、`web/webclient/presentation/exploration.py` |
| 2 | `npc-title-import-pipeline` | `CHARACTER_SCHEMA_V1` 必填 `title`、loader 落庫、姓名對既有 NPC 唯一 gate、範例卡＋GM 文件、匯入邊界事件 | `world/imports/`、`docs/gm/characters.md` |
| 3 | `npc-title-authored-identities` | blueprint `npc_req` 必填 `display_name`＋`title`（姓名成為 spawn `key`）、`SHOP_REGISTRY`／`GUILD_BRANCH_REGISTRY`／`GUILD_RANK_REGISTRY` 作者身分＋載入 fail-closed、guild host／考官生成、legacy host 一次性 cleanup、批次收尾的 main-spec 整合 sync | `world/quests/`、`world/ai/`、`world/lore/{shops,guild}.py`、`world/rules/{npc_identity,guild_economy,guild_exams}.py` |

**依賴與批次順序**：

- **Batch A**：change 1 先行——它定義 `validate_npc_title`、`NPC.npc_title`、組合器，並建立
  capability `npc-identity-titles`；2 與 3 都匯入它的產物。
- **Batch B**：changes 2 與 3 並行——檔案零交集（2 只動 `world/imports/`；3 對
  `npc_identity.py` 僅檔尾 append `validate_npc_name`）。
- **main-spec 整合**：`openspec/specs/npc-identity-titles/spec.md` 只有單一寫入者＝批次最後
  落地者（建議順序下為 change 3），單次依序 sync 三件 delta、一次取 canonical ID、統一掛
  `covers_requirement`；各 change 單獨歸檔時才自行 sync。
- 進行中的 namegen 系列 change（`npc-namegen-lore-registry` 等）與本三件檔案零交集、無契約
  相依。

**Rubber-duck 複審（一次、全部 artifacts 完成後）已折入**：(a) onboarding 南門守衛刻意豁免
（註定隨新手教學移除，見 change 3 design D7a）＋生產者清單迴歸案釘死清單；(b) import schema
移除 raw `maxLength`，驗證器為唯一長度真相；(c) blueprint 姓名唯一性收緊為整份 blueprint
無例外；(d) host 稱號 backfill 改為一次性 legacy cleanup（無 runtime 寫入後門）；(e) sync 時序
改為批次單一寫入者契約。
