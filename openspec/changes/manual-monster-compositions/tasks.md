# Tasks

All tasks are future implementation work. Follow design.md verbatim for signatures, state shapes, boundaries, prohibited scope and canonical-ID handling. Do not begin without the Batch prerequisites.

## 1. Cut over site declarations and callers to explicit compositions

- [ ] 1.1 Change MonsterSite signature, validators, existing declarations and all variant_keys/cycling consumers to composition_key. Update `world/lore/tests/test_monster_placement.py`, site definition tests and generic registry-reference tests with synthetic exact-count/mixed/stray cases. Document the new shape and manual exception in the developer document and amend the capability Purpose during implementation; consume the already-required explicit world-seed API without a missing-seed default. Check: no old site variant_keys reader remains, invalid composition/capacity/surface rejects before publication, and current sites preserve their declared owner/lifecycle relations without pinned balance tables.

## 2. Commit and recover full owned manual groups

- [ ] 2.1 Update monster_sites.py population/state/snapshots and identity-based member discovery; extend `world/maps/tests/test_monster_sites.py` and `world/quests/tests/test_site_clear_out_acceptance.py` with live absent members, A+A+B, lawful settlement-buffer placement, manual overpopulation, one-shot/not-due reads, recovered-new-ID binding controls and a failure after first real registration. Check: manual exceptions survive ordinary maintenance, pure reads create nothing, absent living members prevent false clearing, old bindings reject substitute IDs, and DB reload plus live caches restore complete pre-wave state after fault.

## 3. Slice handoff

- [ ] 3.1 Run the focused labels in design.md, changed-logging observability lint, command documentation contract when applicable, `openspec validate manual-monster-compositions --strict` and `uv run --locked python -m tools.contract_gate`; record actual evidence and the assertion-role/requirement mapping in the named developer document. Check: all required commands exit zero, new test ownership is exact, no retired annotations remain, and no unexecuted check is reported as passed. Do not run CI shard/full-browser or complete evidence verification locally.
