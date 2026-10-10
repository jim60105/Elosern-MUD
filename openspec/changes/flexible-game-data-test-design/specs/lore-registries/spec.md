# Spec Delta

## MODIFIED Requirements

### Requirement: RaceProfile encodes the three-race power gap
`world/lore/races.py` SHALL define a frozen `RaceProfile` dataclass with exactly the fields `key`, `lifespan`, `vital_baseline`, `static_baseline`, `learning_multiplier`, and `can_use_divine_arts`, and a module-level `RACE_REGISTRY: dict[str, RaceProfile]` containing exactly three entries keyed `"human"`, `"beastfolk"`, and `"elf"`.

#### Scenario: Registry has exactly the three documented races
- **WHEN** `RACE_REGISTRY` is inspected
- **THEN** it contains exactly the keys `"human"`, `"beastfolk"`, and `"elf"`, each mapping to a
  `RaceProfile` instance, and no other keys

#### Scenario: Elf sits roughly two orders of magnitude above human on vital pools
- **WHEN** `RACE_REGISTRY["elf"].vital_baseline.hp[0]` (the elf HP baseline) is compared against
  `RACE_REGISTRY["human"].vital_baseline.hp[1]` (the human HP gifted ceiling)
- **THEN** the elf value is at least 50 times the human value, reflecting the documented
  120-150-vs-10000 gap design doc §5.1 depends on

#### Scenario: Elf sits roughly one order of magnitude above the human elite tier on static stats
- **WHEN** `RACE_REGISTRY["elf"].static_baseline.atk_phys[0]` (the elf `atk_phys` floor) is
  compared against `STATIC_TIER_REGISTRY["human_elite"].band[1]` (the human 精銳-tier `atk_phys`
  ceiling, 14) ;  **not** `RACE_REGISTRY["human"].static_baseline`'s species-wide ceiling, which
  includes the S-rank 大劍豪 tier and would understate the ratio
- **THEN** the ratio is between 5× and 15×, reflecting `world_info.md`'s own worked comparison
  ("對照人類精銳(7-14)約為8-10倍，與設定文字「10倍」相符") ;  and this ratio is checked
  independently of the vital-pool ratio above; neither scenario's assertion may be satisfied by
  deriving one band from the other

#### Scenario: Only elves can use divine arts
- **WHEN** `RACE_REGISTRY` is inspected
- **THEN** `can_use_divine_arts` is `True` for `"elf"` and `False` for `"human"` and `"beastfolk"`

#### Scenario: magic_power band ordering matches the documented gap
- **WHEN** the three races' `static_baseline.magic_power` bands are compared
- **THEN** every upper bound of `beastfolk` is below every lower bound of `human`, and every
  upper bound of `human` is below every lower bound of `elf`, matching the interim table
  and authored band constraints, and no `RaceProfile` field named `magic_cap` or
  `starting_magic_level` exists anywhere in the dataclass

#### Scenario: The fourth band axis is mandatory and integral
- **WHEN** every `StaticBand` instance in the registry modules is inspected
- **THEN** each carries a `magic_power` tuple of two integers with a non-decreasing range, for
  every race baseline and every monster tier band

#### Scenario: StaticBand is four-dimensional
- **WHEN** `StaticBand` is inspected
- **THEN** it is four-dimensional ;  `atk_phys`, `agility`, `defense`, and `magic_power`, each a `tuple[int, int]`

#### Scenario: Race static baselines carry the growth-redesign interim bands
- **WHEN** the three races' `static_baseline` values are inspected
- **THEN** they carry explicit complete authored axis bands; exact endpoints are adjustable game data, with the existing independent power-gap and band-shape constraints retained

#### Scenario: The former magic fields do not exist and the fourth axis is the only bound
- **WHEN** `RaceProfile` is inspected
- **THEN** the former `magic_cap` and `starting_magic_level` fields SHALL NOT exist ;  the fourth `static_baseline` axis is the only race-owned magic-power bound, and no race-owned magic average survives

