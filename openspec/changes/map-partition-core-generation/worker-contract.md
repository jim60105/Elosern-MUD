# Worker contract

## Authoritative shared contract

Read [the fixed interfaces and caller cutover checklist](../map-core-sparse-geometry/worker-contract.md) before implementing this slice. That file is the single shared contract for this batch; do not copy it into another implementation or infer a second persistence path. It includes typed single-document create/replace/remove effects, expected absence, guarded history inverses, execution-time external-reference freshness and writer-fingerprint watcher reconciliation.

## This slice

Extract actual snapshot-to-partition input assembly and the existing generation algorithm into an optional independent core extra.

Implementation owners: packages/map-core generation extra and lightweight partition codec/freshness; tools/map_district_partition.py; world/maps/district_partition.py game adapter; world/maps/data/district_partition.json

Prerequisites: map-district-yaml-cutover.

Required evidence owners: packages/map-core/tests/test_partition.py; world/maps/tests/test_map_district_partition.py; tests/test_map_partition_independence.py (new).

Use this change's design.md, complete spec deltas and ordered tasks.md for its exact behavior and negative cases. Every test must assert the actual consumer effect or unchanged baseline. The shared contract does not authorize generic file mutation, cross-document cascades, extra product surfaces, implementation during proposal creation or omission of any dependent domain/editor acceptance.
