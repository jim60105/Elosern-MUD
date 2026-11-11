# Design

## Context

See proposal.md (Why). Facts at `cf4643a1` plus the planned Wave 2, Wave 3 and earlier Wave 4 species rows still open under `openspec/changes/*-species/`, which land first in the serial chain:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS` and `_VARIANT_DECLARATIONS` at import. Bands come from `MONSTER_TIER_REGISTRY`: low HP 25–70, attack 3–12, agility 3–12, defense 2–8, grades F–E; mid HP 110–230, attack 18–28, agility 10–24, defense 10–16, grades D–C; high HP 300–750, attack 26–40, agility 16–30, defense 18–32, grades B–A. `magic_power` must be 0 and MP/SP have no band. Display names are limited to 5 code points (`MONSTER_NAME_MAX_CODE_POINTS`).
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」 and `author_conjecture_zh` to contain 「尚未證實」, and it forbids registry strings that name a skill, behaviour or trait key.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by `(slot, effect family, audience, requires_hit_from)` and requires one committed representative per group, the group's sorted-minimum key. This kit's signature is `(("active", "damage", "enemies", None), ("active", "self_buff_apply", "self", None))`, the shipped self-guard strike group, whose representative `burrow_maker` is declared in `world.rules.tests.test_tide_lamp_crab_resource_skill`. Every new variant key sorts after `burrow_maker` (as every Wave 1, Wave 2 and Wave 3 key does), so the representative does not move and no smoke module, shard entry or seed entry is added. The self policy declares no hit dependency, following the crab and hare kits, so the mount lands on every resolved attempt including a miss. The self mount raises defense (`defense`), the axis of the crab's and the hare's shipped guards. The skill is elementless with an SP-only cost, so `spell_tier_for` returns `None` (the goblin and wolverine precedent).
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests` requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, a magic tier for elemental MP skills (MP 10–16 single, 14–20 area) and `None` otherwise. `validate_catalog` requires one narration row per active skill, and `world/rules/status_display.py` fails closed for a buff or modifier without a display row.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, modifier rule, intelligence and mode entry, plus the referenced bindings. `world/rules/tests/test_monster_ai_activation.py` compares that fingerprint with `docs/development/monster-ai-activation-evidence/activation.json`.
- Every kit here carries a damage occurrence, so the legacy decision body proposes it and no utility binding or intelligence value is needed (`owned-kit-decision-coverage` applies only to support-only kits).

## Candidate review (`docs/lore/monster-creation-guidelines.md`)

