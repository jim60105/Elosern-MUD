# Tasks

Implementation budget: 5 hours total. Prerequisites are the exact `depends-on` lines in proposal.md.

## 1. Implement the bounded slice

- [ ] 1.1 Add the frozen six-field registry, real initial entries and canonical node validation; use existing lore registration/sync conventions where appropriate without materializing rooms.
- [ ] 1.2 Validate uniqueness, kind/region constraints, reachability and the single declared spacing rule; preserve the one deep-forest region district.
- [ ] 1.3 Implement read-only lighting from parse_knowledge and exact node membership; document registry authoring and ownership.

## 2. Focused behavioral verification

- [ ] 2.1 Create focused pure tests in proposed `world.lore.tests.test_map_districts` for schema, identity, spacing and invalid fixtures, and run that exact label.
- [ ] 2.2 Create focused `world.rules.tests.test_map_district_lighting` assertions for exact-visit lighting, near misses, no persistent writes and multi-nation forest identity; run only that module.

## 3. Contracts and focused handoff

- [ ] 3.1 Register any new/moved Evennia package test modules in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use synthetic fixtures except explicitly registered production data contracts.
- [ ] 3.2 Obtain canonical requirement IDs through `tools.spec_traceability list` on the current tree and an equivalent merged-spec tree for this delta; attach literal `covers_requirement` annotations to substantive discoverable Python unit/integration/browser tests. Run traceability check with the matching spec tree; never claim a pre-sync root pass covers new deltas.
- [ ] 3.3 Run only the focused labels/files/classes named above, run observability lint if server logging changes, then `uv run --locked python -m tools.contract_gate` and strict validation. Record commands/results and update the existing behavior documentation; no broad suites, CI shard commands, or local full evidence verification.
