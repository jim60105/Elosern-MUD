## Context

This is roadmap item #12 (design doc §11, Phase 3 "World space"), depending on change 2
(`lore-world-data`) and change 3 (`entity-traits`), both archived. No code exists yet for this
change's scope: `typeclasses/rooms.py` is still Evennia's stock `Room(ObjectParent, DefaultRoom):
pass`; `world/prototypes.py` is the commented-out tutorial stub; `world/lore/anchors.py`'s
`ANCHOR_REGISTRY` (nine entries: three capitals, three elven villages, three dungeons) carries no
coordinate of any kind.

**What already exists for this change to build on, unmodified:**
- Change 2: `ANCHOR_REGISTRY: dict[str, Anchor]` (frozen `Anchor` dataclass: `key`, `kind`,
  `display_name_zh`, `nation_key`, `population`, `floors`, `description` — no placement field) and
  `world/lore/sync.py::sync_all()`, which mirrors eleven registries (including `ANCHOR_REGISTRY`)
  into persistent `LoreRecord` Scripts, called from `server/conf/at_server_startstop.py::
  at_server_start()` on every server start. Confirmed idempotent (`world/lore/tests/test_sync.py`).
- Change 3: `LivingEntity`/`PlayerCharacter`/`NPC`/`Monster` typeclasses, none of which reference a
  room type or coordinate.
- Design doc §4's Contrib Reuse Matrix already names `evennia.contrib.grid.xyzgrid.xyzroom`
  (`XYZRoom`, `XYZExit`) as "Use directly," verified at the class-import level by
  `tests/test_contrib_matrix.py` (change 1). That check does not cover `XYZGrid`, `get_xyzgrid`, or
  `XYMap` — this change's own §4 addendum (below) fills that gap.
- `scipy==1.16.0` is already pinned in `pyproject.toml` (`uv.lock` lines confirm it resolves for
  Python 3.13), satisfying `xyzgrid`'s one hard dependency. Confirmed by actually invoking
  `XYMap.calculate_path_matrix()` (see the "xyzgrid API — verified against Evennia 6.1.0" section
  below) — no new dependency needs to be added.

**What genuinely does not exist yet, and is out of this change's scope by roadmap design.** Change
13 (`map-wilderness`) has not built `WildernessMapProvider`; change 14 (`map-instance`) has not built
`InstanceRoom`, TTL reclamation, or room promotion; change 22 (`art-queue`) has not built the
`SceneArchetype` registry. This change must leave each of those a place to attach without inventing
their content.

## Goals / Non-Goals

**Goals:**
- Resolve the "Anchor has no placement data" gap with a new, separate, keyed registry
  (`ANCHOR_PLACEMENT_REGISTRY`) rather than extending the frozen `Anchor` dataclass.
- Distinguish, by name and by module, the two things "anchor sync" could mean: change 2's existing
  `sync_all()` (data → `LoreRecord` mirror, done) and this change's new `sync_grid()` (map data →
  real `ObjectDB` rooms/exits, new), and make the second one idempotent across repeated server
  starts.
- Add `GridRoom`/`AnchorRoom` to `typeclasses/rooms.py`, with the `scene_archetype` seam design doc
  D10/§8 requires, and make an explicit, justified decision not to forward-declare `InstanceRoom`.
- Build exactly one sample city (聖潔王都, `capital_altoria`) as real, walkable rooms and exits,
  concretely scoped: thirteen rooms, exteriors only, connected to Limbo by one authored bridging
  exit.
- Verify the real `xyzgrid` call signatures this change depends on (`XYZRoom.create`, `XYZGrid.
  add_maps`/`spawn`, `get_xyzgrid`, the `evennia xyzgrid` CLI subcommands) against the installed
  Evennia 6.1.0, and record what was verified.
- Decide how the grid gets built inside a container that only runs `evennia migrate --noinput` and
  `evennia start --log` (`docker-entrypoint.sh`) with no interactive step.

**Non-Goals:**
- **No wilderness layer** (change 13). This change does not build `WildernessMapProvider` or any
  terrain description, and the sample city's grid has no working exit toward one — see D-5.
- **No instance layer, TTL reclamation, or room promotion** (change 14). `InstanceRoom` is not
  forward-declared — see D-3 for why a stub here would be a fake implementation, not a seam.
- **No `SceneArchetype` registry or art pipeline** (change 22). This change adds the `scene_archetype`
  attribute seam on `GridRoom` only; nothing here validates it against a registry, enqueues art, or
  renders an image.
- **No building interiors.** Every named building (inn, guild hall, temple, smithy) is represented by
  exactly one exterior `GridRoom`. Interior rooms are a distinct future concern (plausibly change 14's
  instance-promotion path, or a later content change) — see D-6.
- **No change to `settings.START_LOCATION`.** It stays Limbo (`#2`). See D-7.
- **No movement command wiring to `WorldClock`.** `rulebook/clock.yaml`'s `command_defaults.move: 30`
  (change 11, `world-clock`, D-9) remains declared data only; this change adds real `Exit` objects
  that Evennia's own auto-generated exit-traversal command already handles, but does not add a
  bespoke `move` command or call `WorldClock.advance()` on traversal — see D-8.
