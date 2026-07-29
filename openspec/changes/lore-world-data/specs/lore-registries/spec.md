## ADDED Requirements

### Requirement: RaceProfile encodes the three-race power gap
`world/lore/races.py` SHALL define a frozen `RaceProfile` dataclass with exactly the fields
`key`, `lifespan`, `magic_cap`, `vital_baseline`, `static_baseline`, `learning_multiplier`, and
`can_use_divine_arts`, and a module-level `RACE_REGISTRY: dict[str, RaceProfile]` containing
exactly three entries keyed `"human"`, `"beastfolk"`, and `"elf"`.

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
  ceiling, 14) — **not** `RACE_REGISTRY["human"].static_baseline`'s species-wide ceiling, which
  includes the S-rank 大劍豪 tier and would understate the ratio
- **THEN** the ratio is between 5× and 15×, reflecting `world_info.md`'s own worked comparison
  ("對照人類精銳(7-14)約為8-10倍，與設定文字「10倍」相符") — and this ratio is checked
  independently of the vital-pool ratio above; neither scenario's assertion may be satisfied by
  deriving one band from the other

#### Scenario: Only elves can use divine arts
- **WHEN** `RACE_REGISTRY` is inspected
- **THEN** `can_use_divine_arts` is `True` for `"elf"` and `False` for `"human"` and `"beastfolk"`

#### Scenario: magic_cap ordering matches the documented gap
- **WHEN** the three races' `magic_cap` values are compared
- **THEN** `beastfolk.magic_cap < human.magic_cap < elf.magic_cap`, matching 30 / 90 / 900

### Requirement: StaticTier registry records named power bands within each race's static_baseline
`world/lore/races.py` SHALL define a frozen `StaticTier` dataclass with fields `key`, `race_key`,
`display_name_zh`, `order`, `band`, `guild_rank_hint`, and `description`, and a module-level
`STATIC_TIER_REGISTRY: dict[str, StaticTier]` containing five human tiers, four beastfolk tiers,
and two elf tiers.

#### Scenario: Every tier references a real race and stays within that race's static_baseline
- **WHEN** every entry in `STATIC_TIER_REGISTRY` is inspected
- **THEN** each entry's `race_key` exists as a key in `RACE_REGISTRY`, and each entry's `band` falls
  within (or, for the top tier of a race, extends to) that race's `static_baseline` range on every
  axis

