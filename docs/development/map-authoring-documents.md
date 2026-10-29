# Map authoring documents

The standalone map editor and the game read the same authored YAML documents.
`packages/map-core` (`elosern_map_core`) owns the document schema, the
restricted round-trip codec, deterministic source discovery, the authoring
diagnostics and the runtime acceptance gates. The core never imports Evennia,
Django, game modules, HTTP, UI state, a watcher or editor policy, and importing
it performs no filesystem work.

## Source set

Discovery is deterministic (lexicographic canonical relative paths):

| Path | Kind | Identity |
| --- | --- | --- |
| `content/maps/continent.yaml` | `continent` | fixed `continent` |
| `content/maps/locations.yaml` | `locations` | fixed `locations` |
| `content/maps/districts.yaml` | `districts` | fixed `districts` |
| `content/maps/settlements/<map_id>.yaml` | `settlement` | file stem |
| `content/maps/interiors/<interior_id>.yaml` | `interior` | file stem |

`content/map-editor-layouts/<interior_id>.yaml` is a typed `layout` document
for the codec but is never a world snapshot input. Generated artifacts (the
district partition, the reference context) and any other path are never
scanned as sources. Every document declares `version: 1` and a `kind`; the
kind, version and fixed id or file-stem identity must agree. Unknown document
kinds, unsupported versions, duplicate identities and missing singleton
documents fail the whole authoring load.

All shapes are documented machine-readably: `schema()` returns a deep copy of
the version-1 schema, and `python -m elosern_map_core schema` prints it as
JSON. That description is authoritative for the editor frontend as well.

## Coordinate naming

Every coordinate is explicitly named for its domain:

| Value | Fields | Unit |
| --- | --- | --- |
| wilderness cell | `cell_x`, `cell_y` | one-kilometre cell indices |
| continental geometry | `east_km`, `north_km` | absolute kilometres |
| settlement-local point | `x_m`, `y_m` or `east_m`, `north_m` | integer metres |
| road bend | `x_m`, `y_m` | integer metres |
| layout position | `x`, `y` | editor canvas units, never world geometry |

## Document fields

### continent

`frame_cells`, `cell_size_km`, `mainland_boundary_km[]`, `regions{}`,
`harbor_sites{}`, `terrain`.

- `mainland_boundary_km`: `{east_km, north_km}` vertices, at least three.
- `regions.<id>`: `display_name_zh`, `nation_key` (nullable), `terrain_flavor_zh[]`,
  `nominal_nation_keys[]`, `scene_archetype` (nullable). The seven core terrain
  region keys are required.
- `harbor_sites.<id>`: `display_name`, `cell`, `role`.
- `terrain`: `forest_edge[]` (`cell_x`,`cell_y`, X-increasing),
  `ridge{base_x, period, step, min_x, max_x, north_limit_y,
  mountain_corridor_half_width, passes[{y_min,y_max}]}`, `coastal_y_max`,
  `waterways{}` (`{route[], fords[]}` per waterway), `border_river_key`.
  Terrain geometry is validated by the core `TerrainDefinition`; inconsistent
  inputs are a saveable `terrain_inconsistent` diagnostic.

### locations

`locations.<id>`: `kind` (`capital`, `elven_village`, `dungeon`),
`display_name_zh`, `description`, `cell`, `geographic_constraint`,
`scene_archetype` (nullable). Political/population/floor lore stays with its
existing game owners.

### districts

`districts.<id>`: `district_name_zh`, `landmark_name_zh`, `landmark`, `kind`
(`voronoi` or `region`), `region_key` (required for `region`, forbidden for
`voronoi`).

`landmark` is a qualified reference:

```yaml
landmark:
  domain: settlement_node      # settlement_node | interior_room | location | wilderness_cell
  map_id: capital_altoria      # required for settlement_node/interior_room
  object_id: central_plaza     # required except for wilderness_cell
  cell: null                   # required exactly for wilderness_cell
```

This document is the sole district authority: `world/lore/map_districts.py`
loads and validates it against the published terrain and settlement/location
bindings, then publishes one immutable snapshot (startup step
the map-world adoption step). Structure faults reject the load; sea, blocked
or unreachable landmarks, region disagreement and insufficient declared
spacing are saveable semantic diagnostics that reject runtime adoption only.
Landmarks are never authored as coordinates, so moving a settlement node moves
the district's canonical visited identity without editing this document.

### settlement

`location_ref`, `binding{anchor_cell, local_anchor_m}`, optional
`options{map_visual_range, map_mode}`, optional `exit_prototype`
(`prototype_parent: xyz_exit`, `typeclass`), `nodes{}`, `roads[]`, optional
`wilderness_entry`, optional `city_gate`.

- `nodes.<node_id>` (the id is the stable identity and matches
  `^[a-z][a-z0-9_]*$`): `x_m`, `y_m`, `prototype_parent`
  (`grid_room`|`anchor_room`), `key`, `desc`, `anchor_key` (required exactly for
  `anchor_room`), `typeclass` (nullable), `scene_archetype` (nullable).
  Node coordinates are unique.
- `roads[]`: `source`, `destination`, `direction`
  (`n`/`ne`/`e`/`se`/`s`/`sw`/`w`/`nw`), `bends[]` (`{x_m,y_m}`, optional).
  Endpoints must exist, self-loops and duplicate ordered roads are rejected,
  and one node may not declare the same outgoing compass direction twice.
- `wilderness_entry`: `shape[]` (`#`/`.` footprint mask rows), `origin`,
  `gates[]` (`return_direction`, `destination_node`).
