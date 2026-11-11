# Design

## Context

See proposal.md (Why). Facts at `3756992d`:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS` and `_VARIANT_DECLARATIONS` at import. Bands come from `MONSTER_TIER_REGISTRY`: low HP 25–70, attack 3–12, agility 3–12, defense 2–8, grades F–E; mid HP 110–230, attack 18–28, agility 10–24, defense 10–16, grades D–C; high HP 300–750, attack 26–40, agility 16–30, defense 18–32, grades B–A. `magic_power` must be 0 and MP/SP have no band. Display names are limited to 5 code points (`MONSTER_NAME_MAX_CODE_POINTS`).
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」 and `author_conjecture_zh` to contain 「尚未證實」, and it forbids registry strings that name a skill, behaviour or trait key.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by `(slot, effect family, audience, requires_hit_from)` and requires one committed representative per group, the group's sorted-minimum key. This kit's signature is `(("active", "damage", "enemies", None), ("active", "buff_apply", "enemies", 0))`, the shipped enemy hit-rider group, whose representative `cliff_stepper` is declared in `world.rules.tests.test_sway_whistle_sparrow_resource_skill`. Every new variant key sorts after `cliff_stepper`, so the representative does not move and no smoke module, shard entry or seed entry is added. `EnemyRiderGroupMemberTests` in that module derives the group's members from the shipped declarations, so both new variants are exercised on their own rider axis without a test edit.
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests` requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, a magic tier for elemental MP skills (MP 10–16 single, 14–20 area) and `None` otherwise. `validate_catalog` requires one narration row per active skill, and `world/rules/status_display.py` fails closed for a buff or modifier without a display row.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, modifier rule, intelligence and mode entry, plus the referenced bindings. `world/rules/tests/test_monster_ai_activation.py` compares that fingerprint with `docs/development/monster-ai-activation-evidence/activation.json`.
- Every kit here carries a damage occurrence, so the legacy decision body proposes it and no utility binding or intelligence value is needed (`owned-kit-decision-coverage` applies only to support-only kits).

## Candidate review (`docs/lore/monster-creation-guidelines.md`)

