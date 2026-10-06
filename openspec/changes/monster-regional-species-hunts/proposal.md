## Batch:

- depends-on: monster-quest-objectives (the species-hunt selector, acceptance-time provisioning, and the authored prose fields this change publishes content through), monster-site-placement (the ambient placement rules whose authored capacity constrains each hunt's count), monster-identity-construction (the individual-speed count that makes a hunt's quantity achievable), monster-balance-profiles (the approved profiles and danger grades; a hunt's rating rationale describes a graded encounter, so the numbers must exist first).
- conflicts: file-level, serialized: `world/quests/catalog.py`, `world/rules/rulebook/guild_economy.yaml` `quest_rewards`, `world/rules/tests/test_guild_config/test_catalog_loading.py`'s offer-set assertion, and the new hunt content contract module are shared with `monster-site-clear-out-hunts`, which lands after this change and appends its own definitions and rewards to the same files. `tools/test_data_freeze.json` + `tools/test_data_lint_seed.json` gain this change's contract entry first; the dependent change extends it. `.github/evennia-shards.json` is not touched (package labels `world.quests`, `world.rules`, `commands` already own the modules involved).
- external-prerequisite: user balance approval — GRANTED 2026-10-06 for the twelve first-batch variants (landed by `monster-balance-profiles`) and for the hunts this change publishes. The approved hunts' numbers below are the user's decision and are encoded literally.
- external-prerequisite: the six special abilities still have no executable mechanics owned by other work. This change publishes no ability, registers no skill, and authors no rating rationale or background flavor that asserts an ability's effect: the prose describes group composition, numbers, and terrain, which is what the design says a rating rationale is for.

## Why

`monster-quest-objectives` landed the regional species-hunt semantics, the acceptance-time guarantee, and the three authored prose fields, but its own proposal records the boundary that keeps the shipped catalog tier-based: "the shipped catalog stays tier-based until balance approval lands — this change is the follow-up that publishes species hunts". With the approval landed, four regions have authored ambient placement (eastern plains, northwest highland forest, southwest coast, western hills and valleys) and six species-bearing variants pairs live in them, so an F-to-D member can now be offered a real hunt that names a region, a species, and a countable variant set whose numbers exist. Without this change the machinery has no shipped production content at all, and the placement wave's authored population is reachable only by wandering into it.

## What Changes

- Publish six regional species hunts in `world/quests/catalog.py`, one per (region, species) pair the authored ambient placement covers, each naming its region key, species key, countable variant keys (the ordinary baseline plus the stronger partner, so a qualifying stronger individual counts once), and a count at or below the region's authored per-coordinate legal supply `min(quantity, capacity)`:

  | definition key | region | species | countable variants | count | rank |
  |---|---|---|---|---|---|
  | `eastern_plains_sway_whistle_sparrow` | eastern_plains | sway_whistle_sparrow | grain_pecker, flock_leader | 2 | F |
  | `eastern_plains_ridge_burrow_hare` | eastern_plains | ridge_burrow_hare | burrow_maker, nest_guard | 2 | F |
  | `northwest_highland_forest_fog_mane_lynx` | northwest_highland_forest | fog_mane_lynx | wood_stalker, trail_hunter | 1 | D |
  | `southwest_coast_tide_lamp_crab` | southwest_coast | tide_lamp_crab | shore_walker, reef_warden | 1 | E |
  | `western_hills_valleys_ridge_burrow_hare` | western_hills_valleys | ridge_burrow_hare | burrow_maker, nest_guard | 1 | E |
  | `western_hills_valleys_rock_echo_goat` | western_hills_valleys | rock_echo_goat | cliff_stepper, pass_warden | 1 | D |

  The counts respect the authored ceilings (eastern plains `min(2, 3) = 2`; the other three regions `min(1, 2) = 1`), so no published hunt asks for more than its region's authored placement can legally provision. That is a content rule, not a promise that every acceptance succeeds: the landed guarantee still refuses with its named reason when the world is not provisioned or the region is momentarily at capacity. `southeast_coast` carries no regional hunt: it has no authored ambient rule, so a hunt there could never be satisfied by construction — its only species presence is the boss site, published by `monster-site-clear-out-hunts`.
- Author each hunt's own guild rank, `rating_rationale_zh`, and `background_flavor_zh` as three separate fields, and its hand-written reward in `world/rules/rulebook/guild_economy.yaml` `quest_rewards` (the existing join point), with copper inside the rank's own band. Ranks are authored from the arrangement — group composition, numbers, and terrain — never from a targeted variant's individual danger grade: the two mid-tier hunts are `D` (the rank whose own description is party-based work, matching the approved "a party of ordinary adventurers" calibration) while their strongest countable variants are graded `C`. `background_flavor_zh` carries the bestiary's approved commission-background example for that species (the bestiary's own usage boundary sanctions this and requires the author to supply rank and rating rationale separately); `rating_rationale_zh` states the composition/terrain risk without asserting any special ability's effect, because none has mechanics.
- Make the published-hunt contract durable: a new registered data-contract module asserts that every published regional hunt names a region with an authored ambient rule, that at least one of its ordinary countable variants is in that rule's eligible set, that its count does not exceed `min(quantity, capacity)`, that no hunt exists for a region without an ambient rule, and that each hunt carries its own rank, rationale, flavor, and a rank-banded reward. These are content contracts over the shipped catalog, so the runtime guarantee (which already refuses an illegal hunt at acceptance with a named reason) keeps its single owner.
- Extend the affected contract: `world/rules/tests/test_guild_config/test_catalog_loading.py`'s offer-set assertion moves from `{"introductory_hunt"}` to the seven published definitions, with the new reward rows appended after the existing one so the module's order-dependent `quest_offers[0]` reads keep their subject.
- No production mechanism changes: no new objective field, no new validator branch, no rendering change. The shipped catalog now exercises the landed species-hunt path in production, and `docs/game/commands.md`, `docs/game/command-reference.md` and `tests/test_command_docs.py` stay untouched because the board one-liner and the detail sections render exactly what they already render — only the offers they render change.

## Capabilities

### New Capabilities

- None. (The selector, the acceptance guarantee, the prose fields, and the rendering already exist as `quest-blueprint` and `guild-quest-board` requirements; this change publishes content through them and adds the content contract.)

### Modified Capabilities

- `quest-blueprint`: two added requirements — a published regional hunt must be legally provisionable by its region's authored placement (and regions without placement carry none), and every shipped hunt carries its own rank, rationale, flavor, and rank-banded reward with the rank never derived from a targeted variant's danger grade.

## Impact

- Code: `world/quests/catalog.py` (six definitions appended to `QUEST_CATALOG`), `world/rules/rulebook/guild_economy.yaml` (six appended `quest_rewards` rows), `world/quests/tests/test_hunt_catalog_content.py` (new registered data-contract module), `world/rules/tests/test_guild_config/test_catalog_loading.py` (offer-set assertion).
- Data contracts: `tools/test_data_freeze.json` + `tools/test_data_lint_seed.json` gain the new contract entry with its reason, both files changing together because `seed-mismatch` pins the frozen fields.
- Docs: none. No command, syntax, alias, or rendering changes: the board one-liner and `guild show` sections are unchanged, so `tests/test_command_docs.py` stays green without an edit. `.github/evennia-shards.json` needs no entry (existing package labels).
- Behaviour: an F member's board gains two F hunts and an E member gains two more; a D member gains the two mid-tier hunts. Each acceptance now provisions through the landed ambient owner and refuses with its named reason when the region cannot legally supply the count.
- Downstream: `monster-site-clear-out-hunts` adds the three bound clear-outs on top of this change's catalog, rewards, and content-contract module.
