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
| Familiar archetype | A wild horse of the open grassland. |
| Special way of life | Faint wind power gathers air around its own hooves, so it reaches full speed in one stride and turns sharply without stumbling; the wind tires it the longer it runs. |
| World relation | 駿原鎮 breeds horses for the imperial army and 東牧鎮 runs the livestock market of the eastern pastures (eastern plains: ranch towns and pastures). |
| Ability limits | The wind stays around its own hooves; it raises no storm and pushes no one. The kick brings a brief self agility rise on every resolved attempt (wind element: motion and evasion). |
| Local conflict | A herd breaks ranch fences, grazes the winter pasture and leads a ranch mare away, so the commission is to drive the herd off and bring the mare back. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar), the Wave 1 species (spore-cap mushroom, moss-quill porcupine, hollow-tree bat, hush-wing owl, vine-net spider, moss-crown stag), the Wave 2 species (mountain frog, fire salamander, bearded vulture, giant moth, giant constrictor, capercaillie, beaver, mole, wolverine, griffin) and the other six Wave 3 species. It is an animal, clearly distinct from every beastfolk subspecies (wolf, cat, bear, rabbit, cattle, tiger, fox).

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `eastern-plains-deep-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "dust_mane_horse",
        "揚塵野馬",
        "揚塵野馬是肩高與人相當的野馬類魔獸，成小群奔馳於東部大平原的丘陵牧野與開闊草原。",
        "沙褐色的短毛沾滿塵土，鬃毛與尾毛又長又粗，奔跑時在身後拖出一道灰黃。"
        "四肢修長，蹄子寬大堅硬，蹄緣一圈顏色較深。",
        "牠們以三五匹為一群，清晨與黃昏在草原上吃草，白天躲在丘陵背風處休息。"
        "牠能以微弱風屬性力量讓氣流聚在四蹄周圍，起跑時一蹬就衝到全速，在草原上急轉也不會失足；"
        "這股風力繞在牠自己的蹄邊，跑得越久越耗體力。"
        "駿原鎮與東牧鎮靠養馬與放牧維生，野馬群常撞開牧場的木柵欄，啃光留給家畜的冬季草場，有時還把牧場的母馬引進野馬群裡。"
        "近身時，牠人立而起以前蹄踢擊對手，踢擊時蹄邊捲起一陣風，短時間內腳步更快。",
        ("eastern_plains",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；蹄邊風力的成因不在設定中交代。",
        "（作者私有：作者解釋）中階小群生活的野馬：風屬性只把氣流聚在自身四蹄周圍以加速與轉向，不颳起風暴、不推動他人；戰鬥呈現為前蹄踢擊與自身短暫敏捷提升。描寫維持動物體態，不與任何獸人亞種相比。連結駿原鎮的馬匹繁育與東牧鎮的牧場柵欄。",
        "（作者私有：尚未證實的猜想）駿原鎮的馴馬師相信跟過野馬群一季的母馬，生下的小馬跑得特別快，這種說法尚未證實。",
        "plain_runner",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "plain_runner",
        "dust_mane_horse",
        "奔原型",
        "普通版本，成小群在草原上吃草、奔馳。",
        "mid",
        True,
        MonsterCombatProfile(
            hp=150, mp=30, sp=20, atk_phys=21, agility=20, defense=11, magic_power=0
        ),
        "D",
        True,
        active_skill_keys=("dust_gallop_kick",),
        passive_skill_keys=(),
        behaviour_profile_key="pack_hunter",
    ),
```

```python
    MonsterVariant(
        "herd_stallion",
        "dust_mane_horse",
        "頭馬型",
        "帶領整群野馬的成年公馬，體型最大，會擋在馬群前方迎向靠近的身影。",
        "mid",
        False,
        MonsterCombatProfile(
            hp=200, mp=50, sp=30, atk_phys=26, agility=22, defense=13, magic_power=0
        ),
        "C",
        True,
        active_skill_keys=("dust_gallop_kick",),
        passive_skill_keys=(),
        behaviour_profile_key="pack_hunter",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "dust_gallop_kick",
        "疾蹄踢擊",
        "以風屬性力量把氣流聚在四蹄周圍，人立而起以前蹄踢擊單一敵方目標，造成物理傷害；出招時短暫提高自身敏捷。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 5},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="wind",
        effects=["damage:wind:physical", "self_buff_apply:gale_hooves"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="wind",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("dust_mane_horse",),
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

- `world/rules/rulebook/buffs.yaml`, appended after the last monster resource-skill buff (the buff of the latest species already merged in the serial chain), with a zh-TW comment line before it:

```yaml
# 魔物資源技能（東部大平原第三波）：揚塵野馬疾蹄踢擊：每次已結算且具合法目標的施放都讓氣流聚在四蹄，agility_flat +3 資料在 combat_modifiers.yaml 的 gale_hooves_agility_flat 列（wax_slip_agility_flat 的 agility_flat 先例）。
- key: gale_hooves
  duration: 15
  stacking: refresh
  polarity: buff
  modifiers: {}
