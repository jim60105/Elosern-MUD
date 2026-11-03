# Locations and districts

## `content/maps/locations.yaml`

One singleton document (`id: locations`). It lists every static geographic
location, including those with no local map yet, such as the dungeons.

```yaml
version: 1
kind: locations
id: locations
locations:
  village_ciaran:                       # stable id; never rename
    kind: elven_village                 # capital | city | town | port | elven_village | dungeon
    display_name_zh: 暗影谷村
    description: Ciaran village underground on the western side of the neutral
      central range.                    # map-facing English prose
    cell: {cell_x: 1340, cell_y: 1220}  # 1 km wilderness cell, y grows north
    geographic_constraint: Underground settlement on the western flank of the central mountains
    scene_archetype:                    # nullable; must be a registered archetype when set
```

Rules and joins:

- A location **never** lists its local maps. A settlement declares
  `location_ref: <location_id>`, and the editor's 開啟本地圖 follows that
  field. At most one settlement may bind a location.
- **Moving a location**: change `cell` and nothing else. The settlement's world
  frame comes from this cell and its unique `anchor_room`, and its footprint
  origin is this cell plus the entry's offset, so every node's world metres,
  the mask, its midpoint and every gate approach translate by the same delta
  (see [settlements.md](settlements.md)). The cell must be inside the frame and
  on the mainland. A footprint must also be walkable: no ridge wall or river.
- Political affiliation, population and dungeon floor counts are **not**
  map fields. They live in `ANCHOR_LORE` (`world/lore/anchors.py`). Every
  `ANCHOR_LORE` row must have a location with the same id. Nation capitals
  (`NATION_REGISTRY[*].capital_anchor_key`) must be `kind: capital`. You
  therefore cannot add a location for a new nation's capital, or remove a
  location, without touching Python lore. Ask first.
- A new location is just a new key here. Its local map is a separate,
  optional new settlement document.
- Deleting a location is refused while a settlement binds it, a district
  landmark names it, or the reference index lists incoming references to
  `location:<id>`. Qualified IDs are written `domain:map:object`, and an
  empty part is left out: `location:village_ciaran`,
  `settlement_node:capital_altoria:central_plaza`,
  `wilderness_cell:1250,2420`.

### Location kinds

`kind` is a closed list: `capital`, `city`, `town`, `port`, `elven_village`,
`dungeon`. Use the matching ID prefix (`capital_`, `city_`, `town_`,
`port_`, `village_`, `dungeon_`).

| Kind | Use it for |
| --- | --- |
| `capital` | a nation's seat; `NATION_REGISTRY` names it |
| `city` | an inland national settlement of about 25,000 people or more, including a beast tribal city |
| `town` | a smaller national settlement, a frontier keep or a ferry town |
| `port` | a settlement whose role is a sea harbour, whatever its size |
| `elven_village` | hidden; neutral, no nation |
| `dungeon` | hidden; carries floors, not population |

`elven_village` and `dungeon` are hidden from public map knowledge; every
other kind is public. A capital draws as `capital` on the world map and the
other public kinds as `settlement`.

Adding or renaming a kind is a code change that must agree in all of these
places, so ask before you do it:

- `packages/map-core/elosern_map_core/schema.py` → `LOCATION_KINDS`;
- `world/lore/anchors.py` → `AnchorKind`;
- `tools/map-editor/frontend/src/components/ContinentInspector.vue` →
  `LOCATION_KINDS` (the inspector's dropdown labels);
- `web/webclient/presentation/world_map_geometry.py` → `_place_geometry`
  (which wire kind a place draws as);
- `world/rules/sight.py` and `world/rules/wilderness_disclosure.py` →
  `HIDDEN_ANCHOR_KINDS`, only when the new kind is hidden;
- `world/lore/tests/test_anchors.py`, which expects every `AnchorKind` to be
  used by some shipped location.

A national location also needs its `ANCHOR_LORE` row (nation and population).
That change stales the reference context; regenerate it.

## `content/maps/districts.yaml`

A singleton (`id: districts`). These are the world-map districts that the
player discovers by visiting the district's landmark. This document is the
only authority for districts. `world/lore/map_districts.py` only loads it.

```yaml
version: 1
kind: districts
id: districts
districts:
  north_deep_forest:
    district_name_zh: 北部深林          # unique across districts
    landmark_name_zh: 古樹之心          # unique across districts
    landmark:                           # qualified reference, see below
      domain: wilderness_cell
      map_id:
      object_id:
      cell: {cell_x: 1250, cell_y: 2420}
    kind: region                        # region | voronoi
    region_key: north_deep_forest       # required for region, empty for voronoi
```

### Landmark reference

Write all four keys every time, and leave the unused ones empty:

| `domain` | `map_id` | `object_id` | `cell` |
| --- | --- | --- | --- |
| `wilderness_cell` | empty | empty | `{cell_x, cell_y}` |
| `location` | empty | location id | empty |
| `settlement_node` | settlement id | node id | empty |
| `interior_room` | interior id | room id | empty. The schema accepts it, but the **game refuses** it as a district landmark, because it has no continental position. |

A settlement-node landmark follows its node. Moving the node or the whole
settlement moves the landmark without editing this file. Never replace a
node reference with the node's current cell.

### District kinds

- `region` takes every cell of one terrain region. Its landmark must lie in
  that region. Today only `north_deep_forest` is a region district.
- `voronoi` districts seed the walking-distance partition. Each landmark must
  be on reachable land. It must not lie inside a region district's region,
  and it must be **≥ 100 km** from every other Voronoi landmark. The target
  district size is about 200 km.

### Optional distant-sighting fields

A district may also author how it is seen from far away. All four fields are
optional and absent fields stay absent; the editor never invents a value.

```yaml
  march_watch_hills:
    # ...name, landmark, kind and region_key as above...
    vantage: true            # this landmark's cell widens ground sight
    sight_km: 30             # daytime sighting range in km
    light_km: 12             # night (light) range in km; omit for a dark place
    silhouette_zh: 一座燃著燈火的石塔哨所   # what a distant viewer sees
```

- `vantage` is a boolean and defaults to false. Only `true` makes the
  landmark's wilderness cell a widened-viewpoint cell.
- `sight_km` and `light_km` are finite non-negative numbers. `light_km`
  describes a light source such as a lighthouse beacon, so a place with no
  night light omits it. Twilight reads `sight_km` scaled by the sight
  rulebook's twilight factor.
- `silhouette_zh` is non-blank text of at most 256 code points. A **positive**
  `sight_km` or `light_km` requires it: an authored range is never anonymous.
- `silhouette_zh` is authored prose, in the fantasy idiom of the world and
  never naming a command, mechanic or UI element. It is human-reviewed, like
  other authored wording, not a value a test pins.
- The sight rules themselves (light phases, radius rows, factors and the
  anonymous settlement silhouettes) belong to
  `world/rules/rulebook/sight.yaml`; see
  [距離制旅行與地形耗時](../../../../docs/development/distance-based-travel.md).
  A wild cell landmark with a range is a distant-sighting source; a landmark
  that references a settlement merges with that settlement's automatic
  source instead of producing a second marker.

### Diagnostics

Structure errors block loading:
- an unknown domain or reference;
- a missing `region_key` for a `region` district, or a `region_key` on a
  `voronoi` district;
- a duplicate name.

Semantic diagnostics are saveable work in progress:
- the landmark is in the sea, blocked or unreachable;
- `region_mismatch`;
- `region_territory_overlap`;
- `invalid_spacing`.

Any district change stales the partition, so regenerate it. The partition
generator rejects an `interior_room` seed.

### Editor equivalents

`create_district` and `set_district_field` cover names, membership
(`kind` and `region_key`, set together) and the landmark. There is no
district delete command. Removing a district is a deliberate hand edit: ask
first, then regenerate the partition.

Every district landmark with a continental position is drawn as a diamond on
the continent canvas (地點 layer); clicking it selects the district. Only a
`wilderness_cell` landmark drags. The release saves one `set_district_field`
command with `field: landmark` and the full four-key value
`{domain: wilderness_cell, map_id: null, object_id: null, cell: [x, y]}`, which
writes only `districts.yaml` and leaves the partition stale. Landmarks in the
`location` and `settlement_node` domains follow their referent and do not
drag; an `interior_room` landmark has no continental position and is not
drawn. The drag never turns a reference into a cell: switching domains stays a
deliberate choice in the inspector's 領域 selector. A negative cell (a drop
west or south of the frame) is refused with 400 and nothing is written; a sea
or unreachable cell saves as diagnosed work in progress
(`unreachable_landmark`).

The editor projection exposes `landmark.cell` as an `[x, y]` pair (or null)
and a derived `landmark_centre_m` (the referent's centre in metres, or null),
while the YAML keeps `{cell_x, cell_y}`.
