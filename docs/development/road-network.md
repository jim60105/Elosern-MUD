# Wilderness road network

The wilderness road network (官道) joins the gated settlements with roads that
an offline generator derives from the terrain. Nobody authors road cells. The
approved design is
`docs/superpowers/specs/2026-11-07-official-roads-design.md`.

| Unit | Role |
| --- | --- |
| `content/maps/road_network.yaml` | Authored parameters: node kinds, forbidden regions, slope and noise factors, detour limit, reuse factor |
| `packages/map-core/elosern_map_core/roads.py` | The pure generator, on the map core's `generation` extra (NumPy, SciPy) |
| `packages/map-core/elosern_map_core/roads_codec.py` | Artifact encoding, decoding and freshness, standard library only |
| `tools/road_network.py` | Game adapter: builds the input from the candidate world and writes the artifact |
| `world/maps/data/road_network.json` | The committed, generated, read-only artifact |

## Regenerating

Run from the repository root:

```console
uv run --locked python -m tools.road_network
uv run --locked python -m tools.road_network --check
uv run --locked python -m tools.road_network --preview /tmp/roads.png
```

- The plain command writes `world/maps/data/road_network.json`.
- `--check` regenerates in memory and exits 1 when the committed file differs
  byte for byte. It never writes. CI runs it in the preflight job, in the step
  "Validate road network freshness".
- `--preview PATH` also writes a PNG of the whole frame. North is up. The image
  shows sea, land, unwalkable land, forbidden-region land, fords, road cells and
  the nodes' gate approaches. Keep the path outside the repository; the image is
  never committed.
- `--output PATH` writes or checks another file instead of the committed one.

When the self-check fails, the command prints every problem, naming the node or
road at fault. It exits 1 and leaves the output file unchanged. Fix the source
or the parameters. Do not weaken the check.

The command prints the elapsed time and the peak resident memory. The figures
are informational and are never a pass criterion. On the shipped map, one run
takes about a minute and peaks near 2.5 GB.

## Regeneration order after a terrain change

The road input reads the committed elevation bands, and the adapter refuses a
stale elevation artifact. A change to `road_network.yaml` or to the region
speeds in `movement.yaml` needs only step 3 below: neither the partition nor
the elevation tiles depend on them. After any other change, meaning the
terrain or a settlement's location or gates, regenerate in this order (a step
that has nothing to update rewrites identical bytes):

1. The district partition:
   `uv run --locked python -m tools.map_district_partition`
2. The elevation tiles:
   `uv run --locked --project tools/map-editor python .agents/skills/map-data-authoring/scripts/regenerate_elevation.py`
3. The road network:
   `uv run --locked python -m tools.road_network`

Commit the regenerated artifacts with the source change that caused them.

## Runtime adoption

`world/maps/road_network.py` is the read view over the committed artifact. It
decodes the file once per process and answers road-cell lookups; it never
computes a road and never imports the generator, so the game runs without the
generation extra.

The startup step `map_world_adoption` calls `world.maps.runtime.adopt()`, which
accepts a candidate only when the committed artifact is current: its source
signature must match the candidate's own continent, location, settlement and
road-parameter documents, the committed elevation fingerprint and the authored
region speeds. Interiors and districts cannot move a road, so editing them
never invalidates the artifact. When the gate accepts, the decoded network is
published with the map bundle; `world.rules.travel_cost.wilderness_terrain`
then prices a step at road speed when both of its ends are road cells, and the
area and travel maps publish `road: true` for a disclosed road cell.

A rejected startup means the artifact is missing, corrupt or stale. A stale
artifact's error names the regeneration command; run it and commit the result.
A missing or corrupt artifact is reported as a read or decode rejection.

```console
uv run --locked python -m tools.road_network
```

Saving a settlement move in the map editor therefore needs a regeneration
before the game will adopt the new world. Editor-driven regeneration is not
part of this flow.

## What a node is

A location is a node when its kind is in `node_kinds` and its settlement
document declares at least one wilderness gate. A location without a settlement
document, or with no wilderness gate, is not a node. It joins the network after
its document gains gates and the network is regenerated. No other change is
needed.

Roads begin and end on gate approach cells. They never enter an anchor
footprint or the point gateway of a location that is not a node. They also
never cross a forbidden region, so each side of a forbidden barrier forms its
own network.

## Determinism

Identical inputs give identical bytes within one locked NumPy and SciPy
environment. Step costs are whole milliseconds, so path sums are exact. Where
several paths cost the same, SciPy's heap order picks one. A dependency upgrade
can therefore change the bytes with no source change, and `--check` then reports
the artifact as stale. Regenerate it and review the preview.

## Tuning the parameters

Every parameter lives in `content/maps/road_network.yaml`. Nothing here is a
requirement, and no test pins a value. You tune by looking at the preview.

