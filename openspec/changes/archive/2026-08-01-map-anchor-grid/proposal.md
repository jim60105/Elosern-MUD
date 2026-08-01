## Why

Design doc §3.2 names `AnchorRoom`/`GridRoom`/`InstanceRoom` as the room typeclasses for three of the
four map layers in D3 ("Anchor (permanent) / Grid (xyzgrid) / Virtual (wilderness) / Instance
(ephemeral, TTL)"), and roadmap item 12 (§11, depends on 2 and 3) is the first change to give the
world any walkable space at all. Two prior changes already exist to build on: change 2
(`lore-world-data`) defined `ANCHOR_REGISTRY` — nine named capitals, elven villages, and dungeons —
and idempotently mirrors it into `LoreRecord` Scripts at every server start; change 3
(`entity-traits`) built `LivingEntity`/`PlayerCharacter`/`NPC`/`Monster`. Neither one, nor anything
since, has created a single `Room` or `Exit` a character could actually stand in. `typeclasses/
rooms.py` is still Evennia's stock `Room(ObjectParent, DefaultRoom): pass`, `world/prototypes.py` is
still the commented-out tutorial stub, and `ANCHOR_REGISTRY`'s nine entries carry no coordinate of any
kind — they are lore facts (population, nation, floor count), not places a character can walk to.
This change closes that gap for one representative anchor, using Evennia's `xyzgrid` contrib (already
verified in the design doc's §4 matrix at the class-import level, and confirmed here at the
call-signature level — `scipy` is already pinned in `pyproject.toml`, satisfying the contrib's one
dependency).

## What Changes

- Add `world/lore/anchor_placement.py::AnchorPlacement` (frozen dataclass: `anchor_key`, `zcoord`,
  `entrance_xy`) and `ANCHOR_PLACEMENT_REGISTRY: dict[str, AnchorPlacement]` — a new, separate,
  keyed registry giving grid coordinates to anchors that have been built into the grid so far. It
  does **not** extend the existing frozen `Anchor` dataclass (`world/lore/anchors.py`, change 2) and
  does not require all nine `ANCHOR_REGISTRY` entries to have a placement; it starts with exactly one
  entry, `capital_altoria`, and is intentionally open for later changes to extend, mirroring the
  "declare a keyed registry, populate later" idiom `settlement-stage-order`'s `_EVENT_SOURCES`
  registry already established.
- Wire `ANCHOR_PLACEMENT_REGISTRY` into change 2's already-landed `world/lore/sync.py::_ALL_REGISTRIES`
  (one dict entry added, `"anchor_placements"`), so it gets the identical idempotent `LoreRecord`
  mirroring every other lore registry already gets — an edit to change 2's implementation file, not
  to its OpenSpec artifacts, the same pattern change 11 (`world-clock`) used on change 8's
  `commands/action.py`.
- Add `typeclasses/rooms.py::GridRoom(XYZRoom)` and `AnchorRoom(GridRoom)`. `GridRoom` carries the
  forward-declared `scene_archetype: str | None` seam design doc D10/§8 requires (unresolved against
  any registry — change 22, `art-queue`, owns that). `AnchorRoom` adds `anchor_key: str | None`,
  resolved against `ANCHOR_REGISTRY` by callers, not enforced at the typeclass level. Neither class
  is spawned via `Room` (the stock class stays as-is for Limbo and other non-grid rooms).
  `InstanceRoom` is **not** forward-declared here — see design.md for why a stub would be a fake
  implementation, not a seam.
- Add `world/prototypes.py::GRID_ROOM` / `ANCHOR_ROOM` module prototypes (`prototype_parent:
  "xyz_room"`, `typeclass` pointed at the two new classes above) so map-definition modules can chain
  `"prototype_parent": "grid_room"` / `"anchor_room"` per coordinate.
- Add `world/maps/` (a new package; design.md records this as an explicit, reasoned addition to
  design doc §3.2's directory layout) containing `altoria_capital.py` (the sample city's `XYMAP_DATA`
  — thirteen rooms: one `AnchorRoom` at the city's central plaza, twelve `GridRoom`s forming gate,
  main streets, and building exteriors — see design.md for the room table) and `bootstrap.py::
  sync_grid()`, the idempotent room/exit instantiation entry point.
