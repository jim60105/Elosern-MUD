## 1. Package layout

- [ ] 1.1 Confirm `world/lore/` exists as an empty stub package from change 1; add
      `world/lore/tests/__init__.py`.
- [ ] 1.2 Create `world/lore/races.py`, `elements.py`, `magic.py`, `nations.py`, `guild.py`,
      `monsters.py`, `anchors.py`, `economy.py`, `sync.py` as empty modules with module docstrings
      referencing design doc §5.1 and this change.

## 2. Races and subraces (`world/lore/races.py`)

- [ ] 2.1 Define `Vitals` (frozen dataclass: `hp`, `mp`, `sp`, each `tuple[int, int]`) per
      design.md D-2.
- [ ] 2.2 Define `RaceProfile` (frozen dataclass: `key`, `lifespan`, `magic_cap`,
      `vital_baseline`, `learning_multiplier`, `can_use_divine_arts`) per design.md D-1 — exactly
      these six fields, no more.
- [ ] 2.3 Populate `RACE_REGISTRY` with `human`, `beastfolk`, `elf` using the values tabulated in
      design.md D-1 and D-2.
- [ ] 2.4 Define `Subrace` (frozen dataclass: `key`, `race_key`, `display_name_zh`,
      `common_name_zh`, `population`, `home_anchor_key`, `affinity_elements`, `specialty`) per
      design.md D-3.
- [ ] 2.5 Populate `SUBRACE_REGISTRY` with the three elf branches (`fionnen`, `ciaran`, `eolas`)
      and the seven beastfolk subspecies (`wolfkin`, `catkin`, `bearkin`, `rabbitkin`,
      `bovinekin`, `tigerkin`, `foxkin`) per design.md D-3. Elf branches reference
      `home_anchor_key` values that must exist once task 8 populates `ANCHOR_REGISTRY` — sequence
      this after task 8, or forward-declare and verify with the test in task 6.2.

## 3. Elements (`world/lore/elements.py`)

- [ ] 3.1 Define `Element` (frozen dataclass: `key`, `display_name_zh`, `description`) and
      populate `ELEMENT_REGISTRY` with the eight elements (火/水/風/土/雷/冰/光/暗) and their
      one-line English descriptions from `world_info.md`'s 元素類型 list.

## 4. Magic tiers and rank titles (`world/lore/magic.py`)

- [ ] 4.1 Define `MagicTier` (frozen dataclass: `key`, `display_name_zh`, `level_min`,
      `level_max: int | None`, `example_spells_zh`, `description`) and populate
      `MAGIC_TIER_REGISTRY` with the five tiers and the resolved 90/91 boundary per design.md D-5.
- [ ] 4.2 Define `RankTitle` (frozen dataclass: `key`, `display_name_zh`, `order`,
      `unlocks_tier: str | None`, `description`) and populate `RANK_TITLE_REGISTRY` with the five
      titles (學徒/術師/大師/賢者/主宰) per design.md D-5.

## 5. Nations, guild ranks, monster tiers, anchors

- [ ] 5.1 Define `AnchorKind` (`StrEnum`: `CAPITAL`, `ELVEN_VILLAGE`, `DUNGEON`) and `Anchor`
      (frozen dataclass: `key`, `kind`, `display_name_zh`, `nation_key: str | None`,
      `population: int | None`, `floors: int | None`, `description`) in `world/lore/anchors.py`.
      Populate `ANCHOR_REGISTRY` with the three capitals, three elven villages, and three known
      dungeons (永夜迷宮 80F, 龍之巢穴 50F, 魔導遺跡 60F) per design.md D-7, including the 永夜迷宮
      nominal-jurisdiction judgment call.
- [ ] 5.2 Define `Nation` (frozen dataclass: `key`, `display_name_zh`, `capital_anchor_key`,
      `government`, `dominant_race`, `population`, `territory_share`, `ruler_zh`,
      `military_notes`, `notes`) in `world/lore/nations.py`. Populate `NATION_REGISTRY` with
      格蘭迪亞帝國, 阿爾托利亞王國, 瓦爾哈拉獸王國 from `world_info.md`'s 國家與政治 section.
- [ ] 5.3 Define `GuildRank` (frozen dataclass: `key`, `order`, `reward_min_copper: int`,
      `reward_max_copper: int | None`, `description`) in `world/lore/guild.py`. Populate
      `GUILD_RANK_REGISTRY` with F through S using the corrected copper conversion in design.md
      D-6 (`1金=100銀=10000銅`); the resulting ladder is strictly increasing and non-degenerate
      across all seven ranks (F 10–100, E 100–500, D 500–5,000, C 5,000–50,000, B 50,000–500,000,
      A 500,000–5,000,000, S 5,000,000+).
- [ ] 5.4 Define `MonsterTier` (frozen dataclass: `key`, `display_name_zh`, `guild_rank_range`,
      `example_monsters_zh`, `description`) in `world/lore/monsters.py`. Populate
      `MONSTER_TIER_REGISTRY` with the four bands (F-E, D-C, B-A, 災厄級) and their example
      monsters from `world_info.md`'s 魔獸 section.

## 6. Currency and price table (`world/lore/economy.py`)

- [ ] 6.1 Define `COPPER_PER_SILVER = 100` and `COPPER_PER_GOLD = 10000` as module-level integer
      constants (the corrected rate — see design.md D-6), and
      `to_copper(gold: int = 0, silver: int = 0, copper: int = 0) -> int`.