- **No other eight anchors' grid placement.** Only `capital_altoria` gets a `AnchorPlacement` entry
  and real rooms in this change. `ANCHOR_PLACEMENT_REGISTRY` is deliberately left open for whichever
  future change places the rest; this change does not assign that work to anyone.
- No backward-compatibility, migration, or deprecation handling — the project is unreleased with zero
  users.

## Decisions

### D-1. `AnchorPlacement`: a new, separate registry — not an extension of the frozen `Anchor` dataclass.

```python
# world/lore/anchor_placement.py
@dataclass(frozen=True)
class AnchorPlacement:
    anchor_key: str          # must exist in ANCHOR_REGISTRY (checked by a test, not the dataclass)
    zcoord: str               # the XYMap's Z-coordinate/name this anchor's grid lives on
    entrance_xy: tuple[int, int]  # the (X, Y) of the AnchorRoom within that map

ANCHOR_PLACEMENT_REGISTRY: dict[str, AnchorPlacement] = {
    "capital_altoria": AnchorPlacement("capital_altoria", "capital_altoria", (2, 2)),
}
```

**Why a separate registry, not a fourth/fifth field on `Anchor` itself.** Two reasons, both grounded
in AGENTS.md's lore invariants:

1. **Different rate of change, different owner.** `Anchor` (change 2, archived) encodes lore facts
   that do not change once written — population, nation, floor count, the kind of place it is. Grid
   placement is a spatial/engineering fact that *will* change: this change places one anchor;
   changes 13/14/22 and any future world-building pass will place, re-lay-out, or resize others.
   Coupling a fact that changes rarely (lore) with one that changes often (grid layout) inside one
   frozen dataclass means every future grid change touches `world/lore/anchors.py` — the one file
   every other registry's `home_anchor_key`/`capital_anchor_key` cross-reference already points at —
   for a reason that has nothing to do with lore.
2. **Not every anchor has a placement yet, and that must be representable without a sentinel.** Six
   of the nine `ANCHOR_REGISTRY` entries get no grid presence in this change (or, likely, changes 13/
   14 either, since dungeons plausibly become instance/virtual content, not permanent grid rooms). A
   field directly on `Anchor` would need to be `xy: tuple[int,int] | None` on every entry, six of
   which would carry an unexplained `None` forever, with no test asserting *why*. A separate,
   independently-keyed registry that simply does not contain an entry for an anchor without a
   placement is a cleaner, more honest expression of "not yet decided" than a nullable field bolted
   onto an otherwise-complete dataclass — the same reasoning `settlement-stage-order`'s open
   `_EVENT_SOURCES` registry (change 11) already used for "not every boundary-stage kind has a source
   registered yet."

This still satisfies every AGENTS.md lore invariant: `AnchorPlacement` is a frozen dataclass, the
registry is keyed (by `anchor_key`), and it is mirrored into `LoreRecord` Scripts by the identical
idempotent mechanism every other lore registry uses (D-2) — it is not a duplicated, ungoverned
constant living outside the registry discipline, it is one more registry inside it.

**Alternative considered and rejected**: editing `Anchor` to add `grid_xy: tuple[int, int] | None =
None` directly. Rejected for the two reasons above. This project has precedent for a downstream
change editing an archived change's *implementation* file (change 11 added one call to change 8's
`CmdCast`) — but that precedent is for wiring a call site, not for redefining an already-shipped,
already-tested frozen dataclass's shape across all nine of its existing literal instances for a
concern (spatial layout) that belongs to a different change's charter.

### D-2. `ANCHOR_PLACEMENT_REGISTRY` is mirrored into `LoreRecord` Scripts the same way every other
lore registry is — a small, additive edit to change 2's `world/lore/sync.py`.

```python
# world/lore/sync.py — _ALL_REGISTRIES gains one entry
from .anchor_placement import ANCHOR_PLACEMENT_REGISTRY
_ALL_REGISTRIES["anchor_placements"] = ANCHOR_PLACEMENT_REGISTRY
```

This is the same "downstream change touches upstream code, not upstream artifacts" pattern
`world-clock`'s design.md documented for its own `CmdCast` edit. `lore-startup-sync`'s own
requirement text scopes itself to "every lore registry defined by this change" (change 2's own
eleven, enumerated by name) — adding a twelfth registry from a later change does not violate that
requirement; `sync_all()`'s actual behavior (iterate `_ALL_REGISTRIES`, mirror every entry, idempotent
on repeat) is unchanged, it now iterates over one more dict. No edit to `lore-startup-sync`'s
`spec.md` is needed, and none is made.

### D-3. `sync_all()` (data mirror) and `sync_grid()` (room/exit instantiation) are two different
functions in two different modules, with two different idempotency mechanisms — this is the direct
resolution of the "anchor sync is an overloaded term" gap.

