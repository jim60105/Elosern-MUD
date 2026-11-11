# Design

## Context

See proposal.md (Why). Facts at `ae9185c9` plus the planned Wave 1 and Wave 2 species rows still open under `openspec/changes/*-species/`, which land first in the serial chain:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS` and `_VARIANT_DECLARATIONS` at import. Bands come from `MONSTER_TIER_REGISTRY`: low HP 25–70, attack 3–12, agility 3–12, defense 2–8, grades F–E; mid HP 110–230, attack 18–28, agility 10–24, defense 10–16, grades D–C; high HP 300–750, attack 26–40, agility 16–30, defense 18–32, grades B–A. `magic_power` must be 0 and MP/SP have no band. Display names are limited to 5 code points (`MONSTER_NAME_MAX_CODE_POINTS`).
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」 and `author_conjecture_zh` to contain 「尚未證實」, and it forbids registry strings that name a skill, behaviour or trait key.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by `(slot, effect family, audience, requires_hit_from)` and requires one committed representative per group, the group's sorted-minimum key. This kit's signature is `(("active", "damage", "enemies", None), ("active", "buff_apply", "enemies", 0))`, the shipped enemy hit-rider group, whose representative `cliff_stepper` is declared in `world.rules.tests.test_sway_whistle_sparrow_resource_skill`. Every new variant key sorts after `cliff_stepper` (as every Wave 1 and Wave 2 key does), so the representative does not move and no smoke module, shard entry or seed entry is added. `EnemyRiderGroupMemberTests` in that module derives the group's members from the shipped declarations, so both new variants are exercised on their own rider axis without a test edit. The skill is elementless with an SP-only cost, so `spell_tier_for` returns `None` (the goblin and wolverine precedent).
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests` requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, a magic tier for elemental MP skills (MP 10–16 single, 14–20 area) and `None` otherwise. `validate_catalog` requires one narration row per active skill, and `world/rules/status_display.py` fails closed for a buff or modifier without a display row.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, modifier rule, intelligence and mode entry, plus the referenced bindings. `world/rules/tests/test_monster_ai_activation.py` compares that fingerprint with `docs/development/monster-ai-activation-evidence/activation.json`.
- Every kit here carries a damage occurrence, so the legacy decision body proposes it and no utility binding or intelligence value is needed (`owned-kit-decision-coverage` applies only to support-only kits).

## Candidate review (`docs/lore/monster-creation-guidelines.md`)

| Question | Answer |
| --- | --- |
| Familiar archetype | A grey heron, the patient wading bird. |
| Special way of life | Its folded neck carries abnormal spring and snaps straight in a blink, so it spears fish below canal sluices. |
| World relation | The irrigation canals of the eastern plain and the fish ponds farmers dig beside them (terrain flavour: irrigation canals; 黑土鎮 farms and 翠湖鎮 fishers). |
| Ability limits | The spring is a body ability with no element; it blinds no one and leaves no lasting harm. A landed jab throws a splash into the face, a brief accuracy rider; a miss changes nothing. |
| Local conflict | One heron empties a fish pond below a sluice and jabs the sluice keeper, so the farmers ask for it to be driven off until harvest. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar), the Wave 1 species (spore-cap mushroom, moss-quill porcupine, hollow-tree bat, hush-wing owl, vine-net spider, moss-crown stag), the Wave 2 species (mountain frog, fire salamander, bearded vulture, giant moth, giant constrictor, capercaillie, beaver, mole, wolverine, griffin) and the other six Wave 3 species. It is an animal, clearly distinct from every beastfolk subspecies (wolf, cat, bear, rabbit, cattle, tiger, fox).

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `eastern-plains-deep-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "sluice_spear_heron",
        "渠矛蒼鷺",
        "渠矛蒼鷺是站起來與人齊高的鷺類魔獸，獨自涉行於東部大平原的灌溉渠、水門與魚塘邊。",
        "背羽灰藍，頸部細長雪白，頭頂後方垂著兩根黑色飾羽。"
        "暗黃色的長喙尖直如矛，雙腿細長，能在及膝的渠水裡一動也不動地站上半天。",
        "牠縮著長頸站在水門下方的急流邊，等魚群與青蛙游近。"
        "牠的頸部帶著異常的彈力，收縮的長頸能在眨眼間彈直，長喙刺進水裡的速度快得看不清。"
        "平原上的灌溉渠沿線都有農家挖的魚塘，渠矛蒼鷺會守在同一座水門旁，把一整池魚苗啄個精光；"
        "管水門的人走近時，牠也會揚喙刺向來人。"
        "近身時，牠以長喙疾刺對手，刺中時順勢甩起一片水花撲在對手臉上，讓對手短暫看不準目標。",
        ("eastern_plains",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；頸部異常彈力的成因不在設定中交代。",
        "（作者私有：作者解釋）中階獨居涉禽：頸部彈力屬於身體能力，不帶元素、不造成失明或持續傷害；戰鬥呈現為長喙疾刺與命中後短暫命中下降（水花撲面）。連結灌溉渠水門與農家魚塘。",
        "（作者私有：尚未證實的猜想）翠湖鎮的漁人說渠矛蒼鷺站在哪座水門下，那年那條渠的魚就最多，這種說法尚未證實。",
        "sluice_wader",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "sluice_wader",
        "sluice_spear_heron",
        "涉渠型",
        "普通版本，獨自守在灌溉渠的水門下捕魚。",
        "mid",
        True,
        MonsterCombatProfile(
            hp=125, mp=0, sp=24, atk_phys=22, agility=18, defense=10, magic_power=0
        ),
        "D",
        True,
        active_skill_keys=("spear_beak_jab",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
```