- [ ] 6.2 Define `PriceEntry` (frozen dataclass: `key`, `display_name_zh`, `min_copper: int`,
      `max_copper: int | None`, `notes`) and populate `PRICE_TABLE` with the seven purchasing-power
      references from `world_info.md`'s 經濟與貨幣 section (inn stay, meal, potion, plain sword,
      magic weapon, commoner annual income, adventurer annual income), converted at the same
      corrected rate as `GuildRank` (design.md D-6).

## 7. Package exports

- [ ] 7.1 `world/lore/__init__.py` re-exports every public dataclass and registry constant from
      the modules above, so consumers can `from world.lore import RACE_REGISTRY` etc. without
      knowing the internal module split.

## 8. Idempotent startup sync (`world/lore/sync.py`)

- [ ] 8.1 Verify, against the installed Evennia 6.1.0 (pinned by change 1), that
      `server/conf/at_server_startstop.py` exists with an `at_server_start()` hook, and that
      `evennia.utils.create.create_script()` / `evennia.utils.search.search_script()` behave as
      design.md D-8 assumes. Adjust the design note in this file if reality differs.
- [ ] 8.2 Define a minimal `LoreRecord(DefaultScript)` typeclass (no ticking/interval behavior)
      whose `.db.category` and `.db.fields` hold a synced entry's data.
- [ ] 8.3 Implement `sync_one(category: str, key: str, entry: Any) -> None` — get-or-create a
      `LoreRecord` keyed `f"lore:{category}:{key}"`, then unconditionally overwrite `.db.fields`
      with `dataclasses.asdict(entry)`.
- [ ] 8.4 Implement `sync_all() -> None` iterating all ten registries (`RACE_REGISTRY`,
      `SUBRACE_REGISTRY`, `ELEMENT_REGISTRY`, `MAGIC_TIER_REGISTRY`, `RANK_TITLE_REGISTRY`,
      `NATION_REGISTRY`, `GUILD_RANK_REGISTRY`, `MONSTER_TIER_REGISTRY`, `ANCHOR_REGISTRY`,
      `PRICE_TABLE`) and calling `sync_one` for every entry.
- [ ] 8.5 Wire a single call to `world.lore.sync.sync_all()` into
      `server/conf/at_server_startstop.py`'s `at_server_start()` hook.

## 9. Self-consistency tests (`world/lore/tests/`)

- [ ] 9.1 `test_races.py` — registry membership (exactly 3 races, exactly 10 subraces), the
      elf/human vitals magnitude assertion, `magic_cap` ordering, every subrace's `race_key`
      resolves, every elf branch's `home_anchor_key` resolves to an `ELVEN_VILLAGE` anchor.
- [ ] 9.2 `test_elements.py` — exactly 8 elements with distinct keys.
- [ ] 9.3 `test_magic.py` — magic tier band contiguity (0/16/31/71/91 seams, no overlap,
      `ultimate.level_max is None`); rank title ordering (1–5, no duplicates) and every non-`None`
      `unlocks_tier` resolves against `MAGIC_TIER_REGISTRY`.
- [ ] 9.4 `test_nations.py` — exactly 3 nations, every `capital_anchor_key` resolves to a
      `CAPITAL` anchor, territory shares sum within the documented bound.
- [ ] 9.5 `test_guild.py` — 7 ranks ordered 1–7, `reward_min_copper` non-decreasing by rank, only
      `S` has `reward_max_copper is None`, no `float` anywhere in the reward fields, **and** the
      reward ladder is strictly increasing and non-degenerate across all seven ranks (every rank's
      `reward_max_copper`, where not `None`, is strictly greater than its own `reward_min_copper`,
      and equals the next rank's `reward_min_copper`) — this is the assertion that caught the
      earlier wrong exchange rate, and it must stay in place to keep catching regressions.
- [ ] 9.6 `test_monsters.py` — exactly 4 tiers, `guild_rank_range` values partition
      `GUILD_RANK_REGISTRY`'s keys without gaps, every tier has at least one example monster.
- [ ] 9.7 `test_anchors.py` — exactly 9 anchors (3/3/3 split by kind), dungeon floor counts
      (80/50/60), elven villages have `nation_key is None`.
- [ ] 9.8 `test_economy.py` — `to_copper` conversion correctness (1 gold = 10,000, 1 silver = 100,
      1 copper = 1), every `PriceEntry` and `GuildRank` reward value is an `int`, every price
      entry's `max_copper >= min_copper` where not `None`.
- [ ] 9.9 `test_sync.py` (Evennia integration test, `EvenniaTest` base) — running `sync_all()`
      twice against a fresh test DB produces no duplicate records and the record count equals the
      total entry count across all ten registries; changing a registry value in a test double and
      re-running sync updates the existing record rather than creating a new one.

## 10. Verification

- [ ] 10.1 Run the full `world/lore/tests/` suite and confirm all tests pass.
- [ ] 10.2 Start the Evennia server (or run the equivalent management command) against a fresh
      database and confirm `sync_all()` runs to completion before the server accepts connections,
      with no errors in `server/logs/`.
- [ ] 10.3 Restart the server against the same database and confirm no duplicate lore records were
      created (row count unchanged from the first start).
- [ ] 10.4 Spot-check three registry values against `tmp/story_settings/world_info.md` by hand
      (e.g. elf lifespan, S-rank reward floor, 永夜迷宮 floor count) to confirm the conversion was
      faithful.
