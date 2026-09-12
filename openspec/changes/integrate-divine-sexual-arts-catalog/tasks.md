# Tasks: integrate-divine-sexual-arts-catalog

追蹤性前置：`@covers_requirement` 的 ID 必須存在於 main index（`tools.spec_traceability` 對不存在的 ID 報 `unknown-requirement-id`，與該測是否可執行無關）。本變更兩條 RENAMED（排除集合「three→two named」、effects 的 name-entries 條）sync 後舊 slug 消失、5 處既有 annotation（`world/skills/tests/test_sexual_act_effects.py` 758/771/775/790、`world/skills/sexual_acts/tests/test_registry_structure.py` 689）會孤兒化——re-point 已排進第 6 群，作為 archive+sync 落地的**同變更尾步**執行（先例：`magic-power-static-rename` P.1、repo 26 個 archived RENAMED）。其餘 MODIFIED 全部保留原標题，ID 不動。實作期（sync 前）`check` 以舊 slug 跑綠。

## 1. 效果通道（target-scoped prefix）

- [ ] 1.1 `world/skills/effects.py`：新增 `TargetSexualEventEffect`（`@dataclass(frozen=True)`，欄位 `event_name: str`），文件字串說明它是 `ActorSexualEventEffect` 的鏡像、recipient 為 resolved targets 而非 actor。
- [ ] 1.2 效果解析面（`parse_effect` 所在模組）：讓它認識 `sexual_event_target:` 前綴並解析成 `TargetSexualEventEffect`；空事件名的解析語意照 actor 版處理。
- [ ] 1.3 `world/rules/action.py`：新增 `_handle_sexual_event_target`（`surfaces=frozenset({"sexual"})`、無 required event context）——對每個 resolved target stage 一條 `apply_event(target, event_name, ...)` 的 `PendingEffect`，絕不含 actor；空事件名丟 `RejectedAction(RejectReason.EFFECT_RESOLUTION_FAILED, ...)`；空 `targets` 為正常 no-op；不做觀察者閘門。在 `_EFFECT_HANDLERS` 註冊前綴。
- [ ] 1.4 `world/rules/action.py::_handle_sexual_event`：刪除 `_LEGACY_TARGET_SCOPED_EVENTS` 分支，recipient 恆為 `participants(actor, targets)`；更新該 handler 的文件字串與註解（三通道由前綴決定）。
- [ ] 1.5 `world/skills/sexual_acts/_builder.py`：刪除 `_LEGACY_TARGET_SCOPED_EVENTS` 常數與其所有註解；保留 `_FORBIDDEN_SEXUAL_EVENTS` 原樣，並在其註解補一句「recipient scope 由前綴決定，與本黑名單無關」。

## 2. 持有面閘門（ownership gating 原語）

- [ ] 2.1 `world/skills/sexual_acts/registry.py`：`SexualActDef` 新增 `ownership_gated: bool = False`，文件字串／欄位註解說明「解鎖狀態只能由實際持有提供，派生路徑一律繞過」。`_act_family` 不需參數化（全部 builder 行維持 `False`）。
- [ ] 2.2 `world/rules/sexual_state.py::unlocked_act_keys_for`：計數分支跳過 `ownership_gated=True` 的行；mastery 分支同樣跳過（一般性規則）。確認既有 65 行的派生集合逐字不变（第八招尚未移籍時本節可先行落地）。

## 3. 招式移籍

- [ ] 3.1 `world/skills/sexual_acts/divine.py`：新增第八個 hand-built 對 `divine_sexual_arts`（`SkillDef`：`ACTIVE`、`cost={}`、`usable_out_of_combat=True`、`element=None`、`category=SEXUAL_ACT`、`group="神之秘法"`、`requires_divine_arts=True`、effects `["sexual_event_target:stimulus_applied"]`；`SexualActDef`：`ownership_gated=True`、`unlock={}`、`base_pleasure=1`、`actor_part=None`、`target_part=None`、`actor_pleasure_ratio=0.0`、計數器全空、`resistible=True`），並更新模組 docstring（七招 → 八招；補第八招的 hand-built 理由與 ownership_gated／佔位欄位說明）。
- [ ] 3.2 `world/skills/registry.py`：移除主冊的 `divine_sexual_arts` inline `_skill(...)` 條目（該 key 改由目錄 import 安裝）。確認 `SKILL_REGISTRY` 總數不變、`combat_view.MAX_SKILLS`（192）不動。
- [ ] 3.3 全 repo 掃描殘餘引用：`docs/lore/skill-trees/light.md` 與 `docs/lore/skill-trees/sexual-act.md` 的「Legacy」措辭改為「悠奈簽名技」定位（規則上精靈可習得、內容上僅 `yuna_darknight` 持有、事件範圍走 target 字首）；`docs/lore/magic-system.md` §10 若提及則同步。

## 4. 行為測試

