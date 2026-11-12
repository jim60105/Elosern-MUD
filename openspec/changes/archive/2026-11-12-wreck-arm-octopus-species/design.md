# Design

## Context

See proposal.md (Why). Facts at `cf4643a1` plus the planned Wave 2, Wave 3 and earlier Wave 4 species rows still open under `openspec/changes/*-species/`, which land first in the serial chain:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS` and `_VARIANT_DECLARATIONS` at import. Bands come from `MONSTER_TIER_REGISTRY`: low HP 25–70, attack 3–12, agility 3–12, defense 2–8, grades F–E; mid HP 110–230, attack 18–28, agility 10–24, defense 10–16, grades D–C; high HP 300–750, attack 26–40, agility 16–30, defense 18–32, grades B–A. `magic_power` must be 0 and MP/SP have no band. Display names are limited to 5 code points (`MONSTER_NAME_MAX_CODE_POINTS`).
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」 and `author_conjecture_zh` to contain 「尚未證實」, and it forbids registry strings that name a skill, behaviour or trait key.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by `(slot, effect family, audience, requires_hit_from)` and requires one committed representative per group, the group's sorted-minimum key. This kit's signature is `(("active", "damage", "enemies", None), ("active", "damage", "enemies", None))`, the shipped two-strike (single + area damage) group, whose representative `warm_den_boar` is declared in `world.rules.tests.test_ember_bristle_boar_resource_skill`. Every new variant key sorts after `warm_den_boar` (as every Wave 1, Wave 2 and Wave 3 key does), so the representative does not move and no smoke module, shard entry or seed entry is added. `"warm_den_boar" < "wreck_den_elder"`, so the boar stays the representative and no smoke module is added.
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests` requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, a magic tier for elemental MP skills (MP 10–16 single, 14–20 area) and `None` otherwise. `validate_catalog` requires one narration row per active skill, and `world/rules/status_display.py` fails closed for a buff or modifier without a display row.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, modifier rule, intelligence and mode entry, plus the referenced bindings. `world/rules/tests/test_monster_ai_activation.py` compares that fingerprint with `docs/development/monster-ai-activation-evidence/activation.json`.
- Every kit here carries a damage occurrence, so the legacy decision body proposes it and no utility binding or intelligence value is needed (`owned-kit-decision-coverage` applies only to support-only kits).

## Candidate review (`docs/lore/monster-creation-guidelines.md`)

