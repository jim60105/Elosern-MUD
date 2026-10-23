# Metric local maps and uniform projection

`project-metric-local-maps` cuts the `local_map` transport and client renderer
over to physical coordinates. The wire payload carries canonical
server-authoritative coordinates; the browser projects them at one uniform
physical scale. The property that matters for play is that unequal distances
stay unequal on screen: two nodes 100 m apart and two nodes 900 m apart draw at
a 1:9 ratio at every zoom, and the ratio never changes per axis.

## Unit and ownership contract

| Layer | Unit | Owner |
| --- | --- | --- |
| Settlement node coordinates | integer metres in the settlement's local frame (`x` east, `y` north) | `world/maps/` (room lifecycle), declared by the settlement graph |
| Wilderness node coordinates | integer one-kilometre cell indices (`0 <= x, y < 2700` once rescaling lands) | `world/maps/wilderness_provider.py` |
| `local_map` payload `x`/`y` | those same integers, unchanged | `web/webclient/presentation/local_map/` |
| Lattice cell in the browser | the smallest positive in-view coordinate delta, one divisor for both axes | `web/static/webclient/js/elosern/local_map.js::layoutNodes` |
| Canvas placement | presentation only (`col`/`row` × pitch) | `web/webclient-app/composables/use-map-lattice-geometry.js` |

`z` stays the logical grid/layer key; it is never physical elevation. Interiors
without coordinates stay coordinate-free connected scenes: their payload keeps
`room:` identities and the radial graph layout, and no metre position is
invented for them.

## Wire envelope

Both validators share one exact envelope and enforce it identically:

- `web/webclient/presentation/local_map/validate.py`: `COORD_MIN = -10_000_000`,
  `COORD_MAX = 10_000_000`.
- `web/static/webclient/js/elosern/protocol/constants.js`:
  `LOCAL_MAP_COORD_MIN`/`LOCAL_MAP_COORD_MAX`, consumed by
  `protocol/panels/local_map.js::requireCoord`.

The envelope is a transport bound, not a rendering bound and not a statement
about any map's extent. A `grid:` identity still resolves against the
registered extent of its own `z_map_key`
(`world/rules/map_knowledge._registered_grid_bounds`), and a `wild:` identity
still resolves against the provider frame; widening one never widens the
other. Non-integer, non-finite, boolean and numeric-string coordinates remain
rejected, so the renderer never receives invented geometry.

The on-demand `area_map` and `world_map` drawer panels reuse the same
coordinate envelope but have their own schemas, frames and bounds. See
[map-panel-protocol.md](map-panel-protocol.md). The `local_map` minimap keeps
its existing 65,536-byte budget.

## Projection

`layoutNodes` is a uniform metric projection, not a rank compression:

1. Take the in-view nodes (`current`, `visible_unvisited`, `visible_visited`).
2. `cell` = the smallest positive pairwise coordinate delta on either axis
   (1 when the set has no positive delta, e.g. a single node).
3. `col = (x - minX) / cell`, `row = (y - minY) / cell`, with
   `cols`/`rows` = the span in cells plus one.

Because one divisor serves both axes, every gap ratio and every compass bearing
is preserved exactly; no axis is equalized independently. A coordinate set with
1 m and 7 km spans therefore yields a large cell count rather than a compressed
rank grid, and the surfaces reach the far part of the drawing through their
viewport: the island renders a current-centred 240-unit window at scale 1 and
the full-map overlay shows the whole drawing through its fitted view (zoom,
drag pan, recentre). Payload coordinates are never rewritten by the projection.

The lattice cell is square on every surface: `MapLattice`'s declared
`colPitch`/`rowPitch` are minimums and the larger one binds both axes, so an
eastward and a northward step of one cell draw the same length. Label and
marker clearance terms divide each pair's need by that pair's own cell
separation, so a pair more than one cell apart does not over-inflate the pitch.

`remembered` nodes stay off the canvas: on coordinate-bearing layers they are
named edge-direction markers derived from the **raw** payload delta, and they
keep the same bearing at any projection scale. Coordinate-free layers keep the
radial graph and its text alternative.

## Verification

```sh
node --test web/static/webclient/js/tests/local_map.test.js \
  web/static/webclient/js/tests/protocol_local_map.test.js

pnpm exec vitest run \
  web/webclient-app/tests/world/local_map.test.js \
  web/webclient-app/tests/overlays/map_overlay.test.js \
  web/webclient-app/tests/world/map_lattice_fidelity.test.js \
  web/webclient-app/tests/world/map_lattice_renderer.test.js \
  web/webclient-app/tests/world/map_lattice_name_fit.test.js \
  web/webclient-app/tests/world/map_lattice_edge_names.test.js

uv run --locked --env-file=<file> evennia test --settings test_settings.py --keepdb \
  web.webclient.presentation.tests.test_local_map
```

The browser acceptance path is
`web/tests/browser/test_browser_local_map_lattice.py`
(`test_metric_projection_keeps_gap_ratio_and_actions`): it injects a metric
payload into the real client and checks the drawn gap ratio, the uniform zoom
and pan, and the adjacent node's move identity.