- [ ] 4.1 `world/skills/tests/test_sexual_act_effects.py`（既有承載 `_handle_sexual_event` 案的模組）：新增 target 通道案——(a) `divine_sexual_arts` 對單一未抵抗目標施放，`apply_event` 僅以 `"stimulus_applied"` 對目標呼叫、actor 性狀態不變（等值改寫既有 `test_legacy_stimulus_event_stays_target_scoped`，其斷言語意逐字保留）；(b) 唯一目標抵抗成功 → cast 成功、事件未發射、無 `RejectedAction`；(c) 假設性 `sexual_event_target:` AREA 對三個非 actor 目標 → 呼叫三次且不含 actor；(d) `effects=["sexual_event_target:"]` → `EFFECT_RESOLUTION_FAILED`。
- [ ] 4.2 同模組：新增「participant 通道不再有按名特例」案——假設性技能宣告 `sexual_event:stimulus_applied` 並對單一目標施放，斷言 `apply_event` 對**含 actor 在內**的每個 participant 呼叫（證明舊豁免已死）。既有 participant 預設案（`breast_sex_performed` 對 actor＋目標、SELF 案 `masturbation_climax` 恰一次）原樣保留當回歸網。
- [ ] 4.3 同模組：新增 ownership-gated 派生行為案——(a) 新建非悠奈精靈實體：`owned_keys()` 不義 `divine_sexual_arts`、`unlocked_act_keys()` 不含它、直接 cast → `_step1_ownership` 拒；(b) `apply_pleasure_gain` 計數器飽和／注入 `SexualMasteryEffect` 持有者的兩個分支仍不含它；(c) patch preset 授予該 key 後 → `unlocked_act_keys()` 含它且 cast 通過 `_step1_ownership`（授予路徑仍有效）。
- [ ] 4.4 抵抗閘行為案（併入 4.1 所在模組或 `world/rules/tests/` 既有 cast-wiring 模組）：(a) `divine_sexual_arts` 的 cast 產生一條 `sexual_resist` EventLog entry（證明已進冊、閘門開火）；(b) 非神性血統持有者施放 → `_step1_divine_arts_gate` 先拒、抵抗擲骰未發生（patch `resist_verdict` 斷言未被呼叫）。
- [ ] 4.5 `world/rules/tests/test_cast_settlement*` 性脅迫掃描面：補一條——`divine_sexual_arts` 強迫成功（`resisted=False`、`auto_comply=False`）的結算照既有規則扣 NPC 親和（該招進冊後才可能發生，屬新覆蓋而非回歸）。

## 5. 資料測試（目錄結構與宣稱資料；不與行為測試混置）

- [ ] 5.1 `world/skills/sexual_acts/tests/test_registry_structure.py`：`check_registries_agree` 的排除常數從三項縮為 `{"divine_sexual_mastery", "reincarnation_boon_yuna"}`；新增負向案——假設性只存在於 `SKILL_REGISTRY` 的半移籍狀態下比對失敗並具名 `divine_sexual_arts`（證明它不再被排除集合掩護）。
- [ ] 5.2 同模組：新增第八對結構案——`DIVINE_ACTS` 含 key `divine_sexual_arts` 且欄位符合 spec（`requires_divine_arts=True`、`ownership_gated=True`、`unlock={}`、`target_part=None`、`resistible=True`、計數器全空、effects 恰 `["sexual_event_target:stimulus_applied"]`）；前七對逐對不變；順帶釘該對的 `base_pleasure` 未被任何 effect 字串引用（佔位欄位）。
- [ ] 5.3 同模組：刪除 `LegacyTargetScopedEventTests`，改寫為「`_builder` 命名空間無 `_LEGACY_TARGET_SCOPED_EVENTS`、`_FORBIDDEN_SEXUAL_EVENTS` 仍存在且內容不變」的結構斷言。
- [ ] 5.4 同模組：新增持有面唯一性案——展平 `PLAYER_PRESET_REGISTRY` 每個 preset 的 `active_skills` ＋ `passive_skills`（對現存 registry 做掃描完整性計數校驗），斷言宣稱 `divine_sexual_arts` 者恰為 `yuna_darknight` 一個；另以 `patch.dict` 注入假設性第二宣稱者，斷言測試邏輯失敗並具名兩者。
- [ ] 5.5 同模組：`OwnershipDriftGuardTests::_SEED_KEYS` 的計算式改為「`unlock` 為空**且非 `ownership_gated`**」（第八招不入無條件持有預期集合）；既有七 seed 案全部原樣通過即為回歸證明。
- [ ] 5.6 `world/lore/tests/test_player_presets.py`：kit-validation 面順帶覆蓋第八招——該 key 現在由目錄安裝，`_validate_preset_skill_kits` 的 kind／divine 閘門校驗路徑不變；斷言悠奈 kit 展平後含該 key 且其精靈血統通過 `can_use_divine_arts` 校驗。
- [ ] 5.7 確認 `.github/evennia-shards.json` 零變動（所有測試皆擴充既有已註冊模組），跑 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract`。

## 6. 驗證、文件與 sync 尾步

- [ ] 6.1 焦點測試綠：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.skills world.skills.sexual_acts world.rules world.lore web.webclient`（先最小標籤集；必要時一次 `--parallel 16 --noinput` 全跑）。
- [ ] 6.2 `uv run --locked python -m tools.observability_lint check` 綠（本次無新 logging 面，保持綠即可）；`uv run --locked python -m compileall -q world typeclasses commands server` 綠；`git diff --check` 乾淨。
- [ ] 6.3 `openspec validate integrate-divine-sexual-arts-catalog --strict` 綠。
- [ ] 6.4 archive+sync 落地後（main specs 出現 RENAMED 新 slug、舊 slug 消失）：把 5 處 annotation re-point 到以下精確 slug（已用 `tools.spec_traceability.normalize_requirement_name` 對 delta TO-heading 算證）——`test_registry_structure.py:689` → `sexual-act-registry::sexual-act-registry-s-keys-and-skill-registry-s-sexual-act-categorised-keys-agree-exactly-modulo-the-two-named-mastery-exclusions`；`test_sexual_act_effects.py` 758/771/775 → `sexual-act-effects::sexual-event-target-name-applies-the-named-event-to-the-resolved-targets-only`（原 legacy target-scoped 三案等值改寫為 target 通道案），790 → `sexual-act-effects::sexual-event-name-entries-resolve-through-the-participant-scoped-handler-with-no-name-based-exception-table`（「特例表已死」案）。跑 `uv run --locked python -m tools.spec_traceability check` 綠（無 unknown ID、無新缺口）才算收工。
