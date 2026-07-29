## ADDED Requirements

### Requirement: RaceProfile encodes the three-race power gap
`world/lore/races.py` SHALL define a frozen `RaceProfile` dataclass with exactly the fields
`key`, `lifespan`, `magic_cap`, `vital_baseline`, `learning_multiplier`, and
`can_use_divine_arts`, and a module-level `RACE_REGISTRY: dict[str, RaceProfile]` containing
exactly three entries keyed `"human"`, `"beastfolk"`, and `"elf"`.

#### Scenario: Registry has exactly the three documented races
- **WHEN** `RACE_REGISTRY` is inspected
- **THEN** it contains exactly the keys `"human"`, `"beastfolk"`, and `"elf"`, each mapping to a
  `RaceProfile` instance, and no other keys

#### Scenario: Elf sits three orders of magnitude above human on vitals
- **WHEN** `RACE_REGISTRY["elf"].vital_baseline.hp[0]` (the elf HP baseline) is compared against
  `RACE_REGISTRY["human"].vital_baseline.hp[1]` (the human HP gifted ceiling)
- **THEN** the elf value is at least 50 times the human value, reflecting the documented
  100-vs-10000 gap design doc D1 depends on

#### Scenario: Only elves can use divine arts
- **WHEN** `RACE_REGISTRY` is inspected
- **THEN** `can_use_divine_arts` is `True` for `"elf"` and `False` for `"human"` and `"beastfolk"`

#### Scenario: magic_cap ordering matches the documented gap
- **WHEN** the three races' `magic_cap` values are compared
- **THEN** `beastfolk.magic_cap < human.magic_cap < elf.magic_cap`, matching 30 / 90 / 900

### Requirement: Subrace registry covers elf branches and beastfolk subspecies
`world/lore/races.py` SHALL define a frozen `Subrace` dataclass with fields `key`, `race_key`,
`display_name_zh`, `common_name_zh`, `population`, `home_anchor_key`, `affinity_elements`, and
`specialty`, and a module-level `SUBRACE_REGISTRY: dict[str, Subrace]` containing the three elf
branches (`fionnen`, `ciaran`, `eolas`) and the seven named beastfolk subspecies (`wolfkin`,
`catkin`, `bearkin`, `rabbitkin`, `bovinekin`, `tigerkin`, `foxkin`).

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

### Requirement: MonsterTier registry covers the four documented threat bands
`world/lore/monsters.py` SHALL define a frozen `MonsterTier` dataclass and a module-level
`MONSTER_TIER_REGISTRY: dict[str, MonsterTier]` with four entries corresponding to F-E, D-C, B-A,
and 災厄級 (S and above), each carrying example monster names from `world_info.md`.

#### Scenario: Registry has exactly the four threat bands
- **WHEN** `MONSTER_TIER_REGISTRY` is inspected
- **THEN** it contains exactly 4 entries whose `guild_rank_range` values partition
  `GUILD_RANK_REGISTRY`'s keys without gaps (F-E, D-C, B-A, and S-and-calamity)

#### Scenario: Example monsters are non-empty for every tier
- **WHEN** every `MonsterTier` entry is inspected
- **THEN** `example_monsters_zh` contains at least one name drawn from `world_info.md` (e.g.
  史萊姆, 哥布林 for the lowest tier; 古龍, 魔神 for 災厄級)

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
