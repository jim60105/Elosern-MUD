# Design

## Context

See proposal.md (Why). Facts at `3756992d`:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS` and `_VARIANT_DECLARATIONS` at import. Bands come from `MONSTER_TIER_REGISTRY`: low HP 25–70, attack 3–12, agility 3–12, defense 2–8, grades F–E; mid HP 110–230, attack 18–28, agility 10–24, defense 10–16, grades D–C; high HP 300–750, attack 26–40, agility 16–30, defense 18–32, grades B–A. `magic_power` must be 0 and MP/SP have no band. Display names are limited to 5 code points (`MONSTER_NAME_MAX_CODE_POINTS`).
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」 and `author_conjecture_zh` to contain 「尚未證實」, and it forbids registry strings that name a skill, behaviour or trait key.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by `(slot, effect family, audience, requires_hit_from)` and requires one committed representative per group, the group's sorted-minimum key. This kit's signature is `(("active", "damage", "enemies", None), ("active", "damage", "enemies", None))`, the shipped two-strike (single + area damage) group, whose representative `warm_den_boar` is declared in `world.rules.tests.test_ember_bristle_boar_resource_skill`. Every new variant key sorts after `warm_den_boar`, so the representative does not move and no smoke module, shard entry or seed entry is added. `"warm_den_boar" < "wood_crown_elder"`, so the boar stays the representative and no smoke module is added.
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests` requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, a magic tier for elemental MP skills (MP 10–16 single, 14–20 area) and `None` otherwise. `validate_catalog` requires one narration row per active skill, and `world/rules/status_display.py` fails closed for a buff or modifier without a display row.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, modifier rule, intelligence and mode entry, plus the referenced bindings. `world/rules/tests/test_monster_ai_activation.py` compares that fingerprint with `docs/development/monster-ai-activation-evidence/activation.json`.
- Every kit here carries a damage occurrence, so the legacy decision body proposes it and no utility binding or intelligence value is needed (`owned-kit-decision-coverage` applies only to support-only kits).

## Candidate review (`docs/lore/monster-creation-guidelines.md`)

| Question | Answer |
| --- | --- |
| Familiar archetype | A giant elk or great stag. |
| Special way of life | Earth power firms the moss and vine roots on its antlers into a heavy crown, which it uses to drive large animals out of its rutting clearing. |
| World relation | Expeditions to the deep-forest dungeons travel routes through its clearings ("far away something huge seems to move", the region's terrain flavour). |
| Ability limits | The hardening acts only on its own antler moss. It controls no plants, changes no terrain and carries no divinity or guardian mission, and when its magic and stamina are spent it falls back to plain hoof and head attacks. |
| Local conflict | In rut it holds a clearing on an expedition route and turns parties back, so a branch guild posts a commission for a skilled party. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar) and from the other five Wave 1 species.

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `north-deep-forest-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "moss_crown_stag",
        "苔冠巨鹿",
        "苔冠巨鹿是肩高約兩人的巨大鹿類魔獸，獨自漫遊於北部深林巨木之間的林間空地。",
        "寬闊的鹿角如枯枝般分岔，角上長滿苔蘚、蕨葉與垂落的細藤，遠看如同林間移動的一叢樹冠。"
        "灰褐色長毛垂到膝下，蹄子寬大，每一步都在腐葉上壓出深坑。",
        "牠以嫩枝、苔蘚與林間空地的草本植物為食，會把鹿角抵在巨木樹幹上磨擦，替角上的苔層換上新的藤葉。"
        "牠能以土屬性力量讓角上的苔層與藤根緊實硬化，使整副鹿角沉重如盤根。"
        "發情期間，牠會占據一片林間空地，把闖入的大型動物撞出空地。"
        "往返深林的探險隊會在遠處認出那叢移動的樹冠，提早改走另一條路；"
        "牠把空地選在探險隊的必經之處時，公會便會張貼討伐委託。"
        "牠以硬化的苔冠衝撞單一對手，也會甩動鹿角橫掃身旁的對手；"
        "衝撞與橫掃都耗費牠自身的魔力與體力。"
        "首隻指定個體因角上蒼綠的苔冠被稱為「蒼冠」。",
        ("north_deep_forest",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；鹿角苔層硬化的成因不在設定中交代。",
        "（作者私有：作者解釋）高階獨居巨鹿：土屬性力量只硬化自身鹿角上的苔層與藤根，不操縱植物、不改變地形，也不具神性或守護森林的使命；戰鬥呈現為土屬性物理衝撞與橫掃，資源耗盡後回到普通攻擊。",
        "（作者私有：尚未證實的猜想）虎嘯城的長老說苔冠巨鹿是深林最古老的居民，這種說法尚未證實。",
        "wood_crown_elder",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "wood_crown_elder",
        "moss_crown_stag",
        "老冠型",
        "普通版本，每年在同一片林間空地度過發情期的老雄鹿。",
        "high",
        True,
        MonsterCombatProfile(
            hp=460, mp=48, sp=30, atk_phys=32, agility=18, defense=26, magic_power=0
        ),
        "B",
        True,
        active_skill_keys=("moss_crown_charge", "moss_crown_sweep",),
        passive_skill_keys=(),
        behaviour_profile_key="pack_hunter",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "moss_crown_charge",
        "苔冠衝撞",
        "以土屬性力量硬化鹿角上的苔冠，衝撞單一敵方目標，造成土屬性物理傷害。",
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
            allowed_species=("moss_crown_stag",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=1.2, audience=EffectAudience.ENEMIES),
        ),
    ),
```

