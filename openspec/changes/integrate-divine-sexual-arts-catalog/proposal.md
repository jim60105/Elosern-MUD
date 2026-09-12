# Proposal: integrate-divine-sexual-arts-catalog

## Why

`divine_sexual_arts`（神之秘法：性愛系統）是六線目錄體系落地之前註冊在主冊的舊籍招式，為了保留它「事件僅目標受效」的歷史語意，`_builder.py` 背著一整个 `_LEGACY_TARGET_SCOPED_EVENTS` 特例集合、`action.py` 的 `sexual_event` handler 背著一條對它單開的分支、`sexual-act-registry` 的雙冊一致性結構測試背著一條具名排除。這是全 repo 唯一「為一招維護一套舊系統」的債務。同時，這招的世界觀定位已經明確：它是**悠奈的簽名技**——規則上任何精靈都有機會習得（招式本身對所有持有者開放），內容上只有悠奈的卡持有它（她的性執著 characterization），且沒有移除計畫。本次把這招完全併入目錄體系，消滅 legacy 機制，並把「只有悠奈持有」從隱性作者慣例升格為結構測試守住的內容不變量。

一個關鍵的既有機制缺口決定了設計形態：`unlocked_act_keys_for` 的計數分支對 `unlock={}` 的招式**全種族無條件放行**（seed 語意）。若第八招照七招的 `requires_divine_arts` 血統閘門原樣移籍，每個精靈免持有即可施放，直接違反「只有悠奈持有」。因此目錄需新增「持有面閘門」（ownership gating）：該招的可解鎖集合**只能由實際持有授予**，任何派生路徑（計數器、`SexualMasteryEffect` 全解）一律繞過。

## What Changes

- 把 `divine_sexual_arts` 從 `world/skills/registry.py` 主冊移入 `world/skills/sexual_acts/divine.py` 的 `DIVINE_ACTS`，成為第八個 hand-built `(SkillDef, SexualActDef)` 對（`requires_divine_arts=True`、`unlock={}`、`resistible=True`、無部位、無計數器）。
- `SexualActDef` 新增 `ownership_gated: bool = False` 欄位；`unlocked_act_keys_for` 的計數分支跳過標記 `ownership_gated=True` 的行。既有 65 行全部保持 `False`，行為零變動；此欄位同時成為「簽名技」的長期可複用原語。
- 新增 `sexual_event_target:<name>` 效果字首與 `TargetSexualEventEffect`（`ActorSexualEventEffect` 的鏡像），把「僅目標受效」升格為三種事件範圍通道之一（actor／target／participant）；`divine_sexual_arts` 的 effects 改宣告 `sexual_event_target:stimulus_applied`。
- **BREAKING**（機制面，無玩家可見資料損傷）：刪除 `_builder.py` 的 `_LEGACY_TARGET_SCOPED_EVENTS` 與 `action.py` `_handle_sexual_event` 對它的分支。三種範圍改由字首靜態決定，不再按事件名查特例表。`_FORBIDDEN_SEXUAL_EVENTS`（對 `_act_family()` 行的宣告黑名單）不動。
- **行為變更（刻意）**：移籍後該招進入 `SEXUAL_ACT_REGISTRY`，`_step4b_sexual_resist_gate` 從此對它開火（今日因未進冊而完全跳過抵抗判定）——它的目標現在和其他七招神性技法一樣可以抵抗；抵抗成功的目標不受刺激。這是與神性線對齊的修正，以測試釘住。
- `sexual-act-registry` 雙冊一致性結構測試的具名排除集合從 `{divine_sexual_arts, divine_sexual_mastery, reincarnation_boon_yuna}` 縮為 `{divine_sexual_mastery, reincarnation_boon_yuna}`；同時新增持有面結構測試：`PLAYER_PRESET_REGISTRY` 全部 preset 的 skill 清單中宣告 `divine_sexual_arts` 的只有悠奈（`yuna_darknight`）——「只有她持有」由 CI 防漂移。
- 文件同步：`docs/lore/skill-trees/sexual-act.md` 頂點節將「Legacy 單招」改寫為「悠奈簽名技」定位；`world/skills/sexual_acts/divine.py` 模組 docstring 補第八招的 hand-built 理由。

## Capabilities

### New Capabilities

