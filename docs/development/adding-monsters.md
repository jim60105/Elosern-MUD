# 新增魔物指南

本指南說明一隻魔物從設計文件到 `master` 的工程步驟，範圍限於資料與證據。創作面的規範寫在 [魔物創作傾向指南](/lore/monster-creation-guidelines)，本指南只引用它，不重複它的判斷。

新增魔物同時要滿足內容審查與資料閉合。內容審查決定這隻生物該不該存在、公開文字怎麼寫；資料閉合決定 registry 裡的每個鍵（`key`）是否都有圖鑑段落、審查紀錄、代表煙霧與證據檔。測試只檢查後者的集合關係，不檢查數值本身。

本文假設你已讀過下列文件。

- [魔物創作傾向指南](/lore/monster-creation-guidelines)（`### Documenting a species`、`### Test authoring boundaries`、資源技能與套組配置）
- [魔物資料模型設計](/superpowers/specs/2026-10-05-monster-data-model-design)（物種、變體、個體與委託的資料責任）
- [新增魔法指南](/development/adding-spells)（技能宣告、效果字串、buff 三件套）
- [Evennia 測試效能優化指南](/development/evennia-testing-guide)（shard manifest、data-contract seed 流程）
- [魔物戰鬥 AI 調校](/development/monster-ai)（決策模式、智慧、調校指紋）

---

## 1. 背景：一隻魔物的資料住在哪

### 物種與變體

兩份宣告都在 `world/lore/monster_species.py`，匯出成唯讀 proxy。

`MonsterSpecies` 帶的是身分與公開敘述，欄位依序為 `key`、`display_name_zh`、`published_description_zh`、`published_appearance_zh`、`published_ecology_zh`、`habitat_tags`、`author_hidden_truth_zh`、`author_explanation_zh`、`author_conjecture_zh`、`default_variant_key`、`ordinary_variant`。

`MonsterVariant` 是一筆完整獨立記錄，沒有父鍵或覆寫鏈。欄位為 `key`、`species_key`、`display_name_zh`、`description_zh`、`threat_tier`、`ordinary_variant`、`combat_profile`、`danger_grade`、`profile_required`、`active_skill_keys`、`passive_skill_keys`、`behaviour_profile_key`。

`MonsterCombatProfile` 的七個值 `hp`、`mp`、`sp`、`atk_phys`、`agility`、`defense`、`magic_power` 必須全填或全不填。整份檔案載入時呼叫 `validate_monster_species_registry`，檢查鍵的擁有權、`default_variant_key` 是否真的屬於該物種、棲地標籤是否存在、每個 profile 值是否在宣告階級的帶內，以及 grade 是否在該階級的 guild 段位範圍內。

現行四階的帶與段位如下。

| 階級鍵 | 顯示 | 段位範圍 | HP 帶 |
| --- | --- | --- | --- |
| `low` | 低階 | F–E | 25–70 |
| `mid` | 中階 | D–C | 110–230 |
| `high` | 高階 | B–A | 300–750 |
| `calamity` | 災厄級 | S | 1200 以上 |

### 技能

魔物專屬技能宣告在 `world/skills/registry/data_monster_abilities.py`，由 `assembly.py` 統一掛載。每筆宣告都帶 `SkillEligibility(allowed_actor_kinds=("monster",), allowed_species=("<物種鍵>",))`，`allowed_species` 填技能所屬物種的鍵，不是變體鍵。獨立技能宣告 `prerequisites=()`。

效果字串的語法、`EffectPolicy` 的受眾與命中相依規則，見 [新增魔法指南](/development/adding-spells)。幾個魔物常用的組合寫在該文 §2.6。

### 規則書與敘述

技能之外，含 buff 的效果要同時補三份規則書與一份敘述。

| 檔案 | 補什麼 |
| --- | --- |
| `world/rules/rulebook/buffs.yaml` | 一列 buff，含 `duration`、`stacking`、`polarity`、`modifiers` |
| `world/rules/rulebook/combat_modifiers.yaml` | `buff_active` 列，寫實際的數值效果 |
| `world/rules/rulebook/status_display.yaml` | 一列顯示資料，含 `code`、`label`、`severity` |
| `world/skills/narration/data_<element>.py` | 該技能的敘述列；無元素的身體動作寫在 `data_martial.py` |

`status_display.py` 採 fail-closed 設計，新 buff 的鍵沒有對應顯示列會讓模組載入失敗。`test_narration_coverage` 斷言敘述目錄的鍵集合等於出貨中的主動技能集合，少一列就失敗。

### AI 綁定

