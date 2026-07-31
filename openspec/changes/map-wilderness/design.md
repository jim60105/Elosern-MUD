## Context

This is roadmap item #13 (design doc §11, Phase 3 "World space"), depending on change 12
(`map-anchor-grid`). Change 12 is committed to this repository but **not yet implemented** —
`typeclasses/rooms.py` is still the stock `Room(ObjectParent, DefaultRoom): pass`, `typeclasses/
exits.py` is still the stock `Exit(ObjectParent, DefaultExit): pass`, and no `GridRoom`/`AnchorRoom`
exists anywhere in the repository today (confirmed by reading both files directly). Everything this
design says about `GridRoom` describes change 12's own frozen design/spec for it, which this change
builds on without altering its observable contract. By the time change 13 is actually implemented,
change 12 will already be implemented (roadmap dependency order), so every task below that touches
`typeclasses/rooms.py::GridRoom` is editing real, already-existing code, not a proposal document.

**What already exists for this change to build on, unmodified:**
- Change 12's design: `GridRoom(XYZRoom)` carrying `scene_archetype: str | None`, `AnchorRoom(
  GridRoom)` carrying `anchor_key: str | None`, `ANCHOR_PLACEMENT_REGISTRY` (one entry,
  `capital_altoria`), the thirteen-room sample city, and — load-bearing for this change — the North
  Gate room at `(2, 4, "capital_altoria")` deliberately has exactly one exit (south, back into the
  city) and is explicitly reserved by change 12's own design.md D-7 as this change's attachment
  point: "The North Gate `(2,4)` is deliberately a dead end today; making it more than that is change
  13's decision, exercised on data change 13 owns."
- Change 12's own design.md flags the exact seam this change is asked to resolve: `evennia.contrib.
  grid.wilderness.wilderness.WildernessRoom` subclasses `DefaultRoom` directly, not `XYZRoom`, so "change
  13 (`map-wilderness`) therefore cannot inherit this change's `scene_archetype` attribute for free
  ... the likely resolution is a small, standalone `SceneArchetypeMixin` ... that `GridRoom`, a future
  `WildernessRoom` subclass, and a future `InstanceRoom` can each adopt independently of sharing
  `XYZRoom` as a common ancestor." This design accepts that recommendation (D-2).
- Change 11 (`world-clock`, archived, implemented): `world/rules/clock.py::get_world_clock()`
  (returns a fresh `WorldClock(tick)` snapshot backed by a persistent, non-ticking
  `WorldClockScript`), `WorldClock.advance(seconds, source, entities) -> list[ScheduledEvent]`,
  `AdvanceSource.COMMAND`. `commands/action.py::CmdCast` already calls `get_world_clock().advance(
  result.time_cost_seconds, AdvanceSource.COMMAND, [self.caller])` on a successful action — this
  change's own `WorldClock` integration follows the identical call shape, verified directly (see D-6).
  `rulebook/clock.yaml::command_defaults` already carries `move: 30` and `converse: 60` as declared,
  uninvoked data — change 12 explicitly left `move` inert (its own D-8 Non-Goal: "No movement command
  wiring to `WorldClock`"); this change adds a **new**, distinct key (`wilderness_move`) rather than
  wiring the existing `move` constant, since a wilderness step and a grid step represent different
  real distances (D-5).
- Change 2 (`lore-world-data`, archived): `world/lore/sync.py::_ALL_REGISTRIES`/`sync_all()`, already
  extended once by change 12 for `ANCHOR_PLACEMENT_REGISTRY` — the same additive pattern this change
  repeats for two more registries.
- `world_info.md`'s geography section (gitignored, canonical lore source — see AGENTS.md), which
  names the continent's area (~500萬 km² / ~5,000,000 km²) and seven terrain regions: 中央山脈
  (spans the continent north-south, elf villages hidden inside, a neutral zone no nation controls),
  東部大平原 (Grandia's core territory, fertile plains), 東南海岸 (Grandia's southern ports),
  西部丘陵與谷地 (Altoria's core territory, mineral-rich), 西南海岸 (Altoria's southern ports),
  西北高地森林 (Valhalla's core territory, forest and highland), 北部深林 (untamed, dungeon-dense,
  nominally under Valhalla's unenforced claim).

**What genuinely does not exist yet, and is out of this change's scope by roadmap design.** Change 14
(`map-instance`) has not built `InstanceRoom`, TTL reclamation, or promotion of named rooms — this
change does not promote any wilderness location to a permanent room. No anchor other than
`capital_altoria` has a grid placement (`ANCHOR_PLACEMENT_REGISTRY` has exactly one entry) — there is
no second anchor's grid room for the wilderness to connect to yet. Change 22 (`art-queue`) has not
built the `SceneArchetype` registry — `scene_archetype` remains an unvalidated seam here, exactly as
change 12 left it.

## Goals / Non-Goals

**Goals:**
- A deterministic, offline-computable terrain model: a coordinate `(x, y)` always maps to the same
  region and the same description text, with no LLM, no database read, and no wall-clock or random
  input — satisfying design doc's offline-playability criterion for the first time at the map layer.
- A `WildernessMapProvider` subclass, `ElosernWildernessMapProvider`, bounded to a coordinate range
  that represents the continent at an explicit, justified scale (D-4/D-5).
- A concrete, bidirectional, tested connection between 聖潔王都's North Gate and the wilderness —
  entering and returning both work through ordinary Evennia exit traversal, no bespoke `move` command
  (D-6, D-7).
- Wire wilderness step traversal to `WorldClock.advance()`, giving `rulebook/clock.yaml`'s
  command-default pattern its first real, distance-justified consumer (D-5).
- Resolve change 12's own flagged `SceneArchetypeMixin` risk: one shared attribute contract for
  `GridRoom` and the new `TerrainRoom`, not two independent, drifting seams (D-2).
- Verify the real `WildernessMapProvider`/`WildernessScript`/`WildernessRoom`/`WildernessExit` API
  against the installed Evennia 6.1.0 by actually running it in an `EvenniaTest`, not by trusting the
  module's own docstring example (`PyramidMapProvider`, confirmed in design doc §4 to be
  documentation-only, not an importable class) — see the "Verification" section.

**Non-Goals:**
- **No second anchor's wilderness connection.** Only `capital_altoria` has a grid placement today.
  `WILDERNESS_ENTRY_REGISTRY` is deliberately left open (mirroring `ANCHOR_PLACEMENT_REGISTRY`'s own
  "not every key needs an entry yet" posture) for whichever future change places a second anchor's
  grid and wants a wilderness gateway for it — this change does not guess at that anchor's location.
- **No monster or NPC population of the wilderness.** Nothing in this change's roadmap slot
  (`WildernessMapProvider, terrain description`) asks for encounter tables, and no consumer for one
  exists yet (`scene-builder`, change 21, is Phase 5). Wilderness rooms are empty except for whatever
  the player brings.
- **No travel-shortcut or auto-walk command.** Crossing the wilderness is ordinary compass-direction
  exit traversal, one step at a time, exactly like change 12's grid layer — see D-5's arithmetic for
  why this is still a tractable (if deliberately long) journey, not an accidental one.
- **No promotion of any wilderness location to a permanent room** (change 14's charter). A player who
  returns to the same `(x, y)` twice gets the same *description* (D-1's determinism), never the same
  *room object* — `WildernessRoom`s are pooled and reused by the contrib itself; nothing here changes
  that.
- **No `SceneArchetype` registry, validation, or art enqueue** (change 22). `scene_archetype` remains
  an attribute seam only, exactly as change 12 left it on `GridRoom`.
- **No change to the grid layer's own movement-clock posture.** `rulebook/clock.yaml`'s existing
  `move: 30`/`converse: 60` entries remain exactly as inert as change 11 and change 12 left them; this
  change adds a new, separate `wilderness_move` key and wires only wilderness traversal to it — see
  D-5 for why the two are not unified under one constant. **Amended 2026-08-01 (change
  `map-movement-clock`, roadmap item 13b):** this Non-Goal held for this change's own scope at the
  time it was written, but is no longer the state of the world after `map-movement-clock` lands —
  that change wires `move: 30` to grid/Limbo-bridge/instance-room traversal and, since it depends on
  this change, folds this change's own `wilderness_move` wiring (D-6) onto the identical shared
  `world.rules.movement.charge_movement()` function grid movement now uses too. See this design's own
  D-8 for the corrected account.
- No backward-compatibility, migration, or deprecation handling — the project is unreleased with zero
  users.

## Decisions

### D-1. The terrain model: seven regions from `world_info.md`, assigned to coordinates by a fixed
rectangular partition, with description text chosen by a deterministic arithmetic formula — no RNG,
no LLM, no DB read.

```python
# world/lore/wilderness_regions.py
@dataclass(frozen=True)
class WildernessRegion:
    key: str
    display_name_zh: str
    nation_key: str | None              # None => neutral/contested (see below)
    terrain_flavor_zh: tuple[str, ...]  # 2-3 deterministic description variants