| | `world/lore/sync.py::sync_all()` (change 2, existing) | `world/maps/bootstrap.py::sync_grid()` (this change, new) |
|---|---|---|
| What it creates | `LoreRecord` Script objects — a data mirror, never puppeted, never entered | `XYZRoom`/`XYZExit`/plain `Exit` objects — real, walkable game-world state |
| Idempotency mechanism | `search_script(key)`, create-or-overwrite by deterministic key string | `XYMap.spawn_nodes()`/`spawn_links()`'s own coordinate-existence check (verified below, D-4) |
| Who calls it, and when | `at_server_start()`, always | `at_server_start()`, always, called immediately after `sync_all()` |
| Failure mode if skipped | Lore data becomes stale in `LoreRecord`s (nothing else reads them directly at runtime today) | The sample city does not exist; the game has no walkable content |

Naming them distinctly (`sync_all` vs. `sync_grid`) and putting them in distinct modules
(`world/lore/` vs. the new `world/maps/`) is the concrete fix for the ambiguity flagged in the task:
neither name is a synonym for "mirror lore data," and neither module is responsible for both concerns.
A reader grepping for "anchor sync" in this codebase after this change lands finds two clearly
different things, not one overloaded one.

### D-4. `xyzgrid` API — verified against the installed Evennia 6.1.0, not assumed from the design
doc's §4 matrix alone.

Verified by direct inspection of `evennia/contrib/grid/xyzgrid/{xyzgrid,xyzroom,xymap,launchcmd,
prototypes}.py` in the installed package, and by actually running the parser (`uv run --locked
python`, `DJANGO_SETTINGS_MODULE=server.conf.settings`, `django.setup()`) against the exact map
string this change uses for the sample city (D-6) — not a documentation example.

**`XYZGrid` (module `xyzgrid/xyzgrid.py`) — a `DefaultScript` singleton, one per game:**
```python
class XYZGrid(DefaultScript):
    def add_maps(self, *mapdatas) -> None: ...      # mapdatas: dict with "zcoord"/"map"/"legend"/
                                                       # "prototypes"/"options" keys; idempotent —
                                                       # just a dict assignment keyed by zcoord
    def spawn(self, xyz=("*", "*", "*"), directions=None) -> None: ...
    def get_room(self, xyz, **kwargs): ...            # returns a queryset via XYZRoom.objects.filter_xyz
    def get_exit(self, xyz, name="north", **kwargs): ...
    def get_map(self, zcoord): ...
    def reload(self) -> None: ...                     # rebuilds the in-memory XYMap cache from
                                                       # self.db.map_data. The `.grid` property only
                                                       # calls this lazily when `self.ndb.grid is
                                                       # None` — and it is NOT `None` immediately
                                                       # after `get_xyzgrid()` creates a fresh grid,
                                                       # because `get_xyzgrid()` itself already calls
                                                       # `.reload()` once (setting `ndb.grid = {}`,
                                                       # not `None`) before returning. `add_maps()`
                                                       # does not call `reload()` and does not touch
                                                       # `ndb.grid`. This is load-bearing and is
                                                       # exactly the bug D-5 corrects — see there.

def get_xyzgrid(print_errors=True) -> XYZGrid: ...     # module-level helper; creates the singleton
                                                       # Script if none exists yet (calling
                                                       # `.reload()` once as part of creation — see
                                                       # above), else fetches the existing one and
                                                       # reloads it only if `ndb.loaded` is falsy in
                                                       # THIS process. This is the only sanctioned
                                                       # way to obtain the grid.
```

**`XYZRoom.create()` (module `xyzgrid/xyzroom.py`) — the coordinate-aware room factory:**
```python
@classmethod
def create(cls, key, account=None, xyz=(0, 0, "map"), **kwargs) -> tuple[object | None, list[str]]:
    ...  # returns (room, errors); rejects if a room already exists at that (x, y, z)
