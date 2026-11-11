# Design

## Context

See proposal.md (Why). Facts at `d1ac4b84` plus the planned Wave 1 species rows (`openspec/changes/*-species/`), which land first:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS` and `_VARIANT_DECLARATIONS` at import. Bands come from `MONSTER_TIER_REGISTRY`: low HP 25–70, attack 3–12, agility 3–12, defense 2–8, grades F–E; mid HP 110–230, attack 18–28, agility 10–24, defense 10–16, grades D–C; high HP 300–750, attack 26–40, agility 16–30, defense 18–32, grades B–A. `magic_power` must be 0 and MP/SP have no band. Display names are limited to 5 code points (`MONSTER_NAME_MAX_CODE_POINTS`).
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」 and `author_conjecture_zh` to contain 「尚未證實」, and it forbids registry strings that name a skill, behaviour or trait key.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by `(slot, effect family, audience, requires_hit_from)` and requires one committed representative per group, the group's sorted-minimum key. This kit's signature is `(("active", "damage", "enemies", None), ("active", "self_buff_apply", "self", None))`, the shipped self-guard strike group, whose representative `burrow_maker` is declared in `world.rules.tests.test_tide_lamp_crab_resource_skill`. Every new variant key sorts after `burrow_maker` (and every Wave 1 key does too), so the representative does not move and no smoke module, shard entry or seed entry is added. The self mount raises physical attack rather than defense or agility; `world/rules/combat_modifiers.py::attack_with_bundle` adds a flat `atk_phys` bundle value to the physical attack of any entity. The signature reads only family, audience and hit dependency, so the salamander joins the crab and hare group without a new representative.
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests` requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, a magic tier for elemental MP skills (MP 10–16 single, 14–20 area) and `None` otherwise. `validate_catalog` requires one narration row per active skill, and `world/rules/status_display.py` fails closed for a buff or modifier without a display row.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, modifier rule, intelligence and mode entry, plus the referenced bindings. `world/rules/tests/test_monster_ai_activation.py` compares that fingerprint with `docs/development/monster-ai-activation-evidence/activation.json`.
- Every kit here carries a damage occurrence, so the legacy decision body proposes it and no utility binding or intelligence value is needed (`owned-kit-decision-coverage` applies only to support-only kits).

## Candidate review (`docs/lore/monster-creation-guidelines.md`)

