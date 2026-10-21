# Continental geography and coordinate units

`world/lore/` owns the frozen physical geography of the known continent. These
declarations are authoring contracts only: they spawn no rooms, are independent
of persistent room lifecycle, and do not activate the runtime wilderness scale.
`world/maps/wilderness_provider.py` keeps its current 224-cell, 10 km provider
until the projection, cost and physiology changes land.

## Declarations

| Module | Declaration | Contract |
| --- | --- | --- |
| `world/lore/wilderness_regions.py` | `MAINLAND_BOUNDARY_KM` | Ordered mainland boundary vertices in absolute `(east, north)` kilometres; implicitly closed. Shoelace area is exactly 5,000,000 km². |
| `world/lore/wilderness_regions.py` | `CELL_CENTER_OFFSET_M`, `CONTINENT_FRAME_CELLS`, `CONTINENT_CELL_SIZE_KM` | Wilderness cells are logical one-kilometre areas; the frame is 2700 × 2700 cells (`0 <= X, Y < 2700`). |
| `world/lore/wilderness_regions.py` | `HARBOR_SITE_REGISTRY` | Six reserved land-side harbor cells with their intended roles. A functional site is not a named anchor, city, quest or population. |
| `world/lore/wilderness_regions.py` | `cell_center_m`, `is_wilderness_cell`, `mainland_area_km2`, `is_on_mainland` | Pure geometry helpers over the declarations above; boundary points count as land. |
| `world/lore/anchors.py` | `ANCHOR_GEOGRAPHY_REGISTRY` | The canonical wilderness cell and geographic constraint of all nine lore anchors. Separate from both lore identity (`ANCHOR_REGISTRY`) and built grid rooms (`ANCHOR_PLACEMENT_REGISTRY`, deliberately still two entries). |
| `world/lore/anchors.py` | `LOCAL_FRAME_ANCHOR_REGISTRY`, `world_position_m` | Settlement-local metre anchor bindings and the cross-layer transform. |
| `world/lore/nations.py` | `CONTINENT_AREA_KM2`, `CONTINENT_POPULATION`, `ELVEN_POPULATION`, `NEUTRAL_LANDS_AREA_KM2`, `NEUTRAL_LANDS_POPULATION`, `CAPITAL_POPULATION_SHARE` | Rounded continental totals. The neutral lands have no separate regional population total. |
| `world/lore/nations.py` | `Nation.territory_km2`, `CapitalSupport`, `CAPITAL_SUPPORT_REGISTRY` | National area targets and the authored regional food/storage/water support (Valhalla additionally declares pastoral production and trade). |

National `territory_share` and `territory_km2` are area targets. They are
neither terrain nor actual control, and the mean inhabitants per square
kilometre they produce is an average, never a per-cell population raster.
Nothing in the declarations creates per-cell population or resource state.

## Coordinate units

- A wilderness cell is an area. Its representative center in absolute metres is
  `E = 1000 * X + 500`, `N = 1000 * Y + 500` (`cell_center_m`).
- Settlement positions are integer metres east/north. Their `z` coordinate
  remains the logical grid/layer and is never physical elevation.
- Cross-layer geometry uses the bound local anchor:
  `world_m = wilderness_anchor_center_m + local_m - local_anchor_m`
  (`world_position_m`). Altoria's plaza `(3500, 2850)` binds to cell
  `(860, 1080)`; Ciaran's plaza `(220, 305)` binds to cell `(1340, 1220)`.
- Never subtract settlement-local metres directly from wilderness cell indices.
  Interiors without coordinates stay coordinate-free connected scenes.
- The frame describes one continent. No planet size or further continent is
  inferred.

## Ownership boundary

`world/lore/` stays read-only: the declarations are consumed by later changes
(cost charging, local-map projection, settlement/wilderness rescaling) but this
change neither relocates persistent rooms nor wires the declarations into
movement, rendering, map knowledge or the lore codex. Declaring an anchor cell
also reveals nothing: knowledge and visibility rules remain authoritative, and
`ANCHOR_GEOGRAPHY_REGISTRY` is not a lore-codex category.

The earlier two-entry `ANCHOR_PLACEMENT_REGISTRY` continues to describe exactly
the anchors with a built grid map; all nine geographic cells live in
`ANCHOR_GEOGRAPHY_REGISTRY` instead.

## Verification

```sh
uv run --locked python -m unittest \
  world.lore.tests.test_nations \
  world.lore.tests.test_anchors \
  world.lore.tests.test_wilderness_regions \
  world.lore.tests.test_anchor_placement
uv run --locked python -m tools.spec_traceability check
uv run --locked python -m tools.test_data_lint check
```

The assertions behind `continental-geography` live in those data-contract test
modules; see `openspec/specs/continental-geography/spec.md`.
