## Context

The wilderness/Virtual layer is fully deterministic terrain: `ElosernWildernessMapProvider` computes a
region and a flavor description for every coordinate, but nothing ever places a monster there. The
`engage` command and `world.rules.combat_session.engage()` require a living `Monster` object in the
same room, and the onboarding journey (Beat 6) plus the 新手引導 help entry direct players to fight a
low-tier monster right outside the North Gate — so the intro hunt is currently unwinnable through
natural play.

The wilderness uses `evennia.contrib.grid.wilderness`, whose rooms (`TerrainRoom`) are **pooled and
recycled** across coordinates. Objects placed directly into a room would be stranded when the room is
reused elsewhere; the contrib instead tracks every object by coordinate in the script's
`db.itemcoordinates` mapping and re-attaches them to whichever room is active at their coordinate. Any
durable wilderness population must use that mechanism, not room contents.

## Goals / Non-Goals

**Goals:**
- Deterministic, offline-playable wilderness monsters: no LLM, no RNG, no wall-clock, no DB reads in
  the population decision — matching the `region_for_coordinates` / `terrain_description` contract.
- A guaranteed hunting band around `capital_altoria`'s entry point `(60, 100)` that always hosts a
  low-tier monster, so the introductory hunt works immediately after leaving the North Gate.
- Idempotent population: entering a coordinate repeatedly never duplicates monsters; a killed monster
  is respawned deterministically the next time a player activates its coordinate.
- Monsters persist across wilderness room recycling and server restarts.

**Non-Goals:**
- No changes to combat, `engage`, quest, guild, clock, or loot mechanics. An existing wilderness
  monster is engaged and defeated entirely through already-landed systems.
- No text changes: the 新手引導 help entry already names the wilderness hunt correctly; this change
  makes that promise true.
- No loot drops, no monster schedules, no patrol routes, no player-vs-player wilderness rules.

## Decisions

### D-1: Population is owned by `world/maps/`, the wilderness layer's lifecycle owner

The single-writer boundary names `world/maps/` as the sibling package that owns room/instance
lifecycle directly. Wilderness monster presence is a property of the wilderness layer (which rooms
contain which monsters), exactly the room-lifecycle responsibility `world/maps/instance.py` already
exercises when it registers owned entities in instance rooms and clears them on reclaim. Therefore the
pure population model and the spawn/respawn service both live in a new
`world/maps/wilderness_population.py`; no `world/rules/` write path is needed.

Alternative considered: a spawn service under `world/rules/`. Rejected because the wilderness layer is
already a named `world/maps/` ownership area, and splitting the pure model from its only consumer
across packages adds an import seam without a single-writer benefit.

### D-2: A pure closed-form `population_for_coordinates(x, y)` mirrors the terrain model

A frozen `MonsterPopulation(tier: str, name_zh: str)` dataclass plus a pure function. The full
contract, pinned so no implementer discretion remains:

- **Entry point:** a single named constant `CAPITAL_ENTRY_XY = (60, 100)`, read by both the model and
  the tests (which additionally keep one literal assertion that `WILDERNESS_ENTRY_REGISTRY
  ["capital_altoria"].wilderness_xy == (60, 100)`).
- **Region → tier:** an immutable module-level `_REGION_TIER` mapping:
  `western_hills_valleys`, `southwest_coast`, `southeast_coast`, `eastern_plains` → `low`;
  `northwest_highland_forest` → `mid`; `north_deep_forest`, `central_mountains` → `high`.
- **Region → density:** an immutable module-level `_REGION_DENSITY` mapping of 0–10 presence bands:
  `western_hills_valleys` 6, `southwest_coast` 3, `southeast_coast` 3, `eastern_plains` 3,
  `northwest_highland_forest` 7, `north_deep_forest` 8, `central_mountains` 8.
- **Hunting band:** every coordinate with Chebyshev distance ≤ 3 of `CAPITAL_ENTRY_XY` is always
  present at `low` tier, independent of the density formula — so the intro hunt is always reachable.
- **Presence formula (outside the band):** `(x * 92821 + y * 68917) % 10 < _REGION_DENSITY[region]`.
- **Name formula (all branches, band included):** `name_index = (x * 92821 + y * 68917) %
  len(tier.example_monsters_zh)`, selecting `example_monsters_zh[name_index]`.

With the actual `MONSTER_TIER_REGISTRY["low"].example_monsters_zh == ("史萊姆", "哥布林", "巨鼠")`,
the entry coordinate computes `60 * 92821 + 100 * 68917 = 12,460,960`; `12,460,960 % 3 == 1`, so
`population_for_coordinates(60, 100)` returns `MonsterPopulation("low", "哥布林")` — a literal pin
derived from the formula, not special-cased.

Rationale: the wilderness terrain spec already established the closed-form pattern and the `92821` /
`68917` multipliers as the project's deterministic-hash idiom; reusing it keeps "what is here" and
"what it looks like" consistent and testable with literal pins. Pinning the density and tier tables as
immutable constants (not prose) is what actually prevents the "further regions scale" promise from
silently degrading to all-low.

### D-3: Spawn/respawn goes through the wilderness script's `itemcoordinates`, never room contents

