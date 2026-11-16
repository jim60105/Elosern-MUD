# Design

## Context

Facts below were checked on master at e076e764.

- Every settlement document has exactly one `anchor_room` node, and the map composer
  rejects a document without one. `ANCHOR_PLACEMENT_REGISTRY`
  (`world/lore/anchor_placement.py`) maps each document's `location_ref` to that node
  as a `QualifiedRef`. `static_references.anchor_entrance_xyz(placement)` turns it into
  the current `(x, y, map_id)`. `GridRoom.objects.filter_xyz(xyz=...)` uses
  `filter_family`, so it also finds `AnchorRoom`.
- For each of the 15 subraces in the D7 table, the anchor key equals the settlement's
  `location_ref` and its id. Each landing node is the document's only `anchor_room` node.
- `world/maps/static_references.py::StaticWorld` is the adoption-time closure over every
  authored static declaration family. It is built from the published registries
  (`published_static_world`) or from a candidate (`static_world_for_candidate`, used by
  `world/maps/runtime.py`). `PLACE_REGISTRY` already joins it as a lore-side Python family.
- Anchors come from the published geography, so they cannot be checked when a lore
  module is imported.

## Goals / Non-Goals

Goal: a validated, data-only declaration of where each subrace starts, plus a resolver
that turns it into a room. Nothing calls the resolver yet. Activation starts using it in
`subrace-start-settlements`, so this change alters no player-visible behavior.

Non-goals: activation, `home`, test stubs for activation, browser fixtures, and anything
about 虛境 or city gates.

## Decisions

### D1. Registry shape: subrace to anchor key, in the lore layer

New file `world/lore/start_locations.py`:

```python
@dataclass(frozen=True)
class SubraceStartLocation:
    """One subrace's start settlement, named by its anchor (location) identity."""

    subrace_key: str
    anchor_key: str


SUBRACE_START_LOCATION_REGISTRY: dict[str, SubraceStartLocation] = {
    row.subrace_key: row
    for row in (
        SubraceStartLocation("human_royal", "town_olive_ferry"),
        # ... one row per SUBRACE_REGISTRY key, table in D5
    )
}


def validate_start_locations(
    registry: Mapping[str, object], subraces: Mapping[str, object]
) -> None:
    """Reject a start registry that does not cover ``subraces`` exactly once."""


validate_start_locations(SUBRACE_START_LOCATION_REGISTRY, SUBRACE_REGISTRY)
```

`validate_start_locations` raises `ValueError` in this order:
1. a value is not a `SubraceStartLocation`: `f"start location {key!r} must be a SubraceStartLocation"`
2. `row.subrace_key != key`: `f"start location {key!r} declares mismatched subrace {row.subrace_key!r}"`
3. `key not in subraces`: `f"start location {key!r} names an unknown subrace"`
4. `anchor_key` is not a non-empty `str`: `f"start location {key!r} must name a non-empty anchor key"`
5. after the loop, `missing = sorted(set(subraces) - set(registry))`. If it is non-empty:
   `f"subraces without a start location: {missing}"`

Why an anchor key and not a `(settlement, node)` reference? The owner wants the
landing room to be the settlement's gathering room, which in the map data is its anchor
room. Each settlement has exactly one, and its placement is already a qualified node
identity. Naming only the anchor means a row cannot point at the wrong node of the
right settlement. Moving the anchor node moves the start room with it. Whether the
anchor exists cannot be checked when the lore module is imported, because anchors come
from the published geography. That check runs at adoption instead (D2 below).

A separate module, not a new `Subrace` field. `Subrace` is built positionally in
`races.py` and in the synthetic kit, and its `home_anchor_key` means the lore homeland.
For humans that is not where a character starts (for example `human_royal` lore points
at the capital, while it starts in a town).

Registry inventory: add
`_spec("start_locations", "起始地點", "聚落", _attr("world.lore.start_locations", "SUBRACE_START_LOCATION_REGISTRY"), f"{_LORE}/start_locations.py", "anchor_key")`
to `world/lore/registry_index.py`, after the `starting_kits` line. Use no `ref(...)`
metadata.

### D2. Adoption-time closure: one more StaticWorld family

In `world/maps/static_references.py`:
- `StaticWorld` gains the field `start_locations: Mapping[str, str]` (subrace key to
  anchor key), placed after `place_rooms`.
- `problems()`, after the place-room loop:

```python
        for subrace_key, anchor_key in self.start_locations.items():
            placement = self.anchor_placements.get(anchor_key)
            if placement is None:
                problems.append(
                    f"start location {subrace_key}: anchor {anchor_key!r} has no "
                    "settlement placement"
                )
                continue
            check_node(f"start location {subrace_key}", placement.node)
```

- `fingerprint`: append `tuple(sorted(self.start_locations.items()))` to `parts`.
- `published_static_world()` and `static_world_for_candidate()` both pass
  `start_locations=MappingProxyType({key: row.anchor_key for key, row in SUBRACE_START_LOCATION_REGISTRY.items()})`,
  importing the registry inside the function as the other families do.
