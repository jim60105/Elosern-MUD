# npc-title-identity-core — Proposal

## Why

每隻 NPC 目前只有 `key` 一格姓名，房間人物列、`看 <目標>` 標題與 webclient 探索面板都只印「塞提斯」，玩家看不出他是南門守衛還是雜貨店老闆。已核准設計 `docs/superpowers/specs/2026-09-03-npc-identity-titles-design.md` §3／§4 為 NPC 補一格建立時賦予、之後不可變的純文字稱號，並以「姓名　稱號」（全形空格）呈現在三個指定表面。本 change 只做確定性核心與顯示路由——先把唯一組合點與 opt-in 顯示旗標立起來，作者供給面（import schema、blueprint、registry）由後續兩個 change 接上。

## What Changes

- 新增確定性核心模組 `world/rules/npc_identity.py`，內含三個純函式：
  - `validate_npc_title(value)`：型別 `str`、strip 後 1–32 code points、拒絕任何空白字元（含全形空格 U+3000）、控制字元與 Evennia markup 分隔符 `|`；違反即 raise。
  - `npc_title_value(entity)`：讀 `db.npc_title`，非 NPC／缺值／型別不符一律回 `""`。
  - `npc_display_name(entity)`：有稱號回「姓名　稱號」，無稱號或非 NPC 回純 `key`；**永不 raise**（面板不因一格稱號欄損壞而整塊 unavailable）。全形空格常量由本模組自持，不從 `world/rules/titles.py` 匯入（玩家稱號系統零改動、零耦合）。
- `typeclasses/npcs.py::NPC` 新增 `npc_title: str = AttributeProperty(default="")`。本 change 不新增任何寫入點：無 setter、無命令、無 LLM 路徑，並以結構性缺席測試鎖住（仿 title-system 的 fixed-title 無刪除面測試）。
- `NPC.get_display_name` 接受 opt-in `full_identity=True` kwarg；只有兩個文字表面帶旗標——`ObjectParent.get_display_characters`（房間人物列）與 NPC 的 `看 <目標>` 標題（`return_appearance` 的 name slot）。所有其他呼叫者（移動／說話／給予 echo、`FOLLOW_LOST_MESSAGE`、戰鬥）不帶旗標，輸出 byte-identical 純姓名。
- webclient 探索面板 `web/webclient/presentation/exploration.py` 的 `_look_entities` 與 `_interact_targets` 對 character 類實體改走 `npc_display_name`；exits／rooms／objects 路徑與共用的 `_bounded_display_name` 語義不動，128 code points 上界不動（姓名 ≤64 ＋ 全形空格 1 ＋ 稱號 ≤32 = ≤97）。
- 明確不動的緊湊列，並補上斷言測試釘死為純姓名：戰鬥面板 participants（`world/rules/combat_view.py`）、頭像目錄（`world/rules/art_view.py`）、公會／商店 host 列（`world/rules/service_view.py`）。
- `LLMNPC._npc_context()` 新增唯讀 `title` 欄位，讓交談中的 NPC 知道自己是「南門守衛」。
- 指令與搜尋目標解析維持只匹配純 `key`：玩家永遠不需要在 `交談`／`邀請`／`給` 裡打稱號。
- 無玩家命令新增／改名／改語法 → `docs/game/commands.md`、`docs/game/command-reference.md` 不動。無相容層、無資料遷移（未發布、零使用者）。

## Capabilities

### New Capabilities

- `npc-identity-titles`: NPC 單格稱號的資料模型與顯示契約——`validate_npc_title` 的取值規則、`npc_title` 的建立時寫入／runtime 不可變、`npc_display_name` 的「姓名　稱號」單一組合點與退化語義、`full_identity` opt-in 顯示路由（房間人物列／看標題／探索面板）、緊湊列與 echo 的純姓名保證、prompt 唯讀 `title` 欄位，以及指令目標只匹配 `key`。

  後續兩個 change（import schema `title` 欄位＋loader 落庫＋批次姓名唯一性；blueprint `npc_req` 與 `SHOP_REGISTRY`／`GUILD_RANK_REGISTRY` 作者供給）會**擴充同一個 capability**，把設計 §5／§6 的作者面 requirement 加進來。本 change 的 delta 只涵蓋核心與顯示。

### Modified Capabilities

（無。）`localized-appearance` 的房間框架 requirement 只約束 zh-tw 框架字串（「出口」「人物」標頭、無英文框架字），未約束人物列每格的取名來源；`webclient-exploration-menu` 只要求 entity／target 列帶「bounded display name」，同樣未指定其來源為 `key`。兩者原文皆不需修改，新行為由新 capability 自行宣告，並附「既有 spec 原文不動」的迴歸 scenario（先例：`npc-namegen-lore-registry` 對 `lore-startup-sync` 的處理）。

## Impact

- 新增：`world/rules/npc_identity.py`、`world/rules/tests/test_npc_identity.py`（新測試模組 → 同 change 內更新 `.github/evennia-shards.json`）。
- 修改：`typeclasses/npcs.py`（`npc_title` 屬性、`get_display_name` 旗標、`return_appearance` name slot、`_npc_context` 的 `title`）、`typeclasses/objects.py`（`get_display_characters` 帶旗標）、`web/webclient/presentation/exploration.py`（兩個實體序列化點）。
- 測試觸面：`typeclasses/tests/test_npcs.py`、`typeclasses/tests/test_appearance.py`、`typeclasses/tests/test_npc_dialogue.py`、`web/webclient/presentation/tests/test_exploration_panel.py`、`world/rules/tests/test_combat_view.py`、`world/rules/tests/test_art_view.py`、`world/rules/tests/test_service_view.py`（緊湊列純姓名釘樁）。
- 觀測性：顯示組合為純讀取、本 change 不新增任何持久化寫入或外部 I/O，因此不新增 `world.observability` 事件；設計 §8 的 guild host／examiner boundary event 隨作者供給 change 落地。
- 相鄰但**零交集**的進行中 change：`npc-namegen-lore-registry`／`namegen-npc-flow`／`npc-namegen-rules-roller` 引入 `world/lore/names.py` 與（未來的）`world/rules/namegen.py` 做 NPC 姓名生成。兩條線都會碰到 NPC 身分，但檔案不相交：本 change 不匯入、不依賴、不修改 namegen 模組，也不對「姓名從何而來」下任何規定——只規定拿到姓名之後如何與稱號組合、如何顯示。
- 依賴：本 change 是另外兩個 change（import schema、authored registries）的**前置**——它們寫入的 `npc_title` 與呼叫的 `validate_npc_title` 都由此定義。