WILDERNESS_REGION_REGISTRY: dict[str, WildernessRegion] = {
    "central_mountains": WildernessRegion(
        "central_mountains", "中央山脈", None, (
            "陡峭的山壁直插雲霄，寒風中隱約傳來難以辨明來源的歌聲。",
            "林木稀疏的山徑蜿蜒而上，碎石在腳下滑動，四周異常寂靜。",
            "雲霧終年繚繞山腰，據說深處藏著人族從未涉足之地。",
        ),
    ),
    "eastern_plains": WildernessRegion(
        "eastern_plains", "東部大平原", "grandia", (
            "一望無際的麥田隨風起伏，遠方農莊的炊煙筆直升起。",
            "平整的官道兩側是修剪整齊的果園，牛車緩緩碾過塵土。",
            "肥沃的黑土地上阡陌縱橫，灌溉渠道映著天光。",
        ),
    ),
    "southeast_coast": WildernessRegion(
        "southeast_coast", "東南海岸", "grandia", (
            "鹹濕的海風夾雜著魚市的喧鬧，遠方帆影點點。",
            "石砌的碼頭邊堆滿待運的貨箱，海鳥在桅杆間盤旋。",
            "潮水拍打著防波堤，港區小巷瀰漫著海產與香料的氣味。",
        ),
    ),
    "western_hills_valleys": WildernessRegion(
        "western_hills_valleys", "西部丘陵與谷地", "altoria", (
            "起伏的丘陵間點綴著石砌梯田，遠處傳來礦坑鑿擊的回聲。",
            "谷地間河流蜿蜒，兩岸散落著手工業者的作坊與磨坊。",
            "低緩的丘陵覆滿灌木與野花，羊群在坡地上安靜地啃食。",
        ),
    ),
    "southwest_coast": WildernessRegion(
        "southwest_coast", "西南海岸", "altoria", (
            "精工打磨的木船停靠在小巧的港灣，工匠的敲打聲不絕於耳。",
            "海崖下的漁村炊煙裊裊，曬鹽場在陽光下泛著白光。",
            "商船的旗幟在海風中獵獵作響，岸邊堆滿待售的精工器物。",
        ),
    ),
    "northwest_highland_forest": WildernessRegion(
        "northwest_highland_forest", "西北高地森林", "valhalla", (
            "高聳的針葉林間，獸群的足跡清晰可辨，空氣中帶著松脂的氣味。",
            "起伏的高地覆蓋著濃密的森林，獵人的營火痕跡散落其間。",
            "礦脈裸露的岩壁旁，成群的野獸在林間空地遊蕩。",
        ),
    ),
    "north_deep_forest": WildernessRegion(
        "north_deep_forest", "北部深林", "valhalla", (  # nominal claim only, see below
            "巨木遮蔽天日，林間彌漫著潮濕腐葉的氣息，寂靜得令人不安。",
            "糾結的藤蔓封鎖了視野，遠處似乎有什麼龐然大物正在移動。",
            "無人踏足的密林深處，偶爾傳來不知名生物的低吼。",
        ),
    ),
}
```

These are the **exact, literal strings** the implementer types into `world/lore/wilderness_regions.py`
— not a placeholder. `wilderness-terrain/spec.md`'s "literal expected output" scenario (Fix 4 of the
rubber-duck review that revised this design) pins `terrain_description(60, 100)` against this exact
list, so a reimplementation with different constants or different text is caught by the spec, not
just by this prose — matching the same drift concern that ruled out `hash()`-based selection above.

`north_deep_forest`'s `nation_key` is `"valhalla"` even though `world_info.md` says Valhalla's claim
there is nominal and unenforced ("獸王國擁有邊境名義管轄權，但實際難以掌控") — this dataclass has no field
for "claimed but not controlled," and inventing one for a single region this change does not
otherwise act on would be speculative structure with no reader. The distinction is carried in
`description`/`terrain_flavor_zh` prose instead, where it belongs as a lore fact, not a mechanical
one — no consumer in this change's own scope (or any change through 16) reads `nation_key` to decide
who can act where inside the wilderness.

**Coordinate-to-region assignment — one function, seven rectangular bounds, checked top-to-bottom:**

```python
# world/maps/wilderness_provider.py
_MOUNTAIN_X = (100, 123)      # 24-column central band, full Y range
_NORTH_FOREST_Y_MIN = 190     # top 34 rows, full X range -- checked first, dominates the mountain band
_COASTAL_Y_MAX = 40           # southern strip, both sides of the mountains
_HIGHLAND_Y_MIN = 150         # west side only, between the coast and the northern forest

