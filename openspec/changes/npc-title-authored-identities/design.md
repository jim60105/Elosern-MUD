# npc-title-authored-identities — Design

## Context

已核准設計 `docs/superpowers/specs/2026-09-03-npc-identity-titles-design.md` 是唯一事實來源；本文件只解釋 §5 的 blueprint／registry 三列 ＋§6 的 blueprint／registry 錯誤處理 ＋§7 的 blueprint／guild 測試落地時的技術取捨，不重述設計已定案的決策，也不擴張其範圍。

現況（本 change 動工前，以程式碼為準）：

- **blueprint `npc_req` 的驗證落點**：`world/ai/scenario_director.py::_validate_npc_characterization`（提案 guardrail）與 `world/quests/compile.py::_validate_scene_fields`（編譯邊界）**兩層都呼叫同一個純函式** `world/quests/characterization.py::characterize_errors`。`world/ai/director_templates.py` 不含任何驗證邏輯，它是離線降級用的手寫模板池資料（三筆 `QuestBlueprint`，其中一筆帶一個 `npc_req`，已有 `display_name="黑鬍"`）。設計 §5 寫的「`world/ai/director_templates.py` 的提案驗證」與現況不符，見 D1。
- **場景 NPC 的姓名**：`scene_builder.py::_spawn_npc` 以 `key=f"{_scene_name(archetype)}的{role}"`（例如「林間小徑的盜匪」）建立實體；作者供給的 `display_name` 只被寫進 `npc.db.display_name`，而該屬性目前**唯一的讀者**是 `world/art/subjects.py:201`（頭像 subject 名稱）。也就是說：今天房間人物列印出來的名字，跟作者寫的名字毫無關係。
- **`characterize_errors` 的規則集**：`display_name`／`age`／`apparent_age`／`portrait`／`persona`／`background` 全部**選填**（`if "display_name" in entry:`），上界常量 `MAX_DISPLAY_NAME_LENGTH = 64` 由該模組自持。模組 docstring 明文宣告「不匯入 `world.rules`」的純度契約，但同檔的 `race_lifespan_upper_bound` 已示範以**函式內延遲匯入**取用 `world.lore` registry。
- **guild／shop host**：`world/rules/guild_economy.py::_sync_service_host(key, room, component_specs)` 以 `NPC.objects.filter(db_key=key).first()` 找既有 host，找不到就 `create_object(NPC, key=key, ...)`。`key` 是模組常量 `GUILD_SERVICE_KEY = "altoria_guild_master"`／`MERCHANT_SERVICE_KEY = "altoria_merchant"`，同一字串又被當成元件的 `service_id`。所以公會長現在在房間裡的顯示名稱就是 ASCII 的 `altoria_guild_master`。重用是「找到就更新 location／race／成年身分＋補齊缺少的元件」，不是「找到就完全不動」。
- **`SHOP_REGISTRY`**（`world/lore/shops.py`）目前只有 `altoria_general_store` 一列，欄位為 `key`／`merchant_component_key`／`offered_item_keys`。公會分會 host 沒有任何 registry row：它的身分來源是 `GUILD_BRANCH_REGISTRY["guild_branch_altoria"]`（`world/lore/guild.py`）＋兩個模組常量。
- **考官**：建立點是 `world/rules/guild_exams.py::_spawn_opponent`，由 `start_guild_exam` 呼叫；`settle_exam_outcome` 只寫考試終局狀態，**臨時對手是由呼叫端在結算交易提交後刪除的**。設計 §5 寫的建立點與現況不符，見 D8。現況 key 為 `f"guild-examiner-{rank}-{pk}"`，pk 後綴是 archived change `fix-battlefield-identity-collisions` 為了修 audit finding F08 加的：戰場 roster（`combat.py`／`combat_session.py`）與 skip-safety 註冊表（`skip_safety.py`）**都以 `str(entity.key)` 為鍵**。
- `GUILD_RANK_REGISTRY`（`world/lore/guild.py`）七列，欄位為 `key`／`order`／獎勵區間／`description`／`title_key`（玩家固定稱號，與 NPC 稱號無關）。
- 前置 change `npc-title-identity-core` 交付 `world/rules/npc_identity.py`（`validate_npc_title`／`npc_title_value`／`npc_display_name`）與 `NPC.npc_title`；`npc-title-import-pipeline` 交付匯入面的 `title` 欄位、loader 落庫與對既有 NPC 的重名 gate。

