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
| Familiar archetype | A mudskipper, the goby that walks on tidal mud. |
| Special way of life | Its pectoral fins and tail carry abnormal strength, so it vaults more than a person's height across the mud and outpaces a walker on the flats. |
| World relation | The estuary flats of 金穗港 and 東灣港 where fishing families dig clams and dry nets (southeast coast: fish markets, estuaries, tidal marsh). |
| Ability limits | The fin and tail strength is a body ability with no element; it poisons no one and leaves no lasting harm. A landed slap throws mud into the face, a brief accuracy rider; a miss changes nothing. |
| Local conflict | A colony takes over a clam flat before the spring tide, so the clam diggers ask for the fish to be driven back to the salt marsh. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar), the Wave 1 species (spore-cap mushroom, moss-quill porcupine, hollow-tree bat, hush-wing owl, vine-net spider, moss-crown stag), the Wave 2 species (mountain frog, fire salamander, bearded vulture, giant moth, giant constrictor, capercaillie, beaver, mole, wolverine, griffin) and the other six Wave 3 species. It is an animal, clearly distinct from every beastfolk subspecies (wolf, cat, bear, rabbit, cattle, tiger, fox).

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `southeast-coast-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "flat_leap_goby",
        "灘跳魚",
        "灘跳魚是約小臂長的鰕虎類魔獸，成群生活於東南海岸河口的潮間泥灘與鹽沼。",
        "灰褐色的身體布滿藍色亮點，一對大眼長在頭頂，能各自轉動。"
        "胸鰭粗壯，撐在泥上時形如一對短腿；"
        "背鰭展開時是一面帶黑邊的小旗。",
        "退潮後，牠們撐著胸鰭在泥灘上爬行，啃食泥面的藻類與小蟹。"
        "牠的胸鰭與尾巴帶著異常的力氣，胸鰭一撐、尾巴一甩就能躍過一人高的距離，在泥灘上比人走得還快。"
        "金穗港與東灣港的河口泥灘是漁家挖蛤、晾網的地方，灘跳魚群會把挖好的蛤坑占成自己的洞口，遇到有人靠近便成群跳起。"
        "近身時，牠撲上前以尾巴拍擊對手，拍中時甩起一團濕泥糊在對手臉上，讓對手短暫看不準目標。",
        ("southeast_coast",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；胸鰭與尾巴異常力氣的成因不在設定中交代。",
        "（作者私有：作者解釋）低階群居鰕虎：胸鰭與尾巴的力氣屬於身體能力，不帶元素、不造成中毒或持續傷害；戰鬥呈現為尾擊與命中後短暫命中下降（濺泥）。連結河口漁家的挖蛤與晾網。",
        "（作者私有：尚未證實的猜想）東灣港的挖蛤人說灘跳魚的泥塔築得越高，下個月的大潮就越大，這種說法尚未證實。",
        "mudflat_skipper",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "mudflat_skipper",
        "flat_leap_goby",
        "跳灘型",
        "普通版本，成群在退潮後的泥灘上爬行、啃藻。",
        "low",
        True,
        MonsterCombatProfile(
            hp=32, mp=0, sp=9, atk_phys=5, agility=10, defense=3, magic_power=0
        ),
        "F",
        True,
        active_skill_keys=("mud_tail_flick",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

```python
    MonsterVariant(
        "turret_keeper",
        "flat_leap_goby",
        "築塔型",
        "在洞口堆起泥塔、守著一片泥灘的大型雄魚，會跳向任何走近泥塔的身影。",
        "low",
        False,
        MonsterCombatProfile(
            hp=55, mp=0, sp=15, atk_phys=9, agility=10, defense=5, magic_power=0
        ),
        "E",
        True,
        active_skill_keys=("mud_tail_flick",),
        passive_skill_keys=(),
        behaviour_profile_key="instinctive",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "mud_tail_flick",
        "甩尾濺泥",
        "撲向單一敵方目標以尾巴拍擊，造成物理傷害；命中後甩起濕泥糊在對手臉上，短暫降低其命中。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"sp": 3},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        effects=["damage:none:physical", "buff_apply:mud_fleck"],
        category=SkillCategory.MARTIAL_ARTS,
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("flat_leap_goby",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=0.9, audience=EffectAudience.ENEMIES),
            EffectPolicy(coefficient=1.0, audience=EffectAudience.ENEMIES, requires_hit_from=0),
        ),
    ),
```

Also append one sentence to that module's docstring describing this kit's composition, in the style of the existing sentences.

### D4. Rulebook and narration

- `world/rules/rulebook/buffs.yaml`, appended after the last monster resource-skill buff (the buff of the latest species already merged in the serial chain), with a zh-TW comment line before it:

```yaml
# 魔物資源技能（東南海岸第三波）：灘跳魚甩尾濺泥：命中後濕泥糊臉的 mount，accuracy −2 資料在 combat_modifiers.yaml 的 mud_fleck_accuracy 列（grain_rattle_accuracy 的 hit-rider 先例）。
- key: mud_fleck
  duration: 12
  stacking: refresh
  polarity: debuff
  modifiers: {}
