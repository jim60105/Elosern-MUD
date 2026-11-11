# Design

## Context

See proposal.md (Why). Facts at `d1ac4b84` plus the planned Wave 1 species rows (`openspec/changes/*-species/`), which land first:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS` and `_VARIANT_DECLARATIONS` at import. Bands come from `MONSTER_TIER_REGISTRY`: low HP 25–70, attack 3–12, agility 3–12, defense 2–8, grades F–E; mid HP 110–230, attack 18–28, agility 10–24, defense 10–16, grades D–C; high HP 300–750, attack 26–40, agility 16–30, defense 18–32, grades B–A. `magic_power` must be 0 and MP/SP have no band. Display names are limited to 5 code points (`MONSTER_NAME_MAX_CODE_POINTS`).
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」 and `author_conjecture_zh` to contain 「尚未證實」, and it forbids registry strings that name a skill, behaviour or trait key.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by `(slot, effect family, audience, requires_hit_from)` and requires one committed representative per group, the group's sorted-minimum key. This kit's signature is `(("active", "damage", "enemies", None), ("active", "self_buff_apply", "self", None))`, the shipped self-guard strike group, whose representative `burrow_maker` is declared in `world.rules.tests.test_tide_lamp_crab_resource_skill`. Every new variant key sorts after `burrow_maker` (and every Wave 1 key does too), so the representative does not move and no smoke module, shard entry or seed entry is added. The self mount raises agility rather than defense, like the owl's. The signature reads only family, audience and hit dependency, so the grouse joins the crab and hare group without a new representative.
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests` requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, a magic tier for elemental MP skills (MP 10–16 single, 14–20 area) and `None` otherwise. `validate_catalog` requires one narration row per active skill, and `world/rules/status_display.py` fails closed for a buff or modifier without a display row.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, modifier rule, intelligence and mode entry, plus the referenced bindings. `world/rules/tests/test_monster_ai_activation.py` compares that fingerprint with `docs/development/monster-ai-activation-evidence/activation.json`.
- Every kit here carries a damage occurrence, so the legacy decision body proposes it and no utility binding or intelligence value is needed (`owned-kit-decision-coverage` applies only to support-only kits).

## Candidate review (`docs/lore/monster-creation-guidelines.md`)

