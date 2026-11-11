# Design

## Context

See proposal.md (Why). Facts at `3756992d`:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS` and `_VARIANT_DECLARATIONS` at import. Bands come from `MONSTER_TIER_REGISTRY`: low HP 25–70, attack 3–12, agility 3–12, defense 2–8, grades F–E; mid HP 110–230, attack 18–28, agility 10–24, defense 10–16, grades D–C; high HP 300–750, attack 26–40, agility 16–30, defense 18–32, grades B–A. `magic_power` must be 0 and MP/SP have no band. Display names are limited to 5 code points (`MONSTER_NAME_MAX_CODE_POINTS`).
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」 and `author_conjecture_zh` to contain 「尚未證實」, and it forbids registry strings that name a skill, behaviour or trait key.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by `(slot, effect family, audience, requires_hit_from)` and requires one committed representative per group, the group's sorted-minimum key. This kit's signature is `(("active", "damage", "enemies", None), ("active", "buff_apply", "enemies", 0))`, the shipped enemy hit-rider group, whose representative `cliff_stepper` is declared in `world.rules.tests.test_sway_whistle_sparrow_resource_skill`. Every new variant key sorts after `cliff_stepper`, so the representative does not move and no smoke module, shard entry or seed entry is added. `EnemyRiderGroupMemberTests` in that module derives the group's members from the shipped declarations, so both new variants are exercised on their own agility axis without a test edit. The skill is elementless with an SP-only cost, so `spell_tier_for` returns `None` (the goblin precedent).
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests` requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, a magic tier for elemental MP skills (MP 10–16 single, 14–20 area) and `None` otherwise. `validate_catalog` requires one narration row per active skill, and `world/rules/status_display.py` fails closed for a buff or modifier without a display row.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, modifier rule, intelligence and mode entry, plus the referenced bindings. `world/rules/tests/test_monster_ai_activation.py` compares that fingerprint with `docs/development/monster-ai-activation-evidence/activation.json`.
- Every kit here carries a damage occurrence, so the legacy decision body proposes it and no utility binding or intelligence value is needed (`owned-kit-decision-coverage` applies only to support-only kits).

## Candidate review (`docs/lore/monster-creation-guidelines.md`)

| Question | Answer |
| --- | --- |
| Familiar archetype | An orb-weaving spider. |
| Special way of life | It twists stripped vine fibre into its silk, weaving nets strong enough to hold a young deer across game trails, and waits beside them. |
| World relation | Expeditions to the dragon nest and the eternal-night dungeon have to cut paths through tangled vines (north deep forest terrain flavour: vines blocking sight). |
| Ability limits | Fire and blades cut the nets; in combat the thread only slows a struck enemy briefly. It does not immobilise, poison or bind for long (an elementless body action). |
| Local conflict | A large spider spans a whole forest path, forcing supply parties into a half-day detour, so the guild is asked to cut the net open. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar) and from the other five Wave 1 species.

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `north-deep-forest-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "vine_net_spider",
        "藤網蛛",
        "藤網蛛是身軀約有圓盾大小的蜘蛛類魔獸，獨自生活在北部深林藤蔓糾結的林下與獸徑兩側。",
        "暗綠色身軀覆著短硬毛，八條長腳的關節帶著樹皮般的褐色環紋。"
        "腹部末端的紡器旁常黏著剝下的藤皮纖維。",
        "牠會剝下藤蔓外皮，把纖維與自己吐出的絲撚在一起，織成能兜住小鹿的藤網，橫跨在獸徑兩側的樹幹之間。"
        "藤網的顏色與周圍藤蔓相同，晨露沾上時才顯出網形。"
        "牠守在網邊等待獵物，捕食鹿、野豬幼獸與誤闖的大型鳥類。"
        "藤網的韌度來自藤皮纖維，火焰與利刃都能切開它，探險隊在深林開路時會帶著砍刀與火把清出通道。"
        "近身時，牠以前腳擲出黏絲纏住對手的腿腳，命中後使對手短暫行動遲緩。",
        ("north_deep_forest",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；藤皮纖維與絲線結合的成因不在設定中交代。",
        "（作者私有：作者解釋）中階伏擊型蜘蛛：絲線結合剝下的藤皮纖維形成藤網，戰鬥中的黏絲只在命中時短暫降低敏捷，不定身、不造成中毒或持續傷害。連結深林開路與獸徑狩獵。",
        "（作者私有：尚未證實的猜想）北林堡的工匠相信藤網蛛的舊網纖維能編出最耐用的弓弦，這種說法尚未證實。",
        "vine_weaver",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "vine_weaver",
        "vine_net_spider",
        "織藤型",
        "普通版本，守在獸徑旁的藤網邊等待獵物。",
        "mid",
        True,
        MonsterCombatProfile(
            hp=125, mp=0, sp=24, atk_phys=19, agility=15, defense=12, magic_power=0
        ),
        "D",
        True,
        active_skill_keys=("vine_thread_cast",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
```

```python
    MonsterVariant(
        "trail_netter",
        "vine_net_spider",
        "封道型",
        "把藤網一路織到人走的林道上，占據整段通道的大型個體。",
        "mid",
        False,
        MonsterCombatProfile(
            hp=175, mp=0, sp=36, atk_phys=25, agility=17, defense=14, magic_power=0
        ),
        "C",
        True,
        active_skill_keys=("vine_thread_cast",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
```

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "vine_thread_cast",
        "藤絲纏擲",
        "以前腳擲出摻著藤皮纖維的黏絲纏向單一敵方目標，造成物理傷害；命中後纏住腿腳，短暫降低其敏捷。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"sp": 6},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        effects=["damage:none:physical", "buff_apply:vine_snare"],
        category=SkillCategory.MARTIAL_ARTS,
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("vine_net_spider",),
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