## Goals / Non-Goals

**Goals:**

- 讓「建立時就存在於世界」的三條 NPC 生產路徑（blueprint 場景佔用者、guild／shop host、晉級考官）全部改為作者供給姓名＋稱號，缺一即拒絕建立。
- 稱號規則只有一個實作（change 1 的 `validate_npc_title`）；姓名規則在本 change 收斂成第二個共用實作（`validate_npc_name`），blueprint 與 registry 兩個作者面共用。
- 把設計 §3.2 不變式 2 在 blueprint 面與 registry 面補上：blueprint 內姓名唯一、三份 registry 的作者姓名互不重複。
- 保持既有的碰撞安全網：戰場 roster 與 skip-safety 以 `key` 為鍵的不碰撞保證、host 重複啟動不產生第二隻 NPC。
- 保持離線可玩：本 change 不新增任何對 LLM 的依賴（見 D2 的離線核算）。

**Non-Goals:**

- 匯入 schema／loader／匯入面唯一性（change 2）。
- 核心組合器、`npc_title` 屬性宣告、顯示路由、prompt `title` 欄位（change 1，本 change 只消費）。
- NPC 姓名的**產生方式**（namegen 系列 change）：本 change 只規定 registry 與 blueprint 必須把姓名明文寫出來。設計 §2 已明文拒絕命名池／自動取名，本 change 不引入任何取名演算法。
- `Monster` 稱號、玩家稱號系統、runtime 改稱號、多語言與 markup（設計 §9 範圍外）。
- 任何相容層、遷移或 `schema_version` 分支（未發布、零使用者）。

## Decisions

### D1. blueprint 的規則落點是 `world/quests/characterization.py`（設計文字校正）

設計 §5 寫「blueprint `npc_req`（`world/ai/director_templates.py` 的提案驗證、`world/quests` 編譯鏈）」。實際上提案驗證住在 `world/ai/scenario_director.py::_validate_npc_characterization`，而它與編譯邊界都把規則委派給 `world/quests/characterization.py::characterize_errors`——這正是主規格 `blueprint-portrait-policy` 的「單一規則來源」requirement 明文要求的形狀（「A pure validation function SHALL exist under `world/quests/` ... 兩層都呼叫它，任一層都不得自行 inline」）。

因此本 change 的必填規則**只寫在 `characterize_errors` 裡一次**，兩層自動同步；`director_templates.py` 的改動只有資料（模板 `npc_req` 補 `title`）。設計的敘述在此校正，不影響其結論。

### D2. `display_name` 必填的意義：作者姓名成為 spawned NPC 的 `key`

設計 §2 說「姓名＋稱號一律由作者供給」，§3.2 不變式 1 說「每隻 NPC 必有姓名」，§4.2 的全名組合讀的是 `key`。`npc_req` 沒有 `key` 欄位，唯一能承載作者姓名的就是 `display_name`——所以「`display_name` 由選填改必填」只有在**它成為 NPC 的 `key`** 時才有意義；否則場景 NPC 仍叫「林間小徑的盜匪」，作者寫的名字繼續只有頭像檔名看得到，設計 §5 的這一列等於沒有落地。

因此 `_spawn_npc` 的 prototype `key` 改為 `characterization.display_name`。`npc.db.display_name` 的既有寫入**保留**（頭像 subject 名稱的讀者不變，值與 `key` 同源），避免動到 `art-stable-key-contract` 的任何面。

與 change 2 的差異（不是矛盾）：匯入面的角色卡**有** `key` 欄位，`display_name` 是被驗證但 loader 從不讀取的惰性欄位，change 2 的 D7 因此明文不把它接成顯示姓名。blueprint 面沒有 `key`，情況相反。

**離線核算（設計要求的「不引入命名池」在此成立）**：現況沒有任何「LLM 缺 `display_name` 時由程式湊一個名字」的 fallback——`key` 從來就是 `f"{場景}的{role}"` 這個泛型合成字串，與 LLM 無關。本 change 之後：

1. LLM 提案缺 `display_name`／`title` → guardrail 具名拒絕 → 既有重試預算內重試 → 仍失敗則 `generate_quest_blueprint` 依既有降級路徑改用 `director_templates.py` 的模板池，而模板池的 `npc_req` 由本 change 補齊作者姓名與稱號。
2. 因此「離線可玩」不需要任何取名演算法，也不會出現無名 NPC；泛型合成 key 從此消失。