`ensure_population(wilderness, coordinates)`:
- Computes `expected = population_for_coordinates(*coordinates)`.
- Lists existing `Monster` objects at that coordinate via `wilderness.get_objs_at_coordinates`.
- **Ownership marker:** every monster this service creates SHALL carry a persistent marker recording
  its coordinate — `monster.db.population_key = "wilderness:{x}:{y}"` — so reconciliation acts only
  on monsters this service owns. This is what keeps the service a bounded map-lifecycle owner rather
  than an implicit owner of every `Monster` that happens to be in a wilderness room: monsters without
  the marker (future scripted encounters, bosses, event content) are never deleted or moved by this
  service.
- If `expected is None`: delete and pop only monsters whose `population_key` matches this coordinate
  (stale-cleanup), leaving foreign monsters untouched.
- If `expected` exists: reconcile to **exactly one** living population monster at the coordinate.
  Delete/pop every other `population_key`-matching monster (dead or surplus living duplicates), then
  create one fresh `Monster` with `threat_tier` set, `apply_monster_tier("floor")` applied,
  `db.population_key` set, registered in `wilderness.db.itemcoordinates[monster] = coordinates`, and
  `.location` set to the room currently active at that coordinate (if any). Idempotency is the special
  case where exactly one living marker-matching monster that still matches the current model (same
  `threat_tier` and key/name) already exists, so no write happens; a marker-matching monster that has
  drifted from the model (wrong tier or name), a dead one, or surplus duplicates are all reconciled
  rather than left stale.

Because the monster is registered by coordinate (not by room), the contrib's room recycling leaves it
in `itemcoordinates` and re-attaches it whenever a room is activated there — persistence across
recycling and restart falls out of the contrib's own bookkeeping. `Monster` needs no `db.skills`:
`basic_attack` is innate on every `LivingEntity`, and `monster_behaviour_policy` selects it directly.

**Write-scope boundary (single-writer):** this service's entire write surface is limited to
population entity creation/deletion, the `population_key` marker, `itemcoordinates` registration,
initial tier traits, and location attachment. Combat outcomes, quest progression, loot, and player
state are written exclusively by their existing deterministic owners (`world/rules/`,
`world/quests/`); the provider hook must never touch them.

Alternative considered: spawning into `room.contents` directly. Rejected — the pooled-room design
makes room-attached objects move or strand incorrectly.

Alternative considered: leaving the ownership marker out and reconciling "any Monster at the
coordinate". Rejected after review — that would silently delete future non-population wilderness
monsters (scripted encounters, bosses), making this map service the de-facto owner of all wilderness
combat entities.

### D-4: The seam is `ElosernWildernessMapProvider.at_prepare_room`

`at_prepare_room(coordinates, caller, room)` already fires on every wilderness entry and step (through
the contrib's `set_active_coordinates`) and again at startup for retained rooms (`sync_wilderness`
re-runs it). Extending it to call `ensure_population(room.wilderness, coordinates)` gives lazy,
deterministic population exactly where players go, plus automatic respawn on re-entry. The call is
guarded so a `TerrainRoom` without a wilderness script (as in the provider's existing unit tests) is a
no-op, preserving those tests unchanged.

The import is deferred inside `at_prepare_room` to avoid a load-time cycle:
`wilderness_population` imports `region_for_coordinates` from `wilderness_provider`.

Alternative considered: hooking the gate exit. Rejected — the gate fires only on entry, missing the
per-step activation that makes respawn and deep-wilderness population work.

## Risks / Trade-offs

- [A player standing still in a room with a freshly killed monster does not see a respawn until they
  step away and back] → Intentional: population is ensured on room activation, which cannot occur
  mid-combat (combat blocks movement) and does not resurrect corpses in the player's face.
- [`get_objs_at_coordinates` is an O(n) scan over `itemcoordinates`] → Acceptable for a single-player
  game with a handful of wilderness occupants; the same scan already runs on every contrib step.
- [Monster keys reuse the example names (哥布林 etc.), so two monsters of one name can exist at
  different coordinates] → Not an ambiguity problem: `CmdEngage` searches within the caller's current
  room, and the model guarantees at most one living population monster per coordinate. Distinct
  coordinates are different rooms.
- [A model change could strand monsters at coordinates that no longer call for them] → Mitigated by
  D-3's stale-cleanup branch, which removes marker-matching monsters wherever
  `population_for_coordinates` now says none — but only when that coordinate is next reconciled;
  coordinates no player revisits keep their monsters until revisited, which is the intended zero-migration
  behavior.
- [The population service could be misread as owning all wilderness combat entities] → Mitigated by
  the `population_key` ownership marker and the explicit write-scope boundary in D-3: only monsters
  this service created are ever reconciled, and combat/quest/loot state stays with existing owners.
- [`sync_wilderness()` re-runs `at_prepare_room` on every retained room at startup, a call path
  distinct from ordinary traversal] → Covered by an explicit startup-sync test that re-runs
  `sync_wilderness()` and asserts no duplicate or replacement of a living population monster.

## Migration Plan

No data migration: the project has zero released users. On deploy, `sync_wilderness` continues to
re-run `at_prepare_room` for retained rooms, so already-active coordinates are populated on the next
startup; new coordinates populate lazily as players explore. Rollback is a revert of the two modules
and the provider edit.

## Open Questions

None.
