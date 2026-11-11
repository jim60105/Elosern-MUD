# Design

## Context

See proposal.md (Why). Facts at `ae9185c9` plus the planned Wave 1 and Wave 2 species rows still open under `openspec/changes/*-species/`, which land first in the serial chain:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS` and `_VARIANT_DECLARATIONS` at import. Bands come from `MONSTER_TIER_REGISTRY`: low HP 25–70, attack 3–12, agility 3–12, defense 2–8, grades F–E; mid HP 110–230, attack 18–28, agility 10–24, defense 10–16, grades D–C; high HP 300–750, attack 26–40, agility 16–30, defense 18–32, grades B–A. `magic_power` must be 0 and MP/SP have no band. Display names are limited to 5 code points (`MONSTER_NAME_MAX_CODE_POINTS`).
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」 and `author_conjecture_zh` to contain 「尚未證實」, and it forbids registry strings that name a skill, behaviour or trait key.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by `(slot, effect family, audience, requires_hit_from)` and requires one committed representative per group, the group's sorted-minimum key. This kit's signature is `(("active", "damage", "enemies", None), ("active", "buff_apply", "enemies", 0))`, the shipped enemy hit-rider group, whose representative `cliff_stepper` is declared in `world.rules.tests.test_sway_whistle_sparrow_resource_skill`. Every new variant key sorts after `cliff_stepper` (as every Wave 1 and Wave 2 key does), so the representative does not move and no smoke module, shard entry or seed entry is added. `EnemyRiderGroupMemberTests` in that module derives the group's members from the shipped declarations, so both new variants are exercised on their own rider axis without a test edit. The skill is elementless with an SP-only cost, so `spell_tier_for` returns `None` (the goblin and wolverine precedent).
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests` requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, a magic tier for elemental MP skills (MP 10–16 single, 14–20 area) and `None` otherwise. `validate_catalog` requires one narration row per active skill, and `world/rules/status_display.py` fails closed for a buff or modifier without a display row.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, modifier rule, intelligence and mode entry, plus the referenced bindings. `world/rules/tests/test_monster_ai_activation.py` compares that fingerprint with `docs/development/monster-ai-activation-evidence/activation.json`.
- Every kit here carries a damage occurrence, so the legacy decision body proposes it and no utility binding or intelligence value is needed (`owned-kit-decision-coverage` applies only to support-only kits).

## Candidate review (`docs/lore/monster-creation-guidelines.md`)