代價（刻意接受）：同一個模板重複派發時，場景佔用者永遠叫同一個名字（例如兩次「討伐林間盜匪」都遇到「黑鬍」）。這與設計 §3.2「runtime 生成沿用既有具名佔用者的冪等同步語義（同名即同一人）」一致——同一位盜匪頭子在不同任務裡是同一個角色。

### D3. 稱號規則的取得方式：`characterization.py` 函式內延遲匯入 `world.rules.npc_identity`

```python
def characterize_errors(entry, *, lifespan_upper_bound):
    from world.rules.npc_identity import validate_npc_name, validate_npc_title
    ...
```

`characterization.py` 的 docstring 目前宣告「只匯入不可變 lore registry 與成年下限常量」的純度契約，並以此為由讓 `MAX_PERSONA_FIELD_LENGTH` 與 `world.rules.character_creation` 之間走「parity contract」（兩邊各寫一個數字，用測試釘住相等）。本 change **不**沿用那個模式：change 1 的 requirement 已把 `validate_npc_title` 定義成「每一條 NPC 稱號寫入路徑共用的**單一**驗證器」，在此複製一份字元集規則會直接違反它，而 parity contract 只能釘住數字、釘不住規則。

延遲匯入是安全的：`world/rules/npc_identity.py` 的 module scope 只有 stdlib（change 1 的設計明文），不匯入 typeclass、Evennia、`world.quests` 或 `world.ai`，因此不可能形成環。同檔的 `race_lifespan_upper_bound` 已是同一手法的先例。實作時同批修訂該 docstring：純度契約改述為「不在 module scope 匯入 `world.rules`；規則委派以函式內延遲匯入取得，且被委派的模組必須是無副作用的純驗證器」。

`MAX_DISPLAY_NAME_LENGTH = 64` 改為 `from world.rules.npc_identity import MAX_NPC_NAME_CODE_POINTS`（同一延遲匯入），數字來源收斂成一個。64 這個上界不變（設計 §4.2 的界內核算以它為前提）。

**`validate_npc_name` 的規則**（本 change 在 `npc_identity.py` 新增，與 `validate_npc_title` 同形）：`str`、strip 後 1–64 code points、拒控制字元、拒 `|`、拒全形空格 U+3000（它是組合器的分隔符，混進姓名會讓全名無法逆解）。**允許**一般 ASCII 空白（既有角色姓名可以有空白，例如「莉絲·晨星」不需要但不該因此收緊既有 `key` 契約）；這是它與 `validate_npc_title` 唯一的規則差異，並在 requirement 裡明文寫出理由。回傳 strip 後的正規形。

### D4. blueprint 面的姓名唯一性：整份 blueprint 內姓名全域唯一（無跨 stage 例外）

- **任何兩筆 `npc_req`**（同 stage 或跨 stage）的 `display_name` 相同即拒，實作為單一的 `duplicate_display_name_errors(entries)` 全集檢查。

理由（rubber-duck 複審後收緊，原「跨 stage 同名＋同 characterization 允許」方案已被否決）：

1. SceneBuilder 的佔用者是**每個 quest record 每次 materialization 新生**的（`_materialize_instance` 依 active record 建 instance room 並綁新佔用者；無任何跨 stage／跨 instance 的具名查找或複用路徑）。允許跨 stage 同名並不會得到「同一位角色登場兩次」，而是兩隻同 `key` 的活體——設計 §3.2 的「同名即同一人」冪等語義在這個面上根本不存在。
2. `display_name` 現在同時是 `key`。同名跨 stage 意味著世界上有兩隻可同時存在的同 `key` NPC，直接違反「姓名全世界唯一」不變式；指令目標解析、戰場 roster、skip-safety 的 key 鍵控全部以「key 唯一」為前提。
3. 「同一位角色在多階段登場」的既有正當用法由**共用 `stable_key`**（頭像身分）承載，不需要也不應該用同 `key` 承載。真需要同一具名角色跨 stage 行動時，作者給不同 stage 用不同角色（或把該 NPC 放進 registry 走固定 key 路徑）。

與 `duplicate_stable_key_errors` 的關係：兩者仍是同形規則（同一份 characterization 一致性比較），只是姓名規則採更嚴的全集唯一；共用 identity tuple 的實作照樣成立。

