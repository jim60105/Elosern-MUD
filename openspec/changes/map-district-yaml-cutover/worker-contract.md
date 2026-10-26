# Worker contract

## Authoritative shared contract

Read [the fixed interfaces and caller cutover checklist](../map-core-sparse-geometry/worker-contract.md) before implementing this slice. That file is the single shared contract for this batch; do not copy it into another implementation or infer a second persistence path. It includes typed single-document create/replace/remove effects, expected absence, guarded history inverses, execution-time external-reference freshness and writer-fingerprint watcher reconciliation.

## This slice

Move all district declarations and stable landmarks to one YAML authority while retaining derived boundary and lighting behavior.

Implementation owners: content/maps/districts.yaml; world/lore/map_districts.py; world/rules/map_district_lighting.py; web map presenters; tools/map_district_partition.py input adapter; docs/development/continental-geography.md

Prerequisites: map-settlement-yaml-cutover.

Required evidence owners: world/lore/tests/test_map_district_content.py; world/maps/tests/test_map_district_partition.py; tests/test_map_district_sources.py (new).

Use this change's design.md, complete spec deltas and ordered tasks.md for its exact behavior and negative cases. Every test must assert the actual consumer effect or unchanged baseline. The shared contract does not authorize generic file mutation, cross-document cascades, extra product surfaces, implementation during proposal creation or omission of any dependent domain/editor acceptance.
