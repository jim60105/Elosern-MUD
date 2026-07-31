## 1. Confirmations before writing code

- [ ] 1.1 Confirm `world/lore/anchors.py::ANCHOR_REGISTRY` and `world/lore/sync.py::{LoreRecord,
      _ALL_REGISTRIES, sync_one, sync_all}` still match the shapes design.md's Context section
      describes (change 2, archived) before editing `sync.py`.
- [ ] 1.2 Confirm `typeclasses/rooms.py` still contains only the stock `Room(ObjectParent,
      DefaultRoom): pass` and that no class named `GridRoom`, `AnchorRoom`, or `InstanceRoom` exists
      anywhere in the repository yet.
- [ ] 1.3 Confirm `world/prototypes.py` is still the commented-out tutorial stub with no active
      `PROTOTYPE_LIST`/module-level prototype dict.
- [ ] 1.4 Confirm, by import, that `evennia.contrib.grid.xyzgrid.xyzroom.{XYZRoom, XYZExit}`,
      `evennia.contrib.grid.xyzgrid.xyzgrid.{XYZGrid, get_xyzgrid}`, and
      `evennia.contrib.grid.xyzgrid.xymap.XYMap` resolve against the installed Evennia version,
      exactly as verified in design.md D-4 — do not assume the signatures without re-checking if the
      pinned Evennia version has changed since this proposal was written.
- [ ] 1.5 Confirm `docker-entrypoint.sh` still runs only `evennia migrate --noinput` followed by
      `evennia start --log`, with no `evennia xyzgrid` step, before relying on design.md D-5's
      at-server-start provisioning decision.

## 2. Anchor placement registry (`world/lore/anchor_placement.py`)

- [ ] 2.1 Implement the frozen `AnchorPlacement` dataclass (`anchor_key: str`, `zcoord: str`,
      `entrance_xy: tuple[int, int]`) per design.md D-1.
- [ ] 2.2 Implement `ANCHOR_PLACEMENT_REGISTRY: dict[str, AnchorPlacement]` with exactly one entry:
      `"capital_altoria": AnchorPlacement("capital_altoria", "capital_altoria", (2, 2))`.
- [ ] 2.3 Test: `ANCHOR_PLACEMENT_REGISTRY` has exactly one entry, keyed `"capital_altoria"`.
- [ ] 2.4 Test: every entry's `anchor_key` exists in `world.lore.anchors.ANCHOR_REGISTRY`.
- [ ] 2.5 Test: `Anchor` (in `world/lore/anchors.py`) still has exactly its pre-change field set
      (`key`, `kind`, `display_name_zh`, `nation_key`, `population`, `floors`, `description`) — a
      regression guard proving this change did not extend it.

## 3. Wire ANCHOR_PLACEMENT_REGISTRY into lore sync (`world/lore/sync.py`)

- [ ] 3.1 Import `ANCHOR_PLACEMENT_REGISTRY` in `world/lore/sync.py` and add it to `_ALL_REGISTRIES`
      under the key `"anchor_placements"`, per design.md D-2. Do not rename or otherwise alter
      `sync_all()`, `sync_one()`, `_db_safe()`, or `LoreRecord`.
- [ ] 3.2 Test: after `sync_all()` runs, a `LoreRecord` Script exists keyed
      `"lore:anchor_placements:capital_altoria"` with `db.fields` matching
      `_db_safe(asdict(ANCHOR_PLACEMENT_REGISTRY["capital_altoria"]))`.
- [ ] 3.3 Test: calling `sync_all()` twice leaves exactly one such record (extend the existing
      idempotency test pattern in `world/lore/tests/test_sync.py` rather than duplicating its
      structure).
- [ ] 3.4 Confirm (via `git diff`) that this task's edit to `world/lore/sync.py` is the only change
      to any file authored by change 2, and that `openspec/specs/lore-registries/spec.md` and
      `openspec/specs/lore-startup-sync/spec.md` are untouched.

