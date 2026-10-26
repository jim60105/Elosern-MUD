# Worker contract

## Authoritative shared contract

Read [the fixed interfaces and caller cutover checklist](../map-core-sparse-geometry/worker-contract.md) before implementing this slice. That file is the single shared contract for this batch; do not copy it into another implementation or infer a second persistence path. It includes typed single-document create/replace/remove effects, expected absence, guarded history inverses, execution-time external-reference freshness and writer-fingerprint watcher reconciliation.

## This slice

Define the complete typed authoring schema, restricted round-trip YAML codec, source discovery and runtime acceptance gates.

Implementation owners: packages/map-core schema/codec/discovery/validation; proposed authoring inspection CLI used on synthetic and converted documents; no game source-format cutover in this slice

Prerequisites: map-core-sparse-geometry.

Required evidence owners: packages/map-core/tests/test_authoring.py, test_yaml_codec.py; tests/test_map_authoring_contract.py.

Use this change's design.md, complete spec deltas and ordered tasks.md for its exact behavior and negative cases. Every test must assert the actual consumer effect or unchanged baseline. The shared contract does not authorize generic file mutation, cross-document cascades, extra product surfaces, implementation during proposal creation or omission of any dependent domain/editor acceptance.
