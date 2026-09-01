# Design: wilderness-anchor-footprint

## Context

The city of Altoria is a phantom point: `WILDERNESS_ENTRY_REGISTRY` gives it one wild coordinate
`(60, 100)` that is an ordinary walkable cell (region `western_hills_valleys`), and the return gate
is a hardcoded `key == "south"` match duplicated in `typeclasses/exits.py::WildernessReturnExit`
and `world/maps/wilderness_destination.py::resolve_wilderness_destination`. The user chose
Model A — the anchor occupies an authored wilderness footprint, gates sit on faces of that
footprint, and per-face rules replace the hardcoded pair. Constraints from the stock contrib
(Evennia 6.1, `contrib/grid/wilderness/wilderness.py`, unpatched):

- Boundary machinery is two-layered and agrees by construction:
  `WildernessRoom.set_active_coordinates` (lines 574–585) sets `traverse/view` lock strings on
  every self-loop exit purely from `wilderness.is_valid_coordinates(neighbor)`, and
  `WildernessExit.at_traverse` re-checks through `at_traverse_coordinates` →
  `is_valid_coordinates` before moving anything. Locks hide the exit; the re-check refuses the
  step even if a lock is ever stale.
- `at_prepare_room` is called at the very end of `set_active_coordinates` (line 589) — after the
  stock lock pass — on every coordinate activation. It is the sanctioned seam for per-cell exit
  adjustment; re-applying the same lock-string idiom there is stock-consistent, not a patch.
- `sync_wilderness()` already has a refresh pass that replays `at_prepare_room` for retained
  rooms after restart, so hook-level customization is self-healing.
- AGENTS.md: lore registries are frozen dataclasses and the source of truth; `world/ai/` is
  untouched; movement stays in the existing exit lineage; no released users, so registry v1 → v2
  is a clean replacement with no shim.

## Goals / Non-Goals

**Goals**

1. Anchors occupy an authored, possibly non-rectangular footprint of non-walkable wilderness
   cells; the wilderness is never walkable "over" a city.
2. Per-face gates: each authored gate is visible/approachable only from its exterior approach
   cell and leads to its registered grid room; other faces of the same footprint are plain
   blocked boundary.
3. Point-shape anchors (every direction at the entry cell reaches one exit) remain expressible —
   the legitimate cave/dungeon semantics.
4. Traversal (`WildernessReturnExit`) and the canonical resolver
   (`resolve_wilderness_destination`) read the same registry rules and the same validity rule,
   so the map never lies about where a step lands.

**Non-Goals**

- Any webclient presentation — the sibling change `wilderness-anchor-footprint-local-map` owns
  the presentation half (and `webclient-map-scale-legend` its scale note, serialized after it).
- New anchors (cave content), LLM generation, art, or any player-command surface change.
- Grid-layer changes inside the city (its rooms/exits are unchanged).
- A legend entry for boundary walls: an invalid cell renders exactly like the map's outer edge
  does today (absent), which is the established "you cannot go there" language.

## Decisions

### D1 — Registry v2 schema (shape mask + return-direction gates)

`world/lore/wilderness_entry.py` replaces the v1 record with frozen dataclasses:

```python
@dataclass(frozen=True)
class WildernessGate:
    return_direction: str        # canonical short key (n/ne/e/se/s/sw/w/nw)
    grid_xy: tuple[int, int]     # destination room coordinate on the anchor grid
    z_map_key: str               # destination map key, e.g. "capital_altoria"

@dataclass(frozen=True)
class WildernessEntryPoint:
    anchor_key: str
    shape: tuple[str, ...]       # ASCII mask; "#" = footprint cell, "." = outside
    origin_xy: tuple[int, int]   # wilderness cell of shape[0][0]
    gates: tuple[WildernessGate, ...]
```

`return_direction` is named from the wilderness side, where the rule is read: standing on the
gate's exterior approach cell, the exit with that key traverses to `grid_xy`. This kills the
hardcoded `key == "south"` comparison outright — the registry field and the exit key are the
same vocabulary. Its `face` is the opposite direction (the footprint side the gate sits on).

Derived pure helpers on the entry:

