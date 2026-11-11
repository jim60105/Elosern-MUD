# Design

## Context

See proposal.md (Why). Facts at `d1ac4b84` plus the planned Wave 1 species rows (`openspec/changes/*-species/`), which land first:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS` and `_VARIANT_DECLARATIONS` at import. Bands come from `MONSTER_TIER_REGISTRY`: low HP 25–70, attack 3–12, agility 3–12, defense 2–8, grades F–E; mid HP 110–230, attack 18–28, agility 10–24, defense 10–16, grades D–C; high HP 300–750, attack 26–40, agility 16–30, defense 18–32, grades B–A. `magic_power` must be 0 and MP/SP have no band. Display names are limited to 5 code points (`MONSTER_NAME_MAX_CODE_POINTS`).
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」 and `author_conjecture_zh` to contain 「尚未證實」, and it forbids registry strings that name a skill, behaviour or trait key.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by `(slot, effect family, audience, requires_hit_from)` and requires one committed representative per group, the group's sorted-minimum key. This kit's signature is `(("active", "damage", "enemies", None), ("active", "buff_apply", "enemies", 0))`, the shipped enemy hit-rider group, whose representative `cliff_stepper` is declared in `world.rules.tests.test_sway_whistle_sparrow_resource_skill`. Every new variant key sorts after `cliff_stepper` (and every Wave 1 key does too), so the representative does not move and no smoke module, shard entry or seed entry is added. `EnemyRiderGroupMemberTests` in that module derives the group's members from the shipped declarations, so both new variants are exercised on their own rider axis without a test edit.
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests` requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, a magic tier for elemental MP skills (MP 10–16 single, 14–20 area) and `None` otherwise. `validate_catalog` requires one narration row per active skill, and `world/rules/status_display.py` fails closed for a buff or modifier without a display row.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, modifier rule, intelligence and mode entry, plus the referenced bindings. `world/rules/tests/test_monster_ai_activation.py` compares that fingerprint with `docs/development/monster-ai-activation-evidence/activation.json`.
- Every kit here carries a damage occurrence, so the legacy decision body proposes it and no utility binding or intelligence value is needed (`owned-kit-decision-coverage` applies only to support-only kits).

## Candidate review (`docs/lore/monster-creation-guidelines.md`)

