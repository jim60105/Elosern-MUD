# Design

## Context

See proposal.md (Why). Facts at `d1ac4b84` plus the planned Wave 1 species rows (`openspec/changes/*-species/`), which land first:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS` and `_VARIANT_DECLARATIONS` at import. Bands come from `MONSTER_TIER_REGISTRY`: low HP 25–70, attack 3–12, agility 3–12, defense 2–8, grades F–E; mid HP 110–230, attack 18–28, agility 10–24, defense 10–16, grades D–C; high HP 300–750, attack 26–40, agility 16–30, defense 18–32, grades B–A. `magic_power` must be 0 and MP/SP have no band. Display names are limited to 5 code points (`MONSTER_NAME_MAX_CODE_POINTS`).
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」 and `author_conjecture_zh` to contain 「尚未證實」, and it forbids registry strings that name a skill, behaviour or trait key.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by `(slot, effect family, audience, requires_hit_from)` and requires one committed representative per group, the group's sorted-minimum key. This kit's signature is `(("active", "damage", "enemies", None), ("active", "buff_apply", "enemies", 0))`, the shipped enemy hit-rider group, whose representative `cliff_stepper` is declared in `world.rules.tests.test_sway_whistle_sparrow_resource_skill`. Every new variant key sorts after `cliff_stepper` (and every Wave 1 key does too), so the representative does not move and no smoke module, shard entry or seed entry is added. `EnemyRiderGroupMemberTests` in that module derives the group's members from the shipped declarations, so both new variants are exercised on their own rider axis without a test edit. The skill is elementless with an SP-only cost, so `spell_tier_for` returns `None` (the goblin and spider precedent). `world/rules/combat_modifiers.py::defense_with_bundle` adds the negative flat `defense` value to the struck entity's defense.
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests` requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, a magic tier for elemental MP skills (MP 10–16 single, 14–20 area) and `None` otherwise. `validate_catalog` requires one narration row per active skill, and `world/rules/status_display.py` fails closed for a buff or modifier without a display row.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, modifier rule, intelligence and mode entry, plus the referenced bindings. `world/rules/tests/test_monster_ai_activation.py` compares that fingerprint with `docs/development/monster-ai-activation-evidence/activation.json`.
- Every kit here carries a damage occurrence, so the legacy decision body proposes it and no utility binding or intelligence value is needed (`owned-kit-decision-coverage` applies only to support-only kits).

## Candidate review (`docs/lore/monster-creation-guidelines.md`)

| Question | Answer |
| --- | --- |
| Familiar archetype | A wolverine, the glutton of northern forests (named and described as a badger-like animal so it never reads as a wolf or bear beastfolk). |
| Special way of life | Its jaws carry abnormal crushing force that opens frozen bone and iron traps, and it remembers every trap line it has raided across a huge range. |
| World relation | Beastfolk tribes lay trap lines across seasonal hunting grounds (northwest hunting culture; terrain flavour: hunters' campfire traces). |
| Ability limits | The bite force is a body ability with no element; it breaks no bones and leaves no lasting harm. A landed bite loosens the target's guard briefly (defense rider); a miss changes nothing. |
| Local conflict | It follows one town's trap line and eats the season's catch, so the hunters ask for it to be tracked down along the line. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar), the Wave 1 species (spore-cap mushroom, moss-quill porcupine, hollow-tree bat, hush-wing owl, vine-net spider, moss-crown stag) and the other nine Wave 2 species. It is an animal, clearly distinct from every beastfolk subspecies (wolf, cat, bear, rabbit, cattle, tiger, fox).

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `northwest-highland-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "cache_raider_wolverine",
        "掠藏獾",
        "掠藏獾是體型如中型犬、身軀粗壯的獾類魔獸，獨自遊走於西北高地針葉林與高地雪原之間的廣大範圍。",
        "深棕色長毛在兩側各有一道淡黃寬紋，從肩頭延伸到尾根。"
        "四肢短而粗，腳掌寬大，爪子彎長，頭部寬短，顎部肌肉鼓起如拳。",
        "牠一天能走過好幾座山頭，循著氣味找出埋在雪下的獸屍與其他動物藏起的食物。"
        "牠的顎部帶著異常的咬合力，咬得開凍硬的獸骨，也扳得開鐵製獸夾。"
        "獸人部族在季節性獵場佈下綿長的陷阱線，掠藏獾記得每一條走過的陷阱線，會沿線吃掉夾到的獵物，再把剩下的拖去藏起來。"
        "獵人巡陷阱時若發現獸夾被扳開、獵物只剩一撮毛，就知道牠來過。"
        "近身時，牠撲上去以顎部鉗住對手的手腳猛力扳扭，咬中時讓對手的護身架勢短暫鬆開。",
        ("northwest_highland_forest",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；異常咬合力的成因不在設定中交代。",
        "（作者私有：作者解釋）中階獨居掠食者：異常咬合力屬於身體能力，不帶元素、不造成骨折或持續傷害；戰鬥呈現為鉗顎咬擊與命中後短暫防禦下降。命名與外觀刻意避開狼與熊，避免與獸人亞種混淆。連結獸人部族季節性獵場的陷阱線。",
        "（作者私有：尚未證實的猜想）霜風鎮的獵人說掠藏獾會故意避開設過兩次的陷阱，這種說法尚未證實。",
        "trapline_raider",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "trapline_raider",
        "cache_raider_wolverine",
        "掠索型",
        "普通版本，沿著獵人的陷阱線一路吃掉夾到的獵物。",
        "mid",
        True,
        MonsterCombatProfile(
            hp=140, mp=0, sp=24, atk_phys=22, agility=14, defense=13, magic_power=0
        ),
        "D",
        True,
        active_skill_keys=("jaw_lock_bite",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
```

