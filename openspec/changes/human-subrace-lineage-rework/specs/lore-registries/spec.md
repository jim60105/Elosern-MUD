# Delta: lore-registries — human subrace lineage rework

## MODIFIED Requirements

### Requirement: Subrace registry covers elf branches, beastfolk subspecies, and human bloodline subraces with stat modifiers
`world/lore/races.py` SHALL define a frozen `StatModifiers` dataclass with fields `atk_phys`,
`agility`, and `defense` (each a `float` fractional delta, default `0.0`), a frozen `Subrace`
dataclass with fields `key`, `race_key`, `display_name_zh`, `common_name_zh`, `population`,
`home_anchor_key`, `affinity_elements`, `specialty`, `static_modifiers`, and `vital_overrides`, and
a module-level `SUBRACE_REGISTRY: dict[str, Subrace]` containing the three elf branches
(`fionnen`, `ciaran`, `eolas`), the seven named beastfolk subspecies (`wolfkin`, `catkin`,
`bearkin`, `rabbitkin`, `bovinekin`, `tigerkin`, `foxkin`), and the five named human bloodline
subraces (`human_royal`, `human_noble`, `human_coastal`, `human_plains`, `human_highland`), so
that every race in `RACE_REGISTRY` has at least one subrace and no player-facing subrace selection
ever needs a "none" option.

#### Scenario: Every subrace references a real race
- **WHEN** every entry in `SUBRACE_REGISTRY` is inspected
- **THEN** each entry's `race_key` exists as a key in `RACE_REGISTRY`

#### Scenario: Every race has at least one subrace
- **WHEN** each key of `RACE_REGISTRY` is inspected against `SUBRACE_REGISTRY`
- **THEN** for every race key there is at least one `SUBRACE_REGISTRY` entry whose `race_key`
  equals it, including `human`

#### Scenario: Every elf branch has a home village anchor
- **WHEN** `SUBRACE_REGISTRY["fionnen"]`, `["ciaran"]`, and `["eolas"]` are inspected
- **THEN** each has a non-`None` `home_anchor_key` that resolves to an entry in `ANCHOR_REGISTRY`
  whose `kind` is `AnchorKind.ELVEN_VILLAGE`

#### Scenario: Beastfolk subspecies have no fabricated population figures
- **WHEN** the seven beastfolk subspecies entries are inspected
- **THEN** each has `population=None`, since `world_info.md` gives no per-subspecies count

#### Scenario: Elf branches carry no stat-distribution skew
- **WHEN** `SUBRACE_REGISTRY["fionnen"]`, `["ciaran"]`, and `["eolas"]` are inspected
- **THEN** each has `static_modifiers == StatModifiers()` (all fields `0.0`) and
  `vital_overrides is None`, since `world_info.md` documents no per-branch stat skew for elves

#### Scenario: Beastfolk subspecies carry the documented stat-distribution skew
- **WHEN** `SUBRACE_REGISTRY["catkin"]`, `["bearkin"]`, `["rabbitkin"]`, `["bovinekin"]`,
  `["tigerkin"]`, and `["foxkin"]` are inspected
- **THEN** each has all three `static_modifiers` fields matching `world_info.md`'s 「亞種數值傾向」
  block exactly (e.g. `catkin.static_modifiers == StatModifiers(atk_phys=-0.10, agility=0.40,
  defense=-0.30)`), and `wolfkin.static_modifiers == StatModifiers()` (balanced, all zero)

#### Scenario: Human bloodline subraces carry zero-sum stat-distribution skew
- **WHEN** every one of the five human `SUBRACE_REGISTRY` entries' `static_modifiers` is inspected
- **THEN** `abs(atk_phys + agility + defense) <= 1e-12` for every entry, so a bloodline subrace skews
  the three physical axes without shifting aggregate physical power, and the same values are
  justified per-lineage in `world_info.md`'s human 「數值傾向」 block

#### Scenario: Human subrace keys name geographic and hereditary lineages
- **WHEN** `SUBRACE_REGISTRY` is inspected
- **THEN** the human keys are exactly `human_royal`, `human_noble`, `human_coastal`,
  `human_plains`, and `human_highland`; no legacy wealth-ladder key (`human_wealthy`,
  `human_commoner`, `human_laborer`) appears as a subrace key anywhere, and no human subrace is
  named after an occupation — 農民 is an occupation practised within `human_plains`, not a subrace

