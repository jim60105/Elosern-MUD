# Worker contract

## Authoritative shared contract

Read [the fixed interfaces and caller cutover checklist](../map-core-sparse-geometry/worker-contract.md) before implementing this slice. That file is the single shared contract for this batch; do not copy it into another implementation or infer a second persistence path. It includes typed single-document create/replace/remove effects, expected absence, guarded history inverses, execution-time external-reference freshness and writer-fingerprint watcher reconciliation.

## This slice

Prove the complete independent editor and preserved game behavior through real browser/file/game consumer acceptance without inventing new behavior.

Implementation owners: proposed web/tests/browser/test_map_editor_workflows.py and test_map_editor_accessibility.py; tests/test_map_editor_independent_environment.py; map runtime integration tests; CI/package evidence entry points; docs/development/map-editor.md and docs/design/map-editor-review.md

Prerequisites: map-editor-partition-jobs.

Required evidence owners: real standalone service/browser and filesystem paths; existing game test_bootstrap/runtime_adoption/knowledge; focused local class then contract gate; full evidence in CI only.

Use this change's design.md, complete spec deltas and ordered tasks.md for its exact behavior and negative cases. Every test must assert the actual consumer effect or unchanged baseline. The shared contract does not authorize generic file mutation, cross-document cascades, extra product surfaces, implementation during proposal creation or omission of any dependent domain/editor acceptance.