```python
    MonsterVariant(
        "winter_den_glutton",
        "cache_raider_wolverine",
        "冬穴型",
        "入冬前把整季食物藏進雪下巢穴的個體，守著儲糧，會撲向靠近巢穴的任何身影。",
        "mid",
        False,
        MonsterCombatProfile(
            hp=190, mp=0, sp=36, atk_phys=27, agility=15, defense=15, magic_power=0
        ),
        "C",
        True,
        active_skill_keys=("jaw_lock_bite",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "jaw_lock_bite",
        "鉗顎扳咬",
        "以顎部鉗住單一敵方目標猛力扳扭，造成物理傷害；命中後讓對手的護身架勢短暫鬆開，降低其防禦。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"sp": 6},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        effects=["damage:none:physical", "buff_apply:jaw_wrench"],
        category=SkillCategory.MARTIAL_ARTS,
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("cache_raider_wolverine",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=1.0, audience=EffectAudience.ENEMIES),
            EffectPolicy(coefficient=1.0, audience=EffectAudience.ENEMIES, requires_hit_from=0),
        ),
    ),
```

Also append one sentence to that module's docstring describing this kit's composition, in the style of the existing sentences.

### D4. Rulebook and narration

- `world/rules/rulebook/buffs.yaml`, appended after the last monster resource-skill buff (the buff of the latest species already merged in the serial chain), with a zh-TW comment line before it:

```yaml
# 魔物資源技能（西北高地第二波）：掠藏獾鉗顎扳咬：命中後扳開護身架勢的 mount，defense −2 資料在 combat_modifiers.yaml 的 jaw_wrench_defense 列（high_exposure_defense_penalty 的 defense 負值先例）。
- key: jaw_wrench
  duration: 15
  stacking: refresh
  polarity: debuff
  modifiers: {}
```

