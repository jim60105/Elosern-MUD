# Worker contract

## Authoritative shared contract

Read [the fixed interfaces and caller cutover checklist](../map-core-sparse-geometry/worker-contract.md) before implementing this slice. That file is the single shared contract for this batch; do not copy it into another implementation or infer a second persistence path. It includes typed single-document create/replace/remove effects, expected absence, guarded history inverses, execution-time external-reference freshness and writer-fingerprint watcher reconciliation.

## This slice

Move all permanent interiors and topology to YAML and finish all-world immutable game publication with authoritative validation.

Implementation owners: content/maps/interiors/*.yaml; world/maps/{bootstrap,map_data,room_art}.py and new runtime adapter; world/lore/settlements/{places,places_*,_hosts}.py; world/rules/guild_economy.py; server/conf/at_server_startstop.py; quest/service/art/GM/presenter consumers

Prerequisites: map-district-yaml-cutover, map-partition-core-generation.

Required evidence owners: world/maps/tests/test_interior_sources.py and test_runtime_adoption.py (new); test_bootstrap and test_room_art_metadata; world/rules/tests/test_guild_economy_sync.py, test_service_binding_persistence.py; tests/test_map_runtime_contract.py.

Use this change's design.md, complete spec deltas and ordered tasks.md for its exact behavior and negative cases. Every test must assert the actual consumer effect or unchanged baseline. The shared contract does not authorize generic file mutation, cross-document cascades, extra product surfaces, implementation during proposal creation or omission of any dependent domain/editor acceptance.
