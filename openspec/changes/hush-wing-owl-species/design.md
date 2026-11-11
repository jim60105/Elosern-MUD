# Design

## Context

See proposal.md (Why). Facts at `3756992d`:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS` and `_VARIANT_DECLARATIONS` at import. Bands come from `MONSTER_TIER_REGISTRY`: low HP 25–70, attack 3–12, agility 3–12, defense 2–8, grades F–E; mid HP 110–230, attack 18–28, agility 10–24, defense 10–16, grades D–C; high HP 300–750, attack 26–40, agility 16–30, defense 18–32, grades B–A. `magic_power` must be 0 and MP/SP have no band. Display names are limited to 5 code points (`MONSTER_NAME_MAX_CODE_POINTS`).
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」 and `author_conjecture_zh` to contain 「尚未證實」, and it forbids registry strings that name a skill, behaviour or trait key.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by `(slot, effect family, audience, requires_hit_from)` and requires one committed representative per group, the group's sorted-minimum key. This kit's signature is `(("active", "damage", "enemies", None), ("active", "self_buff_apply", "self", None))`, the shipped self-guard strike group, whose representative `burrow_maker` is declared in `world.rules.tests.test_tide_lamp_crab_resource_skill`. Every new variant key sorts after `burrow_maker`, so the representative does not move and no smoke module, shard entry or seed entry is added. The self mount raises agility rather than defense. The signature reads only family, audience and hit dependency, so the owl joins the crab and hare group without a new representative.
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests` requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, a magic tier for elemental MP skills (MP 10–16 single, 14–20 area) and `None` otherwise. `validate_catalog` requires one narration row per active skill, and `world/rules/status_display.py` fails closed for a buff or modifier without a display row.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, modifier rule, intelligence and mode entry, plus the referenced bindings. `world/rules/tests/test_monster_ai_activation.py` compares that fingerprint with `docs/development/monster-ai-activation-evidence/activation.json`.
- Every kit here carries a damage occurrence, so the legacy decision body proposes it and no utility binding or intelligence value is needed (`owned-kit-decision-coverage` applies only to support-only kits).

## Candidate review (`docs/lore/monster-creation-guidelines.md`)

| Question | Answer |
| --- | --- |
| Familiar archetype | A great owl. |
| Special way of life | Faint wind power combs out its wing-edge feathers so wingbeats dissolve into the surrounding wind; it hunts silently along the canopy at dusk and midnight. |
| World relation | Hunting parties from 北林堡 and 虎嘯城 camp overnight in the deep forest with dogs and small pack animals (beastfolk hunting culture). |
| Ability limits | The wind acts only on its own feathers; it causes no invisibility, sleep or change to anyone else's senses, and its strike is an ordinary talon swoop followed by a short lift (wind element: movement and evasion). |
| Local conflict | A nesting owl keeps clawing a hunting party's dogs at a known camp site, so the party asks for it to be dealt with before dusk. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar) and from the other five Wave 1 species.

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `north-deep-forest-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "hush_wing_owl",
        "靜羽梟",
        "靜羽梟是雙翼展開近一人高的大型貓頭鷹類魔獸，獨自或成對棲息於北部深林巨木高處的樹洞。",
        "灰綠色羽毛帶著苔蘚般的斑紋，停在樹枝上時幾乎與樹皮融為一體。"
        "圓臉盤中央是一對琥珀色大眼，腳爪粗壯，趾尖彎鉤。",
        "牠在黃昏與深夜狩獵，以微弱風屬性力量梳開翼緣細羽，讓拍翼聲散進周圍的風裡，再貼著林冠滑向獵物。"
        "這股風力作用在牠自己的羽翼周圍，飛行與攻擊的方向由牠的腳爪與身形決定。"
        "牠捕食野兔、松鼠與落單的空木蝠，也會撲向夜裡在林間移動的小型馱獸。"
        "獵人在深林營地過夜時，會留意頭頂樹枝上的琥珀色眼光，並把燈火留在馱獸身旁。"
        "近身時，牠以腳爪掠擊對手，擊出後順勢藉風抬升，短暫變得更加靈活。",
        ("north_deep_forest",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；靜羽風力的成因不在設定中交代。",
        "（作者私有：作者解釋）中階獨居獵食者：風屬性只梳開自身翼緣細羽，使拍翼聲散開，不造成隱形、催眠或改變他人感官；戰鬥呈現為腳爪掠擊與自身短暫敏捷提升。黃昏與深夜才主動接觸。",
        "（作者私有：尚未證實的猜想）虎嘯城的獵人相信靜羽梟的叫聲預示天氣轉壞，這種說法尚未證實。",
        "hush_wing_hunter",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "hush_wing_hunter",
        "hush_wing_owl",
        "夜獵型",
        "普通版本，在黃昏與深夜沿林冠獵捕。",
        "mid",
        True,
        MonsterCombatProfile(
            hp=120, mp=30, sp=20, atk_phys=21, agility=22, defense=10, magic_power=0
        ),
        "D",
        True,
        active_skill_keys=("hush_wing_swoop",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
```

