## Why

This is roadmap item #2 (design doc §11), depending on change 1
(`bootstrap-container-evennia`). Nothing in Phase 1 onward can be built without it: `entity-traits`
(change 3) needs `RaceProfile` to derive trait scales, `import-contract` (change 4) needs the race
and skill registries to validate imported characters, and `guild-economy` (change 16) needs
`GuildRank` reward bands and the price table. `world/lore/` is the single typed source of truth the
design doc assigns these consumers to read from instead of hardcoding magic numbers (§5.1). Right
now that source of truth exists only as free-form Traditional Chinese prose in
`tmp/story_settings/world_info.md`, which is gitignored, not typed, and not importable by any other
module.

## What Changes

- Add `world/lore/` as frozen-dataclass registries derived from `world_info.md`, per design doc
  §5.1 and D9 (lore is Python, not YAML):
  - `RaceProfile` (human / beastfolk / elf) with the exact field list from §5.1 — `key`,
    `lifespan`, `magic_cap`, `vital_baseline`, `static_baseline`, `learning_multiplier`,
    `can_use_divine_arts` — the single place that encodes the power gap between the three races.
    `vital_baseline` (HP/MP/SP pools) and `static_baseline` (atk_phys/agility/defense) scale by
    different factors (~100× and ~10× human-to-elf respectively) and neither is derived from the
    other.
  - `StaticTier` — a new registry recording the named power bands within each race's
    `static_baseline` (human 平民→大劍豪, beastfolk 幼年→獸王級, elf 一般→異數), since
    `world_info.md` specifies human and beastfolk combat strength as tiered distributions, not a
    single flat band.
  - `Subrace` — a new registry (not named in §5.1, needed to model the elf three-branch split the
    import contract's reference example already assumes `subrace: "ciaran"` exists for). Covers
    the three elf branches (Fionnen/Ciaran/Eolas) and the seven named beastfolk subspecies, and now
    also carries each beastfolk subspecies' documented stat-distribution skew (e.g. 貓人 favors
    `agility`, penalizes `defense`) and, for 狐人, an override of the species MP vital band.
  - `Element` (八元素: 火水風土雷冰光暗).
  - `MagicTier` (初級/中級/高級/超級/究極) with non-overlapping level bands.
  - `RankTitle` (學徒/術師/大師/賢者/主宰).
  - `Nation` (格蘭迪亞帝國 / 阿爾托利亞王國 / 瓦爾哈拉獸王國).
  - `GuildRank` (F–S) with reward bands.
  - `MonsterTier` (F-E / D-C / B-A / 災厄級), with physical-stat and HP bands derived from
    `world_info.md`'s guild-rank-to-monster correspondence, so change 3 can instantiate `Monster`
    entities without inventing numbers of its own.
  - `Anchor` (three capitals, three elven villages, three known dungeons — 永夜迷宮 80F, 龍之巢穴
    50F, 魔導遺跡 60F).
  - Currency stored as an integer count of 銅 (1 金 = 100 銀 = 10000 銅), plus the purchasing-power
    price table from `world_info.md`. No floats anywhere in the money path.
- Add `world/lore/sync.py`: an idempotent startup sync that mirrors every registry entry into the
  DB (one Evennia `Script` row per entry, get-or-created and overwritten by `key`), wired into the
  Evennia server-start hook scaffolded by change 1.
- Add a self-consistency test suite: registry membership checks, the race power-gap assertion,
  magic-tier band contiguity, guild-rank band ordering, currency conversion correctness, and
  sync idempotency (running the sync twice creates no duplicate rows).

## Capabilities

### New Capabilities
- `lore-registries`: the frozen-dataclass registries themselves — `RaceProfile`, `StaticTier`,
  `Subrace`, `Element`, `MagicTier`, `RankTitle`, `Nation`, `GuildRank`, `MonsterTier`, `Anchor`,
  and the currency/price-table module — derived from `world_info.md` and internally self-consistent.
- `lore-startup-sync`: the idempotent mechanism that mirrors every registry entry into the DB at
  Evennia server start, keyed by `key`, safe to run on every restart without duplicating rows.

### Modified Capabilities
- None. `openspec/specs/` is currently empty (change 1 has not been archived yet).

## Impact

- **New files**: `world/lore/__init__.py`, `world/lore/races.py`, `world/lore/elements.py`,
  `world/lore/magic.py`, `world/lore/nations.py`, `world/lore/guild.py`, `world/lore/monsters.py`,
  `world/lore/anchors.py`, `world/lore/economy.py`, `world/lore/sync.py`, and a
  `world/lore/tests/` package.
- **Modified files**: `server/conf/at_server_startstop.py` (scaffolded empty by change 1's
  `evennia --init`) — its `at_server_start()` hook gains one call to `world.lore.sync.sync_all()`.
- **No modification** to `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`.
- **Depends on** change 1 for the Evennia project skeleton and the pinned Evennia 6.1.0 dependency
  the sync mechanism runs against.
- **Consumers deferred to later changes**: this change does not implement the overwhelm threshold,
  guild-rank reward *validation* logic, or import-schema enforcement — only the typed data those
  consumers will read. Change 3 (`entity-traits`), change 4 (`import-contract`), and change 16
  (`guild-economy`) own that logic.
