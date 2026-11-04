# Tasks

All tasks are future implementation work. Follow design.md verbatim for signatures, state shapes, boundaries, prohibited scope and canonical-ID handling. Do not begin without the Batch prerequisites.

## 1. Implement counts and seeded complete-wave planning

- [x] 1.1 Create regional_population.py using the exact public shapes above and synthetic tests in `world/maps/tests/test_regional_population.py`; register that module once. Cover local geometry versus eligible area, manual/site/quest visitors, detached/unlocated home owners, bool/state errors, duplicate registration deduplication, complete mixed outcomes, both upper bounds, per-cell/wave fitting and no legal space. Document ownership and selection inputs. Check: a five-member group consumes five units, departures free no home headroom, manual excess creates no automatic individual and no foreign resource changes.

## 2. Implement constrained initialization and atomic commits

- [x] 2.1 Implement initialization and commit plus snapshot/restore integration in the same owner, using the real species constructor. Add fault injection after first actual construction, coordinate write, room attachment and final state write. Check: DB reload and live caches equal baseline, no partial mixed group or on_commit success remains, retry has the same variant/count/cell plan, valid members keep IDs/resources after room recycling/reload, and initialization runs once.

- [x] 2.2 Establish the explicit persisted world-seed initializer/read API in design.md and fresh-script bootstrap before site sampling; migrate GM and wilderness quest construction to register_explicit_individual without enabling ordinary births. Extend `world/maps/tests/test_gm.py` and `world/quests/tests/test_permanent_occupants.py`, and document the explicit incompatible-save refusal. Check: absent-seed reads refuse, a newly provisioned script saves its supplied seed once, manual creation is visible/countable after room recycle/reload, and a post-registration fault restores all surfaces.

## 3. Slice handoff

- [x] 3.1 Run the focused labels in design.md, changed-logging observability lint, command documentation contract when applicable, `openspec validate regional-population-owner --strict` and `uv run --locked python -m tools.contract_gate`; record actual evidence and the assertion-role/requirement mapping in the named developer document. Check: all required commands exit zero, new test ownership is exact, no retired annotations remain, and no unexecuted check is reported as passed. Do not run CI shard/full-browser or complete evidence verification locally.
