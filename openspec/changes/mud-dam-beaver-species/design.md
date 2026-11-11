# Design

## Context

See proposal.md (Why). Facts at `d1ac4b84` plus the planned Wave 1 species rows (`openspec/changes/*-species/`), which land first:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS` and `_VARIANT_DECLARATIONS` at import. Bands come from `MONSTER_TIER_REGISTRY`: low HP 25–70, attack 3–12, agility 3–12, defense 2–8, grades F–E; mid HP 110–230, attack 18–28, agility 10–24, defense 10–16, grades D–C; high HP 300–750, attack 26–40, agility 16–30, defense 18–32, grades B–A. `magic_power` must be 0 and MP/SP have no band. Display names are limited to 5 code points (`MONSTER_NAME_MAX_CODE_POINTS`).
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」 and `author_conjecture_zh` to contain 「尚未證實」, and it forbids registry strings that name a skill, behaviour or trait key.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by `(slot, effect family, audience, requires_hit_from)` and requires one committed representative per group, the group's sorted-minimum key. This kit's signature is `(("active", "damage", "enemies", None), ("active", "self_buff_apply", "self", None))`, the shipped self-guard strike group, whose representative `burrow_maker` is declared in `world.rules.tests.test_tide_lamp_crab_resource_skill`. Every new variant key sorts after `burrow_maker` (and every Wave 1 key does too), so the representative does not move and no smoke module, shard entry or seed entry is added. The self policy declares no hit dependency, following the crab and hare kits, so the mount lands on every resolved attempt including a miss.
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests` requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, a magic tier for elemental MP skills (MP 10–16 single, 14–20 area) and `None` otherwise. `validate_catalog` requires one narration row per active skill, and `world/rules/status_display.py` fails closed for a buff or modifier without a display row.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, modifier rule, intelligence and mode entry, plus the referenced bindings. `world/rules/tests/test_monster_ai_activation.py` compares that fingerprint with `docs/development/monster-ai-activation-evidence/activation.json`.
- Every kit here carries a damage occurrence, so the legacy decision body proposes it and no utility binding or intelligence value is needed (`owned-kit-decision-coverage` applies only to support-only kits).

## Candidate review (`docs/lore/monster-creation-guidelines.md`)

