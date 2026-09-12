# Tasks: integrate-divine-sexual-arts-catalog

追蹤性前置：`@covers_requirement` 的 ID 必須存在於 main index（`tools.spec_traceability` 對不存在的 ID 報 `unknown-requirement-id`，與該測是否可執行無關）。本變更兩條 RENAMED（排除集合「three→two named」、effects 的 name-entries 條）sync 後舊 slug 消失、既有 annotation 會孤兒化——re-point 排進第 6 群，作為 archive+sync 落地的**同變更尾步**（先例：`magic-power-static-rename` P.1、repo 26 個 archived RENAMED）。其餘 MODIFIED 全部保留原標題，ID 不動。實作期（sync 前）`check` 以舊 slug 跑綠。

**批次紀律（duck round-2 教訓）**：`_register_rows`（`world/skills/sexual_acts/__init__.py:35-49`）對「key 已在 `SKILL_REGISTRY`」的目錄行直接 `ValueError`——第八對與主冊條目的移除**不可拆成相鄰兩任務**，否則中間狀態 import 必炸。同理，`_handle_sexual_event` 的 legacy 分支刪除必須與該分支的既有行為測改寫**同批落地**。群 1、2 為純增量（紅面零）；群 3 是原子切換點；群 4、5 全在綠色基線上加測。

## 1. 效果通道純增量（只加不刪）

- [ ] 1.1 `world/skills/effects.py`：新增 `TargetSexualEventEffect`（`@dataclass(frozen=True)`，欄位 `event_name: str`，`ActorSexualEventEffect` 的鏡像）＋`parse_effect` 辨識 `sexual_event_target:` 前綴，走既有 `_parse_single_arg`（空／雙 payload 在**解析期**丟 `ValueError`，與 `sexual_event_actor:` 完全同款）。
- [ ] 1.2 `world/skills/tests/test_effects.py`：順接既有 `test_sexual_event_actor_*` 兩案的形制，新增 target 前綴解析案（正常解析、`"sexual_event_target:"`／`":a:b"` 丟 `ValueError`）。跑 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.skills.test_effects`。
- [ ] 1.3 `world/rules/action.py`：新增 `_handle_sexual_event_target`（`surfaces=frozenset({"sexual"})`、無 required event context）——對每個 resolved target stage 一條 `apply_event(target, event_name, ...)` 的 `PendingEffect`，絕不含 actor；空 `targets` 為正常 no-op；不做觀察者閘門。在 `_EFFECT_HANDLERS` 註冊前綴。空事件名不可能到達 handler（解析期已擋）。

## 2. 持有面閘門純增量（65 行零影響）

- [ ] 2.1 `world/skills/sexual_acts/_builder.py`：`SexualActDef`（`_builder.py:79-111`）新增 `ownership_gated: bool = False`，欄位註解說明「解鎖狀態只能由 base 持有提供，派生路徑（計數器、mastery 全解）一律繞過；confer 不是任何招式的取得途徑」。`_act_family` 不參數化。
- [ ] 2.2 `world/skills/sexual_acts/__init__.py::unlocked_act_keys_for`（注意：派生器在此模組，非 `world/rules/sexual_state.py`）：計數分支跳過 `ownership_gated=True`；mastery 分支同樣跳過（一般性規則）。同時更新該函數 docstring 裡「a divine act declaring `unlock={}` stays owned by everyone」一段—— ownership-gated 行是該句的例外。
- [ ] 2.3 群 1＋2 驗證：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.skills world.skills.sexual_acts world.rules`（65 行全 `False`，既有派生測試應全綠）。

## 3. 原子切換（單一批次，紅面只存在於本批內部）

同一批（一個 commit 邊界）內一次完成，結尾全綠：

