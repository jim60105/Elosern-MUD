# Worker contract

## Authoritative shared contract

Read [the fixed interfaces and caller cutover checklist](../map-core-sparse-geometry/worker-contract.md) before implementing this slice. That file is the single shared contract for this batch; do not copy it into another implementation or infer a second persistence path. It includes typed single-document create/replace/remove effects, expected absence, guarded history inverses, execution-time external-reference freshness and writer-fingerprint watcher reconciliation.

## This slice

Implement complete cross-layer entrance editing, navigation and reference-safe deletion from a single owning relationship.

Implementation owners: frontend qualified selector/entrance inspectors/cross-map navigation; service settlement/interior relationship handlers; existing core reference rules; no new persistent game writer

Prerequisites: map-editor-continent-tools, map-editor-settlement-tools, map-editor-interior-tools.

Required evidence owners: tests/test_map_editor_relationships.py (new); relationship component tests; real browser cross-map navigation/edit/deletion cases.

Use this change's design.md, complete spec deltas and ordered tasks.md for its exact behavior and negative cases. Every test must assert the actual consumer effect or unchanged baseline. The shared contract does not authorize generic file mutation, cross-document cascades, extra product surfaces, implementation during proposal creation or omission of any dependent domain/editor acceptance.
