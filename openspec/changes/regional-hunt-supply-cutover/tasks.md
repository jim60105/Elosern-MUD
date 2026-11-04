# Tasks

All tasks are future implementation work. Follow design.md verbatim for signatures, state shapes, boundaries, prohibited scope and canonical-ID handling. Do not begin without the Batch prerequisites.

## 1. Remove supply creation and single-cell publication caps

- [x] 1.1 Implement read-only source shapes/validation in definitions and publication callers. Remove provisioning module, runtime helpers and provisioning snapshots after migrating all callers; remove only its owned test/shard entry. Replace catalog per-coordinate assertions in `test_hunt_catalog_content.py` with generic source/reference validation and synthetic quantity-greater-than-cell cases. Extend `test_species_hunt_acceptance.py` with zero-target acceptance and unchanged population state/due/sequence. Check: source-backed quantity10 with cell-capacity3 registers/accepts, no-source fails publication, and no provisioning import or compatibility ensure helper remains.

  Evidence: `world.maps.monster_provisioning` and its test/shard entry are
  deleted; no caller or helper remains. `test_species_hunt_acceptance` accepts a
  quantity-10 hunt against a cell-capacity-3 zone with no individuals, and
  asserts `regional_population`, seed, coordinate, site and Monster surfaces are
  unchanged; an unsourced species fails publication. Focused runs are recorded
  in `docs/development/regional-monster-population.md`.

## 2. Preserve board, binding and truthful habitat guidance

- [x] 2.1 Update guild availability/refusal callers and map_quest_destinations plus marker projections using the specified destination_kind contract; extend `test_site_clear_out_acceptance.py`, `test_map_quest_destinations.py` and guild acceptance tests with live-shortage, exact bound-set, deadline and post-affinity-write rollback controls. Amend the named data-model design, catalog/tutorial promises and both command docs. Check: empty habitats still yield destination guidance and an active record but no live-monster/entity marker or births; not-due/one-shot sites remain cleared and recovered IDs cannot satisfy old bindings.

  Evidence: `guild list`/availability, `map_quest_destinations` and the area
  marker projection use `destination_kind`; a habitat marker is a bearing with
  no entity field; an owner-backed acceptance-path test resolves guidance from
  real source and birth geometry with zero births. Board live-shortage and a
  witnessed post-affinity-write rollback live in `test_species_hunt_acceptance`;
  the existing exact-bound-set, deadline, one-shot/not-due-cleared and
  recovered-ID controls in `test_site_clear_out_acceptance.py` are unchanged
  (that file's setUp is concurrently owned by the sibling recovery change).

## 3. Slice handoff

- [x] 3.1 Run the focused labels in design.md, changed-logging observability lint, command documentation contract when applicable, `openspec validate regional-hunt-supply-cutover --strict` and `uv run --locked python -m tools.contract_gate`; record actual evidence and the assertion-role/requirement mapping in the named developer document. Check: all required commands exit zero, new test ownership is exact, no retired annotations remain, and no unexecuted check is reported as passed. Do not run CI shard/full-browser or complete evidence verification locally.

  Evidence is recorded in `docs/development/regional-monster-population.md`
  ("Regional hunt supply cutover"). All focused test labels, the observability
  lint (`violations=0`), the test-data lint, the command-documentation contract,
  `openspec validate --strict`, the shard manifests and the contract suite pass.
  Because this delta uses `## REMOVED Requirements`, the checkout's traceability
  gate necessarily reports exactly one uncovered identifier with 0 errors
  (`quest-blueprint::published-regional-species-hunts-are-legally-provisionable-in-their-authored-region`)
  until the archive sync; no retired annotation was re-pointed and no canonical
  ID was fabricated. No test module was added, so `.github/evennia-shards.json`
  only lost the deleted provisioning label.
