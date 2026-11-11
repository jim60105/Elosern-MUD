# Design

## Context

See proposal.md (Why). Facts at `d1ac4b84` plus the planned Wave 1 species rows (`openspec/changes/*-species/`), which land first:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS` and `_VARIANT_DECLARATIONS` at import. Bands come from `MONSTER_TIER_REGISTRY`: low HP 25–70, attack 3–12, agility 3–12, defense 2–8, grades F–E; mid HP 110–230, attack 18–28, agility 10–24, defense 10–16, grades D–C; high HP 300–750, attack 26–40, agility 16–30, defense 18–32, grades B–A. `magic_power` must be 0 and MP/SP have no band. Display names are limited to 5 code points (`MONSTER_NAME_MAX_CODE_POINTS`).
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」 and `author_conjecture_zh` to contain 「尚未證實」, and it forbids registry strings that name a skill, behaviour or trait key.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by `(slot, effect family, audience, requires_hit_from)` and requires one committed representative per group, the group's sorted-minimum key. This kit's signature is `(("active", "damage", "enemies", None), ("active", "buff_apply", "enemies", 0))`, the shipped enemy hit-rider group, whose representative `cliff_stepper` is declared in `world.rules.tests.test_sway_whistle_sparrow_resource_skill`. Every new variant key sorts after `cliff_stepper` (and every Wave 1 key does too), so the representative does not move and no smoke module, shard entry or seed entry is added. `EnemyRiderGroupMemberTests` in that module derives the group's members from the shipped declarations, so both new variants are exercised on their own rider axis without a test edit.
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests` requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, a magic tier for elemental MP skills (MP 10–16 single, 14–20 area) and `None` otherwise. `validate_catalog` requires one narration row per active skill, and `world/rules/status_display.py` fails closed for a buff or modifier without a display row.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, modifier rule, intelligence and mode entry, plus the referenced bindings. `world/rules/tests/test_monster_ai_activation.py` compares that fingerprint with `docs/development/monster-ai-activation-evidence/activation.json`.
- Every kit here carries a damage occurrence, so the legacy decision body proposes it and no utility binding or intelligence value is needed (`owned-kit-decision-coverage` applies only to support-only kits).

## Candidate review (`docs/lore/monster-creation-guidelines.md`)

| Question | Answer |
| --- | --- |
| Familiar archetype | A giant moth drawn to light. |
| Special way of life | Dark-element wing scales fall in quantity only at a landed wingbeat and make limbs feel heavy for a moment; it rests on misty trunks by day and follows light at night. |
| World relation | Stone shelters on the mountain paths light guide lamps on misty nights (central mountains terrain flavour: mist around the slopes all year). |
| Ability limits | The scales act only on a landed strike and cause a brief heaviness (agility rider). No poison, sleep or hallucination (dark element: weakening, magic-system §3). |
| Local conflict | An old moth keeps knocking out a shelter's guide lamp so late travellers lose the shelter, so the lamp keeper asks for it to be dealt with on the next misty night. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar), the Wave 1 species (spore-cap mushroom, moss-quill porcupine, hollow-tree bat, hush-wing owl, vine-net spider, moss-crown stag) and the other nine Wave 2 species. It is an animal, clearly distinct from every beastfolk subspecies (wolf, cat, bear, rabbit, cattle, tiger, fox).

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `central-mountains-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "mist_lamp_moth",
        "霧燈蛾",
        "霧燈蛾是雙翅展開約兩臂寬的大型蛾類魔獸，獨自棲息於中央山脈終年雲霧繚繞的山腰林帶。",
        "灰白翅膀上帶著兩枚暗色眼紋，翅緣垂著絨毛般的長鱗。"
        "羽狀觸角寬如手掌，身軀覆著厚密白毛，停在樹幹上時像一片積著霜的樹皮。",
        "牠白天收翅貼在霧中的樹幹上，入夜後循著光亮飛行，以花蜜與樹液為食。"
        "山徑上的避難石屋在霧夜會點燈指路，燈火常引來霧燈蛾繞著燈籠撲飛，翅膀撞得燈罩搖晃。"
        "牠的翅鱗帶著微弱暗屬性力量，鱗粉落在身上時會讓手腳短暫發沉；"
        "撲翅擊中對手的那一下，鱗粉才會大量抖落。"
        "守燈的人會在燈罩外加一層細網，讓燈光照得到山徑，蛾翅則碰不到燈火。"
        "近身時，牠以厚重的翅膀撲打對手，撲中時抖落鱗粉，使對手動作短暫遲緩。",
        ("central_mountains",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；翅鱗暗屬性力量的成因不在設定中交代。",
        "（作者私有：作者解釋）中階獨居蛾類：暗屬性翅鱗只在撲擊命中時抖落，作用為短暫手腳發沉，不造成中毒、睡眠、幻覺或持續傷害；戰鬥呈現為翅膀撲打與命中後短暫敏捷下降。連結山徑石屋的霧夜燈火。",
        "（作者私有：尚未證實的猜想）翻越山徑的旅人之間流傳，霧燈蛾繞燈越久，隔天的霧散得越快，這種說法尚未證實。",
        "lamp_seeker",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "lamp_seeker",
        "mist_lamp_moth",
        "逐光型",
        "普通版本，入夜後循著光亮在霧中飛行。",
        "mid",
        True,
        MonsterCombatProfile(
            hp=115, mp=30, sp=16, atk_phys=18, agility=19, defense=10, magic_power=0
        ),
        "D",
        True,
        active_skill_keys=("veil_scale_flutter",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
```

