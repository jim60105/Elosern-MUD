## Why

Roadmap item 16 must turn the deterministic quest and combat engines into a complete player-facing
offline game loop. The repository has rank and price lore, persistent wallet and guild seams, and
reserved clock stages, but it has no guild registration, quest board, reward claim, combat-entry
command, rank examination, merchant transaction, or stock-restock behavior.

This is the final deterministic-layer milestone before generative work begins. It must prove that a
player can register, accept and finish a hand-written quest, claim rewards, trade, and earn a rank
promotion while every LLM service is unavailable.

## What Changes

- Add guild registration that always assigns F rank and records the displayed registration stats
  through the existing disguise accessor without exposing disguised values to combat.
- Add a rank-filtered guild quest board, player-facing accept/abandon/list/turn-in commands, and
  all-or-nothing reward settlement for integer copper, item quantities, and guild merit.
- Extend deterministic quest content with immutable rewards, an inventory-backed ACQUIRE objective,
  and per-quest-ID claim records that prevent duplicate payout while preserving quest history.
- Add YAML-tuned merit thresholds and mandatory next-rank combat examinations. Examinations use a
  callable deterministic trigger API so a future validated NPC intent can request the same operation
  without granting `world/ai/` a state-mutating import.
- Add a player combat-session command path that engages a present hostile or examination opponent,
  accepts one player action per ordinary round, uses the selected first action to enter resolver-backed
  overwhelm compression, settles elapsed combat time, and supports nonlethal examination outcomes.
- Add an innate `basic_attack` skill so a character with no imported combat skill can use the combat
  loop; the existing `ActionResolver` remains the sole skill-resolution path.
- Add immutable item/shop definitions, finite persistent merchant stock, integer-copper buy and sell
  transactions, opening hours, and deterministic caravan restocking through the existing ordered
  world-clock stages.
- Add `GuildStaff`, `Merchant`, and `GuildExaminer` components as capability markers and command
  adapters; all mutation remains in the deterministic core.
- Extend the Altoria sample city with permanent guild-hall and general-store interiors containing
  hand-written staff, exam, quest, and shop content.
- Add an offline command-level integration test for registration through rank promotion. No migration
  or backward-compatibility layer is added because the project is unreleased.
- Amend the authoritative engine design with the approved Phase-4 contracts and a future
  `request_guild_exam` NPC intent whose legality is checked by the deterministic exam API.

## Capabilities

### New Capabilities

- `guild-registration`: Guild staff components, F-rank registration, displayed-stat snapshots, and
  membership access rules.
- `guild-quest-board`: Rank-filtered hand-written quest offers and player-facing list, accept,
  abandon, and turn-in interaction.
- `quest-reward-settlement`: Immutable quest rewards, claim state, atomic copper/item/merit payout,
  and inventory-derived ACQUIRE progress.
- `guild-rank-exams`: Merit thresholds, next-rank examination eligibility, deterministic exam
  triggering, nonlethal combat outcome, and rank promotion.
- `player-combat-session`: Player-facing engagement and round orchestration over the existing combat
  and action-resolution engines.
- `shop-economy`: Immutable item/shop catalogs, finite stock, integer-copper buy/sell settlement,
  opening hours, and caravan restocking.

### Modified Capabilities

- `universal-action-ownership`: Add `basic_attack` beside `flee` as an unconditional innate skill.
- `equipment-inventory`: Route item quantity changes through a validated atomic mutation boundary that
  can stage ACQUIRE progress and participate in larger reward/shop transactions.
- `disguised-stats-boundary`: Implement guild registration as one of the three sanctioned display-stat
  consumers while preserving true-stat combat behavior.
- `sample-city-altoria`: Add permanent, idempotently synchronized guild-hall and general-store
  interiors and their hand-written service NPCs without changing the grid street topology.
- `action-resolution-pipeline`: Add side-effect-free player-action preflight and a context-driven
  nonlethal damage projection that emits knockout rather than ordinary defeat before planners run.
- `world-clock`: Distinguish out-of-combat CmdCast command time from combat-session time settled once at
  the terminal combat result.

## Impact

- New deterministic modules under `world/rules/` for guild membership, quest settlement, examinations,
  combat sessions, and economy; new rulebook YAML for merit, exams, prices, hours, and restocking.
- New immutable item and shop content under `world/lore/`, plus project-authored components under
  `typeclasses/` and player commands under `commands/`.
- Additive integration with the change-15 `world/quests/` definitions/runtime, existing combat,
  equipment, clock event-source registry, map bootstrap, and `PlayerCharacter` attributes.
- The quest runtime remains sole owner of quest-record lifecycle data. Cross-surface reward and shop
  operations preflight all writes, use `transaction.atomic()`, and restore Evennia attribute caches on
  failure.
- `world/ai/` remains proposal-only. Change 19 may emit `request_guild_exam`, but only the deterministic
  API validates and applies an eligible request.
- No new runtime dependency or external service is required.
