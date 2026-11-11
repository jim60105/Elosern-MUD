# Design

## Context

See proposal.md (Why). Facts at `cf4643a1` plus the planned Wave 2, Wave 3 and earlier Wave 4 species rows still open under `openspec/changes/*-species/`, which land first in the serial chain:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS` and `_VARIANT_DECLARATIONS` at import. Bands come from `MONSTER_TIER_REGISTRY`: low HP 25–70, attack 3–12, agility 3–12, defense 2–8, grades F–E; mid HP 110–230, attack 18–28, agility 10–24, defense 10–16, grades D–C; high HP 300–750, attack 26–40, agility 16–30, defense 18–32, grades B–A. `magic_power` must be 0 and MP/SP have no band. Display names are limited to 5 code points (`MONSTER_NAME_MAX_CODE_POINTS`).
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」 and `author_conjecture_zh` to contain 「尚未證實」, and it forbids registry strings that name a skill, behaviour or trait key.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by `(slot, effect family, audience, requires_hit_from)` and requires one committed representative per group, the group's sorted-minimum key. This kit's signature is `(("active", "damage", "enemies", None), ("active", "buff_apply", "enemies", 0))`, the shipped enemy hit-rider group, whose representative `cliff_stepper` is declared in `world.rules.tests.test_sway_whistle_sparrow_resource_skill`. Every new variant key sorts after `cliff_stepper` (as every Wave 1, Wave 2 and Wave 3 key does), so the representative does not move and no smoke module, shard entry or seed entry is added. `EnemyRiderGroupMemberTests` in that module derives the group's members from the shipped declarations, so both new variants are exercised on their own rider axis without a test edit. The rider lowers accuracy (`accuracy`), the axis of the sparrow's and the mushroom's shipped riders. The skill is elementless with an SP-only cost, so `spell_tier_for` returns `None` (the goblin and wolverine precedent).
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests` requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, a magic tier for elemental MP skills (MP 10–16 single, 14–20 area) and `None` otherwise. `validate_catalog` requires one narration row per active skill, and `world/rules/status_display.py` fails closed for a buff or modifier without a display row.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, modifier rule, intelligence and mode entry, plus the referenced bindings. `world/rules/tests/test_monster_ai_activation.py` compares that fingerprint with `docs/development/monster-ai-activation-evidence/activation.json`.
- Every kit here carries a damage occurrence, so the legacy decision body proposes it and no utility binding or intelligence value is needed (`owned-kit-decision-coverage` applies only to support-only kits).

## Candidate review (`docs/lore/monster-creation-guidelines.md`)

