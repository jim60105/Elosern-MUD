# Design

## Context

See proposal.md (Why). Facts at `cf4643a1` plus the planned Wave 2, Wave 3 and earlier Wave 4 species rows still open under `openspec/changes/*-species/`, which land first in the serial chain:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS` and `_VARIANT_DECLARATIONS` at import. Bands come from `MONSTER_TIER_REGISTRY`: low HP 25–70, attack 3–12, agility 3–12, defense 2–8, grades F–E; mid HP 110–230, attack 18–28, agility 10–24, defense 10–16, grades D–C; high HP 300–750, attack 26–40, agility 16–30, defense 18–32, grades B–A. `magic_power` must be 0 and MP/SP have no band. Display names are limited to 5 code points (`MONSTER_NAME_MAX_CODE_POINTS`).
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」 and `author_conjecture_zh` to contain 「尚未證實」, and it forbids registry strings that name a skill, behaviour or trait key.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by `(slot, effect family, audience, requires_hit_from)` and requires one committed representative per group, the group's sorted-minimum key. This kit's signature is `(("active", "damage", "enemies", None), ("active", "buff_apply", "enemies", 0))`, the shipped enemy hit-rider group, whose representative `cliff_stepper` is declared in `world.rules.tests.test_sway_whistle_sparrow_resource_skill`. Every new variant key sorts after `cliff_stepper` (as every Wave 1, Wave 2 and Wave 3 key does), so the representative does not move and no smoke module, shard entry or seed entry is added. `EnemyRiderGroupMemberTests` in that module derives the group's members from the shipped declarations, so both new variants are exercised on their own rider axis without a test edit. The rider lowers defense (`defense`), the axis of the wolverine's rider. The skill is elementless with an SP-only cost, so `spell_tier_for` returns `None` (the goblin and wolverine precedent).
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests` requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, a magic tier for elemental MP skills (MP 10–16 single, 14–20 area) and `None` otherwise. `validate_catalog` requires one narration row per active skill, and `world/rules/status_display.py` fails closed for a buff or modifier without a display row.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, modifier rule, intelligence and mode entry, plus the referenced bindings. `world/rules/tests/test_monster_ai_activation.py` compares that fingerprint with `docs/development/monster-ai-activation-evidence/activation.json`.
- Every kit here carries a damage occurrence, so the legacy decision body proposes it and no utility binding or intelligence value is needed (`owned-kit-decision-coverage` applies only to support-only kits).

## Candidate review (`docs/lore/monster-creation-guidelines.md`)