## 4. Room typeclasses (`typeclasses/rooms.py`)

- [ ] 4.1 Add `GridRoom(XYZRoom)` (import from `evennia.contrib.grid.xyzgrid.xyzroom`) with a
      persistent `scene_archetype: str | None = AttributeProperty(default=None)` seam, per design.md
      D-6. Leave the existing `Room(ObjectParent, DefaultRoom)` class exactly as-is.
- [ ] 4.2 Add `AnchorRoom(GridRoom)` with a persistent `anchor_key: str | None =
      AttributeProperty(default=None)` seam.
- [ ] 4.3 Do **not** add any class or stub named `InstanceRoom` — confirm by source inspection that
      no such name exists anywhere in `typeclasses/rooms.py` after this task group.
- [ ] 4.4 Test: creating a `GridRoom` via `GridRoom.create(key="test", xyz=(9, 9, "test_map"))`
      succeeds, `.xyz == (9, 9, "test_map")`, and `.scene_archetype is None` by default.
- [ ] 4.5 Test: setting `room.scene_archetype = "tavern_interior"` succeeds with no registry lookup
      (no `SceneArchetype` import anywhere in `typeclasses/rooms.py`), and the value persists across
      a fresh fetch of the same object from the database.
- [ ] 4.6 Test: creating an `AnchorRoom` via `AnchorRoom.create(key="test", xyz=(8, 8, "test_map"))`
      exposes both `.xyz` and `.scene_archetype` (inherited from `GridRoom`) and `.anchor_key`
      (defaulting to `None`).
- [ ] 4.7 Test: setting `anchor_room.anchor_key = "does_not_exist"` on a freshly created `AnchorRoom`
      does not raise — confirming the typeclass itself performs no `ANCHOR_REGISTRY` validation (that
      validation lives in `sync_grid()`/its tests, task group 6).
- [ ] 4.8 Test: `Room` (the stock class) is unchanged — instantiate it and confirm it has no
      `scene_archetype` or `anchor_key` attribute and is not an instance of `GridRoom`.

## 5. Prototypes (`world/prototypes.py`)

- [ ] 5.1 Replace the inert tutorial-stub comment block with two active module-level prototype
      dicts, `GRID_ROOM` and `ANCHOR_ROOM`, each with `"prototype_parent": "xyz_room"` and
      `"typeclass"` pointed at `typeclasses.rooms.GridRoom` / `typeclasses.rooms.AnchorRoom`
      respectively (chaining from the contrib's own `xyz_room` prototype, which
      `evennia.contrib.grid.xyzgrid.prototypes` supplies once added to `PROTOTYPE_MODULES` — task
      7.2). Keep the module's existing docstring; do not delete the file's top-level documentation.
- [ ] 5.2 Test: `GRID_ROOM["typeclass"]` resolves to an importable `typeclasses.rooms.GridRoom`, and
      likewise for `ANCHOR_ROOM`/`AnchorRoom` — a simple `class_from_module`-style import check, not
      an Evennia-prototype-registry test (that is exercised indirectly by task group 8's spawn
      tests).

## 6. Sample city map data (`world/maps/altoria_capital.py`)

- [ ] 6.1 Create `world/maps/__init__.py` (empty package marker) and `world/maps/altoria_capital.py`.
- [ ] 6.2 Author the verified `MAPSTR` from design.md D-6 exactly (the thirteen-node, twelve-link
      layout parsed and path-matrix-computed against the real `XYMap` class during this proposal's
      own research):
      ```
      + 0 1 2 3 4

      4     #
            |
      3   #-#-#
            |
      2 #-#-#-#-#
            |
      1   #-#-#
            |
      0     #

      + 0 1 2 3 4
      ```
