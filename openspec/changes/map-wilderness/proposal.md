## Why

Design doc D3 names four map layers — Anchor / Grid / Virtual (wilderness) / Instance — and roadmap
item 13 (§11, depends on 12) is the first change to build the Virtual layer. Change 12
(`map-anchor-grid`) built exactly one walkable place, 聖潔王都 (`capital_altoria`), as thirteen
`xyzgrid` rooms, and deliberately left its North Gate `(2,4,"capital_altoria")` a dead end — its own
design.md D-7 says so explicitly: "Change 13 depends on this change, not the reverse ...
`WildernessMapProvider` does not exist. The North Gate `(2,4)` is deliberately a dead end today;
making it more than that is change 13's decision." Without this change, the sample city is an
island: a player can walk its streets but cannot leave them, `world_info.md`'s seven named terrain
regions (中央山脈, 東部大平原, 東南海岸, 西部丘陵與谷地, 西南海岸, 西北高地森林, 北部深林) covering the
continent's ~500萬 km² exist only as lore prose, and `rulebook/clock.yaml`'s `command_defaults.move:
30` — declared inert by both change 11 (`world-clock`) and change 12 — has no consumer. This change
gives the world open space: a deterministic, offline-computable terrain model spanning the
continent, a bounded `evennia.contrib.grid.wilderness.WildernessMapProvider` subclass instantiating
it, and a concrete, bidirectional gateway connecting the sample city's North Gate to it — closing
the loop on movement's clock cost that change 12 explicitly deferred.

## What Changes

- Add `world/lore/wilderness_regions.py::WildernessRegion` (frozen dataclass: `key`,
  `display_name_zh`, `nation_key: str | None`, `terrain_flavor_zh: tuple[str, ...]`) and
  `WILDERNESS_REGION_REGISTRY: dict[str, WildernessRegion]` — exactly the seven terrain regions
  `world_info.md`'s geography section names, each carrying two or three deterministic Traditional
  Chinese flavor-text variants. Wired into `world/lore/sync.py::_ALL_REGISTRIES` (one entry added,
  `"wilderness_regions"`), the same additive edit change 12 already made to the same file for
  `ANCHOR_PLACEMENT_REGISTRY`.
- Add `world/lore/wilderness_entry.py::WildernessEntryPoint` (frozen dataclass: `anchor_key: str`,
  `wilderness_xy: tuple[int, int]`) and `WILDERNESS_ENTRY_REGISTRY: dict[str, WildernessEntryPoint]`
  — a keyed, intentionally partial registry (mirroring change 12's `ANCHOR_PLACEMENT_REGISTRY`
  exactly) linking an anchor that already has a grid placement to the one wilderness coordinate its
  gate opens onto. Starts with exactly one entry, `capital_altoria`. Also wired into `sync.py`'s
  `_ALL_REGISTRIES` (`"wilderness_entries"`).
- Add `world/maps/wilderness_provider.py`: `region_for_coordinates(x, y) -> str` and
  `terrain_description(x, y) -> str` (both pure functions — no LLM, no randomness, no DB read — the
  same input always produces the same output), the coordinate bounds (`WILDERNESS_MAX_X`,
  `WILDERNESS_MAX_Y` — a 224×224 grid at 10 km/cell) and `ElosernWildernessMapProvider(
  WildernessMapProvider)`, the map provider subclass required by design doc §4's "Extend" call on
  this contrib, overriding `is_valid_coordinates`, `get_location_name`, and `at_prepare_room` and
  pointing `room_typeclass`/`exit_typeclass` at this change's own room/exit subclasses.