def region_for_coordinates(x: int, y: int) -> str:
    if y >= _NORTH_FOREST_Y_MIN:
        return "north_deep_forest"
    if _MOUNTAIN_X[0] <= x <= _MOUNTAIN_X[1]:
        return "central_mountains"
    if x > _MOUNTAIN_X[1]:                      # east of the mountains
        return "southeast_coast" if y <= _COASTAL_Y_MAX else "eastern_plains"
    # x < _MOUNTAIN_X[0] -- west of the mountains
    if y <= _COASTAL_Y_MAX:
        return "southwest_coast"
    if y >= _HIGHLAND_Y_MIN:
        return "northwest_highland_forest"
    return "western_hills_valleys"
```

This is a deliberately simple, hand-authored schematic partition, not a literal cartographic
reconstruction — `world_info.md` gives no coordinates, only qualitative adjacency ("中央山脈 ...
縱貫大陸南北", "因中央山脈阻隔，內陸交通不便，東西兩邊以海洋通商形成東西兩大文化圈"). The partition honors
every adjacency fact the lore actually states (mountains run the full north-south extent and split
east/west; the deep forest is northern and spans the width; each nation's core territory sits between
its coast and the mountains) without inventing precision the source material does not have. It is
still a real, testable function: every one of the seven keys is reachable, the boundaries are exact
integers, and `capital_altoria`'s registered wilderness entry point — `(60, 100)`, west of the
mountains, south of the highland band, north of the coastal strip — resolves to
`"western_hills_valleys"`, matching `world_info.md`'s own placement of Altoria's territory (nations.py:
"領土: 西部丘陵、谷地與西南海岸"). This self-consistency is asserted by a test, not just claimed here.

**Description text — a second, independent deterministic choice, never randomness:**

```python
def terrain_description(x: int, y: int) -> str:
    region = WILDERNESS_REGION_REGISTRY[region_for_coordinates(x, y)]
    variants = region.terrain_flavor_zh
    index = (x * 92821 + y * 68917) % len(variants)   # arbitrary large odd multipliers purely to
                                                          # spread adjacent coordinates across variants;
                                                          # not a hash function, not seeded, not
                                                          # randomness -- pure integer arithmetic on
                                                          # the two inputs, same output every call
    return variants[index]
```

**Why arithmetic on `(x, y)` and not `random.Random(seed=(x,y))`.** Both are technically deterministic
given a fixed seed, but a `random.Random`-based approach ties correctness to Python's RNG algorithm
never changing its output for a given seed across interpreter/version upgrades — an implicit,
unstated dependency. A closed-form integer formula has no such dependency and is trivially auditable
by reading it, matching this project's own established preference for "simplest correct number, not
apologized for" (cited repeatedly in change 11's design.md for its own quantum/day-length constants).

**Why this satisfies the offline-playability requirement.** `terrain_description()` and
`region_for_coordinates()` take only `(x, y)` and return a `str`; neither touches the database, the
network, or any mutable module state. Calling `ElosernWildernessMapProvider.at_prepare_room()` (which
calls both) with the LLM entirely offline produces the exact same room description it would with the
LLM online — because it never consults the LLM in the first place. This is Phase 3's own version of
design doc §10's "Offline playability" row.

### D-2. `SceneArchetypeMixin` is introduced now, and change 12's `GridRoom` is retrofitted onto it —
not duplicated.

```python
# typeclasses/rooms.py
class SceneArchetypeMixin:
    """The design doc D10/§8 seam: which SceneArchetype (change 22, unbuilt) a room's scene art
    should use. Not validated against any registry here -- see change 12's own GridRoom docstring
    for why (no SceneArchetype registry exists yet)."""

    scene_archetype: str | None = AttributeProperty(default=None)


class GridRoom(SceneArchetypeMixin, XYZRoom):
    """Unchanged from change 12's own design except for where scene_archetype now lives."""


class TerrainRoom(SceneArchetypeMixin, WildernessRoom):
    """A room on the wilderness/Virtual layer (design doc D3). Unlike GridRoom, TerrainRoom
    instances are pooled and reused across many different (x, y) coordinates over their lifetime
    (WildernessScript._create_room() recycles unused rooms) -- see D-3 for why scene_archetype must
    be re-set on every at_prepare_room() call, not merely defaulted once."""