### How a parameter reaches the roads

The generator runs three stages, and each parameter acts on one or more of them.

1. **Cost field.** Every legal step between two walkable cells gets a cost in
   milliseconds of travel time:
   `1000 × step × slower endpoint's seconds per cell × (1 + slope_factor_per_band × |band difference|) × (1 + noise_amplitude × mean noise of the two cells)`.
   `step` is 1 for a cardinal step and √2 for a diagonal one. The seconds per
   cell come from the region speeds in `movement.yaml`, and the noise lies in
   [-1, 1]. Steps move in eight directions and never cut a corner.
2. **Topology.** The distance between two settlements is the cheapest path
   between any of their gate approach cells. A pair is kept unless a third
   settlement is closer to both (relative neighbourhood graph). That rule has no
   parameter. Then, for every pair of terrain neighbours that is not kept, the
   cost through the kept network is compared with the direct cost, and the worst
   pair above `detour_limit` is added until none remains.
3. **Routing.** The kept pairs are routed from the cheapest to the most
   expensive. A step between two cells that already carry a road costs
   `reuse_factor` times its cost, so later roads join earlier ones. This
   discount affects routing only. It never changes which pairs are kept.

### The parameters

| Parameter | Range | Stage | Effect |
| --- | --- | --- | --- |
| `detour_limit` | ≥ 1 | Topology | How many extra roads the repair adds. Lower means more roads. At 3 or more it adds none and only the relative neighbourhood graph remains. |
| `reuse_factor` | 0.01 to 1 | Routing | How strongly roads merge into trunks. Lower means more shared cells, fewer distinct cells and longer detours to reach a trunk. At 1 nothing merges. |
| `slope_factor_per_band` | ≥ 0 | Cost field | The extra cost of each elevation band of difference between two cells. Higher means roads bend around slopes. At 0 elevation is ignored. |
| `noise_amplitude` | 0 to 0.9 | Cost field | The strength of the seeded noise on step costs. At 0 there is no noise. |
| `noise_wavelength_cells` | ≥ 2 | Cost field | The size of the noise features, in cells. Small values jitter, large values vary gently. |
| `noise_seed` | integer ≥ 0 | Cost field | Which noise pattern is used. A different seed rerolls the pattern. |
| `node_kinds` | list | Nodes | Which location kinds become nodes. See "What a node is". |
| `forbidden_regions` | list | Cost field | Regions that carry no road. Today only `north_deep_forest`. |

`forbidden_regions` and `node_kinds` are decisions about the world, not tuning.
Removing `north_deep_forest` lets a road cross the forest and join the east and
west networks, which contradicts the lore: the central range blocks inland
traffic, and both sides trade by sea. Adding `elven_village` or `dungeon` to
`node_kinds` would draw roads to hidden places.

### Measured effects

One run of the generator per row on the shipped map at the initial values, with
one parameter changed at a time. It is a single sample, so read the direction
and the size of a change, not the exact figures. Nothing was committed from
these runs, and a different map or seed gives different numbers.

The baseline is `detour_limit` 1.8, `reuse_factor` 0.4, `slope_factor_per_band`
0.15, `noise_amplitude` 0.15, `noise_wavelength_cells` 48 and `noise_seed`
20261107.

- **Roads** is the number of settlement pairs joined.
- **Distinct cells** is the number of cells that carry a road.
- **Shared** is the share of road cells used by more than one road.
- **Detour** is the average of road length over the straight distance between
  its ends. The smallest possible value on an eight-direction grid is about 1.
- **Turns** is the average number of direction changes per 100 road cells. It
  is a rough measure of how bent the roads are.

| Run | Roads | Distinct cells | Shared | Detour | Turns |
| --- | --- | --- | --- | --- | --- |
| Baseline | 78 | 15,415 | 23% | 1.19 | 9.7 |
| `detour_limit` 1.0 | 121 | 15,949 | 59% | 1.31 | 9.6 |
| `detour_limit` 1.3 | 106 | 16,025 | 51% | 1.30 | 9.3 |
| `detour_limit` 3.0 (same at 100) | 71 | 14,873 | 9% | 1.14 | 9.8 |
| `reuse_factor` 1.0 | 78 | 17,758 | 2% | 1.10 | 10.2 |
| `reuse_factor` 0.1 | 78 | 11,652 | 66% | 1.81 | 9.7 |
| `noise_amplitude` 0 | 79 | 15,580 | 25% | 1.20 | 10.5 |
| `noise_amplitude` 0.5 | 76 | 15,818 | 19% | 1.19 | 8.9 |
| `noise_amplitude` 0.9 | 77 | 16,568 | 20% | 1.24 | 10.6 |
| amplitude 0.5, wavelength 12 | 79 | 15,847 | 27% | 1.22 | 15.9 |
| amplitude 0.5, wavelength 150 | 77 | 15,979 | 19% | 1.18 | 9.3 |
| `slope_factor_per_band` 0 | 78 | 15,453 | 23% | 1.19 | 6.9 |
| `slope_factor_per_band` 0.6 | 77 | 15,191 | 24% | 1.20 | 10.8 |
| `noise_seed` 7 | 81 | 15,495 | 29% | 1.22 | 10.3 |

