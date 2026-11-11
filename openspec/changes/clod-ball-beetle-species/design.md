# Design

## Context

See proposal.md (Why). Facts at `ae9185c9` plus the planned Wave 1 and Wave 2 species rows still open under `openspec/changes/*-species/`, which land first in the serial chain:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS` and `_VARIANT_DECLARATIONS` at import. Bands come from `MONSTER_TIER_REGISTRY`: low HP 25–70, attack 3–12, agility 3–12, defense 2–8, grades F–E; mid HP 110–230, attack 18–28, agility 10–24, defense 10–16, grades D–C; high HP 300–750, attack 26–40, agility 16–30, defense 18–32, grades B–A. `magic_power` must be 0 and MP/SP have no band. Display names are limited to 5 code points (`MONSTER_NAME_MAX_CODE_POINTS`).
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」 and `author_conjecture_zh` to contain 「尚未證實」, and it forbids registry strings that name a skill, behaviour or trait key.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by `(slot, effect family, audience, requires_hit_from)` and requires one committed representative per group, the group's sorted-minimum key. This kit's signature is `(("active", "damage", "enemies", None), ("active", "buff_apply", "enemies", 0))`, the shipped enemy hit-rider group, whose representative `cliff_stepper` is declared in `world.rules.tests.test_sway_whistle_sparrow_resource_skill`. Every new variant key sorts after `cliff_stepper` (as every Wave 1 and Wave 2 key does), so the representative does not move and no smoke module, shard entry or seed entry is added. `EnemyRiderGroupMemberTests` in that module derives the group's members from the shipped declarations, so both new variants are exercised on their own rider axis without a test edit. The rider lowers flat agility (`agility_flat`), the axis of the goat's and the goblin's shipped riders.
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests` requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, a magic tier for elemental MP skills (MP 10–16 single, 14–20 area) and `None` otherwise. `validate_catalog` requires one narration row per active skill, and `world/rules/status_display.py` fails closed for a buff or modifier without a display row.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, modifier rule, intelligence and mode entry, plus the referenced bindings. `world/rules/tests/test_monster_ai_activation.py` compares that fingerprint with `docs/development/monster-ai-activation-evidence/activation.json`.
- Every kit here carries a damage occurrence, so the legacy decision body proposes it and no utility binding or intelligence value is needed (`owned-kit-decision-coverage` applies only to support-only kits).

## Candidate review (`docs/lore/monster-creation-guidelines.md`)