```
`GridRoom`/`AnchorRoom` (D-6) do not call this directly — `sync_grid()` goes through the higher-level
`XYZGrid.spawn()` → `XYMap.spawn_nodes()` → `MapNode.spawn()` path (below), which itself calls
`XYZRoom.create()` (or the equivalent typeclass named in the coordinate's prototype) only when no room
exists yet at that XYZ.

**`XYZExit` (same module) — coordinate-aware exit; `.xyz` (source) and `.xyz_destination` properties,
`.create()` mirrors `XYZRoom.create()`'s shape.** Used directly (per design doc §4's original "Use
directly" call, reconfirmed) — this change adds no project-owned `Exit` subclass, since neither
`scene_archetype` nor `anchor_key` is an exit concern, and the contrib class itself is unmodified and
remains directly usable elsewhere. **Amended 2026-08-01 (change `map-movement-clock`, roadmap item
13b):** "remains directly usable elsewhere" no longer describes the state of this project once that
change lands. It adds a `("*", "*", "*")` wildcard link-prototype override to this change's own
`ALTORIA_CAPITAL_MAP_DATA["prototypes"]`, so all twelve of the sample city's links — the only
`xyzgrid` map anywhere in the current roadmap — spawn as `typeclasses.exits.CostedXYZExit`
(`MovementCostMixin` composed with `XYZExit`, unmodified in every other respect) instead of the bare
contrib class. `XYZExit` itself is still unmodified and still directly importable/usable — nothing
about the contrib class changes — but there is no longer an "elsewhere" in this project where a bare
`XYZExit` is actually instantiated. See `openspec/changes/map-movement-clock/design.md` D-4/D-9 for
the full mechanics and why this is expressed as a delta spec against `sample-city-altoria` rather than
an edit to this change's own implementation files.

**Idempotency of the spawn step itself, verified by reading the actual spawn implementation
(`xymap.py::XYMap.spawn_nodes`, `xymap_legend.py::MapNode.spawn`/`spawn_links`), not merely asserted
by the README:**
- `spawn_nodes()` queries `XYZRoom.objects.filter_xyz(xyz=(x, y, self.Z))` for rooms that exist on
  disk but are no longer on the map (deletes them), then calls `node.spawn()` for every node still on
  the map.
- `MapNode.spawn()` calls `NodeTypeclass.objects.get_xyz(xyz=xyz)`; on `DoesNotExist` it creates a new
  room via `Typeclass.create(...)`; **if the room already exists, it does not create a second one** —
  it falls through to `spawner.batch_update_objects_with_prototype(self.prototype, objects=[nodeobj],
  exact=False)`, which updates the existing room's Attributes from the prototype rather than
  duplicating it.
- `MapNode.spawn_links()` performs the symmetric-difference check between the map's declared links and
  the exits that already exist at that XYZ, deleting removed links and creating only genuinely missing
  ones — never re-creating an exit that is already there.

**This idempotency is conditional on `spawn()` actually being handed a non-empty, up-to-date
`self.grid` — a separate, sequencing-level correctness question from the one above, resolved in D-5.**
Calling `add_maps()` then `spawn()` with no `reload()` between them is *not* idempotent-and-correct,
it is silently a no-op on first boot (D-5 walks through exactly why, since it is the more serious of
the two findings). The conclusion "repeated calls create no duplicates" is correct and still holds —
but only once D-5's corrected three-call sequence (`add_maps()` → `reload()` → `spawn()`) is used.

**CLI subcommands (module `xyzgrid/launchcmd.py::xyzcommand`), confirmed by reading the dispatch
table**: `help | list | init | add | spawn | initpath | delete`. Confirmed by reading `_option_add`/
`_option_spawn` directly (not merely their existence): `_option_add` calls `grid.add_maps(*maps)` then
`grid.reload()` — two calls, not one, and the second is load-bearing (D-5). `_option_spawn` calls only
`grid.spawn(xyz=...)`, with no `add_maps()`/`reload()` of its own — it relies on `get_xyzgrid()`'s own
top-of-function reload-if-`ndb.loaded`-is-falsy check, which fires because `add`/`spawn` are two
separate `evennia xyzgrid` process invocations, and `ndb.loaded` (like all `ndb` state) does not
survive between them. This is *not* the same mechanism this change's own single-process `sync_grid()`
can rely on — see D-5.

**Settings this change must add, confirmed against `evennia/settings_default.py` and the contrib's own
`prototypes.py`/`launchcmd.py`**: `EXTRA_LAUNCHER_COMMANDS` defaults to `{}` (must add the `"xyzgrid"`
key); `PROTOTYPE_MODULES` defaults to `["world.prototypes"]` (must append `"evennia.contrib.grid.
xyzgrid.prototypes"`, which supplies the `"xyz_room"`/`"xyz_exit"` prototype parents this change's own
`GRID_ROOM`/`ANCHOR_ROOM` prototypes chain from — `world.prototypes` is already present by default, so
this change's own prototypes need no additional settings edit beyond the contrib's own module).

### D-5. The grid is spawned automatically at server start, from Python — the `evennia xyzgrid` CLI
stays available for operators but is not part of the boot path.

`docker-entrypoint.sh` (change 1, unmodified by this change) runs exactly two commands: `evennia
migrate --noinput` then `exec evennia start --log`. There is no interactive shell step, and no
container-build-time step either (the grid must exist against whatever database volume is mounted at
runtime, which may be a fresh empty one). The contrib's own documented workflow —
`evennia xyzgrid add <module>` then `evennia xyzgrid spawn` then `evennia reload` — is an *external*,
human-operator-driven, multi-command process explicitly described as running "outside of the regular
evennia process." That workflow cannot be the sole path to a spawned sample city, because nothing in
the container's boot sequence would ever run it.

**Decision**: `world/maps/bootstrap.py::sync_grid()` calls `get_xyzgrid()`, then `.add_maps(
ALTORIA_CAPITAL_MAP_DATA)`, then **`.reload()`**, then `.spawn()` — three calls, not two. This is
called from `server/conf/at_server_startstop.py::at_server_start()` — the exact hook change 2 already
uses for `sync_all()`, right after it. This makes grid provisioning part of ordinary server startup,
requiring no operator action on a fresh container boot, mirroring the precedent this project already
set for lore data.

