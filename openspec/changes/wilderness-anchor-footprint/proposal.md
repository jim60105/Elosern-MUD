# Proposal: wilderness-anchor-footprint

## Why

An anchor currently occupies zero wilderness cells: `WILDERNESS_ENTRY_REGISTRY` maps
`capital_altoria` to a single ordinary wild coordinate `(60, 100)`, and the only way back to the
grid is a hardcoded rule — `WildernessReturnExit.at_traverse` matches `key == "south"` at exactly
that coordinate, and `resolve_wilderness_destination` mirrors the same hardcoded `"s"`. The result
is a phantom city: the wilderness is walkable "over" the city footprint, the gate seems to exist
only from one hardcoded direction, and every presentation surface faithfully renders that broken
world model. The user chose **Model A**: each anchor occupies an authored wilderness FOOTPRINT of
non-walkable cells, with per-FACE gates that are visible and approachable only from their
registered side.

## What Changes

- **BREAKING** (world-data only; the project has no released users, no migration):
  `WildernessEntryPoint` in `world/lore/wilderness_entry.py` becomes a v2 record: an ASCII shape
  mask with an origin cell (mirroring the project's own `altoria_capital.MAPSTR` idiom and the
  Evennia wilderness contrib's pyramid-map example), plus one or more authored GATES. Each gate is
  a face direction + the grid-side destination room `(x, y, z_map_key)`. A point-shape variant
  (no footprint; every direction leads to one exit — the legitimate cave/dungeon semantics) is
  part of the schema.
- `ElosernWildernessMapProvider.is_valid_coordinates` returns false for every footprint cell
  (continent rectangle MINUS all anchor footprints). Evennia's stock per-exit traverse/view locks,
  applied in `WildernessRoom.set_active_coordinates`, then hide and block movement into the
  footprint with no contrib patch.
- Gate visibility: standing at a gate's exterior approach cell, the face-direction exit is the
  return exit (visible, traversable to its registered grid room); from every other cell that
  direction behaves like any other blocked edge into invalid ground.
- **BREAKING**: `WildernessReturnExit.at_traverse` and `resolve_wilderness_destination` are
  generalized from the hardcoded `(coordinate, "s")` pair to registry-driven per-face rules. They
  remain in lockstep (the existing adjacency-truth pinning test keeps them honest).
- `sync_wilderness()` idempotently provisions one grid-side `WildernessGateExit` per registered
  face on its destination room (capital_altoria: north face → 北門 `(2,4)`, south face → 南門
  `(2,0)`); `_grid_room_for_anchor` generalizes to per-face lookup.
- Registry validation rejects malformed authored data before persistence: one origin marker,
  connected footprint inside the continent rectangle, canonical face keys, grid-room targets that
  exist in their map.
- Three contracts pin the old single entry point `(60, 100)` with literal/spec text and re-pin as
  part of this cutover: `wilderness-terrain` (entry-region + description literal pins),
  `wilderness-monster-population` (`CAPITAL_ENTRY_XY`, entry monster pin, hunting-band geometry —
  the band recenters on the north gate's approach cell since the old band would overlap the
  footprint), and `party-system` (companions arrive at the gate's approach cell).

Webclient presentation (footprint cells never rendering as walkable ground, per-gate nodes,
grid-side gate identity) is split into the sibling change
`wilderness-anchor-footprint-local-map`, which depends on this change's registry v2 API.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `wilderness-gateway`: registry entry becomes a v2 footprint-plus-faces record;
  `WildernessReturnExit` routes any registered (approach-cell, face) pair back to its grid room;
  `sync_wilderness()` provisions one grid-side gate per face.
- `wilderness-map-provider`: `is_valid_coordinates` bounds the map to the 224×224 grid minus every
  anchor footprint.
- `canonical-wilderness-destination`: the canonical resolver reads per-face gateway rules instead
  of the single hardcoded south rule.
- `wilderness-terrain`: entry-region and literal-description pins move from `(60, 100)` to
  footprint-derived coordinates (anchor cell plus gate approach cells).
- `wilderness-monster-population`: the entry coordinate and hunting band recenter on the north
  gate's approach cell `(60, 103)`; literal pins re-derived.
- `party-system`: following through the gate delivers companions to the gate's approach cell,
  not a single hardcoded entry coordinate.

## Impact

- Affected code: `world/lore/wilderness_entry.py`, `world/maps/wilderness_provider.py`,
  `world/maps/wilderness_destination.py`, `world/maps/bootstrap.py`, `typeclasses/exits.py`,
  `world/maps/wilderness_population.py` (`CAPITAL_ENTRY_XY`), plus their tests and the
  `.github/evennia-shards.json` manifest if a test module is added.
- Consumer migration (clean cutover, no shim): `typeclasses/exits.py` both lineages,
  `world/maps/wilderness_destination.py` (incl. the `gateway_rule` injection seam), and the
  v1-coordinate test consumers `world/lore/tests/test_wilderness_entry.py`,
  `world/rules/tests/test_{map_knowledge_integration,movement_settlement,party_follow}.py`,
  `world/maps/tests/{test_bootstrap,test_city_wilderness_roundtrip,test_wilderness_population,test_wilderness_provider,test_wilderness_destination}.py`,
  `typeclasses/tests/test_exits.py`.
- Webclient survival minimum: the `entry.wilderness_xy` reads in
  `web/webclient/presentation/local_map.py`, its test seed pin, and
  `web/tests/browser/seed.py` are repointed to the north gate's approach cell so the v2 cut
  never leaves a red build; the per-gate presentation rework stays in the sibling change.
- No player-command surface change: gates are directional exits, so `docs/game/commands.md` and
  `docs/game/command-reference.md` are unchanged (verified during implementation).
- No new dependencies; no contrib patch; stock wilderness machinery (provider validity + per-exit
  locks) carries the boundary semantics.

**Dependency chain:** `wilderness-anchor-footprint` (this) →
`wilderness-anchor-footprint-local-map` (webclient presentation; same file and capability as the
next link) → `webclient-map-scale-legend` (10 km/cell scale note on the expanded overlay). All
three MUST serialize in this order.
