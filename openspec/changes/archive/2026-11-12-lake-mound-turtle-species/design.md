# Design

## Context

See proposal.md (Why). Facts at `ae9185c9` plus the planned Wave 1 and Wave 2 species rows still open under `openspec/changes/*-species/`, which land first in the serial chain:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS` and `_VARIANT_DECLARATIONS` at import. Bands come from `MONSTER_TIER_REGISTRY`: low HP 25–70, attack 3–12, agility 3–12, defense 2–8, grades F–E; mid HP 110–230, attack 18–28, agility 10–24, defense 10–16, grades D–C; high HP 300–750, attack 26–40, agility 16–30, defense 18–32, grades B–A. `magic_power` must be 0 and MP/SP have no band. Display names are limited to 5 code points (`MONSTER_NAME_MAX_CODE_POINTS`).
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」 and `author_conjecture_zh` to contain 「尚未證實」, and it forbids registry strings that name a skill, behaviour or trait key.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by `(slot, effect family, audience, requires_hit_from)` and requires one committed representative per group, the group's sorted-minimum key. This kit's signature is `(("active", "damage", "enemies", None), ("active", "damage", "enemies", None))`, the shipped two-strike (single + area damage) group, whose representative `warm_den_boar` is declared in `world.rules.tests.test_ember_bristle_boar_resource_skill`. Every new variant key sorts after `warm_den_boar` (as every Wave 1 and Wave 2 key does), so the representative does not move and no smoke module, shard entry or seed entry is added. `"warm_den_boar" < "wide_mound_elder"`, so the boar stays the representative and no smoke module is added.
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests` requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, a magic tier for elemental MP skills (MP 10–16 single, 14–20 area) and `None` otherwise. `validate_catalog` requires one narration row per active skill, and `world/rules/status_display.py` fails closed for a buff or modifier without a display row.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, modifier rule, intelligence and mode entry, plus the referenced bindings. `world/rules/tests/test_monster_ai_activation.py` compares that fingerprint with `docs/development/monster-ai-activation-evidence/activation.json`.
- Every kit here carries a damage occurrence, so the legacy decision body proposes it and no utility binding or intelligence value is needed (`owned-kit-decision-coverage` applies only to support-only kits).

## Candidate review (`docs/lore/monster-creation-guidelines.md`)