**Correction recorded here, not silently fixed — a rubber-duck review caught a genuine defect in an
earlier draft of this decision, which claimed `add_maps()` + `spawn()` (two calls, no `reload()`)
"matches the CLI's `add`/`spawn` subcommands' internal calls." That claim was wrong on the facts, and
the two-call sequence it justified was broken. Traced precisely:**
1. On a fresh database, `get_xyzgrid()` finds no `XYZGrid` Script, creates one, and calls `.reload()`
   itself as part of that creation (see D-4). At that moment `self.db.map_data == {}` (set in
   `at_script_creation()`), so this first `reload()` sets `self.ndb.grid = {}` — empty, but **not**
   `None`.
2. `add_maps(*mapdatas)` only writes `self.db.map_data[zcoord] = mapdata`. It never touches
   `self.ndb.grid` and never calls `.reload()` itself.
3. `XYZGrid.grid`, the property `spawn()` reads, is `if self.ndb.grid is None: self.reload(); return
   self.ndb.grid`. Since step 1 already left `ndb.grid` at `{}` (falsy but not `None`), this guard does
   **not** fire, and the property returns the stale, empty `{}` from before `add_maps()` ran.
4. `spawn(xyz=("*","*","*"))` takes `xymaps = self.grid` — `{}` — and iterates zero maps. It creates
   zero rooms and raises nothing, so the failure is silent.
5. On a *second* server start (a fresh process), `get_xyzgrid()` finds the existing `XYZGrid` Script,
   and since `ndb.loaded` does not survive between processes, it reloads unconditionally — this time
   correctly picking up the `db.map_data` the first start's `add_maps()` call had already persisted.
   **The sample city would silently fail to exist on the exact fresh-container-boot scenario this
   change exists to serve, and would only appear after a second, unrelated server start** — the worst
   possible failure mode for a task whose entire job is "make sure this exists on first boot."

**This is why `.reload()` is not optional between `add_maps()` and `spawn()` within one process.**
`_option_add`'s CLI implementation already does this correctly (`grid.add_maps(*maps)` then
`grid.reload()`, per D-4) — the earlier draft of this decision misread that as "the same thing
`sync_grid()` should do with `add_maps()`+`spawn()`," missing that `reload()`, not `spawn()`, is the
call `_option_add` actually pairs with `add_maps()`, and that `_option_spawn`'s own correctness in the
CLI workflow depends on it running as a *separate process* from `_option_add`, which `sync_grid()`
does not have the luxury of.

The `evennia xyzgrid` CLI remains fully functional (the settings wiring in D-4 is unconditional) for
manual operator use — inspecting the grid (`list`/`show`), forcing a rebuild after editing map data
(`spawn`), or tearing it down during development (`delete`) via `podman exec` into a running
container or a local dev shell. It is a debugging and authoring tool, not a deployment dependency.

**Risk noted, not solved here**: `spawn()` walks every node/link on every registered map on every
server start (boot and reload alike), which is O(rooms) work done synchronously in `at_server_start()`
before the server accepts connections — acceptable at thirteen rooms, and each `MapNode.spawn()` call
already short-circuits to an Attribute-only update once the room exists, but this does not scale
indefinitely as later changes (13, 14, and any future content) add more maps. This change accepts that
cost now, at a scale where it is negligible, without designing a lazier provisioning strategy no
current content needs.

### D-6. `GridRoom`/`AnchorRoom` and the concrete sample city.

```python
# typeclasses/rooms.py — added, Room (stock) is left as-is
from evennia.contrib.grid.xyzgrid.xyzroom import XYZRoom
from evennia.typeclasses.attributes import AttributeProperty


class GridRoom(XYZRoom):
    """A room on the xyzgrid layer (design doc D3's 'Grid' layer)."""

    # Forward-declared seam for design doc D10/§8 (change 22, art-queue). Unresolved against any
    # registry here -- no SceneArchetype registry exists yet. Mirrors the treatment already given
    # to NPC.schedule and Monster.behaviour_tree (change 3): the attribute exists so change 22 has
    # somewhere to read from and write validation against; nothing here enforces a value.
    scene_archetype: str | None = AttributeProperty(default=None)


class AnchorRoom(GridRoom):
    """The one canonical room per anchor (design doc D3's 'Anchor' layer), still a real xyzgrid
    node -- 'Anchor' and 'Grid' are complementary, not mutually exclusive: an anchor's canonical
    room is a GridRoom with one extra fact (which ANCHOR_REGISTRY entry it represents)."""

    anchor_key: str | None = AttributeProperty(default=None)
```