唯一來源是 `world/rules/rulebook/monster_behaviour.yaml`。變體用 `behaviour_profile_key` 指向 `archetypes` 之一，該原型提供 `target_strategy`、`flee_hp_fraction` 與 `decision_mode`。

兩個永久模式是 `reflex`（本能模式）與 `deliberation`（權衡模式）；舊名稱 `legacy`、`utility` 不被接受，也沒有別名。只有當變體的有效決策模式是 `deliberation` 時，才需要在 `variant_intelligence` 宣告智慧值，並在 `variant_decision_mode` 宣告 `deliberation`。沒有覆寫的變體沿用原型的模式（原型未宣告時即為 `reflex`）。

`skill_choice: highest_expected_damage` 的原型必須另外宣告 `reflex_temperature`：一個有限正數，單位是原始輸出估算 `E = A × c × R`，初始調校值為 `10.0`，不是固定正確常數，也不是百分比。`first_owned` 的原型可以省略它。這個值只影響本能模式的抽樣，權衡模式永遠用自己的智慧溫度。

任何新增的 buff、modifier 或模式覆寫都會改變調校指紋。`docs/development/monster-ai-activation-evidence/activation.json` 記錄的是舊指紋，測試會比對，因此要一併重生。

### 放置

`world/lore/monster_placement.py` 提供四種宣告。

- `EcologyZone`，有界矩形與稀疏族群預算。
- `EncounterComposition(key, activity_key, members)`，一筆完整遭遇。
- `CompositionMember(variant_key, minimum, maximum)`，組成中的一個變體列。
- `MonsterSite`，手動據點，欄位為 `key`、`kind`、`region_key`、`coordinates`、`composition_key`、`activity_key`、`capacity`、`one_shot`、`recover_after_ticks`、`individual_name_zh`。

`one_shot=True` 的據點不得宣告回復條件。`individual_name_zh` 只用於「任何合法結果都恰好一名個體」的據點，是據點在個體建構時給牠的個體名，不是身分，長度上限為 `MONSTER_NAME_MAX_CODE_POINTS`（5 個字元）。物種與變體的 `display_name_zh` 也受同一上限約束。未命名個體的 `key` 是物種名，變體名不再當作名字。高階變體不得納入常態區域池。

---

## 2. 事前決定

動手前先回答五個問題，答案決定後面要改哪些檔案。

| 問題 | 影響 |
| --- | --- |
| 新物種，還是既有物種的新變體 | 新物種要多一筆 `MonsterSpecies`；新變體要多一筆 `MonsterVariant`，並把 `species_key` 指向父物種 |
| 新技能簽章，還是沿用既有群組 | 影響代表煙霧模組。代表者的推導規則是同簽章群組內排序最小的鍵 |
| 屬於哪個階級與 grade | profile 值必須在該階級帶內，grade 必須在該階級段位範圍內 |
| 決策模式走 `reflex` 還是 `deliberation` | 帶支援型主動技能的變體必須綁 `deliberation`，本能決策不會提出支援技能 |
| 放置方式是區域池、手動據點，還是一次性 boss 據點 | 三者的宣告檔案與生命週期不同 |

技能的「簽章」由變體的主動與被動技能列的宣告順序導出，每一項記為 `(slot, effect family, audience, hit-dependency index)`。兩隻變體只要這個序列相同，就歸入同一個群組。

---

## 3. Step by Step

### Step 0，從設計文件取得內容與角色

從設計文件取出物種與變體的公開敘述、kit 表、tier 與 grade。數值由你依現行階級帶與成本邊界選定，寫進宣告一次，不另建審核表。設計文件沒寫的能力不要自行補上。

### Step 1，寫入物種與變體列

在 `_SPECIES_DECLARATIONS` 追加 `MonsterSpecies(...)`，在 `_VARIANT_DECLARATIONS` 追加 `MonsterVariant(...)`。三個作者私有欄位都要有內容，`author_hidden_truth_zh` 記下保留的起源邊界。

```python
MonsterVariant(
    "mudbank_dweller",
    "mudfilm_slime",
    "濕岸型",
    "普通版本，貼著濕地起伏活動。",
    "low",
    True,
    MonsterCombatProfile(
        hp=34, mp=12, sp=16, atk_phys=4, agility=3, defense=5, magic_power=0
    ),
    "F",
    True,
    active_skill_keys=("mudfilm_guard",),
    behaviour_profile_key="instinctive",
),
```

改完先確認載入成功，這一步會找出大部分宣告錯誤。

```sh
uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY; print(len(MONSTER_VARIANT_REGISTRY))"
```

