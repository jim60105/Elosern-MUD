# Design

## Context

See proposal.md (Why). Facts at `3756992d`:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS` and `_VARIANT_DECLARATIONS` at import. Bands come from `MONSTER_TIER_REGISTRY`: low HP 25–70, attack 3–12, agility 3–12, defense 2–8, grades F–E; mid HP 110–230, attack 18–28, agility 10–24, defense 10–16, grades D–C; high HP 300–750, attack 26–40, agility 16–30, defense 18–32, grades B–A. `magic_power` must be 0 and MP/SP have no band. Display names are limited to 5 code points (`MONSTER_NAME_MAX_CODE_POINTS`).
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」 and `author_conjecture_zh` to contain 「尚未證實」, and it forbids registry strings that name a skill, behaviour or trait key.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by `(slot, effect family, audience, requires_hit_from)` and requires one committed representative per group, the group's sorted-minimum key. This kit's signature is `(("active", "damage", "enemies", None), ("active", "gauge_transfer", "enemies", 0))`, the shipped contact drain group, whose representative `bank_lurker` is declared in `world.rules.tests.test_crocodile_resource_skill`. Every new variant key sorts after `bank_lurker`, so the representative does not move and no smoke module, shard entry or seed entry is added. The drained gauge is HP instead of the crocodile's MP. The signature reads only the effect family, so the group and its representative stay unchanged. HP drain transfer and rollback are owned by the shared synthetic suites in `world/rules/tests/test_gauge_transfer/`, and AI estimation of an HP drain by `world/rules/tests/test_monster_ai_estimation.py`.
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests` requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, a magic tier for elemental MP skills (MP 10–16 single, 14–20 area) and `None` otherwise. `validate_catalog` requires one narration row per active skill, and `world/rules/status_display.py` fails closed for a buff or modifier without a display row.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, modifier rule, intelligence and mode entry, plus the referenced bindings. `world/rules/tests/test_monster_ai_activation.py` compares that fingerprint with `docs/development/monster-ai-activation-evidence/activation.json`.
- Every kit here carries a damage occurrence, so the legacy decision body proposes it and no utility binding or intelligence value is needed (`owned-kit-decision-coverage` applies only to support-only kits).

## Candidate review (`docs/lore/monster-creation-guidelines.md`)

