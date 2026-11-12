# Design

## Context

See proposal.md (Why). Facts at `cf4643a1` plus the planned Wave 2, Wave 3 and earlier Wave 4 species rows still open under `openspec/changes/*-species/`, which land first in the serial chain:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS` and `_VARIANT_DECLARATIONS` at import. Bands come from `MONSTER_TIER_REGISTRY`: low HP 25–70, attack 3–12, agility 3–12, defense 2–8, grades F–E; mid HP 110–230, attack 18–28, agility 10–24, defense 10–16, grades D–C; high HP 300–750, attack 26–40, agility 16–30, defense 18–32, grades B–A. `magic_power` must be 0 and MP/SP have no band. Display names are limited to 5 code points (`MONSTER_NAME_MAX_CODE_POINTS`).
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」 and `author_conjecture_zh` to contain 「尚未證實」, and it forbids registry strings that name a skill, behaviour or trait key.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by `(slot, effect family, audience, requires_hit_from)` and requires one committed representative per group, the group's sorted-minimum key. This kit's signature is `(("active", "damage", "enemies", None), ("active", "self_buff_apply", "self", None))`, the shipped self-guard strike group, whose representative `burrow_maker` is declared in `world.rules.tests.test_tide_lamp_crab_resource_skill`. Every new variant key sorts after `burrow_maker` (as every Wave 1, Wave 2 and Wave 3 key does), so the representative does not move and no smoke module, shard entry or seed entry is added. The self policy declares no hit dependency, following the crab and hare kits, so the mount lands on every resolved attempt including a miss. The self mount raises flat agility (`agility_flat`), the axis of the rat's shipped self rise; the signature reads only family, audience and hit dependency, so the species joins the crab and hare group without a new representative. The skill is elementless with an SP-only cost, so `spell_tier_for` returns `None` (the goblin and wolverine precedent).
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests` requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, a magic tier for elemental MP skills (MP 10–16 single, 14–20 area) and `None` otherwise. `validate_catalog` requires one narration row per active skill, and `world/rules/status_display.py` fails closed for a buff or modifier without a display row.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, modifier rule, intelligence and mode entry, plus the referenced bindings. `world/rules/tests/test_monster_ai_activation.py` compares that fingerprint with `docs/development/monster-ai-activation-evidence/activation.json`.
- Every kit here carries a damage occurrence, so the legacy decision body proposes it and no utility binding or intelligence value is needed (`owned-kit-decision-coverage` applies only to support-only kits).

## Candidate review (`docs/lore/monster-creation-guidelines.md`)

