# 新增物品指南

本指南說明如何為 Elosern 加入一個新的物品。物品的**身份、外觀與專屬效果**現在只住在一個地方：`content/items/` 的 YAML 目錄。以目前的目錄為基準（筆數本身不是契約），走一遍新增物品的完整流程：決定物品形狀、寫入 catalog、補價格與商店，以及哪些消費端會自動跟著動。

本文假設你已讀過：

- `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`（世界資料與確定性核心的邊界，含 D9 修訂）
- `openspec/specs/equipment-inventory/spec.md`、`openspec/specs/item-use-resolution/spec.md`、`openspec/specs/inventory-item-actions/spec.md`（物品、裝備與使用行為的現行契約）

---

## 1. 背景：一件物品的資料住在哪裡

物品目錄的唯一入口是 `content/items/catalog.yaml`：

```yaml
schema_version: 1
files:
  - core_items.yaml
  - armor_accessories_materials.yaml
```

`files` 是**作者決定的呈現順序**；載入器依序讀取每個檔案，並保留檔內列順序。`world/lore/items/assembly.py` 是唯一的資料讀取器：它只匯入物品詞彙與 PyYAML，不匯入 `world.rules`，載入後發布：

- `ITEM_REGISTRY`：`key -> ItemDefinition`（順序即呈現順序）
- `ITEM_SOURCES`：每個 key 的來源檔（相對於儲存庫根目錄，例如 `content/items/core_items.yaml`）
- `ITEM_USE_EFFECT_INPUTS` / `ITEM_EQUIPMENT_EFFECT_INPUTS`：每個列自己的原始效果輸入

身份與數值仍然分離：目錄只管「這是什麼、長怎樣、有沒有機制、它的專屬效果長什麼樣」；共用的使用耗時與裝備預算住在 `world/rules/rulebook/`，可調平衡不必動目錄。

每個檔案含一個 `items:` 清單，每列是一個 mapping：

```yaml
items:
  - key: healing_potion
    display_name_zh: 治療藥水
    price_table_key: potion
    sellable: true
    presentation:
      kind: potion
      icon_key: potion
      rarity: rare
      summary_zh: 盛裝於小瓶中的治療藥水。
    use_mechanics:
      consumable: true
      combat_allowed: true
      effects:
        - stat: hp
          amount: 40
```

### 允許的欄位

必填：`key`、`display_name_zh`、`price_table_key`、`sellable`、`presentation`。選填：`guild_property`、`liturgical_role`、`use_mechanics`、`equipment_slot`、`equipment_effects`。未知欄位一律拒絕（包含已退役的 `modifier_key`）。

機制三選一，互斥：

| 形狀 | 宣告 | 結果 |
|---|---|---|
| 可使用 | `use_mechanics`（含 `consumable`、`combat_allowed`、`effects`） | 玩家可用 `使用`／介面「使用」；效果就是同列的有序 `effects` |
| 可裝備 | `equipment_slot` 加同列的 `equipment_effects`（無效果裝備寫 `{}`） | 玩家可用 `裝備`／介面切換；效果以物品自己的 `key` 綁定 |
| 純觀察 | 兩者都不給 | 只能持有、檢視、買賣 |

`key` 必須符合 `[a-z][a-z0-9]*(?:_[a-z0-9]+)*`：冒號會破壞既有的 `buff_key:item_key` 掛載識別。`equipment_slot` 的封閉詞彙是主手 `weapon_main`、副手 `weapon_off`、護甲 `armor`、飾品 `accessory`（飾品共用五件上限）。

---

## 2. 事前決定：這個物品是哪一種形狀？

1. 它會被「使用」嗎？是 → 在 `use_mechanics.effects` 寫下有序效果（見 Step 2）。
2. 它能裝備嗎？是 → 選 `equipment_slot` 並在同一列寫 `equipment_effects`（見 Step 2b）。
3. 它能買賣嗎？是 → 需要 `PRICE_TABLE` 價格帶與至少一家店的 offer。
4. 三個現成動詞（`stat`＋`amount`、`apply_status`、`remove_status`）加上既有狀態鍵，能描述它的效果嗎？不能 → 這已超出加資料的範圍，見 §5。

---

## 3. Step by Step

### Step 0 — 從設計文件取得數值

價格、效果量級不得自行發明。以設計文件與既有 rulebook 為來源；需要新數值時先更新設計文件，再實作。錢幣一律整數銅板（金 1 = 銀 100 = 銅 10000）。