```python
    MonsterVariant(
        "heronry_elder",
        "sluice_spear_heron",
        "林巢型",
        "在渠邊柳林裡帶領整片鷺巢的老個體，孵育期會連續刺向走近巢樹的身影。",
        "mid",
        False,
        MonsterCombatProfile(
            hp=175, mp=0, sp=36, atk_phys=26, agility=19, defense=12, magic_power=0
        ),
        "C",
        True,
        active_skill_keys=("spear_beak_jab",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "spear_beak_jab",
        "矛喙疾刺",
        "以彈直的長頸驅使長喙疾刺單一敵方目標，造成物理傷害；命中後甩起水花撲向對手臉上，短暫降低其命中。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"sp": 6},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        effects=["damage:none:physical", "buff_apply:canal_splash"],
        category=SkillCategory.MARTIAL_ARTS,
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("sluice_spear_heron",),
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
# 魔物資源技能（東部大平原第三波）：渠矛蒼鷺矛喙疾刺：命中後水花撲面的 mount，accuracy −3 資料在 combat_modifiers.yaml 的 canal_splash_accuracy 列（grain_rattle_accuracy 的 hit-rider 先例）。
- key: canal_splash
  duration: 12
  stacking: refresh
  polarity: debuff
  modifiers: {}
```

- `world/rules/rulebook/combat_modifiers.yaml`, appended after the last monster resource-skill rule (the latest merged species' rule) and before the fatigue block:

```yaml
- id: canal_splash_accuracy
  when: {buff_active: canal_splash}
  then: {accuracy: -3}
```

- `world/rules/rulebook/status_display.yaml`, appended after the last monster resource-skill rows (the latest merged species' rows):

```yaml
- code: canal_splash
  label: 水花撲眼
  severity: harmful
- code: canal_splash_accuracy
  label: 水花撲眼命中下降
  severity: harmful
```

- `world/skills/narration/data_martial.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "spear_beak_jab",
        action=(
            "{actor} 縮起的長頸驟然彈直，長喙直刺對手。",
            "{actor} 一喙刺出，帶起的水花撲了對方滿臉。",
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

  `| 中階 | 渠矛蒼鷺 | 東部大平原的灌溉渠、水門與魚塘邊 | 收縮的長頸能在眨眼間彈直出喙 | 涉渠型、林巢型 |`

- New section at the end of `## 中階魔物`, immediately before `## 高階魔物` (after every mid section an earlier programme change added), transcribed exactly:

````markdown
### 渠矛蒼鷺

```bestiary
species: sluice_spear_heron
parent-species: sluice_spear_heron
default-variant: sluice_wader
variants:
  - key: sluice_wader
    status: delivered
  - key: heronry_elder
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

**原型與棲地。**渠矛蒼鷺是站起來與人齊高的鷺類魔獸，獨自涉行於東部大平原的灌溉渠、水門與魚塘邊。

**外觀。**背羽灰藍，頸部細長雪白，頭頂後方垂著兩根黑色飾羽。暗黃色的長喙尖直如矛，雙腿細長，能在及膝的渠水裡一動也不動地站上半天。

**生態與在地關係。**牠縮著長頸站在水門下方的急流邊，等魚群與青蛙游近。平原上的灌溉渠沿線都有農家挖的魚塘，渠矛蒼鷺會守在同一座水門旁，把一整池魚苗啄個精光；管水門的人走近時，牠也會揚喙刺向來人。在渠邊柳林裡帶領整片鷺巢、孵育期守著巢樹的老個體稱為林巢型。

**戰鬥中的表現。**牠的頸部帶著異常的彈力，收縮的長頸能在眨眼間彈直，長喙刺進水裡的速度快得看不清。近身時，牠以長喙疾刺對手，刺中時順勢甩起一片水花撲在對手臉上，讓對手短暫看不準目標；刺空時對手視線照常。

| 變體 | 核准方向 |
| --- | --- |
| 涉渠型 | 普通版本，獨自守在灌溉渠的水門下捕魚 |
| 林巢型 | 在渠邊柳林裡帶領整片鷺巢的老個體，孵育期會連續刺向走近巢樹的身影 |

**委託背景示例。**黑土鎮西渠第三水門下的魚塘，入夏後魚苗少了一大半，管水門的老農也被啄傷了手背。農會委託公會趕走守在水門旁的渠矛蒼鷺，讓魚塘撐到秋收。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `sluice_spear_heron` | <implementation date> | read against the registry's published ecology field; the trouble stays local to one irrigation sluice and the farm fish pond beside it, and the strike speed comes from the heron's own neck | checked against the declared kit: the beak jab is a single-target elementless physical strike that spends SP, and the section states that the brief splash to the face follows a jab that lands, matching the declared hit dependency; the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D7. Tests

- `world/rules/tests/test_combat_modifiers.py::CombatModifierTests`: add `test_rule_canal_splash_accuracy`, copying the four lines of `test_rule_rock_echo_stagger_agility_flat` with `RULES["canal_splash_accuracy"]`. Copy those four lines exactly and assert no rule value of your own.

### D8. Developer review section

Append `## 渠矛蒼鷺` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Patient wading striker: agility in the mid band's upper half, defense at the band's floor and hit points in its lower part.
* The kit spends no MP, so the MP pool is zero; SP holds four casts of the jab's SP cost.
* The rider (−3 accuracy for 12 s) matches the sparrow's shipped accuracy magnitude, milder than the lynx's −5.
* The stronger 林巢型 guards a heronry at grade C.
- `### Reuse of the enemy hit-rider representative`: the signature, the unchanged representative `cliff_stepper`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later key sorts before a representative] → every Wave 1, Wave 2 and Wave 3 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_sway_whistle_sparrow_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.rules.tests.test_combat_modifiers.CombatModifierTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change sluice-spear-heron-species` and `openspec validate sluice-spear-heron-species --strict`.