- Wire `sync_grid()` into `server/conf/at_server_startstop.py::at_server_start()`, immediately after
  change 2's `sync_all()` — so a freshly-booted container has the sample city fully spawned with no
  manual `evennia xyzgrid` step, relying on `XYMap.spawn_nodes()`/`spawn_links()`'s own documented,
  verified idempotency (each checks for an existing room/exit at the target XYZ before creating one).
  This is named `sync_grid()`, deliberately distinct from change 2's `sync_all()`, because the two do
  different things: `sync_all()` mirrors immutable Python data into `LoreRecord` Scripts;
  `sync_grid()` instantiates real, walkable `ObjectDB` rooms and exits. Conflating the two names is
  exactly the "anchor sync" ambiguity this change must not reproduce.
- Add one ordinary (non-grid) `Exit` linking Limbo (looked up by `key="Limbo"`, never by dbref — see
  design.md D-7 for why the two disagree inside this project's own `EvenniaTest` fixtures) to the
  sample city's south gate coordinate, and a return exit, using the xyzgrid contrib's own documented
  non-grid-to-grid bridging idiom (`open <name>;<aliases> = (x,y,z)`) — created idempotently by
  `sync_grid()` alongside the grid itself, degrading to a logged no-op (never a hard failure) if no
  room keyed `"Limbo"` exists. This is the concrete answer to "how does the sample city connect to the
  rest of the world": today, only through this one authored link from the existing default start area,
  since no wilderness layer (change 13) exists yet to attach to.
- Add `EXTRA_LAUNCHER_COMMANDS["xyzgrid"]` and `PROTOTYPE_MODULES += ["evennia.contrib.grid.xyzgrid.
  prototypes"]` to `server/conf/settings.py` — two settings touched, not two new list entries:
  `PROTOTYPE_MODULES` already defaults to `["world.prototypes"]` (`evennia/settings_default.py`), so
  this appends exactly one new module path rather than re-adding `"world.prototypes"`, which is
  already present. Also add `XYZGridCmdSet` to `commands/default_cmdsets.py::CharacterCmdSet` — the
  contrib's own required installation steps.
  The `evennia xyzgrid <op>` CLI stays available for manual operator use (inspecting or rebuilding the
  grid from a shell) but is not depended on for normal container boot.
- Extend `tests/test_contrib_matrix.py::MATRIX_IMPORTS` with the additional xyzgrid symbols this
  change actually calls (`XYZGrid`, `get_xyzgrid`, `XYMap`) beyond the class-import-only check change
  1 already added for `XYZRoom`/`XYZExit`.

## Capabilities

### New Capabilities
- `anchor-placement`: `AnchorPlacement`, `ANCHOR_PLACEMENT_REGISTRY`, and its idempotent mirroring
  into `LoreRecord` Scripts alongside every other lore registry.
- `grid-room-typeclasses`: `GridRoom`/`AnchorRoom`, the `scene_archetype` and `anchor_key` seams, and
  the explicit non-decision on `InstanceRoom`.
- `grid-room-sync`: `sync_grid()` — idempotent instantiation of real rooms/exits from declared
  `XYMAP_DATA`, its distinctness from change 2's data-mirror `sync_all()`, its automatic invocation at
  server start, and the Limbo bridging exit.
- `sample-city-altoria`: the concrete room/exit inventory of the one sample city this change builds,
  its scope boundaries (exteriors only, no building interiors), and its connection point to the rest
  of the world.

### Modified Capabilities
- None. `lore-registries` (the frozen `Anchor` dataclass and `ANCHOR_REGISTRY`) and `lore-startup-sync`
  (`sync_all()`'s own behavior) are unmodified — this change adds a new registry and a new entry to
  `sync.py`'s internal dict, but does not change either capability's documented requirements or
  scenarios.

## Impact

- New files: `world/lore/anchor_placement.py`, `world/maps/__init__.py`, `world/maps/
  altoria_capital.py`, `world/maps/bootstrap.py`, plus their test modules.
- Edits to already-landed implementation files (not their OpenSpec artifacts): `typeclasses/
  rooms.py` (add two classes), `world/prototypes.py` (add two module prototypes, replacing the inert
  tutorial stub comment), `world/lore/sync.py` (`_ALL_REGISTRIES` gains one entry), `server/conf/
  at_server_startstop.py` (`at_server_start()` gains one call), `server/conf/settings.py` (two new
  settings), `commands/default_cmdsets.py` (one cmdset added), `tests/test_contrib_matrix.py`
  (`MATRIX_IMPORTS` gains one row).
- Reads change 2's `ANCHOR_REGISTRY` (for `anchor_key` validation in tests) and change 2's
  `sync.py` module (extended, not replaced).
- No database migration concerns (project is unreleased, zero users). No change to `START_LOCATION`
  (stays Limbo) — see design.md's Non-Goals for why that is deliberately out of scope here.
