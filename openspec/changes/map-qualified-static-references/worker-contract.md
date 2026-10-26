# Worker contract

## Authoritative shared contract

Read [the fixed interfaces and caller cutover checklist](../map-core-sparse-geometry/worker-contract.md) before implementing this slice. That file is the single shared contract for this batch; do not copy it into another implementation or infer a second persistence path. It includes typed single-document create/replace/remove effects, expected absence, guarded history inverses, execution-time external-reference freshness and writer-fingerprint watcher reconciliation.

## This slice

Replace static coordinate targets with qualified authored references before converting their owning documents.

Implementation owners: world/maps/{city_gates,room_art,bootstrap}.py; world/lore/{anchor_placement,wilderness_entry,map_districts}.py; world/lore/settlements/places*.py and _hosts.py; static quest/service declarations; web/webclient/presentation/map_quest_destinations.py; scene-address/locator adapters

Prerequisites: map-core-sparse-geometry, npc-title-authoring-removal.

Required evidence owners: world/maps/tests/test_static_map_references.py (new); existing test_bootstrap, test_room_art_metadata; world/rules/tests/test_map_knowledge.py and map quest destination tests; synthetic factories.

Use this change's design.md, complete spec deltas and ordered tasks.md for its exact behavior and negative cases. Every test must assert the actual consumer effect or unchanged baseline. The shared contract does not authorize generic file mutation, cross-document cascades, extra product surfaces, implementation during proposal creation or omission of any dependent domain/editor acceptance.