```python
    MonsterVariant(
        "old_veil_moth",
        "mist_lamp_moth",
        "老翅型",
        "翅膀磨得破舊、體型最大的老個體，整夜守著同一盞燈火撲飛。",
        "mid",
        False,
        MonsterCombatProfile(
            hp=150, mp=50, sp=24, atk_phys=23, agility=21, defense=11, magic_power=0
        ),
        "C",
        True,
        active_skill_keys=("veil_scale_flutter",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "veil_scale_flutter",
        "鱗粉撲翅",
        "以帶著暗屬性鱗粉的翅膀撲打單一敵方目標，造成物理傷害；命中後抖落鱗粉，使對手手腳短暫發沉，降低其敏捷。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 4},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="dark",
        effects=["damage:dark:physical", "buff_apply:veil_scale"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="dark",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("mist_lamp_moth",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=0.9, audience=EffectAudience.ENEMIES),
            EffectPolicy(coefficient=1.0, audience=EffectAudience.ENEMIES, requires_hit_from=0),
        ),
    ),
```

Also append one sentence to that module's docstring describing this kit's composition, in the style of the existing sentences.

### D4. Rulebook and narration

- `world/rules/rulebook/buffs.yaml`, appended after the last monster resource-skill buff (the buff of the latest species already merged in the serial chain), with a zh-TW comment line before it:

```yaml
# 魔物資源技能（中央山脈第二波）：霧燈蛾鱗粉撲翅：命中後抖落鱗粉的 mount，agility_flat −3 資料在 combat_modifiers.yaml 的 veil_scale_agility_flat 列（rock_echo_stagger_agility_flat 的 hit-rider 先例）。
- key: veil_scale
  duration: 15
  stacking: refresh
  polarity: debuff
  modifiers: {}
```