```python
    _skill(
        "moss_crown_sweep",
        "苔冠橫掃",
        "甩動硬化的苔冠橫掃周圍所有敵方目標，對每個目標造成土屬性物理傷害。",
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
            allowed_species=("moss_crown_stag",),
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
        "moss_crown_charge",
        action=(
            "{actor} 壓低苔冠，踏著深坑直衝而來。",
            "{actor} 鹿角上的藤根一緊，整副苔冠撞向對手。",
        ),
    ),
```

- `world/skills/narration/data_earth.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "moss_crown_sweep",
        action=(
            "{actor} 甩動沉重的苔冠，朝四周橫掃。",
            "{actor} 昂首一甩，垂藤與硬角掃過身旁眾人。",
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

  `| 高階 | 苔冠巨鹿 | 北部深林巨木間的林間空地 | 以土屬性力量硬化角上苔層，使鹿角沉重如盤根 | 老冠型 |`

- New section at the end of `## 高階魔物`, immediately before `<!-- bestiary-current-end -->`, transcribed exactly:

````markdown
### 苔冠巨鹿

```bestiary
species: moss_crown_stag
parent-species: moss_crown_stag
default-variant: wood_crown_elder
variants:
  - key: wood_crown_elder
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

**原型與棲地。**苔冠巨鹿是肩高約兩人的巨大鹿類魔獸，獨自漫遊於北部深林巨木之間的林間空地。

**外觀。**寬闊的鹿角如枯枝般分岔，角上長滿苔蘚、蕨葉與垂落的細藤，遠看如同林間移動的一叢樹冠。灰褐色長毛垂到膝下，蹄子寬大，每一步都在腐葉上壓出深坑。

**生態與在地關係。**牠以嫩枝、苔蘚與林間空地的草本植物為食，會把鹿角抵在巨木樹幹上磨擦，替角上的苔層換上新的藤葉。發情期間，牠會占據一片林間空地，把闖入的大型動物撞出空地。往返深林的探險隊會在遠處認出那叢移動的樹冠，提早改走另一條路；牠把空地選在探險隊的必經之處時，公會便會張貼討伐委託。首隻指定個體因角上蒼綠的苔冠被稱為「蒼冠」。

**戰鬥中的表現。**牠以土屬性力量讓角上的苔層與藤根緊實硬化，使整副鹿角沉重如盤根。衝撞集中於單一對手；橫掃則掃過身旁每個敵對身影，撞擊分別落在每個身影身上。兩者都耗費牠自身的魔力與體力，耗盡時牠以蹄踏與頂撞應戰。

| 變體 | 核准方向 |
| --- | --- |
| 老冠型 | 普通版本，每年在同一片林間空地度過發情期的老雄鹿 |

**委託背景示例。**往永夜迷宮的探險隊回報，林道中段的空地被一頭角上長滿蒼綠苔冠的巨鹿占據，三支隊伍都被撞回原路。虎嘯城分會判定這頭老雄鹿需要熟練隊伍處理，正式張貼討伐委託。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `moss_crown_stag` | <implementation date> | read against the registry's published ecology field; the trouble is a rutting clearing on an expedition route, local and avoidable, the hardening acts on the stag's own antler moss, and the local name 「蒼冠」 is an observation rather than a new naming tradition | checked against the declared kit: the charge is a single-target earth-element physical strike and the sweep reaches every eligible enemy with its own hit and defense outcome, both spend the stag's own magic and stamina once per cast, and the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D7. Tests

- No test file changes. Narration coverage, the kit contract and the composition-group derivation already include the new rows.

### D8. Developer review section

Append `## 苔冠巨鹿` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Heavy bruiser: hit points above the boar's, defense in the upper half of the high band, agility near its floor.
* MP holds one charge plus two sweeps (12 + 16 + 16 = 44 ≤ 48); SP holds three of the larger casts.
* Costs and coefficients repeat the boar's shipped charge and sweep shape; only the element differs (earth instead of fire).
* Grade B: a dangerous solitary site boss, below the A-grade 蓄潮型.
- `### Reuse of the two-strike (single + area damage) representative`: the signature, the unchanged representative `warm_den_boar`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later Wave 1 key sorts before a representative] → every Wave 1 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_ember_bristle_boar_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change moss-crown-stag-species` and `openspec validate moss-crown-stag-species --strict`.