- [ ] 6.3 Author the `PROTOTYPES` dict keyed by (X,Y) coordinate for all thirteen rooms per design.md
      D-6's table (南門 (2,0), 南大道 (2,1), 旅店外 (1,1), 冒險者公會外 (3,1), 中央廣場 (2,2)
      [`"prototype_parent": "anchor_room"`, `"anchor_key": "capital_altoria"`], 鐵匠鋪外 (0,2),
      市場街 (1,2), 神殿街 (3,2), 光明神殿外 (4,2), 北大道 (2,3), 貴族區門口 (1,3), 城牆哨塔 (3,3),
      北門 (2,4)) — every coordinate other than (2,2) uses `"prototype_parent": "grid_room"`. Each
      entry sets `key` (the Traditional Chinese room name) and a short `desc`.
- [ ] 6.4 Assemble `XYMAP_DATA = {"zcoord": "capital_altoria", "map": MAPSTR, "prototypes":
      PROTOTYPES}` and `XYMAP_DATA_LIST = [XYMAP_DATA]`.
- [ ] 6.5 Test: `XYMap(dict(XYMAP_DATA), Z="capital_altoria", xyzgrid=None).parse()` succeeds and
      yields exactly the thirteen coordinates listed above, with no others.
- [ ] 6.6 Test: `.calculate_path_matrix()` succeeds without error (confirms `scipy` resolves in the
      project's own environment for this specific map) and a shortest path exists between every pair
      of the thirteen coordinates.
- [ ] 6.7 Test: the parsed link set has exactly twelve edges and is a tree (no cycle) — for example,
      by asserting `len(edges) == len(nodes) - 1` and that the graph is connected (task 6.6 already
      proves connectivity; combine both into one assertion or two adjacent ones).
- [ ] 6.8 Test: only `(2,2)`'s prototype entry has `"prototype_parent": "anchor_room"`; every other
      of the twelve has `"prototype_parent": "grid_room"`.

## 7. Settings and cmdset wiring

- [ ] 7.1 Add `EXTRA_LAUNCHER_COMMANDS["xyzgrid"] = "evennia.contrib.grid.xyzgrid.launchcmd.
      xyzcommand"` to `server/conf/settings.py`, per design.md D-4/D-5.
- [ ] 7.2 Append `"evennia.contrib.grid.xyzgrid.prototypes"` and `"world.prototypes"` to
      `PROTOTYPE_MODULES` in `server/conf/settings.py` (confirm `"world.prototypes"` is not already
      present by default before appending — `evennia.settings_default` already lists it; do not
      duplicate the entry).
- [ ] 7.3 Add `evennia.contrib.grid.xyzgrid.commands.XYZGridCmdSet` to `commands/default_cmdsets.py::
      CharacterCmdSet.at_cmdset_creation()`.
- [ ] 7.4 Test: `evennia xyzgrid help` (or an equivalent non-interactive invocation) runs without a
      settings-resolution error, confirming `EXTRA_LAUNCHER_COMMANDS` is wired correctly.
- [ ] 7.5 Test: `CharacterCmdSet` contains the commands `XYZGridCmdSet` provides (for example,
      `map`, `goto`) after `at_cmdset_creation()` runs, via `EvenniaTest`.

## 8. Grid bootstrap and idempotent room/exit sync (`world/maps/bootstrap.py`)

- [ ] 8.1 Implement `sync_grid()` per design.md D-3/D-5: obtain the singleton via `get_xyzgrid()`,
      call `.add_maps(*ALTORIA_CAPITAL.XYMAP_DATA_LIST)`, then **`.reload()`**, then `.spawn()` — all
      three calls, in that exact order, within the same process. Do not drop the `.reload()` call: as
      design.md D-5 documents in detail (a defect a rubber-duck review caught and this project
      verified against the installed Evennia source), `add_maps()` followed directly by `spawn()`
      with no `reload()` in between silently spawns zero rooms on a fresh database, because
      `get_xyzgrid()`'s own creation path already primes `self.ndb.grid` to `{}` (not `None`) before
      `add_maps()` ever runs, so the `.grid` property's lazy-reload guard does not fire on its own.
      Name the function `sync_grid`, not `sync_all` or any other name that could be confused with
      `world/lore/sync.py::sync_all()` — this distinction is the direct resolution of the "anchor
      sync is overloaded" gap and must not be blurred by a task-time naming shortcut.
- [ ] 8.2 Implement the idempotent Limbo-bridging `Exit` pair inside `sync_grid()`, per design.md
      D-7: look up Limbo by **`key="Limbo"`** (never by dbref — this project's own `EvenniaTest`
      fixtures put an unrelated object at dbref `#2`) and the spawned South Gate room
      (`(2, 0, "capital_altoria")`) after `.spawn()` completes. If no object keyed `"Limbo"` is
      found, log a warning and return without creating either bridging exit — do not raise. If Limbo
      is found and no exit from Limbo to the South Gate room already exists (checked by `location` +
      `destination`, not by key alone, to tolerate a future rename), create one named "南門" (aliases
      `south gate`, `altoria`) using the plain `typeclasses.exits.Exit` typeclass; do the symmetric
      check/create for the return exit "離開王都" (aliases `leave`, `limbo`).
- [ ] 8.3 Test: `sync_grid()` against an empty database containing a room keyed `"Limbo"` creates
      exactly thirteen `GridRoom`/`AnchorRoom` instances and exactly twelve intra-city `XYZExit`
      instances (the map's own links), plus the two Limbo-bridging `Exit`s (fourteen exits total).
- [ ] 8.4 Test idempotency: calling `sync_grid()` a second time with unchanged map data leaves the
      room count, intra-city exit count, and bridging-exit count all unchanged, and every room's
      `dbid` from the first call still resolves to the same object (no delete-and-recreate). Include
      a variant of this test that confirms the fix for the blocking sequencing defect specifically:
      construct a fresh `XYZGrid` (simulating the very first `get_xyzgrid()` call on an empty
      database) and assert that a *single* `sync_grid()` call — not a second one — already produces
      all thirteen rooms, so the fresh-boot regression this task group exists to catch cannot silently
      return.
- [ ] 8.5 Test in-place update: change one coordinate's `desc` in a test-local copy of the map data,
      call the spawn path again, and assert the existing room's `desc` changed with no new room
      created at that coordinate (mirrors design.md D-4's read of `MapNode.spawn()`'s
      `batch_update_objects_with_prototype(..., exact=False)` behavior).
- [ ] 8.6 Test the AnchorRoom/anchor_key/ANCHOR_PLACEMENT_REGISTRY cross-check named in design.md's
      Risks section: after `sync_grid()` runs, the spawned room at `ANCHOR_PLACEMENT_REGISTRY[
      "capital_altoria"].entrance_xy` on zcoord `ANCHOR_PLACEMENT_REGISTRY["capital_altoria"].zcoord`
      is an `AnchorRoom` with `anchor_key == "capital_altoria"`.
- [ ] 8.7 Test the bridging exits specifically, against a database containing a room keyed `"Limbo"`:
      that room has exactly one exit toward `(2, 0, "capital_altoria")`, and the South Gate room has
      exactly one exit toward it, both before and after a second `sync_grid()` call. Also test the
      lookup-by-key guarantee directly: with an unrelated object occupying dbref `#2` and the actual
      `"Limbo"`-keyed room elsewhere in the database, `sync_grid()` still attaches the bridging exits
      to the `"Limbo"`-keyed room, not to `#2`.
- [ ] 8.8 Test the North Gate dead end: the room at `(2, 4, "capital_altoria")` has exactly one exit
      (south, back into the city) and no other.
- [ ] 8.9 Test the absent-Limbo degradation path: `sync_grid()` against a database with no object
      keyed `"Limbo"` still spawns all thirteen rooms and twelve intra-city exits, creates no bridging
      exit, and does not raise.

## 9. Server startup wiring (`server/conf/at_server_startstop.py`)

- [ ] 9.1 Add a call to `world.maps.bootstrap.sync_grid()` inside `at_server_start()`, immediately
      after the existing `sync_all()` call, per design.md D-5.
- [ ] 9.2 Test (source-order check): `at_server_start()`'s source lists the `sync_grid()` call after
      the `sync_all()` call.
- [ ] 9.3 Test (integration): simulating a server start (calling `at_server_start()` directly against
      a fresh test database, or the equivalent `EvenniaTest` setup) results in both the lore
      `LoreRecord`s and the sample city's rooms/exits existing, with no exception raised. Run this
      once against a plain `EvenniaTest` fixture (no room keyed `"Limbo"` present) to prove the
      absent-Limbo path (task 8.9) does not abort the rest of startup, and once against a fixture with
      a `"Limbo"`-keyed room present to prove the bridging exits are also created during a simulated
      real start.

## 10. Contrib matrix regression coverage (`tests/test_contrib_matrix.py`)

- [ ] 10.1 Add `"xyzgrid runtime"` (or similarly named) row(s) to `MATRIX_IMPORTS` covering
      `evennia.contrib.grid.xyzgrid.xyzgrid` (`XYZGrid`, `get_xyzgrid`) and
      `evennia.contrib.grid.xyzgrid.xymap` (`XYMap`) — the symbols this change actually calls beyond
      the `XYZRoom`/`XYZExit` class-import check change 1 already added.
- [ ] 10.2 Test: `ContribMatrixTests.test_matrix_imports_and_attributes` passes with the new rows
      included (no separate test needed — extending the existing parametrized dict is sufficient).

## 11. Full-suite integration test for the sample city

- [ ] 11.1 Write one `EvenniaTest`-based integration test that: renames/creates the fixture's dbref
      `#2` (or another fixture room) to be keyed exactly `"Limbo"`, per design.md D-7's test
      convention, so the bridging exits are actually exercised — do not rely on `EvenniaTest`'s
      default fixture naming; runs `sync_all()` then `sync_grid()` against a fresh test database;
      walks from the `"Limbo"`-keyed room through the bridging exit into the South Gate; traverses
      north through South Main Street to the Central Plaza (`AnchorRoom`); confirms
      `return_appearance()` (inherited from `XYZRoom`) renders without error for at least one room —
      proving the grid is not just spawned but actually navigable via ordinary Evennia exit
      traversal, with no custom `move` command needed.
- [ ] 11.2 Test: every one of the thirteen rooms is reachable from the South Gate via ordinary exit
      traversal (breadth-first walk using each room's `.exits`, or equivalent), confirming the tree
      topology is fully connected in the spawned database state, not just in the parsed `XYMap`.

## 12. Verification

- [ ] 12.1 Run the full test suite added by this change (`world/lore/tests/`, `typeclasses/tests/`,
      `world/maps/tests/`, `tests/test_contrib_matrix.py`) and confirm every test passes.
- [ ] 12.2 Confirm (via `git diff`) that every edit to an already-landed file (`world/lore/sync.py`,
      `typeclasses/rooms.py`, `world/prototypes.py`, `server/conf/settings.py`, `server/conf/
      at_server_startstop.py`, `commands/default_cmdsets.py`, `tests/test_contrib_matrix.py`) is
      additive and does not remove or alter any behavior a prior change's own tests depend on; run
      each prior change's own test module (`world/lore/tests/test_sync.py`, `world/rules/tests/
      test_clock.py`, `world/rules/tests/test_cmd_cast.py`) and confirm they still pass unmodified.
- [ ] 12.3 Confirm no file added or edited by this change contains a reference to `world/ai/` or an
      LLM call, mirroring this project's established no-generative-layer-in-the-deterministic-core
      discipline (this change touches no `world/rules/` file at all, but the check costs nothing and
      keeps the discipline visible).
- [ ] 12.4 Confirm `settings.START_LOCATION` is unchanged (still `"#2"`) by source inspection, per
      design.md D-7's Non-Goal.
- [ ] 12.5 Run `openspec validate map-anchor-grid --strict` and confirm it passes.