```

- `world/rules/rulebook/combat_modifiers.yaml`, appended after the last monster resource-skill rule (the latest merged species' rule) and before the fatigue block:

```yaml
- id: gale_hooves_agility_flat
  when: {buff_active: gale_hooves}
  then: {agility_flat: 3}
```

- `world/rules/rulebook/status_display.yaml`, appended after the last monster resource-skill rows (the latest merged species' rows):

```yaml
- code: gale_hooves
  label: 疾風蹄步
  severity: beneficial
- code: gale_hooves_agility_flat
  label: 疾風蹄步敏捷提升
  severity: beneficial
```

- `world/skills/narration/data_wind.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "dust_gallop_kick",
        action=(
            "{actor} 人立而起，前蹄猛力踢向對手。",
            "{actor} 四蹄捲起一陣塵風，繞到側面猛然一踢。",
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

  `| 中階 | 揚塵野馬 | 東部大平原的丘陵牧野與開闊草原 | 把氣流聚在四蹄周圍，一蹬就衝到全速 | 奔原型、頭馬型 |`

- New section at the end of `## 中階魔物`, immediately before `## 高階魔物` (after every mid section an earlier programme change added), transcribed exactly:

````markdown
### 揚塵野馬

```bestiary
species: dust_mane_horse
parent-species: dust_mane_horse
default-variant: plain_runner
variants:
  - key: plain_runner
    status: delivered
  - key: herd_stallion
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

**原型與棲地。**揚塵野馬是肩高與人相當的野馬類魔獸，成小群奔馳於東部大平原的丘陵牧野與開闊草原。

**外觀。**沙褐色的短毛沾滿塵土，鬃毛與尾毛又長又粗，奔跑時在身後拖出一道灰黃。四肢修長，蹄子寬大堅硬，蹄緣一圈顏色較深。

**生態與在地關係。**牠們以三五匹為一群，清晨與黃昏在草原上吃草，白天躲在丘陵背風處休息。駿原鎮與東牧鎮靠養馬與放牧維生，野馬群常撞開牧場的木柵欄，啃光留給家畜的冬季草場，有時還把牧場的母馬引進野馬群裡。帶領整群野馬、體型最大的成年公馬稱為頭馬型。

**戰鬥中的表現。**牠能以微弱風屬性力量讓氣流聚在四蹄周圍，起跑時一蹬就衝到全速，在草原上急轉也不會失足；這股風力繞在牠自己的蹄邊，跑得越久越耗體力。近身時，牠人立而起以前蹄踢擊對手，每次踢擊時蹄邊都捲起一陣風，短時間內腳步更快。

| 變體 | 核准方向 |
| --- | --- |
| 奔原型 | 普通版本，成小群在草原上吃草、奔馳 |
| 頭馬型 | 帶領整群野馬的成年公馬，體型最大，會擋在馬群前方迎向靠近的身影 |

**委託背景示例。**東牧鎮東邊的冬季草場被一群揚塵野馬占住，柵欄撞破了兩處，還有一匹牧場母馬跟著馬群跑了。牧場主委託公會把野馬群趕離草場，若能把那匹母馬牽回來另有酬謝。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `dust_mane_horse` | <implementation date> | read against the registry's published ecology field; the trouble stays local to ranch fences and winter pastures, and the wind stays around the horse's own hooves | checked against the declared kit: the fore-hoof kick is a single-target wind-element physical strike, and the brief agility rise mounts on the caster for every resolved attempt, matching the self policy with no hit dependency; the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D7. Tests

- `world/rules/tests/test_combat_modifiers.py::CombatModifierTests`: add `test_rule_gale_hooves_agility_flat`, copying the four lines of `test_rule_rock_echo_stagger_agility_flat` with `RULES["gale_hooves_agility_flat"]`. Copy those four lines exactly and assert no rule value of your own.

### D8. Developer review section

Append `## 揚塵野馬` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Herd runner: agility in the mid band's upper half, equal to the lynx's ordinary variant, with defense one above the band's floor.
* MP holds three casts of the kick's MP cost; SP holds four casts of its SP cost.
* The gallop (+3 agility for 15 s) equals the rat's shipped self agility rise.
* The stronger 頭馬型 leads the herd at grade C with a larger pool.
- `### Reuse of the self-guard strike representative`: the signature, the unchanged representative `burrow_maker`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later key sorts before a representative] → every Wave 1, Wave 2 and Wave 3 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_tide_lamp_crab_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.rules.tests.test_combat_modifiers.CombatModifierTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change dust-mane-horse-species` and `openspec validate dust-mane-horse-species --strict`.
