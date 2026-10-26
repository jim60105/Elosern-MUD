# Worker contract

## Authoritative shared contract

Read [the fixed interfaces and caller cutover checklist](../map-core-sparse-geometry/worker-contract.md) before implementing this slice. That file is the single shared contract for this batch; do not copy it into another implementation or infer a second persistence path. It includes typed single-document create/replace/remove effects, expected absence, guarded history inverses, execution-time external-reference freshness and writer-fingerprint watcher reconciliation.

## This slice

Implement service-owned single-document autosave, overwrite guards and manual-segment undo/redo with real interior-layout operations.

Implementation owners: elosern_map_editor command executor/file writer/history/session endpoints; frontend draft/persistence state; interior layout handler; content/map-editor-layouts; docs/development/map-editor.md

Prerequisites: map-editor-standalone-service.

Required evidence owners: independent test_document_commands.py, test_history.py; tests/test_map_editor_persistence.py; focused layout component/browser tests.

Use this change's design.md, complete spec deltas and ordered tasks.md for its exact behavior and negative cases. Every test must assert the actual consumer effect or unchanged baseline. The shared contract does not authorize generic file mutation, cross-document cascades, extra product surfaces, implementation during proposal creation or omission of any dependent domain/editor acceptance.
