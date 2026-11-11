# Design

## Context

See proposal.md (Why). Facts at `3756992d`:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS` and `_VARIANT_DECLARATIONS` at import. Bands come from `MONSTER_TIER_REGISTRY`: low HP 25–70, attack 3–12, agility 3–12, defense 2–8, grades F–E; mid HP 110–230, attack 18–28, agility 10–24, defense 10–16, grades D–C; high HP 300–750, attack 26–40, agility 16–30, defense 18–32, grades B–A. `magic_power` must be 0 and MP/SP have no band. Display names are limited to 5 code points (`MONSTER_NAME_MAX_CODE_POINTS`).
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」 and `author_conjecture_zh` to contain 「尚未證實」, and it forbids registry strings that name a skill, behaviour or trait key.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by `(slot, effect family, audience, requires_hit_from)` and requires one committed representative per group, the group's sorted-minimum key. This kit's signature is `(("active", "damage", "enemies", None), ("active", "self_buff_apply", "self", None))`, the shipped self-guard strike group, whose representative `burrow_maker` is declared in `world.rules.tests.test_tide_lamp_crab_resource_skill`. Every new variant key sorts after `burrow_maker`, so the representative does not move and no smoke module, shard entry or seed entry is added. The self policy declares no hit dependency, following the crab and hare kits, so the guard mounts on every resolved attempt including a miss.
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests` requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, a magic tier for elemental MP skills (MP 10–16 single, 14–20 area) and `None` otherwise. `validate_catalog` requires one narration row per active skill, and `world/rules/status_display.py` fails closed for a buff or modifier without a display row.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, modifier rule, intelligence and mode entry, plus the referenced bindings. `world/rules/tests/test_monster_ai_activation.py` compares that fingerprint with `docs/development/monster-ai-activation-evidence/activation.json`.
- Every kit here carries a damage occurrence, so the legacy decision body proposes it and no utility binding or intelligence value is needed (`owned-kit-decision-coverage` applies only to support-only kits).

## Candidate review (`docs/lore/monster-creation-guidelines.md`)

