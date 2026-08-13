# 新增魔法指南

本指南說明如何為 Elosern 加入一個新的魔法。以目前八屬性×五位階、共 80 個魔法的目錄為基準，說明新增或調整魔法時的完整流程：從設計文件出發、寫入 `SKILL_REGISTRY`、處理 buff、補測試，再到 OpenSpec 工件同步與驗證。

本文假設你已讀過：

- `docs/superpowers/specs/2026-08-12-skill-system-redesign-design.md`（§4.3 MP 成本位階表、§4.4 魔法目錄、§9 測試約定）— 這是魔法內容的**唯一來源**，所有數值不得自行發明
- `openspec/specs/skill-registry/spec.md`（registry 契約與各元素魔法集合需求）
- 已落地的範例：`openspec/changes/archive/2026-08-13-spell-catalog-fire/` 以及後續的 `spell-catalog-water/earth/...` 系列

---

## 1. 背景：一個魔法如何運作

魔法是 `world/skills/registry.py` 中 `SKILL_REGISTRY` 字典裡的 `SkillDef`。結構上的重點：

- **純資料、不可變**：`SkillDef` 是 frozen dataclass，`cost`／`effects` 都是不可變集合；`SkillDef.__post_init__` 會在建構時解析每個 `effects` 字串（無法辨識的前綴直接拋錯，registry 載入即失敗）。
- **沒有 tier 欄位**：位階由 registry 位置與 MP 成本帶推導（`world/skills/cost_tiers.py::spell_tier_for`），再交給 `world/rules/progression.py::can_cast_spell_tier` 施放門檻使用。
- **效果字串是型別化契約**：所有效果前綴在 `world/skills/effects.py` 有對應的 typed dataclass。魔法會用到的前綴：

| 前綴 | 語法 | 說明 |
|---|---|---|
| `damage` | `damage:<element>:<school>` | 造成傷害，`<school>` 為 `physical`／`magic`；字串**不含數值**，量級由戰鬥公式依施法者數值推導 |
| `heal` | `heal:single`／`heal:area` | 恢復 HP；形狀必須與 `TargetSpec` 相符（`single` 只能配 `SINGLE`／`SELF`，`area` 只能配 `AREA`，否則建構即失敗） |
| `self_heal` | `self_heal` | 恢復自身 HP |
| `cleanse` | `cleanse:status` | 解除目標所有 debuff 極性 buff |
| `buff_apply` | `buff_apply:<buff_key>` | 對每個目標套用 `buffs.yaml` 中定義的 buff |
| `self_buff_apply` | `self_buff_apply:<buff_key>` | 只對施法者套用 buff（本質上自我限定，見 §4.3） |
| `movement` | `movement:flight`／`movement:flash_step` | 移動豁免，只用在 PASSIVE 技能（`flight`） |

- **元素**：`element` 欄位是 `world.lore.elements.ELEMENT_REGISTRY` 的 key：`fire`、`water`、`wind`、`earth`、`lightning`、`ice`、`light`、`dark`。

---

## 2. 事前決定：這個魔法是哪一種形狀？

新增前先回答三個問題，決定寫法：

| 問題 | 答案 | 寫法 |
|---|---|---|
| 屬於某元素的 ACTIVE 魔法，`FactionConstraint` 為 `ANY`？ | 是（絕大多數） | 放進該元素的 `*_elemental_spells(...)` builder 區塊 |
| 效果本質上只作用於自己（`self_buff_apply` 等）？ | 是 | 以個別 `_skill(...)` 宣告並設 `faction_constraint=FactionConstraint.SELF_ONLY`（builder 固定 `ANY`，不能用） |
| 是 PASSIVE 技能（如 `movement:flight`）？ | 是 | 以個別 `_skill(...)` 宣告，`kind=SkillKind.PASSIVE`，不進 builder |

> [!NOTE]
> 主規格 `skill-registry` 規定：效果本質上自我限定的技能 SHALL 宣告 `SELF_ONLY`。既有的 `hardened_skin`（土）、`gale_step`（風）、`static_ward`／`thunder_gods_haste`（雷）都是個別宣告的前例。

---

## 3. Step by Step

### Step 0 — 從設計文件取得數值

在 `2026-08-12-skill-system-redesign-design.md` §4.4 的魔法目錄中挑出（或新增）該魔法的：key、名稱（正體中文）、位階、目標、效果描述、MP。**不要自己發明數值**；若要新增表格外內容，先更新設計文件。

MP 必須落在 §4.3 的對應位階成本帶內：

| 位階 | 等級區間 | 單體／直接效果 MP | 範圍／強效 MP |
|---|---|---|---|
| 學徒 | 0–15 | 10–16 | 14–20 |
| 術師 | 16–30 | 20–28 | 26–34 |
| 大師 | 31–70 | 35–48 | 45–60 |
| 賢者 | 71–90 | 65–85 | 80–110 |
| 主宰 | 90+ | 120–150 | 140–180 |

