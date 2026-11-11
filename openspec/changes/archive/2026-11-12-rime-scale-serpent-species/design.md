# Design

## Context

See proposal.md (Why). Facts at `d1ac4b84` plus the planned Wave 1 species rows (`openspec/changes/*-species/`), which land first:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS` and `_VARIANT_DECLARATIONS` at import. Bands come from `MONSTER_TIER_REGISTRY`: low HP 25–70, attack 3–12, agility 3–12, defense 2–8, grades F–E; mid HP 110–230, attack 18–28, agility 10–24, defense 10–16, grades D–C; high HP 300–750, attack 26–40, agility 16–30, defense 18–32, grades B–A. `magic_power` must be 0 and MP/SP have no band. Display names are limited to 5 code points (`MONSTER_NAME_MAX_CODE_POINTS`).
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」 and `author_conjecture_zh` to contain 「尚未證實」, and it forbids registry strings that name a skill, behaviour or trait key.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by `(slot, effect family, audience, requires_hit_from)` and requires one committed representative per group, the group's sorted-minimum key. This kit's signature is `(("active", "damage", "enemies", None), ("active", "damage", "enemies", None))`, the shipped two-strike (single + area damage) group, whose representative `warm_den_boar` is declared in `world.rules.tests.test_ember_bristle_boar_resource_skill`. Every new variant key sorts after `warm_den_boar` (and every Wave 1 key does too), so the representative does not move and no smoke module, shard entry or seed entry is added. `"warm_den_boar" < "white_rime_coil"`, so the boar stays the representative and no smoke module is added.
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests` requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, a magic tier for elemental MP skills (MP 10–16 single, 14–20 area) and `None` otherwise. `validate_catalog` requires one narration row per active skill, and `world/rules/status_display.py` fails closed for a buff or modifier without a display row.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, modifier rule, intelligence and mode entry, plus the referenced bindings. `world/rules/tests/test_monster_ai_activation.py` compares that fingerprint with `docs/development/monster-ai-activation-evidence/activation.json`.
- Every kit here carries a damage occurrence, so the legacy decision body proposes it and no utility binding or intelligence value is needed (`owned-kit-decision-coverage` applies only to support-only kits).

## Candidate review (`docs/lore/monster-creation-guidelines.md`)

| Question | Answer |
| --- | --- |
| Familiar archetype | A giant constricting serpent (a python). |
| Special way of life | Ice power frosts its own scales so it lies coiled in the mist like a frosted rock ridge; one large meal lets it rest in its ravine for a month. |
| World relation | Prospecting parties from 銀嶺鎮 search ravine walls for silver veins (central mountains terrain flavour: mist around the slopes, places people have never reached). |
| Ability limits | The frost acts only on its own scales. It freezes no one, changes no weather, carries no divinity or guardian mission and is not the source of the singing in the wind; when its magic and stamina are spent it falls back to plain strikes (ice element used only as damage element). |
| Local conflict | It coils in a ravine where prospectors found a new silver outcrop and turns them back, so a branch guild posts a commission for a skilled party. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar), the Wave 1 species (spore-cap mushroom, moss-quill porcupine, hollow-tree bat, hush-wing owl, vine-net spider, moss-crown stag) and the other nine Wave 2 species. It is an animal, clearly distinct from every beastfolk subspecies (wolf, cat, bear, rabbit, cattle, tiger, fox).

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `central-mountains-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "rime_scale_serpent",
        "霜鱗巨蟒",
        "霜鱗巨蟒是身長超過十人並列的巨大蟒類魔獸，獨自盤踞於中央山脈霧氣積聚的深谷。",
        "灰白鱗片邊緣結著一層細霜，在霧中幾乎與覆雪的岩石融為一體。"
        "頭部寬如門板，琥珀色豎瞳，腹側鱗片隨呼吸起伏時會抖落細碎冰屑。",
        "牠以野山羊、碎骨鷲與誤入深谷的大型動物為食，一次飽食後能在谷底盤臥一整個月。"
        "牠能以冰屬性力量讓自己的鱗片結霜，盤在霧中時看起來像一段覆著霜雪的岩脊；"
        "結霜作用在牠自己的鱗片上。"
        "牠盤踞的深谷四周少有人跡，只有銀嶺鎮的探礦隊偶爾沿谷壁尋找銀脈。"
        "牠以結霜的獠牙噬咬單一對手，也會甩動長尾橫掃身旁的對手；"
        "噬咬與橫掃都耗費牠自身的魔力與體力。"
        "首隻指定個體因盤成一圈時像谷底的一道白霜環，被稱為「霜環」。",
        ("central_mountains",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；鱗片結霜的成因不在設定中交代。",
        "（作者私有：作者解釋）高階獨居巨蟒：冰屬性只讓自身鱗片結霜，不凍結他人、不改變天氣，也不具神性或守護山脈的使命，與寒風中的歌聲無關；戰鬥呈現為冰屬性物理噬咬與橫掃，資源耗盡後回到普通攻擊。",
        "（作者私有：尚未證實的猜想）銀嶺鎮的老礦工說霜鱗巨蟒盤踞的深谷必定藏著銀脈，這種說法尚未證實。",
        "white_rime_coil",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "white_rime_coil",
        "rime_scale_serpent",
        "霜谷型",
        "普通版本，盤踞同一座霧谷多年的成年個體。",
        "high",
        True,
        MonsterCombatProfile(
            hp=500, mp=48, sp=30, atk_phys=31, agility=20, defense=24, magic_power=0
        ),
        "B",
        True,
        active_skill_keys=("rime_fang_strike", "rime_tail_lash",),
        passive_skill_keys=(),
        behaviour_profile_key="pack_hunter",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "rime_fang_strike",
        "霜牙噬擊",
        "以冰屬性力量讓獠牙結霜，噬咬單一敵方目標，造成冰屬性物理傷害。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 12, "sp": 6},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="ice",
        effects=["damage:ice:physical"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="ice",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("rime_scale_serpent",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=1.2, audience=EffectAudience.ENEMIES),
        ),
    ),
```