| Question | Answer |
| --- | --- |
| Familiar archetype | A sea star of rock pools, oyster beds and slipways. |
| Special way of life | Its body wall stiffens abnormally in a blink from soft to stone-hard, so it clings to rock through breaking waves and pries oysters open with its arms. |
| World relation | The oyster racks of the fishing villages of 漁灣鎮 and 南潮港 and the boatyard slipways where wooden ships are launched (southwest coast terrain flavour: finely built wooden ships, shipwright workshops, fishing villages). |
| Ability limits | The hardening is a body ability with no element and acts only on its own body wall; it hardens nothing around it. Every resolved press brings a brief self defense rise. |
| Local conflict | A swarm empties three rows of oyster racks, so the fishers ask for the sea stars to be cleared off the racks before the spring tide. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar), the Wave 1 species (spore-cap mushroom, moss-quill porcupine, hollow-tree bat, hush-wing owl, vine-net spider, moss-crown stag), the Wave 2 species (mountain frog, fire salamander, bearded vulture, giant moth, giant constrictor, capercaillie, beaver, mole, wolverine, griffin), the Wave 3 species (dung beetle, wild horse, grey heron, giant snapping turtle, mudskipper, herring gull, harbour seal) and the other six Wave 4 species (giant harvester ant of dry salt roads, mantis shrimp of harbour shallows, marine iguana of sea cliffs, giant octopus of sea caves (kraken folklore), cave cricket of mines and cellars, antlion larva of quarry sand). It is an animal, clearly distinct from every beastfolk subspecies (wolf, cat, bear, rabbit, cattle, tiger, fox).

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `southwest-coast-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "stiff_arm_starfish",
        "硬腕海星",
        "硬腕海星是五條腕足張開約一臂寬的海星類魔獸，成片棲息於西南海岸的潮池、蚵架與造船坊的下水滑道。",
        "身體是五條粗短腕足連成的星形，背面橙紅，布滿顆粒狀的硬疣；"
        "每條腕足的腹面排著兩列細密的管足。",
        "牠們以管足沿著礁石與蚵架爬行，用腕足扳開蚵殼與貽貝，吃裡頭的肉。"
        "牠的體壁帶著異常的變化力，平時柔軟，一受驚就在眨眼間硬得像石頭，緊貼在礁石上承受整道浪頭。"
        "漁灣鎮與南潮港的漁家在潮間帶搭起蚵架，硬腕海星成片爬上架子，一夜就能吃空一整排蚵殼；"
        "造船坊的下水滑道也常被牠們占住，木船滑下時刮傷船底。"
        "近身時，牠撐起腕足撲壓到對手身上，撲壓時全身體壁一併硬化，短時間內更加堅固。",
        ("southwest_coast",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；體壁瞬間硬化的成因不在設定中交代。",
        "（作者私有：作者解釋）低階群聚海星：體壁硬化屬於身體能力，不帶元素、不讓周圍環境變硬；戰鬥呈現為腕足撲壓與自身短暫防禦提升。連結漁家蚵架與造船坊的下水滑道。",
        "（作者私有：尚未證實的猜想）漁灣鎮的老漁婦說硬腕海星背上的硬疣越紅，當年的蚵就越肥，這種說法尚未證實。",
        "oyster_rack_creeper",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "oyster_rack_creeper",
        "stiff_arm_starfish",
        "爬架型",
        "普通版本，成片爬過潮池礁石與蚵架，扳開貝殼覓食。",
        "low",
        True,
        MonsterCombatProfile(
            hp=40, mp=0, sp=9, atk_phys=4, agility=3, defense=6, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("stiff_arm_press",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

```python
    MonsterVariant(
        "tide_pool_elder",
        "stiff_arm_starfish",
        "老礁型",
        "占住崖腳一座深潮池的老個體，腕足最粗、硬疣最厚，會撲向任何涉進潮池的身影。",
        "low",
        False,
        MonsterCombatProfile(
            hp=64, mp=0, sp=15, atk_phys=9, agility=3, defense=8, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("stiff_arm_press",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "stiff_arm_press",
        "硬腕撲壓",
        "撐起腕足撲壓單一敵方目標，造成物理傷害；撲壓時全身體壁硬化，短暫提高自身防禦。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"sp": 3},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        effects=["damage:none:physical", "self_buff_apply:body_wall_set"],
        category=SkillCategory.MARTIAL_ARTS,
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("stiff_arm_starfish",),
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
# 魔物資源技能（西南海岸第四波）：硬腕海星硬腕撲壓：每次已結算且具合法目標的施放都讓體壁硬化，防禦 +2 資料在 combat_modifiers.yaml 的 body_wall_set_defense 列（lamp_carapace_guard_defense 的 defense 先例）。
- key: body_wall_set
  duration: 20
  stacking: refresh
  polarity: buff
  modifiers: {}
```

- `world/rules/rulebook/combat_modifiers.yaml`, appended after the last monster resource-skill rule (the latest merged species' rule) and before the fatigue block:

```yaml
- id: body_wall_set_defense
  when: {buff_active: body_wall_set}
  then: {defense: 2}
```

- `world/rules/rulebook/status_display.yaml`, appended after the last monster resource-skill rows (the latest merged species' rows):

```yaml
- code: body_wall_set
  label: 體壁硬化
  severity: beneficial
- code: body_wall_set_defense
  label: 體壁硬化防禦提升
  severity: beneficial
```

- `world/skills/narration/data_martial.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "stiff_arm_press",
        action=(
            "{actor} 撐起五條腕足，整個身體撲壓上來。",
            "{actor} 腕足一收，硬化的身體猛力壓向對手。",
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

  `| 低階 | 硬腕海星 | 西南海岸的潮池、蚵架與造船坊滑道 | 體壁一受驚就硬得像石頭 | 爬架型、老礁型 |`

- New section at the end of `## 低階魔物`, immediately before `## 中階魔物` (after every low section an earlier programme change added), transcribed exactly:

````markdown
### 硬腕海星

```bestiary
species: stiff_arm_starfish
parent-species: stiff_arm_starfish
default-variant: oyster_rack_creeper
variants:
  - key: oyster_rack_creeper
    status: delivered
  - key: tide_pool_elder
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

**原型與棲地。**硬腕海星是五條腕足張開約一臂寬的海星類魔獸，成片棲息於西南海岸的潮池、蚵架與造船坊的下水滑道。

**外觀。**身體是五條粗短腕足連成的星形，背面橙紅，布滿顆粒狀的硬疣；每條腕足的腹面排著兩列細密的管足。

**生態與在地關係。**牠們以管足沿著礁石與蚵架爬行，用腕足扳開蚵殼與貽貝，吃裡頭的肉。漁灣鎮與南潮港的漁家在潮間帶搭起蚵架，硬腕海星成片爬上架子，一夜就能吃空一整排蚵殼；造船坊的下水滑道也常被牠們占住，木船滑下時刮傷船底。占住崖腳深潮池、腕足最粗的老個體稱為老礁型。

**戰鬥中的表現。**牠的體壁帶著異常的變化力，平時柔軟，一受驚就在眨眼間硬得像石頭，緊貼在礁石上承受整道浪頭。近身時，牠撐起腕足撲壓到對手身上，每次撲壓時全身體壁都一併硬化，短時間內更加堅固。

| 變體 | 核准方向 |
| --- | --- |
| 爬架型 | 普通版本，成片爬過潮池礁石與蚵架，扳開貝殼覓食 |
| 老礁型 | 占住崖腳一座深潮池的老個體，腕足最粗、硬疣最厚，會撲向任何涉進潮池的身影 |

**委託背景示例。**漁灣鎮東邊的蚵架這個月被硬腕海星爬滿，三排蚵殼被吃得只剩空殼。漁家委託公會把海星從蚵架上清走，趁大潮前讓蚵架重新掛上蚵苗。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `stiff_arm_starfish` | <implementation date> | read against the registry's published ecology field; the trouble stays local to a fishing village's oyster racks and a boatyard slipway, and the hardening acts on the sea star's own body wall | checked against the declared kit: the arm press is a single-target elementless physical strike that spends SP, and the brief defense rise mounts on the caster for every resolved attempt, matching the self policy with no hit dependency; the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D7. Tests

- `world/rules/tests/test_combat_modifiers.py::CombatModifierTests`: add `test_rule_body_wall_set_defense`, copying the four lines of `test_rule_rock_echo_stagger_agility_flat` with `RULES["body_wall_set_defense"]`. Copy those four lines exactly and assert no rule value of your own.

### D8. Developer review section

Append `## 硬腕海星` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Slow armoured creeper: defense in the low band's upper part, agility at its floor, hit points in its middle.
* The kit spends no MP, so the MP pool is zero; SP holds three casts of the press's SP cost (five on 老礁型).
* The guard (+2 defense for 20 s) equals the crab's shipped self guard.
* The stronger 老礁型 holds a deep cliff-foot pool at grade E with the low band's defense ceiling.
- `### Reuse of the self-guard strike representative`: the signature, the unchanged representative `burrow_maker`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later key sorts before a representative] → every Wave 1, Wave 2, Wave 3 and Wave 4 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_tide_lamp_crab_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.rules.tests.test_combat_modifiers.CombatModifierTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change stiff-arm-starfish-species` and `openspec validate stiff-arm-starfish-species --strict`.