#### Scenario: Human tiers are ordered and reach the species ceiling
- **WHEN** the five human tiers are sorted by `order`
- **THEN** the sequence is 平民與非戰鬥者, 一般冒險者, 精銳, 一流, 大劍豪 with strictly increasing
  `order`, and the highest tier's `band` upper bound equals `RACE_REGISTRY["human"]
  .static_baseline.atk_phys[1]` (22) — a human S-rank adventurer is numerically representable, not
  capped out by a narrower species band

#### Scenario: Guild rank hints are present only where world_info.md states them
- **WHEN** every `StaticTier` entry is inspected
- **THEN** `guild_rank_hint` is a non-`None` `GuildRank` key for every human tier above 平民 (F-D,
  C-B, A, S), and `None` for every beastfolk and elf tier, since `world_info.md` does not state a
  guild-rank correlation for those two races

### Requirement: Subrace registry covers elf branches and beastfolk subspecies with stat modifiers
`world/lore/races.py` SHALL define a frozen `StatModifiers` dataclass with fields `atk_phys`,
`agility`, and `defense` (each a `float` fractional delta, default `0.0`), a frozen `Subrace`
dataclass with fields `key`, `race_key`, `display_name_zh`, `common_name_zh`, `population`,
`home_anchor_key`, `affinity_elements`, `specialty`, `static_modifiers`, and `vital_overrides`, and
a module-level `SUBRACE_REGISTRY: dict[str, Subrace]` containing the three elf branches
(`fionnen`, `ciaran`, `eolas`) and the seven named beastfolk subspecies (`wolfkin`, `catkin`,
`bearkin`, `rabbitkin`, `bovinekin`, `tigerkin`, `foxkin`).

#### Scenario: Every subrace references a real race
- **WHEN** every entry in `SUBRACE_REGISTRY` is inspected
- **THEN** each entry's `race_key` exists as a key in `RACE_REGISTRY`

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

#### Scenario: Every beastfolk subspecies' static_modifiers sum to exactly zero
- **WHEN** every one of the seven beastfolk `SUBRACE_REGISTRY` entries' `static_modifiers` is
  inspected
- **THEN** `atk_phys + agility + defense == 0.0` for every entry, with no exemption for `foxkin` —
  its physical-axis modifiers alone already sum to zero (`-0.05 + 0.15 + -0.10 == 0.0`); its
  separate MP vital-band override (below) is a different, independently-checked mechanism and is
  not required to make this sum work

#### Scenario: Foxkin overrides its MP vital band above the species baseline
- **WHEN** `SUBRACE_REGISTRY["foxkin"]` is inspected
- **THEN** `vital_overrides` is not `None` and `vital_overrides["mp"] == (50, 70)`, which is a
  higher band than `RACE_REGISTRY["beastfolk"].vital_baseline.mp` ((30, 50)) — confirming a subrace
  can override a vital bound, not only a static one

#### Scenario: Every other subrace leaves vital_overrides unset
- **WHEN** every `SUBRACE_REGISTRY` entry other than `"foxkin"` is inspected
- **THEN** `vital_overrides is None`, meaning that subrace uses `RaceProfile.vital_baseline`
  unmodified

### Requirement: Element registry covers the eight documented elements
`world/lore/elements.py` SHALL define a frozen `Element` dataclass and a module-level
`ELEMENT_REGISTRY: dict[str, Element]` containing exactly eight entries corresponding to 火, 水,
風, 土, 雷, 冰, 光, and 暗.

#### Scenario: Registry has exactly eight elements
- **WHEN** `ELEMENT_REGISTRY` is inspected
- **THEN** it contains exactly 8 entries, each with a distinct `key` and a `display_name_zh`
  matching one of 火/水/風/土/雷/冰/光/暗

### Requirement: MagicTier bands are contiguous and non-overlapping
`world/lore/magic.py` SHALL define a frozen `MagicTier` dataclass with `level_min` and
`level_max: int | None`, and a module-level `MAGIC_TIER_REGISTRY: dict[str, MagicTier]` with five
entries (`apprentice`/初級, `intermediate`/中級, `advanced`/高級, `superior`/超級,
`ultimate`/究極) whose bands do not overlap.

#### Scenario: Bands cover 0 upward with no gaps or overlaps
- **WHEN** the five tiers are sorted by `level_min`
- **THEN** each tier's `level_min` equals the previous tier's `level_max + 1` (0, 16, 31, 71, 91),
  and no two tiers' `[level_min, level_max]` ranges overlap

#### Scenario: Ultimate tier is open-ended
- **WHEN** `MAGIC_TIER_REGISTRY["ultimate"]` is inspected
- **THEN** `level_min` is 91 and `level_max` is `None`

### Requirement: RankTitle registry is ordered and references magic tiers
`world/lore/magic.py` SHALL define a frozen `RankTitle` dataclass with an `order: int` field and
an `unlocks_tier: str | None` field, and a module-level `RANK_TITLE_REGISTRY: dict[str, RankTitle]`
with five entries (學徒, 術師, 大師, 賢者, 主宰) ordered 1 through 5.

#### Scenario: Titles are strictly ordered
- **WHEN** `RANK_TITLE_REGISTRY` entries are sorted by `order`
- **THEN** the resulting sequence is 學徒, 術師, 大師, 賢者, 主宰 with `order` values 1 through 5
  and no duplicate `order` values

#### Scenario: Non-apprentice titles reference an existing magic tier
- **WHEN** any `RankTitle` entry with a non-`None` `unlocks_tier` is inspected
- **THEN** `unlocks_tier` exists as a key in `MAGIC_TIER_REGISTRY`

### Requirement: Nation registry covers the three states
`world/lore/nations.py` SHALL define a frozen `Nation` dataclass and a module-level
`NATION_REGISTRY: dict[str, Nation]` containing exactly three entries for 格蘭迪亞帝國,
阿爾托利亞王國, and 瓦爾哈拉獸王國, each referencing its capital by `capital_anchor_key`.

#### Scenario: Each nation's capital anchor resolves
- **WHEN** every `Nation` entry's `capital_anchor_key` is inspected
- **THEN** it exists as a key in `ANCHOR_REGISTRY` and that anchor's `kind` is
  `AnchorKind.CAPITAL`

#### Scenario: Territory shares are documented and bounded
- **WHEN** the three nations' `territory_share` values are summed
- **THEN** the total is between 0.85 and 1.0 (accounting for the unclaimed northern deep forest and
  the neutral central mountain range documented in `world_info.md`)

### Requirement: GuildRank registry provides ordered reward bands in copper
`world/lore/guild.py` SHALL define a frozen `GuildRank` dataclass with `order`,
`reward_min_copper: int`, and `reward_max_copper: int | None`, and a module-level
`GUILD_RANK_REGISTRY: dict[str, GuildRank]` with seven entries (F, E, D, C, B, A, S) ordered 1
through 7.

#### Scenario: Reward bands never decrease going up in rank
- **WHEN** the seven ranks are sorted by `order`
- **THEN** each rank's `reward_min_copper` is greater than or equal to the previous rank's
  `reward_min_copper`

#### Scenario: The reward ladder is strictly increasing and non-degenerate across all seven ranks
- **WHEN** the seven ranks are sorted by `order` and each rank's `reward_min_copper` is compared
  against its own `reward_max_copper` (where not `None`), and against the next rank's
  `reward_min_copper`
- **THEN** every rank's `reward_max_copper` (where not `None`) is strictly greater than its own
  `reward_min_copper` — no rank collapses to a single-value band — and each rank's
  `reward_max_copper` equals the next rank's `reward_min_copper`, forming a continuous, strictly
  increasing ladder from F through S

#### Scenario: Only S rank is open-ended
- **WHEN** all seven `GuildRank` entries are inspected
- **THEN** `reward_max_copper` is a concrete integer for F through A, and `None` only for S

#### Scenario: No floats appear anywhere in a GuildRank's reward fields
- **WHEN** `reward_min_copper` and `reward_max_copper` (where not `None`) are inspected for every
  rank
- **THEN** every value is an `int`, never a `float`

### Requirement: MonsterTier registry has physical stat and HP bands derived from guild rank
`world/lore/monsters.py` SHALL define a frozen `MonsterTier` dataclass with fields `key`,
`display_name_zh`, `guild_rank_range`, `static_band` (a `StaticBand`), `hp_band`, and
`example_monsters_zh`, and a module-level `MONSTER_TIER_REGISTRY: dict[str, MonsterTier]` with four
entries corresponding to F-E, D-C, B-A, and 災厄級 (S and above), each carrying example monster
names from `world_info.md`.

#### Scenario: Registry has exactly the four threat bands
- **WHEN** `MONSTER_TIER_REGISTRY` is inspected
- **THEN** it contains exactly 4 entries whose `guild_rank_range` values partition
  `GUILD_RANK_REGISTRY`'s keys without gaps (F-E, D-C, B-A, and S-and-calamity)

#### Scenario: Example monsters are non-empty for every tier
- **WHEN** every `MonsterTier` entry is inspected
- **THEN** `example_monsters_zh` contains at least one name drawn from `world_info.md` (e.g.
  史萊姆, 哥布林 for the lowest tier; 古龍, 魔神 for 災厄級)

#### Scenario: Each monster tier's static band is beatable by the guild rank that handles it
- **WHEN** each `MonsterTier` entry's `static_band` is compared against the corresponding
  `StaticTier` band from `STATIC_TIER_REGISTRY`
- **THEN** `low`'s band falls inside `human_adventurer`'s band (a novice handles it solo); `mid`'s
  band exceeds `human_elite`'s band (stronger than one veteran, needs a party); `high`'s band
  reaches or exceeds `human_swordmaster`'s band (matches or exceeds the human ceiling); and
  `calamity`'s band exceeds `elf_common`'s band (beyond human scale entirely) — this
  guild-rank-to-monster-tier correspondence, not any single literal number, is the property under
  test

#### Scenario: Calamity-tier monsters deliberately exceed the elf band and this is not corrected away
- **WHEN** `MONSTER_TIER_REGISTRY["calamity"].static_band` is compared against
  `RACE_REGISTRY["elf"].static_baseline`
- **THEN** `calamity`'s band overlaps and extends above the elf band, reflecting `world_info.md`'s
  explicit statement that 古龍/魔神-tier threats are beyond what any human — or even a typical elf —
  can face alone

#### Scenario: HP bands scale with static bands at the documented ratio
- **WHEN** each `MonsterTier` entry's `hp_band` is compared against its own `static_band`
- **THEN** the HP band is within roughly 15-20× the static band at both ends, matching
  `world_info.md`'s stated ratio (and the human reference point: Lidzia's `atk_phys` 8 to `hp` 120
  is 15×)

### Requirement: Anchor registry covers capitals, elven villages, and known dungeons
`world/lore/anchors.py` SHALL define an `AnchorKind` string enum (`CAPITAL`, `ELVEN_VILLAGE`,
`DUNGEON`) and a frozen `Anchor` dataclass, and a module-level `ANCHOR_REGISTRY: dict[str, Anchor]`
with exactly nine entries: three capitals, three elven villages, and three known dungeons.

#### Scenario: Registry has exactly nine anchors of the right kinds
- **WHEN** `ANCHOR_REGISTRY` is inspected
- **THEN** it contains exactly 3 entries with `kind == AnchorKind.CAPITAL`, 3 with
  `kind == AnchorKind.ELVEN_VILLAGE`, and 3 with `kind == AnchorKind.DUNGEON`

#### Scenario: Dungeon floor counts match world_info.md
- **WHEN** the three dungeon anchors are inspected
- **THEN** 永夜迷宮 has `floors == 80`, 龍之巢穴 has `floors == 50`, and 魔導遺跡 has
  `floors == 60`

#### Scenario: Elven villages are not assigned to a nation
- **WHEN** the three elven-village anchors are inspected
- **THEN** each has `nation_key is None`, reflecting `world_info.md`'s description of the central
  mountain range as neutral ground no nation can govern

### Requirement: Currency is an integer count of 銅 with no floats in the money path
`world/lore/economy.py` SHALL define `COPPER_PER_SILVER = 100` and `COPPER_PER_GOLD = 10000` as
integer constants, a `to_copper(gold: int = 0, silver: int = 0, copper: int = 0) -> int` helper
that returns an `int`, a frozen `PriceEntry` dataclass with integer `min_copper` and
`max_copper: int | None` fields, and a module-level `PRICE_TABLE: dict[str, PriceEntry]` covering
every purchasing-power reference in `world_info.md` (inn stay, meal, potion, plain sword, magic
weapon, commoner annual income, adventurer annual income).

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
