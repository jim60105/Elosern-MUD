# Design: integrate-divine-sexual-arts-catalog

## Context

`divine_sexual_arts`（神之秘法：性愛系統）是六線目錄（`world/skills/sexual_acts/`）落地之前就存在的主冊技能：`ACTIVE`、空 `cost`、`usable_out_of_combat=True`、`category=SEXUAL_ACT`、`group="神之秘法"`、`requires_divine_arts=True`、effects 為一條 `sexual_event:stimulus_applied`。它不在 `SEXUAL_ACT_REGISTRY`，因此：

- `_step4b_sexual_resist_gate` 查冊不中，**從不抵抗**（與 `divine.py` 七招行為不一致）；
- 雙冊一致性結構測試為它單開具名排除；
- 「事件僅目標受效」的 D-9 豁免由 `_builder.py::_LEGACY_TARGET_SCOPED_EVENTS = {"stimulus_applied"}` 特例表在 `action.py::_handle_sexual_event` 裡按**事件名**查表實現——這是全 repo 唯一按事件名而非前綴決定受效範圍的分支，也是「為一招維護舊系統」的實質。

世界觀定位已定：這是**悠奈（`yuna_darknight`）的簽名技**。規則面任何精靈都有機會習得，內容面全大陸只有她的卡持有它——這是她的性執著 characterization 的一部分，無移除計畫。但目錄的既有派生機制**無法**直接表達這件事：`unlocked_act_keys_for` 的計數分支對 `unlock={}` 的招式全種族無條件放行（seed 語意），照七招 shape 原樣移籍會讓每個精靈免持有即可施放。因此本變更附帶一個最小新原語（D6：`ownership_gated` 欄位），把「持有面只認實際持有」釘成派生器的永久規則。

參考系：`sexual-act-registry`（雙冊配對與結構測試族）、`sexual-catalog-divine-core`／`-mutators`（hand-built 七招的既有 shape）、`sexual-act-effects`（事件三通道現為 participant 預設＋legacy 特例）、`divine-mystery`（血統閘門）、`skill-registry`（該招存在性釘選）。

## Goals / Non-Goals

**Goals:**
- `divine_sexual_arts` 成為 `DIVINE_ACTS` 第八對，全進 `SEXUAL_ACT_REGISTRY`，享受（並服從）目錄的全部結構不變量與抵抗閘。
- 「僅目標受效」從按事件名的 legacy 特例表升格為**字首通道** `sexual_event_target:`，三通道（actor／target／participant）由字首靜態決定；刪除 `_LEGACY_TARGET_SCOPED_EVENTS` 及其 handler 分支。
- 「只有悠奈持有」由結構測試防漂移：全資料面掃描，宣稱該 key 的卡只有悠奈。
- 行為契約（目標受刺激、施法者不受刺激）逐字保留，只是路徑換成字首。

**Non-Goals:**
- 不動 `requires_divine_arts` 血統閘門本身、mastery 全面解鎖對既有招式的覆蓋面（第八招因 `requires_divine_arts=True` 繼續被 mastery 分支排除，見 D6）。
- 不給悠奈卡新增任何欄位；`ownership_gated` 是唯一的新欄位，掛在 `SexualActDef` 上作為可複用的簽名技原語，既有 65 行全部保持 `False`。
- 不動 `_FORBIDDEN_SEXUAL_EVENTS`（其存在理由——與 `pleasure:` 重複計數——與 legacy 無關）。
- 不新增 test module（shards manifest 零變動）、不做任何遷移。

## Decisions

### D1：移籍為 hand-built 第八對，不走 `_act_family()`
`_act_family()` 的行強制附 `pleasure:<key>`＋`sexual_counter:<key>` 三連套，而本招**無計數器、無 pleasure 自加算**（它的刺激全部來自事件規則表），強塞進行格式會偽造不存在的資料。`divine.py` 的七招本來就是手搭 `(SkillDef, SexualActDef)` 對（各自一條專屬效果字首），第八對同構：`requires_divine_arts=True`、`ownership_gated=True`（D6）、`unlock={}`、`base_pleasure=1`（佔位、無碼路徑讀取，與七招同款文件化註明）、`actor_part=target_part=None`、`actor_pleasure_ratio=0.0`、計數器全空、`resistible=True`、effects `["sexual_event_target:stimulus_applied"]`。
**替代方案**：擴展 `_act_family()` 允許零 pleasure 行——被否：為一行改六線共用 builder 的行契約，波及面比手搭一行大得多，且七招先例已樹立 hand-built 模式。

