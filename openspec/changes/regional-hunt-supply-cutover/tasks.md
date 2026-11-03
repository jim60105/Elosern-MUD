# Tasks

All tasks are future implementation work. Follow design.md verbatim for signatures, state shapes, boundaries, prohibited scope and canonical-ID handling. Do not begin without the Batch prerequisites.

## 1. Remove supply creation and single-cell publication caps

- [ ] 1.1 Implement read-only source shapes/validation in definitions and publication callers. Remove provisioning module, runtime helpers and provisioning snapshots after migrating all callers; remove only its owned test/shard entry. Replace catalog per-coordinate assertions in `test_hunt_catalog_content.py` with generic source/reference validation and synthetic quantity-greater-than-cell cases. Extend `test_species_hunt_acceptance.py` with zero-target acceptance and unchanged population state/due/sequence. Check: source-backed quantity10 with cell-capacity3 registers/accepts, no-source fails publication, and no provisioning import or compatibility ensure helper remains.

## 2. Preserve board, binding and truthful habitat guidance

- [ ] 2.1 Update guild availability/refusal callers and map_quest_destinations plus marker projections using the specified destination_kind contract; extend `test_site_clear_out_acceptance.py`, `test_map_quest_destinations.py` and guild acceptance tests with live-shortage, exact bound-set, deadline and post-affinity-write rollback controls. Amend the named data-model design, catalog/tutorial promises and both command docs. Check: empty habitats still yield destination guidance and an active record but no live-monster/entity marker or births; not-due/one-shot sites remain cleared and recovered IDs cannot satisfy old bindings.

## 3. Slice handoff

- [ ] 3.1 Run the focused labels in design.md, changed-logging observability lint, command documentation contract when applicable, `openspec validate regional-hunt-supply-cutover --strict` and `uv run --locked python -m tools.contract_gate`; record actual evidence and the assertion-role/requirement mapping in the named developer document. Check: all required commands exit zero, new test ownership is exact, no retired annotations remain, and no unexecuted check is reported as passed. Do not run CI shard/full-browser or complete evidence verification locally.