### Step 1 — 在 catalog 的某個檔案加一列

在 `catalog.yaml` 已列出的某個檔案（例如 `core_items.yaml`）的 `items:` 尾端追加一列。**不要**新開未列入的 YAML 檔：載入器會拒絕未宣告的檔案；要新增檔案時，先把它加進 `catalog.yaml` 的 `files`（順序即呈現順序）。

```yaml
  - key: lucky_charm
    display_name_zh: 幸運符
    price_table_key: accessory
    sellable: true
    presentation:
      kind: accessory
      icon_key: accessory
      rarity: uncommon
      summary_zh: 編織著紅色絲繩的小護符。
    equipment_slot: accessory
    equipment_effects:
      adjustments:
        defense: 1
```

載入器會拒絕：重複的列 key、重複的 YAML mapping key、檔案層級的未知欄位、錯誤型別（`sellable` 必須是 bool、`schema_version` 必須是整數 1）、不合文法的 key、沒有槽卻寫 `equipment_effects`、有槽卻漏寫 `equipment_effects`、以及同時宣告使用與裝備機制。錯誤訊息會指出檔案、列位置／key 與欄位。

`ItemDefinition` 的 `__post_init__` 另外驗證：`presentation` 的三個封閉列舉、摘要非空且不超過 128 字元、單行純文字、不含 `<`、不含 URL、不含 emoji；`guild_property` 必須是 bool 且不可同時 `sellable`；`liturgical_role` 必須是封閉列舉且只出現在裝備物品。

icon 只存 key，SVG 由 Vue 端自行映射，目錄不接受任何圖片位址或 CSS。

### Step 2 — 可使用物品：在同一列寫效果

`use_mechanics.effects` 是至少一個條目的有序列表；每個條目恰好聲明一個動詞欄位：

```yaml
    use_mechanics:
      consumable: true
      combat_allowed: true
      effects:
        - remove_status: poisoned
        - apply_status: focus
```

`world/rules/item_effects.py` 做**雙向封閉檢查**：每件已註冊可使用物品恰好一組效果、效果不得出現在非可使用列、清單至少一個條目。條目級驗證：動詞欄位互斥、`stat` 是封閉計量條、`amount` 非零且絕對值不超過 9999、`apply_status` 只收 `buffs.yaml` 的具體狀態鍵、`remove_status` 收具體鍵或 `all`／`positive`／`negative` 選擇器、同一列不得對同一計量條宣告兩筆調整、`scope` 是五檔封閉詞彙（`self` 預設／`single`／`all-allies`／`all-enemies`／`all`）。任何違規，載入即拋 `ItemEffectsRulebookError` 並指名來源。

非戰鬥使用耗時是**共用設定**，住在 `world/rules/rulebook/item_effects.yaml` 的 `item_use_seconds`（目前 6 秒），不可逐列宣告。使用流程（先驗證、提交、回滾）由 `world/rules/items/` 與 `world/rules/equipment.py` 的共同寫入路徑處理；效果依宣告順序執行。新增資料不需要寫新的狀態變更程式碼，也不需要擴充任何效果鍵列舉。

### Step 2b — 可裝備物品：在同一列寫裝備效果

每件裝備在**自己的列**上寫恰好一個 `equipment_effects` mapping；無效果裝備寫 `{}`（例如 `storage_pouch`、`royal_traveling_robe`）。欄位是封閉詞彙：

```yaml
    equipment_slot: accessory
    equipment_effects:
      adjustments:
        defense: 1
      gauge_caps:
        hp: 5
      immune:
        - poisoned
      exposure_bias: 0
```

載入器 `world/rules/equipment_effects.py` 驗證（任一失敗即拋 `EquipmentEffectsRulebookError`，伺服器啟動時就爆並指名來源列）：

- 每個有槽的列恰好一個 mapping、非裝備列不得有 mapping、mapping 欄位與 `adjustments` 鍵都在封閉詞彙內。
- 數值種類：平值欄（`atk_phys`／`defense`／`magic_power`／`exposure_bias`）是整數；百分比欄（`mp_cost`／`sp_cost`／`pleasure_gain`／`heal_gain`）是帶正負號字串（`"-10%"`／`"+15%"`）；唯獨 `agility` 兩種皆可，種類決定預算欄位。`bool` 一律拒收。
- 預算：`world/rules/rulebook/equipment_effects.yaml` 的 `budgets` 依物品 `presentation.rarity` 決定每欄上限；`abs(值)` 超過即拒絕。護盾上限只收正整數（hp／mp／sp），單筆上限 ≤ 9999。`weapon_damage_multiplier` 只允許武器，且受 `weapon_multiplier` 預算約束。
- `immune`／`attached_buffs` 必須是 `buffs.yaml` 的 buff key，同一 mapping 不得同時免疫與掛載同一個 buff，也不得免疫生理投影。
- 空 mapping 合法，代表「純觀察的裝備，無效果」。