- `world/rules/rulebook/buffs.yaml`, appended after the last monster resource-skill buff (`reservoir_film`, or the previous Wave 1 species' buff), with a zh-TW comment line before it:

```yaml
# 魔物資源技能（北部深林第一波）：藤網蛛藤絲纏擲：命中後纏住腿腳的 mount，agility_flat −3 資料在 combat_modifiers.yaml 的 vine_snare_agility_flat 列（rock_echo_stagger_agility_flat 的 hit-rider 先例）。
- key: vine_snare
  duration: 15
  stacking: refresh
  polarity: debuff
  modifiers: {}
```

- `world/rules/rulebook/combat_modifiers.yaml`, appended after the last monster resource-skill rule (`reservoir_film_defense`, or the previous Wave 1 rule) and before the fatigue block:

```yaml
- id: vine_snare_agility_flat
  when: {buff_active: vine_snare}
  then: {agility_flat: -3}
```

- `world/rules/rulebook/status_display.yaml`, appended after `reservoir_film_defense` (or the previous Wave 1 rows):

```yaml
- code: vine_snare
  label: 藤絲纏縛
  severity: harmful
- code: vine_snare_agility_flat
  label: 藤絲纏縛敏捷下降
  severity: harmful
```

- `world/skills/narration/data_martial.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "vine_thread_cast",
        action=(
            "{actor} 甩動前腳，一束帶著藤皮的黏絲纏向對手腿腳。",
            "{actor} 從藤網邊竄出，絲線接連繞上對方的小腿。",
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

- Overview row, inserted in the `## 收錄總覽` table after the last `| 中階 |` or `| 中階／高階 |` row:

  `| 中階 | 藤網蛛 | 北部深林藤蔓糾結的林下與獸徑兩側 | 把藤皮纖維與絲線撚成能兜住小鹿的藤網 | 織藤型、封道型 |`

- New section at the end of `## 中階魔物`, immediately before `## 高階魔物` (after any Wave 1 mid section already added), transcribed exactly:

````markdown
### 藤網蛛

```bestiary
species: vine_net_spider
parent-species: vine_net_spider
default-variant: vine_weaver
variants:
  - key: vine_weaver
    status: delivered
  - key: trail_netter
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

**原型與棲地。**藤網蛛是身軀約有圓盾大小的蜘蛛類魔獸，獨自生活在北部深林藤蔓糾結的林下與獸徑兩側。

**外觀。**暗綠色身軀覆著短硬毛，八條長腳的關節帶著樹皮般的褐色環紋。腹部末端的紡器旁常黏著剝下的藤皮纖維。

**生態與在地關係。**牠會剝下藤蔓外皮，把纖維與自己吐出的絲撚在一起，織成能兜住小鹿的藤網，橫跨在獸徑兩側的樹幹之間。藤網的顏色與周圍藤蔓相同，晨露沾上時才顯出網形。牠守在網邊捕食鹿、野豬幼獸與誤闖的大型鳥類。火焰與利刃都能切開藤網，探險隊在深林開路時會帶著砍刀與火把清出通道。把藤網一路織到林道上的大型個體稱為封道型。

**戰鬥中的表現。**近身時，牠以前腳擲出摻著藤皮纖維的黏絲，纏住對手的腿腳；黏絲命中後，對手短暫行動遲緩，纏擲落空時對手行動照常。

| 變體 | 核准方向 |
| --- | --- |
| 織藤型 | 普通版本，守在獸徑旁的藤網邊等待獵物 |
| 封道型 | 把藤網一路織到人走的林道上，占據整段通道的大型個體 |

**委託背景示例。**往龍巢方向的林道被一張橫跨整段通道的藤網封住，補給隊只能繞行半天。北林堡分會委託熟練隊伍砍開藤網，處理守在網邊的封道型。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `vine_net_spider` | <implementation date> | read against the registry's published ecology field; the trouble stays local to game trails and forest paths that expeditions clear, and the web strength comes from vine fibre the spider strips itself | checked against the declared kit: the thread cast is a single-target elementless physical strike that spends SP, and the section states that the brief slowing follows a cast that lands, matching the declared hit dependency; the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D7. Tests

- `world/rules/tests/test_combat_modifiers.py::CombatModifierTests`: add `test_rule_vine_snare_agility_flat`, copying the four lines of `test_rule_rock_echo_stagger_agility_flat` with `RULES["vine_snare_agility_flat"]`.

### D8. Developer review section

Append `## 藤網蛛` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Patient web ambusher: agility in the lower half of the mid band.
* Sturdy body: defense matches the lynx's ordinary variant (12).
* The kit spends no MP, so the MP pool is zero; SP holds four casts of the cast's SP cost.
* The rider (−3 agility for 15 s) equals the goat's shipped `rock_echo_stagger_agility_flat` contribution and lifetime.
* The stronger 封道型 holds a whole forest path at grade C.
- `### Reuse of the enemy hit-rider representative`: the signature, the unchanged representative `cliff_stepper`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later Wave 1 key sorts before a representative] → every Wave 1 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_sway_whistle_sparrow_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.rules.tests.test_combat_modifiers.CombatModifierTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change vine-net-spider-species` and `openspec validate vine-net-spider-species --strict`.