- `footprint_cells`: origin + mask offsets (empty for a point-shape entry).
- `anchor_cell`: the bounding-box midpoint of the `#` cells,
  `((min_x + max_x) // 2, (min_y + max_y) // 2)` in world coordinates (Python floor division —
  one deterministic tie-break for even spans). Validation requires the result to itself be a
  `#` cell: concave masks whose midpoint is `.`, and even spans whose tie-break falls in a
  hole, are rejected authored data, never silently rounded into the shape. For
  `capital_altoria` this stays `(60, 100)`, matching v1's entry coordinate.
- `approach_cell(gate)` (footprint entries): trace from `anchor_cell` along `face`'s delta,
  where `face` is the direction opposite `return_direction` (the footprint side the gate sits
  on), while cells are in the footprint; the first cell outside is the approach cell.
  Validation requires the ray to cross at least one footprint cell and land provider-valid and
  outside every footprint.

Mask grammar is strict — every row the same non-empty length containing only `#` and `.`, the
same well-formed-rectangle expectation the `altoria_capital.MAPSTR` loader imposes — and D5
rejects ragged or illegal masks as authored-data errors rather than tolerating them at read
time.

A mask of exactly one `#` encodes the **point-shape** variant: no footprint, no approach cell;
at the anchor cell itself every direction is a gateway to the single registered gate room. The
schema expresses the cave semantics directly; no special-case branch is needed elsewhere (the
gateway lookup checks both cases uniformly).
A point-shape entry's `approach_cell(gate)` IS its `anchor_cell` (the registry requirement pins
this identity), so every consumer formula — gate exit landing cell, gateway match, resolver —
uses `approach_cell` uniformly and can never receive `None` for a valid gate.

`capital_altoria` authors a 5×5 all-`#` mask (matching its 5×5 grid extent) with origin
`(58, 98)` (x = 58..62, y = 98..102). Gates:

| gate | return_direction | approach cell | grid destination |
|------|------------------|---------------|------------------|
| 南門 | `"n"`            | `(60, 97)`    | `(2, 0, "capital_altoria")` |
| 北門 | `"s"`            | `(60, 103)`   | `(2, 4, "capital_altoria")` |

The mapping preserves v1 intuition verbatim: v1's rule was "south at the entry coordinate →
North Gate", and v2 says "south at the north approach cell `(60, 103)` → North Gate `(2, 4)`".
What changes is everything the bug was made of: `(60, 100)` and the other 24 city cells are no
longer walkable wild ground, and entering through 北門 now lands the player at the cell outside
the wall instead of inside the phantom city point.

Why an ASCII mask: same idiom the project already uses for the city (`altoria_capital.MAPSTR`)
and that the stock contrib documents for arbitrary terrain shapes (pyramid example); authored
shape stays human-editable in the registry, and non-rectangular anchors (L-shape, crescent bay)
become a data change, not a code change. Rejected: `(width, height)` rectangles (cannot express
non-rectangular cities — the user explicitly required per-anchor shape), and per-cell
terrain-type registries (huge data, no expressiveness gain).

### D2 — Footprint invalidity via the provider

`ElosernWildernessMapProvider.is_valid_coordinates` becomes: inside the 0..223 rectangle AND not
in any `WILDERNESS_ENTRY_REGISTRY` footprint. The footprint set is computed from the registry at
call time through a small module-level cache keyed on the ordered `(anchor_key, entry)` pairs of
the live registry snapshot — the key tuple retains the entry objects, so CPython cannot recycle
their ids behind the cache's back and a `patch.dict`/rebind replaces value objects, producing a
key miss on the next call. The provider reads the registry as a module attribute of
`world.lore.wilderness_entry` at call time (never a `from … import` binding) so a rebinding in a
test is observed. Point-shape anchors contribute no cells. Consequences ride stock machinery
with zero new traversal code:

- Walking toward the city: the last valid cell's exit into the footprint is hidden and blocked by
  the stock lock pass, and the step is additionally refused by `at_traverse_coordinates` — the
  wall is enforced at both stock layers.
- `enter_wilderness` validation rejects footprint cells (stale/misconfigured gate exits fail
  closed with no clock charge).
- Monster population never runs at footprint cells (rooms are never activated there).
- `world.maps.wilderness_destination.wilderness_neighbor` gains the same validity rule (currently
  bounds-only): it returns `None` for provider-invalid neighbors, making the resolver and the
  minimap's adjacency truth match `at_traverse`'s refusal exactly. (v1 had no invalid interior
  cells, so bounds-only was accidentally equivalent; that equivalence dies with footprints.)

