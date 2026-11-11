# Design

## Context

See proposal.md (Why). Facts at `d1ac4b84` plus the planned Wave 1 species rows (`openspec/changes/*-species/`), which land first:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS` and `_VARIANT_DECLARATIONS` at import. Bands come from `MONSTER_TIER_REGISTRY`: low HP 25–70, attack 3–12, agility 3–12, defense 2–8, grades F–E; mid HP 110–230, attack 18–28, agility 10–24, defense 10–16, grades D–C; high HP 300–750, attack 26–40, agility 16–30, defense 18–32, grades B–A. `magic_power` must be 0 and MP/SP have no band. Display names are limited to 5 code points (`MONSTER_NAME_MAX_CODE_POINTS`).
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」 and `author_conjecture_zh` to contain 「尚未證實」, and it forbids registry strings that name a skill, behaviour or trait key.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by `(slot, effect family, audience, requires_hit_from)` and requires one committed representative per group, the group's sorted-minimum key. This kit's signature is `(("active", "damage", "enemies", None), ("active", "gauge_transfer", "enemies", 0))`, the shipped contact drain group, whose representative `bank_lurker` is declared in `world.rules.tests.test_crocodile_resource_skill`. Every new variant key sorts after `bank_lurker` (and every Wave 1 key does too), so the representative does not move and no smoke module, shard entry or seed entry is added. The drained gauge is MP, as for the crocodile, at a smaller fixed amount. The signature reads only the effect family, so the group and its representative stay unchanged. MP drain transfer and rollback are owned by the shared synthetic suites in `world/rules/tests/test_gauge_transfer/`.
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests` requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, a magic tier for elemental MP skills (MP 10–16 single, 14–20 area) and `None` otherwise. `validate_catalog` requires one narration row per active skill, and `world/rules/status_display.py` fails closed for a buff or modifier without a display row.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, modifier rule, intelligence and mode entry, plus the referenced bindings. `world/rules/tests/test_monster_ai_activation.py` compares that fingerprint with `docs/development/monster-ai-activation-evidence/activation.json`.
- Every kit here carries a damage occurrence, so the legacy decision body proposes it and no utility binding or intelligence value is needed (`owned-kit-decision-coverage` applies only to support-only kits).

## Candidate review (`docs/lore/monster-creation-guidelines.md`)