| Question | Answer |
| --- | --- |
| Familiar archetype | A mantis shrimp of harbour shallows and seawalls. |
| Special way of life | Its folded club limbs snap out with abnormal force, cracking crab shells and thick oyster shells in one blow, so it hunts from a burrow mouth. |
| World relation | The small craft harbours of the south-west shore, whose quays stack glazed jars and glass floats for the merchant ships (southwest coast terrain flavour: small harbours, merchant ships carrying fine craft goods). |
| Ability limits | The force is a body ability with no element; it raises no shock wave and no lightning. A landed strike cracks the surface of the target's guard, a brief defense rider; a miss leaves the guard as it was. |
| Local conflict | One old shrimp dens under a quay stair and cracks a merchant's jars night after night, so the merchant asks for it to be driven out before the next ship docks. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar), the Wave 1 species (spore-cap mushroom, moss-quill porcupine, hollow-tree bat, hush-wing owl, vine-net spider, moss-crown stag), the Wave 2 species (mountain frog, fire salamander, bearded vulture, giant moth, giant constrictor, capercaillie, beaver, mole, wolverine, griffin), the Wave 3 species (dung beetle, wild horse, grey heron, giant snapping turtle, mudskipper, herring gull, harbour seal) and the other six Wave 4 species (giant harvester ant of dry salt roads, sea star of rock pools and oyster racks, marine iguana of sea cliffs, giant octopus of sea caves (kraken folklore), cave cricket of mines and cellars, antlion larva of quarry sand). It is an animal, clearly distinct from every beastfolk subspecies (wolf, cat, bear, rabbit, cattle, tiger, fox).

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `southwest-coast-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "shell_crack_shrimp",
        "碎殼蝦",
        "碎殼蝦是體長約有半個人高的螳螂蝦類魔獸，獨自穴居於西南海岸港灣的淺灘、礁縫與石砌海堤。",
        "甲殼泛著綠、紅、藍交錯的光澤，一對長在短柄上的眼睛各自轉動。"
        "胸前收著一對錘狀的捕肢，平時折疊貼在身下，末端圓鈍堅硬，形如兩柄小錘。",
        "牠在淺灘的沙底與海堤的石縫裡挖出洞穴，守在洞口等待路過的蟹與貝。"
        "牠的錘狀捕肢帶著異常的爆發力，彈出時快得看不清，一擊就能敲碎蟹殼與厚實的蚵殼。"
        "西南海岸的小港靠著精工器物的買賣維生，碼頭上常堆著待裝船的上釉陶罐與玻璃浮球；"
        "碎殼蝦把洞挖在碼頭石階下，夜裡出洞時會把擋路的陶罐敲出裂痕。"
        "近身時，牠彈出錘狀捕肢重擊對手，擊中時震裂對手的護具表面，短時間內防禦下降。",
        ("southwest_coast",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；錘狀捕肢爆發力的成因不在設定中交代。",
        "（作者私有：作者解釋）中階獨居螳螂蝦：捕肢的爆發力屬於身體能力，不帶元素、不發出衝擊波或雷光；戰鬥呈現為重擊與命中後短暫防禦下降。描寫維持甲殼類體態。連結港口碼頭待裝船的陶罐與玻璃浮球。",
        "（作者私有：尚未證實的猜想）南潮港的陶器商說聽得見碎殼蝦在石階下敲殼的夜晚，隔天的海面必定平靜，這種說法尚未證實。",
        "reef_burrow_striker",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "reef_burrow_striker",
        "shell_crack_shrimp",
        "穴擊型",
        "普通版本，守在淺灘與礁縫的洞口伏擊路過的蟹貝。",
        "mid",
        True,
        MonsterCombatProfile(
            hp=125, mp=0, sp=24, atk_phys=24, agility=18, defense=11, magic_power=0
        ),
        "D",
        True,
        active_skill_keys=("club_limb_strike",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
```

```python
    MonsterVariant(
        "seawall_den_holder",
        "shell_crack_shrimp",
        "深穴型",
        "在港口石砌海堤裡挖出深穴的大型老個體，捕肢最粗，會擊向任何在洞口前停步的身影。",
        "mid",
        False,
        MonsterCombatProfile(
            hp=175, mp=0, sp=36, atk_phys=28, agility=18, defense=13, magic_power=0
        ),
        "C",
        True,
        active_skill_keys=("club_limb_strike",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "club_limb_strike",
        "錘肢彈擊",
        "彈出錘狀捕肢重擊單一敵方目標，造成物理傷害；命中後震裂對手的護具表面，短暫降低其防禦。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"sp": 6},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        effects=["damage:none:physical", "buff_apply:guard_crack"],
        category=SkillCategory.MARTIAL_ARTS,
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("shell_crack_shrimp",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=1.0, audience=EffectAudience.ENEMIES),
            EffectPolicy(coefficient=1.0, audience=EffectAudience.ENEMIES, requires_hit_from=0),
        ),
    ),
```

Also append one sentence to that module's docstring describing this kit's composition, in the style of the existing sentences.

### D4. Rulebook and narration

- `world/rules/rulebook/buffs.yaml`, appended after the last monster resource-skill buff (the buff of the latest species already merged in the serial chain), with a zh-TW comment line before it:

```yaml
# 魔物資源技能（西南海岸第四波）：碎殼蝦錘肢彈擊：命中後震裂護具表面的 mount，defense −2 資料在 combat_modifiers.yaml 的 guard_crack_defense 列（jaw_wrench_defense 的 defense 先例）。
- key: guard_crack
  duration: 15
  stacking: refresh
  polarity: debuff
  modifiers: {}
```