Gate faces are the only exception: `at_prepare_room` re-opens the one gate exit at each approach
cell (D3).

### D3 — Gate approach cells via `at_prepare_room` lock re-application

At a footprint entry's approach cell for gate G, `at_prepare_room` locates the room's exit whose
key is G's `return_direction` long form (the contrib normalizes exit keys to "north"…"northwest")
and sets its locks to `traverse:true();view:true()` — the exact string the stock lock pass uses
for valid neighbors. Because `at_prepare_room` runs after the stock pass in the same activation
and the stock pass recomputes every activation, the override is re-applied per-cell and no stale
state can survive a coordinate change; `sync_wilderness()`'s existing refresh pass heals retained
rooms after restart with no extra code.

The traversal itself needs no lock cooperation: `WildernessReturnExit.at_traverse`'s gateway
branch (D4) replaces the stock body entirely for a registered (cell, key) pair, so
`at_traverse_coordinates` — which would refuse the footprint neighbor — is never consulted for a
gate step. The lock re-application exists purely to make the exit visible/offerable.

Point-shape anchors need the same hook unconditionally: at the anchor cell the hook re-opens all
EIGHT directional exits. The gateway-match condition is therefore
`(footprint: cell == approach_cell(gate) AND dir == return_direction) OR (point-shape: cell ==
anchor_cell, any direction)` — uniform across traversal, resolver, and presentation. Validation
(D5) guarantees a point anchor's eight neighbors are provider-valid; re-opening all eight anyway
keeps offered exits identical to resolver truth by construction instead of relying on that
validation to make the stock pass agree.

