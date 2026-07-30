## 1. Package layout

- [x] 1.1 Confirm `world/lore/` exists as an empty stub package from change 1; add
      `world/lore/tests/__init__.py`.
- [x] 1.2 Create `world/lore/races.py`, `elements.py`, `magic.py`, `nations.py`, `guild.py`,
      `monsters.py`, `anchors.py`, `economy.py`, `sync.py` as empty modules with module docstrings
      referencing design doc §5.1 and this change.

## 2. Races, static tiers, and subraces (`world/lore/races.py`)

- [x] 2.1 Define `Vitals` (frozen dataclass: `hp`, `mp`, `sp`, each `tuple[int, int]`) per
      design.md D-2.
- [x] 2.2 Define `StaticBand` (frozen dataclass: `atk_phys`, `agility`, `defense`, each
      `tuple[int, int]`) per design.md D-2b. Do not reuse or derive from `Vitals` — the two scale
      by different factors (~100× vs ~8-10× human-to-elf) and must stay independent types.
- [x] 2.3 Define `RaceProfile` (frozen dataclass: `key`, `lifespan`, `magic_cap`,
      `vital_baseline`, `static_baseline`, `learning_multiplier`, `can_use_divine_arts`) per
      design.md D-1 — exactly these seven fields, no more.
- [x] 2.4 Populate `RACE_REGISTRY` with `human`, `beastfolk`, `elf`. `static_baseline` is now the
      **species-wide floor-to-ceiling band** per design.md D-2b, taken directly from
      `world_info.md`'s 物理數值 blocks: human `(1, 22)`, beastfolk `(4, 34)`, elf `(70, 95)`
      (open-ended above 95 for 精靈中的異數, same treatment as the elf `vital_baseline`). Do not
      derive these from the sample character cards alone — the cards are illustrative examples
      inside the bands, not the bands themselves.
- [x] 2.5 Define `StaticTier` (frozen dataclass: `key`, `race_key`, `display_name_zh`, `order`,
      `band: tuple[int, int | None]`, `guild_rank_hint`, `description`) per design.md D-2c.
- [x] 2.6 Populate `STATIC_TIER_REGISTRY` with the eleven tiers tabulated in design.md D-2c: five
      human (`human_commoner` 1-5, `human_adventurer` 5-9, `human_elite` 7-14, `human_veteran`
      14-18, `human_swordmaster` 18-22), four beastfolk (`beastfolk_juvenile` 4-8,
      `beastfolk_warrior` 10-16, `beastfolk_city_apex` 18-24, `beastfolk_tribal_apex` 26-34), two
      elf (`elf_common` 70-95, `elf_prodigy` 95-open). Set `guild_rank_hint` for the four
      guild-correlated human tiers using the documented range's lower rank (`"F"`, `"C"`, `"A"`,
      and `"S"` respectively) and leave it `None` everywhere else. Note the intentional overlaps in the source data (human adventurer/
      elite bands overlap at 7-9; `beastfolk_city_apex` overlaps `human_swordmaster` at 18-22) —
      do not "fix" these into non-overlapping ranges.
- [x] 2.7 Define `StatModifiers` (frozen dataclass: `atk_phys`, `agility`, `defense`, each `float`
      defaulting to `0.0`) and `Subrace` (frozen dataclass: `key`, `race_key`, `display_name_zh`,
      `common_name_zh`, `population`, `home_anchor_key`, `affinity_elements`, `specialty`,
      `static_modifiers`, `vital_overrides: dict[str, tuple[int, int]] | None = None`) per
      design.md D-3.