（無——全部落在既有 capability。）

### Modified Capabilities

- `sexual-act-registry`：`SexualActDef` 欄位清單新增 `ownership_gated`；雙冊一致性排除集合縮編為兩項（requirement 標題的「three named」改「two named」——RENAMED）；新增第八行結構、持有面唯一宣稱、效果字首解析三條 ADDED 要求。
- `sexual-state-handler`：`unlocked_act_keys()` 派生要求補 ownership-gated 排除（計數分支與 mastery 分支皆然）——只有實際持有才授予；既有的「空 unlock 必定在場」場景加「非 ownership-gated」限定詞（requirement 標題不動）。
- `sexual-act-effects`：`sexual_event` handler 的事件範圍解析從「participant 預設＋`_LEGACY_TARGET_SCOPED_EVENTS` 按名特例」改為「三通道字首靜態決定」（新增 `sexual_event_target:`）；legacy target-scoped 場景改寫為新字首場景（原標題的「unchanged」已假——RENAMED）。
- `skill-registry`：`divine_sexual_arts` 的存在性要求改寫——effects 從 `["sexual_event:stimulus_applied"]` 改為 `["sexual_event_target:stimulus_applied"]`，並註明其冊籍已遷入 `SEXUAL_ACT_REGISTRY`（`divine.py`）。
- `divine-mystery`：血統閘門要求的措辭更新——`divine_sexual_arts` 現在同時受 `_step4b_sexual_resist_gate` 管轄（與 `divine.py` 七招一致）；`can_use_divine_arts` 閘門本身不變。
- `sexual-catalog-divine-mutators`：條目數釘選場景更新為「恰好八對且前七對逐對不變」（requirement 標題主語仍是四招 C7b，標題不動；正文承認第八對為 ownership-gated 的 `divine_sexual_arts`）。
- `skill-category-registry`：`divine_sexual_arts` 再分類場景的 effects 釘選從 `sexual_event:stimulus_applied` 更新為 `sexual_event_target:stimulus_applied`。

## Impact

- **程式碼**：`world/skills/sexual_acts/divine.py`（＋第八對）、`world/skills/sexual_acts/_builder.py`（刪 `_LEGACY_TARGET_SCOPED_EVENTS`）、`world/skills/sexual_acts/registry.py`（`SexualActDef` ＋`ownership_gated` 欄位）、`world/skills/registry.py`（移除該 SkillDef）、`world/skills/effects.py`（新增 `TargetSexualEventEffect`）、`world/rules/action.py`（新 handler＋`_EFFECT_HANDLERS` 註冊、刪 legacy 分支）、`world/rules/sexual_state.py`（派生分支跳過 ownership-gated 行）。
- **測試**：`world/skills/sexual_acts/tests/`（目錄結構測擴為八對、排除集合縮編、持有面掃描測、`OwnershipDriftGuardTests` 的派生集合**排除** ownership-gated 行——歸入**資料測試**組）、`world/rules/tests/` 與 `world/skills/tests/` 相關模組（target 字首行為案、未持有不可派生行為案、移籍後抵抗閘行為案——歸入**行為測試**組）。既有 `test_legacy_stimulus_event_stays_target_scoped` 與 `LegacyTargetScopedEventTests` 改寫為新字首路徑的等值斷言。新測試一律擴充既有已註冊模組，`.github/evennia-shards.json` 零變動。
- **資料**：零遷移（未發布專案、無使用者）。`player_presets.py` 的悠奈卡不改——她的清單引用 key，key 不變。
- **副作用（修正性）**：該招從所有人類（及所有非悠奈角色）的 `owned_keys()`／戰鬥選單消失——舊主冊時代它對人類可見但 cast 必拒；移籍加 ownership 閘門後它只對持有者可見，消除幽靈条目。
- **不動**：`_FORBIDDEN_SEXUAL_EVENTS`、`SexualMasteryEffect` 的全解語意（對神性七招的排除照舊）、`cast-settlement-atomicity` 快照面（該招照舊寫入快照超集內實體）、`combat_view.MAX_SKILLS`（192，技能總數不變）、webclient 呈現面（悠奈清單同 key）、`sexual-act-seeds`（七顆 seed 全非 ownership-gated，其要求逐字仍真）。
