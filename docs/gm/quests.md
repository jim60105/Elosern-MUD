# 任務撰寫與上架

現行任務是手寫、不可變且確定性的資料定義。遊戲主持人以 Python 撰寫任務，再以 YAML 設定公會報酬。任務進度由戰鬥、進入房間與受控背包異動等可觀測事件推進，敘事文字不能直接完成任務。

## 撰寫前的設計表

每個任務先記錄穩定鍵、顯示名稱、公會階級、任務類型、階段順序、各階段目標、時限與報酬。任務鍵一經被玩家紀錄引用，請視為持久識別，不要重複使用或以相同鍵註冊不同內容。

目前的任務類型為 `GATHER`、`DEFEAT`、`ESCORT`、`EXPLORE` 與 `EMERGENCY`，它們的值分別是「採集」、「討伐」、「護衛」、「探索」與「緊急」。類型描述任務分類；實際進度由每個階段的目標種類決定。

| 目標種類 | 必填資料 | 進度來源 |
| --- | --- | --- |
| `DEFEAT` | 已登錄的 `monster_tier`，或 `requires_bound_targets=True` 二擇一 | 符合條件的擊敗事件。 |
| `REACH` | `RoomLocator` 目的地 | 玩家抵達可觀測房間。 |
| `ESCORT` | `RoomLocator` 目的地 | 護衛對象與玩家抵達目標房間。 |
| `ACQUIRE` | 已登錄的 `item_key` | 受確定性背包計畫加入該物品。 |

`RoomLocator` 可指向 `ANCHOR`、`GRID` 或 `BOUND_INSTANCE`。錨點使用已存在的 `anchor_key`；網格地點使用 `(x, y, z)`，其中 `z` 必須是已登錄的地圖鍵；綁定執行個體地點不攜帶靜態座標，必須在接取後由受控執行期繫結。現有任務目標不能指向普通 `Room`，因為它不會回報任務到達事件。

## 定義一個任務

在 `world/quests/catalog.py` 宣告 `QuestDefinition`，並把它加入 `QUEST_CATALOG`。階段索引必須由 `0` 連續編號，`stages` 必須是非空白的 tuple。以下範例是 F 級的兩隻低階魔物討伐任務。

```python
from .definitions import (
    ObjectiveKind,
    QuestDefinition,
    QuestObjective,
    QuestStage,
    QuestType,
)

ROADSIDE_CLEARANCE = QuestDefinition(
    key="roadside_clearance",
    display_name="清剿大道旁的魔物",
    quest_type=QuestType.DEFEAT,
    rank="F",
    stages=(
        QuestStage(
            index=0,
            objective=QuestObjective(
                kind=ObjectiveKind.DEFEAT,
                quantity=2,
                monster_tier="low",
            ),
        ),
    ),
    deadline_hours=24,
)

QUEST_CATALOG = (INTRODUCTORY_HUNT, ROADSIDE_CLEARANCE)
```

`DEFEAT` 目標不得同時使用 `monster_tier` 與 `requires_bound_targets`。`REACH` 與 `ESCORT` 不能附帶擊敗選擇器。`ACQUIRE` 只能引用 `world/lore/items.py` 的物品鍵，不能同時提供目的地或擊敗選擇器。任務驗證會拒絕未知魔物階級、物品鍵、錨點與網格地圖鍵。

若任務包含綁定執行個體房間、指定目標或受保護護衛對象，請使用 `world/quests/binding.py` 的受控 API 與對應整合測試。不要自行把資料庫參照寫入 `quest_log`。這類任務需要房間、實體與任務紀錄在同一交易中完成繫結。

## 設定公會任務板與報酬

把每項任務的報酬加入 `world/rules/rulebook/guild_economy.yaml` 的 `quest_rewards`。目前規則書會把它們發給阿爾托利亞分會 `guild_branch_altoria`。銅幣與功績均為非負整數，物品數量為正整數，物品鍵必須已登錄。銅幣金額還必須落在該任務階級的報酬區間。

```yaml
quest_rewards:
  - definition_key: roadside_clearance
    reward:
      copper: 75
      items:
        - item_key: healing_potion
          quantity: 1
      merit: 30
```

公會任務板僅列出角色目前公會階級可接的任務。資格依角色的實際 `guild_rank` 判定，不使用偽裝數值或註冊時的展示快照。玩家接取後可使用下列指令完成流程。

```text
guild list
guild accept <definition_key>
guild log
guild abandon <quest_id>
guild turnin <quest_id>
```

任務完成不會立即重複發獎。回報時，系統會以任務的確定性識別結算銅幣、物品與功績，並拒絕第二次結算。若有時限，世界時鐘跨越截止 tick 時會把仍進行中的任務標記為失敗，並釋放其執行期繫結。

## 測試任務內容

每個新任務至少要測試定義登錄、可接取條件、目標事件推進、完成或失敗、放棄，以及回報報酬。單元測試放在 `world/quests/tests/`；若測試任務板或指令，請同時涵蓋 `commands/tests/` 或 `world/rules/tests/`。完成後依維運指南執行相關測試與完整驗證。