### Requirement: StaticTier registry records named power bands within each race's static_baseline
`world/lore/races.py` SHALL define a frozen `StaticTier` dataclass with fields `key`, `race_key`, `display_name_zh`, `order`, `band: tuple[int, int | None]`, `magic_band: tuple[int, int]`, `guild_rank_hint`, and `description`, and a module-level `STATIC_TIER_REGISTRY: dict[str, StaticTier]` containing five human tiers, four beastfolk tiers, and two elf tiers.

#### Scenario: Every tier references a real race and stays within that race's static_baseline
- **WHEN** every entry in `STATIC_TIER_REGISTRY` is inspected
- **THEN** each entry's `race_key` exists as a key in `RACE_REGISTRY`, and each entry's `band` falls
  within (or, for the top tier of a race, extends to) that race's `static_baseline` range on every
  combat axis, and each entry's `magic_band` is a subset of that race's
  `static_baseline.magic_power` range

#### Scenario: Human tiers are ordered and reach the species ceiling
- **WHEN** the five human tiers are sorted by `order`
- **THEN** the sequence is 平民與非戰鬥者, 一般冒險者, 精銳, 一流, 大劍豪 with strictly increasing
  `order`, and the highest tier's `band` upper bound equals `RACE_REGISTRY["human"]
  .static_baseline.atk_phys[1]` ;  a human S-rank adventurer is numerically representable, not
  capped out by a narrower species band

#### Scenario: Old magic lore anchors survive as tier magic bands
- **WHEN** `STATIC_TIER_REGISTRY["human_adventurer"].magic_band` is inspected
- **THEN** it is mid-band within the authored human `magic_power` band, and the 平民 tier's `magic_band` lower bound is the race floor while the 大劍豪
  tier's upper bound is the race ceiling ;  the race magic band is spanned deterministically by
  the tier ladder instead of the deleted `starting_magic_level`

#### Scenario: Guild rank hints are present only where world_info.md states them
- **WHEN** every `StaticTier` entry is inspected
- **THEN** `guild_rank_hint` is a non-`None` `GuildRank` key for every human tier above 平民 (F-D,
  C-B, A, S), and `None` for every beastfolk and elf tier, since `world_info.md` does not state a
  guild-rank correlation for those two races; the single-key hints are the lower bound of each
  documented band (`"F"`, `"C"`, `"A"`, and `"S"` respectively)

#### Scenario: An open-ended top tier is representable
- **WHEN** `STATIC_TIER_REGISTRY["elf_prodigy"]` is inspected
- **THEN** its `band` has an authored integral floor and `None` upper bound, where `None` records the source's lack of a hard ceiling,
  while its `magic_band` is a closed two-integer tuple within the elf `magic_power` band (no
  open-ended magic dimension exists)

#### Scenario: A magic_band outside the race band fails registry load
- **WHEN** a `StaticTier` is constructed with a `magic_band` whose endpoints fall outside the
  owning race's `static_baseline.magic_power` band
- **THEN** registry load raises a named error rather than accepting the deviating tier

#### Scenario: Band and magic_band carry their documented roles
- **WHEN** a tier's `band` and `magic_band` fields are inspected
- **THEN** `band` remains the shared physical-power band applied to `atk_phys`/`agility`/`defense`, and `magic_band` is the tier's own deterministic `magic_power` floor-to-ceiling band, replacing the deleted race-level `starting_magic_level` as the source of tier-built NPC and profile magic power

#### Scenario: Registry load validates every magic_band against the race band
- **WHEN** the registry loads
- **THEN** load validates every `magic_band` is a subset of the owning race's `static_baseline.magic_power` band

### Requirement: Subrace registry covers elf branches, beastfolk subspecies, and human bloodline subraces with stat modifiers
`world/lore/races.py` SHALL define a frozen `StatModifiers` dataclass with fields `atk_phys`, `agility`, and `defense` (each a `float` fractional delta, default `0.0`), a frozen `Subrace` dataclass with fields `key`, `race_key`, `display_name_zh`, `common_name_zh`, `population`, `home_anchor_key`, `affinity_elements`, `specialty`, `static_modifiers`, and `vital_overrides`, and a module-level `SUBRACE_REGISTRY: dict[str, Subrace]`.

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
- **WHEN** shipped subrace declarations are validated
- **THEN** Beastfolk static modifiers SHALL retain their documented directional trade-offs and wolfkin zero baseline; exact percentages SHALL be adjustable authoring data.

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
  named after an occupation ;  農民 is an occupation practised within `human_plains`, not a subrace

#### Scenario: Human subrace naming is synonymous across key and Chinese fields
- **WHEN** the five human `SUBRACE_REGISTRY` entries are inspected
- **THEN** `display_name_zh`/`common_name_zh` are exactly 王族/王室血脈, 貴族/貴族血脈,
  濱海民/濱海血脈, 平原民/平原血脈, and 山地民/山地血脈 for `human_royal`, `human_noble`,
  `human_coastal`, `human_plains`, and `human_highland` respectively, and for the three
  geographic lineages the key, `display_name_zh`, and `common_name_zh` are the same word in the
  three forms (coastal/plains/highland ↔ 濱海/平原/山地 ↔ 濱海血脈/平原血脈/山地血脈), the
  `common_name_zh` being `display_name_zh` plus the 血脈 suffix

#### Scenario: Human bloodline stat modifiers keep the documented lineage values
- **WHEN** shipped subrace declarations are validated
- **THEN** Human bloodline modifiers SHALL retain their existing lineage rationale, directional trade-offs, zero-sum discipline and human_plains zero baseline. Royal MP override SHALL remain explicit; exact percentages and pool endpoints SHALL be authoring data.

#### Scenario: Human specialty prose states the lineage and its bent
- **WHEN** the five human `SUBRACE_REGISTRY` entries' `specialty` fields are inspected
- **THEN** they are exactly, verbatim:
  王族 → 「王都王室的血脈。自幼受統御與學識的教養，長於謀略而非武藝，魔力底蘊高於同族。」;
  貴族 → 「領地貴族的血脈。自幼習劍術與馬術，攻守取捨偏向進取。」;
  濱海民 → 「世居港市與海岸的血脈。船上作業與碼頭往來練就輕捷身手，慣穿輕裝。」;
  平原民 → 「世居平原與城鎮的血脈。農耕與工坊並重，各項資質最為均衡。」;
  山地民 → 「世居丘陵與谷地的血脈。礦坑與工坊的重勞動造就體魄與耐久，不以靈巧取勝。」

#### Scenario: Elf branch specialty prose names home, affinity, and art
- **WHEN** the three elf `SUBRACE_REGISTRY` entries' `specialty` fields are inspected
- **THEN** they are exactly, verbatim:
  斐歐恩族 → 「翠綠森林村的森林精靈。親和光屬性魔法，弓術與光法並修，從容而精準。」;
  基亞蘭族 → 「暗影谷村的黑暗精靈。親和火與暗屬性魔法，刀術造詣尤深，攻勢凌厲。」;
  伊歐拉斯族 → 「幽月谷村的幻童精靈。外表永駐童年，親和所有屬性魔法，並擅長神之秘法。」 ; 
  each naming the branch's own village, affinity, and signature art from `world_info.md`'s 三分支
  block, with no occupational determinism

#### Scenario: Beastfolk specialty prose names a physique, its habit, and its tradeoff
- **WHEN** the seven beastfolk `SUBRACE_REGISTRY` entries' `specialty` fields are inspected
- **THEN** they are exactly, verbatim:
  狼人 → 「群居狩獵的狼人，體格均衡而耐力出眾，慣於配合同伴作戰，無突出短板亦無驚人天賦。」;
  貓人 → 「身形輕盈、舉步無聲的貓人，敏捷遠出同族之上，代價是肌骨纖薄，難以吃下正面重創。」;
  熊人 → 「骨架厚重、力大無窮的熊人，慣用重型武器，卻因轉身遲鈍而追不上靈活的對手。」;
  兔人 → 「奔躍如風的兔人，為獸人之中最快的亞種，擅長遊走遠射，卻經不起近身的一擊。」;
  牛人 → 「身軀如山、皮糙肉厚的牛人，防禦最厚而善於陣地戰，只因其行動緩慢而難以追擊機動的敵人。」;
  虎人 → 「爆發力驚人、攻速兼備的虎人，出擊凌厲而防禦為全亞種最弱，講求一擊制敵而非持久消耗。」;
  狐人 → 「體格在獸人之中不突出的狐人，以體力換來同族最深厚的魔力底蘊，是最接近施法者的亞種。」 ; 
  each naming a physique and its habit plus the tradeoff its `static_modifiers` encode, matching
  `world_info.md`'s 「亞種數值傾向」 block, never an occupation as identity

#### Scenario: Every beastfolk subspecies' static_modifiers sum to zero
- **WHEN** every one of the seven beastfolk `SUBRACE_REGISTRY` entries' `static_modifiers` is
  inspected
- **THEN** `abs(atk_phys + agility + defense) <= 1e-12` for every entry, with no exemption for
  `foxkin` ;  its physical-axis modifiers alone already sum to zero (`-0.05 + 0.15 + -0.10 ==
  0.0`); its separate MP vital-band override (below) is a different, independently-checked
  mechanism and is not required to make this sum work; the tolerance accounts only for binary
  `float` representation of the documented decimal percentages

#### Scenario: Foxkin overrides its MP vital band above the species baseline
- **WHEN** shipped subrace declarations are validated
- **THEN** Foxkin SHALL retain an explicit MP vital-band override above its species baseline; exact endpoints SHALL be adjustable data.

#### Scenario: Every other subrace leaves vital_overrides unset
- **WHEN** every `SUBRACE_REGISTRY` entry other than `"foxkin"` and any human bloodline subrace that
  documents a `vital_overrides` band is inspected
- **THEN** `vital_overrides is None` for that entry, meaning it uses `RaceProfile.vital_baseline`
  unmodified

#### Scenario: The registry carries the three elf branches
- **WHEN** `SUBRACE_REGISTRY` is inspected for elven entries
- **THEN** it contains the three elf branches (`fionnen`, `ciaran`, `eolas`)

#### Scenario: The registry carries the seven named beastfolk subspecies
- **WHEN** `SUBRACE_REGISTRY` is inspected for beastfolk entries
- **THEN** it contains the seven named beastfolk subspecies (`wolfkin`, `catkin`, `bearkin`, `rabbitkin`, `bovinekin`, `tigerkin`, `foxkin`)

#### Scenario: The registry carries the five named human bloodline subraces
- **WHEN** `SUBRACE_REGISTRY` is inspected for human entries
- **THEN** it contains the five named human bloodline subraces (`human_royal`, `human_noble`, `human_coastal`, `human_plains`, `human_highland`)

#### Scenario: No subrace selection ever needs a "none" option
- **WHEN** the registry is read as a whole against `RACE_REGISTRY`
- **THEN** every race in `RACE_REGISTRY` has at least one subrace and no player-facing subrace selection ever needs a "none" option

### Requirement: MagicTier bands are contiguous and non-overlapping
`world/lore/magic.py` SHALL define a frozen `MagicTier` dataclass with `level_min` and
`level_max: int | None`, and a module-level `MAGIC_TIER_REGISTRY: dict[str, MagicTier]` with five
entries (`apprentice`/初級, `intermediate`/中級, `advanced`/高級, `superior`/超級,
`ultimate`/究極) whose bands do not overlap.

#### Scenario: Bands cover 0 upward with no gaps or overlaps
- **WHEN** the five tiers are sorted by `level_min`
- **THEN** each tier's `level_min` equals the previous tier's `level_max + 1`,
  and no two tiers' `[level_min, level_max]` ranges overlap

#### Scenario: Ultimate tier is open-ended
- **WHEN** `MAGIC_TIER_REGISTRY["ultimate"]` is inspected
- **THEN** `level_min` follows the previous maximum and `level_max` is `None`; exact internal boundaries are author-adjustable

### Requirement: MonsterTier registry has physical stat and HP bands derived from guild rank
The registry SHALL remain frozen keyed MonsterTier lore data with key, display_name_zh, guild_rank_range, independent-axis static_band, hp_band and example_monsters_zh. It SHALL contain exactly four tiers corresponding to F-E, D-C, B-A and S/calamity, preserving non-empty canonical examples and rank-range partitioning.

#### Scenario: Registry has exactly the four threat bands
- **WHEN** the keyed registry loads
- **THEN** its four guild_rank_range values partition F-E, D-C, B-A and S/calamity without gaps

#### Scenario: Example monsters are non-empty for every tier
- **WHEN** each tier's example list is inspected
- **THEN** it retains at least one canonical example from world_info.md
MonsterTier SHALL retain four keyed threat tiers, their names/examples and guild-rank ranges, with independent HP/attack/agility/defense authored independent-axis bounds and zero magic for current profiles. HP SHALL be independent endurance; no fixed 15-20-times relationship or elf/beastfolk calibration SHALL remain. Calamity upper reference values SHALL be open-ended (None upper limits), without altering human racial/static-tier bounds. Every future concrete monster SHALL have explicit literals and encounter evidence; maximum-axis Cartesian products SHALL NOT imply guaranteed balance.

The exact independent-axis bounds SHALL reside in the authored tier registry without a duplicated numerical table in specs or tests.

These are authoring bounds and reference envelopes, not a guarantee for every Cartesian combination. Taking every axis at its maximum can exceed the intended encounter difficulty. Calamity upper reference values are open-ended for monster classification; this does not open human racial validation bounds. Every future concrete monster still needs explicit literal values and encounter evidence.

High and calamity tiers have no approved existing species in this roster. Their probes below are unshipped representative monsters, not newly authored species. Newly constructed instances use the updated authoritative variant data. No live-instance migration is introduced.

#### Scenario: No ratio requirement
- **WHEN** valid independent axis/HP values do not satisfy legacy HP ratio
- **THEN** they validate under their own ranges

#### Scenario: No new species
- **WHEN** updated envelopes load
- **THEN** no high/calamity species are shipped solely from representative probes

#### Scenario: Each monster tier's static band is beatable by the guild rank that handles it
- **WHEN** authoring classifies encounters relative to the listed equipped skilled human builds
- **THEN** section 8.1 solo/party expectations govern conditional evidence, with no bare-human-band overlap test or universal maximum-axis guarantee

#### Scenario: Calamity-tier monsters deliberately exceed the elf band and this is not corrected away
- **WHEN** an explicit calamity monster has values beyond the upper reference envelopes
- **THEN** open-ended monster bounds accept valid literals without consulting elf/beastfolk targets or changing finite human bounds

#### Scenario: HP bands scale with static bands at the documented ratio
- **WHEN** an authored monster HP is compared with its independent physical axes
- **THEN** the superseded fixed-ratio rule is not enforced; independent endurance and resolver encounter evidence govern authoring

### Requirement: Currency is an integer count of 銅 with no floats in the money path
`world/lore/economy.py` SHALL define `COPPER_PER_SILVER = 100` and `COPPER_PER_GOLD = 10000` as integer constants, a `to_copper(gold: int = 0, silver: int = 0, copper: int = 0) -> int` helper that returns an `int`, and a frozen `PriceEntry` dataclass with integer `min_copper` and `max_copper: int | None` fields.

#### Scenario: Conversion constants match the documented rate
- **WHEN** `to_copper(gold=1)`, `to_copper(silver=1)`, and `to_copper(copper=1)` are each called
- **THEN** they return `10000`, `100`, and `1` respectively, matching "1 金 = 100 銀 = 10000 銅"

#### Scenario: No float ever appears in a currency value
- **WHEN** `to_copper`'s return value and every `PriceEntry.min_copper` / `max_copper` (where not
  `None`) are inspected
- **THEN** every one of them is an `int`

#### Scenario: Price table entries never have max below min
- **WHEN** every `PriceEntry` with a non-`None` `max_copper` is inspected
- **THEN** `max_copper >= min_copper`

#### Scenario: An item naming an absent band fails the catalog load
- **WHEN** an item definition names a price-table key that `PRICE_TABLE` does not define
- **THEN** the shop-catalog load raises for that item rather than defaulting to an unbounded price

#### Scenario: One band serves both mechanical shapes of a category
- **WHEN** a usable item and an equipment item both name the intimacy-device band
- **THEN** both resolve the same `PriceEntry`, so a category's two mechanical shapes never require separate bands

The price registry SHALL retain separate authored `magic_armor`, mundane armor and magic-weapon price bands with integer minima and existing finite/open-ended shape. Exact price endpoints SHALL be mutable data; the currency conversion SHALL remain 10000 copper per gold.

#### Scenario: Enchanted armor has its own price range
- **WHEN** an enchanted armor offer lies within its declared magic_armor band, including above mundane armor maximum
- **THEN** magic_armor validates it without changing mundane armor bounds

#### Scenario: The price table covers every documented purchasing-power reference
- **WHEN** the module-level `PRICE_TABLE: dict[str, PriceEntry]` is inspected
- **THEN** it covers every purchasing-power reference in `world_info.md` (inn stay, meal, potion, plain sword, magic weapon, commoner annual income, adventurer annual income) plus every band the lore item codex assigns to a catalogued item

#### Scenario: The regional-delicacy band separates named local foods
- **WHEN** `PRICE_TABLE` is inspected for local-food pricing
- **THEN** it includes the regional-delicacy band that separates named local foods from an ordinary meal

#### Scenario: The intimacy-device band is shared by both codex shapes
- **WHEN** `PRICE_TABLE` is inspected for intimacy-device pricing
- **THEN** it includes the intimacy-device band shared by the codex's wearable and usable 性玩具 entries

### Requirement: Human lineage renames ship without a save-data compatibility layer
The human subrace rename SHALL remain a clean breaking change without aliases, migration scripts or compatibility handling for retired keys. The unrelated human_commoner StaticTier identity SHALL survive independently of its mutable authored physical band.

#### Scenario: Retired keys resolve nowhere in shipped data
- **WHEN** subrace/preset/starting-kit registries and import/browser fixtures are inspected
- **THEN** no subrace key references human_wealthy, human_laborer or human_commoner and no alias maps a retired key

#### Scenario: The static tier named human_commoner is untouched
- **WHEN** human_commoner StaticTier and static_tier_key/default_tier occurrences resolve
- **THEN** they resolve to the same 平民與非戰鬥者 StaticTier concept using its current authored physical band, not an expected (1,5) table

#### Scenario: The retired keys are exactly the wealth-ladder subrace keys
- **WHEN** rename scope is inspected
- **THEN** only human_wealthy, human_commoner as a subrace key and human_laborer are retired

#### Scenario: Only the new keys are named
- **WHEN** subrace registries, tests, fixtures, presets and docs are inspected
- **THEN** only new subrace keys are named, while unrelated StaticTier meaning stays

#### Scenario: Orphaned Scripts are not pruned and the database is rebuilt
- **WHEN** a database were carried across the rename
- **THEN** it would retain orphaned lore:subraces Scripts because sync creates/overwrites without pruning; the existing rebuild policy remains, with pruning explicitly out of scope