| Question | Answer |
| --- | --- |
| Familiar archetype | A vampire bat. |
| Special way of life | Dark-element incisors draw a small amount of life through a shallow bite, which lets a colony roost in hollow giant trunks and dungeon mouths and feed at dusk. |
| World relation | The north deep forest is dense with dungeons (`docs/lore/overview.md`), and supply parties camp at dungeon entrances with pack animals. |
| Ability limits | The draw happens only at a landed bite, is a small fixed amount, and the wound heals by the next day. No disease, lasting bleed or permanent loss (dark element: HP drain, magic-system §3). |
| Local conflict | A colony keeps biting a supply party's pack animals at a dungeon-approach camp, so the party asks for the roost tree above the camp to be cleared. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar) and from the other five Wave 1 species.

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `north-deep-forest-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "hollow_tree_bat",
        "空木蝠",
        "空木蝠是翼展約一臂寬的蝙蝠類魔獸，成群棲息於北部深林巨木的中空樹幹與迷宮入口附近的岩縫。",
        "深褐色短毛覆蓋小巧身軀，薄翼膜在火光下透出暗紅血管。"
        "尖耳大而薄，口中兩枚細長門牙向前突出。",
        "黃昏時，群體從同一株空心巨木湧出，在林冠下穿梭捕食飛蟲。"
        "牠們以叫聲辨認方向，在不透光的樹洞與岩縫裡也能自在飛行。"
        "牠們會落在熟睡的鹿與馱獸身上，以帶著暗屬性的門牙咬開淺口，從咬口吸取少量血氣，轉成自己的體力；"
        "每次咬合吸取的分量有限，傷口隔日即可癒合。"
        "深入迷宮的探險隊常在入口附近遇上整群空木蝠，夜裡守營的人會替馱獸蓋上厚布。",
        ("north_deep_forest",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；門牙暗屬性力量的成因不在設定中交代。",
        "（作者私有：作者解釋）低階群居蝙蝠：暗屬性門牙只在咬合命中時吸取少量體力，不傳染疾病、不造成持續失血或永久傷害；戰鬥呈現為咬擊與命中後的固定體力吸取。連結迷宮入口與探險隊的夜間營地。",
        "（作者私有：尚未證實的猜想）探險者之間流傳空木蝠群聚的樹洞附近必有迷宮入口，這種說法尚未證實。",
        "hollow_roost_flier",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "hollow_roost_flier",
        "hollow_tree_bat",
        "棲洞型",
        "普通版本，成群棲息於中空樹幹，黃昏外出覓食。",
        "low",
        True,
        MonsterCombatProfile(
            hp=28, mp=20, sp=6, atk_phys=5, agility=11, defense=2, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("hollow_bat_bite",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

```python
    MonsterVariant(
        "colony_sentinel",
        "hollow_tree_bat",
        "哨群型",
        "棲群中體型最大的個體，守在樹洞口最先迎向闖入者，以尖銳叫聲召回同伴。",
        "low",
        False,
        MonsterCombatProfile(
            hp=50, mp=30, sp=10, atk_phys=9, agility=12, defense=3, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("hollow_bat_bite",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "hollow_bat_bite",
        "空木吸咬",
        "以帶著暗屬性的門牙咬向單一敵方目標，造成物理傷害；命中時從咬口吸取少量體力轉入自身。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 2},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="dark",
        effects=["damage:dark:physical", "gauge_transfer:hp:drain:fixed:4"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="dark",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("hollow_tree_bat",),
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
- `world/skills/narration/data_dark.py`, appended after the last monster row in that file:

```python
    NarrationRow(
        "hollow_bat_bite",
        action=(
            "{actor} 從暗處掠下，細長門牙咬向對手。",
            "{actor} 拍著薄翼貼近，一口咬住對方的手背。",
        ),
    ),
```

### D5. AI binding and activation evidence

No `world/rules/rulebook/monster_behaviour.yaml` edit. Each variant binds the shipped archetype named in D2, and the legacy body selects the damage-bearing kit. Run `ActivationRecordTests`, `ActivationBindingTests` and `RollbackTests`. If they pass, the fingerprint did not move and the evidence stays untouched. If a fingerprint comparison fails, re-fingerprint following the `mudfilm-slime-species` precedent (archived change design D5, steps 1–4), without touching `activated` or `activation_bindings`:

1. Run `uv run --locked python tools/monster_ai_manual_reports.py selector` and copy `.var/monster-ai-manual-reports/selector-check.json` and `.md` over `docs/development/monster-ai-manual-evidence/`.
2. Read the new `configuration_fingerprint` from the regenerated `selector-check.json`. Read the rollback fingerprint from the `RollbackTests` failure message.
3. In `activation.json`, update `configuration_fingerprint`, `legacy_rollback.configuration_fingerprint` and the `selector-check.json` evidence entry's fingerprint.
4. Update the fingerprint lines in `docs/development/monster-ai-activation-evidence/README.md` and the selector paragraph of `docs/development/monster-ai-manual-evidence/README.md`.

### D6. Bestiary and ledger

- Overview row, inserted in the `## 收錄總覽` table after the last `| 低階 |` row:

  `| 低階 | 空木蝠 | 北部深林巨木的中空樹幹與迷宮入口岩縫 | 咬合時以暗屬性門牙吸取少量體力 | 棲洞型、哨群型 |`

- New section at the end of `## 低階魔物`, immediately before `## 中階魔物` (after any Wave 1 low section already added), transcribed exactly:

````markdown
### 空木蝠

```bestiary
species: hollow_tree_bat
parent-species: hollow_tree_bat
default-variant: hollow_roost_flier
variants:
  - key: hollow_roost_flier
    status: delivered
  - key: colony_sentinel
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

**原型與棲地。**空木蝠是翼展約一臂寬的蝙蝠類魔獸，成群棲息於北部深林巨木的中空樹幹與迷宮入口附近的岩縫。

**外觀。**深褐色短毛覆蓋小巧身軀，薄翼膜在火光下透出暗紅血管。尖耳大而薄，口中兩枚細長門牙向前突出。

**生態與在地關係。**黃昏時，群體從同一株空心巨木湧出，在林冠下穿梭捕食飛蟲，並以叫聲辨認方向。牠們也會落在熟睡的鹿與馱獸身上咬開淺口，傷口隔日即可癒合。深入迷宮的探險隊常在入口附近遇上整群空木蝠，夜裡守營的人會替馱獸蓋上厚布。棲群中體型最大、守在樹洞口的個體稱為哨群型。

**戰鬥中的表現。**牠以帶著暗屬性的門牙咬向對手，咬中時從咬口吸取少量血氣，轉成自己的體力；吸取只發生在咬中的瞬間，每次咬合吸取的分量有限。

| 變體 | 核准方向 |
| --- | --- |
| 棲洞型 | 普通版本，成群棲息於中空樹幹，黃昏外出覓食 |
| 哨群型 | 棲群中體型最大的個體，守在樹洞口最先迎向闖入者，以尖銳叫聲召回同伴 |

**委託背景示例。**前往永夜迷宮的補給隊在入口外紮營時，馱獸連續兩晚被空木蝠群叮咬。補給隊長委託公會清理營地上方那株空心巨木裡的棲群，讓隊伍能安心過夜。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `hollow_tree_bat` | <implementation date> | read against the registry's published ecology field; the trouble stays local to dungeon-approach camps and their pack animals, the bites heal by the next day, and the drain comes from the creature's own teeth | checked against the declared kit: the bite is a single-target dark-element physical strike, and the section states that the small HP draw follows a landed bite and a miss draws nothing, matching the declared hit dependency; the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. The reviewer may reword a cell after actually reading the section, but must keep all six cells.

### D7. Tests

- No test file changes. Narration coverage, the kit contract and the composition-group derivation already include the new rows.

### D8. Developer review section

Append `## 空木蝠` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Agile, fragile flier: agility near the low band's top, defense at its floor, hit points near its floor.
* MP holds two casts of the bite's MP cost; SP holds three casts of its SP cost.
* The fixed HP drain (4) is far below the crocodile's fixed MP drain (10), which suits a low-tier contact bite.
* The stronger 哨群型 guards the roost mouth, so it carries a larger pool and attack at grade E.
- `### Reuse of the contact drain representative`: the signature, the unchanged representative `bank_lurker`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later Wave 1 key sorts before a representative] → every Wave 1 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_crocodile_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.skills.tests.test_narration_catalog`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change hollow-tree-bat-species` and `openspec validate hollow-tree-bat-species --strict`.