```python
    MonsterVariant(
        "old_hollow_owl",
        "hush_wing_owl",
        "古巢型",
        "長年占據同一株巨木樹洞的老個體，育雛期間會撲向靠近巢樹的身影。",
        "mid",
        False,
        MonsterCombatProfile(
            hp=160, mp=50, sp=30, atk_phys=26, agility=24, defense=12, magic_power=0
        ),
        "C",
        True,
        active_skill_keys=("hush_wing_swoop",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "hush_wing_swoop",
        "靜羽掠爪",
        "以風屬性力量收斂拍翼聲後掠爪攻擊單一敵方目標，造成物理傷害；出擊後藉風抬升，短暫提高自身敏捷。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 5},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="wind",
        effects=["damage:wind:physical", "self_buff_apply:hush_lift"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="wind",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("hush_wing_owl",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=1.0, audience=EffectAudience.ENEMIES),
            EffectPolicy(coefficient=1.0, audience=EffectAudience.SELF),
        ),
    ),
```

Also append one sentence to that module's docstring describing this kit's composition, in the style of the existing sentences.

### D4. Rulebook and narration

- `world/rules/rulebook/buffs.yaml`, appended after the last monster resource-skill buff (`reservoir_film`, or the previous Wave 1 species' buff), with a zh-TW comment line before it:

```yaml
# 魔物資源技能（北部深林第一波）：靜羽梟靜羽掠爪：每次已結算且具合法目標的施放都藉風抬升，敏捷提升資料在 combat_modifiers.yaml 的 hush_lift_agility_flat 列（wax_slip_agility_flat 的 agility_flat 先例）。
- key: hush_lift
  duration: 15
  stacking: refresh
  polarity: buff
  modifiers: {}
```

- `world/rules/rulebook/combat_modifiers.yaml`, appended after the last monster resource-skill rule (`reservoir_film_defense`, or the previous Wave 1 rule) and before the fatigue block:

```yaml
- id: hush_lift_agility_flat
  when: {buff_active: hush_lift}
  then: {agility_flat: 3}
```

- `world/rules/rulebook/status_display.yaml`, appended after `reservoir_film_defense` (or the previous Wave 1 rows):

```yaml
- code: hush_lift
  label: 靜羽抬升
  severity: beneficial
- code: hush_lift_agility_flat
  label: 靜羽抬升敏捷提升
  severity: beneficial
```

- `world/skills/narration/data_wind.py`, appended after the last monster row in that file:

```python
    NarrationRow(
        "hush_wing_swoop",
        action=(
            "{actor} 無聲滑下，腳爪掠過對手肩頭。",
            "{actor} 貼著枝葉俯衝，一爪抓出後隨風拔高。",
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

- Overview row, inserted in the `## 收錄總覽` table after the last `| 中階 |` or `| 中階／高階 |` row:

  `| 中階 | 靜羽梟 | 北部深林巨木高處的樹洞 | 梳開翼緣細羽，使拍翼聲散進風裡 | 夜獵型、古巢型 |`

- New section at the end of `## 中階魔物`, immediately before `## 高階魔物` (after any Wave 1 mid section already added), transcribed exactly:

````markdown
### 靜羽梟

```bestiary
species: hush_wing_owl
parent-species: hush_wing_owl
default-variant: hush_wing_hunter
variants:
  - key: hush_wing_hunter
    status: delivered
  - key: old_hollow_owl
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

**原型與棲地。**靜羽梟是雙翼展開近一人高的大型貓頭鷹類魔獸，獨自或成對棲息於北部深林巨木高處的樹洞。

**外觀。**灰綠色羽毛帶著苔蘚般的斑紋，停在樹枝上時幾乎與樹皮融為一體。圓臉盤中央是一對琥珀色大眼，腳爪粗壯，趾尖彎鉤。

**生態與在地關係。**牠在黃昏與深夜狩獵，捕食野兔、松鼠與落單的空木蝠，也會撲向夜裡在林間移動的小型馱獸。獵人在深林營地過夜時，會留意頭頂樹枝上的琥珀色眼光，並把燈火留在馱獸身旁。長年占據同一株巨木樹洞的老個體稱為古巢型，育雛期間會撲向靠近巢樹的身影。

**戰鬥中的表現。**牠以微弱風屬性力量梳開翼緣細羽，讓拍翼聲散進周圍的風裡，再貼著林冠滑向獵物；這股風力作用在牠自己的羽翼周圍。近身時，牠以腳爪掠擊對手，擊出後順勢藉風抬升，短暫變得更加靈活。

| 變體 | 核准方向 |
| --- | --- |
| 夜獵型 | 普通版本，在黃昏與深夜沿林冠獵捕 |
| 古巢型 | 長年占據同一株巨木樹洞的老個體，育雛期間會撲向靠近巢樹的身影 |

**委託背景示例。**北林堡的狩獵隊在深林第一處宿營地過夜時，獵犬接連被抓傷，夜哨只見到頭頂一對琥珀色眼光。隊長委託公會在黃昏前趕到宿營地，處理盤據那片林冠的靜羽梟。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `hush_wing_owl` | <implementation date> | read against the registry's published ecology field; the trouble stays local to deep-forest camps at dusk and night, and the wind acts on the owl's own wing feathers | checked against the declared kit: the talon swoop is a single-target wind-element physical strike, and the brief agility rise mounts on the caster for every resolved attempt, matching the self policy with no hit dependency; the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. The reviewer may reword a cell after actually reading the section, but must keep all six cells.

### D7. Tests

- `world/rules/tests/test_combat_modifiers.py::CombatModifierTests`: add `test_rule_hush_lift_agility_flat`, copying the four lines of `test_rule_rock_echo_stagger_agility_flat` with `RULES["hush_lift_agility_flat"]`.

### D8. Developer review section

Append `## 靜羽梟` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Agile ambush predator: agility above the lynx's ordinary variant and below the mid band's ceiling.
* Lightly built: defense at the mid band's floor.
* MP holds three casts of the swoop's MP cost; SP holds four casts of its SP cost.
* The lift (+3 agility for 15 s) equals the rat's shipped self agility rise.
* The stronger 古巢型 guards a nest tree at grade C with a larger pool.
- `### Reuse of the self-guard strike representative`: the signature, the unchanged representative `burrow_maker`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later Wave 1 key sorts before a representative] → every Wave 1 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_tide_lamp_crab_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.rules.tests.test_combat_modifiers.CombatModifierTests`, `world.skills.tests.test_narration_catalog`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change hush-wing-owl-species` and `openspec validate hush-wing-owl-species --strict`.