- `binding_signature()` is unchanged. It keys presenter caches, and no presenter reads
  start locations.

This rejects adoption at server start (`runtime.adopt` and `sync_all`), before any
persistent write, as the spec requires. It is the same pattern `PLACE_REGISTRY` uses.

### D3. Resolver: `world/rules/start_location.py`

```python
class StartLocationError(ValueError):
    """A subrace's start room cannot be resolved."""


def resolve_start_room(subrace_key: str | None) -> Any:
    """Return the materialized anchor room of ``subrace_key``'s start settlement."""
```

The body uses function-local imports (`GridRoom`, `ANCHOR_PLACEMENT_REGISTRY`,
`SUBRACE_START_LOCATION_REGISTRY`, `anchor_entrance_xyz`,
`elosern_map_core.references.ReferenceError`). Steps:
1. `row = SUBRACE_START_LOCATION_REGISTRY.get(subrace_key) if subrace_key else None`.
   If `None`, raise `StartLocationError(f"subrace {subrace_key!r} has no start location")`.
2. `placement = ANCHOR_PLACEMENT_REGISTRY.get(row.anchor_key)`. If `None`, raise
   `f"start settlement {row.anchor_key!r} has no map placement"`.
3. `xyz = anchor_entrance_xyz(placement)`. Convert a `ReferenceError` to
   `f"start settlement {row.anchor_key!r} does not resolve"`.
4. `room = GridRoom.objects.filter_xyz(xyz=xyz).first()`. If `None`, raise
   `f"start room of {row.anchor_key!r} is not built"`.

There is no fallback room, because `world/maps/AGENTS.md` forbids reader fallbacks.
Function-local imports matter for two reasons: the synthetic kit's swaps stay visible,
and test patches can target one attribute, `world.rules.start_location.resolve_start_room`.

### D4. Synthetic kit row

 in `world/tests/synthetic_data/data_characters.py` add
  `SYNTH_START_LOCATIONS: dict[str, SubraceStartLocation] = {"t_duskmari_evensong": SubraceStartLocation("t_duskmari_evensong", "t_hollow_tarn")}`.
  In `targets.py`, add it to the content table as `"start_locations": lambda: SYNTH_START_LOCATIONS`,
  and add
  `"start_locations": ("world.lore.start_locations", "SUBRACE_START_LOCATION" + "_REGISTRY")`
  to `REGISTRY_TARGETS`. Export `SYNTH_START_LOCATIONS` from `__init__.py` the same way
  as `SYNTH_STARTING_KITS`. `t_hollow_tarn` already has a synthetic placement on a
  borrowed node that is materialized as a real room, so the real resolver works inside a
  scope of `("subraces", "start_locations", "anchor_placements")` once
  `sync_test_settlements((placement.node.map_id,))` has run.

Coupling note, to be added to the `world/tests/synthetic_data/__init__.py` docstring: the
`start_locations` and `anchor_placements` swaps belong together. A scope that swaps
`anchor_placements` without `start_locations` (or the reverse), and then calls
`validate_static_references()` (through `sync_grid`, `sync_all`, `sync_interiors` or
`runtime.adopt`), fails the start-location family. Today no scope does that. Task 4.2
greps for it.

### D5. Shipped mapping (game data, not spec)

| Subrace | Anchor key | Anchor node (room name) |
|---|---|---|
| `fionnen` | `elven_village_fionnen` | `light_court` (林間光庭) |
| `ciaran` | `elven_village_ciaran` | `village_plaza` (村中廣場) |
| `eolas` | `elven_village_eolas` | `valley_floor` (谷底空地) |
| `human_royal` | `town_olive_ferry` | `central_plaza` (中央廣場) |
| `human_noble` | `town_steed_plain` | `central_plaza` (中央廣場) |
| `human_coastal` | `port_fishers_cove` | `central_plaza` (中央廣場) |
| `human_plains` | `town_orange_blossom` | `central_plaza` (中央廣場) |
| `human_highland` | `town_silver_ridge` | `central_plaza` (中央廣場) |
| `foxkin` | `city_fox_fire` | `central_plaza` (狐火石坪) |
| `bearkin` | `city_iron_claw` | `central_plaza` (鐵砧石坪) |
| `catkin` | `city_shadow_wood` | `central_plaza` (苔石坪) |
| `wolfkin` | `city_moon_howl` | `central_plaza` (嚎月石坪) |
| `bovinekin` | `city_horn_plain` | `central_plaza` (野牛石坪) |
| `tigerkin` | `city_tiger_roar` | `central_plaza` (虎嘯石坪) |
| `rabbitkin` | `city_swift_wind` | `central_plaza` (長風石坪) |

The registry stores only the first two columns. The node column is what adoption
derives, and it is listed for review only.

## Risks / Trade-offs

- [A synthetic scope or a non-borrowed `install_synthetic_catalogs()` swaps one of the
  two coupled registries and then validates.] Mitigation: the coupling note above and
  the grep in task 4.2. The browser path uses `borrow_authored_world=True`, which merges
  the kit placements.
- [Two of the rows depend on the elven village documents.] Already merged in e076e764.