| Question | Answer |
| --- | --- |
| Familiar archetype | A bearded vulture (lammergeier), the bone-dropping mountain scavenger. |
| Special way of life | Faint wind power gathers the cold air under its own wings so it hangs nearly motionless above the mist; it lives on bones it drops onto one fixed slab and defends that slab. |
| World relation | Herb gatherers of 斷崖鎮 climb the cliff paths for cliff moss (central mountains terrain flavour: cliffs into the clouds, mist around the slopes). |
| Ability limits | The wind acts only under its own wings; it raises no storm and moves no one else. The strike is a dive whose landing throws grit and snow, giving a brief accuracy rider on a landed hit (wind element: motion). |
| Local conflict | A nesting pair blocks the cliff path the gatherers use, so the commission is an escort past the ledge. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar), the Wave 1 species (spore-cap mushroom, moss-quill porcupine, hollow-tree bat, hush-wing owl, vine-net spider, moss-crown stag) and the other nine Wave 2 species. It is an animal, clearly distinct from every beastfolk subspecies (wolf, cat, bear, rabbit, cattle, tiger, fox).

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `central-mountains-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "bone_breaker_vulture",
        "碎骨鷲",
        "碎骨鷲是雙翼展開近兩人寬的大型鷲類魔獸，成對棲息於中央山脈雲霧上方的斷崖岩棚。",
        "頭頸覆著淡黃羽毛，眼周一圈紅色，嘴基垂著一撮黑色鬚羽。"
        "背羽灰黑，翼尖細長，飛行時翅膀幾乎一動也不動。",
        "牠以動物骨骼為主食，會叼起獸骨飛到高處，丟在固定的岩板上摔碎，再吞下骨片與骨髓。"
        "牠能以微弱風屬性力量讓翼下的冷風聚攏，在雲霧上方的上升氣流裡長時間懸停；"
        "這股風力作用在牠自己的翅膀周圍。"
        "每對碎骨鷲都有一塊用了多年的摔骨岩板，岩板四周鋪滿白色碎骨，牠會撲向靠近岩板的身影。"
        "斷崖鎮的採藥人上山採崖苔時，會繞開這些鋪滿碎骨的岩棚。"
        "近身時，牠俯衝撲擊對手，撲中後振翅掀起碎石與雪粒，使對手短暫看不準目標。",
        ("central_mountains",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；翼下風力的成因不在設定中交代。",
        "（作者私有：作者解釋）中階成對棲息的鷲類：風屬性只聚攏自身翼下的氣流以懸停，不操控天氣或他人的移動；戰鬥呈現為俯衝撲擊與命中後短暫命中下降。連結採藥人的崖苔採集路線。",
        "（作者私有：尚未證實的猜想）斷崖鎮的老採藥人說摔骨岩板附近的崖苔長得最好，這種說法尚未證實。",
        "updraft_glider",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "updraft_glider",
        "bone_breaker_vulture",
        "盤谷型",
        "普通版本，在雲霧上方的上升氣流裡盤旋，尋找獸骨。",
        "mid",
        True,
        MonsterCombatProfile(
            hp=135, mp=30, sp=20, atk_phys=21, agility=17, defense=11, magic_power=0
        ),
        "D",
        True,
        active_skill_keys=("grit_wing_strike",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
```

```python
    MonsterVariant(
        "crag_nest_vulture",
        "bone_breaker_vulture",
        "崖巢型",
        "孵育期守在巢邊岩棚的個體，會連續俯衝驅趕靠近巢崖的身影。",
        "mid",
        False,
        MonsterCombatProfile(
            hp=180, mp=50, sp=30, atk_phys=26, agility=18, defense=13, magic_power=0
        ),
        "C",
        True,
        active_skill_keys=("grit_wing_strike",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "grit_wing_strike",
        "揚礫撲擊",
        "藉風屬性力量俯衝撲擊單一敵方目標，造成物理傷害；命中後振翅掀起碎石與雪粒，使對手短暫看不準目標，降低其命中。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 5},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="wind",
        effects=["damage:wind:physical", "buff_apply:grit_gust"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="wind",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("bone_breaker_vulture",),
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
# 魔物資源技能（中央山脈第二波）：碎骨鷲揚礫撲擊：命中後掀起碎石與雪粒的 mount，accuracy −3 資料在 combat_modifiers.yaml 的 grit_gust_accuracy 列（grain_rattle_accuracy 的 hit-rider 先例）。
- key: grit_gust
  duration: 12
  stacking: refresh
  polarity: debuff
  modifiers: {}
```