| Question | Answer |
| --- | --- |
| Familiar archetype | A giant snapping turtle of lakes and marshes. |
| Special way of life | Earth power firms the lake mud on its own shell, so the mud layer and its reeds grow year by year and the resting turtle reads as a reed mound. |
| World relation | The fishers of 沉鐘鎮 and the lake district of the north-eastern plain net around the reed mounds of the lake (settlement: lake town of the far north-eastern plain). |
| Ability limits | The earth power acts on the mud of its own shell and on the ground it slams; it raises no earthquake and reshapes no shore. No divinity, guardian mission or elven tie; when its magic and stamina are spent it falls back to plain bites. |
| Local conflict | The named turtle 白蘆 keeps surfacing at the boats' netting ground and capsizes skiffs, so the fishers' guild posts a commission for a skilled party. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar), the Wave 1 species (spore-cap mushroom, moss-quill porcupine, hollow-tree bat, hush-wing owl, vine-net spider, moss-crown stag), the Wave 2 species (mountain frog, fire salamander, bearded vulture, giant moth, giant constrictor, capercaillie, beaver, mole, wolverine, griffin) and the other six Wave 3 species. It is an animal, clearly distinct from every beastfolk subspecies (wolf, cat, bear, rabbit, cattle, tiger, fox).

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `eastern-plains-deep-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "lake_mound_turtle",
        "湖丘巨龜",
        "湖丘巨龜是背甲寬過一座小屋的巨大龜類魔獸，獨自棲息於東部大平原東北的湖沼深處。",
        "背甲上糊著一層厚實的湖泥，長滿蘆葦與水草，露出水面時看起來是一座小土丘。"
        "頭部粗大，鉤狀上顎的邊緣厚鈍如石，四肢粗短，覆著灰黑色的硬鱗。",
        "牠一年裡大半時間靜臥在湖底，以路過的大魚與水鳥為食。"
        "牠能以土屬性力量讓背甲上的湖泥結得緊實，泥層一年比一年厚，上頭的蘆葦也越長越高。"
        "沉鐘鎮與周邊湖畔的漁人熟悉湖上每一座蘆葦小丘，下網時會避開會移動的那一座。"
        "牠以巨顎咬住單一對手，也會撐起身軀把背甲猛力砸向地面，讓身旁的泥地一陣翻湧，撞向四周所有對手；"
        "兩者都耗費牠自身的魔力與體力。"
        "首隻指定個體的背甲上長著一叢秋天開白花的蘆葦，被稱為「白蘆」。",
        ("eastern_plains",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；背甲泥層緊實之力的成因不在設定中交代。",
        "（作者私有：作者解釋）高階獨居巨龜：土屬性只讓自身背甲上的湖泥緊實，並在砸地時讓身旁泥地翻湧，不引發地震、不改變湖岸地形；戰鬥呈現為土屬性物理咬擊與範圍震地，資源耗盡後回到普通攻擊。不具神性、守護使命或精靈關聯。連結沉鐘鎮湖畔漁人的下網習慣。",
        "（作者私有：尚未證實的猜想）沉鐘鎮的老漁人說湖丘巨龜背上的蘆葦開花的那年，湖裡的魚會特別多，這種說法尚未證實。",
        "wide_mound_elder",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "wide_mound_elder",
        "lake_mound_turtle",
        "丘背型",
        "普通版本，背甲泥層積了多年、長滿蘆葦的成年個體。",
        "high",
        True,
        MonsterCombatProfile(
            hp=500, mp=48, sp=30, atk_phys=32, agility=16, defense=30, magic_power=0
        ),
        "B",
        True,
        active_skill_keys=("lake_mound_bite", "lake_mound_quake",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "lake_mound_bite",
        "碎顎咬合",
        "以土屬性力量讓四足陷進泥地撐住身軀，探出粗大的頭部以厚鈍如石的巨顎咬住單一敵方目標，造成土屬性物理傷害。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 12, "sp": 6},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="earth",
        effects=["damage:earth:physical"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="earth",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("lake_mound_turtle",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=1.2, audience=EffectAudience.ENEMIES),
        ),
    ),
```

```python
    _skill(
        "lake_mound_quake",
        "背甲震地",
        "撐起身軀把背甲猛力砸向地面，以土屬性力量讓泥地翻湧，對周圍每個敵方目標造成土屬性物理傷害。",
        SkillKind.ACTIVE,
        TargetSpec.AREA,
        cost={"mp": 16, "sp": 8},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="earth",
        effects=["damage:earth:physical"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="earth",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("lake_mound_turtle",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=0.8, audience=EffectAudience.ENEMIES),
        ),
    ),
```

Also append one sentence to that module's docstring describing this kit's composition, in the style of the existing sentences.

### D4. Rulebook and narration

- No timed effect, modifier or status row: the kit's riders are a damage occurrence and, where present, a gauge transfer or a second damage occurrence.
- `world/skills/narration/data_earth.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "lake_mound_bite",
        action=(
            "{actor} 從泥水裡探出巨頭，一口咬向對手。",
            "{actor} 粗大的頸子一伸，厚鈍的巨顎猛然合上。",
        ),
    ),
```

- `world/skills/narration/data_earth.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "lake_mound_quake",
        action=(
            "{actor} 撐起背甲猛力砸下，四周泥地一陣翻湧。",
            "{actor} 整座背甲壓向地面，湧起的泥浪撞向身旁眾人。",
        ),
    ),
```

### D5. AI binding and activation evidence

No `world/rules/rulebook/monster_behaviour.yaml` edit. This link adds no timed effect or modifier, so the tuning fingerprint is expected to stay unchanged. Each variant binds the shipped archetype named in D2, and the legacy body selects the damage-bearing kit. Run `ActivationRecordTests`, `ActivationBindingTests` and `RollbackTests`. If they pass, the fingerprint did not move and the evidence stays untouched. If a fingerprint comparison fails, re-fingerprint following the `mudfilm-slime-species` precedent (archived change design D5, steps 1–4), without touching `activated` or `activation_bindings`:

1. Run `uv run --locked python tools/monster_ai_manual_reports.py selector` and copy `.var/monster-ai-manual-reports/selector-check.json` and `.md` over `docs/development/monster-ai-manual-evidence/`.
2. Read the new `configuration_fingerprint` from the regenerated `selector-check.json`. Read the rollback fingerprint from the `RollbackTests` failure message.
3. In `activation.json`, update `configuration_fingerprint`, `legacy_rollback.configuration_fingerprint` and the `selector-check.json` evidence entry's fingerprint.
4. Update the fingerprint lines in `docs/development/monster-ai-activation-evidence/README.md` and the selector paragraph of `docs/development/monster-ai-manual-evidence/README.md`.

### D6. Bestiary and ledger

- Overview row, inserted in the `## 收錄總覽` table after the last `| 高階 |` row:

  `| 高階 | 湖丘巨龜 | 東部大平原東北的湖沼深處 | 以土屬性力量讓背甲上的湖泥結得緊實 | 丘背型 |`

- New section at the end of `## 高階魔物`, immediately before `<!-- bestiary-current-end -->` (after every high section an earlier programme change added), transcribed exactly:

````markdown
### 湖丘巨龜

```bestiary
species: lake_mound_turtle
parent-species: lake_mound_turtle
default-variant: wide_mound_elder
variants:
  - key: wide_mound_elder
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

**原型與棲地。**湖丘巨龜是背甲寬過一座小屋的巨大龜類魔獸，獨自棲息於東部大平原東北的湖沼深處。

**外觀。**背甲上糊著一層厚實的湖泥，長滿蘆葦與水草，露出水面時看起來是一座小土丘。頭部粗大，鉤狀上顎的邊緣厚鈍如石，四肢粗短，覆著灰黑色的硬鱗。

**生態與在地關係。**牠一年裡大半時間靜臥在湖底，以路過的大魚與水鳥為食；背甲上的泥層一年比一年厚，上頭的蘆葦也越長越高。沉鐘鎮與周邊湖畔的漁人熟悉湖上每一座蘆葦小丘，下網時會避開會移動的那一座。首隻指定個體的背甲上長著一叢秋天開白花的蘆葦，被稱為「白蘆」。

**戰鬥中的表現。**牠能以土屬性力量讓背甲上的湖泥結得緊實。咬合集中於單一對手；震地則讓身旁泥地翻湧，撞向每個敵對身影，撞擊分別落在每個身影身上。兩者都耗費牠自身的魔力與體力，耗盡時牠以巨顎與背甲衝撞應戰。

| 變體 | 核准方向 |
| --- | --- |
| 丘背型 | 普通版本，背甲泥層積了多年、長滿蘆葦的成年個體 |

**委託背景示例。**沉鐘鎮北邊的湖灣裡，一座長著白花蘆葦的小丘連續三晚移到漁船的下網處，掀翻了兩條小船。鎮上的漁會判定這頭巨龜需要熟練隊伍處理，向公會正式張貼討伐委託。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `lake_mound_turtle` | <implementation date> | read against the registry's published ecology field; the trouble is one turtle on the lake bay where the fishers net, local and avoidable, the earth power acts on the mud of its own shell and the ground it slams, and the local name 「白蘆」 is an observation rather than a new naming tradition | checked against the declared kit: the bite is a single-target earth-element physical strike and the shell slam reaches every eligible enemy with its own hit and defense outcome, both spend the turtle's own magic and stamina once per cast, and the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D7. Tests

- No test file changes. Narration coverage, the kit contract and the composition-group derivation already include the new rows.

### D8. Developer review section

Append `## 湖丘巨龜` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Armoured lake boss: defense near the high band's ceiling, agility at the band's floor, hit points between the boar's and the 蓄潮型's.
* MP holds one bite plus two slams (12 + 16 + 16 = 44 ≤ 48); SP holds three of the larger casts.
* Costs and coefficients repeat the boar's, the stag's and the griffin's shipped single-plus-area shape; the element is earth, as for the stag.
* Grade B: a dangerous site boss, below the A-grade 蓄潮型.
- `### Reuse of the two-strike (single + area damage) representative`: the signature, the unchanged representative `warm_den_boar`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later key sorts before a representative] → every Wave 1, Wave 2 and Wave 3 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_ember_bristle_boar_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change lake-mound-turtle-species` and `openspec validate lake-mound-turtle-species --strict`.