**不做（延後，非遺漏）**：blueprint 姓名對 `SHOP_REGISTRY`／`GUILD_BRANCH_REGISTRY`／`GUILD_RANK_REGISTRY` 作者姓名的跨面碰撞檢查，以及對資料庫既有 NPC 的查覆。理由：前者是純資料檢查但屬於第四條規則、可獨立追加；後者在編譯時根本問不到（編譯發生在 spawn 之前很久，且 SceneBuilder 依設計 §3.2 走「同名即同一人」的冪等語義而非碰撞語義）。這是本不變式在 blueprint 面的**已知缺口**，記在 Risks 與 tasks 的延後清單。

### D5. 資料形狀：結構層維持 `str | None`，必填由單一驗證器執行

`BlueprintNpcReq.title`／`StageNpcCharacterization.title` 都宣告為 `str | None = None`，`display_name` 維持現有宣告，**不**改成無預設值的必填 dataclass 欄位。理由：

- `QuestBlueprint` 是 frozen dataclass，`from_payload` 以 `.get()` 建構；把欄位改成必填會讓「缺欄」變成 `TypeError`／`KeyError` 而不是 guardrail 的具名診斷 ＋ 重試，而 `scenario-director` 的既有 requirement 要求缺欄走「validation failure → 附上錯誤 → 預算內重試」。
- 欄位順序調整會打到既有以位置參數建構 `BlueprintNpcReq` 的測試與模板。

必填性由 `characterize_errors` 這一個地方執行，而它在 guardrail 與編譯邊界都會對**每一筆** entry 跑（現況已是如此），因此沒有繞過路徑。SceneBuilder 另有第三道重驗（D6）。

`_npc_req_canonical` 與 `_stage_requirement_canonical` 帶上 `title`，所以兩個只差稱號的 blueprint 會得到不同的內容 digest（與既有 `display_name` 的處理一致）。`_characterization_from_payload`（durable store 還原路徑）以具名拒絕讀取 `title`：既存的生成任務 payload 沒有這個欄位，還原時會以 `QuestCompileError` 明確失敗，而不是 `KeyError`——見 Risks。

### D6. SceneBuilder：第三道 fail-closed 重驗，缺欄即回滾整個 materialization

`_revalidate_characterization` 目前在「沒有 characterization」或「entry 為空」時**靜默 return**。本 change 改為：任一佔用者缺 characterization、缺 `display_name` 或缺 `title` 一律 `raise SceneBuilderSpawnError`。理由與該函式既有的設計理由完全相同（偽造的 `StageSpawnRequirement` 可以繞過編譯邊界寫入未成年年齡）——姓名與稱號現在是同一等級的不變式，缺席就是 fail closed，整個 materialization 在建立任何房間或實體之前回滾。

`_apply_characterization` 以 `npc.npc_title = validate_npc_title(characterization.title)` 落庫（寫驗證器的回傳值＝strip 後正規形，與 change 2 的 loader 同一手法）。

### D7. guild／shop host：以元件 `service_id` 為冪等錨，作者姓名為 `key`

```python
def _sync_service_host(service_id, name, title, room, component_specs) -> NPC:
    host = _host_by_service_id(service_id)      # 掃 NPC family，比對元件上的 service_id
    if host is None:
        host = create_object(NPC, key=validate_npc_name(name), location=room)
        host.npc_title = validate_npc_title(title)
        log_info("guild_service_host_created", context={...})
    ...
```

設計 §5 說「沿用既有 key 冪等重用邏輯：既存 host 不改名」，§3.2 說「guild host／examiner 走 registry 固定 key，天然冪等」。這裡的「固定 key」指的是 **registry 的固定識別碼**（`service_id`／`shop_key`），不是 NPC 的顯示 `key`——一旦 NPC 的 `key` 變成作者姓名，再用 `db_key` 當重用錨就會在下次啟動找不到自己造的 host、每次啟動多生一隻。因此重用錨改為元件上的 `service_id`（元件 `DBField`，與作者姓名完全脫鉤）。

三條性質因此同時成立：(1) 重複啟動不產生第二隻 host；(2) 既存 host **永不改名**（找到就沿用，即使 registry 的 `host_name` 後來被改）；(3) 稱號只在既存 host 的稱號為空時補寫，非空時不覆寫——這維持 change 1 的「稱號建立後不可變」（補空是把未設定的欄位設定起來，不是改寫已賦值的稱號），也維持該函式既有的「找到就把缺的補齊」語義（它今天就會補 location／race／成年身分／缺少的元件）。