- [x] 2.8 Populate `SUBRACE_REGISTRY` with the three elf branches (`fionnen`, `ciaran`, `eolas`,
      each `static_modifiers=StatModifiers()` and `vital_overrides=None`) and the seven beastfolk
      subspecies (`wolfkin`, `catkin`, `bearkin`, `rabbitkin`, `bovinekin`, `tigerkin`, `foxkin`)
      per design.md D-3, with each beastfolk subspecies' `static_modifiers` set from
      `world_info.md`'s 亞種數值傾向 table (design.md D-3's table) — all three axes are now stated
      explicitly for every subspecies: `wolfkin` (0.0, 0.0, 0.0), `catkin` (-0.10, +0.40, -0.30),
      `bearkin` (+0.45, -0.40, -0.05), `rabbitkin` (-0.35, +0.50, -0.15), `bovinekin` (-0.10, -0.35,
      +0.45), `tigerkin` (+0.35, +0.10, -0.45), `foxkin` (-0.05, +0.15, -0.10) — every triple sums
      to exactly `0.0`; do not default any axis to `0.0` from omission, all seven are fully
      specified in the source. Set `foxkin.vital_overrides = {"mp": (50, 70)}`; leave every other
      subrace's `vital_overrides` as `None`. Elf branches reference `home_anchor_key` values that
      must exist once task 5.1 populates `ANCHOR_REGISTRY` — sequence this after task 5.1, or
      forward-declare and verify with the test in task 9.1.

## 3. Elements (`world/lore/elements.py`)

- [x] 3.1 Define `Element` (frozen dataclass: `key`, `display_name_zh`, `description`) and
      populate `ELEMENT_REGISTRY` with the eight elements (火/水/風/土/雷/冰/光/暗) and their
      one-line English descriptions from `world_info.md`'s 元素類型 list.

## 4. Magic tiers and rank titles (`world/lore/magic.py`)

- [x] 4.1 Define `MagicTier` (frozen dataclass: `key`, `display_name_zh`, `level_min`,
      `level_max: int | None`, `example_spells_zh`, `description`) and populate
      `MAGIC_TIER_REGISTRY` with the five tiers and the resolved 90/91 boundary per design.md D-5.
- [x] 4.2 Define `RankTitle` (frozen dataclass: `key`, `display_name_zh`, `order`,
      `unlocks_tier: str | None`, `description`) and populate `RANK_TITLE_REGISTRY` with the five
      titles (學徒/術師/大師/賢者/主宰) per design.md D-5.

## 5. Nations, guild ranks, monster tiers, anchors

- [x] 5.1 Define `AnchorKind` (`StrEnum`: `CAPITAL`, `ELVEN_VILLAGE`, `DUNGEON`) and `Anchor`
      (frozen dataclass: `key`, `kind`, `display_name_zh`, `nation_key: str | None`,
      `population: int | None`, `floors: int | None`, `description`) in `world/lore/anchors.py`.
      Populate `ANCHOR_REGISTRY` with the three capitals, three elven villages, and three known
      dungeons (永夜迷宮 80F, 龍之巢穴 50F, 魔導遺跡 60F) per design.md D-7, including the 永夜迷宮
      nominal-jurisdiction judgment call.
- [x] 5.2 Define `Nation` (frozen dataclass: `key`, `display_name_zh`, `capital_anchor_key`,
      `government`, `dominant_race`, `population`, `territory_share`, `ruler_zh`,
      `military_notes`, `notes`) in `world/lore/nations.py`. Populate `NATION_REGISTRY` with
      格蘭迪亞帝國, 阿爾托利亞王國, 瓦爾哈拉獸王國 from `world_info.md`'s 國家與政治 section.
- [x] 5.3 Define `GuildRank` (frozen dataclass: `key`, `order`, `reward_min_copper: int`,
      `reward_max_copper: int | None`, `description`) in `world/lore/guild.py`. Populate
      `GUILD_RANK_REGISTRY` with F through S using the corrected copper conversion in design.md
      D-6 (`1金=100銀=10000銅`); the resulting ladder is strictly increasing and non-degenerate
      across all seven ranks (F 10–100, E 100–500, D 500–5,000, C 5,000–50,000, B 50,000–500,000,
      A 500,000–5,000,000, S 5,000,000+).
- [x] 5.4 Define `MonsterTier` (frozen dataclass: `key`, `display_name_zh`, `guild_rank_range`,
      `static_band: StaticBand`, `hp_band: tuple[int, int]`, `example_monsters_zh`, `description`)
      in `world/lore/monsters.py` — import `StaticBand` from `races.py` (design.md D-6b). Populate
      `MONSTER_TIER_REGISTRY` with the four bands (F-E, D-C, B-A, 災厄級), their example monsters
      from `world_info.md`'s 魔獸 section, and the physical/HP bands now specified there:
      `low` (guild F-E, static (3, 8), hp (50, 150)), `mid` (guild D-C, static (12, 20), hp (200,
      400)), `high` (guild B-A, static (22, 35), hp (400, 700)), `calamity` (guild S+, static (60,
      150), hp (1200, 3000)). Populate `static_band` uniformly across `atk_phys`/`agility`/
      `defense` for each tier, matching D-2b's "one shared band across all three stats" convention.
      Do not add loot tables, behaviour, or resistances — those are out of scope (design.md
      Non-Goals); this task is stats only.

