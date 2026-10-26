# Worker contract

## Authoritative shared contract

Read [the fixed interfaces and caller cutover checklist](../map-core-sparse-geometry/worker-contract.md) before implementing this slice. That file is the single shared contract for this batch; do not copy it into another implementation or infer a second persistence path. It includes typed single-document create/replace/remove effects, expected absence, guarded history inverses, execution-time external-reference freshness and writer-fingerprint watcher reconciliation.

## This slice

Run explicit partition jobs outside the request loop with cancellation, mutation exclusion and fingerprint-guarded output publication.

Implementation owners: editor background job runner/status routes and partition frontend controls; editor uv generation extra; existing session mutation guard and artifact writer

Prerequisites: map-partition-core-generation, map-editor-entrance-tools.

Required evidence owners: tests/test_map_editor_generation.py (new); independent job tests with real small generation inputs; focused browser partition state/cancel/stale case.

Use this change's design.md, complete spec deltas and ordered tasks.md for its exact behavior and negative cases. Every test must assert the actual consumer effect or unchanged baseline. The shared contract does not authorize generic file mutation, cross-document cascades, extra product surfaces, implementation during proposal creation or omission of any dependent domain/editor acceptance.
