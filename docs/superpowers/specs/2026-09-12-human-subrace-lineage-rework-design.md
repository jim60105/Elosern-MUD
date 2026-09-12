# Human Subrace Lineage Rework Design

Date: 2026-09-12
Status: approved by the project owner in a brainstorming session (sections 1-5)
Change split: three independent openspec changes —
`human-subrace-lineage-rework` (section 3) →
`subrace-specialty-localization` (section 4) →
`custom-kit-worn-at-activation` (section 5)

## 1. Problem and current state

`SUBRACE_REGISTRY` models the five human groups as `Subrace` entries, structurally
identical to the three elf branches and seven beastfolk subspecies. The five entries
are today:

| key | `display_name_zh` | `common_name_zh` | `specialty` |
| --- | --- | --- | --- |
| `human_royal` | 王族 | 皇族與大貴族 | `Royal blood and high-noble upbringing; education over combat.` |
| `human_noble` | 貴族 | 中小貴族 | `Minor nobility such as 侍從貴族 (薇歐蕾特's attendant 莉茲婭).` |
| `human_wealthy` | 富裕平民 | 商人與高階冒險者 | `Wealthy commoners: big merchants, senior adventurers, mages.` |
| `human_commoner` | 平民 | 普通平民 | `Ordinary commoners: artisans, shopkeepers, adventurers.` |
| `human_laborer` | 底層平民 | 農民與勞工 | `The lower class: farmers and laborers.` |

Five defects, in order of severity.

**1. The taxonomy encodes a wealth ladder, and the vocabulary is discriminatory.**
`world_info.md` derives the split entirely from 社會階層: `富裕平民(大商人、高階冒險者、
魔法師)` over `普通平民(工匠、商人、冒險者)` over `底層平民(農民、勞工)`. 「底層」 places
people at the bottom of a vertical ladder as an identity, and the 「XX平民」 construction
makes 農民 a subordinate tier *of* 平民 — ranking an occupation below the general
population. The project owner rejected this framing outright.

**2. Naming an at-birth category after an occupation is occupational determinism.**
`docs/lore/overview.md:39` states human stats are fixed at birth and never rise. Labelling
such a category 「農民」 asserts that a person is born a farmer. Substituting a different
occupation does not fix this; the naming *axis* is wrong. Beastfolk subspecies avoid the
problem by naming a **physique** (狼人 balanced, 熊人 strength, 兔人 speed) — a wolfkin may
be a warrior or a merchant.

**3. Demographics contradict the lore.** `overview.md:77` makes agriculture the empire's
dominant industry and `overview.md:26` makes the eastern plain fertile farmland. Farmers
should be the *largest* human group, not one-fifth of the population assigned the smallest
starting kit.

**4. English `specialty` prose leaks to players.** `commands/character_creation.py:191`
renders `{display_name_zh}（{common_name_zh}）——{specialty}` and
`web/static/webclient/js/elosern/creation_menu.js:247` uses `entry.specialty` as the menu
description. A player building a character literally sees
`底層平民（農民與勞工）——The lower class: farmers and laborers.` All 15 subraces are
affected, not just the human five. No spec constrains the language of `specialty`, though
`openspec/specs/webclient-character-creation-ui/spec.md:52` already requires the `sex`
labels to be "server-owned Traditional Chinese text derived server-side".

**5. English key and Chinese fields are not synonymous.** `human_laborer` (an occupation)
against 底層平民 (a social stratum); `common_name_zh` holds an occupation list for humans
while it holds a genuine alias for every elf and beastfolk entry.

### Two supporting findings

**The human stat modifiers have no documented source.** `world_info.md` carries a full
〈亞種數值傾向〉 block for beastfolk with design principles and a per-subspecies rationale.
It carries **no equivalent block for humans**. The values in `races.py` were introduced
code-side without lore justification, so they can be re-justified freely.

**Starting kits are a pure affluence gradient.** Measured by `ItemDefinition` rarity:

| subrace | kit | rarity |
| --- | --- | --- |
| `human_royal` | 鍍金軍刀 + 鎖子甲 + 銀髮簪 | U, U, C (3 items) |
| `human_noble` | 騎士制式長劍 + 皮甲 + 銀髮簪 | U, C, C (3 items) |
| `human_wealthy` | 騎士制式長劍 + 鎖子甲 + 銀髮簪 | U, U, C (3 items) |
| `human_commoner` | 普通劍 + 皮甲 | C, C (2 items) |
| `human_laborer` | 木製棍棒 + 皮甲 | C, C (2 items) |