- Add `typeclasses/rooms.py::SceneArchetypeMixin` (the `scene_archetype: str | None` seam, factored
  out of change 12's `GridRoom` into a class both `GridRoom` and this change's new `TerrainRoom` can
  adopt independently, resolving the exact risk change 12's own design.md flagged: "the likely
  resolution is a small, standalone `SceneArchetypeMixin` ... that `GridRoom`, a future
  `WildernessRoom` subclass, and a future `InstanceRoom` can each adopt"). Retrofits `GridRoom` onto
  it (an edit to change 12's already-landed implementation file, behavior-preserving per design.md,
  **and** paired with a `MODIFIED grid-room-typeclasses` delta spec — see Capabilities below — since
  changing an already-shipped class's base classes is the kind of change change 12's own design.md D-1
  says needs a new artifact, not merely a same-file edit) and adds
  `TerrainRoom(SceneArchetypeMixin, WildernessRoom)`.
- Add `typeclasses/exits.py::WildernessGateExit` (an ordinary, project-owned `Exit` whose
  `at_traverse` is fully overridden to call `wilderness.enter_wilderness()` instead of moving to a
  fixed `destination` — verified against the installed Evennia 6.1.0 as the correct, sanctioned
  pattern by reading `WildernessExit.at_traverse`'s own identical override style, including its
  `at_pre_move` veto/announcement/`at_post_move` sequence, which this exit now honors too) and
  `WildernessReturnExit(WildernessExit)` (the wilderness's own `exit_typeclass`, which special-cases
  exactly one coordinate-and-direction pair — the registered entry point, direction `south` — for
  *routing* back into the grid room instead of another wilderness coordinate; every other coordinate
  and direction routes like a stock `WildernessExit`. **The clock cost is not gated the same way**:
  every successful traversal through `WildernessReturnExit`, special-cased or not, advances
  `WorldClock` by `wilderness_move` — see below).
- Add `world/maps/bootstrap.py::sync_wilderness()` — idempotently calls
  `wilderness.create_wilderness(name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider())`
  (verified idempotent by reading the contrib source: a no-op if a `WildernessScript` of that name
  already exists) and idempotently ensures the one `WildernessGateExit` exists at North Gate **with
  its `db.anchor_key` set to `"capital_altoria"`** — omitting that assignment leaves the gate exit
  present but crashing on first use (`WILDERNESS_ENTRY_REGISTRY[None]` raises `KeyError`), a defect an
  earlier draft of this change had and a rubber-duck review caught before implementation. Wired into
  `server/conf/at_server_startstop.py::at_server_start()` immediately after change 12's `sync_grid()`
  call.
- Extend `rulebook/clock.yaml::command_defaults` with one new key, `wilderness_move: 9000` (2.5
  in-game hours per wilderness step at the chosen 10 km/step scale) — an additive edit to change 11's
  already-landed data file, following the same pattern that file's own `move`/`converse` entries
  already established as "declared now, consumed by whichever future change builds the command."
  `WildernessGateExit`/`WildernessReturnExit` are that consumer: **on every successful traversal —
  every wilderness step, not only entering and the final return —** both call `world.rules.clock.
  get_world_clock().advance(9000, AdvanceSource.COMMAND, [traversing_object])`, verified end-to-end
  against this project's own `world/rules/clock.py` with a multi-step walk in an `EvenniaTest` (an
  earlier draft only wired the two special-cased legs and left every intermediate step free — caught
  and fixed before implementation; see design.md D-6's correction note). This is the concrete
  resolution of the roadmap's long-deferred "wire movement to `WorldClock`" item, scoped to the one
  place distance genuinely matters (wilderness steps represent 10 km; grid steps remain unwired,
  unchanged from change 12 — see design.md D-8 for why no roadmap item currently owns closing that
  gap either).
- Extend `tests/test_contrib_matrix.py::MATRIX_IMPORTS` with the wilderness symbols this change calls
  (`WildernessMapProvider`, `WildernessRoom`, `WildernessExit`, `create_wilderness`,
  `enter_wilderness`), beyond the class-import-only checks already present.

## Capabilities

### New Capabilities
- `wilderness-terrain`: `WildernessRegion`, `WILDERNESS_REGION_REGISTRY`, `region_for_coordinates()`,
  `terrain_description()` — the deterministic, offline terrain model covering the continent's seven
  named regions.
- `wilderness-map-provider`: `ElosernWildernessMapProvider`, `TerrainRoom`, the 224×224/10 km
  coordinate scale and its arithmetic justification against the stated ~500萬 km² continent area and
  the chosen movement cost.
- `scene-archetype-mixin`: `SceneArchetypeMixin`, its adoption by `TerrainRoom`, and the
  behavior-preserving retrofit of change 12's `GridRoom` onto it.
- `wilderness-gateway`: `WildernessEntryPoint`, `WILDERNESS_ENTRY_REGISTRY`, `WildernessGateExit`,
  `WildernessReturnExit`, `sync_wilderness()`, and the `WorldClock` wiring for wilderness steps — the
  concrete, bidirectional, tested path from 聖潔王都's North Gate into the wilderness and back.

### Modified Capabilities
- `grid-room-typeclasses` (change 12): `GridRoom`'s `scene_archetype` attribute is now inherited from
  `SceneArchetypeMixin` rather than declared directly — the *observable* attribute contract (default
  `None`, unvalidated assignment, persists across a reload) is unchanged, but `GridRoom`'s base
  classes change, which change 12's own design.md D-1 treats as the kind of edit that needs a new
  artifact, not a same-file-only edit (see design.md D-2's corrected reasoning). The delta spec adds
  one scenario asserting `SceneArchetypeMixin` is in `GridRoom.__mro__`.

`world-clock` (change 11) and `lore-startup-sync`/`lore-registries` (change 2) remain unmodified: this
change only adds data to already-open registries/dicts (`rulebook/clock.yaml`'s `command_defaults`,
`sync.py`'s `_ALL_REGISTRIES`), exactly as change 12 itself did to the same files, and neither
capability's documented requirements or scenarios change.

## Impact

- New files: `world/lore/wilderness_regions.py`, `world/lore/wilderness_entry.py`,
  `world/maps/wilderness_provider.py`, plus their test modules.
- Edits to already-landed implementation files (not their OpenSpec artifacts): `typeclasses/rooms.py`
  (`SceneArchetypeMixin` added, `GridRoom` retrofitted, `TerrainRoom` added), `typeclasses/exits.py`
  (`WildernessGateExit`, `WildernessReturnExit` added), `world/lore/sync.py` (`_ALL_REGISTRIES` gains
  two entries), `world/maps/bootstrap.py` (`sync_wilderness()` added, `sync_grid()` untouched),
  `server/conf/at_server_startstop.py` (`at_server_start()` gains one call, after `sync_grid()`),
  `world/rules/rulebook/clock.yaml` (`command_defaults.wilderness_move` added), `tests/
  test_contrib_matrix.py` (`MATRIX_IMPORTS` gains wilderness rows).
- Reads change 12's `ANCHOR_PLACEMENT_REGISTRY` (to validate `WILDERNESS_ENTRY_REGISTRY` keys) and
  change 11's `world.rules.clock.get_world_clock`/`AdvanceSource` (direct import — change 11 is a
  transitive dependency via change 12's own roadmap position, guaranteed importable).
- No database migration concerns (project is unreleased, zero users). No second anchor gets a
  wilderness connection — only `capital_altoria`, the one anchor change 12 gave a grid placement.
