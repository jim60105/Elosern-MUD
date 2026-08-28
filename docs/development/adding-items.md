# 新增物品指南

本指南說明如何為 Elosern 加入一個新的物品。以目前三筆（`meal`、`healing_potion`、`plain_sword`）的 registry 為基準，走一遍新增物品的完整流程：決定物品形狀、寫入 `ITEM_REGISTRY`、接上效果與價格的 rulebook、補測試，以及哪些消費端會自動跟著動。

本文假設你已讀過：

- `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`（世界資料與確定性核心的邊界）
- `openspec/specs/equipment-inventory/spec.md`、`openspec/specs/item-use-resolution/spec.md`、`openspec/specs/inventory-item-actions/spec.md`（物品、裝備與使用行為的現行契約）
- 已落地的範例：`openspec/changes/archive/2026-08-29-add-inventory-item-actions/`

---

## 1. 背景：一件物品的資料住在四個地方

物品是 `world/lore/items.py` 中 `ITEM_REGISTRY` 字典裡的 `ItemDefinition`。架構上最重要的設計決定是**身份與數值分離**：registry 只管「這是什麼、長怎樣、有沒有機制」，所有可調的數值都住在確定性 rulebook，調平衡不用動 lore。

| 資料域 | 位置 | 內容 |
|---|---|---|
| 身份＋外觀＋機制宣告 | `world/lore/items.py::ITEM_REGISTRY` | key、正體中文名稱、`price_table_key`、`sellable`、presentation、三選一的機制 |
| 價格帶 | `world/lore/economy.py::PRICE_TABLE` | 每個 `price_table_key` 的 `min_copper`／`max_copper` 上下界 |
| 商店成交值 | `world/rules/rulebook/guild_economy.yaml` | 各店 offer 的 `buy_copper`／`sell_copper`（整數銅板）、庫存、補貨 |
| 效果量級 | `world/rules/rulebook/item_effects.yaml` | 每個 `ItemEffectKey` 的正整數 `amount`（上限 9999），以及非戰鬥使用耗時 `item_use_seconds`（目前 6 秒） |

`ItemDefinition` 是 frozen dataclass，`__post_init__` 在構造時驗證 presentation 與機制的形狀及互斥關係（`key`、名稱、`price_table_key`、`sellable` 本身不做驗證），壞定義會讓 registry 載入直接失敗，不會拖到運行時才爆。機制部分是**唯一的行為縫隙**，三選一：

| 形狀 | 宣告 | 結果 |
|---|---|---|
| 可使用（藥水、食物） | `use_mechanics=ItemUseMechanics(effect_key, consumable, combat_allowed)` | 玩家可用 `使用`／介面「使用」；`consumable` 決定是否消耗 |
| 可裝備（武器、護甲、飾品） | `equipment_slot=EquipmentSlot.X` | 玩家可用 `裝備`／介面切換；單例槽互換、`ACCESSORY` 上限 5 件 |
| 純觀察 | 兩者都不給 | 只能持有、檢視、買賣，沒有行前驗證可用的動作 |

> [!NOTE]
> `use_mechanics` 與 `equipment_slot` 同時出現會直接拋錯。外觀的 `kind`（food／weapon／…）純視覺，規則與前端一律不得從 `kind` 或名稱推測行為。

---

## 2. 事前決定：這個物品是哪一種形狀？

新增前先回答四個問題，它們決定你要碰哪幾個檔案：

1. 它會被「使用」嗎？是 → 需要 `ItemEffectKey` 與 `item_effects.yaml` 條目。
2. 它能裝備嗎？是 → 選 `EquipmentSlot`（`weapon_main`／`weapon_off`／`armor`／`accessory`），飾品共用 5 件上限。
3. 它能買賣嗎？是 → 需要 `PRICE_TABLE` 價格帶與至少一家店的 offer。
4. 現有的 effect key（`self_heal`／`greater_heal`／`mana_restore`）能描述它的效果嗎？不能 → 這不只是加資料，見 §5。

---

## 3. Step by Step

