# Worker contract

## Authoritative shared contract

Read [the fixed interfaces and caller cutover checklist](../map-core-sparse-geometry/worker-contract.md) before implementing this slice. That file is the single shared contract for this batch; do not copy it into another implementation or infer a second persistence path. It includes typed single-document create/replace/remove effects, expected absence, guarded history inverses, execution-time external-reference freshness and writer-fingerprint watcher reconciliation.

## This slice

Implement coordinate-free permanent interior room/connection editing and separately persisted layout controls.

Implementation owners: frontend interior room/connection/layout tools; service interior handlers; content/maps/interiors and content/map-editor-layouts; existing move_interior_layout route

Prerequisites: map-editor-interaction-shell.

Required evidence owners: tests/test_map_editor_interiors.py (new); interior component tests; real browser standalone/service-interior/layout workflows.

Use this change's design.md, complete spec deltas and ordered tasks.md for its exact behavior and negative cases. Every test must assert the actual consumer effect or unchanged baseline. The shared contract does not authorize generic file mutation, cross-document cascades, extra product surfaces, implementation during proposal creation or omission of any dependent domain/editor acceptance.
