# Worker contract

## Authoritative shared contract

Read [the fixed interfaces and caller cutover checklist](../map-core-sparse-geometry/worker-contract.md) before implementing this slice. That file is the single shared contract for this batch; do not copy it into another implementation or infer a second persistence path. It includes typed single-document create/replace/remove effects, expected absence, guarded history inverses, execution-time external-reference freshness and writer-fingerprint watcher reconciliation.

## This slice

Convert every settlement graph, prototype, binding, footprint and entry relationship to discovered YAML with complete game caller migration.

Implementation owners: content/maps/settlements/*.yaml; world/maps/{map_data,altoria_capital,village_ciaran,bootstrap,city_gates,room_art}.py; world/lore/{anchor_placement,anchors,wilderness_entry,sync}.py; typeclasses/exits.py; grid provider/route/knowledge/presenter consumers

Prerequisites: map-qualified-static-references, map-geography-yaml-cutover.

Required evidence owners: world/maps/tests/test_settlement_sources.py (new); test_bootstrap, test_sparse_graph, test_city_movement_cost; world/lore/tests/test_wilderness_entry.py; tests/test_map_settlement_contract.py.

Use this change's design.md, complete spec deltas and ordered tasks.md for its exact behavior and negative cases. Every test must assert the actual consumer effect or unchanged baseline. The shared contract does not authorize generic file mutation, cross-document cascades, extra product surfaces, implementation during proposal creation or omission of any dependent domain/editor acceptance.
