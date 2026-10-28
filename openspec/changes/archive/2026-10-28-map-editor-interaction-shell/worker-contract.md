# Worker contract

## Authoritative shared contract

Read [the fixed interfaces and caller cutover checklist](../map-core-sparse-geometry/worker-contract.md) before implementing this slice. That file is the single shared contract for this batch; do not copy it into another implementation or infer a second persistence path. It includes typed single-document create/replace/remove effects, expected absence, guarded history inverses, execution-time external-reference freshness and writer-fingerprint watcher reconciliation.

## This slice

Deliver the complete accessible workspace navigation, inspection, diagnostics and copy-only context surfaces implementing the approved frontend design.

Implementation owners: editor frontend workspace/navigation/inspection/diagnostics/clipboard/focus modules; docs/design/map-editor-review.md (per-scenario fidelity review of the approved design); no game shell imports

Prerequisites: map-editor-file-following.

Required evidence owners: editor frontend tests for workspace/search/diagnostics/context/focus; proposed web/tests/browser/test_map_editor_accessibility.py for real keyboard/viewport/zoom behavior and traceability.

Use this change's design.md, complete spec deltas and ordered tasks.md for its exact behavior and negative cases. Every test must assert the actual consumer effect or unchanged baseline. The shared contract does not authorize generic file mutation, cross-document cascades, extra product surfaces, implementation during proposal creation or omission of any dependent domain/editor acceptance.
