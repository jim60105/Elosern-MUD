# Tasks

All tasks are future implementation work. Follow design.md verbatim for signatures, state shapes, boundaries, prohibited scope and canonical-ID handling. Do not begin without the Batch prerequisites.

## 1. Replace prospective facts with actual live projection

- [x] 1.1 Rewrite population_view only, preserving its API and character/NPC support while removing expected-slot and capital dependencies. Update `world/maps/tests/test_wilderness_population_species.py` and `test_wilderness_population.py` view tests for same-label objects, unmaterialized coordinates, stored HP, pending recovery, changed position, dead IDs and repeated read no-mutation. Document the fact contract. Check: zero real members yields zero hostile facts even for a due authored habitat; rename/reload retains each object key without creating rooms or traits.

## 2. Cut over presence consumers and GM inspection

- [x] 2.1 Update the named travel, map/sight and GM read consumers and their focused tests, without changing quest-owned destination shape or introducing hostility admission. Extend `test_travel_events.py`, `test_area_map.py` and GM monster read tests using actual placement. Check: room recycling gives no false hostile transition, a new live ID gives the normal commit-qualified transition, dead/future IDs are absent, and home region/current region are displayed independently with no variant-based ownership guess.

## 3. Slice handoff

- [ ] 3.1 Run the focused labels in design.md, changed-logging observability lint, command documentation contract when applicable, `openspec validate actual-live-population-view --strict` and `uv run --locked python -m tools.contract_gate`; record actual evidence and the assertion-role/requirement mapping in the named developer document. Check: all required commands exit zero, new test ownership is exact, no retired annotations remain, and no unexecuted check is reported as passed. Do not run CI shard/full-browser or complete evidence verification locally.

  Blocked on the archive sync only: every focused label, `openspec validate --strict` and the observability lint pass, and `contract_gate` passes reference-context, test-data, manifests and contracts, but its traceability step reports exactly the two `wilderness-population-view` requirements this delta REMOVES as uncovered (`0 errors`) because the main spec still lists them until the delta is synced. No retired annotation was re-pointed to keep the gate green.