掃描成本：一次 `NPC.objects.all_family()` 走訪，與同檔既有的 `_initialize_merchant_stock` 同形，且只在啟動同步時各跑一次。

替代方案：(a) 直接以作者姓名當 `db_key` 查覆——被否決：registry 改名即產生孤兒 host ＋ 第二隻 host。(b) 保留 `db_key=service_id` 當 key、把姓名塞進別的欄位——被否決：顯示層讀 `key`，公會長會繼續叫 `altoria_guild_master`。

### D8. 考官：建立點是 `_spawn_opponent`（設計文字校正），去衝突後綴改為條件式

設計 §5 寫「`world/rules/guild_exams.py::settle_exam_outcome` 的對手 NPC 改用 authored 姓名為 `key`」。實際建立點是 `_spawn_opponent`（`start_guild_exam` 呼叫），`settle_exam_outcome` 只寫終局狀態、對手由呼叫端在提交後刪除。校正落點，結論不變。

衝突處理是本 change 唯一與既有主規格**正面衝突**的地方：`guild-rank-exams` 現有 requirement 要求「每次 spawn 的 display key 都帶專屬唯一成分」，而作者姓名依定義是固定的。解法：

```python
opponent = create_object(NPC, key=rank.examiner_name)   # 作者姓名
opponent.npc_title = validate_npc_title(rank.examiner_title)
...
if _key_taken_by_other(opponent):          # 任何其他實體（含玩家）已持有同名
    opponent.key = f"{rank.examiner_name}-{opponent.pk}"
```

即：**作者姓名優先，被佔用時才附加 `-{pk}`**。兩條既有 scenario 的保證原封不動——玩家legally 取了同名時考試照樣開得起來（對手改用後綴形），兩場同階級考試同時進行時兩隻對手的 key 仍互異——而 audit finding F08（roster／skip-safety 以 `str(entity.key)` 為鍵）的修補不被回退。requirement 原文改述為這個條件式規則。

替代方案：(a) 永遠附加 `-{pk}`——被否決：房間人物列會印「雷加·鐵拳-12　F 級考官」，作者供給等於白做。(b) 永不附加，改為把 roster 改成以 dbref 為鍵——被否決：archived change 的 phase-6 驗證已結論「roster identity 遷移要動每一個 roster-key 消費端＋`Battlefield.__post_init__` 斷言」，遠超本 change 的一天預算，且與 NPC 稱號無關。

### D9. registry 載入 fail closed：module 載入時驗證自己的 rows ＋跨 registry 姓名唯一

設計 §6 要求「`SHOP_REGISTRY`／`GUILD_RANK_REGISTRY` 缺欄 → 載入 fail closed」。落地形狀：

- **缺欄**：新欄位在 frozen dataclass 上宣告為**無預設值**的必填欄位，少寫一欄就是 module 匯入時的 `TypeError`——不需要額外程式碼，而且不可能被繞過。
- **違規值**：`world/lore/shops.py` 與 `world/lore/guild.py` 在 module 尾端對自己的 rows 跑一次驗證（延遲匯入 `validate_npc_name`／`validate_npc_title`），失敗即具名 `ValueError`。先例：`world/lore/titles.py` 在 module 載入時 `validate_fixed_titles(...)`；`world/lore/wilderness_entry.py::validate_wilderness_entries()` 由 `sync_all()` 在鏡射前呼叫。
- **跨 registry 姓名唯一**：三份 registry 的作者姓名（1 個 shop host ＋1 個分會 host ＋7 位考官）必須互不重複。放在 `world/lore/guild.py`（它已匯入自己的兩份 registry；shops 以延遲匯入取得）或一個由兩邊共用的小 helper，實作時擇一，requirement 只規定「載入時 fail closed」不綁模組。

驗證函式必須是**可被測試直接呼叫的純函式**（傳入 rows、回傳／raise），才能對違規 row 寫測試而不需要污染真實 registry。

### D10. 觀測性：兩個建立邊界事件

依設計 §8 與觀測性目錄（新增持久狀態變更必須留 info 事件）：

```python
log_info("guild_service_host_created", context={"char": host.key, "shop": shop_key_or_none, "service": service_id})
log_info("guild_exam_opponent_created", context={"char": opponent.key, "rank": target_rank})
```