- `world/rules/rulebook/combat_modifiers.yaml`, appended after the last monster resource-skill rule (the latest merged species' rule) and before the fatigue block:

```yaml
- id: guard_crack_defense
  when: {buff_active: guard_crack}
  then: {defense: -2}
```

- `world/rules/rulebook/status_display.yaml`, appended after the last monster resource-skill rows (the latest merged species' rows):

```yaml
- code: guard_crack
  label: 護具震裂
  severity: harmful
- code: guard_crack_defense
  label: 護具震裂防禦下降
  severity: harmful
```

- `world/skills/narration/data_martial.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "club_limb_strike",
        action=(
            "{actor} 錘狀捕肢猛然彈出，正中對手胸前。",
            "{actor} 一記快得看不清的彈擊，對方護具上多了一道裂痕。",
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

- Overview row, inserted in the `## 收錄總覽` table after the last `| 中階 |` or `| 中階／高階 |` row:

  `| 中階 | 碎殼蝦 | 西南海岸港灣的淺灘、礁縫與石砌海堤 | 錘狀捕肢一擊就能敲碎厚殼 | 穴擊型、深穴型 |`

- New section at the end of `## 中階魔物`, immediately before `## 高階魔物` (after every mid section an earlier programme change added), transcribed exactly:

````markdown
### 碎殼蝦

```bestiary
species: shell_crack_shrimp
parent-species: shell_crack_shrimp
default-variant: reef_burrow_striker
variants:
  - key: reef_burrow_striker
    status: delivered
  - key: seawall_den_holder
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

**原型與棲地。**碎殼蝦是體長約有半個人高的螳螂蝦類魔獸，獨自穴居於西南海岸港灣的淺灘、礁縫與石砌海堤。

**外觀。**甲殼泛著綠、紅、藍交錯的光澤，一對長在短柄上的眼睛各自轉動。胸前收著一對錘狀的捕肢，平時折疊貼在身下，末端圓鈍堅硬，形如兩柄小錘。

**生態與在地關係。**牠在淺灘的沙底與海堤的石縫裡挖出洞穴，守在洞口等待路過的蟹與貝。西南海岸的小港靠著精工器物的買賣維生，碼頭上常堆著待裝船的上釉陶罐與玻璃浮球；碎殼蝦把洞挖在碼頭石階下，夜裡出洞時會把擋路的陶罐敲出裂痕。在石砌海堤裡挖出深穴、捕肢最粗的大型老個體稱為深穴型。

**戰鬥中的表現。**牠的錘狀捕肢帶著異常的爆發力，彈出時快得看不清，一擊就能敲碎蟹殼與厚實的蚵殼。近身時，牠彈出捕肢重擊對手，擊中時震裂對手的護具表面，短時間內防禦下降。

| 變體 | 核准方向 |
| --- | --- |
| 穴擊型 | 普通版本，守在淺灘與礁縫的洞口伏擊路過的蟹貝 |
| 深穴型 | 在港口石砌海堤裡挖出深穴的大型老個體，捕肢最粗，會擊向任何在洞口前停步的身影 |

**委託背景示例。**南潮港西碼頭的石階下住進一隻深穴型碎殼蝦，一個月裡敲裂了十幾只待運的上釉陶罐。陶器商委託公會趕在下一艘商船靠港前，把牠從石階下的洞穴趕走。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `shell_crack_shrimp` | <implementation date> | read against the registry's published ecology field; the trouble stays local to a harbour quay and its stacked glazed jars, and the striking force sits in the shrimp's own club limbs | checked against the declared kit: the club strike is a single-target elementless physical strike that spends SP, and the section states that the brief cracked guard follows a strike that lands, matching the declared hit dependency; the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D7. Tests

- `world/rules/tests/test_combat_modifiers.py::CombatModifierTests`: add `test_rule_guard_crack_defense`, copying the four lines of `test_rule_rock_echo_stagger_agility_flat` with `RULES["guard_crack_defense"]`. Copy those four lines exactly and assert no rule value of your own.

### D8. Developer review section

Append `## 碎殼蝦` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Burrow ambusher: attack in the mid band's upper part, agility above the band's middle, defense and hit points in its lower part.
* The kit spends no MP, so the MP pool is zero; SP holds four casts of the strike's SP cost (six on 深穴型).
* The rider (−2 defense for 15 s) equals the wolverine's −2 defense rider.
* The stronger 深穴型 holds a seawall den at grade C with the mid band's attack ceiling.
- `### Reuse of the enemy hit-rider representative`: the signature, the unchanged representative `cliff_stepper`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later key sorts before a representative] → every Wave 1, Wave 2, Wave 3 and Wave 4 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_sway_whistle_sparrow_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.rules.tests.test_combat_modifiers.CombatModifierTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change shell-crack-shrimp-species` and `openspec validate shell-crack-shrimp-species --strict`.