### D2：三通道由前綴靜態決定，刪除按名特例表
新增 `TargetSexualEventEffect(event_name)`（`effects.py`，`ActorSexualEventEffect` 的鏡像；解析走既有 `_parse_single_arg`——空／雙 payload 在**解析期** `ValueError`，與 actor 前綴同款 fail-closed，構造的 `SkillDef` 直接拒收，不可能到達 cast 期）與 `action.py` 的 `sexual_event_target:` handler：對每個 resolved target（不含 actor）stage 一條 `apply_event(target, event_name)`；`surfaces={"sexual"}`、無 event context 要求，與 `sexual_event_actor:` 完全同構。解析器契約的唯一主人是 `sexual-act-effects` capability（`parse_effect` 的家）；registry delta 只釘第八行的 `parsed_effects` 形態。`_handle_sexual_event` 刪 `_LEGACY_TARGET_SCOPED_EVENTS` 分支，participant 語意不變。舊場景「legacy skill 的 stimulus 事件保持 target-scoped」改寫為「`divine_sexual_arts` 的 `sexual_event_target:stimulus_applied` 僅對目標發射、施法者不受事件影響」——斷言內容等值，路徑換新。
**替代方案**：保留特例表只把 key 從事件名換成技能 key——被否：仍是「一招一特例」，債務原樣保留。三通道字首讓「僅目標受效」成為任何 hand-built 行都可選用的正規通道，悠奈只是第一個使用者。

### D3：抵抗閘生效是修正不是回歸
移籍後 `_step4b_sexual_resist_gate` 對本招開火（今日跳過）。敘事上正確：這招是**對目標施為**的神性刺激技，與七招同列，憑什麼免擲骰？行為面影響面極小：持有者僅悠奈（NPC 卡），她的目標多為魔獸（`resist_verdict` 照常與魔獸擲骰）。以行為測試釘住「未抵抗→目標受刺激；抵抗成功→targets 清空、cast 成功、無人受刺激」兩案。`TestSpec.SINGLE` 空 targets 的 handler 容錯沿用七招同款常規結果語意。
**替代方案**：宣告 `resistible=False` 保持今日免擲行為——被否：與「對人施為的神性技可被抵抗」的線內慣例矛盾，且 `False` 在目錄語意裡保留給「對自己做的事」。

### D4：持有面唯一性用結構掃描測，不用執行期閘門
執行期已由 D6 的 ownership gating 保證「未持有即不可解鎖、cast 由 `_step1_ownership` 拒」；「只有悠奈**持有**」則是內容不變量，用結構測釘宣稱資料（`test_registry_structure.py` 新 class）：(a) `PLAYER_PRESET_REGISTRY` 所有 preset 的 active＋passive 清單展平後，宣稱 `divine_sexual_arts` 的只有 `yuna_darknight`，並以 `patch.dict` 注入假設性第二宣稱者證明測試邏輯會具名失敗；(b) 掃描域是模組內顯式常數（現行唯一授予通道：preset 清單與 NPC `db.active_skills` 卡定義），未來新通道漏入域時配套清單斷言先炸。這是**資料測試**（釘宣稱資料，非行為）。
**替代方案**：執行期把 cast 閘門再綁「持有者 id == 悠奈」——被否：規則上它是精靈秘術，執行期硬釘單一角色反而殺死「按理其它精靈也有機會」的設定，且違反單寫者邊界外的特例膨脹。

### D5：既有釘選面逐點改寫清單
- seed 推導有**兩處**都要改成「`unlock` 為空**且非 ownership_gated**」：`OwnershipDriftGuardTests._SEED_KEYS` 的集合推導，與 `test_owned_keys_resolves_without_a_sexual_attribute`（`test_registry_structure.py:897-910` 的條列式 comprehension）——第八招 `unlock={}` 但 `ownership_gated=True`，兩處都**不得**進預期集合（這是 D6 規則在釘選面的直譯，非漏洞遮蓋）。
- `unlocked_act_keys_for`（`world/skills/sexual_acts/__init__.py`）的派生面：計數分支與 mastery 分支都跳過 `ownership_gated=True` 行（`sexual-state-handler` MODIFIED delta；第八招同時帶 `requires_divine_arts=True`，對既有角色的派生集合實際零變化，規則本身為長期原語）。該函數 docstring「a divine act declaring `unlock={}` stays owned by everyone」一段同步標明 ownership-gated 例外。
- `world/rules/combat_view.py:35-40` 與 `web/static/webclient/js/elosern/protocol.js:97-100` 的「91…65 招目錄＋pre-existing divine_sexual_arts」鏡面註解改「66 招目錄」；`MAX_SKILLS = 192` 不動。`docs/game/command-reference.md:248-250` 的泛發取得描述同步改為悠奈簽名技定位。
- `cast-settlement-atomicity` 的七技能清單**不動**（該招照舊寫快照超集內實體：僅目標）。
- `skill-category-registry`／`skill-registry`／`divine-mystery` 場景中的 effects 釘選同步為新字首（MODIFIED delta 全塊改寫）。
- `sexual-catalog-divine-mutators` 的條目數場景 → 「恰好八對且前七逐對不變」（requirement 標題不動——主語仍是 C7b 四招，既有的 `@covers_requirement` 因此零遷移）。
- 光樹文件（`docs/lore/skill-trees/light.md`）與情慾秘術文件（`sexual-act.md`）的「Legacy」措辭改「悠奈簽名技」，`divine.py` docstring 補第八對條目。