```

**Why now, and why this is the right call given the task's own framing.** Change 12's own design.md
already worked through this exact question and left a named, unresolved risk: "the `scene_archetype`
seam lives on `GridRoom` only, and later map-layer changes are unlikely to share that base class ...
the likely resolution is a small, standalone `SceneArchetypeMixin` ... change 12 should not decide
change 13 or 14's room hierarchy on their behalf — but named so 13/14/22 inherit this analysis instead
of rediscovering it." This change is exactly the first one to hit that fork, precisely as the task
predicted. Declining to introduce the mixin now and instead duplicating a second, independent
`scene_archetype: str | None = AttributeProperty(default=None)` directly on `TerrainRoom` was
considered and rejected: it costs nothing today (both spellings are attribute-identical), but it
means change 22 (`art-queue`) inherits two unrelated attribute definitions with no shared contract to
type-check or introspect against, and any future third mention (`InstanceRoom`, change 14) would make
it three. A five-line mixin, adopted by both room types that need the seam today, is strictly
cheaper than that outcome and is the specific fix change 12's own author already named.

**Why retrofitting `GridRoom` is behavior-preserving, and why it still gets a `MODIFIED` delta spec.**
Change 12's `grid-room-typeclasses` spec requirement states only: "`typeclasses/rooms.py` SHALL define
`GridRoom`, subclassing `evennia.contrib.grid.xyzgrid.xyzroom.XYZRoom`, with a persistent
`scene_archetype: str | None` attribute defaulting to `None`." Nothing in that text, or in any of its
three scenarios, specifies scene_archetype must be declared directly in `GridRoom`'s own class body
rather than inherited from a mixin — `room.scene_archetype` still resolves to `None` by default,
still accepts an arbitrary string with no registry lookup, and still persists across a reload,
identically, via Python's ordinary MRO attribute lookup. This is a behavior-preserving refactor of
change 12's already-landed implementation *file*.

An earlier draft of this design treated that behavior-preservation as sufficient reason to skip a
delta spec entirely, reasoning by analogy to change 11 editing change 8's `CmdCast` — "wiring a call
site" needs no new artifact. A rubber-duck review corrected this: change 12's own design.md D-1 draws
the line one step earlier than that analogy assumed — "wiring a call site" is safe to edit upstream in
place, but *changing an already-shipped, already-tested class's base classes* is the other kind, the
kind D-1 says needs a new artifact (the exact reasoning change 12 itself used to justify a *separate*
`AnchorPlacement` registry rather than adding a field to the already-shipped `Anchor` dataclass).
Retrofitting `GridRoom.__bases__` from `(XYZRoom,)` to `(SceneArchetypeMixin, XYZRoom)` is structurally
that second kind, not the first, even though the *observable* attribute behavior is unchanged. The
practical cost of treating it as a same-file, no-artifact edit: `openspec/specs/grid-room-typeclasses/
spec.md`, once change 12 archives, would say nothing about `SceneArchetypeMixin` or the fact that
`scene_archetype` now lives on a shared seam — and change 22 (`art-queue`), the change that most needs
to know the seam is shared across room types, reads `openspec/specs/`, not archived changes' internal
reasoning. **Decision, corrected: this change files a `MODIFIED grid-room-typeclasses` delta spec**
(`specs/grid-room-typeclasses/spec.md`), reproducing change 12's full requirement text with the
`scene_archetype` provenance sentence updated and one new scenario asserting `SceneArchetypeMixin` is
in `GridRoom.__mro__`, cross-referencing this change's own `scene-archetype-mixin` capability. Task
group 6 below still re-runs change 12's own `scene_archetype` tests unmodified, proving the *behavior*
claim; the delta spec is what makes the *contract* claim visible to a reader of `openspec/specs/`
alone, which the behavior test cannot do by itself.

**Why `TerrainRoom` needs the identical seam to `GridRoom`'s, not a wilderness-specific variant.**
Design doc D10 states scene art is "keyed by archetype, not by room" — a tavern interior looks the
same everywhere. That principle does not distinguish grid rooms from wilderness rooms: a
"western_hills_valleys_plains" archetype should look the same regardless of which layer requested it.
One shared attribute name and default across both typeclasses is what lets change 22 read
`room.scene_archetype` generically later, without an `isinstance` branch per room type.

### D-3. `scene_archetype` must be re-set on every `at_prepare_room()` call for a `TerrainRoom` —
unlike `GridRoom`, where it is set once and persists for that room's entire lifetime.

This is a genuine, non-obvious consequence of how the wilderness contrib manages room objects,
verified by reading `WildernessScript._create_room()`/`set_active_coordinates()` directly (not
assumed): a `TerrainRoom` instance is not permanently tied to one `(x, y)` coordinate the way a
`GridRoom` is. `WildernessScript` pools rooms — when a traveler leaves a coordinate with no one else
present, `_destroy_room()` moves that same room object into `self.db.unused_rooms`, and the *next*
traveler who needs a room at a *different* coordinate may be handed that exact object back via
`_create_room()`'s `if self.db.unused_rooms: room = self.db.unused_rooms.pop()` branch. A
`scene_archetype` value written for one coordinate would silently persist onto whichever unrelated
coordinate reuses that pooled object next, if nothing re-set it. **Decision**:
`ElosernWildernessMapProvider.at_prepare_room(coordinates, caller, room)` — the hook the contrib
itself calls every time `set_active_coordinates()` activates a room for a (possibly new) coordinate,
verified by reading `set_active_coordinates()`'s own final line, `self.wilderness.mapprovider.
at_prepare_room(new_coordinates, obj, self)` — recomputes and reassigns `room.scene_archetype`
unconditionally on every call, alongside setting `room.ndb.active_desc` from `terrain_description()`.
Both are cheap, pure recomputations from `(x, y)` — there is no correctness cost to doing this on
every step, only the same marginal per-step Attribute write the wilderness system already performs
for its own coordinate bookkeeping.

### D-4. Coordinate scale: 10 km per wilderness step, a 224×224 bounded map — arithmetic shown, not
asserted.

`world_info.md`: "面積: 約500萬平方公里" (~5,000,000 km²). Modeling the continent as approximately
square for coordinate-bound purposes: `sqrt(5,000,000) ≈ 2236.07 km` per side. **Decision: 10 km per
wilderness grid cell, 224 cells per axis** (`WILDERNESS_MAX_X = WILDERNESS_MAX_Y = 223`, 0-indexed,
224 valid values): `224 × 10 km = 2,240 km` per side, `2,240² = 5,017,600 km²` — within 0.35% of the
stated area, using round, easy-to-audit numbers rather than a value hand-fitted to hit 5,000,000
exactly (matching this project's established "simplest correct number" convention). `capital_altoria`'s
registered entry point, `(60, 100)`, sits comfortably inside this bound and inside `western_hills_
valleys` (D-1's self-consistency test).

```python
# world/maps/wilderness_provider.py
WILDERNESS_KM_PER_CELL = 10
WILDERNESS_MAX_X = 223
WILDERNESS_MAX_Y = 223

class ElosernWildernessMapProvider(WildernessMapProvider):
    room_typeclass = TerrainRoom
    exit_typeclass = WildernessReturnExit

    def is_valid_coordinates(self, wilderness, coordinates):
        x, y = coordinates
        return 0 <= x <= WILDERNESS_MAX_X and 0 <= y <= WILDERNESS_MAX_Y

    def get_location_name(self, coordinates):
        return WILDERNESS_REGION_REGISTRY[region_for_coordinates(*coordinates)].display_name_zh

    def at_prepare_room(self, coordinates, caller, room):
        room.scene_archetype = region_for_coordinates(*coordinates)   # D-3
        room.ndb.active_desc = terrain_description(*coordinates)