| Question | Answer |
| --- | --- |
| Familiar archetype | A marine iguana of black sea cliffs. |
| Special way of life | Its nasal salt glands concentrate the sea salt it swallows into brine with abnormal strength and snort it out hard, so its head wears a thick white salt crust. |
| World relation | The salt pans walled with stone dikes below the sea cliffs and the seaweed the fishing villages dry on the rocks (southwest coast terrain flavour: sea cliffs, fishing villages, salt pans). |
| Ability limits | The brine is a body ability with no element; it carries no poison and leaves no lasting harm. A landed butt sprays brine into the eyes, a brief accuracy rider; a miss sprays nothing. |
| Local conflict | A colony led by a crested male packs a salt-pan dike and sprays the salt workers, so the salt-pan owner asks for the colony to be driven back up the cliff before the autumn harvest. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar), the Wave 1 species (spore-cap mushroom, moss-quill porcupine, hollow-tree bat, hush-wing owl, vine-net spider, moss-crown stag), the Wave 2 species (mountain frog, fire salamander, bearded vulture, giant moth, giant constrictor, capercaillie, beaver, mole, wolverine, griffin), the Wave 3 species (dung beetle, wild horse, grey heron, giant snapping turtle, mudskipper, herring gull, harbour seal) and the other six Wave 4 species (giant harvester ant of dry salt roads, sea star of rock pools and oyster racks, mantis shrimp of harbour shallows, giant octopus of sea caves (kraken folklore), cave cricket of mines and cellars, antlion larva of quarry sand). It is an animal, clearly distinct from every beastfolk subspecies (wolf, cat, bear, rabbit, cattle, tiger, fox).

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `southwest-coast-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "salt_snort_iguana",
        "噴鹽鬣蜥",
        "噴鹽鬣蜥是體長超過一人的鬣蜥類魔獸，成群棲息於西南海岸的黑色海崖與崖下的曬鹽場。",
        "深灰近黑的鱗皮粗糙如岩，背脊上一排尖刺從頸後延伸到尾根。"
        "頭部短而鈍圓，鼻孔周圍與頭頂結著一層白色鹽殼，四肢粗壯，爪子彎長。",
        "牠們白天成群趴在被太陽曬暖的崖石上，退潮時潛到崖腳啃食礁石上的海藻。"
        "牠鼻內的鹽腺帶著異常的力氣，能把吃進的海鹽濃成鹽水，猛力從鼻孔噴出，頭頂因此結著一層厚實的白鹽殼。"
        "海崖下的曬鹽場以石堤圍出成排的鹽田，堤面被太陽曬得溫熱，噴鹽鬣蜥常整群爬上堤面曬太陽，壓碎剛結好的鹽層，也把漁村攤在礁石上晾曬的海藻吃個精光。"
        "近身時，牠以鈍圓的頭頂撞對手，撞中時從鼻孔噴出一股濃鹽水，刺得對手短時間內看不準目標。",
        ("southwest_coast",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；鼻內鹽腺異常力氣的成因不在設定中交代。",
        "（作者私有：作者解釋）中階群居鬣蜥：鹽腺噴鹽屬於身體能力，不帶元素、不造成中毒或持續傷害；戰鬥呈現為頂撞與命中後短暫命中下降。描寫維持蜥蜴體態，不與鱷魚或蠑螈混同。連結海崖下的曬鹽場鹽田與漁村晾曬的海藻。",
        "（作者私有：尚未證實的猜想）曬鹽場的鹽工說噴鹽鬣蜥一整天都留在崖上的日子，隔天必定下雨，這種說法尚未證實。",
        "seacliff_basker",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "seacliff_basker",
        "salt_snort_iguana",
        "曬崖型",
        "普通版本，成群趴在曬暖的崖石上，退潮時潛到崖腳啃食海藻。",
        "mid",
        True,
        MonsterCombatProfile(
            hp=150, mp=0, sp=24, atk_phys=20, agility=12, defense=14, magic_power=0
        ),
        "D",
        True,
        active_skill_keys=("brine_snort_butt",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

```python
    MonsterVariant(
        "salt_dike_holder",
        "salt_snort_iguana",
        "冠刺型",
        "背刺最高、鹽殼最厚的大型雄蜥，帶著一群母蜥占住曬鹽場最溫暖的一段堤面，會頂向任何走上那段堤面的身影。",
        "mid",
        False,
        MonsterCombatProfile(
            hp=205, mp=0, sp=36, atk_phys=25, agility=12, defense=16, magic_power=0
        ),
        "C",
        True,
        active_skill_keys=("brine_snort_butt",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "brine_snort_butt",
        "噴鹽頂撞",
        "以鈍圓的頭頂撞單一敵方目標，造成物理傷害；命中後從鼻孔噴出濃鹽水刺進對手眼中，短暫降低其命中。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"sp": 6},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        effects=["damage:none:physical", "buff_apply:brine_sting"],
        category=SkillCategory.MARTIAL_ARTS,
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("salt_snort_iguana",),
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
# 魔物資源技能（西南海岸第四波）：噴鹽鬣蜥噴鹽頂撞：命中後鹽水刺眼的 mount，accuracy −3 資料在 combat_modifiers.yaml 的 brine_sting_accuracy 列（spore_haze_accuracy 的 accuracy 先例）。
- key: brine_sting
  duration: 15
  stacking: refresh
  polarity: debuff
  modifiers: {}
```

- `world/rules/rulebook/combat_modifiers.yaml`, appended after the last monster resource-skill rule (the latest merged species' rule) and before the fatigue block:

```yaml
- id: brine_sting_accuracy
  when: {buff_active: brine_sting}
  then: {accuracy: -3}
```

- `world/rules/rulebook/status_display.yaml`, appended after the last monster resource-skill rows (the latest merged species' rows):

```yaml
- code: brine_sting
  label: 鹽水刺眼
  severity: harmful
- code: brine_sting_accuracy
  label: 鹽水刺眼命中下降
  severity: harmful
```

- `world/skills/narration/data_martial.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "brine_snort_butt",
        action=(
            "{actor} 低頭一頂，鼻孔裡噴出一股鹽水。",
            "{actor} 結著鹽殼的頭撞了過來，鹽水濺得對方睜不開眼。",
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

  `| 中階 | 噴鹽鬣蜥 | 西南海岸的黑色海崖與崖下的曬鹽場 | 鼻內鹽腺能把海鹽濃成鹽水猛力噴出 | 曬崖型、冠刺型 |`

- New section at the end of `## 中階魔物`, immediately before `## 高階魔物` (after every mid section an earlier programme change added), transcribed exactly:

````markdown
### 噴鹽鬣蜥

```bestiary
species: salt_snort_iguana
parent-species: salt_snort_iguana
default-variant: seacliff_basker
variants:
  - key: seacliff_basker
    status: delivered
  - key: salt_dike_holder
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

**原型與棲地。**噴鹽鬣蜥是體長超過一人的鬣蜥類魔獸，成群棲息於西南海岸的黑色海崖與崖下的曬鹽場。

**外觀。**深灰近黑的鱗皮粗糙如岩，背脊上一排尖刺從頸後延伸到尾根。頭部短而鈍圓，鼻孔周圍與頭頂結著一層白色鹽殼，四肢粗壯，爪子彎長。

**生態與在地關係。**牠們白天成群趴在被太陽曬暖的崖石上，退潮時潛到崖腳啃食礁石上的海藻。海崖下的曬鹽場以石堤圍出成排的鹽田，堤面被太陽曬得溫熱，噴鹽鬣蜥常整群爬上堤面曬太陽，壓碎剛結好的鹽層，也把漁村攤在礁石上晾曬的海藻吃個精光。背刺最高、帶著一群母蜥占住最溫暖堤面的大型雄蜥稱為冠刺型。

**戰鬥中的表現。**牠鼻內的鹽腺帶著異常的力氣，能把吃進的海鹽濃成鹽水，猛力從鼻孔噴出，頭頂因此結著一層厚實的白鹽殼。近身時，牠以鈍圓的頭頂撞對手，撞中時從鼻孔噴出一股濃鹽水，刺得對手短時間內看不準目標。

| 變體 | 核准方向 |
| --- | --- |
| 曬崖型 | 普通版本，成群趴在曬暖的崖石上，退潮時潛到崖腳啃食海藻 |
| 冠刺型 | 背刺最高、鹽殼最厚的大型雄蜥，帶著一群母蜥占住曬鹽場最溫暖的一段堤面，會頂向任何走上那段堤面的身影 |

**委託背景示例。**漁灣鎮西邊海崖下的曬鹽場，這一季有整片鹽田被一群噴鹽鬣蜥占住，鹽工一靠近就被鹽水噴了滿臉。鹽場主委託公會把帶頭的冠刺型與蜥群趕回崖上，讓鹽工趕在秋風前收完今年的鹽。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `salt_snort_iguana` | <implementation date> | read against the registry's published ecology field; the trouble stays local to the dikes of a cliff-foot salt pan and a fishing village's drying seaweed, and the brine comes from the iguana's own nasal salt glands | checked against the declared kit: the head butt is a single-target elementless physical strike that spends SP, and the section states that the stinging brine follows a butt that lands, matching the declared hit dependency; the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D7. Tests

- `world/rules/tests/test_combat_modifiers.py::CombatModifierTests`: add `test_rule_brine_sting_accuracy`, copying the four lines of `test_rule_rock_echo_stagger_agility_flat` with `RULES["brine_sting_accuracy"]`. Copy those four lines exactly and assert no rule value of your own.

### D8. Developer review section

Append `## 噴鹽鬣蜥` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Heavy basker: defense in the mid band's upper part, agility near its floor, hit points just below its middle.
* The kit spends no MP, so the MP pool is zero; SP holds four casts of the butt's SP cost (six on 冠刺型).
* The rider (−3 accuracy for 15 s) matches the mushroom's shipped −3 accuracy rider in size and lasts three seconds longer.
* The stronger 冠刺型 holds the warmest dike stretch at grade C with the mid band's defense ceiling.
- `### Reuse of the enemy hit-rider representative`: the signature, the unchanged representative `cliff_stepper`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later key sorts before a representative] → every Wave 1, Wave 2, Wave 3 and Wave 4 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_sway_whistle_sparrow_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.rules.tests.test_combat_modifiers.CombatModifierTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change salt-snort-iguana-species` and `openspec validate salt-snort-iguana-species --strict`.
