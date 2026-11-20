# Proposal

## Why

世界觀明定精靈三村各有居民（森林精靈 120、黑暗精靈 100、幻童精靈 80），但現行地圖只有承載交易的「服務主人」應答，村子讀起來空蕩。`elven-resident-npcs-mechanism` 交付了「常駐聊天居民」的建立路徑與同步；本改變是純內容切片，把三村各 15 位（共 45 位）居民的作者資料接上那條路徑，不碰任何引擎程式碼。

## What Changes

- 內容：三村各新增 15 位居民的「家」內室（`content/maps/interiors/`，含 editor layout，各接村街道／公共 node 的真實 Exit）。
- 內容：三村各 15 張 `NpcProfile`（`world/lore/npc_profiles/`，完整七欄人物卡＋age／apparent_age＋`misunderstood` voice line；有對話表的居民 `greeting=None`）。
- 內容：三村各 15 條條件式劇本對話表（`world/lore/dialogue/content/<key>.yaml`），每位至少一個 hidden/locked 的選填話題，搭配 `requires`／`variants`。
- 資料：把 45 位列填進 `RESIDENT_REGISTRY`（key、顯示名、profile_key、`elf`/亞種/`female`、字面數值、`home_room`、`resident` 作息模板、對話 key），並在 `NPC_SOURCE_INVENTORY` 登錄 45 筆 `resident` 來源（owner＝三個村切片）。
- 所有居民都是成年女性；幻童（伊歐拉斯族）居民只寫成年、不寫任何年齡或「孩童」框架。字面數值落在世界觀帶內（HP/MP/SP 各 10000、物理三軸 70–95、魔力 100–200）。
- 名冊帳本：`docs/development/npc-editorial-review.md` 每居民一筆；`content/map-reference-context.json` 重新產生。
- 本改變**不新增**測試模組、manifest 條目或任何引擎／runtime 程式碼。

## Capabilities

### New Capabilities

<!-- 無。 -->

### Modified Capabilities

- `npc-residents`（introduced by `elven-resident-npcs-mechanism`）：ADDED requirement 「三座精靈村承載其作者居民」——45 位居民經登錄表與同步可達、可交談。

## Impact

- 內容檔：`world/lore/npc_profiles/`（居民切片）、`world/lore/dialogue/content/`（45 表）、`world/lore/`（`RESIDENT_REGISTRY` 資料列）、`content/maps/interiors/`（15 個家庭屋，每村 5 個，各住母女三人）、`content/map-editor-layouts/`。
- 登錄：`world/lore/npc_profiles/inventory.py`（45 筆 `resident`）、`docs/development/npc-editorial-review.md`（45 筆）。
- 衍生物：`content/map-reference-context.json`（重新產生）。
- 不碰引擎程式碼、loader、shared 註冊清單、`npc_schedules.yaml`、`places*.py`。

## Non-goals

不改任何服務主人的既有內容或人設；不改排程詞彙、能力詞彙、數值公式；不新增測試或 manifest；不發明任何地名／物品／稱號（全部解析到既有登錄表）。

## Batch:

depends-on: elven-resident-npcs-mechanism

Code-conflict notes: 本切片獨佔其居民的 `npc_profiles/` 切片、`dialogue/content/*.yaml`、居民家的 `interiors/*.yaml`、以及每村一份 review 文件；不編輯 `resident_sync.py`、loader、任何 shared 註冊清單或 `npc_schedules.yaml`。三位服務主人既有檔案（`eolas_*`、`ciaran_*`、`fionnen_*` 之 host）不受影響。整合擁有者在機制改變歸檔後跑combined gate。