| Question | Answer |
| --- | --- |
| Familiar archetype | A dung beetle (ball-rolling scarab) of pastures. |
| Special way of life | Faint earth power compacts the dung-and-soil balls it rolls until they are stone-hard, so its brood balls survive gravel roads and rain. |
| World relation | Grandia's pastures and fields flank the official roads: 東牧鎮 ox carts and the small sluices of the irrigation canals (eastern plains terrain flavour: official roads, ox carts, irrigation canals). |
| Ability limits | The power acts only on balls it has rolled; it changes no terrain and opens no pits. A landed shove leaves a brief agility rider through bad footing (earth element: footing and fixed defense, magic-system §3); a miss changes nothing. |
| Local conflict | Hard balls on the official road jolt ox carts into the ditch, so a rancher asks for the brood heap beside the road to be moved. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar), the Wave 1 species (spore-cap mushroom, moss-quill porcupine, hollow-tree bat, hush-wing owl, vine-net spider, moss-crown stag), the Wave 2 species (mountain frog, fire salamander, bearded vulture, giant moth, giant constrictor, capercaillie, beaver, mole, wolverine, griffin) and the other six Wave 3 species. It is an animal, clearly distinct from every beastfolk subspecies (wolf, cat, bear, rabbit, cattle, tiger, fox).

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `eastern-plains-deep-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "clod_ball_beetle",
        "滾土甲蟲",
        "滾土甲蟲是約拳頭大小的甲蟲類魔獸，成對生活於東部大平原的牧場、官道與田埂一帶。",
        "黑亮的甲殼泛著深綠光澤，頭部前端長著一片鏟狀寬板。"
        "前腳扁平帶齒，適合推土與挖掘；"
        "後腳細長，能倒退著推動比自己大上數倍的土球。",
        "牠們把牧場的牛糞與田土揉成圓球，倒退著推回地洞，在土球裡產卵育幼。"
        "牠能以微弱土屬性力量讓揉好的土球迅速壓實，壓實後的土球硬如石塊，推過碎石路也不會散開。"
        "東部的官道兩側是牧場與田地，滾土甲蟲常把土球推上路面，牛車輪子壓到硬球就會顛簸卡住；"
        "牠們埋在田邊的土球，也會堵住灌溉渠的小水門。"
        "近身時，牠低頭以鏟狀頭板頂撞對手，同時把土球滾向對手腳邊，撞中時讓對手腳步一絆、短暫慢下來。",
        ("eastern_plains",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；壓實土球之力的成因不在設定中交代。",
        "（作者私有：作者解釋）低階成對生活的甲蟲：土屬性力量只讓自己揉成的土球壓實，不改變地形、不造成陷落；戰鬥呈現為頭板頂撞與命中後短暫敏捷下降（土讓腳下變壞）。連結官道牛車與灌溉渠水門。",
        "（作者私有：尚未證實的猜想）東牧鎮的牧人說滾土甲蟲把土球推往哪個方向，隔天的風就往哪裡吹，這種說法尚未證實。",
        "road_ball_roller",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "road_ball_roller",
        "clod_ball_beetle",
        "滾球型",
        "普通版本，成對推著土球在牧場與官道之間來回。",
        "low",
        True,
        MonsterCombatProfile(
            hp=38, mp=20, sp=9, atk_phys=5, agility=4, defense=6, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("clod_ball_shove",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

```python
    MonsterVariant(
        "heap_brood_keeper",
        "clod_ball_beetle",
        "育堆型",
        "守著牧場邊一整座育幼土堆的大型個體，甲殼最厚，會正面頂撞靠近土堆的身影。",
        "low",
        False,
        MonsterCombatProfile(
            hp=60, mp=30, sp=15, atk_phys=10, agility=4, defense=8, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("clod_ball_shove",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "clod_ball_shove",
        "鏟頭滾球",
        "以土屬性力量壓實土球後，以鏟狀頭板頂撞單一敵方目標，造成物理傷害；命中後讓土球絆住對手腳步，短暫降低其敏捷。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 3},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="earth",
        effects=["damage:earth:physical", "buff_apply:clod_stumble"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="earth",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("clod_ball_beetle",),
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
# 魔物資源技能（東部大平原第三波）：滾土甲蟲鏟頭滾球：命中後土球絆住腳步的 mount，agility_flat −2 資料在 combat_modifiers.yaml 的 clod_stumble_agility_flat 列（sticky_palm_drag_agility_flat 的 agility_flat 先例）。
- key: clod_stumble
  duration: 12
  stacking: refresh
  polarity: debuff
  modifiers: {}
```

- `world/rules/rulebook/combat_modifiers.yaml`, appended after the last monster resource-skill rule (the latest merged species' rule) and before the fatigue block:

```yaml
- id: clod_stumble_agility_flat
  when: {buff_active: clod_stumble}
  then: {agility_flat: -2}
```

- `world/rules/rulebook/status_display.yaml`, appended after the last monster resource-skill rows (the latest merged species' rows):

```yaml
- code: clod_stumble
  label: 土球絆腳
  severity: harmful
- code: clod_stumble_agility_flat
  label: 土球絆腳敏捷下降
  severity: harmful
```

- `world/skills/narration/data_earth.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "clod_ball_shove",
        action=(
            "{actor} 低頭一頂，壓得死硬的土球滾向對手腳邊。",
            "{actor} 倒退著推出土球，鏟狀頭板跟著撞了上去。",
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

  `| 低階 | 滾土甲蟲 | 東部大平原的牧場、官道與田埂 | 以土屬性力量把土球壓得硬如石塊 | 滾球型、育堆型 |`

- New section at the end of `## 低階魔物`, immediately before `## 中階魔物` (after every low section an earlier programme change added), transcribed exactly:

````markdown
### 滾土甲蟲

```bestiary
species: clod_ball_beetle
parent-species: clod_ball_beetle
default-variant: road_ball_roller
variants:
  - key: road_ball_roller
    status: delivered
  - key: heap_brood_keeper
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

**原型與棲地。**滾土甲蟲是約拳頭大小的甲蟲類魔獸，成對生活於東部大平原的牧場、官道與田埂一帶。

**外觀。**黑亮的甲殼泛著深綠光澤，頭部前端長著一片鏟狀寬板。前腳扁平帶齒，適合推土與挖掘；後腳細長，能倒退著推動比自己大上數倍的土球。

**生態與在地關係。**牠們把牧場的牛糞與田土揉成圓球，倒退著推回地洞，在土球裡產卵育幼。東部的官道兩側是牧場與田地，滾土甲蟲常把土球推上路面，牛車輪子壓到硬球就會顛簸卡住；牠們埋在田邊的土球，也會堵住灌溉渠的小水門。守著牧場邊一整座育幼土堆、甲殼最厚的大型個體稱為育堆型。

**戰鬥中的表現。**牠能以微弱土屬性力量讓揉好的土球迅速壓實，壓實後的土球硬如石塊，推過碎石路也不會散開。近身時，牠低頭以鏟狀頭板頂撞對手，同時把土球滾向對手腳邊，撞中時讓對手腳步一絆、短暫慢下來；撞空時土球滾到一旁，對手腳步照常。

| 變體 | 核准方向 |
| --- | --- |
| 滾球型 | 普通版本，成對推著土球在牧場與官道之間來回 |
| 育堆型 | 守著牧場邊一整座育幼土堆的大型個體，甲殼最厚，會正面頂撞靠近土堆的身影 |

**委託背景示例。**東牧鎮往帝河津的官道上，這個月接連有三輛運牛乳的牛車壓上硬土球，車輪卡進了路旁的溝裡。牧場主委託公會找出路旁那座由育堆型守著的土堆，把甲蟲們請離官道兩側。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `clod_ball_beetle` | <implementation date> | read against the registry's published ecology field; the trouble stays local to ranch-side official roads and small irrigation sluices, and the firming acts only on the beetle's own soil balls | checked against the declared kit: the head shove is a single-target earth-element physical strike, and the section states that the brief stumble follows a shove that lands, matching the declared hit dependency; the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D6a. Sixth-batch approval notes (this change only)

- `docs/lore/monster-creation-guidelines.md`: directly after the paragraph that starts `**第五批核准（2026-11-11）：**` (added by `mist-spring-frog-species`), add a paragraph:

  `**第六批核准（2026-11-11）：**東部大平原另行核准四種物種：低階的滾土甲蟲，中階的揚塵野馬與渠矛蒼鷺，以及高階的湖丘巨龜。東南海岸另行核准三種物種：低階的灘跳魚與桅風海鷗，以及中階的臥堤海豹。每個物種只出現在明確宣告的棲地、據點或遭遇中；災厄級物種與新的文明種族仍不在核准範圍內。`

- `docs/lore/bestiary.md`: directly after the paragraph that starts `**第五批核准：**`, add:

  `**第六批核准：**2026-11-11 起，東部大平原另行核准一種低階、兩種中階與一種高階物種，東南海岸另行核准兩種低階與一種中階物種；各物種逐一收錄於下方現行小節。`

- `docs/development/monster-content-expansion.md`: append to the opening paragraph the sentence `Sections from 滾土甲蟲 onward record the eastern plains and southeast coast species of the near-settlement programme's Wave 3.`

The user authorised the Wave 3 roster in the session that requested this change set. These notes record that approval. The species changes that follow do not edit them.

### D7. Tests

- `world/rules/tests/test_combat_modifiers.py::CombatModifierTests`: add `test_rule_clod_stumble_agility_flat`, copying the four lines of `test_rule_rock_echo_stagger_agility_flat` with `RULES["clod_stumble_agility_flat"]`. Copy those four lines exactly and assert no rule value of your own.

### D8. Developer review section

Append `## 滾土甲蟲` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Armoured slow pusher: defense equal to the beaver's ordinary variant, agility in the low band's lower half.
* MP holds two casts of the shove's MP cost; SP holds three casts of its SP cost.
* The rider (−2 agility for 12 s) equals the goblin's shipped −2 agility rider, the smallest shipped agility magnitude.
* The stronger 育堆型 guards a brood heap at grade E with the low band's defense ceiling.
- `### Reuse of the enemy hit-rider representative`: the signature, the unchanged representative `cliff_stepper`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later key sorts before a representative] → every Wave 1, Wave 2 and Wave 3 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_sway_whistle_sparrow_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.rules.tests.test_combat_modifiers.CombatModifierTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change clod-ball-beetle-species` and `openspec validate clod-ball-beetle-species --strict`.
