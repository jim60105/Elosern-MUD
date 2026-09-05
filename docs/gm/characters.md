# 角色建立與匯入

目前的角色建立入口是版本 `1` 的 JSON 匯入格式。它用於建立 NPC 與 `PlayerCharacter` 實體，並在寫入資料庫前執行結構與語意驗證。`PlayerCharacter` 匯入只建立遊戲物件，不會建立帳號、登入憑證或角色操控關係。

## 建立角色卡

複製 `world/imports/examples/example_character.json` 的參考角色卡，修改後存放在受版本控制的內容資料夾。請保留 `record_type: "character"` 與 `schema_version: 1`。匯入器不接受未宣告的欄位，因此不要以自訂欄位承載任務、帳號或臨時備註。

下列欄位為必填欄位。`subrace` 可省略，其他欄位都必須存在。

| 欄位 | 用途與限制 |
| --- | --- |
| `key` | 非空白的穩定物件識別。 |
| `display_name` | 非空白顯示名稱。此版本要求它存在；目前載入器仍以 `key` 建立 Evennia 物件。 |
| `title` | NPC 稱號（職稱／異名）：單行純文字；驗證與落庫前會先去除首尾空白，**限制套用在去除首尾空白後的正規形上**：1–32 個碼點、不得含任何空白（含全形空格 U+3000）、控制字元或 `\|`。完整規則由 `world.rules.npc_identity.validate_npc_title` 唯一執行。**只對 NPC 匯入生效**；以 `PlayerCharacter` 為目標時此欄為惰性，不會被持久化。 |
| `age`、`apparent_age` | 皆為整數且至少 `18`。 |
| `race`、`subrace` | 必須分別存在於種族與亞種登錄表，亞種須屬於指定種族。 |
| `sex` | 必須是 `female`、`male` 或 `other` 其中之一。 |
| `stats` | 基礎數值。數值不得預先乘上技能倍率。 |
| `disguised_stats` | 可為空物件；其中每個鍵都必須同時出現在 `stats`。 |
| `skills`、`passives` | 技能鍵陣列，鍵值必須存在於技能登錄表。 |
| `equipment`、`inventory` | 裝備物件與背包陣列。 |
| `sexual_baseline` | 必須含 `arousal`、`virgin` 與 `sensitivity`，值域受正規詞彙表限制。 |
| `persona` | 物件型別的敘事資料。匯入器不解析其內部欄位。 |
| `profession` | 選填。非空白字串或 `null`；值必須是職業規則書列（`world/rules/rulebook/professions.yaml`）的金鑰。缺席時行為與變更前完全相同。**只對 NPC 匯入有效**；以 `PlayerCharacter` 為目標且宣告此欄時整批拒絕。職業列的預設階級僅在 `stats` 為空時作為特質基準；只要記錄宣告任何字面數值，職業不影響特質。 |
| `components` | 選填。`{ "type": 字串, "kwargs": 物件 }` 條目陣列，只能與 `profession` 併用。條目定義最終組裝的元件集合：與藍圖同型的條目完全取代藍圖條目（kwargs 只取記錄值），藍圖未列的詞彙型別按記錄順序附加。身分辨識欄位（`service_id`、`shop_key`、`branch_key`、`dialogue_key`）一律由記錄手寫；匯入器絕不憑空補值——解析後仍缺身份欄的規畫會以具名問題整批拒絕。 |

`stats` 可提供 `hp`、`mp`、`sp`、`atk_phys`、`agility`、`defense`、`magic_power` 與 `guild_merit`。未提供的特質會以種族基準補足。`hp` 至少為 `1`；其餘數值為非負整數。若值落在種族建議區間外，驗證器會提出警告；`magic_power` 超過種族魔力帶上界、未知種族、錯誤亞種、未知技能與不合格的結構會直接拒絕匯入。

NPC 在遊戲中的顯示姓名來自 `key`（`display_name` 目前仍不被載入器使用）：要讓人物列顯示中文姓名，就把 `key` 寫成中文。房間人物列與探索面板會把 `key` 與 `title` 以全形空格組成「姓名　稱號」。

```json
{
  "record_type": "character",
  "schema_version": 1,
  "key": "altoria_scout",
  "display_name": "阿爾托利亞斥候",
  "title": "城郊斥候",
  "age": 24,
  "apparent_age": 24,
  "race": "human",
  "sex": "female",
  "stats": {"hp": 100, "mp": 30, "sp": 80, "atk_phys": 8},
  "disguised_stats": {},
  "skills": ["basic_attack"],
  "passives": [],
  "equipment": {},
  "inventory": [],
  "sexual_baseline": {
    "arousal": "平靜",
    "virgin": false,
    "sensitivity": {"general": "普通"}
  },
  "persona": {"identity": "負責巡邏城郊的成年斥候。"}
}
```

範例中的鍵值必須先和目前的登錄表核對，例如 `basic_attack` 是否仍在 `world/skills/registry.py`。角色卡不應用人物敘述取代這些可計算的資料。

## 驗證角色卡

在寫入資料庫前，使用以下命令驗證單一或多個 JSON 檔。命令會輸出拒絕原因與警告，失敗時不應進行匯入。

```sh
uv run --locked -m world.imports.validate path/to/character.json
```

批次資料應全部通過驗證後再載入。`load_batch()` 會先驗證整批檔案，並在資料庫交易中建立全部角色；其中任一檔案失敗時，該批次不會留下部分建立的角色。

驗證的責任線：CLI 只檢查檔案本身與批次內的一致性（含批次內重名）；**與資料庫既有 NPC 的重名由 `load_batch()` 在載入時整批把關**，CLI 不做這件事，也不會把它回報為降級檢查。

## 匯入 NPC

在受控的啟動或內容載入程式中呼叫 `load_batch()`。預設型別是 `NPC`。

```python
from pathlib import Path

from world.imports.loader import load_batch

npcs = load_batch([
    Path("content/characters/altoria_scout.json"),
])
```

若只需建立一名已驗證的角色，請呼叫 `instantiate_character(record)`。這個函式同樣會先驗證資料，再建立物件。

## 建立可操控角色

要建立 `PlayerCharacter`，把目標型別傳入載入器。這適合世界建立流程或測試資料；帳號與角色的綁定須由 Evennia 的帳號管理流程另外處理。

```python
from pathlib import Path

from typeclasses.characters import PlayerCharacter
from world.imports.loader import load_batch

characters = load_batch(
    [Path("content/characters/player_template.json")],
    typeclass=PlayerCharacter,
)
```

請不要改用 `create_object()` 略過角色卡驗證。若需要建立服務 NPC，請使用既有的啟動同步程序或在受測試的內容程式中附加對應元件；公會服務人員需要 `GuildStaff` 元件，商人需要 `Merchant` 元件。
# Player character registration

New accounts receive one inert, account-owned character shell. The player must
activate that shell before world commands become available. `character` lists
the two supported modes:

- `character preset <key>` selects a shipped adult character.
- `character create` prompts for a name, actual age, apparent age, race,
  optional compatible subrace, and six stat allocations.

Both ages must be at least 18. Custom allocations must remain inside the
selected lore bands and spend the exact displayed budget. Magic level is not a
player input; activation samples it inside ±10% of the selected race's average.
After activation, ordinary commands such as `look`, `inventory`, and `rest 5s`
become available.