| Question | Answer |
| --- | --- |
| Familiar archetype | A small mountain frog (a torrent or tree frog). |
| Special way of life | It draws moisture from the mist through its skin, clings to wet seep walls by day and calls at dusk; its tongue carries faint water power. |
| World relation | Path-crossing travellers and herb gatherers from 斷崖鎮 refill at the same mid-slope springs (central mountains terrain flavour: mist around the slopes, sparse paths). |
| Ability limits | The draw happens only at a landed tongue strike, is a small fixed MP amount and recovers with rest. No poison, paralysis or lasting harm (water element: MP drain, `docs/lore/magic-system.md` §3). |
| Local conflict | A colony fills the spring a herb-gathering party camps at, so the commission is to drive the frogs from the pool, not to exterminate a threat. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar), the Wave 1 species (spore-cap mushroom, moss-quill porcupine, hollow-tree bat, hush-wing owl, vine-net spider, moss-crown stag) and the other nine Wave 2 species. It is an animal, clearly distinct from every beastfolk subspecies (wolf, cat, bear, rabbit, cattle, tiger, fox).

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `central-mountains-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "mist_spring_frog",
        "霧泉蛙",
        "霧泉蛙是約手掌大小的蛙類魔獸，成群棲息於中央山脈山腰的滲水岩壁與霧中泉眼。",
        "灰藍色皮膚帶著細小水珠般的疣點，在霧裡泛著微光。"
        "後腿修長，指端長著吸盤，能貼在濕滑的岩壁上；"
        "喉囊鼓起時呈半透明的淡青色。",
        "牠們白天貼在泉眼周圍的岩壁上，以皮膚吸取霧氣中的水分，傍晚才成群鳴叫、捕食飛蟲。"
        "牠的舌尖帶著微弱水屬性力量，黏中獵物或對手時，會從對方身上汲走少量魔力，轉為自身的魔力；"
        "每次汲取的分量有限，被汲走的魔力會隨休息逐步恢復。"
        "翻越山徑的旅人與上山採藥的人都在這些泉眼補水，泉邊一旦擠滿霧泉蛙，取水的人就得先把蛙群趕開。"
        "近身時，牠彈出長舌拍打對手，舌尖黏中時順勢汲取魔力。",
        ("central_mountains",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；舌尖水屬性力量的成因不在設定中交代。",
        "（作者私有：作者解釋）低階群居蛙類：水屬性舌尖只在命中時汲取少量魔力，不造成中毒、麻痺或持續傷害；戰鬥呈現為舌擊與命中後的固定魔力汲取。連結山徑泉眼的取水。",
        "（作者私有：尚未證實的猜想）斷崖鎮的採藥人說霧泉蛙鳴叫得越早，當晚的霧就越濃，這種說法尚未證實。",
        "seep_sipper",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "seep_sipper",
        "mist_spring_frog",
        "汲泉型",
        "普通版本，成群貼在泉眼周圍的岩壁上吸取霧氣。",
        "low",
        True,
        MonsterCombatProfile(
            hp=34, mp=20, sp=6, atk_phys=5, agility=8, defense=3, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("mist_tongue_sip",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

```python
    MonsterVariant(
        "spring_keeper",
        "mist_spring_frog",
        "泉主型",
        "占據一整處泉池的老個體，體型大上一倍，喉囊鳴聲能壓過整群同伴。",
        "low",
        False,
        MonsterCombatProfile(
            hp=58, mp=30, sp=10, atk_phys=9, agility=8, defense=5, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("mist_tongue_sip",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "mist_tongue_sip",
        "霧舌汲取",
        "以帶著水屬性力量的長舌拍擊單一敵方目標，造成物理傷害；命中時從對方身上汲走少量魔力，轉為自身的魔力。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 2},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="water",
        effects=["damage:water:physical", "gauge_transfer:mp:drain:fixed:4"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="water",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("mist_spring_frog",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=0.8, audience=EffectAudience.ENEMIES),
            EffectPolicy(audience=EffectAudience.ENEMIES, requires_hit_from=0, transfer=GaugeTransferPolicy(caster_recovery_share=1.0)),
        ),
    ),
```

Also append one sentence to that module's docstring describing this kit's composition, in the style of the existing sentences.

### D4. Rulebook and narration

- No timed effect, modifier or status row: the kit's riders are a damage occurrence and, where present, a gauge transfer or a second damage occurrence.
- `world/skills/narration/data_water.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "mist_tongue_sip",
        action=(
            "{actor} 鼓起淡青喉囊，長舌倏地彈向對手。",
            "{actor} 從濕岩上一躍，黏濕的舌尖拍上對方手臂。",
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

- Overview row, inserted in the `## 收錄總覽` table after the last `| 低階 |` row:

  `| 低階 | 霧泉蛙 | 中央山脈山腰的滲水岩壁與霧中泉眼 | 舌尖黏中時汲走少量魔力 | 汲泉型、泉主型 |`

- New section at the end of `## 低階魔物`, immediately before `## 中階魔物` (after every low section an earlier programme change added), transcribed exactly:

````markdown
### 霧泉蛙

```bestiary
species: mist_spring_frog
parent-species: mist_spring_frog
default-variant: seep_sipper
variants:
  - key: seep_sipper
    status: delivered
  - key: spring_keeper
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

**原型與棲地。**霧泉蛙是約手掌大小的蛙類魔獸，成群棲息於中央山脈山腰的滲水岩壁與霧中泉眼。

**外觀。**灰藍色皮膚帶著細小水珠般的疣點，在霧裡泛著微光。後腿修長，指端長著吸盤，能貼在濕滑的岩壁上；喉囊鼓起時呈半透明的淡青色。

**生態與在地關係。**牠們白天貼在泉眼周圍的岩壁上，以皮膚吸取霧氣中的水分，傍晚才成群鳴叫、捕食飛蟲。翻越山徑的旅人與上山採藥的人都在這些泉眼補水，泉邊一旦擠滿霧泉蛙，取水的人就得先把蛙群趕開。占據一整處泉池、體型大上一倍的老個體稱為泉主型。

**戰鬥中的表現。**牠的舌尖帶著微弱水屬性力量。近身時，牠彈出長舌拍打對手，舌尖黏中時從對方身上汲走少量魔力，轉為自身的魔力；汲取只發生在黏中的瞬間，每次的分量有限，被汲走的魔力會隨休息逐步恢復。

| 變體 | 核准方向 |
| --- | --- |
| 汲泉型 | 普通版本，成群貼在泉眼周圍的岩壁上吸取霧氣 |
| 泉主型 | 占據一整處泉池的老個體，體型大上一倍，喉囊鳴聲能壓過整群同伴 |

**委託背景示例。**斷崖鎮的採藥隊每年入秋都在半山腰的泉眼補水過夜，今年泉池被一隻泉主型帶著整群霧泉蛙占住，隊員的水袋裝不滿。採藥隊長委託公會趕開泉邊的蛙群，讓隊伍能按時上山。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `mist_spring_frog` | <implementation date> | read against the registry's published ecology field; the trouble stays local to mountain-path springs that travellers and gatherers refill at, and the drain comes from the frog's own tongue | checked against the declared kit: the tongue strike is a single-target water-element physical strike, and the section states that the small MP draw follows a landed strike and recovers with rest, matching the declared hit dependency; the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D6a. Fifth-batch approval notes (this change only)

- `docs/lore/monster-creation-guidelines.md`: directly after the paragraph that starts `**第四批核准（2026-11-11）：**` (added by `spore-cap-mushroom-species`), add a paragraph:

  `**第五批核准（2026-11-11）：**中央山脈另行核准五種物種：低階的霧泉蛙與暖岩蠑螈，中階的碎骨鷲與霧燈蛾，以及高階的霜鱗巨蟒。西北高地森林另行核准五種物種：低階的鼓翼松雞、泥壩河狸與礦脈鼴，中階的掠藏獾，以及高階的礦巢獅鷲。每個物種只出現在明確宣告的棲地、據點或遭遇中；災厄級物種與新的文明種族仍不在核准範圍內。`

- `docs/lore/bestiary.md`: directly after the paragraph that starts `**第四批核准：**`, add:

  `**第五批核准：**2026-11-11 起，中央山脈另行核准兩種低階、兩種中階與一種高階物種，西北高地森林另行核准三種低階、一種中階與一種高階物種；各物種逐一收錄於下方現行小節。`

- `docs/development/monster-content-expansion.md`: append to the opening paragraph the sentence `Sections from 霧泉蛙 onward record the central mountains and northwest highland forest species of the near-settlement programme's Wave 2.`

The user authorised the Wave 2 roster in the session that requested this change set. These notes record that approval. The species changes that follow do not edit them.

### D7. Tests

- No test file changes. Narration coverage, the kit contract and the composition-group derivation already include the new rows.

### D8. Developer review section

Append `## 霧泉蛙` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Fragile colony hopper: hit points and defense near the low band's floor, agility in the band's upper half.
* MP holds two casts of the tongue's MP cost; SP holds three casts of its SP cost.
* The fixed MP drain (4) is far below the crocodile's fixed MP drain (10) and equals the bat's fixed HP drain, which suits a low-tier contact strike.
* The stronger 泉主型 holds a whole spring pool, so it carries a larger pool, attack and defense at grade E.
- `### Reuse of the contact drain representative`: the signature, the unchanged representative `bank_lurker`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later key sorts before a representative] → every Wave 1 and Wave 2 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_crocodile_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change mist-spring-frog-species` and `openspec validate mist-spring-frog-species --strict`.