### Step 0 — 從設計文件取得數值

價格、效果量級不得自行發明。以設計文件與既有 rulebook 為來源；需要新數值時先更新設計文件，再落地。錢幣一律整數銅板（金 1 = 銀 100 = 銅 10000，見 `world/lore/economy.py`）。

### Step 1 — 寫入 `ITEM_REGISTRY`

在 `world/lore/items.py` 的 `ITEM_REGISTRY` 直譯中加入一筆。以一枚飾品為例：

```python
ItemDefinition(
    key="lucky_charm",
    display_name_zh="幸運符",
    price_table_key="accessory",
    sellable=True,
    presentation=ItemPresentation(
        kind=ItemKind.ACCESSORY,
        icon_key=ItemIconKey.ACCESSORY,
        rarity=ItemRarity.UNCOMMON,
        summary_zh="編織著紅色絲繩的小護符。",
    ),
    equipment_slot=EquipmentSlot.ACCESSORY,
),
```

構造時會被拒絕的寫法（全部在 `__post_init__` 攔下）：

| 約束 | 所屬欄位 |
|---|---|
| kind／icon／rarity 必須是封閉列舉成員 | `presentation` |
| 摘要非空、不超過 128 字元、單行純文字、不含 `<`、不含 URL、不含 emoji | `summary_zh` |
| `effect_key` 必須是 `ItemEffectKey` 成員，旗標必須是真 bool | `use_mechanics` |
| `equipment_slot` 必須是 `EquipmentSlot` 成員 | `equipment_slot` |
| use 與 slot 互斥 | `ItemDefinition` |

icon 只存 key，SVG 由 Vue 端自行映射，registry 不接受任何圖片位址或 CSS。

### Step 2 — 可使用物品：接上效果 rulebook

在 `item_effects.yaml` 確認該 `effect_key` 有條目：

```yaml
effects:
  self_heal:
    amount: 40
  greater_heal:
    amount: 120
  mana_restore:
    amount: 40
```

載入器 `world/rules/items.py` 做**雙向封閉檢查**：每個 `ItemEffectKey` 成員必須恰好對應一條正整數、不超過 9999 的規則；rulebook 裡也不能出現 registry 沒註冊的 key。任何一邊缺條目，載入即拋 `ItemEffectsRulebookError`。

使用流程（非戰鬥與戰鬥中的先驗證、提交、回滾語意）都已由 `world/rules/items.py` 與 `world/rules/equipment.py` 的共同寫入路徑處理，新增資料不需要寫新的狀態變更程式碼。

### Step 3 — 可交易物品：價格帶與商店 offer

先在 `world/lore/economy.py::PRICE_TABLE` 註冊價格帶（若 `price_table_key` 已存在可沿用，例如魔法藥劑共用 `potion`）：

```python
"accessory": PriceEntry("accessory", "魔法飾品", 80, 800, "A minor magical accessory."),
```

再確認目標店在 `world/lore/shops.py::SHOP_REGISTRY` 的登記。商店的身份（含 `offered_item_keys`）住在這個不可變 registry，YAML 的 offer 必須與它一致，缺了一邊，`world/rules/guild_config.py` 載入時就拋 `GuildConfigError`：

```python
ShopDefinition(
    key="altoria_general_store",
    merchant_component_key="merchant",
    offered_item_keys=("meal", "healing_potion", "plain_sword", "lucky_charm"),
),
```

最後在 `guild_economy.yaml` 該店的 `offers` 加入成交值。載入器的驗證是不對稱的，別誤會價格帶的保護範圍：`buy_copper` 必須非負且落在價格帶 `min_copper`～`max_copper` 內；`sell_copper` 只要求非負且不超過 `buy_copper`，**不受價格帶下限約束**：

```yaml
- item_key: lucky_charm
  buy_copper: 150
  sell_copper: 75
  max_stock: 3
  initial_stock: 1
  restock_quantity: 1
```

### Step 4 — 檢查受影響的消費端（既有數值通常零程式碼）

