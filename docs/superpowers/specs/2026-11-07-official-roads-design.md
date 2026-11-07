# Official roads design

Generate the wilderness road network (官道) between settlements with a
deterministic offline algorithm, so that moving or adding a settlement only
requires one regeneration, never hand-authored road data.

## Goals

- Nearby settlements are usually joined by a road.
- Distant settlements are reached through intermediate settlements.
- A settlement does not connect to every neighbour; terrain decides.
- Roads bend with the terrain and are never straight lines between endpoints.
- Roads appear on the area and travel maps and raise travel speed.

## Non-goals

- Sea routes, bridges, road tiers, and hand-picked or excluded roads.
- Road display on the world map or a map editor layer.
- A "prefer roads" routing rule. The planner already weighs steps by duration,
  so the faster road terrain attracts routes by itself.
- Migration between road network versions. The network is recomputed whole.

## Decisions

| Topic | Decision |
| --- | --- |
| Scope | Network, map display and movement speed |
| River crossing | Authored fords only; river passability is unchanged |
| Central range | No crossing; the east and west sides form separate networks |
| Node kinds | `capital`, `city`, `port`, `town` |
| Node requirement | The location has a settlement document with wilderness gates |
| Topology | Terrain-metric relative neighbourhood graph plus detour repair |

The lore states that the central range blocks inland traffic and that both
sides trade by sea (`docs/lore/overview.md`). Sea routes do not exist yet, so
the two networks stay unconnected.

`port_south_cape` has no settlement document, so it has no gates and stays out
of the network until that document exists. It then joins with no other change.
Elven villages and dungeons are excluded so that roads never disclose them.

## Algorithm

All inputs are explicit, and identical inputs produce identical output bytes.

Inputs: terrain definition, elevation bands, settlement gate approach cells,
anchor footprints and the road parameters.

### 1. Cost field

- Only walkable cells may carry a road, so rivers are crossed only at fords and
  anchor footprints are never entered. Steps use the runtime legality rule:
  eight directions with no diagonal corner cutting.
- A step costs its distance multiplied by the terrain travel time of the slower
  endpoint, a slope factor from the elevation band difference, and a seeded
  low-frequency noise factor of about ±15%.
- Cells in a forbidden region cost infinity. `north_deep_forest` is the only
  forbidden region, which splits the walkable continent into its east and west
  sides.

### 2. Terrain distance

The distance between two settlements is the lowest-cost path between any of
their gate approach cells. Two settlements are *terrain neighbours* when their
regions in the multi-source nearest-settlement labelling of the cost field share
a boundary.

### 3. Topology

1. Relative neighbourhood: keep a pair A, B unless some settlement C satisfies
   `d(A, C) < d(A, B)` and `d(C, B) < d(A, B)`. The kept set contains a minimum
   spanning forest, so every network is connected. A town beside a ford becomes
   the natural relay for traffic crossing there.
2. Detour repair: for every terrain neighbour pair, compare the cost through the
   network with the direct cost. While the worst ratio exceeds the configured
   limit (initially 1.8), add that pair and recompute.

### 4. Routing

Route the kept pairs from cheapest to most expensive. Cells already on a road
cost a configured fraction (initially 0.4), so later roads merge into shared
trunks and form junctions. A road leaves through whichever gate is cheapest, and
one gate may serve several roads. Ties break on stable settlement identifiers.

### 5. Self-check

Generation fails without writing the artifact unless all of these hold:

- Every node has at least one road.
- Each network is connected.
- Every road cell is walkable and every step is legal.
- The east and west networks share no node or cell.

The error names the node or road at fault.

## Road ends at gates

Roads stop at gate approach cells and never pass through a settlement. Continued
travel crosses the settlement's own map, and wilderness route planning does not
plan across a settlement. This is the intended behaviour.

## Units

| Unit | Responsibility |
| --- | --- |
| `content/maps/road_network.yaml` | Parameters: node kinds, forbidden regions, cost factors, detour limit, reuse factor, noise seed |
| `packages/map-core/elosern_map_core/roads.py` | The pure algorithm, on the `generation` extra (`numpy`, `scipy`) |
| `packages/map-core/elosern_map_core/roads_codec.py` | Artifact encoding, decoding and freshness on the standard library |
| `tools/road_network.py` | Game adapter: builds the input snapshot and writes the artifact; `--check` fails when it is stale |
| `world/maps/data/road_network.json` | Committed artifact: each road's end settlements and cell route |
| `world/maps/road_network.py` | Runtime read view with constant-time road cell lookup |

The parameters live outside `continent.yaml` because the elevation artifact's
freshness depends on that document, and tuning roads must not invalidate it.

## Integration

- `world/maps/runtime.py`: `map_world_adoption` requires a current road artifact
  and rejects the candidate otherwise, matching the partition gate. The runtime
  never computes the network.
- `world/rules/travel_cost.py`: `wilderness_terrain` returns `road` when both
  ends of the step are road cells and the existing regional terrain otherwise.
  Planning, prediction and charging all read this function.
- `web/webclient/presentation/area_map.py`: the `road` fact reads the road cell
  set instead of the fixed `False`.
- The web client needs no change. `travel-paint.js` already draws road cells, and
  the facts follow the existing map disclosure, so unrevealed roads stay hidden.

Walkability, river and ridge barriers, region prose, the district partition and
elevation data are unchanged.

## Regeneration

After changing a settlement's location or gates, the terrain or the parameters:

```sh
uv run --locked python -m tools.road_network
```

Commit the artifact with the source change. A stale artifact fails `--check` and
startup adoption.

## Error handling

- Invalid `road_network.yaml` content, such as an unknown region or kind, is
  rejected with no default substitution.
- A failed generation leaves the committed artifact unchanged.
- A missing, corrupt or stale artifact rejects map world adoption.

## Testing

Tests use small synthetic maps, carry no game data and assert no wall-clock time.

| Area | Cases |
| --- | --- |
| Algorithm | A middle settlement removes the long pair; rivers are crossed only at fords; a forbidden region creates two networks; a large detour adds a road; later roads reuse earlier cells; repeat runs match byte for byte |
| Self-check | Isolated node, unwalkable gate approach and joined networks all fail |
| Codec | Round trip; changed input reads as stale; corrupt artifact is rejected |
| Movement | Road speed needs road cells at both ends; a partial step keeps regional terrain; the planner picks the road at equal distance |
| Map | Road cells publish `road: true`; unrevealed cells publish nothing |
| Shipped data | The committed artifact passes `--check` in the existing CI gate |

Whether the distribution looks reasonable is human review, not an automated
visual test. The generator can write an uncommitted preview image of settlements,
roads, rivers and fords, and the parameters are tuned from that image.