```

- `world/rules/rulebook/combat_modifiers.yaml`, appended after the last monster resource-skill rule (the latest merged species' rule) and before the fatigue block:

```yaml
- id: mud_fleck_accuracy
  when: {buff_active: mud_fleck}
  then: {accuracy: -2}
```

- `world/rules/rulebook/status_display.yaml`, appended after the last monster resource-skill rows (the latest merged species' rows):

```yaml
- code: mud_fleck
  label: 濺泥糊眼
  severity: harmful
- code: mud_fleck_accuracy
  label: 濺泥糊眼命中下降
  severity: harmful
```

- `world/skills/narration/data_martial.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "mud_tail_flick",
        action=(
            "{actor} 胸鰭一撐躍起，尾巴拍向對手。",
            "{actor} 從泥裡彈起，甩了對方一臉濕泥。",
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

  `| 低階 | 灘跳魚 | 東南海岸河口的潮間泥灘與鹽沼 | 胸鰭一撐、尾巴一甩就能躍過一人高的距離 | 跳灘型、築塔型 |`

- New section at the end of `## 低階魔物`, immediately before `## 中階魔物` (after every low section an earlier programme change added), transcribed exactly:

````markdown
### 灘跳魚

```bestiary
species: flat_leap_goby
parent-species: flat_leap_goby
default-variant: mudflat_skipper
variants:
  - key: mudflat_skipper
    status: delivered
  - key: turret_keeper
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

**原型與棲地。**灘跳魚是約小臂長的鰕虎類魔獸，成群生活於東南海岸河口的潮間泥灘與鹽沼。

**外觀。**灰褐色的身體布滿藍色亮點，一對大眼長在頭頂，能各自轉動。胸鰭粗壯，撐在泥上時形如一對短腿；背鰭展開時是一面帶黑邊的小旗。

**生態與在地關係。**退潮後，牠們撐著胸鰭在泥灘上爬行，啃食泥面的藻類與小蟹。金穗港與東灣港的河口泥灘是漁家挖蛤、晾網的地方，灘跳魚群會把挖好的蛤坑占成自己的洞口，遇到有人靠近便成群跳起。在洞口堆起泥塔、守著一片泥灘的大型雄魚稱為築塔型。

**戰鬥中的表現。**牠的胸鰭與尾巴帶著異常的力氣，胸鰭一撐、尾巴一甩就能躍過一人高的距離，在泥灘上比人走得還快。近身時，牠撲上前以尾巴拍擊對手，拍中時甩起一團濕泥糊在對手臉上，讓對手短暫看不準目標；拍空時泥點落在一旁。

| 變體 | 核准方向 |
| --- | --- |
| 跳灘型 | 普通版本，成群在退潮後的泥灘上爬行、啃藻 |
| 築塔型 | 在洞口堆起泥塔、守著一片泥灘的大型雄魚，會跳向任何走近泥塔的身影 |

**委託背景示例。**東灣港外的挖蛤灘，這週被一隻築塔型帶著整群灘跳魚占住，挖蛤人一靠近就被甩得滿臉是泥。漁家委託公會把魚群趕回下游的鹽沼，讓大潮前的挖蛤能照常進行。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `flat_leap_goby` | <implementation date> | read against the registry's published ecology field; the trouble stays local to estuary clam flats and net-drying ground, and the leap and the slap come from the fish's own fins and tail | checked against the declared kit: the tail slap is a single-target elementless physical strike that spends SP, and the section states that the brief mud splash to the face follows a slap that lands, matching the declared hit dependency; the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D7. Tests

- `world/rules/tests/test_combat_modifiers.py::CombatModifierTests`: add `test_rule_mud_fleck_accuracy`, copying the four lines of `test_rule_rock_echo_stagger_agility_flat` with `RULES["mud_fleck_accuracy"]`. Copy those four lines exactly and assert no rule value of your own.

### D8. Developer review section

Append `## 灘跳魚` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Fragile mudflat hopper: hit points near the low band's floor, agility in its upper half.
* The kit spends no MP, so the MP pool is zero; SP holds three casts of the slap's SP cost.
* The rider (−2 accuracy for 12 s) is the smallest monster accuracy rider, below the sparrow's and the mushroom's −3.
* The stronger 築塔型 guards a mud turret at grade E.
- `### Reuse of the enemy hit-rider representative`: the signature, the unchanged representative `cliff_stepper`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later key sorts before a representative] → every Wave 1, Wave 2 and Wave 3 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_sway_whistle_sparrow_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.rules.tests.test_combat_modifiers.CombatModifierTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change flat-leap-goby-species` and `openspec validate flat-leap-goby-species --strict`.