**Why `AnchorRoom` is a `GridRoom` subclass, not a sibling class or a non-grid room type.** Design
doc D3 names four *layers*, which reads at first as four disjoint room types. Reading it against
`xyzgrid`'s actual data model changes that: `XYZRoom` (and therefore `GridRoom`) is the only
typeclass with the X/Y/Z-coordinate machinery (`Tags`, pathfinding, `return_appearance`'s map
rendering) that a walkable capital city needs. An `AnchorRoom` that was *not* a `GridRoom` would need
to either duplicate that coordinate machinery or live outside the grid entirely — but "the capital's
main plaza" is exactly the kind of place that needs a coordinate, an ASCII map, and pathfinding like
every other room in the city around it. The distinguishing fact an `AnchorRoom` needs is narrow — "I
am the one room `ANCHOR_REGISTRY[anchor_key]` refers to" — so it is modeled as that one additional
field on top of `GridRoom`, not a parallel hierarchy.

**Sample city: 聖潔王都 (`capital_altoria`), thirteen rooms, verified topology.** Chosen over
`capital_grandia` for no lore-preference reason (`world_info.md` states no in-fiction basis for
picking one capital over another for a first sample) — `capital_altoria`'s population (600,000) sits
between the other two capitals (800,000 / 400,000), making it a representative "medium" capital rather
than the largest or smallest. The map string below was written against `xyzgrid`'s documented format
and then **actually parsed** with `evennia.contrib.grid.xyzgrid.xymap.XYMap.parse()` and `.
calculate_path_matrix()` (confirming `scipy` resolves the shortest-path matrices without error) in
this project's own `uv`-managed environment — the coordinates and adjacency below are the verified
parser output, not a hand-traced guess:

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

| (X,Y) | Room (zh) | English gloss | Typeclass | Links |
|---|---|---|---|---|
| (2,0) | 南門 | South Gate | `GridRoom` | n → (2,1); one non-grid `Exit` out to Limbo (D-7) |
| (2,1) | 南大道 | South Main Street | `GridRoom` | n/s/e/w — the four-way junction |
| (1,1) | 旅店外 | Inn Exterior | `GridRoom` | e → (2,1) |
| (3,1) | 冒險者公會外 | Adventurers' Guild Exterior | `GridRoom` | w → (2,1) |
| (2,2) | 中央廣場 | Central Plaza | `AnchorRoom` (`anchor_key="capital_altoria"`) | n/s/e/w — the anchor's canonical room |
| (0,2) | 鐵匠鋪外 | Blacksmith Exterior | `GridRoom` | e → (1,2) |
| (1,2) | 市場街 | Market Street | `GridRoom` | e/w |
| (3,2) | 神殿街 | Temple Street | `GridRoom` | e/w |
| (4,2) | 光明神殿外 | Temple of Light Exterior | `GridRoom` | w → (3,2) |
| (2,3) | 北大道 | North Main Street | `GridRoom` | n/s/e/w — the four-way junction |
| (1,3) | 貴族區門口 | Noble Quarter Gate | `GridRoom` | e → (2,3) |
| (3,3) | 城牆哨塔 | Wall Watchtower | `GridRoom` | w → (2,3) |
| (2,4) | 北門 | North Gate | `GridRoom` | s → (2,3); no further exit — reserved for change 13 (D-5 of that future change, not this one) |

Twelve links total, a tree (no cycles) — every room reachable from every other room, matching design
doc §10's Evennia-integration testing expectation ("rooms, exits, spawn"). `(2,2)` (中央廣場) is the
`AnchorRoom`, deliberately the plaza rather than the gate: it is the room every future "return to the
capital"/teleport-to-anchor feature should target, and a capital's central plaza is the more natural
canonical point than its edge.

**Why exteriors only, no interiors (Non-Goal, restated with reasoning here).** Every building the
table names above (inn, guild, temple, smithy) is a single street-facing `GridRoom` with a description
gesturing at the building without a door the player can walk through. Building an interior for even
one of them means deciding, ahead of change 21 (`scene-builder`) and change 16 (`guild-economy`), what
an inn's or guild hall's actual functional interior looks like — a decision this change's charter
("Anchor sync, xyzgrid grid layer, one sample city") does not ask for and the roadmap assigns to no
change before 21. Keeping the sample city to street-level exteriors keeps this change's scope to
exactly what §11 asked for: proving the grid layer works, not authoring the capital's full floor plan.

### D-7. The sample city connects to the rest of the world through exactly one authored, non-grid
`Exit` from Limbo — not through `settings.START_LOCATION`, and not (yet) through wilderness.

`sync_grid()` also idempotently ensures a plain `typeclasses.exits.Exit` named "南門" (aliases:
`south gate`, `altoria`) exists at Limbo leading to `(2, 0, "capital_altoria")`, and a return exit
named "離開王都" (aliases: `leave`, `limbo`) at the South Gate room leading back to Limbo — the exact
non-grid-to-grid bridging idiom the `xyzgrid` README documents as the sanctioned way to embed grid
space inside the wider, non-grid world (`open <name>;<aliases> = (x,y,z)`), implemented here via plain
`Exit.create()` rather than the in-game `open` command, since this runs at server start with no
logged-in builder. Idempotency for this pair follows the same shape as change 2's `sync_one()`: look
up an existing exit by `(location, key)` before creating one.