`spell_tier_for` 會先看「目標形狀對應的欄位」（`AREA` 看範圍欄、其餘看單體欄），成本若落在同一位階的另一欄也算該位階（例如 `dust_veil` 範圍 MP 22 落在術師單體帶）——這是目錄的刻意設計。

### Step 1 — 對照目標欄位

| 設計文件目標欄 | `TargetSpec` | `FactionConstraint` |
|---|---|---|
| 單體 | `TargetSpec.SINGLE` | `FactionConstraint.ANY` |
| 範圍 | `TargetSpec.AREA` | `FactionConstraint.ANY` |
| 單體(自) | `TargetSpec.SELF` | `FactionConstraint.SELF_ONLY` |
| 範圍(友) | `TargetSpec.AREA` | `FactionConstraint.ANY` |

「(友)」只是文案上的友善限定，registry 沒有 ally-only 機制，維持 `ANY`。

### Step 2 — 寫入 registry

在 `world/skills/registry.py` 的 `SKILL_REGISTRY` 字典 literal 中，找到該元素的 `*_elemental_spells(...)` 區塊（若沒有就先建一個），以五行成對註解（`# 火 — 學徒`）分組。builder 的 row 格式是 `(key, label, description, target_spec, mp, effects)`：

```python
*_elemental_spells(
    "fire",
    # 火 — 學徒
    ("fire_ball", "火球術", "凝聚火焰魔力，對單一目標造成魔法傷害。", TargetSpec.SINGLE, 14, ("damage:fire:magic",)),
    # 火 — 術師
    ("scorching_wave", "灼熱波動", "釋放灼熱的波動，對單一目標造成魔法傷害並使其灼燒。", TargetSpec.SINGLE, 24, ("damage:fire:magic", "buff_apply:fire_scorch")),
    ...
),
```

`_elemental_spells(element, *rows)` 會固定 `SkillKind.ACTIVE`、`FactionConstraint.ANY`、`cost={"mp": <mp>}`，元素只寫一次。

### Step 3 — 特殊案例

**自我限定（SELF_ONLY）**：寫成個別 `_skill(...)`，放在該元素 builder 區塊之後、同一階層註解之下：

```python
# 土 — 學徒
# hardened_skin is inherently self-only (`self_buff_apply`), so it declares
# SELF_ONLY — the `_elemental_spells` builder fixes ANY, so this single entry
# is written out individually per the skill-registry spec's self-only constraint.
_skill(
    "hardened_skin",
    "硬化肌膚",
    "使自身肌膚硬化如岩，提升防禦。",
    SkillKind.ACTIVE,
    TargetSpec.SELF,
    cost={"mp": 10},
    element="earth",
    faction_constraint=FactionConstraint.SELF_ONLY,
    effects=["self_buff_apply:earth_hardened_skin"],
),
```

**PASSIVE 技能**：`flight` 是唯一前例——保持既有 `_skill(...)` entry、`kind=SkillKind.PASSIVE`，cost 只是顯示用途（PASSIVE 不會走資源扣減），且**不列入**可施放位階的測試配對。

**重新調整既有魔法（recost）**：直接改該 entry 的 cost，**不要複製一份**。若它原本是獨立 `_skill(...)`，可像 `fire_ball`、`wind_blade` 那樣遷入 builder 區塊並刪除舊 entry（key 仍只出現一次）。改完記得搜尋是否有測試或程式碼鎖死了舊 MP。

### Step 4 — 處理 buff

若魔法帶有 `buff_apply:`／`self_buff_apply:` 效果：

1. **`world/rules/rulebook/buffs.yaml`** 加一列。`modifiers` 只能用 `rate`／`bounds`／`decay` 三個 key；`polarity` 為 `buff`（增益）或 `debuff`（減益）：

```yaml
- key: water_bind
  duration: 30
  stacking: refresh
  polarity: debuff
  modifiers: {}
- key: dark_corrosion
  duration: 300
  tick_interval: 10
  stacking: refresh
  polarity: debuff
  modifiers:
    rate: {target: hp, delta: -5}
```

> [!WARNING]
> `rate` 的 `target` 只能是 gauge trait（`hp`／`mp`／`sp`，見 `world/rules/traits.py::GAUGE_KEYS`）；tick 時對其他目標套 `rate` 會直接拋 `NotImplementedError`。敏捷、防禦、命中這類調整請用 `bounds: {target: <trait>, ceiling: <delta>}`（目前為惰性的前向宣告，無 consumer）。

2. **`world/rules/rulebook/status_display.yaml`** 必須加一列對應的顯示資料（label 為正體中文、`severity` 為 `beneficial`／`informational`／`warning`／`harmful`／`critical`）——`status_display.py` 是 fail-closed 的，新 buff key 沒對應顯示列會讓模組載入失敗：

```yaml
- code: water_bind
  label: 束縛
  severity: harmful
```

3. 能沿用既有 buff（如 `paralysis`、`fear`）就沿用，不要重複定義。

### Step 5 — 補測試

測試與行為同步落地，位置與風格對齊 `spell-catalog-*` 系列：

