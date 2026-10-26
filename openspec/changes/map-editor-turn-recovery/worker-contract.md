# Worker contract

## Authoritative shared contract

Read [the fixed interfaces and caller cutover checklist](../map-core-sparse-geometry/worker-contract.md) before implementing this slice. That file is the single shared contract for this batch; do not copy it into another implementation or infer a second persistence path. It includes typed single-document create/replace/remove effects, expected absence, guarded history inverses, execution-time external-reference freshness and writer-fingerprint watcher reconciliation.

## This slice

Implement external AI turn-taking, directory watching, stale preview adoption and explicit reconnect/restart recovery.

Implementation owners: elosern_map_editor session state machine/watch coordinator/SSE; frontend connection/preview/turn state and handoff dialogs; all mutation guards; independent real-filesystem tests

Prerequisites: map-editor-document-commands.

Required evidence owners: tests/test_map_editor_turns.py, test_map_editor_watching.py (new discoverable wrappers); standalone service tests; focused standalone browser recovery class.

Use this change's design.md, complete spec deltas and ordered tasks.md for its exact behavior and negative cases. Every test must assert the actual consumer effect or unchanged baseline. The shared contract does not authorize generic file mutation, cross-document cascades, extra product surfaces, implementation during proposal creation or omission of any dependent domain/editor acceptance.
