# npc-title-identity-core — Design

## Context

已核准設計 `docs/superpowers/specs/2026-09-03-npc-identity-titles-design.md` 是本 change 的唯一事實來源；本文件只解釋 §3（資料模型）＋§4（顯示路由）落地時的技術取捨，不重述設計已定案的決策，也不擴張其範圍。

現況：

- `NPC`（`typeclasses/npcs.py`）繼承 `LivingEntity`，身分只有 `key`；`get_display_name` 未覆寫，直接用 Evennia 的 `DefaultObject.get_display_name`（回 `self.name`）。
- 文字房間人物列在 `ObjectParent.get_display_characters`（`typeclasses/objects.py`），對每位在場角色呼叫 `char.get_display_name(looker, **kwargs)`。
- `看 <目標>` 走 `caller.at_look(target)` → `target.return_appearance(looker)`；Evennia 的 `appearance_template` 的 `{name}` 槽由 `self.get_display_name(looker, **kwargs)` 填。webclient 的 `explore.look` 走同一個 appearance 框架，因此 `localized-appearance` 規格要求三個入口輸出相同。
- webclient 探索面板的實體列（`_look_entities`）與互動目標列（`_interact_targets`）用共用 helper `_bounded_display_name(obj)`（`web/webclient/presentation/affordances.py`，`str(obj.key)[:128]`）；房間、出口、物件列也共用同一個 helper。
- 緊湊列各自直接讀 `entity.key`：`world/rules/combat_view.py::_build_participants`、`world/rules/art_view.py::_entity_view`、`world/rules/service_view.py`（host 列 `str(host.pk)`／`str(host.key)`）。
- 玩家稱號合成在 `world/rules/titles.py::compose_title`，以私有 `_FULL_WIDTH_SPACE` 常量連接；那套 collection／slot 機制專屬玩家。

## Goals / Non-Goals

**Goals:**

- 讓 NPC 稱號的組合規則只存在一個地方（`world/rules/npc_identity.py`），任何顯示表面都只是委派。
- 讓「哪些表面顯示全名」成為呼叫端的明示決定（opt-in 旗標），而非被顯示層全域偷改。
- 未帶旗標的所有既有輸出保持 byte-identical——移動／說話／給予 echo、跟丟通知、戰鬥文字與面板一格都不能變。
- 為後續兩個 change 準備好唯一驗證器 `validate_npc_title` 與唯一讀取器 `npc_title_value`。

**Non-Goals:**

- 任何 `npc_title` 寫入點（import loader、blueprint、registry、SceneBuilder、guild host／examiner）——屬 change 2／3。
- 姓名唯一性驗證、批次拒絕語義、examples JSON 補欄——屬 change 2／3。
- `Monster` 稱號、玩家稱號系統、runtime 改稱號、多語言／顏色 markup（設計 §9 範圍外）。
- NPC 姓名的產生方式：`world/lore/names.py`／未來的 `world/rules/namegen.py`（進行中的 namegen 系列 change）與本 change 檔案不相交，本 change 不匯入、不依賴、不修改它們。

## Decisions

### D1. 組合點放 `world/rules/npc_identity.py`，全形空格常量自持

新模組住確定性核心，只含純函式、無狀態、無 I/O、無 log。全形空格以模組私有常量 `_FULL_WIDTH_SPACE = "　"` 自持，**不從** `world/rules/titles.py` 匯入。

理由：玩家稱號系統與 NPC 稱號在設計上零共用（設計 §2）；共用一個單字元常量會製造跨系統匯入邊，未來任一邊改格式都會誤傷另一邊。單字元不是可複製的邏輯。

替代方案：把 NPC 稱號塞進 `world/rules/titles.py`——被設計 §2「方案 C」明確否決（那套機器是為玩家提名／裝備／刪除造的）。

### D2. `npc_title_value` 用延遲 import 做顯式 NPC 判定

```python
def npc_title_value(entity) -> str:
    from typeclasses.npcs import NPC   # 函式內延遲匯入
    ...
```

理由：`world/rules/` 模組不得在 module scope 匯入 typeclass（Evennia 匯入順序＋循環風險）；同檔案慣例已存在（`world/rules/party.py::live_companion_ids` 就是函式內 `from typeclasses.npcs import NPC`）。

替代方案：鴨子型別（有 `npc_title` 屬性就當有稱號）——被否決：`Monster` 不是 NPC（設計 §3.2 不變式 4），若哪天有人在 Monster 上留了同名屬性，鴨子型別會靜默把它渲染出來。顯式 isinstance 讓「非 NPC → 純姓名」成為型別事實而非巧合。

### D3. `full_identity` 是 opt-in kwarg，且呼叫端以 **合併** 方式帶旗標