**Limbo lookup convention — decided explicitly, not left for the implementer to guess.** `sync_grid()`
locates Limbo by **`key="Limbo"`** (an ordinary object search), not by dbref `#2`. Two facts drove
this, both checked rather than assumed:
- In a real container boot, `evennia migrate` followed by `evennia start` runs Evennia's
  `initial_setup.create_objects()` before `at_server_start()` ever fires, and that function
  unconditionally creates and names object `#2` `"Limbo"` — so `key="Limbo"` and dbref `#2` agree in
  production, and either lookup would work there.
- They do **not** agree inside this project's own test suite. `EvenniaTest.setUp()` (the base class
  every one of the 30+ existing test modules under `world/rules/tests/`, `world/lore/tests/`, and
  `typeclasses/tests/` uses) never runs `initial_setup` — it builds its own fixture rooms, and dbref
  `#2` in an `EvenniaTest`-backed database is that fixture's `room2` (key `"Room2"`), not Limbo.
  `settings.DEFAULT_HOME`, which also resolves to the literal string `"#2"`, does not help distinguish
  the two. A `sync_grid()` written to look up Limbo by dbref would attach the bridging exits to
  whatever object happens to hold `#2` in whichever database is running — passing tests by
  coincidence of fixture creation order rather than by testing the behavior D-7 actually describes.

**Absent-Limbo behavior: log and skip, never raise.** If no object keyed `"Limbo"` exists when
`sync_grid()` runs (a state that should not occur in production, per the first bullet above, but is
easy to hit accidentally in a hand-built test fixture), `sync_grid()` logs a warning and skips
creating the bridging exit pair, without raising. This matches this project's established
graceful-degradation posture (the generative layer's guardrail-degradation table, §7.5 of the design
doc) applied to a much smaller case: the sample city and its rooms still exist and remain reachable by
coordinate, builder tooling, or the `evennia xyzgrid` CLI even if the one convenience bridge from
Limbo could not be created — a missing bridge should never prevent the server from starting.