### Step 2，宣告技能

在 `data_monster_abilities.py` 追加技能。`usable_out_of_combat` 要顯式寫，預設值會讓新技能歸入「未決定」集合。含支援效果的主動技能填 `False`，並在 `world/skills/tests/_support.py` 的 `USABLE_OUT_OF_COMBAT_FALSE_KEYS` 補上該鍵。

```python
_skill(
    "mudfilm_guard", "泥膜收束", "收緊泥膜護住身體。",
    SkillKind.ACTIVE, TargetSpec.SELF,
    cost={"sp": 6},
    usable_out_of_combat=False,
    effects=["self_buff_apply:mudfilm_shell"],
    category=SkillCategory.MARTIAL_ARTS,
    faction_constraint=FactionConstraint.SELF_ONLY,
    eligibility=SkillEligibility(
        allowed_actor_kinds=("monster",),
        allowed_species=("mudfilm_slime",),
    ),
    prerequisites=(),
    effect_policies=(EffectPolicy(coefficient=1.0, audience=EffectAudience.SELF),),
),
```

### Step 3，補規則書與敘述

依 Step 1 選定的效果補 `buffs.yaml`、`combat_modifiers.yaml`、`status_display.yaml`，再補一格敘述列。三份規則書的鍵必須一致，缺一會在載入期失敗。

### Step 4，綁定 AI 並重生指紋

在 `monster_behaviour.yaml` 補 `variant_intelligence` 與 `variant_decision_mode`（僅 `deliberation` 需要），確認 `behaviour_profile_key` 指向存在的原型；若該原型是 `highest_expected_damage`，確認它宣告了 `reflex_temperature`。接著重生指紋相關證據。

```sh
uv run --locked python tools/monster_ai_manual_reports.py selector
```

`selector` 產生 `docs/development/monster-ai-manual-evidence/selector-check.json` 與 `.md`。`activation.json`、`focused-tests.txt`、`gates.txt` 的更新方式見 [魔物戰鬥 AI 調校](/development/monster-ai)。

### Step 5，寫圖鑑段與審查紀錄

在 `docs/lore/bestiary.md` 的概覽表加一列，並在對應階級段落加 `### <公開名稱>` 與 ` ```bestiary ` 索引區塊。索引要寫 species、parent-species、default-variant、每個變體與其狀態、本段記錄的公開欄位。

在 `docs/development/bestiary-editorial-review.md` 加一列，欄位為 species 鍵、reviewed 日期、生態敘述、能力邊界、歷史與現行分離、結論。兩份文件由 `world/lore/tests/test_bestiary_documentation.py` 做雙向覆蓋與集合相等檢查，缺一就失敗。

### Step 6，補代表煙霧模組

每個技能簽章群組需要恰好一支已提交的代表煙霧模組。模組在 `world/rules/tests/` 下，模組層級宣告代表者。

```python
REPRESENTATIVE_VARIANT = "mudbank_dweller"
```

檢查程式會掃描該目錄下的測試檔，找出所有 `REPRESENTATIVE_VARIANT` 指派，再與推導出的代表者比對。代表者是群組內排序最小的鍵，因此新變體加入既有群組時，代表者可能換人。這種情況要新增一支煙霧模組，或把既有的那一支改成新的代表者，宣告與建構都要指向新的代表者，個體用 `construct_species_individual` 建出。

模組第一行寫 `Data-contract test: <理由>`，並在 `tools/test_data_lint_seed.json` 登記。

### Step 7，登記清單

新增的測試模組要登記在 `.github/evennia-shards.json`，且只屬於一個 shard。新增的 data-contract 模組依序更新 seed 與帳本。

```sh
uv run --locked python -m tools.test_data_lint seed
uv run --locked python -m tools.test_data_lint check
```

只改 seed 或只改帳本都會以 `seed-mismatch` 失敗，帳本不要手改。

### Step 8，重生參照雜湊

`content/map-reference-context.json` 記錄 `world/lore` 與 `world/rules` 每個檔案的雜湊。改過這兩個目錄的任何檔案後重生。

重生也會一併更新地圖編輯器的怪物生成圖層，讓它顯示最新的生態區與生成點。

```sh
uv run --locked python -m tools.map_reference_context
```

### Step 9，驗證

```sh
# 載入期驗證
uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"

# 聚焦測試，label 換成你改到的模組
uv run --locked --env-file=<file> evennia test --settings test_settings.py --keepdb \
  world.lore.tests.test_monster_species_content \
  world.lore.tests.test_bestiary_documentation \
  world.rules.tests.test_monster_composition_coverage \
  world.skills.tests.test_skill_registry.test_out_of_combat_policy

