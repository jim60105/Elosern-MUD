# Design

## Context

See proposal.md (Why). Facts at `d1ac4b84` plus the planned Wave 1 species rows (`openspec/changes/*-species/`), which land first:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS` and `_VARIANT_DECLARATIONS` at import. Bands come from `MONSTER_TIER_REGISTRY`: low HP 25–70, attack 3–12, agility 3–12, defense 2–8, grades F–E; mid HP 110–230, attack 18–28, agility 10–24, defense 10–16, grades D–C; high HP 300–750, attack 26–40, agility 16–30, defense 18–32, grades B–A. `magic_power` must be 0 and MP/SP have no band. Display names are limited to 5 code points (`MONSTER_NAME_MAX_CODE_POINTS`).
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」 and `author_conjecture_zh` to contain 「尚未證實」, and it forbids registry strings that name a skill, behaviour or trait key.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by `(slot, effect family, audience, requires_hit_from)` and requires one committed representative per group, the group's sorted-minimum key. This kit's signature is `(("active", "damage", "enemies", None), ("active", "damage", "enemies", None))`, the shipped two-strike (single + area damage) group, whose representative `warm_den_boar` is declared in `world.rules.tests.test_ember_bristle_boar_resource_skill`. Every new variant key sorts after `warm_den_boar` (and every Wave 1 key does too), so the representative does not move and no smoke module, shard entry or seed entry is added. `"warm_den_boar" < "windcrest_elder"`, so the boar stays the representative and no smoke module is added.
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests` requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, a magic tier for elemental MP skills (MP 10–16 single, 14–20 area) and `None` otherwise. `validate_catalog` requires one narration row per active skill, and `world/rules/status_display.py` fails closed for a buff or modifier without a display row.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, modifier rule, intelligence and mode entry, plus the referenced bindings. `world/rules/tests/test_monster_ai_activation.py` compares that fingerprint with `docs/development/monster-ai-activation-evidence/activation.json`.
- Every kit here carries a damage occurrence, so the legacy decision body proposes it and no utility binding or intelligence value is needed (`owned-kit-decision-coverage` applies only to support-only kits).

## Candidate review (`docs/lore/monster-creation-guidelines.md`)

| Question | Answer |
| --- | --- |
| Familiar archetype | A griffin, the folklore eagle-headed winged beast (described with a four-legged beast body, never as a cat or a person). |
| Special way of life | Wind power gathers air under its own wings so its heavy body can take off from cliff tops and turn sharply; it lines its nest with bright ore chips pecked from vein walls. |
| World relation | Beastfolk miners and old hunters work exposed ore veins and hunt the herds in clearings (northwest highland terrain flavour: exposed ore-vein walls, herds in clearings). |
| Ability limits | The wind acts only under its own wings. It controls no weather and has no treasure-guarding mission, divinity or elven tie; ore collecting is nesting behaviour, and when its magic and stamina are spent it falls back to plain claws and beak. |
| Local conflict | Its nest crowns the cliff above a newly found vein and it strikes miners down, so a branch guild posts a commission for a skilled party. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar), the Wave 1 species (spore-cap mushroom, moss-quill porcupine, hollow-tree bat, hush-wing owl, vine-net spider, moss-crown stag) and the other nine Wave 2 species. It is an animal, clearly distinct from every beastfolk subspecies (wolf, cat, bear, rabbit, cattle, tiger, fox).

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `northwest-highland-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "ore_nest_griffin",
        "礦巢獅鷲",
        "礦巢獅鷲是雙翼展開超過四人寬的巨大有翼魔獸，生著鷹首與四足獸身，成對棲息於西北高地礦脈裸露的高崖。",
        "金褐色的鷹首帶著彎鉤巨喙，頸羽向下逐漸轉為覆蓋獸身的黃褐短毛。"
        "前足是鷹爪，後足是帶著肉墊的獸足，長尾末端垂著一簇深色毛。",
        "牠在高崖上以枯枝築成寬大的巢，巢裡鋪滿從礦脈岩壁上啄下的閃亮礦石碎片。"
        "牠以林間空地上的大型獸群為獵物，從高空盤旋鎖定落單的個體後俯衝而下。"
        "牠能以風屬性力量把氣流聚到翼下，讓沉重的身軀從崖頂起飛、在空中驟然轉向；"
        "這股風力作用在牠自己的雙翼周圍。"
        "獸人部族的老獵人與礦工都認得那些崖頂閃著礦光的巢，開採礦脈時會避開巢崖下方。"
        "牠以鷹爪俯衝擊打單一對手，也會在低空猛振雙翼，以翼下風壓撞向身旁所有對手；"
        "兩者都耗費牠自身的魔力與體力。"
        "首隻指定個體因頸羽在陽光下閃著金光，被稱為「金翎」。",
        ("northwest_highland_forest",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；翼下風力的成因不在設定中交代。",
        "（作者私有：作者解釋）高階成對棲息的有翼魔獸：風屬性只把氣流聚到自身翼下以起飛與轉向，不操控天氣、不造成擊退或持續傷害，也不具神性、守護寶物的使命或精靈關聯；收集礦石碎片是築巢習性。外觀以鷹首與四足獸身描寫，不寫成貓科或獸人。戰鬥呈現為風屬性物理俯衝與範圍翼壓，資源耗盡後回到普通攻擊。",
        "（作者私有：尚未證實的猜想）鐵爪城的礦工相信礦巢獅鷲叼回巢裡的礦石碎片都來自最純的礦脈，這種說法尚未證實。",
        "windcrest_elder",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "windcrest_elder",
        "ore_nest_griffin",
        "巔巢型",
        "普通版本，占據同一座礦脈高崖多年的成年個體。",
        "high",
        True,
        MonsterCombatProfile(
            hp=430, mp=48, sp=30, atk_phys=33, agility=26, defense=21, magic_power=0
        ),
        "B",
        True,
        active_skill_keys=("ore_crest_dive", "ore_crest_gale",),
        passive_skill_keys=(),
        behaviour_profile_key="pack_hunter",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "ore_crest_dive",
        "俯衝裂爪",
        "以風屬性力量把氣流聚到翼下，俯衝以鷹爪擊打單一敵方目標，造成風屬性物理傷害。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 12, "sp": 6},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="wind",
        effects=["damage:wind:physical"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="wind",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("ore_nest_griffin",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=1.2, audience=EffectAudience.ENEMIES),
        ),
    ),
```