`WildernessGateExit` (grid → wild) lands the traverser at `approach_cell(gate)` — never inside
the footprint. It already reads `self.db.anchor_key`; it gains `self.db.gate_direction` (the
gate's `return_direction`) set by `sync_wilderness()`, and resolves its gate from the entry by
that direction.

### D4 — Per-gate return routing (traversal + resolver in lockstep)

`world/maps/wilderness_destination.py` gains one registry-reading helper, shared verbatim by
both consumers: given current coordinates and a direction, return the owning entry+gate when the
coordinates equal a footprint entry's `approach_cell(gate)` and the direction is that gate's
`return_direction`, or (point-shape) when the coordinates equal the anchor cell and any
direction matches. `WildernessReturnExit.at_traverse` replaces its
`current == entry.wilderness_xy and self.key == "south"` match with this helper; the destination
room resolves from `gate.grid_xy`/`gate.z_map_key` via `GridRoom.objects.filter_xyz` — the
hardcoded "the gate room is the room the gate exit hangs on" assumption (`_grid_room_for_anchor`)
is deleted, not generalized. `resolve_wilderness_destination` calls the same helper and the same
`wilderness_neighbor` validity rule, so the resolver returns `grid:`/`wild:`/`None` exactly where
traversal reaches a grid room, a wild cell, or refuses. Clock cost, arrival recording, veto, and
cleanup semantics are unchanged (both branches still complete through
`after_successful_movement`).

Rejected: provisioned per-gate room objects (the pooled-room camera model means the approach cell
IS a recycled `TerrainRoom`; provisioning per gate fights the contrib's room recycling).

The resolver's existing `gateway_rule` test-injection seam keeps its injection semantics under a
v2-typed rule callable; the injection-mismatch test updates with the rewrite rather than being
dropped.

### D5 — Registry validation before persistence

`world/lore/wilderness_entry.py` gains `validate_wilderness_entries()` (pure, no DB), called
from `sync_all()`'s wilderness mirror step so malformed authored data fails at startup, matching
the all-or-nothing import convention. Rejection rules:

- Mask grammar: empty mask, empty or ragged row, any character other than `#`/`.`, or no `#`.
- Geometry: any `#` outside the provider rectangle; a footprint whose `#` cells are not
  4-connected; a derived `anchor_cell` that is not itself a `#` cell.
- Gates (footprint entries): a `return_direction` that is non-canonical or duplicated within one
  entry; a gate whose approach-cell ray crosses no footprint cell, or whose approach cell is
  provider-invalid or lies inside any footprint.
- Gates (point-shape entries): any gate count other than exactly one; an anchor cell whose eight
  neighbors are not all provider-valid (in the rectangle and outside every footprint) — a
  gateway advertised toward an invalid cell could not stay honest.
- Global across the registry: two entries' footprints overlap; two gates share the same
  `(approach_cell, return_direction)` key; a point anchor cell equals another entry's gate
  approach cell (one cell would answer two different gateway rules); a `grid_xy` outside the
  extent of its `z_map_key`; an `anchor_key` absent from `ANCHOR_PLACEMENT_REGISTRY`
  (v1 rule, kept).

### D6 — Presentation: boundary absent, gates resolved

The webclient half — footprint cells never rendering as walkable ground, per-gate nodes on both
sides, and grid-side node identity (candidate id, slot direction, label) derived from
`(entry, gate)` → `approach_cell(gate)` plus the registered direction (slot direction =
`return_direction`'s opposite) instead of gate exit key/alias parsing — is specified,
implemented, and tested in the sibling change `wilderness-anchor-footprint-local-map`, which
depends on this change's registry v2 API and carries its own one-engineer-day budget. Splitting
here is deliberate: this change already spans registry, validation, provider, resolver,
traversal, bootstrap, and three contract-test migrations; the presentation + browser surface is
a genuinely independent review unit.

## Risks / Trade-offs

- [Lock re-application ordering] → guaranteed by call order in the same
  `set_active_coordinates` activation (stock locks first, hook last); tests assert per-face lock
  state after arrivals from both sides and after the restart refresh pass.
- [Recycled rooms keep stale exit locks across coordinate changes] → the stock pass recomputes
  every activation before the hook re-applies; pin with a movement test that enters an approach
  cell, leaves by a different direction, and re-enters from elsewhere.
- [`enter_wilderness`/stale exits targeting footprint cells] → provider rejects; the gate exit
  fails closed without clock charge (existing fail-closed scenarios extended to footprint cells).
- [Resolver/traversal drift reappears with richer rules] → single shared helper is the only
  implementation; the existing adjacency-truth pinning test (resolver prediction vs real
  arrival) extends to per-gate and wall directions.
- [Registry data error bricks startup] → deliberate fail-fast at `sync_all()`, matching the
  import convention; validation unit tests cover each rejection.

## Migration Plan

No migration: the single entry is re-authored in code (`wilderness_entry.py`), `sync_wilderness()`
heals mis-provisioned gates (its existing healing scenarios generalize per face: wrong
`db.gate_direction` is corrected in place), test DBs are recreated. Rollback = revert the commit
series; the only persisted data touched is Script payloads regenerated by `sync_all()` and gate
exits' `db` attributes.

Consumers migrated inside this change (clean cutover, no shim):
`typeclasses/exits.py` (both exit lineages), `world/maps/wilderness_destination.py` (including
the `gateway_rule` injection seam), `world/maps/wilderness_population.py` (`CAPITAL_ENTRY_XY`
re-pins to the north-gate approach cell `(60, 103)`, hunting band recentered per its delta), and
the v1-coordinate/`wilderness_xy` test consumers:
`world/lore/tests/test_wilderness_entry.py`,
`world/rules/tests/test_map_knowledge_integration.py`,
`world/rules/tests/test_movement_settlement.py`, `world/rules/tests/test_party_follow.py`,
`world/maps/tests/test_bootstrap.py`, `world/maps/tests/test_city_wilderness_roundtrip.py`,
`world/maps/tests/test_wilderness_population.py`, `world/maps/tests/test_wilderness_provider.py`,
`world/maps/tests/test_wilderness_destination.py`, `typeclasses/tests/test_exits.py`.
The webclient consumers (`web/webclient/presentation/local_map.py`, its tests,
`web/tests/browser/seed.py`) belong to `wilderness-anchor-footprint-local-map`.

## Open Questions

- Exact zh-TW node label for gate approach presentation (implementation decision against the
  existing `_wild_region_label`/room-key style; not spec-blocking — the grid side already labels
  by room key).
- Whether `anchor_cell` should eventually replace `ANCHOR_PLACEMENT`'s separate `(2,2)` — out of
  scope; the two registries stay independent per change-12 design.