**Test convention, stated so task groups 8/9/11 do not each invent their own.** Any test that wants to
exercise the bridging-exit behavior itself must create (or rename an existing fixture room to) a room
keyed exactly `"Limbo"` before calling `sync_grid()`. Tests that only care about the grid/rooms
themselves (for example, most of task group 6's map-parsing tests) need no such setup and are
unaffected by whether a `"Limbo"`-keyed room exists.

**Why not `settings.START_LOCATION`.** Repointing the default new-character spawn point at the sample
city is a genuine, separate decision about onboarding that no roadmap item through change 16 has asked
for yet, and every `EvenniaTest`-based fixture across the whole existing test suite (thirty-plus files
under `world/rules/tests/`, `world/lore/tests/`, `typeclasses/tests/`) implicitly depends on Evennia's
own default test-room setup, not on any particular game-world room existing. Changing `START_LOCATION`
now is an unforced, global behavior change with no consumer asking for it; leaving it at Limbo costs
nothing and this change's own tests reach the sample city by coordinate or by key, never by relying on
where a freshly created character starts.

**Why not a wilderness link.** Change 13 depends on this change, not the reverse — `WildernessMapProvider`
does not exist. The North Gate `(2,4)` is deliberately a dead end today; making it more than that is
change 13's decision, exercised on data change 13 owns.

## Risks / Trade-offs

- **[Risk] `sync_grid()` runs synchronously in `at_server_start()`, before the server accepts
  connections.** At thirteen rooms this is fast; if a much larger map were added by a careless future
  change, boot time would grow with it. → **Mitigation**: none added here (Non-Goal); flagged in D-5
  as a known, currently-negligible cost, not silently ignored.
- **[Risk] Two idempotency mechanisms in one boot sequence (`search_script`-based for lore,
  coordinate-existence-based for rooms) could drift out of sync if `ANCHOR_PLACEMENT_REGISTRY` names a
  `zcoord`/`entrance_xy` that `world/maps/altoria_capital.py`'s actual `XYMAP_DATA` does not contain a
  matching node for.** → **Mitigation**: a test asserts `ANCHOR_PLACEMENT_REGISTRY["capital_altoria"].
  entrance_xy` matches the `AnchorRoom`'s actual spawned `.xyz` after `sync_grid()` runs, catching drift
  directly rather than trusting the two files to agree by construction.
- **[Consequence, by design, not an accidental collision] Installing `XYZGridCmdSet` on
  `CharacterCmdSet` replaces `teleport`/`open` with `CmdXYZTeleport(building.CmdTeleport)`/
  `CmdXYZOpen(building.CmdOpen)`.** This is the contrib's documented, intended override mechanism —
  both subclasses deliberately reuse their parent's command key so the XYZ-aware versions take over
  in place, not a naming accident this change happened to trigger. → **Noted so a future change does
  not mistake it for a bug**: none of changes 1-11 touch `teleport`/`open`, so nothing is displaced
  today; if a future change wants to further customize either command, it is customizing on top of
  the contrib's own subclass, by the contrib's own design.
- **[Trade-off] `AnchorRoom` being a `GridRoom` subclass means an anchor's canonical room is always
  grid-backed** — this change makes no provision for an anchor whose canonical point is *not* on any
  `xyzgrid` map (e.g., a purely virtual/wilderness anchor). None of the nine `ANCHOR_REGISTRY` entries
  need that today (capitals and elven villages are settlements; dungeons are plausibly grid maps too),
  so this is accepted rather than generalized against a need that does not exist yet.
- **[Risk] The `scene_archetype` seam lives on `GridRoom` only, and later map-layer changes are
  unlikely to share that base class.** Verified: `evennia.contrib.grid.wilderness.wilderness.
  WildernessRoom` subclasses `DefaultRoom` directly, not `XYZRoom` — change 13 (`map-wilderness`)
  therefore cannot inherit this change's `scene_archetype` attribute for free. Design doc §4 also
  routes the instance layer through core `evennia.prototypes.spawner.spawn()`, not through `XYZRoom`,
  so change 14's `InstanceRoom` is unlikely to descend from `GridRoom` either. Left unresolved, change
  22 (`art-queue`) could end up reading `scene_archetype` from two or three unrelated typeclasses with
  no shared contract. → **Not solved here** — change 12 should not decide change 13 or 14's room
  hierarchy on their behalf — but named so 13/14/22 inherit this analysis instead of rediscovering it:
  the likely resolution is a small, standalone `SceneArchetypeMixin` (or equivalent plain-attribute
  contract) that `GridRoom`, a future `WildernessRoom` subclass, and a future `InstanceRoom` can each
  adopt independently of sharing `XYZRoom` as a common ancestor.

## xyzgrid API — verification summary (for the record)

Everything below was checked against the installed `evennia==6.1.0` package in this project's own
`.venv` (`uv run --locked python`, `django.setup()` against `server.conf.settings`), not inferred from
documentation:

- `evennia.contrib.grid.xyzgrid.xyzgrid.XYZGrid` — `DefaultScript` subclass; `add_maps(*mapdatas)`,
  `spawn(xyz=("*","*","*"), directions=None)`, `get_room(xyz, **kwargs)`, `get_exit(xyz, name="north",
  **kwargs)`, `get_map(zcoord)`, `reload()`. `get_xyzgrid(print_errors=True)` is the module-level
  singleton accessor.
- `evennia.contrib.grid.xyzgrid.xyzroom.XYZRoom` — `DefaultRoom` subclass; `.xyz` property (from
  Tags), `.create(key, account=None, xyz=(0,0,"map"), **kwargs)` classmethod returning `(room, errors)`
  and rejecting a duplicate coordinate.
- `evennia.contrib.grid.xyzgrid.xyzroom.XYZExit` — `DefaultExit` subclass, symmetric `.xyz`/`.
  xyz_destination` properties and `.create()`.
- `evennia.contrib.grid.xyzgrid.xymap.XYMap` — `.parse()`, `.calculate_path_matrix()` (this is where
  `scipy` is actually exercised — confirmed working against this change's own map string),
  `.spawn_nodes(xy=("*","*"))`, `.spawn_links(xy=("*","*"), nodes=None, directions=None)`.
- `evennia xyzgrid <op>` CLI (`launchcmd.py::xyzcommand`) — confirmed dispatch table: `help | list |
  init | add | spawn | initpath | delete`. Confirmed `_option_add` calls `add_maps()` then `reload()`
  (two calls); `_option_spawn` calls only `spawn()`, relying on `get_xyzgrid()`'s own per-process
  reload-if-not-loaded check rather than an explicit `reload()` of its own (D-5).
- Settings: `EXTRA_LAUNCHER_COMMANDS` (default `{}`), `PROTOTYPE_MODULES` (default
  `["world.prototypes"]`), `XYZGRID_USE_DB_PROTOTYPES` (absent by default — `getattr`-guarded in the
  contrib's own code, defaults to module-prototypes-only, which is what this change uses).
- **`add_maps()` does not itself make `spawn()` see the new map data — `reload()` must run in
  between, within the same process.** This was verified the hard way: an earlier draft of this design
  claimed a bare `add_maps()` + `spawn()` sequence was sufficient and safe, a rubber-duck review
  caught that it silently spawns zero rooms on first boot, and re-reading `xyzgrid.py`'s `grid`
  property and `get_xyzgrid()`'s creation path against the actual source confirmed the review was
  right (full trace in D-5). The corrected, verified sequence is `add_maps()` → `reload()` → `spawn()`.
- Idempotency of the `spawn()` step itself (once handed correct, reloaded map data), confirmed by
  reading `xymap.py::XYMap.spawn_nodes`/`xymap_legend.py::MapNode.spawn`/`MapNode.spawn_links`
  directly (D-4) — not merely citing the README's claim.
- The thirteen-room, twelve-link sample-city topology (D-6) was parsed and path-matrix-computed
  successfully against the real `XYMap` class in this project's environment.

This supersedes nothing in design doc §4 (the original matrix's "Use directly" call for `XYZRoom`/
`XYZExit` is reconfirmed, not corrected) — it is an addendum at the call-signature level the original
matrix did not need to go to.
