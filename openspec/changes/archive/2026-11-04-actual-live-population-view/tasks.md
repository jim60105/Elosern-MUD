# Tasks

All tasks are future implementation work. Follow design.md verbatim for signatures, state shapes, boundaries, prohibited scope and canonical-ID handling. Do not begin without the Batch prerequisites.

## 1. Replace prospective facts with actual live projection

- [x] 1.1 Rewrite population_view only, preserving its API and character/NPC support while removing expected-slot and capital dependencies. Update `world/maps/tests/test_wilderness_population_species.py` and `test_wilderness_population.py` view tests for same-label objects, unmaterialized coordinates, stored HP, pending recovery, changed position, dead IDs and repeated read no-mutation. Document the fact contract. Check: zero real members yields zero hostile facts even for a due authored habitat; rename/reload retains each object key without creating rooms or traits.

## 2. Cut over presence consumers and GM inspection

- [x] 2.1 Update the named travel, map/sight and GM read consumers and their focused tests, without changing quest-owned destination shape or introducing hostility admission. Extend `test_travel_events.py`, `test_area_map.py` and GM monster read tests using actual placement. Check: room recycling gives no false hostile transition, a new live ID gives the normal commit-qualified transition, dead/future IDs are absent, and home region/current region are displayed independently with no variant-based ownership guess.

## 3. Slice handoff

- [x] 3.1 Run the focused labels in design.md, changed-logging observability lint, command documentation contract when applicable, `openspec validate actual-live-population-view --strict` and `uv run --locked python -m tools.contract_gate`; record actual evidence and the assertion-role/requirement mapping in the named developer document. Check: all required commands exit zero, new test ownership is exact, no retired annotations remain, and no unexecuted check is reported as passed. Do not run CI shard/full-browser or complete evidence verification locally.

  Evidence is recorded in `docs/development/regional-monster-population.md`
  ("Actual live population view"): the focused labels (`WildernessPopulationViewTests`
  10, `AmbientSpeciesReconciliationTests` 12, `HuntProvisioningTests` 11,
  `test_travel_events` 35, `WildernessAreaTests` 15 with 1 skip,
  `test_reader_monsters` 12, `StateApiListFilterTests` 2), the observability
  lint (`violations=0`) and `openspec validate --strict` all pass. Because this
  delta uses `## REMOVED Requirements`, the checkout's traceability gate
  necessarily reports the two removed requirements as uncovered (`0 errors`)
  until the archive sync; per `docs/development/spec-test-traceability.md` and
  the `2026-10-31-retire-light-sword-style` precedent, the pre-sync evidence is
  the equivalent spec tree outside Git (main specs + this delta, all test
  sources copied, new tests mounted to the tool-generated IDs):
  `uv run --locked python -m tools.spec_traceability --repo-root <equivalent-tree> check`
  → `2702 requirements, 12332 associations, 2702 covered, 0 uncovered, 0 errors`.
  The generated IDs (`wilderness-population-view::population-reads-report-actual-living-registrations`,
  `…::observation-identity-belongs-to-persistent-individuals`) are mounted at
  sync, not in the checkout; no retired annotation was re-pointed. The temporary
  tree was deleted and never committed.
