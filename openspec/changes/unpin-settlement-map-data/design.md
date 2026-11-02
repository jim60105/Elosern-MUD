# Design

## Context

See proposal.md (Why). Facts the rewrites rely on:

- `world.maps.map_data.current()` returns the published `SettlementSnapshot`.
  - `.settlements` maps a map id to a `SettlementDocument`.
  - `.graphs` maps a map id to a `SparseSettlementGraph`.
- `SettlementDocument` (`packages/map-core/elosern_map_core/documents.py`) exposes:
  - `location_ref`;
  - `nodes`: node id → `NodeDeclaration`, with `.node_id`, `.coordinate` (local metres `(x_m, y_m)`), `.prototype_parent`, `.key`, `.desc` and `.anchor_key`;
  - `roads`: a tuple of `RoadDeclaration`, each with `.source`, `.destination`, `.direction` and `.bends`, where every bend has `.x_m` and `.y_m`;
  - `wilderness_entry`: `None`, or `.shape`, `.offset` `(dx, dy)` and `.gates`, where each gate has `.return_direction` and `.destination_node`;
  - `city_gate`: `None`, or an object with `.node`;
  - `anchor_node` and `local_anchor_m`.
- `world.maps.geography.current().locations.locations[<id>].cell` is the authored location cell `(cell_x, cell_y)`.
- A spawned `GridRoom` has `xyz == (x_m, y_m, map_id)`, and its `sparse_node_id` attribute is the authored node id.
- The movement-cost-charging spec fixes the healthy settlement walking speed at 1.25 m/s. The charged duration of a straight or bent road is `ceil(polyline_metres / 1.25)` seconds, rounded upward once.
- The world position of a node is `(1000*cell_x + 500 + x_m - anchor_x_m, 1000*cell_y + 500 + y_m - anchor_y_m)`. This is the continental-geography "Coordinate frames have explicit physical units" scenario.

## Goals / Non-Goals

**Goals:**
- After this change, the following two edits need no spec or test change:
  - adding a valid settlement document for an unbuilt location;
  - moving Altoria nodes, or adding Altoria nodes and roads. This assumes the anchor stays `central_plaza`, the city gate stays `south_gate`, and the wilderness gates with return directions `n` and `w` keep targeting `south_gate` and `east_gate`.

**Non-Goals:**
- Unpinning Ciaran data. No planned change touches `village_ciaran`.
- Unpinning browser tests. Those run only in CI. The canary cannot run them, see Risks.
- Changing the residual assumptions in D4.

## Decisions

### D1. Expected values come from the documents, read through a different path than the one under test

Each rewritten assertion reads its expected value from `current().settlements[...]` or from the geography locations. The system under test is a composed registry (`ANCHOR_PLACEMENT_REGISTRY`, `WILDERNESS_ENTRY_REGISTRY`, spawned rooms, the clock). Comparing the composed view with the authored declaration still detects the defects these tests exist for:

- a lost node or road;
- a wrong frame transform;
- a mask placed at the wrong origin.

They no longer fail when the data changes. We rejected the alternative of moving every case onto synthetic fixtures, because it would rewrite consumer-wiring tests into different tests.

### D2. Durations are checked by a bracketing relation, not a copied formula

AGENTS.md forbids getting the expected value by copying the calculator's formula. Each of the three duration pins therefore becomes a relation check on the charged tick delta `d` (`after - before`):

- 724 s, south gate to avenue;
- 811 s, east-gate approach;
- 724 s again, the roundtrip copy.

```python
def _polyline_metres(points):
    """Authored length only; the charged seconds come from the clock, never from here."""
    import math

    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))

def assertChargedFor(self, delta, metres):     # a TestCase helper method
    """The spec's healthy settlement speed is 1.25 m/s with one upward rounding."""
    self.assertGreater(delta, 0)
    self.assertLess((delta - 1) * 1.25, metres)
    self.assertLessEqual(metres, delta * 1.25)
```

This detects a wrong road or a wrong length, because the bracket is only 1.25 m wide. It also detects a flat connector cost; keep the existing `assertNotEqual(delta, MOVE)`. The synthetic movement-cost-charging tests already establish the exact arithmetic.

Each test module defines these helpers itself. It must never import or call anything from `world.rules.travel_cost`, `world.rules.movement` or `elosern_map_core.sparse`. The input `points` are local metres read from the document: source node, then each bend `(b.x_m, b.y_m)`, then the destination node. For the gate approach the inputs are world metres, computed with the Context formula.

### D3. A canary proves completeness. It is never committed

The pins listed in the Impact section came from a grep, which may have missed some. The canary perturbs the data the way the later changes will:

1. Add a new map file `content/maps/settlements/town_scarp.yaml`. Its exact YAML is in tasks.md. It was validated against a scratch copy of the workspace: only `stale_partition` is reported.
2. In `capital_altoria.yaml`:
   - change `south_gate.x_m` from `3050` to `3090`;
   - change `east_gate.x_m` from `6500` to `6540`;
   - add the node `canary_lane` at `(3620, 2960)`;
   - add the road pair `central_plaza → canary_lane` (`ne`) and `canary_lane → central_plaza` (`sw`). The outgoing directions `central_plaza` already uses are `n`, `e`, `s` and `w`, so `ne` is free;
   - append two wilderness gates, `return_direction: s → palace_forecourt` and `return_direction: e → craft_alley`.
3. In `locations.yaml`, change `capital_altoria.cell_x` from `850` to `851`. This moves the mask origin, the anchor cell and every approach cell.

   The combined canary (steps 1–3) was validated on a scratch copy of the workspace. The only diagnostic reported was `stale_partition`.
4. Regenerate the partition. The game refuses a stale one, so without this step every test fails.

Run the module list in tasks.md, then restore with `git checkout` and `rm`. A module that still fails under the canary but passes on clean data has a remaining pin. Fix it with the D1/D2 recipes and the same requirement IDs.

### D4. Residual data assumptions accepted for this batch

- Tests still find the capital's gates with `gate_for("n")` and `gate_for("w")`. `altoria-capital-river-rework` keeps both gates, so these lookups keep working. Assertions that a return direction is *absent* are rewritten to derive the absent set from the document (task 3.3).
- `central_plaza` remains the capital's anchor node.
- Ciaran node keys and its 394 s duration are untouched.
- The `sample-city-altoria` scenario titles still say "South Gate" and "East Gate". Those node ids are permanent.

Removing these would mean rewriting about 40 more modules. That is deferred to a later change; this change keeps those assumptions.

## Risks / Trade-offs

- [The canary run is long: about 60 Evennia modules] → Run one module per command, which the guard requires. Capture each log once to the scratchpad and do not rerun just to read output. A module that the guard rejects for more than 100 tests is run class by class.
- [Browser tests (`web/tests/browser/*`) may pin Altoria coordinates or keys, and they cannot run locally] → `test_browser_scene_transitions.py` uses synthetic `grid:capital_altoria:2:0`-style payloads with a non-Altoria key (鐘樓前庭). The grep found no shipped-coordinate pin in the browser tests. Record this as a CI-only residual risk in the final report.
- [A rewritten assertion becomes tautological] → Every rewrite compares a *composed or spawned* value with the *authored* value. A rewrite never compares a document with itself.

## Migration Plan

None: tests and specs only.