What the numbers say:

- **`detour_limit` changes the road count, not the look of the map.** Going from
  1.8 to 1.0 adds 43 roads, but the distinct cells barely move, because the
  added roads mostly follow trunks that already exist. It changes how many
  settlement pairs are directly linked, not how much road is drawn. Above about
  3 the repair does nothing here.
- **`reuse_factor` is the main lever for the look of the map.** It moves the
  distinct cells from 17,758 to 11,652 and the detour from 1.10 to 1.81. Around
  0.4 the network already merges into trunks without long detours. Going down
  to 0.1 makes roads wander far to join a trunk.
- **`noise_amplitude` has little effect.** From 0 to 0.9 the turns and the detour
  barely change. A noise of ±15% is small against the cost of leaving a straight
  line, so the noise alone does not bend roads. Wavelength matters more than
  amplitude, and a short one (12 cells) gives jitter, not curves: the turns
  rise from 9 to 16 per 100 cells.
- **`slope_factor_per_band` bends roads without lengthening them.** The turns go
  from 6.9 to 10.8 and the detour stays at about 1.2, so roads follow the
  ground more closely.
- **`noise_seed` rerolls the details.** In the sample it added 5 pairs and
  dropped 2, and the other figures stayed close to the baseline.

### Known limit of the look

Roads move in eight directions on a one-kilometre grid, so in open ground they
form straight runs joined by 45 degree segments. The parameters above reshape
where roads go, but none of them smooths a road into a curve. The curves you see
come from region boundaries, fords and elevation bands. If the preview still
looks too angular after tuning, the remedy is a smoothing step after routing,
which does not exist and would be a separate change.

### What to change for what you see

| In the preview | Change |
| --- | --- |
| Too many direct links between settlements | Raise `detour_limit` |
| A trip between close settlements goes a long way around | Lower `detour_limit` |
| Several near-parallel roads side by side | Lower `reuse_factor` |
| Roads make long detours to reach a trunk | Raise `reuse_factor` |
| Roads climb slopes straight on | Raise `slope_factor_per_band` |
| Roads avoid slopes by long detours | Lower `slope_factor_per_band` |
| Roads jitter on a small scale | Raise `noise_wavelength_cells` or lower `noise_amplitude` |
| One local stretch looks wrong and the rest is fine | Change `noise_seed`, then review everything again |

### What a change does to the game

Roads are generated whole, so any change in this file rewrites the whole
artifact. A changed `detour_limit` mostly adds or removes roads. A changed cost
parameter, or a new seed, can move paths anywhere, because the distances and the
routing order shift everywhere. Once the runtime change lands, a road cell moves
travel from the open-ground, woodland or mountain speed to the road speed, so a
changed network changes the travel time along every affected route. There is no
migration between networks.

### Procedure

1. Edit `content/maps/road_network.yaml`. An invalid value or an unknown region
   or kind is rejected with no default.
2. Preview without touching the committed artifact. The plain command and
   `--preview` alone both overwrite it, so give a scratch output:

   ```console
   uv run --locked python -m tools.road_network --output /tmp/roads.json --preview /tmp/roads.png
   ```

   A run takes about a minute and peaks near 2.5 GB. Zoom in on the image,
   because a road is one pixel wide in the 2700 by 2700 frame.
3. Repeat from step 1 until the preview looks right. Change one parameter at a
   time, because the effects overlap.
4. Regenerate the committed artifact with the plain command, then run `--check`.
   The parameters are outside `continent.yaml`, so no other artifact needs
   regenerating.
5. Commit `road_network.yaml` and `road_network.json` together, and add a row to
   the record below.

## Human review record

The parameter values in `content/maps/road_network.yaml` are initial values
that nobody has validated. They are tuned by looking at the preview, not by
tests. This record is not a gate: an open row blocks no change and no archive.

| Date | Parameters | Preview | Reviewer | Verdict |
| --- | --- | --- | --- | --- |
| 2026-11-07 | Initial values (detour limit 1.8, reuse factor 0.4, noise amplitude 0.15) | Generated, uncommitted | Pending | Pending review |
| 2026-11-07 | Runtime publication (road cells drawn on the travel and area maps) | Not yet reviewed at 1451x790 and 2560x1440 | Pending | Pending review |
