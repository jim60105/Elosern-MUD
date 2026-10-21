# Metric settlement cutover

`activate-metric-settlements` moves the two authored outdoor settlements from
their compact logical grid onto the approved integer-metre local frames
(world-map-scale design §8/§9) and converges every identity consumer in place.
There is no database migration, no compatibility alias and no second
authoritative map.

## Unit and ownership contract

| Concern | Unit / owner |
| --- | --- |
| Settlement node coordinate | integer metres in the settlement's local frame (`x` east, `y` north), declared in `world/maps/altoria_capital.py` / `world/maps/village_ciaran.py` |
| Road length | Euclidean distance between the authored endpoints, owned by `world/maps/sparse_graph.py` |
| Road compass exit | authored per directed road (`ROADS` third field); an oblique metre delta never renames an exit |
| Room/exit lifecycle | `world/maps/bootstrap.py::sync_grid` / `sync_settlement_graph` |
| Map knowledge | `world/rules/map_knowledge.py` (sole writer) |
| Gate placement | `world/maps/city_gates.py::CITY_GATE_REGISTRY`, `world/lore/wilderness_entry.py` |
| Ghost anchor | `world/lore/anchor_placement.py` |
| Place exteriors | `world/lore/settlements/places*.py` |
| Scene art key | `world/maps/room_art.py::GRID_NODE_SCENE_ARCHETYPES` |
| Local-map and `地圖` projection | `web/webclient/presentation/local_map/`, `commands/localized/xyzgrid.py` |

`z` stays the logical map/layer key; it is never physical elevation. Interiors
without coordinates stay coordinate-free connected scenes.

## Authored tables

- `PROTOTYPES`, `NODE_IDS` and `XYMAP_DATA["options"]`/`["prototypes"]` are
  keyed by the metre coordinate. `XYMAP_DATA` carries no ASCII `map`: it is the
  sparse declaration, not a contrib map.
- `ROADS` entries are `(source identity, destination identity, compass octant)`.
  The octant preserves every pre-cutover exit direction and the two capital
  shortcuts (工匠巷↔校場外 `ne/sw`, 大神殿前↔東市 `se/nw`).
- The measured baselines at the 1.25 m/s healthy settlement speed are 2,193 s
  (南門→中央廣場, ~37 min), 5,618 s (南門→王宮前庭, ~94 min) and 431 s
  (隱密小徑→長老古樹下, ~7 min). Unequal segment lengths charge and display
  unequally.

## In-place cutover

`sync_grid()` plans both graphs read-only, then applies one transaction:

1. Rooms bind by their stable `sparse_node_identity` tag, never by coordinate.
   A moved room keeps its dbid, occupants, `home` references and inbound
   object references; only its XYZ tags and cached projection change.
2. Exits bind by their road identity tag and converge in place (location,
   destination, both coordinate tag sets, key/aliases, prototype).
3. Each moved node contributes an old→new binding. The knowledge owner rewrites
   every affected player's `grid:` ids, preserving first/last-seen ticks and
   merging collapsed ids; it never records a new arrival.
4. A second startup performs no managed write and logs no prune event.
5. A failure rolls back the whole transaction, reloads every touched room/exit
   and resets the attribute caches of every journalled knowledge record.
6. An unbound legacy room that would be pruned while occupants, a `HOME`
   reference or an inbound destination still point at it refuses the run before
   any write.

A database that booted an older version may still carry the retired ASCII
declarations in `XYZGrid.db.map_data`; convergence removes exactly the declared
settlement ids and drops the process-local projection. No room or exit is
deleted by that cleanup.

## Verification

```sh
uv run --locked --env-file=<file> evennia test --settings test_settings.py --keepdb \
  world.maps.tests.test_bootstrap \
  world.maps.tests.test_altoria_capital \
  world.maps.tests.test_village_ciaran \
  world.maps.tests.test_sparse_graph \
  world.maps.tests.test_city_movement_cost \
  world.maps.tests.test_wilderness_destination \
  world.lore.tests.test_anchor_placement \
  world.lore.tests.test_wilderness_entry \
  world.rules.tests.test_map_knowledge
```

`<file>` contains `MUD_TEST_SETTINGS=1`. Local-map coverage runs through
`web.webclient.presentation.tests.test_local_map` (non-browser) and the managed
browser classes; CI owns the complete evidence run.