| Question | Answer |
| --- | --- |
| Familiar archetype | A harbour seal hauling out on breakwaters. |
| Special way of life | Its belly fur carries an abnormal slick oil, so it slides several body lengths across wet stone with one heave. |
| World relation | Fishing boats moor inside the breakwaters of the southeast ports and dry their nets there (southeast coast terrain flavour: breakwaters and stone piers). |
| Ability limits | The oil is a body ability with no element; it freezes nothing and leaves the ground as it was. A landed slam knocks the target off balance, a brief agility rider; a miss changes nothing. |
| Local conflict | A colony packs the old breakwater so boats cannot moor and nets are torn, so the fishers' guild asks for the seals to be driven back to the outer rocks. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar), the Wave 1 species (spore-cap mushroom, moss-quill porcupine, hollow-tree bat, hush-wing owl, vine-net spider, moss-crown stag), the Wave 2 species (mountain frog, fire salamander, bearded vulture, giant moth, giant constrictor, capercaillie, beaver, mole, wolverine, griffin) and the other six Wave 3 species. It is an animal, clearly distinct from every beastfolk subspecies (wolf, cat, bear, rabbit, cattle, tiger, fox).

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `southeast-coast-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "breakwater_seal",
        "臥堤海豹",
        "臥堤海豹是體長超過一人的海豹類魔獸，成群棲息於東南海岸的防波堤、礁岩與河口沙洲。",
        "灰色短毛上散布著深色斑點，身軀圓滾，頭部渾圓，嘴邊一圈硬鬚。"
        "四肢化成鰭狀，後鰭向後並攏，上岸時以腹部貼地蠕行。",
        "牠們漲潮時下海捕魚，退潮後成群爬上防波堤與礁岩曬太陽。"
        "牠的腹毛帶著異常的滑油，在濕滑的石面上一挺身就能滑出好幾丈，比在沙地上爬行快得多。"
        "東南海岸的漁船靠防波堤內側停泊，臥堤海豹群會占滿堤上的繫船石與曬網架，扯破攤開的漁網，搶食網中漁獲。"
        "近身時，牠挺身沿著濕地滑向對手，以整個身軀壓撞過去，撞中時讓對手在濕滑的地面上失去重心，短時間內腳步遲緩。",
        ("southeast_coast",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；腹毛滑油的成因不在設定中交代。",
        "（作者私有：作者解釋）中階群居海豹：腹毛滑油屬於身體能力，不帶元素、不讓地面結冰或持續濕滑；戰鬥呈現為滑行壓撞與命中後短暫敏捷下降。描寫維持海豹體態，不與任何獸人亞種相比。連結漁船停泊的防波堤與曬網架。",
        "（作者私有：尚未證實的猜想）金穗港的老船夫說臥堤海豹全群提早下海的日子，午後必有大浪，這種說法尚未證實。",
        "pier_basker",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "pier_basker",
        "breakwater_seal",
        "曬堤型",
        "普通版本，退潮後成群爬上防波堤與礁岩曬太陽。",
        "mid",
        True,
        MonsterCombatProfile(
            hp=160, mp=0, sp=24, atk_phys=21, agility=12, defense=13, magic_power=0
        ),
        "D",
        True,
        active_skill_keys=("flipper_slide_slam",),
        passive_skill_keys=(),
        behaviour_profile_key="pack_hunter",
    ),
```

```python
    MonsterVariant(
        "haulout_bull",
        "breakwater_seal",
        "霸灘型",
        "占住整片沙洲、帶著一群母海豹的大型公海豹，會滑向任何踏上沙洲的身影。",
        "mid",
        False,
        MonsterCombatProfile(
            hp=215, mp=0, sp=36, atk_phys=26, agility=12, defense=15, magic_power=0
        ),
        "C",
        True,
        active_skill_keys=("flipper_slide_slam",),
        passive_skill_keys=(),
        behaviour_profile_key="pack_hunter",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "flipper_slide_slam",
        "滑身壓撞",
        "挺身沿著濕地滑向單一敵方目標，以整個身軀壓撞，造成物理傷害；命中後讓對手在濕滑的地面上失去重心，短暫降低其敏捷。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"sp": 6},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        effects=["damage:none:physical", "buff_apply:slick_topple"],
        category=SkillCategory.MARTIAL_ARTS,
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("breakwater_seal",),
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
# 魔物資源技能（東南海岸第三波）：臥堤海豹滑身壓撞：命中後失去重心的 mount，agility_flat −3 資料在 combat_modifiers.yaml 的 slick_topple_agility_flat 列（rock_echo_stagger_agility_flat 的 agility_flat 先例）。
- key: slick_topple
  duration: 15
  stacking: refresh
  polarity: debuff
  modifiers: {}
```