- `world/rules/rulebook/combat_modifiers.yaml`, appended after the last monster resource-skill rule (the latest merged species' rule) and before the fatigue block:

```yaml
- id: veil_scale_agility_flat
  when: {buff_active: veil_scale}
  then: {agility_flat: -3}
```

- `world/rules/rulebook/status_display.yaml`, appended after the last monster resource-skill rows (the latest merged species' rows):

```yaml
- code: veil_scale
  label: 鱗粉沉滯
  severity: harmful
- code: veil_scale_agility_flat
  label: 鱗粉沉滯敏捷下降
  severity: harmful
```

- `world/skills/narration/data_dark.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "veil_scale_flutter",
        action=(
            "{actor} 從霧裡撲出，厚翅拍得鱗粉四散。",
            "{actor} 繞著光亮盤旋一圈，翅膀猛然打向對手。",
        ),
    ),
```

### D5. AI binding and activation evidence

No `world/rules/rulebook/monster_behaviour.yaml` edit. This link adds a timed effect and a modifier, so the tuning fingerprint moves and `ActivationRecordTests` and `RollbackTests` are expected to fail until the evidence is re-fingerprinted (steps 1–4 below). Each variant binds the shipped archetype named in D2, and the legacy body selects the damage-bearing kit. Run `ActivationRecordTests`, `ActivationBindingTests` and `RollbackTests`. Expect `ActivationRecordTests` and `RollbackTests` to fail on the fingerprint comparison (the `spore-cap-mushroom-species` and `moss-quill-porcupine-species` landings saw the same failure); this is the expected outcome, not a defect. Then re-fingerprint following the `mudfilm-slime-species` precedent (archived change design D5, steps 1–4), without touching `activated` or `activation_bindings`:

1. Run `uv run --locked python tools/monster_ai_manual_reports.py selector` and copy `.var/monster-ai-manual-reports/selector-check.json` and `.md` over `docs/development/monster-ai-manual-evidence/`.
2. Read the new `configuration_fingerprint` from the regenerated `selector-check.json`. Read the rollback fingerprint from the `RollbackTests` failure message.
3. In `activation.json`, update `configuration_fingerprint`, `legacy_rollback.configuration_fingerprint` and the `selector-check.json` evidence entry's fingerprint.
4. Update the fingerprint lines in `docs/development/monster-ai-activation-evidence/README.md` and the selector paragraph of `docs/development/monster-ai-manual-evidence/README.md`.

### D6. Bestiary and ledger

- Overview row, inserted in the `## 收錄總覽` table after the last `| 中階 |` or `| 中階／高階 |` row:

  `| 中階 | 霧燈蛾 | 中央山脈雲霧繚繞的山腰林帶 | 撲翅抖落使手腳發沉的暗屬性鱗粉 | 逐光型、老翅型 |`

- New section at the end of `## 中階魔物`, immediately before `## 高階魔物` (after every mid section an earlier programme change added), transcribed exactly:

````markdown
### 霧燈蛾

```bestiary
species: mist_lamp_moth
parent-species: mist_lamp_moth
default-variant: lamp_seeker
variants:
  - key: lamp_seeker
    status: delivered
  - key: old_veil_moth
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

**原型與棲地。**霧燈蛾是雙翅展開約兩臂寬的大型蛾類魔獸，獨自棲息於中央山脈終年雲霧繚繞的山腰林帶。

**外觀。**灰白翅膀上帶著兩枚暗色眼紋，翅緣垂著絨毛般的長鱗。羽狀觸角寬如手掌，身軀覆著厚密白毛，停在樹幹上時像一片積著霜的樹皮。

**生態與在地關係。**牠白天收翅貼在霧中的樹幹上，入夜後循著光亮飛行，以花蜜與樹液為食。山徑上的避難石屋在霧夜會點燈指路，燈火常引來霧燈蛾繞著燈籠撲飛，翅膀撞得燈罩搖晃。守燈的人會在燈罩外加一層細網，讓燈光照得到山徑，蛾翅則碰不到燈火。翅膀磨得破舊、整夜守著同一盞燈火撲飛的老個體稱為老翅型。

**戰鬥中的表現。**牠的翅鱗帶著微弱暗屬性力量。近身時，牠以厚重的翅膀撲打對手，撲中時抖落鱗粉，讓對手手腳短暫發沉、動作遲緩；鱗粉在撲中的那一下才大量抖落。

| 變體 | 核准方向 |
| --- | --- |
| 逐光型 | 普通版本，入夜後循著光亮在霧中飛行 |
| 老翅型 | 翅膀磨得破舊、體型最大的老個體，整夜守著同一盞燈火撲飛 |

**委託背景示例。**山徑第三座石屋的指路燈連續幾個霧夜被一隻老翅型霧燈蛾撲熄，晚到的旅人在霧裡找不到石屋。守燈人委託公會在下一個霧夜守在燈旁，處理那隻整夜繞燈的大蛾。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `mist_lamp_moth` | <implementation date> | read against the registry's published ecology field; the trouble stays local to the guide lamps of mountain-path shelters on misty nights, and the scales come from the moth's own wings | checked against the declared kit: the wingbeat is a single-target dark-element physical strike, and the section states that the brief slowing follows a wingbeat that lands, matching the declared hit dependency; the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D7. Tests

- `world/rules/tests/test_combat_modifiers.py::CombatModifierTests`: add `test_rule_veil_scale_agility_flat`, copying the four lines of `test_rule_rock_echo_stagger_agility_flat` with `RULES["veil_scale_agility_flat"]`. Copy those four lines exactly and assert no rule value of your own.

### D8. Developer review section

Append `## 霧燈蛾` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Fragile night flier: hit points and defense at the mid band's floor, agility in the band's upper half.
* MP holds three casts of the wingbeat's MP cost; SP holds four casts of its SP cost.
* The rider (−3 agility for 15 s) equals the goat's shipped `rock_echo_stagger_agility_flat` contribution and lifetime.
* The stronger 老翅型 holds one lamp all night at grade C with a larger pool.
- `### Reuse of the enemy hit-rider representative`: the signature, the unchanged representative `cliff_stepper`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later key sorts before a representative] → every Wave 1 and Wave 2 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_sway_whistle_sparrow_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.rules.tests.test_combat_modifiers.CombatModifierTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change mist-lamp-moth-species` and `openspec validate mist-lamp-moth-species --strict`.