#### Scenario: Human subrace naming is synonymous across key and Chinese fields
- **WHEN** the five human `SUBRACE_REGISTRY` entries are inspected
- **THEN** `display_name_zh`/`common_name_zh` are exactly 王族/王室血脈, 貴族/貴族血脈,
  濱海民/濱海血脈, 平原民/平原血脈, and 山地民/山地血脈 for `human_royal`, `human_noble`,
  `human_coastal`, `human_plains`, and `human_highland` respectively, and for the three
  geographic lineages the key, `display_name_zh`, and `common_name_zh` are the same word in the
  three forms (coastal/plains/highland ↔ 濱海/平原/山地 ↔ 濱海血脈/平原血脈/山地血脈), the
  `common_name_zh` being `display_name_zh` plus the 血脈 suffix

#### Scenario: Human bloodline stat modifiers keep the documented lineage values
- **WHEN** the five human `SUBRACE_REGISTRY` entries' `static_modifiers` and `vital_overrides`
  are inspected
- **THEN** `human_royal` is `StatModifiers(atk_phys=-0.05, agility=-0.05, defense=0.10)` with
  `vital_overrides["mp"] == (120, 220)`; `human_noble` is `StatModifiers(atk_phys=0.10,
  agility=0.05, defense=-0.15)`; `human_coastal` is `StatModifiers(atk_phys=0.05, agility=0.10,
  defense=-0.15)`; `human_plains` is `StatModifiers()` (the human zero baseline, so the largest
  human group's demographics and mechanics agree); and `human_highland` is
  `StatModifiers(atk_phys=0.10, agility=-0.15, defense=0.05)` — every value unchanged by the
  rename, each carrying the lineage rationale in `world_info.md`'s human 「數值傾向」 block
  (王都王室重統御學識; 領地貴族自幼習劍術馬術; 港市海岸船上作業練就輕捷; 東部平原農耕與工坊
  並重; 西部丘陵谷地礦坑與工坊重勞動)

#### Scenario: Human specialty prose states the lineage and its bent
- **WHEN** the five human `SUBRACE_REGISTRY` entries' `specialty` fields are inspected
- **THEN** they are exactly, verbatim:
  王族 → 「王都王室的血脈。自幼受統御與學識的教養，長於謀略而非武藝，魔力底蘊高於同族。」;
  貴族 → 「領地貴族的血脈。自幼習劍術與馬術，攻守取捨偏向進取。」;
  濱海民 → 「世居港市與海岸的血脈。船上作業與碼頭往來練就輕捷身手，慣穿輕裝。」;
  平原民 → 「世居平原與城鎮的血脈。農耕與工坊並重，各項資質最為均衡。」;
  山地民 → 「世居丘陵與谷地的血脈。礦坑與工坊的重勞動造就體魄與耐久，不以靈巧取勝。」

#### Scenario: Every beastfolk subspecies' static_modifiers sum to zero
- **WHEN** every one of the seven beastfolk `SUBRACE_REGISTRY` entries' `static_modifiers` is
  inspected
- **THEN** `abs(atk_phys + agility + defense) <= 1e-12` for every entry, with no exemption for
  `foxkin` — its physical-axis modifiers alone already sum to zero (`-0.05 + 0.15 + -0.10 ==
  0.0`); its separate MP vital-band override (below) is a different, independently-checked
  mechanism and is not required to make this sum work; the tolerance accounts only for binary
  `float` representation of the documented decimal percentages

#### Scenario: Foxkin overrides its MP vital band above the species baseline
- **WHEN** `SUBRACE_REGISTRY["foxkin"]` is inspected
- **THEN** `vital_overrides` is not `None` and `vital_overrides["mp"] == (50, 70)`, which is a
  higher band than `RACE_REGISTRY["beastfolk"].vital_baseline.mp` ((30, 50)) — confirming a
  subrace can override a vital bound, not only a static one

#### Scenario: Every other subrace leaves vital_overrides unset
- **WHEN** every `SUBRACE_REGISTRY` entry other than `"foxkin"` and any human bloodline subrace that
  documents a `vital_overrides` band is inspected
- **THEN** `vital_overrides is None` for that entry, meaning it uses `RaceProfile.vital_baseline`
  unmodified

## ADDED Requirements

### Requirement: Human starting kits express lineage character, not an affluence ladder
The starting-kit registry SHALL map the five human bloodline subraces to exactly the approved
lineage kits, keyed by the renamed subrace keys: `human_royal` → 鍍金軍刀 + 鎖子甲 +
銀髮簪 (`gilded_saber`, `chainmail`, `silver_hairpin` — UNCOMMON, UNCOMMON, COMMON);
`human_noble` → 騎士制式長劍 + 皮甲 + 銀髮簪 (`knight_blade`, `leather_armor`,
`silver_hairpin` — UNCOMMON, COMMON, COMMON); `human_coastal` → 普通劍 + 皮甲 + 鐵短刀
(`plain_sword`, `leather_armor`, `iron_dagger`); `human_plains` → 普通劍 + 皮甲 + 銀髮簪
(`plain_sword`, `leather_armor`, `silver_hairpin`); `human_highland` → 普通劍 + 皮甲 +
狩獵擲斧 (`plain_sword`, `leather_armor`, `hunting_throwing_axe`). The three commoner-lineage
kits SHALL each hold exactly three COMMON items — identical rarity profiles differentiated only
by the character of the third item (dockside 鐵短刀, everyday 銀髮簪, hill-woodland 狩獵擲斧),
never an affluence gradient. 王族 and 貴族 keep their UNCOMMON inherited arms; the equality
that matters is among the three commoner lineages. `wooden_club` SHALL NOT appear in any kit.
Items rejected on tier or incongruity grounds (`great_axe` — the UNCOMMON bearfolk weapon;
`storage_pouch` — RARE, 帝國壟斷的空間魔法小袋; `gliding_cloak` — EPIC) SHALL NOT appear in
any human kit.

#### Scenario: The five human kits match the lineage table
- **WHEN** the starting-kit registry's human entries are inspected
- **THEN** `human_royal`, `human_noble`, `human_coastal`, `human_plains`, and `human_highland`
  resolve to exactly the item-key sets `("gilded_saber", "chainmail", "silver_hairpin")`,
  `("knight_blade", "leather_armor", "silver_hairpin")`, `("plain_sword", "leather_armor",
  "iron_dagger")`, `("plain_sword", "leather_armor", "silver_hairpin")`, and
  `("plain_sword", "leather_armor", "hunting_throwing_axe")` respectively, with no legacy
  `human_wealthy` / `human_commoner` / `human_laborer` kit keys

#### Scenario: The three commoner lineages are equipotent
- **WHEN** the `human_coastal`, `human_plains`, and `human_highland` kits' items are inspected
  against `ITEM_REGISTRY`
- **THEN** each kit holds exactly three items and every item's rarity is `COMMON`, so no
  commoner lineage starts richer than another

#### Scenario: Wooden club is retired from every kit
- **WHEN** every kit in the starting-kit registry is inspected
- **THEN** no kit contains `wooden_club`

### Requirement: Human lineage renames ship without a save-data compatibility layer
The human subrace rename SHALL be a clean breaking change: no alias table, no migration script,
and no compatibility handling for the retired keys `human_wealthy`, `human_commoner` (as a
subrace key), or `human_laborer`. The registry, tests, fixtures, presets, and docs SHALL name
only the new keys. (Any database carried across the rename would keep the orphaned
`lore:subraces:*` Scripts because `world/lore/sync.py::sync_all` creates and overwrites but
never prunes; the database is rebuilt, and adding pruning to `sync_all` is explicitly out of
scope.)

#### Scenario: Retired keys resolve nowhere in shipped data
- **WHEN** `SUBRACE_REGISTRY`, `PLAYER_PRESET_REGISTRY`, the starting-kit registry, and the
  import/browser fixtures are inspected
- **THEN** none of them references `human_wealthy`, `human_laborer`, or `human_commoner` as a
  subrace key, and no alias mapping resolves a retired key to a new one

#### Scenario: The static tier named human_commoner is untouched
- **WHEN** `STATIC_TIER_REGISTRY["human_commoner"]` and every `static_tier_key`/`default_tier`
  occurrence of `human_commoner` are inspected
- **THEN** they still resolve to the 平民與非戰鬥者 physical band ((1, 5)), because that key
  names the unrelated `StaticTier` concept — after the rename it is the only surviving meaning
  of the string
