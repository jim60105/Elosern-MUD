## 1. Confirmations before writing code

- [x] 1.1 Confirm change 12 (`map-anchor-grid`) is implemented: `typeclasses/rooms.py::GridRoom` and
      `AnchorRoom` exist matching its `grid-room-typeclasses` spec, `world/maps/bootstrap.py::
      sync_grid()` exists, the `capital_altoria` sample city spawns thirteen rooms including a North
      Gate at `(2, 4, "capital_altoria")` with exactly one exit (south). Do not proceed past task
      group 4 if this is not true yet — this change's roadmap position (`depends on 12`) assumes it.
- [x] 1.2 Confirm, by import inside an `EvenniaTest`-backed process (`uv run --locked evennia test
      --settings settings.py <scratch module>` — a bare `django.setup()` script is insufficient; the
      wilderness contrib's module-level `from evennia import DefaultScript` resolves to `None` until
      `evennia._init()` has run, which only happens inside Evennia's own test/server bootstrap), that
      `evennia.contrib.grid.wilderness.wilderness.{WildernessMapProvider, WildernessRoom,
      WildernessExit, WildernessScript, create_wilderness, enter_wilderness, get_new_coordinates}`
      resolve against the installed Evennia version, exactly as verified in design.md's Verification
      section — do not assume the signatures without re-checking if the pinned Evennia version has
      changed since this proposal was written.
- [x] 1.3 Confirm no class named `SceneArchetypeMixin` or `TerrainRoom` exists anywhere in the
      repository yet, and that `typeclasses/exits.py` contains no class named `WildernessGateExit` or
      `WildernessReturnExit`.
- [x] 1.4 Confirm `world/rules/rulebook/clock.yaml::command_defaults` has no `wilderness_move` key yet.

## 2. Wilderness terrain lore registry (`world/lore/wilderness_regions.py`)

- [x] 2.1 Implement the frozen `WildernessRegion` dataclass (`key: str`, `display_name_zh: str`,
      `nation_key: str | None`, `terrain_flavor_zh: tuple[str, ...]`) per design.md D-1.
- [x] 2.2 Implement `WILDERNESS_REGION_REGISTRY: dict[str, WildernessRegion]` with exactly seven
      entries (`central_mountains`, `eastern_plains`, `southeast_coast`, `western_hills_valleys`,
      `southwest_coast`, `northwest_highland_forest`, `north_deep_forest`). Use design.md D-1's
      literal table **verbatim** — both `display_name_zh` and every `terrain_flavor_zh` string,
      exactly as written there (three variants each), not a paraphrase or a different ordering. This
      is load-bearing: `wilderness-terrain/spec.md`'s literal-pin scenario (task 6.9) asserts
      `terrain_description(60, 100)` against this exact text, so a reworded variant list would fail
      that test even though it "means the same thing." `nation_key` per design.md D-1's table (`None`
      for `central_mountains`; `"grandia"` for `eastern_plains`/`southeast_coast`; `"altoria"` for
      `western_hills_valleys`/`southwest_coast`; `"valhalla"` for
      `northwest_highland_forest`/`north_deep_forest`).
- [x] 2.3 Test: `WILDERNESS_REGION_REGISTRY` has exactly seven entries, keys match the seven listed
      above, and no `display_name_zh` is duplicated.
- [x] 2.4 Test: every entry's `terrain_flavor_zh` has at least two elements, and every `nation_key`
      that is not `None` exists in `world.lore.nations.NATION_REGISTRY`.

## 3. Wilderness entry point registry (`world/lore/wilderness_entry.py`)

- [x] 3.1 Implement the frozen `WildernessEntryPoint` dataclass (`anchor_key: str`, `wilderness_xy:
      tuple[int, int]`) per the `wilderness-gateway` spec.
- [x] 3.2 Implement `WILDERNESS_ENTRY_REGISTRY: dict[str, WildernessEntryPoint]` with exactly one
      entry: `"capital_altoria": WildernessEntryPoint("capital_altoria", (60, 100))`.