- `world/rules/rulebook/combat_modifiers.yaml`, appended after the last monster resource-skill rule (the latest merged species' rule) and before the fatigue block:

```yaml
- id: grit_gust_accuracy
  when: {buff_active: grit_gust}
  then: {accuracy: -3}
```

- `world/rules/rulebook/status_display.yaml`, appended after the last monster resource-skill rows (the latest merged species' rows):

```yaml
- code: grit_gust
  label: 礫雪撲面
  severity: harmful
- code: grit_gust_accuracy
  label: 礫雪撲面命中下降
  severity: harmful
```

- `world/skills/narration/data_wind.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "grit_wing_strike",
        action=(
            "{actor} 收翅俯衝，落地時掀起一片碎石與雪粒。",
            "{actor} 張開長翼撲下，翅風把砂礫打在對手臉上。",
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

  `| 中階 | 碎骨鷲 | 中央山脈雲霧上方的斷崖岩棚 | 聚攏翼下冷風，在雲霧上方長時間懸停 | 盤谷型、崖巢型 |`

- New section at the end of `## 中階魔物`, immediately before `## 高階魔物` (after every mid section an earlier programme change added), transcribed exactly:

````markdown
### 碎骨鷲

```bestiary
species: bone_breaker_vulture
parent-species: bone_breaker_vulture
default-variant: updraft_glider
variants:
  - key: updraft_glider
    status: delivered
  - key: crag_nest_vulture
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

**原型與棲地。**碎骨鷲是雙翼展開近兩人寬的大型鷲類魔獸，成對棲息於中央山脈雲霧上方的斷崖岩棚。

**外觀。**頭頸覆著淡黃羽毛，眼周一圈紅色，嘴基垂著一撮黑色鬚羽。背羽灰黑，翼尖細長，飛行時翅膀幾乎一動也不動。

**生態與在地關係。**牠以動物骨骼為主食，會叼起獸骨飛到高處，丟在固定的岩板上摔碎，再吞下骨片與骨髓。每對碎骨鷲都有一塊用了多年的摔骨岩板，岩板四周鋪滿白色碎骨，牠會撲向靠近岩板的身影。斷崖鎮的採藥人上山採崖苔時，會繞開這些鋪滿碎骨的岩棚。孵育期守在巢邊岩棚、連續俯衝驅趕來者的個體稱為崖巢型。

**戰鬥中的表現。**牠以微弱風屬性力量讓翼下的冷風聚攏，在雲霧上方的上升氣流裡長時間懸停；這股風力作用在牠自己的翅膀周圍。近身時，牠俯衝撲擊對手，撲中後振翅掀起碎石與雪粒，使對手短暫看不準目標。

| 變體 | 核准方向 |
| --- | --- |
| 盤谷型 | 普通版本，在雲霧上方的上升氣流裡盤旋，尋找獸骨 |
| 崖巢型 | 孵育期守在巢邊岩棚的個體，會連續俯衝驅趕靠近巢崖的身影 |

**委託背景示例。**斷崖鎮採藥人上山的崖徑，今年春天被一對崖巢型碎骨鷲的巢崖擋住，兩名採藥人被撲下岩棚、扭傷了腳。藥舖委託公會護送採藥隊通過巢崖，必要時驅離守巢的碎骨鷲。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `bone_breaker_vulture` | <implementation date> | read against the registry's published ecology field; the trouble stays local to cliff ledges on the gatherers' paths, and the wind acts under the vulture's own wings | checked against the declared kit: the dive is a single-target wind-element physical strike, and the section states that the brief accuracy penalty follows a dive that lands, matching the declared hit dependency; the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D7. Tests

- `world/rules/tests/test_combat_modifiers.py::CombatModifierTests`: add `test_rule_grit_gust_accuracy`, copying the four lines of `test_rule_rock_echo_stagger_agility_flat` with `RULES["grit_gust_accuracy"]`. Copy those four lines exactly and assert no rule value of your own.

### D8. Developer review section

Append `## 碎骨鷲` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Soaring raider: agility in the mid band's middle, between the goat's and the lynx's ordinary variants.
* Lightly armoured: defense one above the mid band's floor.
* MP holds three casts of the strike's MP cost; SP holds four casts of its SP cost.
* The rider (−3 accuracy for 12 s) matches the sparrow's shipped accuracy magnitude, milder than the lynx's −5.
* The stronger 崖巢型 guards a nest ledge at grade C with a larger pool.
- `### Reuse of the enemy hit-rider representative`: the signature, the unchanged representative `cliff_stepper`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later key sorts before a representative] → every Wave 1 and Wave 2 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_sway_whistle_sparrow_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.rules.tests.test_combat_modifiers.CombatModifierTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change bone-breaker-vulture-species` and `openspec validate bone-breaker-vulture-species --strict`.