- [ ] 3.1 `world/skills/registry.py`：移除主冊 `divine_sexual_arts` inline `_skill(...)` 條目。
- [ ] 3.2 `world/skills/sexual_acts/divine.py`：新增第八對 `divine_sexual_arts`（`SkillDef`：`ACTIVE`、`cost={}`、`usable_out_of_combat=True`、`element=None`、`category=SEXUAL_ACT`、`group="神之秘法"`、`requires_divine_arts=True`、effects `["sexual_event_target:stimulus_applied"]`；`SexualActDef`：`ownership_gated=True`、`unlock={}`、`base_pleasure=1`（佔位）、`actor_part=None`、`target_part=None`、`actor_pleasure_ratio=0.0`、計數器全空、`resistible=True`），docstring 七招 → 八招並補 hand-built／ownership_gated／佔位理由。
- [ ] 3.3 `world/rules/action.py::_handle_sexual_event`：刪 `_LEGACY_TARGET_SCOPED_EVENTS` 分支，recipient 恆為 `participants(actor, targets)`；更新文件字串（三通道由前綴決定）。
- [ ] 3.4 `world/skills/sexual_acts/_builder.py`：刪 `_LEGACY_TARGET_SCOPED_EVENTS` 常數與註解；`_FORBIDDEN_SEXUAL_EVENTS` 保留，補註「recipient scope 由前綴決定，與本黑名單無關」。
- [ ] 3.5 `world/rules/tests/test_sexual_act_effects.py`（注意路徑在 `world/rules/tests/`）：`test_legacy_stimulus_event_stays_target_scoped`（:776）等值改寫為 target 通道案——改用 `divine_sexual_arts` 本體：對單一未抵抗目標施放，`apply_event` 僅以 `"stimulus_applied"` 對目標呼叫、actor 性狀態不變。同檔另加「participant 通道無按名特例」案（假設性 `sexual_event:stimulus_applied` → 含 actor 的每個 participant 都吃到，證明舊豁免已死）。既有 participant 預設案與 SELF 案原樣不動當回歸網。
- [ ] 3.6 `world/skills/sexual_acts/tests/test_registry_structure.py`：(a) `check_registries_agree` 排除常數三項縮兩項；(b) **兩處** seed 推導都改成「`not act.unlock and not act.ownership_gated`」——`_SEED_KEYS` 與 `test_owned_keys_resolves_without_a_sexual_attribute`（:897-910 的條列式 comprehension）；(c) 刪 `LegacyTargetScopedEventTests` 與 `:849` 的 disjoint 案，換成「`_builder` 命名空間無 `_LEGACY_TARGET_SCOPED_EVENTS`、`_FORBIDDEN_SEXUAL_EVENTS` 仍存在且內容不變」結構斷言；(d) 新增第八對結構案（欄位照 spec，含 `parsed_effects == (TargetSexualEventEffect("stimulus_applied"),)`、前七對逐對不變、`base_pleasure` 未被任何 effect 字串引用）。
- [ ] 3.7 `world/skills/sexual_acts/tests/test_divine_mutators_catalog.py:98`：`len(DIVINE_ACTS)` 釘選 7 → 8，前七對逐對不變案原樣保留。
- [ ] 3.8 切驗：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.skills world.skills.sexual_acts world.rules world.lore web.webclient` 全綠；`SKILL_REGISTRY` 總數不變、`combat_view.MAX_SKILLS`（192）不動。

## 4. 行為測試（綠色基線上新增）

- [x] 4.1 `world/rules/tests/test_sexual_act_effects.py`：target 通道邊界案——(a) 唯一目標抵抗成功 → cast 成功、事件未發射、無 `RejectedAction`；(b) 假設性 `sexual_event_target:` AREA 對三個非 actor 目標 → 呼叫三次且不含 actor。
- [x] 4.2 同模組或 cast-wiring 模組：ownership 排他三案——(a) 新建非悠奈精靈：`owned_keys()` 無該 key、cast → `_step1_ownership` 拒；(b) 計數器飽和者與注入 `SexualMasteryEffect` 持有者的兩條派生分支仍不含它；(c) **負向**：`patch` 使該 key 只出現在 `conferred_grants()` → `owned_keys()` 仍無它、cast 仍被拒（confer 永遠不是取得途徑）。
- [x] 4.3 抵抗閘案：(a) `divine_sexual_arts` 的 cast 產生一條 `sexual_resist` EventLog entry（閘門開火）；(b) 非神性血統持有者施放 → `_step1_divine_arts_gate` 先拒、抵抗擲骰未發生（patch `resist_verdict` 斷言未被呼叫）。
- [x] 4.4 `world/rules/tests/test_cast_settlement_sexual_coercion.py` 面：用 preset 建構的悠奈當 actor（非假設性合成列）跑 `resisted=False`、`auto_comply=False` 結算，照既有規則扣 NPC 親和（該招進冊後才可能發生，屬新覆蓋）。

## 5. 資料測試（目錄結構與宣稱資料）

- [x] 5.1 同 `test_registry_structure.py`：持有面唯一性案——展平 `PLAYER_PRESET_REGISTRY` 每個 preset 的 `active_skills` ＋ `passive_skills`（掃描完整性計數校驗），斷言宣稱該 key 者恰為 `yuna_darknight`；`patch.dict` 注入假設性第二宣稱者證明邏輯具名失敗。措辭與 spec 同：僅宣稱**authored preset** 面。
- [x] 5.2 同模組：半移籍負向案——只在 `SKILL_REGISTRY` 存在該 key 而目錄缺行時，比對失敗並具名 `divine_sexual_arts`。
- [x] 5.3 `world/lore/tests/test_player_presets.py`：悠奈 kit 展平後含該 key 且其精靈血統通過 `can_use_divine_arts` 校驗（該 key 改由目錄安裝後 kind／divine 閘門路徑不變）。
- [x] 5.4 確認 `.github/evennia-shards.json` 零變動（全部擴充既有已註冊模組），跑 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract`。

