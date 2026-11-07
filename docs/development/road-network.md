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
stale elevation artifact. After you change the terrain, a settlement's location
or gates, the region speeds or the road parameters, regenerate in this order:

1. The district partition:
   `uv run --locked python -m tools.map_district_partition`
2. The elevation tiles:
   `uv run --locked --project tools/map-editor python .agents/skills/map-data-authoring/scripts/regenerate_elevation.py`
3. The road network:
   `uv run --locked python -m tools.road_network`

Commit the regenerated artifacts with the source change that caused them.

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

## Human review record

The parameter values in `content/maps/road_network.yaml` are initial values
that nobody has validated. They are tuned by looking at the preview, not by
tests. This record is not a gate: an open row blocks no change and no archive.

| Date | Parameters | Preview | Reviewer | Verdict |
| --- | --- | --- | --- | --- |
| 2026-11-07 | Initial values (detour limit 1.8, reuse factor 0.4, noise amplitude 0.15) | Generated, uncommitted | Pending | Pending review |