# 契約與規格
uv run --locked python -m tools.contract_gate --change <change>
uv run --locked python -m tools.spec_traceability check
uv run --locked openspec validate <change> --strict
```

`<file>` 是含有 `MUD_TEST_SETTINGS=1` 的 env 檔，`--env-file` 用單一 token 形式。`contract_gate --change` 只在功能 worktree、尚未 sync 之前使用。

---

## 4. 載入期驗證器總表

| 驗證器 | 觸發位置 | 檢查出的問題 |
| --- | --- | --- |
| `validate_monster_species_registry` | `monster_species.py` 載入 | 鍵重複、父物種不存在、default variant 不屬於該物種、棲地標籤未知、profile 值超出階級帶、grade 超出段位範圍、`profile_required=True` 卻缺欄位 |
| `validate_ecology_registries` | `monster_placement.py` 載入 | 區域矩形或棲地未知、composition 未命名、成員變體不存在、池的重複鍵 |
| `validate_monster_placement_registry` | `monster_placement.py` 載入 | 據點座標或區域未知、composition 未命名、成員數超過 capacity、一次性據點宣告了回復條件、多名個體的據點掛了單一個體標籤 |
| `validate_catalog` | `world/skills/narration/catalog.py` 載入 | 敘述列缺漏、行長超出上限、kind 名稱未知 |
| `status_display` 載入檢查 | `world/rules/status_display.py` 載入 | buff 的鍵沒有對應顯示列 |
| `SkillDef.__post_init__` | 技能建構 | 效果字串前綴無法解析、目標形狀與效果不一致 |
| `SkillEligibility` 驗證 | registry 載入 | 物種或變體鍵不存在、資格組合無法滿足 |

---

## 5. 常見錯誤

新變體沿用既有技能簽章，且鍵的排序在前面時，代表者會換人。原本那支煙霧模組變成 stray，新的代表者沒有模組，`test_every_group_has_exactly_its_representative_committed` 直接失敗。

`usable_out_of_combat` 留空，新技能以預設值歸入 `False` 集合，凍結清單比對回報 `extra`。這個情況在 `mudfilm_guard` 首次加入時發生過。

新增 buff 後只改 `buffs.yaml`，忘了 `combat_modifiers.yaml` 或 `status_display.yaml`。前者的效果不會生效，後者讓模組載入失敗。

改了 `monster_behaviour.yaml` 卻沒有重生證據。測試以 `activation.json` 的舊指紋與行程載入的新指紋比對，會在指紋比對處失敗。

圖鑑寫了段落但漏了 ` ```bestiary ` 索引，或索引寫了不存在的變體。雙向覆蓋會指名缺漏的鍵與關係。

`individual_name_zh` 宣告在會產生多名個體的 composition 上，或名字超過 5 個字元。載入期驗證直接拒絕。

只改 seed 沒重生帳本，或手改帳本。`test_data_lint check` 以 `seed-mismatch` 失敗。

---

## 6. 移除一隻魔物

移除比新增多一層風險，因為引用會在載入期就失敗，而不是等到某支測試。依下列順序處理。

1. 先搜尋引用，`EcologyZone` 的池、`EncounterComposition` 的成員、`MonsterSite` 的 composition 都要處理。
2. 移除圖鑑段與概覽列，移除審查紀錄列。兩邊的集合相等檢查會失敗，直到你同步兩邊。
3. 移除代表煙霧模組，或把它改指向同群組的新代表者。
4. 移除技能列、敘述列、三份規則書列，並從 `USABLE_OUT_OF_COMBAT_FALSE_KEYS` 刪除該鍵。
5. 移除 `variant_intelligence` 與 `variant_decision_mode` 條目，重生指紋與選擇器證據。
6. 移除 shard 與 seed 登記，重生帳本與 `content/map-reference-context.json`。
7. 每刪完一輪就匯入一次 registry，讓載入期驗證告訴你下一個漏掉的引用。

```sh
uv run --locked python -c "from world.lore.monster_placement import MONSTER_SITE_REGISTRY; from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"
```

刪除不會讓測試變寬鬆。集合相等、雙向覆蓋、代表者推導與凍結清單都會依刪除後的宣告重新計算。

---

## 7. 範圍外

災厄級魔物的內容與新文明種族的設計需要另外的審查，不套用本指南的預設值。新的戰鬥機制、新的效果前綴、新的決策模式屬於規則層變更，先更新對應的設計文件與規格，再依本指南的步驟處理。
