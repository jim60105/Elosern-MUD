# Worker contract

## Authoritative shared contract

Read [the fixed interfaces and caller cutover checklist](../map-core-sparse-geometry/worker-contract.md) before implementing this slice. That file is the single shared contract for this batch; do not copy it into another implementation or infer a second persistence path. It includes typed single-document create/replace/remove effects, expected absence, guarded history inverses, execution-time external-reference freshness and writer-fingerprint watcher reconciliation.

## This slice

Extract neutral frontend projection, geometry and glyph primitives and migrate existing game maps in the same cutover.

Implementation owners: packages/map-view; web/webclient-app/lib/{map_viewport,area_map_view,minimap_projection}.js; AreaMapView/WorldMapView and glyph consumers; pnpm metadata/lock; map unit/component tests

Prerequisites: none.

Required evidence owners: packages/map-view/tests/*.test.js; web/webclient-app/tests/world/{area_map_view,map_drawer,map_lattice_renderer}.test.js; tests/test_map_view_boundary.py (new, invokes actual JS primitive runner for discoverable evidence).

Use this change's design.md, complete spec deltas and ordered tasks.md for its exact behavior and negative cases. Every test must assert the actual consumer effect or unchanged baseline. The shared contract does not authorize generic file mutation, cross-document cascades, extra product surfaces, implementation during proposal creation or omission of any dependent domain/editor acceptance.