數值來自設計文件（`docs/superpowers/specs/2026-08-29-equipment-combat-effects-design.md` 的平衡表），不得自行發明。

### Step 2c — 光明教會裝備：`liturgical_role`

教會裝備的教義歸屬是**物品自身的不可變資料**，不是效果 mapping 的一欄：在列上宣告 `liturgical_role`（`LiturgicalRole.VESTMENT_OR_EMBLEM` 或 `LiturgicalRole.SANCTUARY_DEVICE`，不宣告就是不屬於教會教義範圍）。`validate_church_doctrine` 會在每次載入時，依物品自己的角色檢查對應效果：

- 聖袍／聖徽：`exposure_bias` 非負、**必須有**非負的 `pleasure_gain`、宣告的 `heal_gain` 非負，且具備正向 `heal_gain` 或一道免疫。
- 聖所器具：`exposure_bias` 非負且 `pleasure_gain` 必須為正；不要求治療或免疫。

兩者都只是裝備分類；一般戰鬥取捨（負 `defense`、`atk_phys`、敏捷等）仍允許。效果 mapping 的欄位是封閉的，所以**效果無法宣告或改寫角色**：表裡寫 `liturgical_role` 只會被當成未知欄位拒絕。

### Step 4 — 可交易物品：價格帶與商店 offer

先在 `world/lore/economy.py::PRICE_TABLE` 註冊價格帶（若 `price_table_key` 已存在可沿用）：

```python
"accessory": PriceEntry("accessory", "魔法飾品", 80, 800, "A minor magical accessory."),
```

再把物品放進一個商品分類（assortment）：商店販售的商品是它引用的分類的聯集，分類的身份（`item_keys`）住在 `world/lore/settlements/assortments.py::ASSORTMENT_REGISTRY`，成交數字住在 `world/rules/rulebook/commerce/` 對應定居點分檔。兩邊缺了一邊，`world/rules/guild_config.py` 載入時就拋 `GuildConfigError`：

```python
AssortmentDefinition(
    key="common_arms",
    display_name_zh="王都兵器",
    allowed_item_kinds=frozenset({ItemKind.WEAPON, ItemKind.TOOL}),
    allowed_equipment_slots=frozenset(
        {EquipmentSlot.WEAPON_MAIN, EquipmentSlot.WEAPON_OFF}
    ),
    item_keys=("plain_sword", "iron_dagger", "lucky_charm"),
),
```

`item_keys` 是身分，貨架政策（`allowed_item_kinds`／`allowed_equipment_slots`）是用途：兩者都由載入器逐項比對，放錯貨架會在載入時指名分類與物品直接拒絕；合法的新商品只要 kind 與槽符合就自動上架。

再把物品加進商店引用的分類，並在該定居點的 commerce 分檔中該分類的 `offers` 加入成交值：

```yaml
assortments:
  - key: common_arms
    offers:
      - item_key: lucky_charm
        buy_copper: 150
        sell_copper: 75
        max_stock: 3
        initial_stock: 1
        restock_quantity: 1
shops:
  - shop_key: altoria_general_store
    open_hour: 8
    close_hour: 20
    restock_hour: 6
```

`buy_copper` 必須落在價格帶 `min_copper`～`max_copper` 內；`sell_copper` 只要求非負且不超過 `buy_copper`。同一間店引用的兩個分類若出現同一個 `item_key`，載入器會指名商店、物品與兩個分類直接拒絕。

**不可販售與信物的優先序**：`sellable=false` 的物品在任何路徑上都不會被買賣。`relic`（信物）帶的物品在**載入時**就從每一條上架路徑全部擋掉；信物仍可持有、檢視，只是永遠接不上商人交易。

### Step 4b — 開局套裝：`SUBRACE_STARTING_KIT_REGISTRY`

自訂建立時每個亞種醒來帶著的裝備住在 `world/lore/starting_kits.py`，一筆 `SubraceStartingKit(subrace_key, items, max_rarity)`。驗證在載入時進行：每個選項必須是已註冊的裝備、槽位可配戴、且不得超過該套裝自己宣告的品質上限。

