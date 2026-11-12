# Design

## Context

See proposal.md (Why). Facts at `cf4643a1` plus the planned Wave 2, Wave 3 and earlier Wave 4 species rows still open under `openspec/changes/*-species/`, which land first in the serial chain:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS` and `_VARIANT_DECLARATIONS` at import. Bands come from `MONSTER_TIER_REGISTRY`: low HP 25–70, attack 3–12, agility 3–12, defense 2–8, grades F–E; mid HP 110–230, attack 18–28, agility 10–24, defense 10–16, grades D–C; high HP 300–750, attack 26–40, agility 16–30, defense 18–32, grades B–A. `magic_power` must be 0 and MP/SP have no band. Display names are limited to 5 code points (`MONSTER_NAME_MAX_CODE_POINTS`).
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」 and `author_conjecture_zh` to contain 「尚未證實」, and it forbids registry strings that name a skill, behaviour or trait key.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by `(slot, effect family, audience, requires_hit_from)` and requires one committed representative per group, the group's sorted-minimum key. This kit's signature is `(("active", "damage", "enemies", None), ("active", "buff_apply", "enemies", 0))`, the shipped enemy hit-rider group, whose representative `cliff_stepper` is declared in `world.rules.tests.test_sway_whistle_sparrow_resource_skill`. Every new variant key sorts after `cliff_stepper` (as every Wave 1, Wave 2 and Wave 3 key does), so the representative does not move and no smoke module, shard entry or seed entry is added. `EnemyRiderGroupMemberTests` in that module derives the group's members from the shipped declarations, so both new variants are exercised on their own rider axis without a test edit. The rider lowers flat agility (`agility_flat`), the axis of the goat's and the goblin's shipped riders. The skill is elementless with an SP-only cost, so `spell_tier_for` returns `None` (the goblin and wolverine precedent).
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests` requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, a magic tier for elemental MP skills (MP 10–16 single, 14–20 area) and `None` otherwise. `validate_catalog` requires one narration row per active skill, and `world/rules/status_display.py` fails closed for a buff or modifier without a display row.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, modifier rule, intelligence and mode entry, plus the referenced bindings. `world/rules/tests/test_monster_ai_activation.py` compares that fingerprint with `docs/development/monster-ai-activation-evidence/activation.json`.
- Every kit here carries a damage occurrence, so the legacy decision body proposes it and no utility binding or intelligence value is needed (`owned-kit-decision-coverage` applies only to support-only kits).

## Candidate review (`docs/lore/monster-creation-guidelines.md`)

