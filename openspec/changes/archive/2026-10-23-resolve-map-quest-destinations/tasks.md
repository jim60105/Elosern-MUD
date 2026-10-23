# Tasks

Implementation budget: 5 hours total. Prerequisites are the exact `depends-on` lines in proposal.md.

## 1. Implement the bounded slice

- [x] 1.1 Add a read-only shared server resolver for accepted commissions using normalized locator/runtime sources, returning separate local identity and world position.
- [x] 1.2 Handle ANCHOR, GRID, region species hunts and authored monster sites; implement deterministic nearest-region ties against amended geography and no fabricated fallback.
- [x] 1.3 Document the supported destination families and the server-only precision boundary.

## 2. Focused behavioral verification

- [x] 2.1 Add proposed `web.webclient.presentation.tests.test_map_quest_destinations` with synthetic locator/site/region fixtures, independently known nearest/tie outcomes, all four families and no-state-write assertions; run only that label.
- [x] 2.2 Add a focused consumer regression showing a GRID destination retains local identity while its world location uses the settlement anchor; assert unsupported locators do not create markers.

## 3. Contracts and focused handoff

- [x] 3.1 Register any new/moved Evennia package test modules in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use synthetic fixtures except explicitly registered production data contracts.
- [x] 3.2 Copy the complete current implementation/tests/manifests/tooling into a disposable ordinary directory; merge prerequisite/current deltas into its copied main specs. Obtain canonical IDs with `tools.spec_traceability --repo-root <equivalent-root> list`, and retain literal intended `covers_requirement` annotations in implementation tests. Run `check` with that equivalent root and the copied contract gate from that directory before sync; the unsynced real-root gate is not an acceptance gate for new IDs.
- [x] 3.3 Run only the focused labels/files/classes named above and observability lint if logging changes; run strict validation and the equivalent-tree gate before handoff, then normal root `tools.spec_traceability check` and `tools.contract_gate` after sync. Record commands/results and existing-doc updates; no broad suites, CI shard commands or local full evidence verification.

## Verification record

- Resolver: `web/webclient/presentation/map_quest_destinations.py`. On the real geography the nearest-hunt search takes about 0.12–0.14 s cold for a player far from the target region (for example Grandia's capital hunting the western hills) and 2–6 ms once the empty-tile memo is warm.
- Evennia runner, `--settings test_settings.py --keepdb`: `web.webclient.presentation.tests.test_map_quest_destinations tests.test_evennia_test_optimization_contract` ran 22 tests OK (13 in the new module).
- `uv run --locked python -m tools.observability_lint check`: 0 violations. The two `NodeIDError` branches carry reasoned R2 exemptions, and the per-entry failure logs `map_quest_destination_unresolved` with `exc=`.
- Manifests: the new module is registered in the `webclient-presentation-a` shard of `.github/evennia-shards.json`. No browser test was added. All fixtures are synthetic; no production data contract was added.
- Equivalent tree: a disposable copy with the delta merged into a new `openspec/specs/map-quest-destinations/spec.md`, given its own throwaway git index for the test-data lint. `tools.spec_traceability --repo-root <equiv> list` gave `map-quest-destinations::accepted-commission-destinations-resolve-on-the-server`; `check` there reports 2472 covered and 0 errors, and the copied `tools.contract_gate` passed. `openspec validate resolve-map-quest-destinations --strict` passes.
- Before sync, the real-root `tools.spec_traceability check` reports only `unknown-requirement-id` for that new ID. After sync at archive, run the root `tools.spec_traceability check` and `tools.contract_gate` with the annotations unchanged.
- Docs: the "Quest destinations on the map" section and the verification command in `docs/development/continental-geography.md`. No UI file changed.
