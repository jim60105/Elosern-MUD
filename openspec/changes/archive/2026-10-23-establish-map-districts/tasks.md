# Tasks

Implementation budget: 5 hours total. Prerequisites are the exact `depends-on` lines in proposal.md.

## 1. Implement the bounded slice

- [x] 1.1 Add the frozen six-field registry, real initial entries and canonical node validation; use existing lore registration/sync conventions where appropriate without materializing rooms.
- [x] 1.2 Validate uniqueness, kind/region constraints, reachability and the single declared spacing rule; preserve the one deep-forest region district.
- [x] 1.3 Implement read-only lighting from parse_knowledge and exact node membership; document registry authoring and ownership.

## 2. Focused behavioral verification

- [x] 2.1 Create focused pure tests in proposed `world.lore.tests.test_map_districts` for schema, identity, spacing and invalid fixtures, and run that exact label.
- [x] 2.2 Create focused `world.rules.tests.test_map_district_lighting` assertions for exact-visit lighting, near misses, no persistent writes and multi-nation forest identity; run only that module.

## 3. Contracts and focused handoff

- [x] 3.1 Register any new/moved Evennia package test modules in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use synthetic fixtures except explicitly registered production data contracts.
- [x] 3.2 Copy the complete current implementation/tests/manifests/tooling into a disposable ordinary directory; merge prerequisite/current deltas into its copied main specs. Obtain canonical IDs with `tools.spec_traceability --repo-root <equivalent-root> list`, and retain literal intended `covers_requirement` annotations in implementation tests. Run `check` with that equivalent root and the copied contract gate from that directory before sync; the unsynced real-root gate is not an acceptance gate for new IDs.
- [x] 3.3 Run only the focused labels/files/classes named above and observability lint if logging changes; run strict validation and the equivalent-tree gate before handoff, then normal root `tools.spec_traceability check` and `tools.contract_gate` after sync. Record commands/results and existing-doc updates; no broad suites, CI shard commands or local full evidence verification.

## Verification record

- Focused Evennia labels (`--settings test_settings.py --keepdb`): `world.lore.tests.test_map_districts`
  (7 OK); `world.lore.tests.test_map_district_content` with `world.rules.tests.test_map_district_lighting`
  (13 OK); `world.lore.tests.test_registry_index_contract` (13 OK with the new `map_districts` index entry).
- `tools.test_data_lint check` and `tools.observability_lint check`: 0 violations; no logging path changed.
- Equivalent root (an ordinary copy with `openspec/specs/map-districts/spec.md` merged from the delta):
  `spec_traceability --repo-root <eq> list` gave the two `map-districts::` IDs, `check` reported 0 errors,
  and the copied `tools.contract_gate` passed. Before sync the root `check` reports only the expected
  `unknown-requirement-id` for these two IDs; the post-sync root check and contract gate run at archive.
- `openspec validate establish-map-districts --strict`: valid.
- Docs: `docs/development/continental-geography.md` gains a "Map districts" section.
