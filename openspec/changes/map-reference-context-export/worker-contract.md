# Worker contract

## Authoritative shared contract

Read [the fixed interfaces and caller cutover checklist](../map-core-sparse-geometry/worker-contract.md) before implementing this slice. That file is the single shared contract for this batch; do not copy it into another implementation or infer a second persistence path. It includes typed single-document create/replace/remove effects, expected absence, guarded history inverses, execution-time external-reference freshness and writer-fingerprint watcher reconciliation.

## This slice

Export a deterministic authoritative static-reference closure and support independent freshness checking for safe editor deletion.

Implementation owners: proposed tools/map_reference_context.py; content/map-reference-context.json; packages/map-core reference-context codec/checker; authoritative quest/service/scene/art/lore declarations; CI planning for check integration; docs/development/map-editor.md

Prerequisites: map-interior-runtime-cutover.

Required evidence owners: tests/test_map_reference_context.py (new); game static export integration test with database access made fatal; synthetic source closure mutation tests.

Use this change's design.md, complete spec deltas and ordered tasks.md for its exact behavior and negative cases. Every test must assert the actual consumer effect or unchanged baseline. The shared contract does not authorize generic file mutation, cross-document cascades, extra product surfaces, implementation during proposal creation or omission of any dependent domain/editor acceptance.