```

`is_valid_coordinates(self, wilderness, coordinates)` — the two-argument signature (not just
`coordinates`) is the base class's real, verified signature (see Verification section), not assumed
from the module docstring's `PyramidMapProvider` example (which itself only overrides the
single-purpose helper, not the base class's actual call site).

**Alternative considered: an unbounded map (the contrib's own default `WildernessMapProvider`
behavior, `x >= 0 and y >= 0`, no upper bound).** Rejected — an unbounded map has no relationship to
the stated ~5,000,000 km² continent size, and `region_for_coordinates()`'s rectangular partition (D-1)
requires finite bounds to be a meaningful "this is the whole continent" statement rather than an
arbitrary function that happens to return a value for any input. A bounded map is also what lets D-5's
"time to cross the continent" arithmetic mean anything concrete.

### D-5. Wilderness steps are wired to `WorldClock`, at a new, distinct cost — resolving the roadmap's
long-deferred movement/clock gap, scoped to where distance actually matters.

Design doc §6.5 lists `move: 30` (seconds) among the clock's three command-default costs; change 11
declared it as inert data (no `move` command existed yet); change 12 explicitly declined to wire it
("No movement command wiring to `WorldClock` ... this change adds real `Exit` objects that Evennia's
own auto-generated exit-traversal command already handles, but does not add a bespoke `move` command
or call `WorldClock.advance()` on traversal"), reasoning that a city block and `move: 30` (30 real
seconds ≈ brisk walking pace for a short urban block) were a reasonable pairing not worth building a
whole clock-integration path for yet. **Decision: this change does wire clock cost to movement, but
only for wilderness steps, through a new and separate `command_defaults.wilderness_move` constant —
not by retroactively wiring the grid's existing `move: 30`.**

**Why here, and why now.** The task framing driving this change is explicit: wilderness traversal, at
continent scale, is where elapsed time first has a real, player-visible consequence (a multi-day
journey, not an instant city stroll). Leaving wilderness steps unwired to the clock would mean a
player could cross the entire modeled continent — 224 steps at the coordinate scale D-4 establishes —
with the in-game calendar never advancing, which is a strictly worse offline-playability and
world-consistency posture than what change 11 already built for combat and skip commands. Wiring it
here, at the one place in the roadmap where "distance" first has a concrete numeric meaning, is a
natural continuation of change 11's own established integration pattern (`CmdCast` calling
`get_world_clock().advance()` on success — this change's `WildernessGateExit`/`WildernessReturnExit`
call the identical function with the identical argument shape, verified directly, see D-6), not an
invention of a new one.

**Why a new constant, `wilderness_move`, rather than reusing `move: 30`.** A grid step and a
wilderness step represent categorically different real distances — a city block (tens of meters) versus
D-4's 10 km cell. Reusing the same constant for both would either make city walking absurdly slow (30
seconds is already tuned for the grid) or make continent travel absurdly fast (10 km in 30 seconds is
1,200 km/h). The two costs are declared, named, and consumed independently; nothing in this change
edits `rulebook/clock.yaml`'s existing `move`/`converse` entries.

**Arithmetic for `wilderness_move`'s value.** At an on-foot/adventuring-party overland pace of roughly
4 km/h (comparable to common tabletop-RPG overland travel conventions, and to the setting's stated
"中世紀+魔法文明(相當於15-16世紀歐洲)" tech level — no paved highway network implied), 10 km takes
`10 / 4 = 2.5` hours `= 9,000` seconds. **`wilderness_move: 9000`** — a clean multiple of
`seconds_per_hour: 3600` (exactly 2.5×), auditable at a glance against the calendar constants already
in the same file.

**Continent-crossing sanity check, per the task's own request — shown, not asserted.** Crossing the
full 224-step span of the bounded map: `224 × 9,000 s = 2,016,000 s`. Converted via the existing
calendar (`seconds_per_hour: 3600`, `hours_per_day: 24` → 86,400 s/day): `2,016,000 / 86,400 ≈ 23.33`
days. Against `days_per_season: 90`: `23.33 / 90 ≈ 26%` of one season, `≈ 6.5%` of the 360-day year.
This is a substantial, multi-week overland journey — appropriately epic for a full continental
crossing in a pre-industrial setting, while remaining a small, bounded fraction of one season, not an
unplayable multi-year trek. (A literal medieval-Europe walking pace across a comparable real distance
would plausibly take longer; this is a deliberate gameplay-pacing compression in the same spirit as
this project's combat/clock formulas throughout — simplified numbers that produce a sane play
experience, not a physics simulation, and not apologized for as such.)

**What this change does not solve.** Crossing 224 steps one command at a time is a lot of individual
player inputs — this change builds no travel-shortcut, waypoint, or auto-walk command (Non-Goals).
That is a legitimate follow-on UX concern for a later change, not something roadmap item 13's own
"`WildernessMapProvider`, terrain description" scope asks this change to solve.

### D-6. The gateway: `WildernessGateExit` (an ordinary `Exit`, fully overriding `at_traverse`) and
`WildernessReturnExit` (a `WildernessExit` subclass whose *routing* is coordinate-and-direction-gated
but whose *clock cost* is not) — verified end-to-end against the installed Evennia 6.1.0, not assumed
from the contrib's docstring.

**Correction recorded here, not silently fixed — a rubber-duck review caught a genuine defect in an
earlier draft of this decision.** That draft advanced the clock only inside `WildernessReturnExit`'s
special-cased return-to-grid branch, and left the `super().at_traverse()` fallback — the branch every
ordinary intermediate wilderness step actually takes — advancing nothing. Because
`ElosernWildernessMapProvider.exit_typeclass = WildernessReturnExit` installs this class on *all
eight* directional exits at *every* coordinate (D-4), the observable consequence was: entering costs
`wilderness_move`, returning costs `wilderness_move`, and all 222 intermediate steps of a full
continent crossing cost **zero** — a flat 18,000 s round trip regardless of how many steps were
actually walked in between. This directly contradicted this design's own Goals ("Wire wilderness step
traversal to `WorldClock.advance()`") and D-5's entire arithmetic, and reintroduced, one layer down,
exactly the "movement costs nothing" posture D-5 criticizes the grid layer for. The verification
probe that shipped alongside the earlier draft did not catch this because it only exercised the two
special-cased branches (enter, then immediately return) and never asserted a clock delta on an
*intermediate* step — it confirmed the code that was written, not the goal that was claimed. **Fixed
below**: `WildernessReturnExit.at_traverse` now advances the clock after *every* successful
traversal — the special-cased return branch and the `super().at_traverse()` fallback both do it, so no
step is free. Re-verified end-to-end with a corrected probe that walks several intermediate steps and
asserts the clock advanced by exactly `steps × wilderness_move` for the whole round trip, including
the steps that take neither special-cased branch (see Verification section).

**The pattern, and why it is the correct one.** The wilderness contrib's own module docstring states
only "there is no command that allows players to enter the wilderness ... it can be a command or an
exit, depending on your needs," with no worked example of the exit form. Reading `DefaultExit.
basetype_setup()` and `WildernessExit.at_traverse()` directly (not inferred) shows the sanctioned
idiom: an exit whose real behavior does not come from Evennia's default `move_to(self.destination)`
path at all — `WildernessExit.at_traverse()` never calls `super().at_traverse()` or reads
`target_location`; it computes new coordinates and calls `self.location.wilderness.move_obj()`
directly. This change's `WildernessGateExit` follows the identical shape for the *opposite* direction
(grid → wilderness): created with `destination` pointed at its own room (the same self-loop
`DefaultExit.basetype_setup()` falls back to when no destination is given, and the same pattern
`WildernessScript._create_room()` uses for its own eight directional exits — `destination=room`), with
`at_traverse()` fully overridden to call `wilderness.enter_wilderness(traversing_object, coordinates=
WILDERNESS_ENTRY_REGISTRY["capital_altoria"].wilderness_xy, name=WILDERNESS_NAME)` and, on success,
`get_world_clock().advance(CLOCK_YAML["command_defaults"]["wilderness_move"], AdvanceSource.COMMAND,
[traversing_object])`. **Amended 2026-08-01 (change `map-movement-clock`):** the code samples below
still show this inline `get_world_clock().advance()` call because that is what this change (`map-
wilderness`) itself builds and tests. `map-movement-clock` (roadmap item 13b, depending on this
change) replaces both inline calls with `world.rules.movement.charge_movement(traversing_object,
"wilderness_move")` — a same-behavior, same-cost, same-success-only-condition edit to this change's
own already-written call sites, folding them onto the identical shared function grid and instance-room
movement now use too. See that change's own design.md D-1/D-9 for why folding this change's bespoke
wiring into a shared mechanism, while this change is still unimplemented, was judged worth doing
rather than leaving two independent movement-clock mechanisms in the codebase.

```python
# typeclasses/exits.py
class WildernessGateExit(Exit):
    """Ordinary Exit at a grid room (e.g. capital_altoria's North Gate) whose at_traverse is fully
    overridden -- mirrors WildernessExit's own pattern of ignoring target_location entirely.
    db.anchor_key is set by sync_wilderness() at creation time (D-7) -- it is NOT optional, and a
    gate exit created without it will KeyError on first use (see D-7's own correction note)."""

    def at_traverse(self, traversing_object, target_location, **kwargs):
        # Honor the same at_pre_move veto every other exit in the game honors -- see Fix 5's
        # rationale below: without this, entering the wilderness would be the one movement path
        # in the game that silently ignores a future movement-blocking convention (combat lock,
        # restraint, quest gating) every other exit already respects.
        if not traversing_object.at_pre_move(None):
            return False
        entry = WILDERNESS_ENTRY_REGISTRY[self.db.anchor_key]
        source_location = traversing_object.location
        ok = enter_wilderness(traversing_object, coordinates=entry.wilderness_xy, name=WILDERNESS_NAME)
        if not ok:
            return False
        if source_location:
            source_location.msg_contents(
                f"{traversing_object.key} leaves into the wilderness.",
                exclude=[traversing_object],
            )
        traversing_object.location.msg_contents(
            f"{traversing_object.key} arrives from {source_location}.",
            exclude=[traversing_object],
        )
        traversing_object.at_post_move(None)
        get_world_clock().advance(
            WILDERNESS_MOVE_SECONDS, AdvanceSource.COMMAND, [traversing_object]
        )
        return True
