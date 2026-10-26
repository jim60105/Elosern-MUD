# Worker contract

## Authoritative shared contract

Read [the fixed interfaces and caller cutover checklist](../map-core-sparse-geometry/worker-contract.md) before implementing this slice. That file is the single shared contract for this batch; do not copy it into another implementation or infer a second persistence path. It includes typed single-document create/replace/remove effects, expected absence, guarded history inverses, execution-time external-reference freshness and writer-fingerprint watcher reconciliation.

## This slice

Install and run the independent local editor service and browser workspace with bounded authenticated domain APIs.

Implementation owners: new tools/map-editor/{pyproject.toml,uv.lock,elosern_map_editor,frontend}; packages/map-view local dependency; frontend pnpm lock; launch/docs/development/map-editor.md; tests/test_map_editor_service.py

Prerequisites: map-interior-runtime-cutover, map-reference-context-export, map-view-shared-foundations.

Required evidence owners: independent service tests plus tests/test_map_editor_service.py; proposed web/tests/browser/test_map_editor_standalone.py uses a real standalone server with no game/database.

Use this change's design.md, complete spec deltas and ordered tasks.md for its exact behavior and negative cases. Every test must assert the actual consumer effect or unchanged baseline. The shared contract does not authorize generic file mutation, cross-document cascades, extra product surfaces, implementation during proposal creation or omission of any dependent domain/editor acceptance.