`human_wealthy` receives the same rarity profile as `human_royal`, while the bottom two
receive two COMMON items. The gradient is the wealth axis expressed in loot.

## 2. Constraints settled with the project owner

- **Naming rule.** The English key, `display_name_zh`, and `common_name_zh` MUST all be
  synonymous for every human subrace.
- **No classist or occupationalist vocabulary**, and 農民 must not sit below 平民.
- **No save-data compatibility layer.** There are no existing characters; the database is
  rebuilt. Key renames are a clean breaking change, following the precedent of commit
  `1fa6ea5 feat(traits)!: retype magic_level counter as magic_power static trait`.
- **All 15 `specialty` values** are localized in this effort, not only the human five.
- **Kit items are worn at activation**, not merely granted.

## 3. Change 1 — `human-subrace-lineage-rework`

Re-anchor the three non-noble human subraces from a wealth ladder onto a **geographic
lineage** axis. 王族 and 貴族 remain title-based: they are hereditary offices describing
who governs, not value judgements about persons.

### 3.1 Naming

| current key | new key | `display_name_zh` | `common_name_zh` |
| --- | --- | --- | --- |
| `human_royal` | unchanged | 王族 | 王室血脈 |
| `human_noble` | unchanged | 貴族 | 貴族血脈 |
| `human_wealthy` | `human_coastal` | 濱海民 | 濱海血脈 |
| `human_commoner` | `human_plains` | 平原民 | 平原血脈 |
| `human_laborer` | `human_highland` | 山地民 | 山地血脈 |

coastal/plains/highland map word-for-word onto 濱海/平原/山地, and `common_name_zh` is the
same word plus a 血脈 suffix.

The synonymy rule necessarily compresses `common_name_zh` into a near-duplicate of
`display_name_zh`. Elves can afford an informative pairing (斐歐恩族 / 森林精靈) because a
clan name and an outsiders' name are genuinely two different words; humans have no such
pair. Placing a region name there instead (西部丘陵與谷地) would break synonymy, because a
place is not a group of people. The owner chose to keep the rule and accept the repetition.

**農民 is no longer a subrace.** Farming is an occupation practised within 平原民, the
largest human group — which is also the `StatModifiers()` zero baseline, so the
demographics and the mechanics now agree.

### 3.2 Stat modifiers: values unchanged, rationale rewritten

| subrace | atk_phys / agility / defense | lineage rationale |
| --- | --- | --- |
| 王族 | −5% / −5% / +10% | 王都王室，重統御學識 (plus the existing MP override 120–220) |
| 貴族 | +10% / +5% / −15% | 領地貴族，自幼習劍術馬術 |
| 濱海民 | +5% / +10% / −15% | 港市與海岸，船上作業練就輕捷 |
| 平原民 | 0% / 0% / 0% | 東部平原與城鎮，農耕與工坊並重，人類的基準 |
| 山地民 | +10% / −15% / +5% | 西部丘陵谷地，礦坑與工坊的重勞動 |

All five remain zero-sum. The axis matches the economy already documented in
`overview.md:77`: the empire leads in agriculture (plains), the kingdom in crafts and ore
(hills), and both nations' port cities in maritime trade (coast).

`world_info.md` gains a human 〈數值傾向〉 block mirroring the beastfolk block's format, so
the values stop being undocumented code-side inventions.

### 3.3 Human `specialty` values

```
王族   王都王室的血脈。自幼受統御與學識的教養，長於謀略而非武藝，魔力底蘊高於同族。
貴族   領地貴族的血脈。自幼習劍術與馬術，攻守取捨偏向進取。
濱海民 世居港市與海岸的血脈。船上作業與碼頭往來練就輕捷身手，慣穿輕裝。
平原民 世居平原與城鎮的血脈。農耕與工坊並重，各項資質最為均衡。
山地民 世居丘陵與谷地的血脈。礦坑與工坊的重勞動造就體魄與耐久，不以靈巧取勝。
```

### 3.4 Starting kits

The three commoner lineages receive **three items each with an identical rarity profile**
(all COMMON), differentiated only by the character of the third item. 王族 and 貴族 keep
their UNCOMMON weapons: a 鍍金軍刀 and a 騎士制式長劍 are inherited arms of a house, and
the equality that matters is *among the three commoner lineages*.