- [x] 3.3 Test: `WILDERNESS_ENTRY_REGISTRY` has exactly one entry, keyed `"capital_altoria"`.
- [x] 3.4 Test: every entry's `anchor_key` exists in `world.lore.anchor_placement.
      ANCHOR_PLACEMENT_REGISTRY` (change 12).
- [x] 3.5 Test: `WILDERNESS_ENTRY_REGISTRY["capital_altoria"].wilderness_xy` is within
      `ElosernWildernessMapProvider`'s valid coordinate bounds (depends on task group 6; may be
      written now and run once task group 6 lands).

## 4. Wire both registries into lore sync (`world/lore/sync.py`)

- [x] 4.1 Import `WILDERNESS_REGION_REGISTRY` and `WILDERNESS_ENTRY_REGISTRY` in `world/lore/sync.py`
      and add them to `_ALL_REGISTRIES` under the keys `"wilderness_regions"` and
      `"wilderness_entries"` respectively. Do not rename or otherwise alter `sync_all()`, `sync_one()`,
      `_db_safe()`, or `LoreRecord` — the same additive edit shape change 12 already made to this file.
- [x] 4.2 Test: after `sync_all()` runs, seven `LoreRecord` Scripts exist keyed
      `"lore:wilderness_regions:<key>"` and one exists keyed
      `"lore:wilderness_entries:capital_altoria"`.
- [x] 4.3 Test: calling `sync_all()` twice leaves the same counts (idempotency), extending the
      existing test pattern in `world/lore/tests/test_sync.py` rather than duplicating its structure.
- [x] 4.4 Confirm (via `git diff`) that this task's edit to `world/lore/sync.py` is additive only, and
      that `openspec/specs/lore-registries/spec.md` and `openspec/specs/lore-startup-sync/spec.md`
      remain untouched.

## 5. Room typeclasses: SceneArchetypeMixin, GridRoom retrofit, TerrainRoom (`typeclasses/rooms.py`)

- [x] 5.1 Add `SceneArchetypeMixin` per design.md D-2: a plain class carrying `scene_archetype: str |
      None = AttributeProperty(default=None)`.
- [x] 5.2 Change `GridRoom`'s base classes from `(XYZRoom,)` to `(SceneArchetypeMixin, XYZRoom)`, and
      remove its own direct `scene_archetype` declaration (now inherited). Do not change any other
      line of `GridRoom`'s or `AnchorRoom`'s bodies.
- [x] 5.3 Add `TerrainRoom(SceneArchetypeMixin, evennia.contrib.grid.wilderness.wilderness.
      WildernessRoom)` with no additional members beyond what the mixin and `WildernessRoom` already
      provide.
- [x] 5.4 Test: re-run change 12's own `scene_archetype` tests for `GridRoom` (default `None`,
      unvalidated assignment, persistence across a reload) unmodified, and confirm they still pass —
      the concrete proof that the retrofit is behavior-preserving (design.md D-2).
- [x] 5.5 Test: `SceneArchetypeMixin` appears in both `GridRoom.__mro__` and `TerrainRoom.__mro__`, and
      `GridRoom` declares no `scene_archetype` class attribute of its own (`"scene_archetype" not in
      GridRoom.__dict__`) — this is the concrete proof for this change's own `MODIFIED
      grid-room-typeclasses` delta spec scenario ("GridRoom shares its scene_archetype seam with
      SceneArchetypeMixin, not a private declaration"), not just the `scene-archetype-mixin`
      capability's own scenario.
- [x] 5.6 Test: `TerrainRoom.__mro__` does not include `evennia.contrib.grid.xyzgrid.xyzroom.XYZRoom`.
- [x] 5.7 Test: creating a `TerrainRoom` (via `create_object`) with no `scene_archetype` supplied
      defaults to `None`, and setting it to an arbitrary string succeeds with no registry lookup.

## 6. Terrain model (`world/maps/wilderness_provider.py`)

- [x] 6.1 Create `world/maps/wilderness_provider.py`. Implement `region_for_coordinates(x: int, y:
      int) -> str` per design.md D-1's exact rectangular partition (`_MOUNTAIN_X = (100, 123)`,
      `_NORTH_FOREST_Y_MIN = 190`, `_COASTAL_Y_MAX = 40`, `_HIGHLAND_Y_MIN = 150`).
- [x] 6.2 Implement `terrain_description(x: int, y: int) -> str` per design.md D-1's arithmetic
      formula (`(x * 92821 + y * 68917) % len(variants)`).
- [x] 6.3 Test: `region_for_coordinates`/`terrain_description` are pure — calling either twice with the
      same `(x, y)` returns the identical result.
- [x] 6.4 Test: every one of the seven region keys is returned by `region_for_coordinates` for at
      least one coordinate within the valid bounds (task group 7 supplies the bounds constants this
      test iterates over).
- [x] 6.5 Test: the central mountain band (`x` in `[100, 123]`) returns `"central_mountains"` at both
      `y = _HIGHLAND_Y_MIN - 1` and `y = _NORTH_FOREST_Y_MIN - 1` (excludes the northern-forest band,
      which is checked first and wins above `y = 189`).
- [x] 6.6 Test: `region_for_coordinates(60, 100)` (the registered `capital_altoria` entry point)
      returns `"western_hills_valleys"`.
- [x] 6.7 Test: `terrain_description(x, y)`'s return value is always one of
      `WILDERNESS_REGION_REGISTRY[region_for_coordinates(x, y)].terrain_flavor_zh`.
- [x] 6.8 Test: `world/maps/wilderness_provider.py` contains no import from `world.ai`, no HTTP client
      import, and no call to the `random` module (a source-inspection test, mirroring change 12's
      "no `world/ai/` reference" discipline check).
- [x] 6.9 Test (literal pin, `wilderness-terrain/spec.md`'s own scenario): `terrain_description(60,
      100)` returns exactly `"谷地間河流蜿蜒，兩岸散落著手工業者的作坊與磨坊。"` — the literal, hand-verified
      output of `(60 * 92821 + 100 * 68917) % 3 == 1`, i.e. `WILDERNESS_REGION_REGISTRY[
      "western_hills_valleys"].terrain_flavor_zh[1]`, against task 2.2's verbatim registry text. This
      pins the formula's *constants* (`92821`, `68917`) and the registry's *exact wording* together, so
      a reimplementation with different multipliers or reworded flavor text — which would satisfy every
      other requirement in this capability — fails this one, exactly as `wilderness-terrain/spec.md`
      requires.

## 7. ElosernWildernessMapProvider (`world/maps/wilderness_provider.py`, continued)

- [x] 7.1 Add `WILDERNESS_KM_PER_CELL = 10`, `WILDERNESS_MAX_X = 223`, `WILDERNESS_MAX_Y = 223`, and
      `WILDERNESS_NAME = "elosern"`.
- [x] 7.2 Implement `ElosernWildernessMapProvider(WildernessMapProvider)` per design.md D-4:
      `room_typeclass = TerrainRoom`, `exit_typeclass = WildernessReturnExit` (forward reference to
      task group 8; import order may require defining the provider after the exits module, or
      importing lazily — resolve per the implementer's judgment, matching this project's existing
      lazy-import precedent for cross-module forward references), `is_valid_coordinates`,
      `get_location_name`, `at_prepare_room` exactly as specified in design.md D-4.
- [x] 7.3 Test: `is_valid_coordinates(wilderness, (0, 0))` and `(223, 223)` return `True`;
      `(-1, 0)` and `(224, 0)` return `False`.
- [x] 7.4 Test: `(WILDERNESS_MAX_X + 1) * WILDERNESS_KM_PER_CELL` squared is within 1% of 5,000,000
      (the design.md D-4 arithmetic, asserted as a regression, not just computed by hand once).
- [x] 7.5 Test: `get_location_name((x, y))` returns `WILDERNESS_REGION_REGISTRY[
      region_for_coordinates(x, y)].display_name_zh` for several representative coordinates spanning
      multiple regions.
- [x] 7.6 Test (`EvenniaTest`): entering the wilderness through `enter_wilderness(char, coordinates=
      (x, y), name=WILDERNESS_NAME)` with a live `ElosernWildernessMapProvider` produces a
      `TerrainRoom` whose `.ndb.active_desc == terrain_description(x, y)` and whose
      `.scene_archetype == region_for_coordinates(x, y)`.
- [x] 7.7 Test: moving a character to a second coordinate in a different region, then recycling that
      same room object back to a coordinate in the first region (construct via repeated
      enter/leave/enter cycles until the same room object is reused, or inspect
      `WildernessScript.db.unused_rooms` directly to force reuse), confirms `scene_archetype` reflects
      the *current* coordinate's region, not a stale prior value (design.md D-3).

## 8. Exit typeclasses (`typeclasses/exits.py`)

- [x] 8.1 Add `WildernessGateExit(Exit)` per design.md D-6 (as corrected): `at_traverse` fully
      overridden. In order: (a) call `traversing_object.at_pre_move(None)` and return `False`
      immediately if it vetoes (Fix 5 — matches the stock `WildernessExit.at_traverse`'s own veto
      check); (b) read its own anchor association via `self.db.anchor_key` (set at creation time by
      `sync_wilderness()` — task 10.1 — **never left unset**, since `WILDERNESS_ENTRY_REGISTRY[None]`
      raises `KeyError`); (c) look up `WILDERNESS_ENTRY_REGISTRY[anchor_key]` and call
      `enter_wilderness(traversing_object, coordinates=entry.wilderness_xy, name=WILDERNESS_NAME)`,
      returning `False` if it fails; (d) on success, send a departure `msg_contents` to the source
      room and an arrival `msg_contents` to the new wilderness room (both excluding the traverser),
      call `traversing_object.at_post_move(None)`, then call `get_world_clock().advance(
      CLOCK_YAML["command_defaults"]["wilderness_move"], AdvanceSource.COMMAND,
      [traversing_object])`, and return `True`.
- [x] 8.2 Add `WildernessReturnExit(evennia.contrib.grid.wilderness.wilderness.WildernessExit)` per
      design.md D-6 (as corrected): on `at_traverse`, look up the traversing object's current
      coordinates via `self.location.wilderness.db.itemcoordinates`. Iterate
      `WILDERNESS_ENTRY_REGISTRY` (not a hardcoded single-key check, per design.md's Risks/Trade-offs
      note, so a future second entry needs no edit here): if the current coordinates match some
      entry's `wilderness_xy` **and** `self.key == "south"`, resolve that entry's anchor's grid room
      (e.g. via `GridRoom.objects.filter_xyz` against `ANCHOR_PLACEMENT_REGISTRY`/a fixed North Gate
      lookup helper), `move_to()` the traversing object there, call `get_world_clock().advance()` with
      the same cost/source as 8.1, and return `True`. **For every other coordinate and direction**,
      call `result = super().at_traverse(traversing_object, target_location)`, and — this is the
      corrected, previously-missing step — **if `result` is truthy, also call
      `get_world_clock().advance()` with the same cost/source before returning `result`.** The clock
      must advance on every successful traversal through this exit, not only the special-cased
      return-to-grid branch — see design.md D-6's correction note for the exact defect this fixes (an
      earlier draft left all 222 intermediate wilderness steps of a continent crossing free).
- [x] 8.3 Test (`EvenniaTest`): traversing a `WildernessGateExit` places the traverser in a
      `TerrainRoom` at the registered entry coordinate, and `get_world_clock().tick` increases by
      exactly `9000`.
- [x] 8.4 Test: an `enter_wilderness()` failure inside `WildernessGateExit.at_traverse` (simulate via
      an invalid coordinate) leaves `get_world_clock().tick` unchanged, and does not raise.
- [x] 8.5 Test: every one of the eight directional exits on a room created by
      `ElosernWildernessMapProvider` is a `WildernessReturnExit` instance.
- [x] 8.6 Test: traversing `"south"` from the registered entry coordinate moves the traverser to the
      exact same grid-room object that existed before entry (identity check, not equality), and
      `get_world_clock().tick` increases by `9000` again.
- [x] 8.7 **Test (blocking-defect regression — the core proof of distance-proportional travel):**
      starting from the registered entry coordinate, traverse **three consecutive intermediate
      steps** in the same direction (e.g. `"east"` three times — none of these traversals are the
      registered coordinate's `"south"` exit, so none takes the special-cased branch), asserting
      `get_world_clock().tick` increases by exactly `9000` after **each individual step**, not just
      in aggregate. Then walk back (e.g. `"west"` three times) and traverse `"south"` once more to
      return to the grid. Assert the **grand total** clock advance across the whole round trip (1
      entry + 3 out + 3 back + 1 return = 8 legs) equals exactly `8 * 9000 = 72000`. This test must
      fail if any single leg — especially an intermediate, non-special-cased one — advances the clock
      by `0`.
- [x] 8.8 Test: traversing any other direction, or `"south"` from a non-entry coordinate, routes
      identically to a stock `WildernessExit` (ordinary coordinate movement, correct edge-of-map
      locking per design.md's Verification section) — this test asserts routing/location correctness;
      task 8.7 asserts the clock cost for the same category of traversal.
- [x] 8.9 Test: after returning via `WildernessReturnExit`, the traverser no longer appears in
      `WildernessScript.db.itemcoordinates`, and the vacated room is not orphaned: it is either in
      `unused_rooms` (when the contrib's recycling condition is met) or retained in
      `WildernessScript.db.rooms` keyed by its coordinates (the contrib's actual behavior for an
      account-character `move_to()`-driven departure — `_destroy_room` sees the departing account
      still in the room's contents and declines to recycle), and re-entering the same coordinates
      reuses that same room object.
- [x] 8.10 Test (Fix 5, movement hooks): a mock/stub `at_pre_move` on the traverser that returns
      `False` prevents `WildernessGateExit.at_traverse` from calling `enter_wilderness()` at all, and
      leaves both the traverser's location and `get_world_clock().tick` unchanged. A default
      character (no veto installed) traverses normally, exactly as task 8.3 already exercises.
- [x] 8.11 Test (rubber-duck fix): a failed return through `WildernessReturnExit` — `move_to()`
      failing its pre-move veto, or `_grid_room_for_anchor` resolving no grid room — returns `False`,
      leaves the traverser in the wilderness, and does not advance the clock.

## 9. Clock rulebook constant (`world/rules/rulebook/clock.yaml`)

- [x] 9.1 Add `command_defaults.wilderness_move: 9000` per design.md D-5's arithmetic (10 km/cell ÷ 4
      km/h = 2.5h = 9000s). Do not modify the existing `move`/`converse`/`cast` entries.
- [x] 9.2 Test: `CLOCK_YAML["command_defaults"]["wilderness_move"] == 9000` and
      `CLOCK_YAML["command_defaults"]["move"] == 30` (unchanged).
- [x] 9.3 Test (regression, raw arithmetic): the full 224-step continent-crossing arithmetic from
      design.md D-5 (`224 * 9000 / 86400 ≈ 23.33` days, `≈ 26%` of a 90-day season) is asserted as a
      closed-form calculation, so a future edit to `wilderness_move` or the map bounds that breaks the
      "sane travel time" property is caught. **This formula-level assertion is necessary but not
      sufficient on its own** — it was, in an earlier draft, the change's only regression coverage for
      "distance costs time," and it does not simulate an actual walk, so it could not have caught the
      blocking defect where intermediate steps advanced the clock by `0`. Task 8.7 is the test that
      actually walks a multi-step path and would have caught that defect; this task and 8.7 are
      deliberately both required, not alternatives.

## 10. Wilderness bootstrap (`world/maps/bootstrap.py`)

- [x] 10.1 Implement `sync_wilderness()` per design.md D-7: call `create_wilderness(name=
      WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider())`; look up the `capital_altoria`
      North Gate `GridRoom` (by `(2, 4, "capital_altoria")`, mirroring change 12's own coordinate
      lookup style); if found and no exit keyed `"荒野"` already exists there, create a
      `WildernessGateExit` (key `"荒野"`, aliases `["wilderness", "north", "n"]`, `location` and
      `destination` both the North Gate room) **and then set `gate.db.anchor_key = "capital_altoria"`
      on the created object** — this line is load-bearing and must not be dropped: without it,
      `WildernessGateExit.at_traverse` (task 8.1) reads `self.db.anchor_key` as `None` and
      `WILDERNESS_ENTRY_REGISTRY[None]` raises `KeyError` on the gate's very first use, after
      `sync_wilderness()` itself reports success (design.md D-7's own correction note has the full
      account of this exact defect in an earlier draft). If not found, log a warning and return
      without creating the gate exit. Do not modify `sync_grid()`.
- [x] 10.2 Test: `sync_wilderness()` against a database where `sync_grid()` has already run creates a
      `WildernessScript` keyed `WILDERNESS_NAME` and exactly one `WildernessGateExit` at the North
      Gate room, **with `db.anchor_key == "capital_altoria"` on that exit** — asserted directly, not
      merely implied by a later successful traversal, so a regression here fails at creation time
      rather than surfacing only when a player first walks through the gate.
- [x] 10.3 Test idempotency: calling `sync_wilderness()` a second time leaves exactly one
      `WildernessScript` keyed `WILDERNESS_NAME` and exactly one gate exit at the North Gate.
- [x] 10.4 Test the absent-North-Gate degradation path: `sync_wilderness()` against a database with no
      `capital_altoria` North Gate room still creates the `WildernessScript`, creates no gate exit, and
      does not raise.
- [x] 10.5 Confirm (via `git diff`) that `sync_grid()`'s own body is unmodified by this task group.
- [x] 10.6 Test (rubber-duck fixes, restart restoration + gate heal): a room retained in
      `WildernessScript.db.rooms` that loses its `ndb.active_desc`/`scene_archetype` across a restart
      has both restored by the next `sync_wilderness()` call; a `WildernessGateExit` with a wrong
      `db.anchor_key` is healed to `"capital_altoria"`; and a same-key non-project exit is left alone
      with no second gate spawned atop it.

## 11. Server startup wiring (`server/conf/at_server_startstop.py`)

- [x] 11.1 Add a call to `world.maps.bootstrap.sync_wilderness()` inside `at_server_start()`,
      immediately after the existing `sync_grid()` call.
- [x] 11.2 Test (source-order check): `at_server_start()`'s source lists `sync_wilderness()` after
      `sync_grid()`.
- [x] 11.3 Test (integration): simulating a server start against a fresh test database results in the
      sample city, the wilderness script, and the gate exit all existing, with no exception raised.

## 12. Contrib matrix regression coverage (`tests/test_contrib_matrix.py`)

- [x] 12.1 Add a `"wilderness"` row (or rows) to `MATRIX_IMPORTS` covering
      `evennia.contrib.grid.wilderness.wilderness.{WildernessMapProvider, WildernessRoom,
      WildernessExit, WildernessScript, create_wilderness, enter_wilderness}` — the symbols this
      change actually calls.
- [x] 12.2 Test: `ContribMatrixTests.test_matrix_imports_and_attributes` passes with the new rows
      included.

## 13. Full-suite round-trip integration test

- [x] 13.1 Write one `EvenniaTest`-based integration test that: runs `sync_all()`, then `sync_grid()`,
      then `sync_wilderness()` against a fresh test database; walks a character from the South Gate
      (Limbo bridge, change 12) through the sample city to the North Gate; traverses the `"荒野"` exit
      into the wilderness, confirming the location, region name, description, and clock advance;
      walks a few steps within the wilderness (confirming `region_for_coordinates`/
      `terrain_description` change appropriately at region boundaries if the path crosses one);
      traverses `"south"` back to the exact North Gate room object; confirms the round trip leaves no
      leaked wilderness bookkeeping (task group 8's cleanup assertions).
- [x] 13.2 Test: `return_appearance()` (inherited from `WildernessRoom`/`TerrainRoom`) renders without
      error for at least one wilderness room, proving the terrain layer is not just spawned but
      actually displayable.

## 14. Verification

- [x] 14.1 Run the full test suite added by this change (`world/lore/tests/`, `typeclasses/tests/`,
      `world/maps/tests/`, `tests/test_contrib_matrix.py`) and confirm every test passes.
- [x] 14.2 Confirm (via `git diff`) that every edit to an already-landed file (`world/lore/sync.py`,
      `typeclasses/rooms.py`, `typeclasses/exits.py`, `world/maps/bootstrap.py`, `world/rules/
      rulebook/clock.yaml`, `server/conf/at_server_startstop.py`, `tests/test_contrib_matrix.py`) is
      additive and does not remove or alter any behavior a prior change's own tests depend on; run
      each prior change's own test module (`world/lore/tests/test_sync.py`, `world/maps/tests/
      test_bootstrap.py` [change 12], `world/rules/tests/test_clock.py`, `commands/tests/
      test_cmd_cast.py`) and confirm they still pass unmodified.
- [x] 14.3 Confirm no file added or edited by this change contains a reference to `world/ai/` or an
      LLM call.
- [x] 14.4 Confirm `settings.START_LOCATION` is unchanged, and that this change does not alter
      `rulebook/clock.yaml`'s existing `move`/`converse` entries.
- [x] 14.5 Run `openspec validate map-wilderness --strict` and confirm it passes.
