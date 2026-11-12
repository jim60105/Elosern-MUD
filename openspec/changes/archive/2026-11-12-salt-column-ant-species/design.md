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
| Familiar archetype | A giant harvester ant of dry ground. |
| Special way of life | Its jaws and neck carry abnormal strength, so one ant drags a lump of salt several times its own weight back to the nest, and the nest mound crusts white with salt. |
| World relation | The salt road from 鹽道城 to the sea, its donkey carts and the salt pans and olive groves of the south-west shore (southwest coast terrain flavour: salt pans; settlement: the salt-road ferry city). |
| Ability limits | The strength is a body ability with no element; it sprays no acid and carries no poison. A landed bite drags the target's footing, a brief agility rider; it acts only on what its jaws hold. |
| Local conflict | A new salt-crusted mound beside the salt road sends columns across it and bites open the salt sacks, so a salt merchant asks for the nest to be moved off the roadside. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar), the Wave 1 species (spore-cap mushroom, moss-quill porcupine, hollow-tree bat, hush-wing owl, vine-net spider, moss-crown stag), the Wave 2 species (mountain frog, fire salamander, bearded vulture, giant moth, giant constrictor, capercaillie, beaver, mole, wolverine, griffin), the Wave 3 species (dung beetle, wild horse, grey heron, giant snapping turtle, mudskipper, herring gull, harbour seal) and the other six Wave 4 species (sea star of rock pools and oyster racks, mantis shrimp of harbour shallows, marine iguana of sea cliffs, giant octopus of sea caves (kraken folklore), cave cricket of mines and cellars, antlion larva of quarry sand). It is an animal, clearly distinct from every beastfolk subspecies (wolf, cat, bear, rabbit, cattle, tiger, fox).

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `southwest-coast-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "salt_column_ant",
        "負鹽蟻",
        "負鹽蟻是約手掌長的蟻類魔獸，成群生活於西南海岸的鹽道、曬鹽場堤岸與橄欖林的乾地。",
        "赤褐色的身體分成頭、胸、腹三節，表面光滑發亮。"
        "頭部方大，一對鉗狀大顎的邊緣帶著細齒；"
        "六條腿細長，觸角在頭前不停擺動。",
        "牠們在乾燥的土坡下挖出深巢，排成長列外出覓食，專找鹽粒、橄欖與掉落的乾果。"
        "牠的大顎與頸部帶著異常的力氣，一隻就能銜起比自己重上好幾倍的鹽塊，拖著倒退回巢；"
        "巢口的土丘因此結著一層白鹽殼。"
        "鹽道城往海邊的鹽道上，運鹽的驢車常被蟻列攔住，麻袋被咬開，鹽粒一路漏進蟻巢。"
        "近身時，牠以大顎咬住對手的腳踝向後拖拽，咬中時讓對手腳下一沉，短時間內步伐遲緩。",
        ("southwest_coast",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；大顎異常力氣的成因不在設定中交代。",
        "（作者私有：作者解釋）低階群居螞蟻：大顎的力氣屬於身體能力，不帶元素、不噴酸、不造成中毒；戰鬥呈現為咬住拖拽與命中後短暫敏捷下降。描寫維持昆蟲體態。連結鹽道城的運鹽驢車與巢口鹽殼。",
        "（作者私有：尚未證實的猜想）鹽道城的趕驢人說負鹽蟻把巢口的鹽殼加厚的那年，雨季會來得特別晚，這種說法尚未證實。",
        "salt_hauler",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "salt_hauler",
        "salt_column_ant",
        "搬鹽型",
        "普通版本，排成長列在鹽道與曬鹽場之間搬運鹽粒。",
        "low",
        True,
        MonsterCombatProfile(
            hp=34, mp=0, sp=9, atk_phys=5, agility=8, defense=4, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("salt_jaw_haul",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

```python
    MonsterVariant(
        "salt_mound_soldier",
        "salt_column_ant",
        "守丘型",
        "頭部特別大、大顎特別寬的兵蟻，守在結著鹽殼的巢丘上，會咬向任何踩上巢丘的身影。",
        "low",
        False,
        MonsterCombatProfile(
            hp=58, mp=0, sp=15, atk_phys=10, agility=7, defense=6, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("salt_jaw_haul",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "salt_jaw_haul",
        "銜鹽拖咬",
        "以大顎咬住單一敵方目標的腳踝向後拖拽，造成物理傷害；命中後讓對手腳下一沉，短暫降低其敏捷。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"sp": 3},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        effects=["damage:none:physical", "buff_apply:jaw_drag"],
        category=SkillCategory.MARTIAL_ARTS,
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("salt_column_ant",),
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
# 魔物資源技能（西南海岸第四波）：負鹽蟻銜鹽拖咬：命中後腳步被拖住的 mount，agility_flat −2 資料在 combat_modifiers.yaml 的 jaw_drag_agility_flat 列（sticky_palm_drag_agility_flat 的 agility_flat 先例）。
- key: jaw_drag
  duration: 12
  stacking: refresh
  polarity: debuff
  modifiers: {}
```

- `world/rules/rulebook/combat_modifiers.yaml`, appended after the last monster resource-skill rule (the latest merged species' rule) and before the fatigue block:

```yaml
- id: jaw_drag_agility_flat
  when: {buff_active: jaw_drag}
  then: {agility_flat: -2}
```

- `world/rules/rulebook/status_display.yaml`, appended after the last monster resource-skill rows (the latest merged species' rows):

```yaml
- code: jaw_drag
  label: 咬腳拖拽
  severity: harmful
- code: jaw_drag_agility_flat
  label: 咬腳拖拽敏捷下降
  severity: harmful
```

- `world/skills/narration/data_martial.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "salt_jaw_haul",
        action=(
            "{actor} 一口咬住對手的腳踝，使勁往後一拖。",
            "{actor} 大顎死命鉗住對方，拖得對方腳步一沉。",
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

- Overview row, inserted in the `## 收錄總覽` table after the last `| 低階 |` row:

  `| 低階 | 負鹽蟻 | 西南海岸的鹽道、曬鹽場堤岸與橄欖林 | 大顎能銜起比自己重上好幾倍的鹽塊 | 搬鹽型、守丘型 |`

- New section at the end of `## 低階魔物`, immediately before `## 中階魔物` (after every low section an earlier programme change added), transcribed exactly:

````markdown
### 負鹽蟻

```bestiary
species: salt_column_ant
parent-species: salt_column_ant
default-variant: salt_hauler
variants:
  - key: salt_hauler
    status: delivered
  - key: salt_mound_soldier
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

**原型與棲地。**負鹽蟻是約手掌長的蟻類魔獸，成群生活於西南海岸的鹽道、曬鹽場堤岸與橄欖林的乾地。

**外觀。**赤褐色的身體分成頭、胸、腹三節，表面光滑發亮。頭部方大，一對鉗狀大顎的邊緣帶著細齒；六條腿細長，觸角在頭前不停擺動。

**生態與在地關係。**牠們在乾燥的土坡下挖出深巢，排成長列外出覓食，專找鹽粒、橄欖與掉落的乾果；巢口的土丘結著一層白鹽殼。鹽道城往海邊的鹽道上，運鹽的驢車常被蟻列攔住，麻袋被咬開，鹽粒一路漏進蟻巢。頭部特別大、守在巢丘上的兵蟻稱為守丘型。

**戰鬥中的表現。**牠的大顎與頸部帶著異常的力氣，一隻就能銜起比自己重上好幾倍的鹽塊，拖著倒退回巢。近身時，牠以大顎咬住對手的腳踝向後拖拽，咬中時讓對手腳下一沉，短時間內步伐遲緩。

| 變體 | 核准方向 |
| --- | --- |
| 搬鹽型 | 普通版本，排成長列在鹽道與曬鹽場之間搬運鹽粒 |
| 守丘型 | 頭部特別大、大顎特別寬的兵蟻，守在結著鹽殼的巢丘上，會咬向任何踩上巢丘的身影 |

**委託背景示例。**鹽道城外的鹽道邊冒出一座結滿鹽殼的新巢丘，蟻列橫過道路，這個月已有五袋鹽被咬破。鹽商行委託公會把蟻巢從道旁移走，讓驢車照常通行。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `salt_column_ant` | <implementation date> | read against the registry's published ecology field; the trouble stays local to a salt road and its donkey carts, and the hauling strength sits in the ant's own jaws | checked against the declared kit: the jaw haul is a single-target elementless physical strike that spends SP, and the section states that the brief slowed footing follows a bite that lands, matching the declared hit dependency; the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D6a. Seventh-batch approval notes (this change only)

- `docs/lore/monster-creation-guidelines.md`: directly after the paragraph that starts `**第六批核准（2026-11-11）：**` (added by `clod-ball-beetle-species`), add a paragraph:

  `**第七批核准（2026-11-12）：**西南海岸另行核准五種物種：低階的負鹽蟻與硬腕海星，中階的碎殼蝦與噴鹽鬣蜥，以及高階的沉船巨蛸。西部丘陵與谷地另行核准兩種物種：低階的坑道灶馬，以及中階的陷坑蟻獅。每個物種只出現在明確宣告的棲地、據點或遭遇中；災厄級物種與新的文明種族仍不在核准範圍內。`

- `docs/lore/bestiary.md`: directly after the paragraph that starts `**第六批核准：**`, add:

  `**第七批核准：**2026-11-12 起，西南海岸另行核准兩種低階、兩種中階與一種高階物種，西部丘陵與谷地另行核准一種低階與一種中階物種；各物種逐一收錄於下方現行小節。`

- `docs/development/monster-content-expansion.md`: append to the opening paragraph the sentence `Sections from 負鹽蟻 onward record the southwest coast and western hills species of the near-settlement programme's Wave 4.`

The user authorised the Wave 4 roster in the session that requested this change set. These notes record that approval. The species changes that follow do not edit them.

### D7. Tests

- `world/rules/tests/test_combat_modifiers.py::CombatModifierTests`: add `test_rule_jaw_drag_agility_flat`, copying the four lines of `test_rule_rock_echo_stagger_agility_flat` with `RULES["jaw_drag_agility_flat"]`. Copy those four lines exactly and assert no rule value of your own.

### D8. Developer review section

Append `## 負鹽蟻` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Small column worker: agility in the low band's middle, defense and hit points in its lower part.
* The kit spends no MP, so the MP pool is zero; SP holds three casts of the bite's SP cost (five on 守丘型).
* The rider (−2 agility for 12 s) equals the goblin's shipped −2 agility rider.
* The stronger 守丘型 guards a salt-crusted nest mound at grade E.
- `### Reuse of the enemy hit-rider representative`: the signature, the unchanged representative `cliff_stepper`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later key sorts before a representative] → every Wave 1, Wave 2, Wave 3 and Wave 4 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_sway_whistle_sparrow_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.rules.tests.test_combat_modifiers.CombatModifierTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change salt-column-ant-species` and `openspec validate salt-column-ant-species --strict`.
