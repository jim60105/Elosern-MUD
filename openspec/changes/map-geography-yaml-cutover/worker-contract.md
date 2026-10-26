# Worker contract

## Authoritative shared contract

Read [the fixed interfaces and caller cutover checklist](../map-core-sparse-geometry/worker-contract.md) before implementing this slice. That file is the single shared contract for this batch; do not copy it into another implementation or infer a second persistence path. It includes typed single-document create/replace/remove effects, expected absence, guarded history inverses, execution-time external-reference freshness and writer-fingerprint watcher reconciliation.

## This slice

Move continent declarations and all geographic locations to YAML, retaining non-map lore ownership and deterministic game behavior.

Implementation owners: content/maps/{continent,locations}.yaml; world/lore/{wilderness_regions,anchors,__init__,sync}.py; world/maps/wilderness_provider.py; continent/map/quest presenters; source contracts; docs/development/continental-geography.md

Prerequisites: map-core-authoring-documents.

Required evidence owners: tests/test_map_geographic_sources.py (new); existing world.lore.tests.test_wilderness_regions, test_anchors, test_anchor_placement; world.maps terrain/provider tests and real geography consumer smoke.

Use this change's design.md, complete spec deltas and ordered tasks.md for its exact behavior and negative cases. Every test must assert the actual consumer effect or unchanged baseline. The shared contract does not authorize generic file mutation, cross-document cascades, extra product surfaces, implementation during proposal creation or omission of any dependent domain/editor acceptance.