## 6. Currency and price table (`world/lore/economy.py`)

- [x] 6.1 Define `COPPER_PER_SILVER = 100` and `COPPER_PER_GOLD = 10000` as module-level integer
      constants (the corrected rate — see design.md D-6), and
      `to_copper(gold: int = 0, silver: int = 0, copper: int = 0) -> int`.
- [x] 6.2 Define `PriceEntry` (frozen dataclass: `key`, `display_name_zh`, `min_copper: int`,
      `max_copper: int | None`, `notes`) and populate `PRICE_TABLE` with the seven purchasing-power
      references from `world_info.md`'s 經濟與貨幣 section (inn stay, meal, potion, plain sword,
      magic weapon, commoner annual income, adventurer annual income), converted at the same
      corrected rate as `GuildRank` (design.md D-6).

## 7. Package exports

- [x] 7.1 `world/lore/__init__.py` re-exports every public dataclass and registry constant from
      the modules above, so consumers can `from world.lore import RACE_REGISTRY` etc. without
      knowing the internal module split.

## 8. Idempotent startup sync (`world/lore/sync.py`)

- [x] 8.1 Verify, against the installed Evennia 6.1.0 (pinned by change 1), that
      `server/conf/at_server_startstop.py` exists with an `at_server_start()` hook, and that
      `evennia.utils.create.create_script()` / `evennia.utils.search.search_script()` behave as
      design.md D-8 assumes. Adjust the design note in this file if reality differs.
- [x] 8.2 Define a minimal `LoreRecord(DefaultScript)` typeclass (no ticking/interval behavior)
      whose `.db.category` and `.db.fields` hold a synced entry's data.
- [x] 8.3 Implement `sync_one(category: str, key: str, entry: Any) -> None` — get-or-create a
      `LoreRecord` keyed `f"lore:{category}:{key}"`, then unconditionally overwrite `.db.fields`
      with a DB-safe `dataclasses.asdict(entry)` representation that recursively converts enum
      members to their string `.value`.
- [x] 8.4 Implement `sync_all() -> None` iterating all eleven registries (`RACE_REGISTRY`,
      `STATIC_TIER_REGISTRY`, `SUBRACE_REGISTRY`, `ELEMENT_REGISTRY`, `MAGIC_TIER_REGISTRY`,
      `RANK_TITLE_REGISTRY`, `NATION_REGISTRY`, `GUILD_RANK_REGISTRY`, `MONSTER_TIER_REGISTRY`,
      `ANCHOR_REGISTRY`, `PRICE_TABLE`) and calling `sync_one` for every entry.
- [x] 8.5 Wire a single call to `world.lore.sync.sync_all()` into
      `server/conf/at_server_startstop.py`'s `at_server_start()` hook.

## 9. Self-consistency tests (`world/lore/tests/`)

