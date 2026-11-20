# Design

## Context

See `proposal.md` — Why/What. Two facts shape the approach:

- **「自由 NPC」不可用。** `docs/lore/settlement-locations.md` 的「自由 NPC」走任務藍圖 `npc_req` → `world/quests/scene_builder.py` 具現化為 `scene_npc`，是任務場景的臨時裝飾人物，跟著場景生滅；已發表場景包的 `scene_llm_npc` 是流程角色，只隨其啟用流程出現。兩者都不是「永住村裡、每天走動」的常駐居民。
- **常駐冒險者同步就是泛用核心。** `world/rules/human_guild_hosts.py::sync_persistent_adventurers` 已做到 find-or-create 持續存在的 `LLMNPC` → 從 `NpcProfile` 組裝七欄人物卡與年齡 → 寫字面數值與性別 → `resolve_residence_route` 解析家↔第二端點往返路線 → `set_npc_schedule` 指派作息 → 單一交易＋rollback 還原快取。這段 100% 可泛用；只有硬編碼的公會部分要參數化或刪除。

既有積木沿用、不改：`npc_schedules`（`set_npc_schedule`、template 詞彙、真實 Exit 結算）、`authored-dialogue-*`（條件式話題）、`npc-profile-registry`／`npc-persona-card`（設定檔與七欄卡）、`LLMNPC.at_talked_to`（生成式聊天＋離線問候語降級）。`world/rules/rulebook/npc_schedules.yaml` 已含 `resident` 模板（`move → market_square`，`state → resting`，`move → residence`），其 target 名是占位，由 per-resident 覆寫綁定到實際房 dbref——與公會模板的 `_bound_schedule` 相同，不新增排程詞彙。

## Goals / Non-Goals

Goals:
- 一份封閉的 `Resident` 作者詞彙，加上一條薄的冪等同步，把既有積木接成「常駐聊天居民」。
- 泛化路線解析，讓家與村內公共空間成為可排程往返的兩端。

Non-Goals:
- 不新增能力詞彙、不新增排程詞彙、不新增 room 型別。居民純對話；其字面數值是人物卡上的作者事實，不是新的戰鬥／考核路徑。本改變**不帶任何居民內容**（內容由 `elven-resident-npcs-content` 接續）。

## Decisions

### D1 — Authored `Resident` registry in `world/lore/`

Frozen `Resident` dataclass + `RESIDENT_REGISTRY`（初始可為空，內容改變填充）：

| Field | Meaning |
|---|---|
| `key` | stable lowercase slug；canonical 居民身分（`resident` 標籤＋名冊 key） |
| `name` | 顯示名（作者 名‧姓） |
| `profile_key` | `NpcProfile` key（七欄卡＋年齡＋voice lines） |
| `race` / `subrace` / `sex` | elf / (`fionnen`\|`ciaran`\|`eolas`) / female |
| `stats` | literal `hp, mp, sp, atk_phys, agility, defense, magic_power` |
| `home_room` | 內室 room ID（居民自己的家） |
| `schedule_template` | `npc_schedules.yaml` template key（預設 `resident`） |
| `dialogue_key` | 選填；條件式劇本表 key |

*Alternative considered:* 173 張 JSON 匯入卡＋包裹 loader 冪等。Rejected —— 匯入是一次性、重名拒收、不帶家與作息，且 JSON 不是名冊身分的正確載體（D9：lore／數值是受審 Python 資料）。`GuildAdventurer` 是既有先例，居民照其樣。

### D2 — Thin resident sync generalising the adventurer core

`world/rules/resident_sync.py::sync_residents()`，直接呼叫既有積木，不複製框架：

1. 先驗證整份 `RESIDENT_REGISTRY`（profile 已註冊、dialogue key 可解析、canonical 身分不重複、schedule template 存在）。
2. 解析每戶家與每個作息移動目標（fail-closed：任一缺漏／歧義即整批拒收），仿 `sync_service_content`「先全部解析再寫」。
3. 單一交易內，逐居民：以 canonical 身分 find-or-create `LLMNPC`；從 `profile` 組裝人物卡（套用既有組裝，玩家編輯過的人物卡在重啟時絕不被覆寫）；寫 canonical 年齡、字面 trait config、性別；有 `dialogue_key` 時掛無綁定（`binding=None`）的 `scripted_dialogue` 元件。
4. 首次建立時放進家，並以 `set_npc_schedule`（`resident` 模板＋per-resident target 覆寫）指派作息。
5. 絕不碰六種受管能力詞彙；居民不掛任何服務元件。

