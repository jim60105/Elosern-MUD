# Design

## Context

See proposal.md (Why). Facts at `ae9185c9` plus the planned Wave 1 and Wave 2 species rows still open under `openspec/changes/*-species/`, which land first in the serial chain:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS` and `_VARIANT_DECLARATIONS` at import. Bands come from `MONSTER_TIER_REGISTRY`: low HP 25–70, attack 3–12, agility 3–12, defense 2–8, grades F–E; mid HP 110–230, attack 18–28, agility 10–24, defense 10–16, grades D–C; high HP 300–750, attack 26–40, agility 16–30, defense 18–32, grades B–A. `magic_power` must be 0 and MP/SP have no band. Display names are limited to 5 code points (`MONSTER_NAME_MAX_CODE_POINTS`).
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」 and `author_conjecture_zh` to contain 「尚未證實」, and it forbids registry strings that name a skill, behaviour or trait key.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by `(slot, effect family, audience, requires_hit_from)` and requires one committed representative per group, the group's sorted-minimum key. This kit's signature is `(("active", "damage", "enemies", None), ("active", "self_buff_apply", "self", None))`, the shipped self-guard strike group, whose representative `burrow_maker` is declared in `world.rules.tests.test_tide_lamp_crab_resource_skill`. Every new variant key sorts after `burrow_maker` (as every Wave 1 and Wave 2 key does), so the representative does not move and no smoke module, shard entry or seed entry is added. The self policy declares no hit dependency, following the crab and hare kits, so the mount lands on every resolved attempt including a miss. The self mount raises flat agility (`agility_flat`), the axis of the rat's shipped self rise; the signature reads only family, audience and hit dependency, so the species joins the crab and hare group without a new representative.
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests` requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, a magic tier for elemental MP skills (MP 10–16 single, 14–20 area) and `None` otherwise. `validate_catalog` requires one narration row per active skill, and `world/rules/status_display.py` fails closed for a buff or modifier without a display row.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, modifier rule, intelligence and mode entry, plus the referenced bindings. `world/rules/tests/test_monster_ai_activation.py` compares that fingerprint with `docs/development/monster-ai-activation-evidence/activation.json`.
- Every kit here carries a damage occurrence, so the legacy decision body proposes it and no utility binding or intelligence value is needed (`owned-kit-decision-coverage` applies only to support-only kits).

## Candidate review (`docs/lore/monster-creation-guidelines.md`)