| Question | Answer |
| --- | --- |
| Familiar archetype | A giant octopus of sea caves and wrecks (the kraken of sailors' folklore, at local scale). |
| Special way of life | Water power wraps a heavy sleeve of seawater along its own arms, so it stays wet out of the sea for a whole tide and hauls itself up the cliff-foot rocks into a stranded wreck. |
| World relation | The fishers of 南潮港 who lift their trap lines around the sea caves, and the wrecks of merchant ships under the sea cliffs (southwest coast terrain flavour: sea cliffs, fishing villages, merchant ships). |
| Ability limits | The water power acts on the sleeves of its own arms; it raises no wave, sinks no ship and moves no current. No divinity, guardian mission or elven tie, and no far-sea monster; when its magic and stamina are spent it falls back to plain blows. |
| Local conflict | The named octopus 沉錨 widens its foraging to the moorings, snapping mooring lines and taking trap lines, so the fishers' guild posts a commission for a skilled party. |

Distinct from the shipped archetypes (sparrow, crab, hare, goat, lynx, crocodile, slime, rat, goblin, boar), the Wave 1 species (spore-cap mushroom, moss-quill porcupine, hollow-tree bat, hush-wing owl, vine-net spider, moss-crown stag), the Wave 2 species (mountain frog, fire salamander, bearded vulture, giant moth, giant constrictor, capercaillie, beaver, mole, wolverine, griffin), the Wave 3 species (dung beetle, wild horse, grey heron, giant snapping turtle, mudskipper, herring gull, harbour seal) and the other six Wave 4 species (giant harvester ant of dry salt roads, sea star of rock pools and oyster racks, mantis shrimp of harbour shallows, marine iguana of sea cliffs, cave cricket of mines and cellars, antlion larva of quarry sand). It is an animal, clearly distinct from every beastfolk subspecies (wolf, cat, bear, rabbit, cattle, tiger, fox).

## Goals / Non-Goals

**Goals:** one complete, constructible species with legacy-AI kits and keyed documentation, transcribed verbatim from this design.

**Non-Goals:** placement, compositions and activities (owned by `southwest-coast-placement`); passives; any new effect prefix, decision mode or composition signature; poison, sleep, immobilisation, invisibility, terrain or plant control; image assets.

## Decisions

### D1. Species row (append at the end of `_SPECIES_DECLARATIONS`)

```python
    MonsterSpecies(
        "wreck_arm_octopus",
        "沉船巨蛸",
        "沉船巨蛸是八條觸腕張開能蓋住一艘漁船的巨大章魚類魔獸，獨自棲息於西南海岸海崖下的海蝕洞與擱淺的沉船殘骸。",
        "軟滑的身體泛著暗紅與褐色的斑紋，一對金黃的眼睛長在頭側，瞳孔是一道橫縫。"
        "八條觸腕粗如船纜，內側排滿兩列碗口大的吸盤，腕根之間藏著一張鉤狀的硬喙。",
        "牠白天縮在海蝕洞深處或沉船的船艙裡，夜裡伸出觸腕，在礁石間摸找蟹、魚與貝類。"
        "牠能以水屬性力量讓海水沿著觸腕裹成一層沉重的水套，離開海面一整個潮汐仍保持濕潤，還能拖著身體爬上崖腳的礁岩。"
        "南潮港一帶的漁家熟知哪幾處海蝕洞有牠出沒，收漁籠時會繞開那些洞口。"
        "牠以單條觸腕纏住一名對手絞緊，也會甩開全部觸腕橫掃身旁每個對手；"
        "兩者都耗費牠自身的魔力與體力。"
        "首隻指定個體盤踞在一艘舊商船的殘骸裡，總是纏著船上那具生鏽的大錨，被稱為「沉錨」。",
        ("southwest_coast",),
        "（作者私有：隱秘真相）本物種沒有已定的起源真相；觸腕水套之力的成因不在設定中交代。",
        "（作者私有：作者解釋）高階獨居巨型章魚：水屬性只在自身觸腕裹成水套，讓牠離水時保持濕潤並加重擊打，不掀起浪潮、不拖沉船隻、不操控海流；戰鬥呈現為水屬性物理絞纏與範圍橫掃，資源耗盡後回到普通攻擊。不具神性、守護使命或精靈關聯，也不屬於遠洋魔獸。連結南潮港漁家收漁籠的習慣與海崖下的沉船。",
        "（作者私有：尚未證實的猜想）南潮港的老船匠說沉錨纏著的那具大錨來自一艘載滿精工銀器的商船，這種說法尚未證實。",
        "wreck_den_elder",
        True,
    ),
```

### D2. Variant rows (append at the end of `_VARIANT_DECLARATIONS`, in this order)

```python
    MonsterVariant(
        "wreck_den_elder",
        "wreck_arm_octopus",
        "沉骸型",
        "普通版本，長年盤踞在海蝕洞或沉船殘骸裡的成年個體。",
        "high",
        True,
        MonsterCombatProfile(
            hp=480, mp=48, sp=30, atk_phys=31, agility=22, defense=22, magic_power=0
        ),
        "B",
        True,
        active_skill_keys=("wreck_arm_bind", "wreck_arm_sweep",),
        passive_skill_keys=(),
        behaviour_profile_key="ambush_predator",
    ),
```

**Deviation (applied during implementation).** `pack_hunter` was the first
choice, but its `skill_choice: highest_expected_damage` cannot select this kit
deterministically: `_choose_skill` compares only the actor's adjusted attack
against the defender's defense and ignores the coefficient, so `wreck_arm_bind`
and the innate `basic_attack` — both physical, both appended to the owned keys
— tie and consume one tie-break die (`_legacy_action` → `_choose_skill`). That
is exactly the dice-dependent kit selection the change must not ship (the
shipped boar smoke has to pin that die for the same reason). `ambush_predator`
preserves the design's targeting and flee semantics exactly — `lowest_hp`
targeting and the same 0.20 flee threshold — and its `first_owned` choice makes
`wreck_arm_bind` the deterministic single-target selection; it is also the
archetype the shipped two-strike kit 湖丘巨龜 binds for the identical
single-plus-area shape. The trade-off is that `prefer_area_when_multiple_enemies`
is not carried, so the legacy body always opens on the single-target arm bind
and never selects 群腕橫掃, exactly as the turtle's area slam behaves today; the
area row stays declared and exercised by the composition contracts. Recorded
here, in D8's decision-mode subsection and in the developer review.

### D3. Skill rows (append at the end of `ROWS` in `world/skills/registry/data_monster_abilities.py`)

```python
    _skill(
        "wreck_arm_bind",
        "觸腕絞纏",
        "以水屬性力量讓海水裹住觸腕，纏住單一敵方目標絞緊，造成水屬性物理傷害。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 12, "sp": 6},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="water",
        effects=["damage:water:physical"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="water",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("wreck_arm_octopus",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=1.2, audience=EffectAudience.ENEMIES),
        ),
    ),
```

```python
    _skill(
        "wreck_arm_sweep",
        "群腕橫掃",
        "甩開裹著水套的全部觸腕橫掃一圈，以水屬性力量對周圍每個敵方目標造成水屬性物理傷害。",
        SkillKind.ACTIVE,
        TargetSpec.AREA,
        cost={"mp": 16, "sp": 8},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="water",
        effects=["damage:water:physical"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="water",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("wreck_arm_octopus",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=0.8, audience=EffectAudience.ENEMIES),
        ),
    ),
```

Also append one sentence to that module's docstring describing this kit's composition, in the style of the existing sentences.

### D4. Rulebook and narration

- No timed effect, modifier or status row: the kit's riders are a damage occurrence and, where present, a gauge transfer or a second damage occurrence.
- `world/skills/narration/data_water.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "wreck_arm_bind",
        action=(
            "{actor} 一條觸腕捲了過來，纏住對手猛然絞緊。",
            "{actor} 裹著海水的觸腕越收越緊，吸盤吸住對方不放。",
        ),
    ),
```

- `world/skills/narration/data_water.py`, appended at the end of `ROWS`, before its closing parenthesis (when this design lists two rows for one file, append them in the listed order):

```python
    NarrationRow(
        "wreck_arm_sweep",
        action=(
            "{actor} 甩開八條觸腕，帶著水花橫掃一圈。",
            "{actor} 沉重的觸腕掃過四周，濺起的海水打在眾人身上。",
        ),
    ),
```

### D5. AI binding and activation evidence

No `world/rules/rulebook/monster_behaviour.yaml` edit. This link adds no timed effect or modifier, so the tuning fingerprint is expected to stay unchanged. Each variant binds the shipped archetype named in D2, and the legacy body selects the damage-bearing kit. Run `ActivationRecordTests`, `ActivationBindingTests` and `RollbackTests`. If they pass, the fingerprint did not move and the evidence stays untouched. If a fingerprint comparison fails, re-fingerprint following the `mudfilm-slime-species` precedent (archived change design D5, steps 1–4), without touching `activated` or `activation_bindings`:

1. Run `uv run --locked python tools/monster_ai_manual_reports.py selector` and copy `.var/monster-ai-manual-reports/selector-check.json` and `.md` over `docs/development/monster-ai-manual-evidence/`.
2. Read the new `configuration_fingerprint` from the regenerated `selector-check.json`. Read the rollback fingerprint from the `RollbackTests` failure message.
3. In `activation.json`, update `configuration_fingerprint`, `legacy_rollback.configuration_fingerprint` and the `selector-check.json` evidence entry's fingerprint.
4. Update the fingerprint lines in `docs/development/monster-ai-activation-evidence/README.md` and the selector paragraph of `docs/development/monster-ai-manual-evidence/README.md`.

### D6. Bestiary and ledger

- Overview row, inserted in the `## 收錄總覽` table after the last `| 高階 |` row:

  `| 高階 | 沉船巨蛸 | 西南海岸海崖下的海蝕洞與沉船殘骸 | 以水屬性力量讓海水裹住觸腕 | 沉骸型 |`

- New section at the end of `## 高階魔物`, immediately before `<!-- bestiary-current-end -->` (after every high section an earlier programme change added), transcribed exactly:

````markdown
### 沉船巨蛸

```bestiary
species: wreck_arm_octopus
parent-species: wreck_arm_octopus
default-variant: wreck_den_elder
variants:
  - key: wreck_den_elder
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

**原型與棲地。**沉船巨蛸是八條觸腕張開能蓋住一艘漁船的巨大章魚類魔獸，獨自棲息於西南海岸海崖下的海蝕洞與擱淺的沉船殘骸。

**外觀。**軟滑的身體泛著暗紅與褐色的斑紋，一對金黃的眼睛長在頭側，瞳孔是一道橫縫。八條觸腕粗如船纜，內側排滿兩列碗口大的吸盤，腕根之間藏著一張鉤狀的硬喙。

**生態與在地關係。**牠白天縮在海蝕洞深處或沉船的船艙裡，夜裡伸出觸腕，在礁石間摸找蟹、魚與貝類。南潮港一帶的漁家熟知哪幾處海蝕洞有牠出沒，收漁籠時會繞開那些洞口。首隻指定個體盤踞在一艘舊商船的殘骸裡，總是纏著船上那具生鏽的大錨，被稱為「沉錨」。

**戰鬥中的表現。**牠能以水屬性力量讓海水沿著觸腕裹成一層沉重的水套，離開海面一整個潮汐仍保持濕潤。絞纏集中於單一對手；橫掃則甩開全部觸腕，撞向每個敵對身影，撞擊分別落在每個身影身上。兩者都耗費牠自身的魔力與體力，耗盡時牠以觸腕與硬喙應戰。

| 變體 | 核准方向 |
| --- | --- |
| 沉骸型 | 普通版本，長年盤踞在海蝕洞或沉船殘骸裡的成年個體 |

**委託背景示例。**南潮港東邊海崖下的沉船附近，這個月接連有四艘小漁船的纜繩被扯斷，漁籠整排失蹤。漁會判定是沉錨把覓食範圍擴到了漁船的泊位，向公會正式張貼討伐委託，請熟練的隊伍前往處理。
````

- `docs/development/bestiary-editorial-review.md`: append one row: `| `wreck_arm_octopus` | <implementation date> | read against the registry's published ecology field; the trouble is one octopus beside the moorings and trap lines near a cliff-foot wreck, local and avoidable, the water power acts on the sleeves of its own arms, and the local name 「沉錨」 is an observation rather than a new naming tradition | checked against the declared kit: the arm bind is a single-target water-element physical strike and the arm sweep reaches every eligible enemy with its own hit and defense outcome, both spend the octopus's own magic and stamina once per cast, and the section names no command, buff identifier or resource field | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: the affirmative prose describes bodies and observed behaviour, and narrative, boundary and delivery status agree |`. Replace `<implementation date>` with the implementation date in `YYYY-MM-DD` form. Keep exactly six cells and put no `|` inside a cell. The reviewer may reword a cell after actually reading the section.

### D7. Tests

- No test file changes. Narration coverage, the kit contract and the composition-group derivation already include the new rows.

### D8. Developer review section

Append `## 沉船巨蛸` to `docs/development/monster-content-expansion.md`, with these subsections:

- `### Role constraints and the chosen literals`. State the following relations, not a value table:
* Reach-heavy sea-cave boss: agility above the high band's floor, defense in its lower part, hit points between the boar's and the turtle's.
* MP holds one bind plus two sweeps (12 + 16 + 16 = 44 ≤ 48); SP holds three of the larger casts.
* Costs and coefficients repeat the boar's and the turtle's single-plus-area shape; the element is water, as for the crocodile's bite.
* Grade B: a dangerous site boss, below the A-grade 蓄潮型.
- `### Reuse of the two-strike (single + area damage) representative`: the signature, the unchanged representative `warm_den_boar`, and the existing module that exercises the group.
- `### Decision mode`: legacy, the archetype named in D2, and the flee threshold that archetype carries. State D2's deviation: the archetype is `ambush_predator` rather than `pack_hunter` because the deterministic `first_owned` choice keeps `wreck_arm_bind` ahead of the innate `basic_attack`, `lowest_hp` targeting and the 0.20 flee threshold are preserved, and the legacy body therefore does not select the area sweep.
- `### Focused commands and results`: the Verification commands and their observed results.
- `### Human review of the prose`: the prose was transcribed from this design and is pending human editorial review in the ledger.

## Risks / Trade-offs

- [A later key sorts before a representative] → every Wave 1, Wave 2, Wave 3 and Wave 4 key was chosen to sort after its group's representative. A rename must keep that order, or it must move the representative declaration.
- [Fingerprint churn across the serial species chain] → D5 runs on every link. Only links that add a buff or modifier move the fingerprint.

## Verification

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. From the repository root, run each label alone with `uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`: `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_monster_visuals`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_ember_bristle_boar_resource_skill`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.skills.tests.test_narration_catalog`, `world.skills.tests.test_skill_registry.test_out_of_combat_policy`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `world.rules.tests.test_monster_ai_activation.ActivationBindingTests`, `world.rules.tests.test_monster_ai_activation.RollbackTests`. Then run `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"`, `uv run --locked python -m tools.map_reference_context` followed by `--check`, `uv run --locked python -m tools.contract_gate --change wreck-arm-octopus-species` and `openspec validate wreck-arm-octopus-species --strict`.