- `city_gate`: `node`, `exit_key`, `exit_aliases[]`.

### interior

`rooms.<room_id>`: `name_zh`, `desc_zh`, `scene_archetype` (nullable),
`art_key` (optional, nullable — the registered room-art key this room
addresses; an absent key declares no room artwork and the room renders its
archetype chain, and no key is ever inferred from the room id or a name);
`connections[]` (`source`, `destination`, `label`); optional `interior_links[]`
(`source_room`, `target_interior`, `target_room`, `label`, `return_label`);
optional `exterior{settlement, node, room, doorway_key, doorway_aliases[]}`.
`room` names the interior room the doorway opens into. Interiors carry no
physical coordinates; external entrance relationships are stored once, in the
owning interior document.

### layout

`positions.<room_id>`: `x`, `y` — editor-only placement, excluded from game
geometry and runtime snapshots.

## Restricted YAML

The codec uses `ruamel.yaml` round-trip mode with YAML 1.2 core scalars and
accepts only data-only values. It rejects:

- duplicate keys, detected on the event stream before mappings are constructed
  (quoted and unquoted spellings of one key are the same key);
- explicit or custom tags, anchors, aliases and merge keys;
- timestamps (values and keys), `.inf`/`.nan`, octal/hex/binary and underscored
  integer literals, sets and binary values;
- multiple documents, empty documents and non-string mapping keys;
- documents beyond 2 MiB, 32 nested collections or 100 000 entries per
  collection;
- unknown fields, unsupported versions and kinds, and any value/type mismatch
  (integer fields never accept booleans, fractions or numeric strings; strings
  are never coerced from numbers).

Comments attached to retained stable-ID objects (mapping keys such as nodes and
typed objects in identified lists such as roads), multiline prose, footprint
masks and road bends survive a serialize round trip. An unchanged sequence --
including one nested inside an identified object -- keeps its retained tree, so
comments inside unchanged bends and masks are preserved. Whitespace and
formatting may be normalized. When an object or an unidentified sequence is
changed, its comments may be removed with it. `serialize_document` validates
first, works on a copy of the retained tree, emits readable literal blocks for
multiline strings, and re-parses its own output; a candidate that would be
lossy or unsupported produces no text and leaves the caller's baseline
unchanged.

## Gates and diagnostics

Diagnostics are typed values with a stable `code`, a `category` (`structure`,
`semantic`, `external`, `freshness`), canonical `relative_path`, dotted
`field_path`, optional qualified `object_id` and one-based `line`/`column`.
They are emitted in deterministic order.

- **Structure** blocks load and writing: invalid YAML/values, unknown
  fields/versions/kinds, identity/stem mismatch, duplicate keys, coordinates or
  roads, unknown endpoints/references, self-loops, duplicate outgoing
  directions, multiple anchor rooms (`multiple_anchor_rooms`), anchor key mismatch
  (`anchor_location_mismatch`), duplicate location bindings across settlements
  (`duplicate_location_binding`), duplicate interior room identities (`duplicate_interior_room`),
  duplicate doorway keys on one exterior node (`duplicate_doorway`), duplicate gate
  destinations (`duplicate_gate_destination`), fingerprint mismatch and unsupported source paths.
- **Semantic** is saveable unfinished map work: missing anchor rooms (`missing_anchor_room`,
  including empty graphs `empty_graph`), point mask gate count (`point_gate_count`),
  disconnected footprints (`disconnected_footprint`), non-point midpoints missing hash cells
  (`invalid_footprint_anchor`), footprint/point cells outside the frame or on impassable terrain
  (`invalid_footprint_cell`), overlapping footprints or point containment (`overlapping_footprint`),
  undefined/out-of-frame approach rays (`invalid_gate_approach`), blocked approach terrain
  (`blocked_approach`), gate approach collisions (`gate_approach_collision`), duplicate gate
  approaches (`duplicate_gate_approach`), invalid point return neighbors (`blocked_point_neighbor`),
  `unreachable_landmark`, `terrain_inconsistent`, and `stale_partition` when a freshness value is supplied.
  Loading returns an
  `AuthoringWorld` with these diagnostics; structured editing and saving remain
  possible.
- **External/freshness** gate runtime adoption only.
  Remaining game-side checks (coordinate binding equalities, external scene archetypes,
  nations, district spacing and static references) gate candidate composition and adoption.

`compile_runtime(world, authoritative_external_result, partition_freshness)`
raises `RuntimeRejection` when the world has any diagnostic, when the external
result is missing, invalid, unsupported-version, fingerprint-less or bound to a
different world fingerprint, or when the partition freshness is missing, stale,
from a different input signature or from an unsupported algorithm version. Only
a fully accepted world yields the immutable `RuntimeMapSnapshot` (settlement
graphs plus the typed documents). A failed candidate never changes published
state.

## Read-only inspection

```console
uv run --locked python -m elosern_map_core schema
uv run --locked python -m elosern_map_core inspect <workspace-root>
```

`inspect` discovers the supported sources, loads the candidate and prints the
sorted document identities, fingerprints and diagnostics as JSON. It reports
`semantic_ready` from the authored diagnostics only; `runtime_ready` stays
`null` because inspection receives neither the authoritative external result
nor the partition freshness. It writes nothing to the inspected workspace.

Source provenance is derived during parsing (the only authority for line and
column) and carried on every typed document and diagnostic; a `SourceDocument`
envelope carries the canonical path, text and content fingerprint.

## Checks

```console
cd packages/map-core && uv run --locked python -m pytest
uv run --locked python -m unittest tests.test_map_authoring_contract
uv run --locked python -m tools.contract_gate
```