- [x] 9.1 `test_races.py` — registry membership (exactly 3 races, exactly 11 static tiers, exactly
      10 subraces), `magic_cap` ordering, every subrace's `race_key` resolves, every elf branch's
      `home_anchor_key` resolves to an `ELVEN_VILLAGE` anchor, every `StaticTier.race_key` resolves
      and its `band` stays within that race's `static_baseline`, human tiers ordered 1–5 reaching
      the species ceiling (22), guild-rank hints present only on the four guild-correlated human
      tiers; **and the two independent scaling-factor assertions from design.md D-2b as separate
      test functions**: (a) the elf/human `vital_baseline` ratio is ~100× (elf `hp[0]` at least 50×
      human `hp[1]`), and (b) the elf/human `static_baseline` ratio is ~8-10× — compared against
      `STATIC_TIER_REGISTRY["human_elite"].band`, **not** `RACE_REGISTRY["human"].static_baseline`
      (elf `atk_phys[0]` between 5× and 15× the human elite tier's `atk_phys` ceiling, per D-2c) —
      written so that a future change deriving one band from the other, or collapsing them to the
      same scale, fails at least one of the two tests; plus every beastfolk subspecies'
      `static_modifiers` matches design.md D-3's table, `wolfkin.static_modifiers == StatModifiers()`,
      elf branches' `static_modifiers == StatModifiers()`, `foxkin.vital_overrides == {"mp": (50,
      70)}`, and every other subrace's `vital_overrides is None`; **and a dedicated assertion that
      every one of the seven beastfolk subspecies' `static_modifiers.atk_phys +
      static_modifiers.agility + static_modifiers.defense` has absolute value at most `1e-12`,
      with no exemption for `foxkin`**
      — this is the invariant design.md D-3 documents as keeping subspecies balanced against each
      other (no subspecies stronger in aggregate, only differently distributed), and it must fail
      if a future subspecies is added, or an existing one edited, without keeping its three axes
      summing to zero. `foxkin`'s vital-band override is checked separately (above) and is not
      part of this sum.
- [x] 9.2 `test_elements.py` — exactly 8 elements with distinct keys.
- [x] 9.3 `test_magic.py` — magic tier band contiguity (0/16/31/71/91 seams, no overlap,
      `ultimate.level_max is None`); rank title ordering (1–5, no duplicates) and every non-`None`
      `unlocks_tier` resolves against `MAGIC_TIER_REGISTRY`.
- [x] 9.4 `test_nations.py` — exactly 3 nations, every `capital_anchor_key` resolves to a
      `CAPITAL` anchor, territory shares sum within the documented bound.
- [x] 9.5 `test_guild.py` — 7 ranks ordered 1–7, `reward_min_copper` non-decreasing by rank, only
      `S` has `reward_max_copper is None`, no `float` anywhere in the reward fields, **and** the
      reward ladder is strictly increasing and non-degenerate across all seven ranks (every rank's
      `reward_max_copper`, where not `None`, is strictly greater than its own `reward_min_copper`,
      and equals the next rank's `reward_min_copper`) — this is the assertion that caught the
      earlier wrong exchange rate, and it must stay in place to keep catching regressions.
- [x] 9.6 `test_monsters.py` — exactly 4 tiers, `guild_rank_range` values partition
      `GUILD_RANK_REGISTRY`'s keys without gaps, every tier has at least one example monster;
      **the guild-rank-to-monster-tier correspondence, not literal values** (design.md D-6b): `low`
      overlaps `human_adventurer`'s static band while beginning below it, `mid` exceeds
      `human_elite`'s, `high` reaches
      or exceeds `human_swordmaster`'s, `calamity` exceeds `elf_common`'s (deliberately, per
      `world_info.md` — assert this overlap holds, do not treat it as a bug to fix); and each
      tier's `hp_band` is within roughly 15-20× its own `static_band` at both ends.
- [x] 9.7 `test_anchors.py` — exactly 9 anchors (3/3/3 split by kind), dungeon floor counts
      (80/50/60), elven villages have `nation_key is None`.
- [x] 9.8 `test_economy.py` — `to_copper` conversion correctness (1 gold = 10,000, 1 silver = 100,
      1 copper = 1), every `PriceEntry` and `GuildRank` reward value is an `int`, every price
      entry's `max_copper >= min_copper` where not `None`.
- [x] 9.9 `test_sync.py` (Evennia integration test, `EvenniaTest` base) — running `sync_all()`
      twice against a fresh test DB produces no duplicate records and the record count equals the
      total entry count across all eleven registries; changing a registry value in a test double
      and re-running sync updates the existing record rather than creating a new one.

## 10. Verification

- [x] 10.1 Run the full `world/lore/tests/` suite and confirm all tests pass.
- [x] 10.2 Start the Evennia server (or run the equivalent management command) against a fresh
      database and confirm `sync_all()` runs to completion before the server accepts connections,
      with no errors in `server/logs/`.
- [x] 10.3 Restart the server against the same database and confirm no duplicate lore records were
      created (row count unchanged from the first start).
- [x] 10.4 Spot-check three registry values against `tmp/story_settings/world_info.md` by hand
      (e.g. elf lifespan, S-rank reward floor, 永夜迷宮 floor count) to confirm the conversion was
      faithful.