```python
    _skill(
        "rime_tail_lash",
        "霜尾橫掃",
        "甩動結霜的長尾橫掃周圍所有敵方目標，對每個目標造成冰屬性物理傷害。",
        SkillKind.ACTIVE,
        TargetSpec.AREA,
        cost={"mp": 16, "sp": 8},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="ice",
        effects=["damage:ice:physical"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="ice",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("rime_scale_serpent",),
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
- `world/skills/narration/data_ice.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "rime_fang_strike",
        action=(
            "{actor} 從霧裡昂起寬大的頭，結霜的獠牙猛然咬下。",
            "{actor} 盤身一縮，帶著冰屑的巨口噬向對手。",
        ),
    ),
```

- `world/skills/narration/data_ice.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "rime_tail_lash",
        action=(
            "{actor} 甩動長尾，結霜的鱗片掃過四周。",
            "{actor} 擰身一甩，冰屑隨著長尾掃向身旁眾人。",
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

  `| 高階 | 霜鱗巨蟒 | 中央山脈霧氣積聚的深谷 | 以冰屬性力量讓自身鱗片結霜 | 霜谷型 |`

- New section at the end of `## 高階魔物`, immediately before `<!-- bestiary-current-end -->` (after every high section an earlier programme change added), transcribed exactly:

````markdown
### 霜鱗巨蟒

```bestiary
species: rime_scale_serpent
parent-species: rime_scale_serpent
default-variant: white_rime_coil
variants:
  - key: white_rime_coil
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

**原型與棲地。**霜鱗巨蟒是身長超過十人並列的巨大蟒類魔獸，獨自盤踞於中央山脈霧氣積聚的深谷。

**外觀。**灰白鱗片邊緣結著一層細霜，在霧中幾乎與覆雪的岩石融為一體。頭部寬如門板，琥珀色豎瞳，腹側鱗片隨呼吸起伏時會抖落細碎冰屑。

**生態與在地關係。**牠以野山羊、碎骨鷲與誤入深谷的大型動物為食，一次飽食後能在谷底盤臥一整個月。牠盤踞的深谷四周少有人跡，只有銀嶺鎮的探礦隊偶爾沿谷壁尋找銀脈；探礦隊入谷前會先找那段覆霜的岩脊，確認牠盤在哪裡。首隻指定個體因盤成一圈時像谷底的一道白霜環，被稱為「霜環」。

**戰鬥中的表現。**牠以冰屬性力量讓自己的鱗片結霜，盤在霧中時看起來像一段覆著霜雪的岩脊。噬咬集中於單一對手；橫掃則掃過身旁每個敵對身影，撞擊分別落在每個身影身上。兩者都耗費牠自身的魔力與體力，耗盡時牠以身軀撞擊與普通噬咬應戰。

| 變體 | 核准方向 |
| --- | --- |
| 霜谷型 | 普通版本，盤踞同一座霧谷多年的成年個體 |

**委託背景示例。**銀嶺鎮的探礦隊在山裡一座深谷找到新的銀脈露頭，谷底卻盤著一條結霜的巨蟒，兩支隊伍都在谷口被逼退。銀嶺鎮分會判定這條巨蟒需要熟練隊伍處理，正式張貼討伐委託。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `rime_scale_serpent` | <implementation date> | read against the registry's published ecology field; the trouble is a remote mist ravine on a prospecting route, local and avoidable, the frost acts on the serpent's own scales, and the local name 「霜環」 is an observation rather than a new naming tradition | checked against the declared kit: the fang strike is a single-target ice-element physical strike and the tail lash reaches every eligible enemy with its own hit and defense outcome, both spend the serpent's own magic and stamina once per cast, and the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D7. Tests

- No test file changes. Narration coverage, the kit contract and the composition-group derivation already include the new rows.

### D8. Developer review section

Append `## 霜鱗巨蟒` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Long-bodied ambusher: hit points above the stag's, defense below it and in the high band's middle, agility a little above the band's floor.
* MP holds one fang strike plus two lashes (12 + 16 + 16 = 44 ≤ 48); SP holds three of the larger casts.
* Costs and coefficients repeat the boar's and the stag's shipped single-plus-area shape; only the element differs (ice).
* Grade B: a dangerous solitary site boss, below the A-grade 蓄潮型.
- `### Reuse of the two-strike (single + area damage) representative`: the signature, the unchanged representative `warm_den_boar`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later key sorts before a representative] → every Wave 1 and Wave 2 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_ember_bristle_boar_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change rime-scale-serpent-species` and `openspec validate rime-scale-serpent-species --strict`.