只在**實際建立**時發（重用是既有的冪等 no-op，不再發一次「建立」）；`context` 帶設計指名的 `char`／`shop`／`rank`，不帶玩家文案。兩個檔案都已經是 facade adopter（都已具名匯入 `log_warn`），所以本 change 不改變 adopter 集合，`tools/observability_freeze.json`（空清單）不動。測試依 AGENTS.md patch **呼叫端模組**的綁定（`world.rules.guild_economy.log_info`），不 patch `world.observability.*`。

## Risks / Trade-offs

- **既存的生成任務 payload 沒有 `title`，重啟還原會失敗** → `restore_generated_quests()` 的既有契約就是「還原不了就大聲失敗，不靜默丟棄」，本 change 沿用並讓它是具名的 `QuestCompileError`（不是 `KeyError`）。開發用資料庫依專案政策可丟棄（未發布、零使用者、無遷移）；tasks 內記明處置方式為清空 generated-quest store 或重建測試資料庫，避免實作者以為是 bug。
- **內容 digest 改變** → canonical 序列化多一個 `title` 欄位，任何寫死 digest 字串的基準線測試會轉紅；tasks 第一步即全 repo 搜尋 `ai_` 前綴的字面 digest 並同批更新。
- **既有測試大面積轉紅**（`npc_req` 字面 dict 缺欄、斷言場景 NPC key 為「XX的YY」、斷言考官 key 為 `guild-examiner-*`）→ 這是必填欄位與改名的必然結果，不是缺陷；tasks 逐檔列出已知落點，實作時先搜尋再補。
- **blueprint 姓名與 registry 姓名的跨面碰撞未檢查**（D4 延後項）→ 已知缺口：作者若把場景佔用者取名成與公會長相同，世界上會出現兩隻同 `key` 的 NPC（不同房間，指令目標解析各自在自己的房間內進行，戰場 roster 也是房間內組成，因此**不會**觸發 F08 類碰撞）。影響限於敘事一致性，且兩個作者面都是人工編輯的少量資料。留給後續 change，或在本 change 若提早完成時追加。
- **（已消除）跨 stage 同名佔用者同時存活** → D4 收緊為整份 blueprint 姓名唯一後，此風險在作者面即被拒絕。
- **既有開發資料庫裡的 host 不會改名** → D7 的刻意行為（設計明文）。那隻 host 會繼續叫 `altoria_guild_master`；稱號則會在下次啟動同步時補上。要看到作者姓名需要重建資料庫，tasks 註明。
- **玩家的指令目標字串改變** → 場景佔用者從「攻擊 盜匪」變成「攻擊 黑鬍」，考官從 `guild-examiner-F-12` 變成人名。這正是本功能的目的（設計 §4.5 保證指令仍只匹配純 `key`，玩家永遠不必打稱號）；`docs/game/` 的命令文件不受影響（無命令面變更）。
- **`characterization.py` 的純度契約被修訂** → D3 已說明理由與環風險核算；實作時同批更新該模組 docstring，避免下一位讀者以為是違規。
- **一天預算** → 若超時，優先保住 registry 面（第 2／3 組：兩隻 host 與七位考官，玩家每一局都會遇到），把 blueprint 面（第 4／5 組）獨立成後續 change 並在 tasks 記錄；兩者之間沒有程式碼相依。

## Migration Plan

無資料遷移、無相容層。落地順序：`validate_npc_name` → registry 欄位與載入驗證 → guild host／考官生成 → blueprint 規則 → 編譯鏈與 SceneBuilder → 觀測性與測試 → 主規格 sync 與 `covers_requirement`。回退方式是整批 revert；本 change 不寫任何無法由重新啟動同步重建的持久狀態（host 與考官都是啟動同步／考試流程產生的）。

## Open Questions

無阻斷性問題。以下為刻意記錄、本 change **不**處理的既有偏差：

- `world/rules/guild_economy.py::sync_service_content` 內 `catalog = get_catalog()` 取得後未被使用（死變數），與本 change 無因果關係，不順手改。
- `GuildRank.title_key` 是**玩家**固定稱號的鍵，與本 change 新增的 `examiner_title`（NPC 稱號純文字）完全無關；兩者同住一列容易誤讀，欄位命名以 `examiner_` 前綴區隔，並在 requirement 內明文寫出兩者不共用。