| Question | Answer |
| --- | --- |
| Familiar archetype | A cave cricket (camel cricket) of mines, cellars and storerooms. |
| Special way of life | Its hind legs carry abnormal spring, so one kick carries it a dozen paces through a dark tunnel and it lands already coiled for the next leap. |
| World relation | The mine shafts of the western hills and the cellars of the valley workshops and mills, where leather, flour and water-wheel belts are stored (western hills terrain flavour: mine shafts, workshops and mills along the rivers). |
| Ability limits | The spring is a body ability with no element; it makes no song that disturbs anyone. Every resolved kick brings a brief self agility rise. |
| Local conflict | A swarm in a mill cellar chews through the water-wheel belts and flour sacks, so the miller asks for the cellar to be cleared before the harvest grain arrives. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar), the Wave 1 species (spore-cap mushroom, moss-quill porcupine, hollow-tree bat, hush-wing owl, vine-net spider, moss-crown stag), the Wave 2 species (mountain frog, fire salamander, bearded vulture, giant moth, giant constrictor, capercaillie, beaver, mole, wolverine, griffin), the Wave 3 species (dung beetle, wild horse, grey heron, giant snapping turtle, mudskipper, herring gull, harbour seal) and the other six Wave 4 species (giant harvester ant of dry salt roads, sea star of rock pools and oyster racks, mantis shrimp of harbour shallows, marine iguana of sea cliffs, giant octopus of sea caves (kraken folklore), antlion larva of quarry sand). It is an animal, clearly distinct from every beastfolk subspecies (wolf, cat, bear, rabbit, cattle, tiger, fox).

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `western-hills-deep-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "shaft_leap_cricket",
        "坑道灶馬",
        "坑道灶馬是約手掌長的穴居蟋蟀類魔獸，成群棲息於西部丘陵的礦坑坑道、作坊地窖與磨坊的倉房。",
        "淺褐色的身體向上拱起，光滑的外殼帶著深色斑紋。"
        "觸角比身體長上好幾倍，後腿粗壯修長，大腿鼓起，小腿上排著細刺。",
        "牠們躲在陰暗潮濕的角落，夜裡成群爬出，啃食皮革、蠟燭的油脂、麵粉與穀屑，也會聚到礦工的燈旁。"
        "牠的後腿帶著異常的彈力，一蹬就能在漆黑的坑道裡躍出十幾步遠，落地後立刻又縮起後腿準備下一跳。"
        "西部丘陵的作坊與磨坊多半挖有地窖存放皮料與麵粉，坑道灶馬一旦在地窖裡繁衍開來，就會咬壞水車的皮帶與麵粉袋。"
        "近身時，牠以後腿猛力蹬踢對手，蹬踢時後腿順勢縮起蓄力，短時間內身形更加靈活。",
        ("western_hills_valleys",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；後腿異常彈力的成因不在設定中交代。",
        "（作者私有：作者解釋）低階群居灶馬：後腿彈力屬於身體能力，不帶元素、不發出鳴聲干擾；戰鬥呈現為蹬踢與自身短暫敏捷提升。描寫維持昆蟲體態。連結礦坑坑道、作坊地窖與磨坊水車的皮帶。",
        "（作者私有：尚未證實的猜想）灰岩城的礦工說坑道灶馬成群往坑口爬的日子，坑道深處就會滲水，這種說法尚未證實。",
        "cellar_leaper",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "cellar_leaper",
        "shaft_leap_cricket",
        "躍窖型",
        "普通版本，成群躲在地窖與坑道的陰暗角落，夜裡出來覓食。",
        "low",
        True,
        MonsterCombatProfile(
            hp=30, mp=0, sp=9, atk_phys=5, agility=11, defense=3, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("coiled_hind_kick",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

```python
    MonsterVariant(
        "old_shaft_leaper",
        "shaft_leap_cricket",
        "守坑型",
        "住在廢棄礦坑口、後腿最長的老個體，坑口一有燈光靠近，就帶著整群躍出。",
        "low",
        False,
        MonsterCombatProfile(
            hp=52, mp=0, sp=15, atk_phys=9, agility=12, defense=4, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("coiled_hind_kick",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "coiled_hind_kick",
        "蓄腿蹬踢",
        "以後腿猛力蹬踢單一敵方目標，造成物理傷害；蹬踢時後腿順勢縮起蓄力，短暫提高自身敏捷。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"sp": 3},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        effects=["damage:none:physical", "self_buff_apply:coiled_legs"],
        category=SkillCategory.MARTIAL_ARTS,
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("shaft_leap_cricket",),
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
# 魔物資源技能（西部丘陵第四波）：坑道灶馬蓄腿蹬踢：每次已結算且具合法目標的施放都讓後腿縮起蓄力，agility_flat +2 資料在 combat_modifiers.yaml 的 coiled_legs_agility_flat 列（wax_slip_agility_flat 的 agility_flat 先例）。
- key: coiled_legs
  duration: 15
  stacking: refresh
  polarity: buff
  modifiers: {}
```

- `world/rules/rulebook/combat_modifiers.yaml`, appended after the last monster resource-skill rule (the latest merged species' rule) and before the fatigue block:

```yaml
- id: coiled_legs_agility_flat
  when: {buff_active: coiled_legs}
  then: {agility_flat: 2}
```

- `world/rules/rulebook/status_display.yaml`, appended after the last monster resource-skill rows (the latest merged species' rows):

```yaml
- code: coiled_legs
  label: 蓄腿待躍
  severity: beneficial
- code: coiled_legs_agility_flat
  label: 蓄腿待躍敏捷提升
  severity: beneficial
```

- `world/skills/narration/data_martial.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "coiled_hind_kick",
        action=(
            "{actor} 從暗處一躍而出，後腿猛力蹬在對手身上。",
            "{actor} 蹬了一腳又彈開，後腿已經縮起準備下一跳。",
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

  `| 低階 | 坑道灶馬 | 西部丘陵的礦坑坑道、作坊地窖與磨坊倉房 | 後腿一蹬就能在黑暗中躍出十幾步遠 | 躍窖型、守坑型 |`

- New section at the end of `## 低階魔物`, immediately before `## 中階魔物` (after every low section an earlier programme change added), transcribed exactly:

````markdown
### 坑道灶馬

```bestiary
species: shaft_leap_cricket
parent-species: shaft_leap_cricket
default-variant: cellar_leaper
variants:
  - key: cellar_leaper
    status: delivered
  - key: old_shaft_leaper
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

**原型與棲地。**坑道灶馬是約手掌長的穴居蟋蟀類魔獸，成群棲息於西部丘陵的礦坑坑道、作坊地窖與磨坊的倉房。

**外觀。**淺褐色的身體向上拱起，光滑的外殼帶著深色斑紋。觸角比身體長上好幾倍，後腿粗壯修長，大腿鼓起，小腿上排著細刺。

**生態與在地關係。**牠們躲在陰暗潮濕的角落，夜裡成群爬出，啃食皮革、蠟燭的油脂、麵粉與穀屑，也會聚到礦工的燈旁。西部丘陵的作坊與磨坊多半挖有地窖存放皮料與麵粉，坑道灶馬一旦在地窖裡繁衍開來，就會咬壞水車的皮帶與麵粉袋。住在廢棄礦坑口、後腿最長的老個體稱為守坑型。

**戰鬥中的表現。**牠的後腿帶著異常的彈力，一蹬就能在漆黑的坑道裡躍出十幾步遠，落地後立刻又縮起後腿準備下一跳。近身時，牠以後腿猛力蹬踢對手，每次蹬踢時後腿都順勢縮起蓄力，短時間內身形更加靈活。

| 變體 | 核准方向 |
| --- | --- |
| 躍窖型 | 普通版本，成群躲在地窖與坑道的陰暗角落，夜裡出來覓食 |
| 守坑型 | 住在廢棄礦坑口、後腿最長的老個體，坑口一有燈光靠近，就帶著整群躍出 |

**委託背景示例。**蜜谷鎮河邊磨坊的地窖這個月爬滿坑道灶馬，水車的皮帶被咬斷兩次，麵粉袋也破了好幾個。磨坊主委託公會清空地窖，趕在秋收的麥子送來前讓磨坊照常運轉。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `shaft_leap_cricket` | <implementation date> | read against the registry's published ecology field; the trouble stays local to a mill cellar and its water-wheel belts, and the leap comes from the cricket's own hind legs | checked against the declared kit: the hind kick is a single-target elementless physical strike that spends SP, and the brief agility rise mounts on the caster for every resolved attempt, matching the self policy with no hit dependency; the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D7. Tests

- `world/rules/tests/test_combat_modifiers.py::CombatModifierTests`: add `test_rule_coiled_legs_agility_flat`, copying the four lines of `test_rule_rock_echo_stagger_agility_flat` with `RULES["coiled_legs_agility_flat"]`. Copy those four lines exactly and assert no rule value of your own.

### D8. Developer review section

Append `## 坑道灶馬` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Light cellar leaper: agility near the low band's ceiling, defense near its floor, hit points in its lower part.
* The kit spends no MP, so the MP pool is zero; SP holds three casts of the kick's SP cost (five on 守坑型).
* The lift (+2 agility for 15 s) is below the rat's shipped self agility rise (+3).
* The stronger 守坑型 leads a swarm at an abandoned shaft mouth at grade E.
- `### Reuse of the self-guard strike representative`: the signature, the unchanged representative `burrow_maker`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later key sorts before a representative] → every Wave 1, Wave 2, Wave 3 and Wave 4 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_tide_lamp_crab_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.rules.tests.test_combat_modifiers.CombatModifierTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change shaft-leap-cricket-species` and `openspec validate shaft-leap-cricket-species --strict`.