| Question | Answer |
| --- | --- |
| Familiar archetype | An antlion larva (doodlebug) of loose sand. |
| Special way of life | Its flat head flings loose sand with abnormal force, so the slope under its prey slides into the funnel pit it digs in quarry sand and spoil heaps. |
| World relation | The quarries and mine spoil heaps of the western hills, their stone carts and the sheep grazing the scrub slopes (western hills terrain flavour: mine shafts and quarries, scrub hills with grazing sheep). |
| Ability limits | The force is a body ability of its own head with no element; the pit is the nest it digs, and it opens no pit or terrain in a fight. A landed bite sends the target's footing sliding, a brief agility rider; a miss leaves the footing as it was. |
| Local conflict | A pit wider than a cart opens beside a quarry track and swallows two stone carts, so the quarry owner asks for the antlion to be found and driven off. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar), the Wave 1 species (spore-cap mushroom, moss-quill porcupine, hollow-tree bat, hush-wing owl, vine-net spider, moss-crown stag), the Wave 2 species (mountain frog, fire salamander, bearded vulture, giant moth, giant constrictor, capercaillie, beaver, mole, wolverine, griffin), the Wave 3 species (dung beetle, wild horse, grey heron, giant snapping turtle, mudskipper, herring gull, harbour seal) and the other six Wave 4 species (giant harvester ant of dry salt roads, sea star of rock pools and oyster racks, mantis shrimp of harbour shallows, marine iguana of sea cliffs, giant octopus of sea caves (kraken folklore), cave cricket of mines and cellars). It is an animal, clearly distinct from every beastfolk subspecies (wolf, cat, bear, rabbit, cattle, tiger, fox).

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `western-hills-deep-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "pit_sand_antlion",
        "陷坑蟻獅",
        "陷坑蟻獅是體長約有半個人高的蟻獅類魔獸，獨自棲息於西部丘陵的採石場、礦渣堆與河谷沙地。",
        "身體肥圓，灰褐色的表皮長滿短硬的剛毛，背上沾著一層沙土。"
        "頭部扁平寬大，前端一對鐮刀狀的長顎向內彎曲，內緣排著尖齒；"
        "六條短腿習慣倒退著走。",
        "牠在鬆軟的沙土裡倒退著挖出一個漏斗狀的深坑，把身體埋在坑底，只露出一對長顎，等待甲蟲、老鼠與失足的小動物滑落。"
        "牠的扁平頭部帶著異常的力氣，一甩就能把一大片沙土拋向坑壁，讓獵物腳下的坡面整片滑落。"
        "西部丘陵的採石場與礦坑外堆著大片碎石與礦渣，運石的板車與坡地上的羊群常在礦渣堆的小路上踩塌坑緣，車輪陷進沙坑，小羊也會滑進坑底。"
        "近身時，牠甩頭把沙土揚向對手腳下，再以長顎鉗咬，咬中時對手腳下的沙土一起滑落，短時間內步伐遲緩。",
        ("western_hills_valleys",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；扁平頭部異常力氣的成因不在設定中交代。",
        "（作者私有：作者解釋）中階獨居蟻獅：甩沙屬於頭部的身體能力，不帶元素、不操控地形；沙坑是牠自己挖出的巢，戰鬥中不造出新的陷坑；戰鬥呈現為甩沙鉗咬與命中後短暫敏捷下降。描寫維持昆蟲幼蟲體態。連結採石場的運石板車與礦渣堆旁放牧的羊群。",
        "（作者私有：尚未證實的猜想）灰岩城的採石工說陷坑蟻獅的坑挖得越深，那年冬天就越冷，這種說法尚未證實。",
        "quarry_pit_lurker",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "quarry_pit_lurker",
        "pit_sand_antlion",
        "伏坑型",
        "普通版本，在採石場與河谷沙地挖坑伏擊。",
        "mid",
        True,
        MonsterCombatProfile(
            hp=140, mp=0, sp=24, atk_phys=23, agility=11, defense=13, magic_power=0
        ),
        "D",
        True,
        active_skill_keys=("sand_toss_pincer",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
```

```python
    MonsterVariant(
        "spoil_heap_elder",
        "pit_sand_antlion",
        "大坑型",
        "在礦渣堆上挖出最寬沙坑的老個體，長顎最長，會鉗住任何踩上坑緣的身影。",
        "mid",
        False,
        MonsterCombatProfile(
            hp=195, mp=0, sp=36, atk_phys=27, agility=11, defense=15, magic_power=0
        ),
        "C",
        True,
        active_skill_keys=("sand_toss_pincer",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "sand_toss_pincer",
        "揚沙鉗咬",
        "甩頭把沙土揚向單一敵方目標的腳下，再以長顎鉗咬，造成物理傷害；命中後讓對手腳下沙土滑落，短暫降低其敏捷。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"sp": 6},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        effects=["damage:none:physical", "buff_apply:sand_slide"],
        category=SkillCategory.MARTIAL_ARTS,
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("pit_sand_antlion",),
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
# 魔物資源技能（西部丘陵第四波）：陷坑蟻獅揚沙鉗咬：命中後腳下沙土滑落的 mount，agility_flat −3 資料在 combat_modifiers.yaml 的 sand_slide_agility_flat 列（rock_echo_stagger_agility_flat 的 agility_flat 先例）。
- key: sand_slide
  duration: 15
  stacking: refresh
  polarity: debuff
  modifiers: {}
```