### D6：`ownership_gated`——持有面只認 base 持有
`SexualActDef`（`_builder.py:79-111`）新增 `ownership_gated: bool = False`。`unlocked_act_keys_for`（`world/skills/sexual_acts/__init__.py`）的計數分支跳過標記 `True` 的行（mastery 分支出於一般性同樣跳過，雖既有唯一標記行已被 `requires_divine_arts` 天然排除）。語意：該行的可解鎖狀態**只能**由 base 持有提供——`SkillHandler.owned_keys()`（`world/skills/handler.py:52-70`）是 base 鍵＋派生鍵，`_step1_ownership`（`world/rules/action.py`）只讀它；`conferred_grants()` 不進入任何取得路徑（這是 repo 現行 ownership-only 契約，對所有招式皆然，本變更不擴展——spec 以**負向案**釘之）。預設 `False` 讓既有 65 行結構性零變動，悠奈的 preset 授予即為唯一實際持有來源。
**替代方案**：(a) 給該招一個不可能的計數器門檻——被否：偽造資料且仍阻不了 mastery 全解；(b) 讓它留在主冊——被否：legacy 債務原樣保留；(c) 複用 `requires_divine_arts` 反推「神性血統即持有」——被否：那正是本次要消滅的免持有放行語意。

## Risks / Trade-offs

- [抵抗閘生效改變悠奈戰內行為] → 這是意圖內修正（D3）；行為測試兩案釘住邊界，其餘測試全綠才收工。
- [`_handle_sexual_event` 刪分支誤傷 65 招的 participant 預設路徑] → 分支刪除僅剩 `targets if False else participants(...)` 等值重寫；既有 `test_*_calls_apply_event_for_every_participant` 族全數保留當回歸網。
- [持有面掃描測的掃描域停滯] → 掃描域是模組內顯式常數；新增授予通道未入域時，配套的「註冊表通道清單」斷言（列舉全部宣稱型 registry）先炸，把擴充強制成顯式動作。
- [`divine_sexual_arts` 的 `SexualActDef` 佔位欄位被誤讀] → 沿用七招的文件化慣例：docstring＋欄位註解標明「無 `pleasure:` 效果，無碼路徑讀取」；結構測順帶釘該對的 `base_pleasure` 不被任何 effect 字串引用。
- [traceability：RENAMED 使 canonical slug 變動、既有 `@covers_requirement` 孤兒化] → 僅兩條 requirement 走 RENAMED（排除集合「three→two named」、effects 標題的「unchanged」已假），其餘全部 MODIFIED 保留原標題（ID 不動）；兩條 RENAMED 的既有 annotation 在 archive+sync 落地的同一變更尾步 re-point 到新 slug 並跑綠 `spec_traceability check`——精確清單：`test_registry_structure.py:689、:693`（registry slug 兩處）、`world/rules/tests/test_sexual_act_effects.py:758、:771、:790`（effects participant-slug 三處；原 :775/:776 的 legacy 案改寫後改掛 target slug），`:849` 的 disjoint 案隨 3.6(c) 刪除而 annotation 同步消失（先例：`magic-power-static-rename` P.1、repo 26 個 archived RENAMED）。

## Migration Plan

無遷移（未發布）。單一 PR、批次紅面紀律（對應 tasks.md 群 1–6）：**群 1＋2 純增量**——`effects.py` 新 dataclass＋解析分支＋解析測、`action.py` 新 handler；`_builder.py` 欄位、`sexual_acts/__init__.py` 兩分支跳過（65 行全 `False`，紅面零）。**群 3 原子切換**——主冊移除＋`divine.py` 第八對（`_register_rows` 對撞鍵直接 `ValueError`，兩者不可拆批）＋刪 legacy 分支與特例表＋`test_sexual_act_effects.py` 改寫＋`test_registry_structure.py` 兩處 seed 推導／排除常數／結構案＋`test_divine_mutators_catalog.py:98` 釘選 7→8，批次尾全綠。**群 4＋5** 綠基線加測（ownership 排他、confer 負向、抵抗閘、coercion、宣稱面掃描）。**群 6** 文件同步＋門禁。回滾＝revert 整個 PR（資料零變動）。

## Open Questions

（無——全部決策已在 D1–D6 收斂。）