這些模組都是讀 registry 取值，用**既有**列舉值與 effect key 新增的物品會自動出現在對應表面：

- 規則端：`world/rules/items.py`、`equipment.py`、`economy.py`、`service_view.py`（背包列的可行動作與停用原因由 preflight 推導）
- 指令端：`使用`（`use`）、`裝備`（`equip`）在 `commands/items.py`；`丟`（`drop`）、`給`（`give`）在 `commands/localized/general.py`；商店為 `shop stock`（別名 `商店庫存`）、`buy`（`購買`）、`sell`（`販賣`），見 `commands/economy.py`
- WebClient：服務面板背包列與確認框（`web/webclient/actions/service_actions.py` 走同一份 preflight，前端不自行推斷行為）

零程式碼的前提是數值沿用現有詞彙。`kind`、`icon_key`、`rarity` 都是封閉列舉，需要一個新的視覺分類或圖示就不是加資料能了事：得擴充 `world/lore/items.py` 的列舉、`web/webclient-app` 的圖示對應與對應測試／展示，前端遇到未知 icon key 一律退回 unknown Treatment。

若你只是加了資料，上面這些檔案不需要修改；需要修改的那個檔案，就是你發現設計違反的地方，先回頭檢查。

### Step 5 — 補測試與驗證

依順序跑最小聚焦集：

```sh
MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb \
  world.lore.tests.test_items \
  world.rules.tests.test_item_use \
  world.rules.tests.test_equipment_toggle \
  world.rules.tests.test_shop_economy
MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb commands.tests.test_items
```

測試該涵蓋的內容，照既有前例辦：新物品的構造通過 registry 驗證（`world/lore/tests/test_items.py`）、可行為的 preflight 分支（如 `hp_full`、飾品達五件上限）、交易價格帶驗證。驗證完成後跑可追溯性門檻：

```sh
uv run --locked python -m tools.spec_traceability check
```

---

## 4. 常見錯誤

| 錯誤 | 後果 |
|---|---|
| 把治療量、價格寫進 `ItemDefinition` | 違反「身份與數值分離」，consumer 端会開始複製常數；registry 驗證与規格稽核都会擋下 |
| 用 `kind` 或名稱推測行為 | 行為只認 `use_mechanics`／`equipment_slot`，前端與規則都有對應測試釘住 |
| 新 effect 只加 YAML 不扩 `ItemEffectKey`（或反之） | 載入器雙向封閉檢查直接失敗 |
| 商店 `buy_copper` 超出價格帶 | `guild_config` 載入失敗，啟動即爆；注意 `sell_copper` 不受價格帶約束 |
| 只改 YAML 沒把物品加進 `shops.py` 的 `offered_item_keys` | 兩邊不一致，載入時 `GuildConfigError` |
| 摘要塞了連結、emoji 或換行 | 構造時被 `summary_zh` 驗證拒絕 |
| 為新物品發明新的 kind／icon／rarity 值卻只改 registry | 構造被封閉列舉拒絕；擴充視覺詞彙見 §5 |
| 為了讓某個測試通過而捏造 registry 資料 | 世界資料是產品決定；測試該用受控 registry 分層（規則層、adapter 層、Storybook），瀏覽器端只測真實資料 |

---

## 5. 什麼時候這不是一篇指南能帶你走完的事

新增一筆資料（新藥水、新飾品、新商店 offer）照上面的流程做即可。但有兩類例外超出「加資料」的範圍：

1. **新行為**，例如新的效果類型（中毒、綁定屬性、消耗品以外的冷卻）、新的裝備槽、或改變使用耗時的規則，會擴及 `ItemEffectKey` 封閉列舉、規則解析與既有規格需求。
2. **新視覺詞彙**，即新的 `ItemKind`、`ItemIconKey` 或 `ItemRarity` 值，會擴及三個封閉列舉、前端圖示對應與展示層。

兩者都屬於規格驅動變更，請走 OpenSpec 流程（`openspec-propose`），並同步 `equipment-inventory`、`item-use-resolution`、`inventory-item-actions` 相關主規格。