- `world/rules/rulebook/combat_modifiers.yaml`, appended after the last monster resource-skill rule (the latest merged species' rule) and before the fatigue block:

```yaml
- id: slick_topple_agility_flat
  when: {buff_active: slick_topple}
  then: {agility_flat: -3}
```

- `world/rules/rulebook/status_display.yaml`, appended after the last monster resource-skill rows (the latest merged species' rows):

```yaml
- code: slick_topple
  label: 滑倒失衡
  severity: harmful
- code: slick_topple_agility_flat
  label: 滑倒失衡敏捷下降
  severity: harmful
```

- `world/skills/narration/data_martial.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "flipper_slide_slam",
        action=(
            "{actor} 挺起身子沿著濕石一滑，整個身軀撞向對手。",
            "{actor} 圓滾的身軀壓了過去，對方腳下一滑。",
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

  `| 中階 | 臥堤海豹 | 東南海岸的防波堤、礁岩與河口沙洲 | 腹毛的滑油讓牠在濕石上一滑數丈 | 曬堤型、霸灘型 |`

- New section at the end of `## 中階魔物`, immediately before `## 高階魔物` (after every mid section an earlier programme change added), transcribed exactly:

````markdown
### 臥堤海豹

```bestiary
species: breakwater_seal
parent-species: breakwater_seal
default-variant: pier_basker
variants:
  - key: pier_basker
    status: delivered
  - key: haulout_bull
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

**原型與棲地。**臥堤海豹是體長超過一人的海豹類魔獸，成群棲息於東南海岸的防波堤、礁岩與河口沙洲。

**外觀。**灰色短毛上散布著深色斑點，身軀圓滾，頭部渾圓，嘴邊一圈硬鬚。四肢化成鰭狀，後鰭向後並攏，上岸時以腹部貼地蠕行。

**生態與在地關係。**牠們漲潮時下海捕魚，退潮後成群爬上防波堤與礁岩曬太陽。東南海岸的漁船靠防波堤內側停泊，臥堤海豹群會占滿堤上的繫船石與曬網架，扯破攤開的漁網，搶食網中漁獲。占住整片沙洲、帶著一群母海豹的大型公海豹稱為霸灘型。

**戰鬥中的表現。**牠的腹毛帶著異常的滑油，在濕滑的石面上一挺身就能滑出好幾丈。近身時，牠挺身沿著濕地滑向對手，以整個身軀壓撞過去，撞中時讓對手在濕滑的地面上失去重心，短時間內腳步遲緩；撞空時對手照常站穩。

| 變體 | 核准方向 |
| --- | --- |
| 曬堤型 | 普通版本，退潮後成群爬上防波堤與礁岩曬太陽 |
| 霸灘型 | 占住整片沙洲、帶著一群母海豹的大型公海豹，會滑向任何踏上沙洲的身影 |

**委託背景示例。**南岬港外的舊防波堤被一群臥堤海豹占滿，漁船靠不了岸，曬網架上的漁網也被扯破了三張。漁會委託公會把海豹群趕回外側的礁岩，讓漁船在入秋前能照常停泊。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `breakwater_seal` | <implementation date> | read against the registry's published ecology field; the trouble stays local to a breakwater mooring and its net racks, and the slide comes from the seal's own oiled belly fur | checked against the declared kit: the sliding body slam is a single-target elementless physical strike that spends SP, and the section states that the brief loss of footing follows a slam that lands, matching the declared hit dependency; the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D7. Tests

- `world/rules/tests/test_combat_modifiers.py::CombatModifierTests`: add `test_rule_slick_topple_agility_flat`, copying the four lines of `test_rule_rock_echo_stagger_agility_flat` with `RULES["slick_topple_agility_flat"]`. Copy those four lines exactly and assert no rule value of your own.

### D8. Developer review section

Append `## 臥堤海豹` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Heavy colony slider: hit points and defense in the mid band's middle, higher on the stronger 霸灘型, agility near the band's floor.
* The kit spends no MP, so the MP pool is zero; SP holds four casts of the slam's SP cost.
* The rider (−3 agility for 15 s) equals the goat's shipped agility rider.
* The stronger 霸灘型 holds a sandbar at grade C.
- `### Reuse of the enemy hit-rider representative`: the signature, the unchanged representative `cliff_stepper`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later key sorts before a representative] → every Wave 1, Wave 2 and Wave 3 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_sway_whistle_sparrow_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.rules.tests.test_combat_modifiers.CombatModifierTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change breakwater-seal-species` and `openspec validate breakwater-seal-species --strict`.