```

**Fix 5 — why the veto/announce/post-move sequence matters even though nothing hooks it today.** The
stock `WildernessExit.at_traverse()` (D-6's own model, quoted above) calls `at_pre_move` (respecting a
`False` veto), sends leave/arrive `msg_contents` announcements, and calls `at_post_move`; this change's
own `WildernessReturnExit` return branch does the same via `move_to()`, which performs all three
internally. An earlier draft of `WildernessGateExit` called only `enter_wilderness()`, which performs a
raw `obj.location = room` assignment with none of those three steps — making entry the *one* movement
path in the game that skipped them. Nothing currently hooks `at_pre_move` to veto a move, so this was
not an active bug, but it is a latent one: any future movement-blocking convention (a combat lock, a
restraint effect, quest-stage gating) that every other exit in the game already honors would be
silently bypassed at exactly this one seam, and bystanders in the source room would get no departure
message. Corrected above to match the pattern this design already claims to follow.

**The return path — one `WildernessExit` subclass, shared by every room in the map, that
special-cases exactly one coordinate.** `ElosernWildernessMapProvider.exit_typeclass =
WildernessReturnExit` means *every* room the wilderness ever creates gets its eight directional exits
from this one class — there is no per-coordinate exit bookkeeping to keep idempotent, because the
contrib's own `WildernessScript._create_room()` already creates all eight exits automatically, once
per newly-created (non-recycled) room object, verified by reading that method directly. The subclass
inspects the *current* coordinates and the *exit's own key* at traversal time, not at creation time:

```python
class WildernessReturnExit(WildernessExit):
    def at_traverse(self, traversing_object, target_location):
        itemcoordinates = self.location.wilderness.db.itemcoordinates
        current = itemcoordinates[traversing_object]
        for entry in WILDERNESS_ENTRY_REGISTRY.values():   # iterated, not hardcoded to one key --
                                                              # see Risks/Trade-offs: a future second
                                                              # entry needs no edit here
            if current == entry.wilderness_xy and self.key == "south":
                traversing_object.move_to(_grid_room_for_anchor(entry.anchor_key), quiet=False)
                get_world_clock().advance(
                    WILDERNESS_MOVE_SECONDS, AdvanceSource.COMMAND, [traversing_object]
                )
                return True
        # ORDINARY wilderness movement -- every coordinate/direction that is not a registered
        # gateway. This is NOT free: a successful ordinary step still pays wilderness_move. Only
        # the routing decision (grid room vs. another wilderness coordinate) is gated; the clock
        # cost is not -- see this section's own correction note above for why an earlier draft got
        # this wrong.
        result = super().at_traverse(traversing_object, target_location)
        if result:
            get_world_clock().advance(
                WILDERNESS_MOVE_SECONDS, AdvanceSource.COMMAND, [traversing_object]
            )
        return result
```

Every other coordinate, and every other direction at a registered coordinate, still falls through to
`super().at_traverse()` for its *routing* (ordinary wilderness movement, unchanged) — only the *clock
wiring* is now unconditional on a successful result. `_grid_room_for_anchor(anchor_key)` is a plain
object lookup (by `(xyz)` via `GridRoom.objects.filter_xyz` against
`ANCHOR_PLACEMENT_REGISTRY[anchor_key]`'s `entrance_xy`/`zcoord`, or equivalent — resolved once change
12's own `AnchorRoom`/`GridRoom` query helpers exist as real code).

**Verified end-to-end, not just read from source.** An `EvenniaTest`-based scratch probe (see
Verification section) built exactly this corrected shape — an ordinary `Exit` subclass calling
`enter_wilderness()`, a `WildernessExit` subclass that advances the clock on both its special-cased
return branch *and* its `super().at_traverse()` fallback — and confirmed: entering advances the clock
by the configured amount; three consecutive *intermediate* steps (none of them the registered
coordinate or a "south" traversal) each advance the clock by `wilderness_move` individually; walking
back and returning via the special-cased branch advances it once more; and the full eight-step round
trip (1 entry + 3 out + 3 back + 1 return) advances the clock by exactly `8 × 9,000 = 72,000` seconds
— asserted directly in the probe, not eyeballed. The return exit is reachable, typed correctly, routes
back to the original grid room object (not a copy); and leaving a wilderness room through either path
correctly triggers the contrib's own cleanup (`itemcoordinates` entry removed, room recycled into
`unused_rooms`) with no manual bookkeeping required on this change's part.

**Why the round trip is built now, not deferred.** An entrance with no return path is a trap, not a
gateway — a player who walks north from the sample city and can never walk back is a strictly worse
outcome than not building the connection at all. Change 12 itself built its own Limbo bridge
bidirectionally (D-7 of that change: an exit and an explicit return exit); this change follows the
identical precedent for the same reason, and the marginal cost is one additional, already-necessary
`WildernessExit` subclass (the map needs *an* `exit_typeclass` regardless; making it this one instead
of the stock class costs nothing extra).

### D-7. `sync_wilderness()`: idempotent, added to `world/maps/bootstrap.py` alongside — not merged
into — change 12's `sync_grid()`.

```python
# world/maps/bootstrap.py
def sync_wilderness() -> None:
    create_wilderness(name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider())
    # create_wilderness() is itself a no-op if a WildernessScript keyed WILDERNESS_NAME already
    # exists (verified by reading wilderness.py directly -- see Verification) -- no extra guard needed.
    north_gate = _find_north_gate()   # GridRoom.objects.filter_xyz((2, 4, "capital_altoria")).first()
    if north_gate is None:
        logger.log_warn("sync_wilderness: capital_altoria North Gate not found, skipping gateway.")
        return
    if not any(e.key == "荒野" for e in north_gate.exits):
        gate, _errors = WildernessGateExit.create(
            key="荒野", aliases=["wilderness", "north", "n"],
            location=north_gate, destination=north_gate,
        )
        gate.db.anchor_key = "capital_altoria"   # load-bearing -- WildernessGateExit.at_traverse
                                                    # (D-6) reads self.db.anchor_key and looks it up
                                                    # in WILDERNESS_ENTRY_REGISTRY; an earlier draft
                                                    # of this function omitted this line, which a
                                                    # rubber-duck review caught: a gate exit created
                                                    # without it has db.anchor_key == None, and
                                                    # WILDERNESS_ENTRY_REGISTRY[None] raises KeyError
                                                    # on the exit's very first traversal, after
                                                    # sync_wilderness() itself reports success. Fixed
                                                    # here; tasks.md's own task 10.1 already had this
                                                    # right and is now consistent with this section.
