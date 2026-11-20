# Proposal

## Why

三座精靈村目前只有承載交易或接待機制的「服務主人」會出現在地圖上，而引擎沒有「只對話、不服務、有位子與作息、持續存在」的常駐居民建立路徑——`docs/lore/settlement-locations.md` 的「自由 NPC」走任務場景生成（`scene_npc`），跟著場景生滅，不是常駐居民。這項改變先交付「居民」這條建立路徑的機制，不帶任何居民內容（內容由 `elven-resident-npcs-content` 接續）。

## What Changes

- 新增封閉的 `Resident` 作者詞彙與登錄表（`world/lore/`）：`key`、顯示名、`profile_key`、`race`／`subrace`／`sex`、字面基礎數值、`home_room`、`schedule_template`、選填 `dialogue_key`。登錄表初始可為空，由內容改變填充。
- 新增冪等、交易式的居民同步，把 `world/rules/human_guild_hosts.py::sync_persistent_adventurers` 的一般核心抽成薄同步：find-or-create 持續存在的 `LLMNPC` → 組裝人物卡與年齡 → 寫字面數值與性別 → 放進家 → 指派作息；**去掉**公會／戰鬥專屬部分（階級、社會身分 `adventurer`、劍術技能、軍備、硬編碼人類性別、考官資格），且**絕不**掛任何受管服務能力。
- 泛化 `world/maps/bootstrap.py::resolve_residence_route` 的第二端點：從「家 ↔ 公會」改成「家 ↔ 村內公共空間」，回傳同一組 `{home, public, frontage}` 形狀供作息覆寫器使用。作息沿用既有 `npc_schedules`（既有 `resident` 模板＋per-resident 目標覆寫）。
- 名冊與帳本整合：`NPC_SOURCE_INVENTORY` 新增 `resident` 來源種類，`npc_persona_roster_validation` 與 `npc_editorial_review` 把居民納入身分／孤設定檔／對話擁有者檢查。
- 啟動步進：居民同步註冊於 `STARTUP_STEP_ORDER`，位在 `npc_persona_roster_validation` 之後、`sync_all` 之前。

## Capabilities

### New Capabilities

- `npc-residents`: 受作者管理的常駐「居民」NPC——持續存在、只對話聊天（`LLMNPC`，無受管服務能力）、具完整人物卡與明確年齡與字面數值、住在自己的家、依作息在家與村內公共空間間移動、以條件式劇本話題加生成式聊天與玩家交談。

### Modified Capabilities

- `npc-profile-registry`: 出貨 NPC 來源名冊新增封閉的 `resident` 種類，來源完整性與啟動名冊門禁把居民納入身分、孤設定檔／孤表與單一對話擁有者檢查。

## Impact

- `world/lore/`：新增 `Resident` 登錄表（dataclass＋registry）。`world/lore/npc_profiles/inventory.py` 新增 `resident` 來源種類。
- `world/rules/`：新增 `resident_sync.py`；`world/lore/npc_editorial_review.py`／`npc_persona_roster_validation` 納入居民。
- `world/maps/bootstrap.py`：泛化（或並列）`resolve_residence_route` 的公共空間端點。
- `server/conf/at_server_startstop.py`：`STARTUP_STEP_ORDER` 新增居民同步步進。
- 測試：以合成 `Resident` 列驅動同步的身分完整性、冪等、人物卡／字面數值／性別、作息指派、無服務能力、rollback，以及路線泛化與名冊驗證的聚焦測試。

## Batch:

depends-on: 無（根改變；`elven-resident-npcs-content` 依賴本改變）。