| Question | Answer |
| --- | --- |
| Familiar archetype | A beaver. |
| Special way of life | Faint earth power firms the stream mud it plasters on its dam and on its own pelt, so its dams survive the spring melt flood and its pelt hardens when it fights. |
| World relation | Valhalla's ford settlements (松濤渡, 鹿鳴渡, 東渡營, 西渡營) depend on steady stream levels and wooden ferry posts. |
| Ability limits | The firming acts only on mud on its dam and pelt; it diverts no river and controls no water (earth element: fixed defense, magic-system §3). |
| Local conflict | A new dam drops a ford's water level and grounds the ferry, so the ferrymen ask for the dam to be opened and the family moved upstream. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar), the Wave 1 species (spore-cap mushroom, moss-quill porcupine, hollow-tree bat, hush-wing owl, vine-net spider, moss-crown stag) and the other nine Wave 2 species. It is an animal, clearly distinct from every beastfolk subspecies (wolf, cat, bear, rabbit, cattle, tiger, fox).

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `northwest-highland-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "mud_dam_beaver",
        "泥壩河狸",
        "泥壩河狸是約中型犬大小的河狸類魔獸，以家族為單位生活於西北高地的溪流與渡口上游。",
        "濃密的深褐毛皮上常糊著一層乾泥，尾巴寬扁如槳，覆著鱗狀硬皮。"
        "門牙橘黃粗大，啃斷手臂粗的松樹只需片刻。",
        "牠們啃倒溪邊的樹木，以樹枝與溪泥築起橫跨溪流的水壩，再在壩後的水塘裡建造圓頂巢屋。"
        "牠們能以微弱土屬性力量讓糊上的溪泥迅速緊實，水壩因此撐得過春季融雪的大水，糊在自己毛皮上的泥層也會變得堅硬。"
        "西北高地的渡口聚落依靠穩定的溪水擺渡，河狸家族在上游築壩時，下游渡口的水位便忽高忽低，渡船的木樁也常被啃斷。"
        "近身時，牠以寬尾拍擊對手，拍擊時讓毛皮上的泥層緊實硬化，更耐得住反擊。",
        ("northwest_highland_forest",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；溪泥緊實之力的成因不在設定中交代。",
        "（作者私有：作者解釋）低階家族群居河狸：土屬性力量只讓自身毛皮泥層與水壩溪泥緊實，不改變河道或操控水流；戰鬥呈現為尾擊與自身短暫防禦提升。連結渡口聚落的水位與渡船木樁。",
        "（作者私有：尚未證實的猜想）松濤渡的船夫相信老壩型築的水壩能預告當年融雪的早晚，這種說法尚未證實。",
        "dam_builder",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "dam_builder",
        "mud_dam_beaver",
        "築壩型",
        "普通版本，以家族為單位在溪流上築壩、啃樹。",
        "low",
        True,
        MonsterCombatProfile(
            hp=46, mp=20, sp=9, atk_phys=5, agility=4, defense=6, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("mud_pelt_slap",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

```python
    MonsterVariant(
        "old_dam_keeper",
        "mud_dam_beaver",
        "老壩型",
        "守著家族最老水壩的大型個體，毛皮上的泥層最厚，會正面迎向靠近水壩的身影。",
        "low",
        False,
        MonsterCombatProfile(
            hp=68, mp=30, sp=15, atk_phys=10, agility=4, defense=8, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("mud_pelt_slap",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "mud_pelt_slap",
        "泥甲尾擊",
        "以土屬性力量讓毛皮泥層緊實後，以寬尾拍擊單一敵方目標，造成物理傷害；出招時短暫提高自身防禦。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 3},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="earth",
        effects=["damage:earth:physical", "self_buff_apply:mud_pelt"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="earth",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("mud_dam_beaver",),
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
# 魔物資源技能（西北高地第二波）：泥壩河狸泥甲尾擊：每次已結算且具合法目標的施放都讓毛皮泥層緊實，防禦 +2 資料在 combat_modifiers.yaml 的 mud_pelt_defense 列（lamp_carapace_guard_defense 的 defense 先例）。
- key: mud_pelt
  duration: 20
  stacking: refresh
  polarity: buff
  modifiers: {}
```

- `world/rules/rulebook/combat_modifiers.yaml`, appended after the last monster resource-skill rule (the latest merged species' rule) and before the fatigue block:

```yaml
- id: mud_pelt_defense
  when: {buff_active: mud_pelt}
  then: {defense: 2}
```

- `world/rules/rulebook/status_display.yaml`, appended after the last monster resource-skill rows (the latest merged species' rows):

```yaml
- code: mud_pelt
  label: 泥甲緊實
  severity: beneficial
- code: mud_pelt_defense
  label: 泥甲緊實防禦提升
  severity: beneficial
```

- `world/skills/narration/data_earth.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "mud_pelt_slap",
        action=(
            "{actor} 甩起寬扁的尾巴，猛力拍向對手。",
            "{actor} 毛皮上的泥層一緊，轉身以硬尾拍了過去。",
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

  `| 低階 | 泥壩河狸 | 西北高地的溪流與渡口上游 | 以土屬性力量讓溪泥與毛皮泥層緊實 | 築壩型、老壩型 |`

- New section at the end of `## 低階魔物`, immediately before `## 中階魔物` (after every low section an earlier programme change added), transcribed exactly:

````markdown
### 泥壩河狸

```bestiary
species: mud_dam_beaver
parent-species: mud_dam_beaver
default-variant: dam_builder
variants:
  - key: dam_builder
    status: delivered
  - key: old_dam_keeper
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

**原型與棲地。**泥壩河狸是約中型犬大小的河狸類魔獸，以家族為單位生活於西北高地的溪流與渡口上游。

**外觀。**濃密的深褐毛皮上常糊著一層乾泥，尾巴寬扁如槳，覆著鱗狀硬皮。門牙橘黃粗大，啃斷手臂粗的松樹只需片刻。

**生態與在地關係。**牠們啃倒溪邊的樹木，以樹枝與溪泥築起橫跨溪流的水壩，再在壩後的水塘裡建造圓頂巢屋。西北高地的渡口聚落依靠穩定的溪水擺渡，河狸家族在上游築壩時，下游渡口的水位便忽高忽低，渡船的木樁也常被啃斷。守著家族最老水壩、毛皮泥層最厚的大型個體稱為老壩型。

**戰鬥中的表現。**牠們能以微弱土屬性力量讓糊上的溪泥迅速緊實，水壩因此撐得過春季融雪的大水。近身時，牠以寬尾拍擊對手，拍擊時讓毛皮上的泥層緊實硬化，更耐得住反擊。

| 變體 | 核准方向 |
| --- | --- |
| 築壩型 | 普通版本，以家族為單位在溪流上築壩、啃樹 |
| 老壩型 | 守著家族最老水壩的大型個體，毛皮上的泥層最厚，會正面迎向靠近水壩的身影 |

**委託背景示例。**鹿鳴渡上游新築了一道河狸水壩，渡口水位一週內降了半個人高，渡船擱在淺灘上動不了。渡口的船夫委託公會拆開那道水壩，把守壩的河狸家族趕往更上游的溪段。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `mud_dam_beaver` | <implementation date> | read against the registry's published ecology field; the trouble stays local to the ford settlements' water level and ferry posts, and the firming acts on mud on the beaver's own dam and pelt | checked against the declared kit: the tail slap is a single-target earth-element physical strike, and the brief defense rise mounts on the caster for every resolved attempt, matching the self policy with no hit dependency; the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D7. Tests

- `world/rules/tests/test_combat_modifiers.py::CombatModifierTests`: add `test_rule_mud_pelt_defense`, copying the four lines of `test_rule_rock_echo_stagger_agility_flat` with `RULES["mud_pelt_defense"]`.

### D8. Developer review section

Append `## 泥壩河狸` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Sturdy family builder: defense equal to the porcupine's and the crab's ordinary variants, agility below the hare's.
* MP holds two casts of the slap's MP cost; SP holds three casts of its SP cost.
* The guard (+2 defense for 20 s) matches the crab's and the porcupine's, the smallest shipped self-guard.
* The stronger 老壩型 keeps the family's oldest dam at grade E with the low band's defense ceiling.
- `### Reuse of the self-guard strike representative`: the signature, the unchanged representative `burrow_maker`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later key sorts before a representative] → every Wave 1 and Wave 2 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_tide_lamp_crab_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.rules.tests.test_combat_modifiers.CombatModifierTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change mud-dam-beaver-species` and `openspec validate mud-dam-beaver-species --strict`.
