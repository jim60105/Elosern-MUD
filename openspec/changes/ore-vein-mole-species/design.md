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
| Familiar archetype | A mole. |
| Special way of life | Faint earth power loosens the soil and gravel just ahead of its claws, so it tunnels quickly under exposed ore veins while hunting grubs. |
| World relation | Beastfolk tribes dig ore at exposed vein outcrops (northwest highland terrain flavour: rock walls with exposed ore veins). |
| Ability limits | The loosening acts only on a small patch in front of its claws; it causes no sinkholes or wide terrain change. In combat it throws grit for a brief accuracy rider on a landed scrape (earth element: footing and terrain, magic-system §3). |
| Local conflict | Its tunnels collapse a mine trench's walls three nights running, so the foreman asks for it to be driven from the diggings. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar), the Wave 1 species (spore-cap mushroom, moss-quill porcupine, hollow-tree bat, hush-wing owl, vine-net spider, moss-crown stag) and the other nine Wave 2 species. It is an animal, clearly distinct from every beastfolk subspecies (wolf, cat, bear, rabbit, cattle, tiger, fox).

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `northwest-highland-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "ore_vein_mole",
        "礦脈鼴",
        "礦脈鼴是約貓大小的鼴類魔獸，獨自生活於西北高地礦脈裸露的岩壁下與林間空地的鬆土中。",
        "黑灰色短絨毛摸起來像天鵝絨，沾著閃亮的礦砂。"
        "前肢寬大如鏟，指爪粗厚，眼睛細小得藏在毛裡，粉紅色的鼻尖靈活地四處嗅探。",
        "牠沿著礦脈下方的鬆土挖掘長隧道，捕食土中的甲蟲幼蟲與蚯蚓，挖出的土堆在地面排成一列。"
        "牠能以微弱土屬性力量讓爪前的土石鬆動，挖起碎石層也很快；"
        "這股力量作用在牠爪前方一小片地面上。"
        "獸人部族在礦脈露頭處開採礦石，礦脈鼴的隧道常挖到採礦溝底下，溝壁因此坍落。"
        "近身時，牠以前爪刨擊對手，刨中時揚起一把礦砂打在對手臉上，使對手短暫看不準目標。",
        ("northwest_highland_forest",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；爪前土石鬆動之力的成因不在設定中交代。",
        "（作者私有：作者解釋）低階獨居鼴類：土屬性力量只鬆動爪前一小片土石，不造成地陷、崩塌或大範圍地形改變；戰鬥呈現為爪刨與命中後短暫命中下降。連結獸人部族的露頭採礦。",
        "（作者私有：尚未證實的猜想）鐵爪城的礦工說礦脈鼴挖出的土堆排成的那條線，就是礦脈延伸的方向，這種說法尚未證實。",
        "vein_digger",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "vein_digger",
        "ore_vein_mole",
        "掘脈型",
        "普通版本，沿著礦脈下方的鬆土挖掘隧道覓食。",
        "low",
        True,
        MonsterCombatProfile(
            hp=36, mp=20, sp=8, atk_phys=6, agility=5, defense=4, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("grit_claw_scrape",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

```python
    MonsterVariant(
        "deep_seam_mole",
        "ore_vein_mole",
        "深脈型",
        "在礦脈深處挖出寬大巢室的老個體，前爪磨得發亮，會從隧道口迎向闖入者。",
        "low",
        False,
        MonsterCombatProfile(
            hp=60, mp=30, sp=12, atk_phys=10, agility=6, defense=7, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("grit_claw_scrape",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "grit_claw_scrape",
        "揚砂爪刨",
        "以土屬性力量鬆動爪前土石後刨擊單一敵方目標，造成物理傷害；命中後揚起礦砂打在對手臉上，使對手短暫看不準目標，降低其命中。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 2},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="earth",
        effects=["damage:earth:physical", "buff_apply:ore_grit"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="earth",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("ore_vein_mole",),
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

- `world/rules/rulebook/buffs.yaml`, appended after the last monster resource-skill buff (the buff of the latest species already merged in the serial chain), with a zh-TW comment line before it:

```yaml
# 魔物資源技能（西北高地第二波）：礦脈鼴揚砂爪刨：命中後揚起礦砂的 mount，accuracy −3 資料在 combat_modifiers.yaml 的 ore_grit_accuracy 列（earth_dust_veil_accuracy_penalty 的 accuracy 先例）。
- key: ore_grit
  duration: 10
  stacking: refresh
  polarity: debuff
  modifiers: {}
```

- `world/rules/rulebook/combat_modifiers.yaml`, appended after the last monster resource-skill rule (the latest merged species' rule) and before the fatigue block:

```yaml
- id: ore_grit_accuracy
  when: {buff_active: ore_grit}
  then: {accuracy: -3}
```

- `world/rules/rulebook/status_display.yaml`, appended after the last monster resource-skill rows (the latest merged species' rows):

```yaml
- code: ore_grit
  label: 礦砂迷眼
  severity: harmful
- code: ore_grit_accuracy
  label: 礦砂迷眼命中下降
  severity: harmful
```

- `world/skills/narration/data_earth.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "grit_claw_scrape",
        action=(
            "{actor} 從土堆裡探出鏟狀前爪，猛然刨向對手。",
            "{actor} 雙爪一刨，一把閃亮的礦砂撲上對方的臉。",
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

  `| 低階 | 礦脈鼴 | 西北高地礦脈裸露的岩壁下與林間鬆土 | 以土屬性力量鬆動爪前的土石 | 掘脈型、深脈型 |`

- New section at the end of `## 低階魔物`, immediately before `## 中階魔物` (after every low section an earlier programme change added), transcribed exactly:

````markdown
### 礦脈鼴

```bestiary
species: ore_vein_mole
parent-species: ore_vein_mole
default-variant: vein_digger
variants:
  - key: vein_digger
    status: delivered
  - key: deep_seam_mole
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

**原型與棲地。**礦脈鼴是約貓大小的鼴類魔獸，獨自生活於西北高地礦脈裸露的岩壁下與林間空地的鬆土中。

**外觀。**黑灰色短絨毛摸起來像天鵝絨，沾著閃亮的礦砂。前肢寬大如鏟，指爪粗厚，眼睛細小得藏在毛裡，粉紅色的鼻尖靈活地四處嗅探。

**生態與在地關係。**牠沿著礦脈下方的鬆土挖掘長隧道，捕食土中的甲蟲幼蟲與蚯蚓，挖出的土堆在地面排成一列。獸人部族在礦脈露頭處開採礦石，礦脈鼴的隧道常挖到採礦溝底下，溝壁因此坍落。在礦脈深處挖出寬大巢室、前爪磨得發亮的老個體稱為深脈型。

**戰鬥中的表現。**牠能以微弱土屬性力量讓爪前的土石鬆動，挖起碎石層也很快；這股力量作用在牠爪前方一小片地面上。近身時，牠以前爪刨擊對手，刨中時揚起一把礦砂打在對手臉上，使對手短暫看不準目標。

| 變體 | 核准方向 |
| --- | --- |
| 掘脈型 | 普通版本，沿著礦脈下方的鬆土挖掘隧道覓食 |
| 深脈型 | 在礦脈深處挖出寬大巢室的老個體，前爪磨得發亮，會從隧道口迎向闖入者 |

**委託背景示例。**鐵爪城外的露頭採礦溝連續三晚坍了溝壁，礦工在溝底找到通往四面八方的新隧道。礦場工頭委託公會把那隻在溝底下挖洞的礦脈鼴趕離採礦區，讓開採能照常進行。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `ore_vein_mole` | <implementation date> | read against the registry's published ecology field; the trouble stays local to beastfolk ore trenches at exposed veins, and the loosening acts on a small patch ahead of the mole's own claws | checked against the declared kit: the claw scrape is a single-target earth-element physical strike, and the section states that the brief accuracy penalty follows a scrape that lands, matching the declared hit dependency; the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D7. Tests

- `world/rules/tests/test_combat_modifiers.py::CombatModifierTests`: add `test_rule_ore_grit_accuracy`, copying the four lines of `test_rule_rock_echo_stagger_agility_flat` with `RULES["ore_grit_accuracy"]`.

### D8. Developer review section

Append `## 礦脈鼴` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Solitary burrower: agility in the low band's lower half, defense between the hare's and the crab's ordinary variants.
* MP holds two casts of the scrape's MP cost; SP holds four casts of its SP cost.
* The rider (−3 accuracy for 10 s) equals the sparrow's shipped `grain_rattle_accuracy` contribution and lifetime.
* The stronger 深脈型 holds a deep nest chamber at grade E with a larger pool and defense.
- `### Reuse of the enemy hit-rider representative`: the signature, the unchanged representative `cliff_stepper`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later key sorts before a representative] → every Wave 1 and Wave 2 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_sway_whistle_sparrow_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.rules.tests.test_combat_modifiers.CombatModifierTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change ore-vein-mole-species` and `openspec validate ore-vein-mole-species --strict`.