| Question | Answer |
| --- | --- |
| Familiar archetype | A herring gull of harbours and fish markets. |
| Special way of life | Faint wind power gathers a side gust under its own wings, so it breaks from a circling glide into a sudden sideways snatch and turns back to the masthead; the gust tires it after a few passes. |
| World relation | The fish market and dockside drying stores of 金穗港 (southeast coast terrain flavour: fish markets, masts, seabirds). |
| Ability limits | The gust forms only under its own wings; it raises no sea wind and moves no sail. The peck brings a brief self agility rise on every resolved attempt (wind element: motion and evasion). |
| Local conflict | A flock raids a dockside fish-drying store, so the store owner asks for the flock to be driven off the roof. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar), the Wave 1 species (spore-cap mushroom, moss-quill porcupine, hollow-tree bat, hush-wing owl, vine-net spider, moss-crown stag), the Wave 2 species (mountain frog, fire salamander, bearded vulture, giant moth, giant constrictor, capercaillie, beaver, mole, wolverine, griffin) and the other six Wave 3 species. It is an animal, clearly distinct from every beastfolk subspecies (wolf, cat, bear, rabbit, cattle, tiger, fox).

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `southeast-coast-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "mast_wind_gull",
        "桅風海鷗",
        "桅風海鷗是雙翼展開約一臂半寬的鷗類魔獸，成群棲息於東南海岸的港口、碼頭與防波堤。",
        "頭胸雪白，背羽淺灰，翼尖一截墨黑。"
        "黃色的嘴粗壯帶鉤，下嘴尖有一點紅斑，雙腳是橘黃色的蹼足。",
        "牠們在桅杆之間盤旋，盯著魚市攤上的漁獲與碼頭工人手裡的乾糧。"
        "牠能以微弱風屬性力量在翼下聚起一股側風，從盤旋中驟然橫掠而下，叼走攤上的魚後一個轉身飛回桅頂；"
        "這股風力在牠自己的雙翼下聚起，連續掠飛幾次就得停下來喘氣。"
        "金穗港的魚市每天清晨開市，攤販得一手收錢、一手揮竿趕鷗，貨箱上的魚乾也常被整串叼走。"
        "近身時，牠俯身啄擊對手，啄擊時翼下的側風一聚，短時間內身形更輕快。",
        ("southeast_coast",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；翼下側風的成因不在設定中交代。",
        "（作者私有：作者解釋）低階群居海鷗：風屬性只在自身翼下聚起側風以橫掠與轉身，不颳起海風、不影響船帆；戰鬥呈現為啄擊與自身短暫敏捷提升。連結金穗港魚市與碼頭貨箱。",
        "（作者私有：尚未證實的猜想）南岬港的船員相信桅風海鷗聚在哪艘船的桅頂，那艘船下一趟就會滿載，這種說法尚未證實。",
        "mast_circler",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "mast_circler",
        "mast_wind_gull",
        "繞桅型",
        "普通版本，成群在港口的桅杆之間盤旋、搶食。",
        "low",
        True,
        MonsterCombatProfile(
            hp=28, mp=20, sp=9, atk_phys=5, agility=11, defense=2, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("wind_snatch_dive",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

```python
    MonsterVariant(
        "stack_colony_elder",
        "mast_wind_gull",
        "堤群型",
        "在防波堤礁石上帶領整片鷗群的老個體，會帶頭撲向靠近繁殖礁石的身影。",
        "low",
        False,
        MonsterCombatProfile(
            hp=50, mp=30, sp=15, atk_phys=9, agility=12, defense=4, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("wind_snatch_dive",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "wind_snatch_dive",
        "掠風啄擊",
        "以風屬性力量在翼下聚起側風，橫掠而下啄擊單一敵方目標，造成物理傷害；出招時短暫提高自身敏捷。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 3},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="wind",
        effects=["damage:wind:physical", "self_buff_apply:gull_updraft"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="wind",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("mast_wind_gull",),
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
# 魔物資源技能（東南海岸第三波）：桅風海鷗掠風啄擊：每次已結算且具合法目標的施放都在翼下聚起側風，agility_flat +2 資料在 combat_modifiers.yaml 的 gull_updraft_agility_flat 列（wax_slip_agility_flat 的 agility_flat 先例）。
- key: gull_updraft
  duration: 15
  stacking: refresh
  polarity: buff
  modifiers: {}
```

- `world/rules/rulebook/combat_modifiers.yaml`, appended after the last monster resource-skill rule (the latest merged species' rule) and before the fatigue block:

```yaml
- id: gull_updraft_agility_flat
  when: {buff_active: gull_updraft}
  then: {agility_flat: 2}
```

- `world/rules/rulebook/status_display.yaml`, appended after the last monster resource-skill rows (the latest merged species' rows):

```yaml
- code: gull_updraft
  label: 乘風輕身
  severity: beneficial
- code: gull_updraft_agility_flat
  label: 乘風輕身敏捷提升
  severity: beneficial
```

- `world/skills/narration/data_wind.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "wind_snatch_dive",
        action=(
            "{actor} 從桅頂橫掠而下，一口啄向對手。",
            "{actor} 翼下側風一聚，轉身又啄了過來。",
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

  `| 低階 | 桅風海鷗 | 東南海岸的港口、碼頭與防波堤 | 在翼下聚起側風，從盤旋中驟然橫掠 | 繞桅型、堤群型 |`

- New section at the end of `## 低階魔物`, immediately before `## 中階魔物` (after every low section an earlier programme change added), transcribed exactly:

````markdown
### 桅風海鷗

```bestiary
species: mast_wind_gull
parent-species: mast_wind_gull
default-variant: mast_circler
variants:
  - key: mast_circler
    status: delivered
  - key: stack_colony_elder
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

**原型與棲地。**桅風海鷗是雙翼展開約一臂半寬的鷗類魔獸，成群棲息於東南海岸的港口、碼頭與防波堤。

**外觀。**頭胸雪白，背羽淺灰，翼尖一截墨黑。黃色的嘴粗壯帶鉤，下嘴尖有一點紅斑，雙腳是橘黃色的蹼足。

**生態與在地關係。**牠們在桅杆之間盤旋，盯著魚市攤上的漁獲與碼頭工人手裡的乾糧。金穗港的魚市每天清晨開市，攤販得一手收錢、一手揮竿趕鷗，貨箱上的魚乾也常被整串叼走。在防波堤礁石上帶領整片鷗群的老個體稱為堤群型。

**戰鬥中的表現。**牠能以微弱風屬性力量在翼下聚起一股側風，從盤旋中驟然橫掠而下；這股風力在牠自己的雙翼下聚起，連續掠飛幾次就得停下來喘氣。近身時，牠俯身啄擊對手，每次啄擊時翼下的側風都會一聚，短時間內身形更輕快。

| 變體 | 核准方向 |
| --- | --- |
| 繞桅型 | 普通版本，成群在港口的桅杆之間盤旋、搶食 |
| 堤群型 | 在防波堤礁石上帶領整片鷗群的老個體，會帶頭撲向靠近繁殖礁石的身影 |

**委託背景示例。**金穗港東碼頭的魚乾倉，這個月被一群桅風海鷗盯上，曬在倉前的魚乾每天少掉好幾串。倉主委託公會把鷗群從倉頂趕走，順便找出帶頭的那隻堤群型。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `mast_wind_gull` | <implementation date> | read against the registry's published ecology field; the trouble stays local to a fish market and a dockside drying store, and the side gust forms under the gull's own wings | checked against the declared kit: the dive peck is a single-target wind-element physical strike, and the brief agility rise mounts on the caster for every resolved attempt, matching the self policy with no hit dependency; the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D7. Tests

- `world/rules/tests/test_combat_modifiers.py::CombatModifierTests`: add `test_rule_gull_updraft_agility_flat`, copying the four lines of `test_rule_rock_echo_stagger_agility_flat` with `RULES["gull_updraft_agility_flat"]`. Copy those four lines exactly and assert no rule value of your own.

### D8. Developer review section

Append `## 桅風海鷗` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Light harbour flier: agility near the low band's ceiling, defense at its floor and hit points in its lower part.
* MP holds two casts of the peck's MP cost; SP holds three casts of its SP cost.
* The gust (+2 agility for 15 s) is below the rat's shipped self agility rise (+3).
* The stronger 堤群型 leads a breakwater colony at grade E.
- `### Reuse of the self-guard strike representative`: the signature, the unchanged representative `burrow_maker`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later key sorts before a representative] → every Wave 1, Wave 2 and Wave 3 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_tide_lamp_crab_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.rules.tests.test_combat_modifiers.CombatModifierTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change mast-wind-gull-species` and `openspec validate mast-wind-gull-species --strict`.