| Question | Answer |
| --- | --- |
| Familiar archetype | A capercaillie (wood grouse), the lekking conifer-forest bird. |
| Special way of life | Faint wind power swells the air under its own wings for an explosive flush from underfoot and a sharp dodge; cocks gather on fixed lek clearings each spring. |
| World relation | Beastfolk tribes use the leks as seasonal spring hunting grounds where young hunters practise tracking (northwest hunting and tribal culture; terrain flavour: herds and tracks among the conifers). |
| Ability limits | The wind acts only under its own wings; it knocks no one back and moves no one else. The strike is a wing buffet followed by a brief self agility rise (wind element: motion and evasion). |
| Local conflict | In lek season the cocks scatter a herder's goats on the path through the lek, so the commission is to drive them off the goat path before the season ends. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar), the Wave 1 species (spore-cap mushroom, moss-quill porcupine, hollow-tree bat, hush-wing owl, vine-net spider, moss-crown stag) and the other nine Wave 2 species. It is an animal, clearly distinct from every beastfolk subspecies (wolf, cat, bear, rabbit, cattle, tiger, fox).

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `northwest-highland-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "drum_wing_grouse",
        "鼓翼松雞",
        "鼓翼松雞是約小型犬大小的松雞類魔獸，成群生活於西北高地針葉林的林床與林間空地。",
        "雄雞羽毛黑藍，眼上一道紅色肉冠，尾羽展開時像一面半圓扇；"
        "雌雞羽色棕褐帶細斑，伏在林床上時與落針融成一片。",
        "牠們在林床上啄食松針、嫩芽與漿果，受驚時以微弱風屬性力量讓翼下的氣流驟然鼓起，從腳邊轟然驚飛，再貼著樹幹急轉閃避；"
        "這股風力作用在牠們自己的翅膀周圍。"
        "每年春天，雄雞聚在固定的林間空地上展尾鳴叫、互相爭鬥，這些求偶場也是獸人部族世代相傳的春季獵場，年輕獵人會在這裡練習追蹤與埋伏。"
        "求偶季的雄雞會撲向走進求偶場的任何身影，連牧人的山羊與獵人的獵犬也照撲不誤。"
        "近身時，牠鼓翼撲擊對手，撲出後順勢驚飛，短暫變得更加靈活。",
        ("northwest_highland_forest",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；翼下風力的成因不在設定中交代。",
        "（作者私有：作者解釋）低階群居松雞：風屬性只鼓起自身翼下氣流以驚飛閃避，不造成擊退或改變他人移動；戰鬥呈現為鼓翼撲擊與自身短暫敏捷提升。連結獸人部族的春季獵場與年輕獵人的練習。",
        "（作者私有：尚未證實的猜想）獵鷹鎮的獵人說領場型雄雞鳴叫的那天早上，整片林子的獵物都會變得警覺，這種說法尚未證實。",
        "pine_floor_grouse",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "pine_floor_grouse",
        "drum_wing_grouse",
        "林床型",
        "普通版本，成群在林床上啄食松針與漿果。",
        "low",
        True,
        MonsterCombatProfile(
            hp=32, mp=20, sp=6, atk_phys=4, agility=9, defense=3, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("drum_wing_burst",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

```python
    MonsterVariant(
        "lek_master_cock",
        "drum_wing_grouse",
        "領場型",
        "在求偶場中央占據最好位置的老雄雞，尾扇最寬，會撲向走進求偶場的任何身影。",
        "low",
        False,
        MonsterCombatProfile(
            hp=56, mp=30, sp=10, atk_phys=9, agility=11, defense=4, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("drum_wing_burst",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "drum_wing_burst",
        "鼓翼驚飛",
        "以風屬性力量鼓起翼下氣流後撲擊單一敵方目標，造成物理傷害；出擊後順勢驚飛，短暫提高自身敏捷。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 2},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="wind",
        effects=["damage:wind:physical", "self_buff_apply:drum_burst"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="wind",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("drum_wing_grouse",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=0.8, audience=EffectAudience.ENEMIES),
            EffectPolicy(coefficient=1.0, audience=EffectAudience.SELF),
        ),
    ),
```

Also append one sentence to that module's docstring describing this kit's composition, in the style of the existing sentences.

### D4. Rulebook and narration

- `world/rules/rulebook/buffs.yaml`, appended after the last monster resource-skill buff (the buff of the latest species already merged in the serial chain), with a zh-TW comment line before it:

```yaml
# 魔物資源技能（西北高地第二波）：鼓翼松雞鼓翼驚飛：每次已結算且具合法目標的施放都順勢驚飛，敏捷提升資料在 combat_modifiers.yaml 的 drum_burst_agility_flat 列（wax_slip_agility_flat 的 agility_flat 先例）。
- key: drum_burst
  duration: 15
  stacking: refresh
  polarity: buff
  modifiers: {}
```

- `world/rules/rulebook/combat_modifiers.yaml`, appended after the last monster resource-skill rule (the latest merged species' rule) and before the fatigue block:

```yaml
- id: drum_burst_agility_flat
  when: {buff_active: drum_burst}
  then: {agility_flat: 2}
```

- `world/rules/rulebook/status_display.yaml`, appended after the last monster resource-skill rows (the latest merged species' rows):

```yaml
- code: drum_burst
  label: 驚飛閃身
  severity: beneficial
- code: drum_burst_agility_flat
  label: 驚飛閃身敏捷提升
  severity: beneficial
```

- `world/skills/narration/data_wind.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "drum_wing_burst",
        action=(
            "{actor} 鼓起雙翼轟然驚飛，順勢撲向對手。",
            "{actor} 展開尾扇低聲鳴響，撲翅撞了上去。",
        ),
    ),
```

### D5. AI binding and activation evidence

No `world/rules/rulebook/monster_behaviour.yaml` edit. This link adds a timed effect and a modifier, so the tuning fingerprint moves and `ActivationRecordTests` and `RollbackTests` are expected to fail until the evidence is re-fingerprinted (steps 1–4 below). Each variant binds the shipped archetype named in D2, and the legacy body selects the damage-bearing kit. Run `ActivationRecordTests`, `ActivationBindingTests` and `RollbackTests`. If they pass, the fingerprint did not move and the evidence stays untouched. If a fingerprint comparison fails, re-fingerprint following the `mudfilm-slime-species` precedent (archived change design D5, steps 1–4), without touching `activated` or `activation_bindings`:

1. Run `uv run --locked python tools/monster_ai_manual_reports.py selector` and copy `.var/monster-ai-manual-reports/selector-check.json` and `.md` over `docs/development/monster-ai-manual-evidence/`.
2. Read the new `configuration_fingerprint` from the regenerated `selector-check.json`. Read the rollback fingerprint from the `RollbackTests` failure message.
3. In `activation.json`, update `configuration_fingerprint`, `legacy_rollback.configuration_fingerprint` and the `selector-check.json` evidence entry's fingerprint.
4. Update the fingerprint lines in `docs/development/monster-ai-activation-evidence/README.md` and the selector paragraph of `docs/development/monster-ai-manual-evidence/README.md`.

### D6. Bestiary and ledger

- Overview row, inserted in the `## 收錄總覽` table after the last `| 低階 |` row:

  `| 低階 | 鼓翼松雞 | 西北高地針葉林的林床與林間空地 | 鼓起翼下氣流，從腳邊轟然驚飛 | 林床型、領場型 |`

- New section at the end of `## 低階魔物`, immediately before `## 中階魔物` (after every low section an earlier programme change added), transcribed exactly:

````markdown
### 鼓翼松雞

```bestiary
species: drum_wing_grouse
parent-species: drum_wing_grouse
default-variant: pine_floor_grouse
variants:
  - key: pine_floor_grouse
    status: delivered
  - key: lek_master_cock
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

**原型與棲地。**鼓翼松雞是約小型犬大小的松雞類魔獸，成群生活於西北高地針葉林的林床與林間空地。

**外觀。**雄雞羽毛黑藍，眼上一道紅色肉冠，尾羽展開時像一面半圓扇；雌雞羽色棕褐帶細斑，伏在林床上時與落針融成一片。

**生態與在地關係。**牠們在林床上啄食松針、嫩芽與漿果。每年春天，雄雞聚在固定的林間空地上展尾鳴叫、互相爭鬥，這些求偶場也是獸人部族世代相傳的春季獵場，年輕獵人會在這裡練習追蹤與埋伏。求偶季的雄雞會撲向走進求偶場的任何身影，連牧人的山羊與獵人的獵犬也照撲不誤。在求偶場中央占據最好位置、尾扇最寬的老雄雞稱為領場型。

**戰鬥中的表現。**受驚時，牠以微弱風屬性力量讓翼下的氣流驟然鼓起，從腳邊轟然驚飛，再貼著樹幹急轉閃避；這股風力作用在牠自己的翅膀周圍。近身時，牠鼓翼撲擊對手，撲出後順勢驚飛，短暫變得更加靈活。

| 變體 | 核准方向 |
| --- | --- |
| 林床型 | 普通版本，成群在林床上啄食松針與漿果 |
| 領場型 | 在求偶場中央占據最好位置的老雄雞，尾扇最寬，會撲向走進求偶場的任何身影 |

**委託背景示例。**獵鷹鎮外的春季求偶場今年聚了特別多雄雞，鎮上牧人趕羊經過時，羊群被撲得四散。牧人委託公會在求偶季結束前把羊道上的雄雞趕回林子裡，讓羊群能照常上山吃草。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `drum_wing_grouse` | <implementation date> | read against the registry's published ecology field; the trouble stays local to spring lek clearings that herders and young hunters cross, and the wind acts under the grouse's own wings | checked against the declared kit: the wing buffet is a single-target wind-element physical strike, and the brief agility rise mounts on the caster for every resolved attempt, matching the self policy with no hit dependency; the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D7. Tests

- `world/rules/tests/test_combat_modifiers.py::CombatModifierTests`: add `test_rule_drum_burst_agility_flat`, copying the four lines of `test_rule_rock_echo_stagger_agility_flat` with `RULES["drum_burst_agility_flat"]`.

### D8. Developer review section

Append `## 鼓翼松雞` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Ground bird with burst flight: agility in the low band's upper half, defense equal to the hare's ordinary variant.
* MP holds two casts of the burst's MP cost; SP holds three casts of its SP cost.
* The burst (+2 agility for 15 s) is one below the rat's and the owl's shipped +3, a low-tier self rise.
* The stronger 領場型 holds the lek centre at grade E with a larger pool and attack.
- `### Reuse of the self-guard strike representative`: the signature, the unchanged representative `burrow_maker`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later key sorts before a representative] → every Wave 1 and Wave 2 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_tide_lamp_crab_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.rules.tests.test_combat_modifiers.CombatModifierTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change drum-wing-grouse-species` and `openspec validate drum-wing-grouse-species --strict`.
