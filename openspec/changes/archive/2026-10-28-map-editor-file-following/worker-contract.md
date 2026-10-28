# Worker contract

## Authoritative shared contract

Read [the fixed interfaces and caller cutover checklist](../map-core-sparse-geometry/worker-contract.md) before implementing this slice. That file is the single shared contract for this batch; do not copy it into another implementation or infer a second persistence path. It includes typed single-document create/replace/remove effects, expected absence, guarded history inverses, execution-time external-reference freshness and writer-fingerprint watcher reconciliation.

## This slice

Implement continuous workspace file following: directory watching, own-write recognition, automatic adoption of loadable external changes, stale preview retention and reconnect/restart recovery, with no explicit AI handoff.

Implementation owners: elosern_map_editor watch coordinator/write-pause state/SSE; frontend connection/preview state, priority banner conditions and draft-held adoption; all mutation guards; independent real-filesystem tests

Prerequisites: map-editor-document-commands.

Required evidence owners: tests/test_map_editor_file_following.py, test_map_editor_watching.py (new discoverable wrappers); standalone service tests; focused standalone browser recovery class.

Use this change's design.md, complete spec deltas and ordered tasks.md for its exact behavior and negative cases. Every test must assert the actual consumer effect or unchanged baseline. The shared contract does not authorize generic file mutation, cross-document cascades, extra product surfaces, implementation during proposal creation or omission of any dependent domain/editor acceptance.