公會路徑的公會／戰鬥專屬部分**刻意抽掉或參數化**，而非複製：

| Adventurer-specific (today) | Resident treatment |
|---|---|
| canonical tag `guild_adventurer_person_key` | `resident` 標籤／居民 key |
| `host.db.guild_rank`＋`adventurer` 社會身分 | 移除（無階級；`NpcProfile.social_identities` 自訂） |
| 劍術技能＋`apply_lineage_auto_seed`＋`toggle_equipment(軍備)` | 移除（居民不帶戰鬥配備或血脈種子） |
| 硬編碼 `race="human"`、`sex="other"` | 參數化為 `elf`／`female`（敵 `allowed_sexes` 單例） |
| `validate_adventurers` 考官資格 | 居民側名冊驗證（profile＋dialogue＋canonical 身分） |
| `initialize_npc_persona`／`_trait_config`／`ensure_entity_sex`／`set_npc_schedule` | 原樣沿用 |

註冊於 `STARTUP_STEP_ORDER`，位在 `npc_persona_roster_validation` 之後、`sync_all` 之前。可靠性仿 host/adventurer sync：rollback 還原重用實體的屬性／元件快取，並 evict 本批建立失敗的物件。

### D3 — Generalise the residence route to home ↔ public space

`resolve_residence_route(home_key, guild_key)` 現把第二端點硬編碼為共街面的公會 place。泛化（或並列一個 resolver）使其第二端點是村內**公共空間 room**（同 settlement node），回傳同一 `{home, public, frontage}` 形狀供作息覆寫器使用。居民 `home_room` 是內室 room ID，解析為 materialized `Room`；作息條目沿用既有 `move` kind 走既有結算路徑。每戶家保有通往村街道／公共 node 的真實 Exit 以利結算穿越。公共空間可被多位居民共用。

### D4 — Chat-only dialogue wiring

居民兩種交談方式皆已實作：`talk <keyword>` → 其無綁定的條件式 `scripted_dialogue` 表；自由 `say` → `LLMNPC.at_talked_to` 生成式聊天，降級到離線問候語（`resolve_greeting` → profile voice／YAML）。不掛任何服務元件，故不入任何服務入口。

### D5 — Roster, inventory and editorial integration

- `NPC_SOURCE_INVENTORY` 新增封閉來源種類 `resident`（keyed by resident key，owner = 村切片），如 `persistent_adventurer`。
- `npc_persona_roster_validation` 納入居民：profile 已註冊且被引用、單一對話擁有者、canonical 身分唯一、無孤設定檔／孤表、voice 覆蓋規則（有對話表的居民 `voice.greeting=None`、作者填 `voice.misunderstood`）。
- `npc_editorial_review.py` 的 per-kind 面向宣告若居民引入未覆蓋面向則擴充；`docs/development/npc-editorial-review.md` 每居民一筆。

### D6 — Naming and map identity

居民 key 是新的小寫 slug；顯示名是作者 名‧姓，走既有 `validate_npc_name`。居民的家是 `content/maps/interiors/` 的新 room（含 editor layout），不與現任一 host 共用。

## Risks / Trade-offs

- [抽公會核心時誤動已測的 guild-exam 路徑] → 不重構 `human_guild_hosts.py`；居民同步是並列薄同步，只共用無痛積木（`initialize_npc_persona` 等），公會路徑不動。
- [排程移動在無真實 Exit 時靜默 skip] → 路線解析 fail-closed（缺邊即拒收整批），內容改變負責讓每戶家都接上村街道／公共 node。
- [共享 NPC 名稱／身分命名空間的重複] → canonical 身分是居民 key，名冊預檢在寫入前拒收重複。
- [玩家編輯過的居民人物卡被回寫] → 重用居民絕不覆寫（同 host 規則）。

## Migration Plan

無資料遷移。新詞彙＋同步＋（接續的）內容為增量；既有 dev world 於下次同步拾起（如需重導年齡／數值，依 `docs/development/database-reset.md` 重建）。回滾即 revert 本改變；同步冪等、自身不刪除任何東西。

## Open Questions

無阻斷項。各村的具體公共空間、消失時間的偏移量與居民清單是內容改變的決定，不改變本 spec、同步方式或任務拆解。