`NPC.get_display_name(self, looker=None, *, full_identity=False, **kwargs)`：旗標為假時原封不動 `super().get_display_name(looker, **kwargs)`（byte-identical），為真時回 `npc_display_name(self)`。

`ObjectParent.get_display_characters` 帶旗標時**必須合併而非直接加關鍵字**：

```python
char.get_display_name(looker, **{**kwargs, "full_identity": True})
```

理由：`return_appearance` 會把自己的 `**kwargs` 往下傳給每個 `get_display_*` helper（見 D4），若 `kwargs` 已含 `full_identity`，寫成 `get_display_name(looker, full_identity=True, **kwargs)` 會直接 `TypeError: got multiple values for keyword argument`。合併形式對兩種情形都安全。

替代方案：全域覆寫 `NPC.get_display_name` 一律回全名——被設計 §2 明確否決（會污染 echo／移動／說話的過程文字）。

### D4. 看標題走 `NPC.return_appearance` 的 kwargs 注入，而非新增 hook

```python
def return_appearance(self, looker, **kwargs):
    kwargs.setdefault("full_identity", True)
    return super().return_appearance(looker, **kwargs)
```

理由：Evennia 的 `{name}` 槽由 `return_appearance` 內部呼叫 `self.get_display_name(looker, **kwargs)` 填，外部無法只針對該槽注入；覆寫 `return_appearance` 是唯一不重寫整個 template 的注入點。`setdefault` 讓呼叫端仍可顯式關閉。

副作用核算：旗標會隨 `**kwargs` 流進同一次 appearance 的其他 helper（`get_display_desc`／`get_display_exits`／`get_display_characters`／`get_display_things`／`filter_visible`），它們的簽名都是 `**kwargs` 收尾、對未知鍵無反應；唯一真正消費它的是 `get_display_characters`——那是「看一隻 NPC 時，列出這隻 NPC 身上帶著的角色」的路徑，在遊戲裡幾乎恆空，且即使有內容，顯示全名也與房間人物列語義一致。

連帶效果（刻意）：文字 `看`、`at_look` seam 與 webclient `explore.look` 共用同一個 appearance 框架，因此三個入口同時取得全名標題——這正是 `localized-appearance`「三個入口輸出相同 appearance」不變式所要求的；若只改文字路徑反而會違反該規格。

### D5. webclient 只換實體列的取名來源，不動共用的 `_bounded_display_name`

在 `web/webclient/presentation/exploration.py` 新增模組私有 helper：

```python
def _bounded_entity_name(obj) -> str:
    return npc_display_name(obj)[:MAX_DISPLAY_NAME_CODE_POINTS]
```

只在 `_look_entities` 與 `_interact_targets` 兩處替換；`look.room`、`move` 列、`_look_objects`／`_look_entries` 續用既有 `_bounded_display_name`。

理由：`_bounded_display_name` 是房間／出口／物件共用的，改它會把稱號語義漏到與 NPC 無關的列。截斷語義（slice，不拋例外）刻意與既有 helper 一致，因為 wire 驗證器只檢上界不做修剪。

設計文字校正（非牴觸）：設計 §4.2 表格把 `_look_entries` 的 display slot 一併列入，但該產生器以 `_entity_kind(obj) is None` 過濾，character 類實體**依建構不可能**出現在其中；因此實際改動面是 `_look_entities` ＋ `_interact_targets` 兩處，對 `_look_entries` 是零改動（不是縮減範圍，是該處本無 NPC 可改）。

界內核算：姓名 ≤64 code points（`MAX_ENTITY_KEY_LENGTH`，源自 `world/art/subjects.py::MAX_SUBJECT_KEY_LENGTH`）＋ 全形空格 1 ＋ 稱號 ≤32 = ≤97 < `MAX_DISPLAY_NAME_CODE_POINTS` 128。所有 wire 驗證器與上界常量不動。

`npc_display_name` 對玩家與 `Monster` 退化為純 `key`（D2），所以兩處序列化點可以無條件呼叫它，不需在呼叫端再判一次 kind——「character 類實體才顯示全名」由組合器本身保證。

### D6. 不可變性以「沒有寫入面」實作，不以執行期防護實作

本 change 只宣告 `npc_title: str = AttributeProperty(default="")`，不提供 setter、不註冊命令、不開 LLM／intent 路徑。以結構性缺席測試釘住（仿 title-system 的 fixed-title 無刪除面測試）：斷言 `NPC` 的公開介面不含任何 `set_npc_title`／`npc_title` 寫入 helper，且指令集中不存在改稱號的命令。

理由：加 property setter 去 raise 反而製造一個「有寫入面但會拒絕」的表面，`AttributeProperty` 本身仍可被 `entity.db.npc_title = ...` 繞過，防護是假的；真正的保證來自「唯一寫入者是建立路徑」這個結構事實，交由 change 2／3 的建立點負責 `validate_npc_title` fail-closed。