1. **`world/skills/tests/test_registry.py`**：定義 `WATER_SPELL_CATALOG` 形式的 tuple，並加三個測試：
   - `test_all_ten_<element>_spells_declare_the_exact_catalog_fields` — 逐一斷言 label、kind、element、target、faction、cost、effects
   - `test_every_<element>_spell_effect_round_trips_through_typed_dispatch` — 每個 effect 字串經 `parse_effect` 得到正確的 typed dataclass 且存在於 `parsed_effects`
   - `test_<element>_active_spell_keys_are_exactly_the_catalog_set` — 精確 key 集合（元素已有其他 ACTIVE 技能時記得納入，例如 光含 `light_sword_style`、暗含 `shadow_slash`／`dual_blade_mastery`）
2. **`world/rules/tests/test_progression.py`**：在 `ElementMasteryGateTests` 加 `test_<element>_spell_tier_boundaries_reject_without_mastery_and_permit_with_it`——四階層門檻（15/16、30/31、70/71、90/91）與 mastery 覆寫；PASSIVE 技能不放進 `spell_tier_for` 配對。
3. **`world/rules/tests/test_buffs.py`**：每個新 buff key 恰好一個 `test_buff_<key>`（`buff-handler-integration` 規格有機械式對應檢查）；DoT buff 要實際 `tick_buffs` 驗證扣血。
4. **traceability 標註**：上述測試以 `tools.spec_traceability.covers_requirement` 標註需求 ID（如 `skill-registry::skill-registry-contains-the-full-水-element-spell-set`）。ID 用 `uv run --locked python -m tools.spec_traceability list` 取得，不要手造。

### Step 6 — 同步 OpenSpec 工件

魔法內容經由 `openspec/changes/spell-catalog-<element>/` 變更落地（見 `.agents/skills/openspec-*` 系列 skill）：

1. 讓 `proposal.md`／`design.md`／`specs/skill-registry/spec.md`／`tasks.md` 彼此一致（含 `status_display.yaml` 列數、SELF_ONLY 決策、recost 說明）。
2. 實作完成後把 delta spec 同步進主規格 `openspec/specs/skill-registry/spec.md`（每元素一個 Requirement 區塊＋情境）。
3. 逐項打勾 `tasks.md`；驗證全綠後再 archive。

### Step 7 — 驗證

```sh
# 單元級（快速迭代）
MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.skills.tests.test_registry world.rules.tests.test_progression world.rules.tests.test_buffs world.rules.tests.test_status_display

# 載入即驗證所有 effect 字串可解析
uv run --locked python -c "from world.skills.registry import SKILL_REGISTRY"

# 規格與測試追溯
uv run --locked python -m tools.spec_traceability check
openspec validate <change> --strict

# 完整套件（handoff 前）
MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb --noinput --parallel 16 commands server typeclasses world web.webclient
uv run --locked python -m unittest discover -s tests -t .
openspec validate --all --strict
```

---

## 4. 檢查清單

- [ ] 數值（key／名稱／位階／目標／MP／效果）與設計文件 §4.4 完全一致
- [ ] MP 落在 §4.3 對應位階成本帶（含 opposite-column 前例）
- [ ] 效果字串全部能通過 `parse_effect`（載入即失敗的契約）
- [ ] `heal:single` 只配 `SINGLE`／`SELF`；`heal:area` 只配 `AREA`
- [ ] 自我限定效果（`self_buff_apply` 等）宣告 `SELF_ONLY` 且寫成個別 `_skill(...)`
- [ ] PASSIVE 技能不進 builder、不列入可施放 tier 配對
- [ ] 既有技能 recost 是 in-place，key 只出現一次，且無測試鎖死舊 MP
- [ ] 每個新 buff key：`buffs.yaml` 一列 ＋ `status_display.yaml` 一列 ＋ `test_buff_<key>` 恰好一個
- [ ] `rate` 只用在 `hp`／`mp`／`sp`；其餘用 `bounds`
- [ ] label ≤ 128、description ≤ 512 code points（`LABEL_MAX`／`DESCRIPTION_MAX`）
- [ ] 測試帶 `covers_requirement` 標註且 `spec_traceability check` 0 errors
- [ ] `openspec validate --all --strict` 全過；`git diff --check` 乾淨

---

## 5. 常見陷阱

- **把 SELF_ONLY 技能塞進 builder**：builder 固定 `ANY`，違反主規格的自限契約（`hardened_skin` 曾因此在 rubber-duck 審查被擋下）。
- **`rate` 用在非 gauge trait**：tick 時拋 `NotImplementedError`，會炸掉世界時鐘的 buff 結算。
- **新 buff key 漏掉 `status_display.yaml`**：模組 import 直接失敗（fail-closed），不是執行期警告。
- **效果字串帶數值**（如 `damage:fire:magic:50`）：`damage` 語法就是三段，量級由公式推導；帶數值會在建構時被拒。
- **位階註解與成本帶不一致**：`spell_tier_for` 只看 MP 成本帶，註解寫錯位階會誤導後續維護者與門檻測試。