### Step 5 — 檢查受影響的消費端（既有數值通常零程式碼）

這些模組都讀 registry 取值，用**既有**列舉值與現成效果動詞新增的物品會自動出現在對應表面：

- 規則端：`world/rules/items/`、`equipment.py`、`economy.py`、`service_view.py`
- 指令端：`使用`（`use`）、`裝備`（`equip`）在 `commands/items.py`；`丟`、`給` 在 `commands/localized/general.py`；商店在 `commands/economy.py`
- WebClient：服務面板背包列與確認框（`web/webclient/actions/service_actions.py` 走同一份 preflight）
- GM 世界資料：物品明細會顯示**載入列自己的來源檔**（`source_path`），登錄表清單仍顯示目錄 `content/items/`

`kind`、`icon_key`、`rarity` 都是封閉列舉，需要新的視覺分類時才需要擴充 `world/lore/items/vocab.py` 與前端圖示對應。

### Step 6 — 補測試與驗證

依序跑最小聚焦集：

```sh
uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb \
  world.lore.tests.test_items \
  world.rules.tests.test_item_effects_rulebook \
  world.rules.tests.test_equipment_effect_rulebook \
  world.rules.tests.test_equipment_toggle \
  world.rules.tests.test_item_use \
  world.rules.tests.test_shop_economy
uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb commands.tests.test_items
```

驗證完成後跑可追溯性與合約門檻：

```sh
uv run --locked python -m tools.spec_traceability check
uv run --locked python -m tools.contract_gate --change <change>
```

測試裡的數值角色分成三類：**通用完整性**驗證 schema、身份與參照、槽位、稀有度預算與價格帶歸屬，不比對具體數值；**共用合成機制**用受控的 file-local 合成宣告驗證算式結果；**代表性整合冒煙**讀取現行宣告當輸入，觀察另一個消費端的結果。價格、庫存、調整與效果量級都住在資料裡，測試只驗證關係與接線。

---

## 4. 常見錯誤

| 錯誤 | 後果 |
|---|---|
| 把治療量、價格寫進物品列 | 違反「身份與數值分離」；效果留在該列，但量級只由該列的 `effects` 擁有，價格仍屬 `PRICE_TABLE` |
| 用 `kind` 或名稱推測行為 | 行為只認 `use_mechanics`／`equipment_slot`，前端與規則都有對應測試釘住 |
| 可使用列漏寫或空寫 `effects` | 載入器雙向封閉檢查直接失敗，啟動即爆並指名來源 |
| 有槽列漏寫 `equipment_effects` | `EquipmentEffectsRulebookError`，啟動即爆；無效果要寫 `{}` |
| 非裝備列寫 `equipment_effects` | 載入器拒絕：效果只能綁在有槽的列 |
| 還寫舊的 `modifier_key` | 未知欄位，目錄載入即拒絕 |
| 新增檔案卻沒列進 `catalog.yaml` | 載入器指名未宣告的檔案 |
| 百分比欄寫成裸數字或平值欄寫成字串 | 數值種類由欄位決定，`bool` 也不算整數 |
| 分類 `buy_copper` 超出價格帶 | `guild_config` 載入失敗，啟動即爆 |
| 只改 commerce 分檔沒把物品加進分類（或反之） | 載入時 `GuildConfigError`，指名分類與物品 |
| 把信物放進分類或場所加成／覆寫 | 載入或解析時直接拒絕，信物永不交易 |
| 想用效果 mapping 改寫教會裝備的教義角色 | mapping 欄位封閉，`liturgical_role` 只會被當成未知欄位拒絕 |
| 替聖袍省掉 `pleasure_gain` 以為可以避開教義 | 缺少該欄位本身就是違規 |
| 摘要放了連結、emoji 或換行 | 構造時被 `summary_zh` 驗證拒絕 |
| 為新物品發明新的 kind／icon／rarity 值卻只改 catalog | 構造被封閉列舉拒絕 |
| 把價格、庫存或效果量級抄進測試當期望值 | 每次合法調價都得回頭改測試；改成讀取宣告並只驗證關係與接線 |

---

## 5. 超出「加資料」範圍的情况

需要新的效果動詞、新的目標範圍語意、新的 `kind`／`icon`／`rarity` 值，或新的裝備欄位時，這已不是加資料，而是規格驅動變更，請走 OpenSpec 流程並同步對應主規格。