| subrace | kit | rarity |
| --- | --- | --- |
| 王族 | 鍍金軍刀 + 鎖子甲 + 銀髮簪 | unchanged (U, U, C) |
| 貴族 | 騎士制式長劍 + 皮甲 + 銀髮簪 | unchanged (U, C, C) |
| 濱海民 | 普通劍 + 皮甲 + **鐵短刀** | C, C, C |
| 平原民 | 普通劍 + 皮甲 + **銀髮簪** | C, C, C |
| 山地民 | 普通劍 + 皮甲 + **狩獵擲斧** | C, C, C |

Each choice quotes the registry's own `summary_zh`: 鐵短刀 is 「王國鍛坊量產的輕便副手短刀」
(port dockhands), 狩獵擲斧 is 「獵手常用的短柄擲斧」 (hill woodland), and 銀髮簪 is
「**市井常見**的細銀髮簪」 — a COMMON everyday item, never a luxury marker.

木製棍棒 disappears from every kit. `great_axe` is not used: it is the UNCOMMON weapon
「熊人戰士慣用」, incongruous for a civilian lineage at +10% atk_phys. `storage_pouch`
(RARE, 帝國壟斷的空間魔法小袋) and `gliding_cloak` (EPIC) were considered and rejected as
far above starting tier.

### 3.5 Files