| Question | Answer |
| --- | --- |
| Familiar archetype | A fire salamander, the folklore amphibian tied to fire. |
| Special way of life | Faint fire power warms its own skin, so it hunts at cold dawn when other small animals are sluggish and basks between hunts; the heat costs it effort. |
| World relation | Stone shelters with hearths on the mountain paths, used by 銀嶺鎮 prospectors and path-crossing travellers (central mountains terrain flavour: cold wind, sparse paths). |
| Ability limits | The heat stays on its own skin. It ignites nothing, breathes no fire and leaves no burning state; the strike is a bite with a brief self attack rise (fire element: burning oneself for a burst, magic-system §3). |
| Local conflict | Several salamanders settle into a shelter's hearth and bite people fetching firewood, so the commission is to move them out before winter prospecting. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar), the Wave 1 species (spore-cap mushroom, moss-quill porcupine, hollow-tree bat, hush-wing owl, vine-net spider, moss-crown stag) and the other nine Wave 2 species. It is an animal, clearly distinct from every beastfolk subspecies (wolf, cat, bear, rabbit, cattle, tiger, fox).

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `central-mountains-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "warm_rock_salamander",
        "暖岩蠑螈",
        "暖岩蠑螈是約前臂長的蠑螈類魔獸，獨自棲息於中央山脈向陽的岩縫與碎石坡。",
        "黑褐色濕潤皮膚上散布著橙紅斑點，體溫升高時斑點會隱約透出火光。"
        "頭部扁平，四肢短小，尾巴約與身體等長。",
        "山上冷霧終日不散，牠卻能以微弱火屬性力量讓自己的皮膚發熱，在其他小動物凍得遲緩的清晨照樣爬出岩縫捕食甲蟲與小蛇。"
        "這股熱力停留在牠自己的皮膚上，發熱越久越耗體力，所以牠大半時間趴在向陽的岩面上曬太陽。"
        "山徑旁的避難石屋留有火塘，夜裡餘溫不散，暖岩蠑螈常鑽進火塘邊的石縫過夜；"
        "旅人伸手撿柴時被咬，是石屋裡常聽到的小意外。"
        "近身時，牠咬住對手，同時讓斑點驟然發亮，短時間內咬勁更強。",
        ("central_mountains",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；皮膚火屬性力量的成因不在設定中交代。",
        "（作者私有：作者解釋）低階獨居蠑螈：火屬性只讓自身皮膚發熱，不點燃周圍物品、不噴火、不造成燒傷狀態；戰鬥呈現為咬擊與自身短暫攻擊提升（燃身換爆發）。連結山徑避難石屋的火塘。",
        "（作者私有：尚未證實的猜想）銀嶺鎮的礦工相信石屋火塘裡有暖岩蠑螈過夜，代表那座石屋整晚都會溫暖，這種說法尚未證實。",
        "ledge_basker",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "ledge_basker",
        "warm_rock_salamander",
        "曬岩型",
        "普通版本，白天趴在向陽岩面上曬太陽，清晨出來捕食。",
        "low",
        True,
        MonsterCombatProfile(
            hp=36, mp=20, sp=9, atk_phys=6, agility=5, defense=3, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("ember_skin_bite",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

```python
    MonsterVariant(
        "vent_crack_dweller",
        "warm_rock_salamander",
        "熱縫型",
        "長年住在山腰地熱裂縫旁的大型個體，皮膚斑點終日微亮，咬勁更強。",
        "low",
        False,
        MonsterCombatProfile(
            hp=60, mp=30, sp=15, atk_phys=10, agility=6, defense=5, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("ember_skin_bite",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "ember_skin_bite",
        "燃斑咬擊",
        "以火屬性力量讓皮膚斑點驟然發熱後咬向單一敵方目標，造成物理傷害；出招時短暫提高自身攻擊。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 3},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="fire",
        effects=["damage:fire:physical", "self_buff_apply:ember_skin"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="fire",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("warm_rock_salamander",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=0.9, audience=EffectAudience.ENEMIES),
            EffectPolicy(coefficient=1.0, audience=EffectAudience.SELF),
        ),
    ),
```

Also append one sentence to that module's docstring describing this kit's composition, in the style of the existing sentences.

### D4. Rulebook and narration

- `world/rules/rulebook/buffs.yaml`, appended after the last monster resource-skill buff (the buff of the latest species already merged in the serial chain), with a zh-TW comment line before it:

```yaml
# 魔物資源技能（中央山脈第二波）：暖岩蠑螈燃斑咬擊：每次已結算且具合法目標的施放都讓皮膚發熱，攻擊 +2 資料在 combat_modifiers.yaml 的 ember_skin_atk_phys 列（retainer_martial_training_atk_phys_bonus 的 atk_phys 先例）。
- key: ember_skin
  duration: 15
  stacking: refresh
  polarity: buff
  modifiers: {}
```

- `world/rules/rulebook/combat_modifiers.yaml`, appended after the last monster resource-skill rule (the latest merged species' rule) and before the fatigue block:

```yaml
- id: ember_skin_atk_phys
  when: {buff_active: ember_skin}
  then: {atk_phys: 2}
```

- `world/rules/rulebook/status_display.yaml`, appended after the last monster resource-skill rows (the latest merged species' rows):

```yaml
- code: ember_skin
  label: 燃斑發熱
  severity: beneficial
- code: ember_skin_atk_phys
  label: 燃斑發熱攻擊提升
  severity: beneficial
```

- `world/skills/narration/data_fire.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "ember_skin_bite",
        action=(
            "{actor} 背上斑點一亮，張口咬住對手。",
            "{actor} 從石縫竄出，帶著熱氣的嘴咬了上去。",
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

  `| 低階 | 暖岩蠑螈 | 中央山脈向陽的岩縫與碎石坡 | 以火屬性力量讓自身皮膚發熱 | 曬岩型、熱縫型 |`

- New section at the end of `## 低階魔物`, immediately before `## 中階魔物` (after every low section an earlier programme change added), transcribed exactly:

````markdown
### 暖岩蠑螈

```bestiary
species: warm_rock_salamander
parent-species: warm_rock_salamander
default-variant: ledge_basker
variants:
  - key: ledge_basker
    status: delivered
  - key: vent_crack_dweller
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

**原型與棲地。**暖岩蠑螈是約前臂長的蠑螈類魔獸，獨自棲息於中央山脈向陽的岩縫與碎石坡。

**外觀。**黑褐色濕潤皮膚上散布著橙紅斑點，體溫升高時斑點會隱約透出火光。頭部扁平，四肢短小，尾巴約與身體等長。

**生態與在地關係。**山上冷霧終日不散，牠在其他小動物凍得遲緩的清晨照樣爬出岩縫捕食甲蟲與小蛇，其餘時間大多趴在向陽的岩面上曬太陽。山徑旁的避難石屋留有火塘，夜裡餘溫不散，牠常鑽進火塘邊的石縫過夜；旅人伸手撿柴時被咬，是石屋裡常聽到的小意外。長年住在山腰地熱裂縫旁、斑點終日微亮的大型個體稱為熱縫型。

**戰鬥中的表現。**牠以微弱火屬性力量讓自己的皮膚發熱，這股熱力停留在牠自己的皮膚上，發熱越久越耗體力。近身時，牠咬住對手，同時讓斑點驟然發亮，短時間內咬勁更強。

| 變體 | 核准方向 |
| --- | --- |
| 曬岩型 | 普通版本，白天趴在向陽岩面上曬太陽，清晨出來捕食 |
| 熱縫型 | 長年住在山腰地熱裂縫旁的大型個體，皮膚斑點終日微亮，咬勁更強 |

**委託背景示例。**銀嶺鎮上山的探礦隊回報，山腰第二座避難石屋的火塘邊住進好幾隻暖岩蠑螈，隊員撿柴生火時接連被咬。石屋管理人委託公會把牠們請出火塘，讓入冬前的探礦隊能安心過夜。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `warm_rock_salamander` | <implementation date> | read against the registry's published ecology field; the trouble stays local to mountain-path stone shelters and their hearths, and the heat stays on the salamander's own skin | checked against the declared kit: the bite is a single-target fire-element physical strike, and the brief attack rise mounts on the caster for every resolved attempt, matching the self policy with no hit dependency; the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D7. Tests

- `world/rules/tests/test_combat_modifiers.py::CombatModifierTests`: add `test_rule_ember_skin_atk_phys`, copying the four lines of `test_rule_rock_echo_stagger_agility_flat` with `RULES["ember_skin_atk_phys"]`. Copy those four lines exactly and assert no rule value of your own.

### D8. Developer review section

Append `## 暖岩蠑螈` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Small solitary crawler: agility in the low band's lower half, defense equal to the hare's ordinary variant.
* MP holds two casts of the bite's MP cost; SP holds three casts of its SP cost.
* The flare (+2 physical attack for 15 s) is a low-tier self rise, below the shipped `atk_phys` precedents (+5).
* The stronger 熱縫型 lives by a warm vent, so it carries a larger pool and attack at grade E.
- `### Reuse of the self-guard strike representative`: the signature, the unchanged representative `burrow_maker`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later key sorts before a representative] → every Wave 1 and Wave 2 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_tide_lamp_crab_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.rules.tests.test_combat_modifiers.CombatModifierTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change warm-rock-salamander-species` and `openspec validate warm-rock-salamander-species --strict`.