| Question | Answer |
| --- | --- |
| Familiar archetype | A walking mushroom, the familiar fantasy fungus creature (a cap, a stem, root stubs). |
| Special way of life | Its cap stores spores that it releases only when the cap is struck or squeezed. That shapes its life: colonies stay on one rotting log, and a threat is answered by a bump and a spore cloud that buys time to shuffle back into the log. |
| World relation | Forest-edge gatherers and the healers of 巫醫窟 collect herbs and firewood from the same fallen logs (northwest hunting and tribal culture; north deep forest terrain flavour of rotting leaves under giant trees). |
| Ability limits | The spores reach about an arm's length, act only on a struck or squeezed cap, weaken in rain, and cause only brief blurred vision. There is no poison, sleep, illness or divine or origin claim (dark element: weakening, `docs/lore/magic-system.md` §3). |
| Local conflict | A colony occupies the logs a healer's gatherers need before the rainy season, so the commission is to clear a path, not to exterminate a threat. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar) and from the other five Wave 1 species.

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `north-deep-forest-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "spore_cap_mushroom",
        "孢傘菇",
        "孢傘菇是約幼犬大小的步行蕈類魔物，生活於北部深林的倒木、腐葉堆與巨木根間。"
        "牠以菌柄底部的短根緩慢挪動，從潮濕的腐木吸取養分。",
        "灰褐色的寬大菌傘覆著細密褶紋，傘緣垂著淡黃色孢粉。"
        "粗短菌柄底部分出數條短根，移動時在腐葉上留下細長拖痕。",
        "孢傘菇成群停留在同一段倒木上，菌傘受到碰撞或擠壓時，會噴出帶著微弱暗屬性的孢粉。"
        "吸入孢粉的動物會短暫視線昏沉，群落便趁這段時間挪回腐木深處。"
        "孢粉飄散範圍約一臂之遠；"
        "雨天時孢粉沾濕結團，噴出的量隨之減少。"
        "往返深林邊緣的採集者與巫醫會留意傘緣的黃粉，因為群落常占據他們採藥與拾柴的倒木。"
        "近身時，牠以菌傘頂撞對手，撞中後揚起孢粉，使對手短暫看不準目標。",
        ("north_deep_forest",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；孢粉暗屬性的成因不在設定中交代。",
        "（作者私有：作者解釋）低階群居蕈類：孢粉只在菌傘受撞擊或擠壓時散出，作用為短暫的視線昏沉，不造成中毒、睡眠或持續傷害；戰鬥呈現為頂撞與命中後的短暫命中下降。連結深林邊緣的採藥與拾柴。",
        "（作者私有：尚未證實的猜想）巫醫窟的藥師傳說菌環型站過的土壤能讓藥草長得更好，這種說法尚未證實。",
        "rotlog_sprout",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "rotlog_sprout",
        "spore_cap_mushroom",
        "腐木型",
        "普通版本，成群附著在倒木上，緩慢挪動覓食。",
        "low",
        True,
        MonsterCombatProfile(
            hp=40, mp=20, sp=8, atk_phys=5, agility=3, defense=5, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("spore_puff_bump",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

```python
    MonsterVariant(
        "ring_elder",
        "spore_cap_mushroom",
        "菌環型",
        "生長在林間菌環中央的老個體，菌傘更寬、孢粉更濃，守著整圈菌群。",
        "low",
        False,
        MonsterCombatProfile(
            hp=62, mp=30, sp=12, atk_phys=9, agility=4, defense=7, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("spore_puff_bump",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "spore_puff_bump",
        "孢粉頂撞",
        "以菌傘頂撞單一敵方目標，造成物理傷害；命中後揚起暗屬性孢粉，使對手短暫視線昏沉，降低其命中。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 2},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="dark",
        effects=["damage:dark:physical", "buff_apply:spore_haze"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="dark",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("spore_cap_mushroom",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=0.8, audience=EffectAudience.ENEMIES),
            EffectPolicy(coefficient=1.0, audience=EffectAudience.ENEMIES, requires_hit_from=0),
        ),
    ),
```

Also append one sentence to that module's docstring describing this kit's composition, in the style of the existing sentences.

### D4. Rulebook and narration

- `world/rules/rulebook/buffs.yaml`, appended after the last monster resource-skill buff (`reservoir_film`, or the previous Wave 1 species' buff), with a zh-TW comment line before it:

```yaml
# 魔物資源技能（北部深林第一波）：孢傘菇孢粉頂撞的命中干擾，buff 列為 mount，accuracy −3 資料在 combat_modifiers.yaml 的 spore_haze_accuracy 列（grain_rattle_accuracy 的 accuracy 先例）。
- key: spore_haze
  duration: 12
  stacking: refresh
  polarity: debuff
  modifiers: {}
```

- `world/rules/rulebook/combat_modifiers.yaml`, appended after the last monster resource-skill rule (`reservoir_film_defense`, or the previous Wave 1 rule) and before the fatigue block:

```yaml
- id: spore_haze_accuracy
  when: {buff_active: spore_haze}
  then: {accuracy: -3}
```

- `world/rules/rulebook/status_display.yaml`, appended after `reservoir_film_defense` (or the previous Wave 1 rows):

```yaml
- code: spore_haze
  label: 孢粉昏沉
  severity: harmful
- code: spore_haze_accuracy
  label: 孢粉昏沉命中下降
  severity: harmful
```

- `world/skills/narration/data_dark.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "spore_puff_bump",
        action=(
            "{actor} 壓低菌傘撞向對手，傘緣揚起一陣黃粉。",
            "{actor} 晃動粗短菌柄，猛然以傘頂撞了上去。",
        ),
    ),
```

### D5. AI binding and activation evidence

No `world/rules/rulebook/monster_behaviour.yaml` edit. This link adds a timed effect and a modifier, so the tuning fingerprint moves and `ActivationRecordTests` and `RollbackTests` are expected to fail until the evidence is re-fingerprinted (steps 1–4 below). Each variant binds the shipped archetype named in D2, and the legacy body selects the damage-bearing kit. Run `ActivationRecordTests`, `ActivationBindingTests` and `RollbackTests`. If they pass, the fingerprint did not move and the evidence stays untouched. If a fingerprint comparison fails, re-fingerprint following the `mudfilm-slime-species` precedent (archived change design D5, steps 1–4), without touching `activated` or `activation_bindings`:

1. Run `uv run --locked python tools/monster_ai_manual_reports.py selector` and copy `.var/monster-ai-manual-reports/selector-check.json` and `.md` over `docs/development/monster-ai-manual-evidence/`.
2. Read the new `configuration_fingerprint` from the regenerated `selector-check.json`. Read the rollback fingerprint from the `RollbackTests` failure message.
3. In `activation.json`, update `configuration_fingerprint`, `legacy_rollback.configuration_fingerprint` and the `selector-check.json` evidence entry's fingerprint.
4. Update the fingerprint lines in `docs/development/monster-ai-activation-evidence/README.md` and the selector paragraph of `docs/development/monster-ai-manual-evidence/README.md`.

### D6. Bestiary and ledger

- Overview row, inserted in the `## 收錄總覽` table after the last `| 低階 |` row:

  `| 低階 | 孢傘菇 | 北部深林的倒木、腐葉堆與巨木根間 | 菌傘受撞擊時噴出使視線昏沉的孢粉 | 腐木型、菌環型 |`

- New section at the end of `## 低階魔物`, immediately before `## 中階魔物` (after any Wave 1 low section already added), transcribed exactly:

````markdown
### 孢傘菇

```bestiary
species: spore_cap_mushroom
parent-species: spore_cap_mushroom
default-variant: rotlog_sprout
variants:
  - key: rotlog_sprout
    status: delivered
  - key: ring_elder
    status: delivered
public-fields:
  - display_name_zh
  - published_description_zh
  - published_appearance_zh
  - published_ecology_zh
  - habitat_tags
  - description_zh
status: delivered
```

**原型與棲地。**孢傘菇是約幼犬大小的步行蕈類魔物，生活於北部深林的倒木、腐葉堆與巨木根間，以菌柄底部的短根緩慢挪動。

**外觀。**灰褐色的寬大菌傘覆著細密褶紋，傘緣垂著淡黃色孢粉。粗短菌柄底部分出數條短根，移動時在腐葉上留下細長拖痕。

**生態與在地關係。**群落成群停留在同一段倒木上，從潮濕的腐木吸取養分。往返深林邊緣的採集者與巫醫會留意傘緣的黃粉，因為群落常占據他們採藥與拾柴的倒木。林間偶爾可見一圈排列整齊的菌群，圈心那隻菌傘最寬的老個體就是菌環型。

**戰鬥中的表現。**孢粉帶著微弱暗屬性，在菌傘受到撞擊或擠壓時散出，飄散範圍約一臂之遠；雨天孢粉沾濕結團，噴出的量隨之減少。近身時，牠以菌傘頂撞對手，撞中後揚起孢粉，使對手短暫視線昏沉、看不準目標。

| 變體 | 核准方向 |
| --- | --- |
| 腐木型 | 普通版本，成群附著在倒木上，緩慢挪動覓食 |
| 菌環型 | 生長在林間菌環中央的老個體，菌傘更寬、孢粉更濃，守著整圈菌群 |

**委託背景示例。**虎嘯城北邊的林緣倒木區連續幾天被孢傘菇占據，巫醫窟派來的採藥人兩度空手而回。藥師委託公會清出一條通往倒木的路，好在雨季前補足藥材。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `spore_cap_mushroom` | <implementation date> | read against the registry's published ecology field; the trouble stays local to fallen logs on the forest edge that gatherers and healers use, and the spores come from the creature's own cap | checked against the declared kit: the cap bump is a single-target dark-element physical strike, and the section states that the brief accuracy penalty follows a bump that lands, matching the declared hit dependency; the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D6a. Fourth-batch approval notes (this change only)

- `docs/lore/monster-creation-guidelines.md`: directly after the paragraph that starts `**第三批核准（2026-11-03）：**`, add a paragraph:

  `**第四批核准（2026-11-11）：**北部深林另行核准六種物種：低階的孢傘菇、苔棘豪豬與空木蝠，中階的靜羽梟與藤網蛛，以及高階的苔冠巨鹿。每個物種只出現在明確宣告的棲地、據點或遭遇中；災厄級物種與新的文明種族仍不在核准範圍內。`

- `docs/lore/bestiary.md`: directly after the paragraph that starts `**第三批核准：**`, add:

  `**第四批核准：**2026-11-11 起，北部深林另行核准三種低階、兩種中階與一種高階物種；各物種逐一收錄於下方現行小節。`

- `docs/development/monster-content-expansion.md`: append to the opening paragraph the sentence `Sections from 孢傘菇 onward record the north deep forest species of the near-settlement programme's Wave 1.`

The user authorised the Wave 1 roster in the session that requested this change set. These notes record that approval. The species changes that follow do not edit them.

### D7. Tests

- `world/rules/tests/test_combat_modifiers.py::CombatModifierTests`: add `test_rule_spore_haze_accuracy`, copying the four lines of `test_rule_rock_echo_stagger_agility_flat` with `RULES["spore_haze_accuracy"]`.

### D8. Developer review section

Append `## 孢傘菇` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Slow colony fungus: agility at the low band's floor, the slowest of every shipped low-tier ordinary variant.
* Sturdier than the evasive low animals: defense between the hare's and the slime's.
* MP holds two casts of the dark bump's MP cost; SP holds four casts of its SP cost.
* The stronger 菌環型 keeps the same kit with a larger pool, attack and defense, inside the low band and at grade E.
* The bump coefficient (0.8) and the accuracy rider (−3 for 12 s) match the sparrow's shipped peck and rider, the smallest shipped hit-rider magnitudes.
- `### Reuse of the enemy hit-rider representative`: the signature, the unchanged representative `cliff_stepper`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later Wave 1 key sorts before a representative] → every Wave 1 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_sway_whistle_sparrow_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.rules.tests.test_combat_modifiers.CombatModifierTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change spore-cap-mushroom-species` and `openspec validate spore-cap-mushroom-species --strict`.