```python
    _skill(
        "ore_crest_gale",
        "振翼風壓",
        "在低空猛振雙翼，以翼下風壓撞擊周圍所有敵方目標，對每個目標造成風屬性物理傷害。",
        SkillKind.ACTIVE,
        TargetSpec.AREA,
        cost={"mp": 16, "sp": 8},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="wind",
        effects=["damage:wind:physical"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="wind",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("ore_nest_griffin",),
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
- `world/skills/narration/data_wind.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "ore_crest_dive",
        action=(
            "{actor} 從高空收翼俯衝，鷹爪直取對手。",
            "{actor} 翼下氣流一聚，巨大的身影驟然撲落。",
        ),
    ),
```

- `world/skills/narration/data_wind.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "ore_crest_gale",
        action=(
            "{actor} 壓低身軀猛振雙翼，狂風撞向四周。",
            "{actor} 張開巨翼一搧，翼下風壓掃過身旁眾人。",
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

  `| 高階 | 礦巢獅鷲 | 西北高地礦脈裸露的高崖 | 以風屬性力量把氣流聚到翼下，讓沉重身軀起飛轉向 | 巔巢型 |`

- New section at the end of `## 高階魔物`, immediately before `<!-- bestiary-current-end -->` (after every high section an earlier programme change added), transcribed exactly:

````markdown
### 礦巢獅鷲

```bestiary
species: ore_nest_griffin
parent-species: ore_nest_griffin
default-variant: windcrest_elder
variants:
  - key: windcrest_elder
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

**原型與棲地。**礦巢獅鷲是雙翼展開超過四人寬的巨大有翼魔獸，生著鷹首與四足獸身，成對棲息於西北高地礦脈裸露的高崖。

**外觀。**金褐色的鷹首帶著彎鉤巨喙，頸羽向下逐漸轉為覆蓋獸身的黃褐短毛。前足是鷹爪，後足是帶著肉墊的獸足，長尾末端垂著一簇深色毛。

**生態與在地關係。**牠在高崖上以枯枝築成寬大的巢，巢裡鋪滿從礦脈岩壁上啄下的閃亮礦石碎片，並以林間空地上的大型獸群為獵物。獸人部族的老獵人與礦工都認得那些崖頂閃著礦光的巢，開採礦脈時會避開巢崖下方。首隻指定個體因頸羽在陽光下閃著金光，被稱為「金翎」。

**戰鬥中的表現。**牠能以風屬性力量把氣流聚到翼下，讓沉重的身軀從崖頂起飛、在空中驟然轉向。俯衝集中於單一對手；翼壓則撞向身旁每個敵對身影，撞擊分別落在每個身影身上。兩者都耗費牠自身的魔力與體力，耗盡時牠以爪擊與巨喙啄咬應戰。

| 變體 | 核准方向 |
| --- | --- |
| 巔巢型 | 普通版本，占據同一座礦脈高崖多年的成年個體 |

**委託背景示例。**鐵爪城礦工在北邊高崖下找到一段新礦脈，崖頂卻是一座閃著礦光的獅鷲巢，兩名礦工被俯衝的巨影撲倒。鐵爪城分會判定這頭獅鷲需要熟練隊伍處理，正式張貼討伐委託。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `ore_nest_griffin` | <implementation date> | read against the registry's published ecology field; the trouble is one nest cliff above a new ore vein, local and avoidable, the wind acts under the griffin's own wings, ore collecting is nesting behaviour, and the local name 「金翎」 is an observation rather than a new naming tradition | checked against the declared kit: the dive is a single-target wind-element physical strike and the wing gale reaches every eligible enemy with its own hit and defense outcome, both spend the griffin's own magic and stamina once per cast, and the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D7. Tests

- No test file changes. Narration coverage, the kit contract and the composition-group derivation already include the new rows.

### D8. Developer review section

Append `## 礦巢獅鷲` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Aerial striker: agility near the high band's upper end, hit points between the boar's and the stag's, defense in the band's lower half.
* MP holds one dive plus two gales (12 + 16 + 16 = 44 ≤ 48); SP holds three of the larger casts.
* Costs and coefficients repeat the boar's and the stag's shipped single-plus-area shape; only the element differs (wind).
* Grade B: a dangerous site boss, below the A-grade 蓄潮型.
- `### Reuse of the two-strike (single + area damage) representative`: the signature, the unchanged representative `warm_den_boar`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later key sorts before a representative] → every Wave 1 and Wave 2 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_ember_bristle_boar_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change ore-nest-griffin-species` and `openspec validate ore-nest-griffin-species --strict`.