```

Named `sync_wilderness()`, distinct from `sync_grid()`, for the identical reason change 12 named its
own function distinctly from change 2's `sync_all()`: two different things are being provisioned (a
`WildernessScript` singleton plus one bridging exit, versus a whole room/exit topology), and blurring
the names would reproduce the exact "anchor sync is an overloaded term" ambiguity change 12's own D-3
existed to resolve. `sync_wilderness()` is called from `at_server_start()` immediately after
`sync_grid()` — the sample city's rooms (including the North Gate) must already exist before this
function can look one up.

**Absent-North-Gate behavior mirrors change 12's absent-Limbo behavior exactly: log and skip, never
raise.** If `sync_grid()` has not run, or the sample city's map data ever changes to remove the North
Gate, `sync_wilderness()` still creates the `WildernessScript` (the terrain layer itself has no
dependency on the grid layer existing) but skips the one grid-side exit, with a warning — the same
graceful-degradation posture change 12's D-7 established for its own Limbo bridge, applied here to an
analogous, smaller case.

**A caveat worth naming, verified by reading the source, not discovered as a surprise later (the same
discipline change 12's own D-5 modeled for `add_maps()`/`reload()`).** `create_wilderness()`'s
idempotency check (`if WildernessScript.objects.filter(db_key=name).exists(): return`) means that on
every server start *after* the first, this function does **not** re-run `mapprovider=
ElosernWildernessMapProvider()` — the already-pickled instance from the first boot is what the
`WildernessScript` keeps using. If a future balance pass edits `region_for_coordinates()`'s bounds or
`WILDERNESS_KM_PER_CELL`, a running server will not pick up the change until the `WildernessScript` is
deleted and `sync_wilderness()` runs again (an `evennia py` one-liner, or a future migration script —
out of scope here). This is the wilderness-layer analogue of change 12's own `add_maps()`/`reload()`
sequencing finding: a real, checked API behavior, not a hypothetical.

### D-8. `command_defaults.move: 30` — **superseded 2026-08-01, no longer an open gap.**

**This section originally documented, not solved, a gap**: as written by this change, it stated that
`command_defaults.move: 30` had no consumer, and that scanning the roadmap (design doc §11, items
14-23) found no future change scoped to give it one — a "permanent gap by omission" this change's own
charter (roadmap item 13, `WildernessMapProvider, terrain description`) did not ask it to close, left
as a visible, recorded open decision for whoever touched map layers or the clock next.

**That claim is now false, and is corrected here rather than left to mislead a future reader.** The
project owner asked for exactly the small, inserted roadmap change this note anticipated, and it
exists: `map-movement-clock` (roadmap item 13b, depending on this change and change 12). It wires
`move: 30` to every `typeclasses.exits.Exit`/`typeclasses.exits.CostedXYZExit` traversal by a
`PlayerCharacter` — covering intra-city grid steps, the Limbo↔grid bridge, and (automatically, with
no code change of its own) change 14's instance-room doorways — through one shared
`world.rules.movement.charge_movement()` function. It also folds this change's own `wilderness_move`
wiring (D-6) onto that same function, so the codebase ends up with one movement-cost mechanism, not
two parallel ones. `move: 30` is, as of `map-movement-clock`, a real, consumed cost, not a
still-open decision. See `openspec/changes/map-movement-clock/design.md` for the full reasoning,
including why it depends on this change specifically (it edits this change's own artifacts, not just
change 12's) and why `converse: 60` remains unwired and out of scope even after this correction.

## Risks / Trade-offs

- **[Risk] `create_wilderness()`'s pickled `mapprovider` does not pick up code changes after first
  boot (D-7).** → **Mitigation**: named explicitly above; out of scope to solve generally in this
  change (no migration tooling exists yet for any registry in this project), but the failure mode
  (stale terrain logic surviving a code update until the script is manually recreated) is documented
  so a future balance-pass change does not rediscover it as a mystery.
- **[Risk] `region_for_coordinates()`'s rectangular partition is a schematic approximation, not a
  literal map.** A player who walks in a straight line will cross region boundaries at exact integer
  lines, not organic ones. → **Mitigation**: accepted — `world_info.md` supplies no coordinate data to
  do better with, and the partition is internally consistent (every named region is reachable, no
  region is empty, `capital_altoria`'s entry point resolves to its own nation's territory). A future
  change with a real cartography requirement can replace the partition function without touching its
  call sites (`region_for_coordinates(x, y) -> str` is the entire contract).
- **[Risk] 224 individual traversal commands to cross the continent is a lot of player input.** →
  **Mitigation**: named as an explicit Non-Goal (D-5); not solved here. The roadmap slot for this
  change is "`WildernessMapProvider`, terrain description," not travel UX.
- **[Trade-off, resolved in the code sample above] `WildernessReturnExit`'s routing decision iterates
  `WILDERNESS_ENTRY_REGISTRY` rather than hardcoding `"capital_altoria"`.** Since the registry has
  exactly one entry today, a loop and a single `if` are behaviorally identical either way; iterating
  is what the D-6 code sample actually does, specifically so a second entry (added by a future change
  placing a second anchor's grid) requires no edit to `WildernessReturnExit` itself — see task group 8.
- **[Risk, corrected — recorded so it is not silently reintroduced] An earlier draft advanced the
  clock only inside `WildernessReturnExit`'s special-cased return branch, leaving every intermediate
  wilderness step free (D-6's own correction note has the full account).** → **Mitigation**: fixed —
  the clock now advances on both the special-cased branch and the `super().at_traverse()` fallback;
  task group 8 adds a regression test that walks several intermediate steps and asserts the clock
  advanced by `steps × wilderness_move` for the whole trip, specifically so this cannot silently
  regress back to the free-intermediate-steps behavior.
- **[Trade-off] `scene_archetype` on `TerrainRoom` is re-written on every step (D-3), a marginal extra
  Attribute write per traversal.** → **Accepted**: negligible next to the wilderness system's own
  per-step Attribute writes (`itemcoordinates`, `active_coordinates`), and correctness (D-3) requires
  it — a stale `scene_archetype` from a recycled room's previous coordinate would be a silent data bug
  reachable in ordinary play, not a hypothetical.

## Verification

Everything below was checked against the installed `evennia==6.1.0` package and this project's own
`world/rules/clock.py`, via `uv run --locked evennia test --settings settings.py <scratch module>`
using `evennia.utils.test_resources.EvenniaTest` (not inferred from the contrib's module docstring,
which this project's own design doc §4 already flags as containing at least one non-importable
documentation-only example, `PyramidMapProvider`):

- `evennia.contrib.grid.wilderness.wilderness.create_wilderness(name="default", mapprovider=None,
  preserve_items=False)` — module-level function; a no-op if a `WildernessScript` keyed `name` already
  exists (read directly from source, and independently confirmed idempotent by calling it twice in
  the same test and observing no error and no duplicate script).
- `enter_wilderness(obj, coordinates=(0, 0), name="default") -> bool` — returns `True`/`False`; on
  invalid coordinates, returns `False` and leaves `obj.location` completely unchanged (verified: an
  out-of-bounds `enter_wilderness()` call against a custom bounded provider left the calling
  character's prior, valid wilderness location untouched).
- `WildernessMapProvider.is_valid_coordinates(self, wilderness, coordinates)` — **two** parameters
  beyond `self` (the wilderness script instance, then the coordinate tuple), not one; confirmed by
  reading the base class and by successfully subclassing it with a bounded override matching this
  exact signature.
- `WildernessMapProvider.get_location_name(self, coordinates)` and `at_prepare_room(self, coordinates,
  caller, room)` — confirmed by the same subclassing test; `at_prepare_room` is called by
  `WildernessRoom.set_active_coordinates()`'s own final line on every activation, including repeated
  activations of a recycled room object at a new coordinate (confirmed by moving two different
  characters through the same bounded map and observing `get_display_desc()`/`ndb.active_desc` update
  correctly each time).
- **Room merging and splitting** (documented in the contrib's own docstring, independently confirmed
  by test): two characters entering the same `(x, y)` share the identical room object
  (`char2.location.id == char1.location.id`); when one moves away, the other's room object is
  unaffected (same `id`), and the mover gets a fresh or recycled room at the new coordinate.
- **The custom `mapprovider` instance must be a module-level class, not a local/closure class.**
  Discovered directly, not assumed: `WildernessScript.mapprovider` is an `AttributeProperty`, and
  `create_wilderness()` immediately assigns the passed-in `mapprovider` instance to it — Evennia's
  Attribute storage pickles the value (`evennia.utils.picklefield`), and a test-local class defined
  inside a test method's body failed with `AttributeError: Can't get local object
  '...test_probe.<locals>.BoundedMapProvider'` when Python's `pickle` tried to resolve its qualified
  name. `ElosernWildernessMapProvider` is therefore a genuine, ordinary module-level class in
  `world/maps/wilderness_provider.py` — this is a hard requirement, not a style preference, and is
  worth stating explicitly since nothing in the contrib's documentation calls it out.
- **Exit-edge locking at a bounded map's boundary.** Walking a character to the last valid coordinate
  before an edge and inspecting the corresponding directional exit showed `traverse:false();
  view:false()` locks already applied (`set_active_coordinates()`'s own per-exit validity check,
  confirmed reading source and by calling `.access(char, "traverse")` and observing `False`) — the
  contrib handles map-edge exit locking entirely on its own; this change adds no separate boundary UI
  logic beyond `is_valid_coordinates()` itself.
- **The gateway pattern (D-6) end-to-end, including the corrected per-step clock wiring**: built and
  ran the exact `WildernessGateExit`/`WildernessReturnExit` shape described above (using stand-in
  `Room`/`Exit` typeclasses in place of change 12's not-yet-implemented `GridRoom`/`AnchorRoom`, since
  this change was authored before change 12 landed) inside an `EvenniaTest`, in two passes. The first
  pass (which shipped in this design's first draft) only exercised the entry and immediate-return
  legs and confirmed each individually advanced the clock by `wilderness_move` — this is the exact gap
  a rubber-duck review caught (D-6's correction note): it never proved *intermediate* steps also pay.
  The corrected, second pass explicitly closes that gap: entering the wilderness, taking **three
  intermediate steps east** (none of them the registered coordinate, none of them a `"south"`
  traversal — the two conditions the special-cased branch requires), walking three steps back west, and
  finally traversing `"south"` from the registered coordinate back to the grid room. Confirmed: every
  one of the eight legs (1 entry + 3 east + 3 west + 1 return) individually advanced `get_world_clock().
  tick` by exactly `9,000`, for a directly-asserted grand total of `8 × 9,000 = 72,000` — not merely
  computed by hand, the test fails (`assert grand_total == expected_steps * 9000`) if any leg is free.
  The south exit at the registered coordinate was confirmed to be an instance of the custom
  `WildernessReturnExit` subclass, as was every ordinary directional exit encountered along the
  intermediate steps (proving `exit_typeclass` wiring reaches every room the map creates, not just the
  one at the registered coordinate); the final return moved the character back to the exact original
  grid-room object (`char1.location` identity-equal to the room created before entry, not a lookalike).
  Cleanup was re-confirmed unchanged by the fix: after the return, the wilderness's own
  `itemcoordinates` no longer tracked that character and its vacated room was recycled into
  `unused_rooms`.
- **The gate exit's movement-hook sequence (Fix 5)**: re-verified with the corrected
  `WildernessGateExit` that calls `at_pre_move`/announces/`at_post_move` before advancing the clock
  (matching the stock `WildernessExit.at_traverse()`'s own sequence) — a default `EvenniaTest` character
  has no veto installed, so `at_pre_move(None)` returns `True` and traversal proceeds exactly as
  before; the sequence adds no observable regression to the entry path already verified above, it only
  adds the hook calls a future movement-blocking convention would need.
- **`WorldClock` integration matches change 8/11's own established shape exactly**: `world.rules.
  clock.get_world_clock()` returns a fresh `WorldClock` snapshot on every call (backed by a persistent
  `WorldClockScript`); `.advance(seconds, source, entities)` is the only way `tick` moves; a probe
  confirmed `AdvanceSource.COMMAND` is accepted with a plain list of traversing objects, identically to
  `commands/action.py::CmdCast`'s own already-landed call. (One probe-authoring pitfall worth
  recording for the implementer: `get_world_clock()` must be re-called to observe a fresh `tick` value
  after a call to `.advance()` elsewhere — a cached `WorldClock` snapshot variable held across the
  `advance()` call will not reflect it, since `WorldClock` is an ordinary, non-live-updating
  `dataclass` snapshot, not a handle to the persisted script. This is a test-authoring detail, not a
  defect in `clock.py`.)

This supersedes nothing in design doc §4's "Extend" call on `WildernessMapProvider` — it is the
call-signature-level addendum that call did not need to go to, in the same spirit as change 12's own
`xyzgrid` verification section.