**Code** — `world/lore/races.py` (five human `Subrace` entries), `world/lore/starting_kits.py:32-36`,
`world/lore/player_presets.py:278` (艾莉莎's subrace).

**Tests** — `world/lore/tests/test_races.py` (`HUMAN_SUBRACES` at 27-33,
`test_human_subraces_exist_with_bloodline_names` at 159-166),
`world/lore/tests/test_player_presets.py` (12 sites),
`world/lore/tests/test_starting_kits.py` (16 sites).

**Data and fixtures** — `world/imports/examples/example_character.json:10`,
`web/browser_support/browser_fixtures_data.py:61` (`SHIPPED_BASE_SUBRACE`).

**Specs and docs** — `openspec/specs/lore-registries/spec.md:115` and `:154`,
`docs/lore/overview.md:39`, `docs/development/adding-player-presets.md:63,76`,
`tmp/story_settings/world_info.md` (lines 42, 141-146, 156, plus the new human
〈數值傾向〉 block).

No `### Requirement:` heading is renamed, so every `@covers_requirement` slug stays valid
and no decorator changes.

### 3.6 Do not touch

These `human_commoner` occurrences name the **`StaticTier`** of that key (the 1–5 physical
band 「平民與非戰鬥者」), an unrelated concept:

`world/lore/races.py:137-138`, `world/lore/npc_tiers.py:41,43,45,46,48` (field
`static_tier_key`), `world/lore/tests/test_races.py:118`,
`world/rules/tests/test_profession_config.py:283,289` (field `default_tier`),
`openspec/specs/entity-trait-scales/spec.md:142-143`.

`web/static/webclient/js/tests/protocol.test.js:3132` also stays: it is a deliberate
synthetic fixture with invented names (竈生民), decoupled from shipped data by design.

Renaming the subrace resolves a pre-existing ambiguity as a side effect — `human_commoner`
currently names two different concepts in two registries, and afterwards means only the
static tier.

## 4. Change 2 — `subrace-specialty-localization`

Rewrite the remaining ten `specialty` values (seven beastfolk, three elf) in Traditional
Chinese, and add a requirement to `lore-registries` that `specialty` SHALL be Traditional
Chinese player-facing prose, locking all 15 entries.

Kept separate from Change 1 because the two have no causal relationship: beastfolk prose
being English is unrelated to human class vocabulary, and the review each needs differs
(translation quality against lore correctness). Change 2's new requirement covers Change
1's output, so this ordering is the natural one.

## 5. Change 3 — `custom-kit-worn-at-activation`

### 5.1 What it reverses

Custom-mode kits are granted unequipped today by explicit decision, not oversight.
`world/rules/character_creation.py:645-646`:

```python
# Custom mode never declares worn gear: the subrace kit stays
# entirely unequipped (preset-starting-equipment non-goal).
starting_equipment: tuple[str, ...] = ()
```

recorded at `openspec/specs/player-character-creation/spec.md:235-236`: "custom-mode
subrace kits are granted entirely unequipped; the player equips those through the ordinary
equipment surface." Changing the behaviour therefore requires a spec change.

### 5.2 Feasibility, verified

All 15 shipped kits were checked for singleton-slot collisions: every kit holds at most one
`weapon_main`, one `weapon_off`, one `armor`, and at most one `accessory` (cap 5). The three
new human kits in section 3.4 are equally clean. No kit needs redesigning.

The wearing machinery already exists and is already specified for presets: declared keys are
applied through `world/rules/equipment.py::toggle_equipment` — the sole equipment writer —
inside the same all-or-nothing activation transaction, after the trait config is applied and
after `inventory` is written, with a rejected toggle rolling the whole activation back.

### 5.3 Implementation

`character_creation.py:646` derives `starting_equipment` from the resolved kit instead of
`()`. Because `_validate_starting_kit` already restricts kits to equipment-only items, the
rule is simply **every kit item is worn**. The existing toggle loop at line 733 is unchanged,
so preset and custom activation share one implementation of wearing, buff attachment, and
gauge-ceiling recomputation.

### 5.4 Required validator hardening

`_validate_preset_starting_equipment` enforces four rules on presets: subset of
`starting_items`, no duplicates, no singleton-slot collision, and no accessory overflow past
`ACCESSORY_MAX_SLOTS`. `_validate_starting_kit` currently enforces only equipment-only and
no-duplicates — it does **not** check slot collisions.

That was harmless while kits went unworn. Once worn, a colliding kit turns from a benign
authoring typo into a failed player activation. The slot and accessory-cap rules must
therefore move into `_validate_starting_kit`, preserving the project's stance that authoring
errors fail at import rather than in front of a player.

### 5.5 Spec changes

Two Requirement bodies change; neither heading is renamed, so no `@covers_requirement`
updates:

- `:205 Preset activation grants the preset's declared starting inventory` — drop
  "custom-mode subrace kits are granted entirely unequipped" from the body.
- `:308 Custom activation grants the chosen subrace's basic starting kit` — the scenario
  `A custom character wakes with its subrace kit` changes `unequipped` to each item
  occupying its resolved slot, and a new scenario covers a colliding kit failing at
  registry load.

### 5.6 Consequence

Custom characters become measurably stronger at creation than before: equipment modifiers,
attached buffs, and gauge ceilings all now apply from the first moment. This is the intended
effect, but it is a balance change rather than a UX polish, and it applies to **all 15
subraces**, not only the human five — which is why it is its own change.

## 6. Rejected alternative: replace `Subrace` with an `Origin` concept

Humans have no biological subspecies; the five groups were a social ladder retrofitted into
the `Subrace` dataclass. Modelling them as a separate `Origin`/`Lineage` concept would be
truer to the fiction.

Rejected as disproportionate. `Subrace` is load-bearing across 21 modules, and
`openspec/specs/character-creation-ux/spec.md:37` requires that no "none"/empty subrace
selection is ever offered — so removing the human subrace would mean rewriting the whole
creation flow. Recorded here so the question is not reopened without new information.

## 7. Migration and data

No compatibility layer, no alias table, no migration script. There are no existing
characters and the database is rebuilt.

One consequence to note: `world/lore/sync.py::sync_all` only creates and overwrites — it
never prunes. Three orphaned `lore:subraces:*` Scripts (`human_commoner`, `human_wealthy`,
`human_laborer`) would survive in any database carried across the rename. Rebuilding the
database removes them. Adding pruning to `sync_all` is a genuine gap in that mechanism but is
out of scope here.

## 8. Testing

The canonical runner is Evennia's, not bare pytest (bare pytest fails with
`ModuleNotFoundError: No module named 'django'` on modules that import
`world/rules/character_creation.py`):

```bash
MUD_TEST_SETTINGS=1 uv run --locked python -m evennia test \
  --settings test_settings.py --noinput world.lore world.rules
uv run --locked python -m tools.spec_traceability check
uv run --locked python -m tools.test_data_lint check
```

Plus a grep sweep confirming `human_wealthy`, `human_laborer`, and the retired Chinese terms
(底層平民, 富裕平民, 農民與勞工, 中小貴族, 皇族與大貴族, 普通平民) reach zero outside
`.worktrees/` and `openspec/changes/archive/`.

Change 3 additionally needs coverage for a custom activation wearing its whole kit, and for a
deliberately colliding kit raising at registry load.