## 6. 文件、驗證與 sync 尾步

- [ ] 6.1 文件同步：`docs/lore/skill-trees/sexual-act.md`（及 `light.md`、`magic-system.md` 若有提及）「Legacy 單招」→「悠奈簽名技」；`docs/game/command-reference.md:248-250` 該招的取得描述同步（不再是泛發給血統合格角色）；`world/rules/combat_view.py:35-40` 與 `web/static/webclient/js/elosern/protocol.js:97-100` 的「91…65 招目錄＋pre-existing divine_sexual_arts」註解鏡面改為「66 招目錄」，`MAX_SKILLS = 192` 不動。
- [ ] 6.2 `uv run --locked python -m tools.observability_lint check` 綠；`uv run --locked python -m compileall -q world typeclasses commands server` 綠；`git diff --check` 乾淨。
- [ ] 6.3 `openspec validate integrate-divine-sexual-arts-catalog --strict` 綠。
- [ ] 6.4 archive+sync 落地後（main specs 出現 RENAMED 新 slug、舊 slug 消失）：把以下**精確清單** re-point（已對 delta TO-heading 用 `normalize_requirement_name` 算證）——
  - `world/skills/sexual_acts/tests/test_registry_structure.py:689、:693` → `sexual-act-registry::sexual-act-registry-s-keys-and-skill-registry-s-sexual-act-categorised-keys-agree-exactly-modulo-the-two-named-mastery-exclusions`
  - `world/rules/tests/test_sexual_act_effects.py:758（participant 案）、:771（dispatch 案）、:790（SELF 案）` → `sexual-act-effects::sexual-event-name-entries-resolve-through-the-participant-scoped-handler-with-no-name-based-exception-table`
  - 3.5 改寫出的 target 通道案與「特例表已死」案 → 分別掛 ADDED／RENAMED slug `sexual-act-effects::sexual-event-target-name-applies-the-named-event-to-the-resolved-targets-only` 與上條 participant slug（3.6 刪除的 `:849` 案 annotation 隨測一併消失，不需 re-point）。
  跑 `uv run --locked python -m tools.spec_traceability check` 綠（無 unknown ID、無新缺口）才算收工。