- `world/rules/rulebook/combat_modifiers.yaml`, appended after the last monster resource-skill rule (the latest merged species' rule) and before the fatigue block:

```yaml
- id: jaw_wrench_defense
  when: {buff_active: jaw_wrench}
  then: {defense: -2}
```

- `world/rules/rulebook/status_display.yaml`, appended after the last monster resource-skill rows (the latest merged species' rows):

```yaml
- code: jaw_wrench
  label: 鉗顎扳扭
  severity: harmful
- code: jaw_wrench_defense
  label: 鉗顎扳扭防禦下降
  severity: harmful
```

- `world/skills/narration/data_martial.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "jaw_lock_bite",
        action=(
            "{actor} 低頭猛撲，顎部一口鉗住對手的手臂。",
            "{actor} 咬住對方不放，粗壯的脖子用力一扭。",
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

- Overview row, inserted in the `## 收錄總覽` table after the last `| 中階 |` or `| 中階／高階 |` row:

  `| 中階 | 掠藏獾 | 西北高地針葉林與高地雪原之間 | 顎部咬合力咬得開凍骨與鐵製獸夾 | 掠索型、冬穴型 |`

- New section at the end of `## 中階魔物`, immediately before `## 高階魔物` (after every mid section an earlier programme change added), transcribed exactly:

````markdown
### 掠藏獾

```bestiary
species: cache_raider_wolverine
parent-species: cache_raider_wolverine
default-variant: trapline_raider
variants:
  - key: trapline_raider
    status: delivered
  - key: winter_den_glutton
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

**原型與棲地。**掠藏獾是體型如中型犬、身軀粗壯的獾類魔獸，獨自遊走於西北高地針葉林與高地雪原之間的廣大範圍。

**外觀。**深棕色長毛在兩側各有一道淡黃寬紋，從肩頭延伸到尾根。四肢短而粗，腳掌寬大，爪子彎長，頭部寬短，顎部肌肉鼓起如拳。

**生態與在地關係。**牠一天能走過好幾座山頭，循著氣味找出埋在雪下的獸屍與其他動物藏起的食物。獸人部族在季節性獵場佈下綿長的陷阱線，掠藏獾記得每一條走過的陷阱線，會沿線吃掉夾到的獵物，再把剩下的拖去藏起來。獵人巡陷阱時若發現獸夾被扳開、獵物只剩一撮毛，就知道牠來過。入冬前把整季食物藏進雪下巢穴、守著儲糧的個體稱為冬穴型。

**戰鬥中的表現。**牠的顎部帶著異常的咬合力，咬得開凍硬的獸骨，也扳得開鐵製獸夾。近身時，牠撲上去以顎部鉗住對手的手腳猛力扳扭，咬中時讓對手的護身架勢短暫鬆開；咬空時對手架勢照常。

| 變體 | 核准方向 |
| --- | --- |
| 掠索型 | 普通版本，沿著獵人的陷阱線一路吃掉夾到的獵物 |
| 冬穴型 | 入冬前把整季食物藏進雪下巢穴的個體，守著儲糧，會撲向靠近巢穴的任何身影 |

**委託背景示例。**霜風鎮獵人在北邊獵場佈下的陷阱線，一週內有一半的獸夾被扳開，夾到的獵物全被吃光。獵人組頭委託公會沿著陷阱線找出那隻掠藏獾，保住這一季的獵獲。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `cache_raider_wolverine` | <implementation date> | read against the registry's published ecology field; the trouble stays local to the trap lines of seasonal hunting grounds, and the bite force is the animal's own body strength | checked against the declared kit: the jaw bite is a single-target elementless physical strike that spends SP, and the section states that the brief loosening of guard follows a bite that lands, matching the declared hit dependency; the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D7. Tests

- `world/rules/tests/test_combat_modifiers.py::CombatModifierTests`: add `test_rule_jaw_wrench_defense`, copying the four lines of `test_rule_rock_echo_stagger_agility_flat` with `RULES["jaw_wrench_defense"]`.

### D8. Developer review section

Append `## 掠藏獾` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Tenacious ground raider: hit points and defense in the mid band's upper half, agility in its lower half.
* The kit spends no MP, so the MP pool is zero; SP holds four casts of the bite's SP cost.
* The rider (−2 defense for 15 s) is the first monster defense rider; its size equals the goblin's shipped −2 rider, the smallest shipped hit-rider magnitude.
* The stronger 冬穴型 guards its snow cache at grade C.
- `### Reuse of the enemy hit-rider representative`: the signature, the unchanged representative `cliff_stepper`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later key sorts before a representative] → every Wave 1 and Wave 2 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_sway_whistle_sparrow_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.rules.tests.test_combat_modifiers.CombatModifierTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change cache-raider-wolverine-species` and `openspec validate cache-raider-wolverine-species --strict`.