### D7. `_npc_context()` 只新增資料欄位，本 change 不動 prompt 模板

`LLMNPC._npc_context()` 回傳新增 `"title": npc_title_value(self)`（缺稱號為 `""`，與既有 `name`／`desc`／`location` 的 `or ""` 慣例一致）。

`world/ai/npc_dialogue.py::_system_message` 目前只讀 `name`／`desc`／`location`，因此新增鍵**不改變任何已渲染的系統訊息**——所有既有 prompt 位元等值基準線保持綠燈。

**刻意延後（明列於 tasks.md）**：把稱號真的送進系統訊息需要 `prompts/npc_dialogue.yaml` 新增 `{title}` 佔位符（或改由 `{name}` 槽承載全名）並更新 prompt 基準線測試。設計 §4.4 的意圖是「交談中的 NPC 知道自己是南門守衛」，而設計 §7 的對應測試項寫的是 `_npc_context()["title"]` 為稱號——本 change 完成後者；在真正有作者稱號可用（change 2／3）之前，模板改動沒有可觀察效果，卻要付基準線重錄的成本，故延後。此欄位在此期間是明示的前置 seam，不是遺漏。

### D8. 指令／搜尋目標維持只匹配 `key`

不改任何 `caller.search()` 呼叫、不註冊別名、不把全名寫入 `aliases`。以測試釘住：帶稱號的 NPC 仍以純姓名被 `交談`／`邀請` 找到，且以全名字串搜尋**不**命中。

理由：設計 §4.5；把全名灌進 `key` 或 aliases 會污染搜尋並破壞 `key` 契約（設計 §2 拒絕的方案 B）。

## Risks / Trade-offs

- **旗標隨 kwargs 擴散進非預期的 `get_display_*`** → D4 已核算：只有 `get_display_characters` 會消費，且該路徑語義一致；其餘 helper 對未知 kwarg 無反應。以「看一隻身上帶著角色的 NPC」的迴歸測試不需要，但 `看 NPC` 與 `看 房間` 兩條既有 appearance 測試會覆蓋整條 template 渲染。
- **重複關鍵字 `TypeError`** → D3 的合併形式；並以「NPC 的 appearance 內含人物列」的路徑實測（`return_appearance` 注入旗標後再進 `get_display_characters`）。
- **echo 意外變成全名** → 以 byte-identical 迴歸測試釘住移動／說話／給予 echo 與 `FOLLOW_LOST_MESSAGE`：帶稱號的 NPC 在這些訊息裡必須只出現純姓名。
- **緊湊列日後被順手改成全名** → 對 `combat_view` participants、`art_view` 目錄、`service_view` host 列各補一條「必須是純姓名」的斷言測試，讓未來的改動撞到紅燈而非默默通過。
- **稱號欄資料損壞讓整塊面板 unavailable** → `npc_display_name` 契約是永不 raise：非字串、全空白、內容腐損的字串（含 markup／內部空白／控制字元——渲染它們會把 Evennia markup 或含糊識別放上螢幕）、稱號存取器 raise、乃至 `key` 存取器 raise，一律退化為純姓名（或 key 亦不可讀時的空字串，絕不產出「　稱號」式含糊識別）；超長但內容合法的字串刻意仍渲染，由顯示邊界截斷（文件化的退化態）。存取器退化由具名收斂的 safe-read `except` 邊界承擔（本模組非 facade adopter，R2 不適用，每個邊界仍附理由註解自我文件）。驗證只發生在寫入端（change 2／3）。
- **與 namegen 系列 change 的相鄰性** → 兩條線都碰 NPC 身分，但檔案不相交（namegen 動 `world/lore/names.py`、`world/rules/namegen.py`、creation UI；本 change 動 `world/rules/npc_identity.py`、`typeclasses/npcs.py`、`typeclasses/objects.py`、`exploration.py`）。唯一的概念交會點是「NPC 的 `key` 從哪來」，而本 change 對此不作任何規定。若兩者同時在 `typeclasses/npcs.py` 落地，衝突面僅為屬性宣告區的相鄰行。
- **觀測性**：本 change 不新增持久化寫入、外部 I/O 或跨系統工作流，顯示組合為純讀取，因此不新增 `world.observability` 事件（設計 §8 的 guild host／examiner boundary event 隨作者供給 change 落地）。`world/rules/npc_identity.py` 非 facade adopter（不匯入 facade），觀測性 R2（靜默吞例外）規則本就不適用於它；其容錯路徑是顯式取值檢查，外加實作期 rubber-duck 折入的兩個具名 safe-read `except` 邊界（稱號存取器、`key` 存取器），每個邊界附 `# observability: ignore R2: <reason>` 註解自我文件，讓宣稱「永不 raise」與實作一致。