| Question | Answer |
| --- | --- |
| Familiar archetype | A porcupine. |
| Special way of life | Earth power hardens the moss soil at its quill roots so the quills stand; it lives by night-time bark gnawing and a strong appetite for salt. |
| World relation | Expedition camps on the deep-forest edge (北林堡, a frontier guild base) leave sweat-salted tack and salted food, so the animal raids camps. |
| Ability limits | The hardening lasts a moment and acts only on its own quill roots; it throws no quills and carries no poison (earth element: fixed defense, magic-system §3). |
| Local conflict | It gnaws through saddle straps, so a departing expedition asks the guild to drive the regular visitor away from camp. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar) and from the other five Wave 1 species.

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `north-deep-forest-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "moss_quill_porcupine",
        "苔棘豪豬",
        "苔棘豪豬是中型犬大小的豪豬類魔獸，生活於北部深林的林緣、倒木下的空洞與巨木根部的土穴。",
        "背上密生長棘，棘根長著一層濕綠苔蘚。"
        "圓鈍的頭部帶著短鬚，前爪粗短，啃過的樹皮上留著成排齒痕。",
        "牠通常獨居，夜間沿固定路線啃食樹皮、嫩根與蕈類，特別喜歡舔食帶有鹽分的東西。"
        "被汗水浸過的皮帶、鞍具與營地遺留的鹽漬食物，都會引牠靠近。"
        "遇到威脅時，牠以土屬性力量讓棘根周圍的苔土緊縮硬化，整排長棘隨之挺立，再轉身以背部倒撞過去；"
        "硬化維持片刻，作用在牠自己的棘根上。"
        "探險隊在林緣紮營時會把鞍具吊高，免得隔天早上發現皮帶被啃斷。",
        ("north_deep_forest",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；棘根苔層硬化的成因不在設定中交代。",
        "（作者私有：作者解釋）低階獨居豪豬：土屬性力量只硬化自身棘根周圍的苔土，不射出棘刺、不造成中毒或持續傷害；戰鬥呈現為背部倒撞與自身短暫防禦提升。舔鹽習性連結林緣營地的鞍具損耗。",
        "（作者私有：尚未證實的猜想）北林堡的獵人說苔棘豪豬會記住給過鹽的人，這種說法尚未證實。",
        "quill_forager",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "quill_forager",
        "moss_quill_porcupine",
        "啃皮型",
        "普通版本，夜間沿固定路線啃食樹皮與嫩根。",
        "low",
        True,
        MonsterCombatProfile(
            hp=44, mp=20, sp=9, atk_phys=6, agility=5, defense=6, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("quill_brace_ram",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

```python
    MonsterVariant(
        "den_sentry",
        "moss_quill_porcupine",
        "守洞型",
        "帶著幼獸占據倒木空洞的個體，棘根苔層更厚，守在洞口正面迎向來者。",
        "low",
        False,
        MonsterCombatProfile(
            hp=66, mp=30, sp=15, atk_phys=11, agility=5, defense=8, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("quill_brace_ram",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "quill_brace_ram",
        "固棘倒撞",
        "以土屬性力量硬化棘根後轉身以背倒撞單一敵方目標，造成物理傷害；出招時短暫提高自身防禦。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 3},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="earth",
        effects=["damage:earth:physical", "self_buff_apply:quill_brace"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="earth",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("moss_quill_porcupine",),
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

- `world/rules/rulebook/buffs.yaml`, appended after the last monster resource-skill buff (`reservoir_film`, or the previous Wave 1 species' buff), with a zh-TW comment line before it:

```yaml
# 魔物資源技能（北部深林第一波）：苔棘豪豬固棘倒撞：每次已結算且具合法目標的施放都硬化棘根，防禦 +2 資料在 combat_modifiers.yaml 的 quill_brace_defense 列（lamp_carapace_guard_defense 的 defense 先例）。
- key: quill_brace
  duration: 20
  stacking: refresh
  polarity: buff
  modifiers: {}
```

- `world/rules/rulebook/combat_modifiers.yaml`, appended after the last monster resource-skill rule (`reservoir_film_defense`, or the previous Wave 1 rule) and before the fatigue block:

```yaml
- id: quill_brace_defense
  when: {buff_active: quill_brace}
  then: {defense: 2}
```

- `world/rules/rulebook/status_display.yaml`, appended after `reservoir_film_defense` (or the previous Wave 1 rows):

```yaml
- code: quill_brace
  label: 固棘挺立
  severity: beneficial
- code: quill_brace_defense
  label: 固棘挺立防禦提升
  severity: beneficial
```

- `world/skills/narration/data_earth.py`, appended after the last monster row in that file:

```python
    NarrationRow(
        "quill_brace_ram",
        action=(
            "{actor} 背上長棘一齊挺立，轉身倒撞過去。",
            "{actor} 收緊棘根的苔土，以滿背硬棘撞向對手。",
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

  `| 低階 | 苔棘豪豬 | 北部深林的林緣、倒木空洞與巨木根部土穴 | 以土屬性力量硬化棘根苔土，使長棘挺立 | 啃皮型、守洞型 |`

- New section at the end of `## 低階魔物`, immediately before `## 中階魔物` (after any Wave 1 low section already added), transcribed exactly:

````markdown
### 苔棘豪豬

```bestiary
species: moss_quill_porcupine
parent-species: moss_quill_porcupine
default-variant: quill_forager
variants:
  - key: quill_forager
    status: delivered
  - key: den_sentry
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

**原型與棲地。**苔棘豪豬是中型犬大小的豪豬類魔獸，通常獨居，生活於北部深林的林緣、倒木下的空洞與巨木根部的土穴。

**外觀。**背上密生長棘，棘根長著一層濕綠苔蘚。圓鈍的頭部帶著短鬚，前爪粗短，啃過的樹皮上留著成排齒痕。

**生態與在地關係。**牠夜間沿固定路線啃食樹皮、嫩根與蕈類，特別喜歡舔食帶有鹽分的東西。被汗水浸過的皮帶、鞍具與營地遺留的鹽漬食物，都會引牠靠近。探險隊在林緣紮營時會把鞍具吊高，免得隔天早上發現皮帶被啃斷。帶著幼獸占據倒木空洞的個體稱為守洞型。

**戰鬥中的表現。**遇到威脅時，牠以土屬性力量讓棘根周圍的苔土緊縮硬化，整排長棘隨之挺立，再轉身以背部倒撞對手。硬化維持片刻，作用在牠自己的棘根上，讓牠在倒撞之後更耐得住反擊。

| 變體 | 核准方向 |
| --- | --- |
| 啃皮型 | 普通版本，夜間沿固定路線啃食樹皮與嫩根 |
| 守洞型 | 帶著幼獸占據倒木空洞的個體，棘根苔層更厚，守在洞口正面迎向來者 |

**委託背景示例。**北林堡外的探險隊營地接連幾晚被苔棘豪豬光顧，三副鞍具的皮帶都被啃斷。隊長委託公會把常來的那隻引離營地，好讓隊伍按時出發。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `moss_quill_porcupine` | <implementation date> | read against the registry's published ecology field; the trouble stays local to forest-edge camps and their salt-soaked tack, and the hardening acts on the creature's own quill roots | checked against the declared kit: the back ram is a single-target earth-element physical strike, and the brief defense rise mounts on the caster for every resolved attempt, matching the self policy with no hit dependency; the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. The reviewer may reword a cell after actually reading the section, but must keep all six cells.

### D7. Tests

- `world/rules/tests/test_combat_modifiers.py::CombatModifierTests`: add `test_rule_quill_brace_defense`, copying the four lines of `test_rule_rock_echo_stagger_agility_flat` with `RULES["quill_brace_defense"]`.

### D8. Developer review section

Append `## 苔棘豪豬` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Defensive forager: defense equal to the crab's, the highest shipped low-tier ordinary defense.
* A plodding walker: agility below the hare's and the rat's.
* MP holds two casts of the ram's MP cost; SP holds three casts of its SP cost.
* The guard (+2 defense for 20 s) matches the crab's, the smallest shipped self-guard.
* The stronger 守洞型 holds a den, so it carries the larger pool and the low band's defense ceiling at grade E.
- `### Reuse of the self-guard strike representative`: the signature, the unchanged representative `burrow_maker`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later Wave 1 key sorts before a representative] → every Wave 1 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_tide_lamp_crab_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.rules.tests.test_combat_modifiers.CombatModifierTests`, `world.skills.tests.test_narration_catalog`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change moss-quill-porcupine-species` and `openspec validate moss-quill-porcupine-species --strict`.