- `world/rules/rulebook/combat_modifiers.yaml`, appended after the last monster resource-skill rule (the latest merged species' rule) and before the fatigue block:

```yaml
- id: sand_slide_agility_flat
  when: {buff_active: sand_slide}
  then: {agility_flat: -3}
```

- `world/rules/rulebook/status_display.yaml`, appended after the last monster resource-skill rows (the latest merged species' rows):

```yaml
- code: sand_slide
  label: 腳下沙陷
  severity: harmful
- code: sand_slide_agility_flat
  label: 腳下沙陷敏捷下降
  severity: harmful
```

- `world/skills/narration/data_martial.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "sand_toss_pincer",
        action=(
            "{actor} 猛一甩頭，沙土揚向對手腳下。",
            "{actor} 從沙裡竄出，長顎一合鉗住對方。",
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

  `| 中階 | 陷坑蟻獅 | 西部丘陵的採石場、礦渣堆與河谷沙地 | 扁平頭部一甩就能拋起整片沙土 | 伏坑型、大坑型 |`

- New section at the end of `## 中階魔物`, immediately before `## 高階魔物` (after every mid section an earlier programme change added), transcribed exactly:

````markdown
### 陷坑蟻獅

```bestiary
species: pit_sand_antlion
parent-species: pit_sand_antlion
default-variant: quarry_pit_lurker
variants:
  - key: quarry_pit_lurker
    status: delivered
  - key: spoil_heap_elder
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

**原型與棲地。**陷坑蟻獅是體長約有半個人高的蟻獅類魔獸，獨自棲息於西部丘陵的採石場、礦渣堆與河谷沙地。

**外觀。**身體肥圓，灰褐色的表皮長滿短硬的剛毛，背上沾著一層沙土。頭部扁平寬大，前端一對鐮刀狀的長顎向內彎曲，內緣排著尖齒；六條短腿習慣倒退著走。

**生態與在地關係。**牠在鬆軟的沙土裡倒退著挖出一個漏斗狀的深坑，把身體埋在坑底，只露出一對長顎，等待甲蟲、老鼠與失足的小動物滑落。西部丘陵的採石場與礦坑外堆著大片碎石與礦渣，運石的板車與坡地上的羊群常在礦渣堆的小路上踩塌坑緣，車輪陷進沙坑，小羊也會滑進坑底。在礦渣堆上挖出最寬沙坑、長顎最長的老個體稱為大坑型。

**戰鬥中的表現。**牠的扁平頭部帶著異常的力氣，一甩就能把一大片沙土拋向坑壁，讓獵物腳下的坡面整片滑落。近身時，牠甩頭把沙土揚向對手腳下，再以長顎鉗咬，咬中時對手腳下的沙土一起滑落，短時間內步伐遲緩。

| 變體 | 核准方向 |
| --- | --- |
| 伏坑型 | 普通版本，在採石場與河谷沙地挖坑伏擊 |
| 大坑型 | 在礦渣堆上挖出最寬沙坑的老個體，長顎最長，會鉗住任何踩上坑緣的身影 |

**委託背景示例。**灰岩城外採石場通往河邊的運石小路旁，礦渣堆上冒出一個比板車還寬的沙坑，已經有兩輛板車連著石料滑了進去。採石場主委託公會找出坑底的大坑型，讓運石的板車照常上路。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `pit_sand_antlion` | <implementation date> | read against the registry's published ecology field; the trouble stays local to a quarry cart track beside a spoil heap and the sheep grazing nearby, and the sand toss comes from the antlion's own flat head | checked against the declared kit: the sand-toss bite is a single-target elementless physical strike that spends SP, and the section states that the sliding footing follows a bite that lands, matching the declared hit dependency; the pit is the animal's own dug nest and the section creates no terrain in combat; the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D7. Tests

- `world/rules/tests/test_combat_modifiers.py::CombatModifierTests`: add `test_rule_sand_slide_agility_flat`, copying the four lines of `test_rule_rock_echo_stagger_agility_flat` with `RULES["sand_slide_agility_flat"]`. Copy those four lines exactly and assert no rule value of your own.

### D8. Developer review section

Append `## 陷坑蟻獅` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Pit ambusher: attack in the mid band's upper half, defense in its middle, hit points in its lower half, agility near its floor.
* The kit spends no MP, so the MP pool is zero; SP holds four casts of the bite's SP cost (six on 大坑型).
* The rider (−3 agility for 15 s) equals the goat's shipped agility rider.
* The stronger 大坑型 holds the widest spoil-heap pit at grade C.
- `### Reuse of the enemy hit-rider representative`: the signature, the unchanged representative `cliff_stepper`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later key sorts before a representative] → every Wave 1, Wave 2, Wave 3 and Wave 4 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_sway_whistle_sparrow_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.rules.tests.test_combat_modifiers.CombatModifierTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change pit-sand-antlion-species` and `openspec validate pit-sand-antlion-species --strict`.
