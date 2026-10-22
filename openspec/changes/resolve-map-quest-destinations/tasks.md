# Tasks

Implementation budget: 5 hours total. Prerequisites are the exact `depends-on` lines in proposal.md.

## 1. Implement the bounded slice

- [ ] 1.1 Add a read-only shared server resolver for accepted commissions using normalized locator/runtime sources, returning separate local identity and world position.
- [ ] 1.2 Handle ANCHOR, GRID, region species hunts and authored monster sites; implement deterministic nearest-region ties against amended geography and no fabricated fallback.
- [ ] 1.3 Document the supported destination families and the server-only precision boundary.

## 2. Focused behavioral verification

- [ ] 2.1 Add proposed `web.webclient.presentation.tests.test_map_quest_destinations` with synthetic locator/site/region fixtures, independently known nearest/tie outcomes, all four families and no-state-write assertions; run only that label.
- [ ] 2.2 Add a focused consumer regression showing a GRID destination retains local identity while its world location uses the settlement anchor; assert unsupported locators do not create markers.

## 3. Contracts and focused handoff

- [ ] 3.1 Register any new/moved Evennia package test modules in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use synthetic fixtures except explicitly registered production data contracts.
- [ ] 3.2 Obtain canonical requirement IDs through `tools.spec_traceability list` on the current tree and an equivalent merged-spec tree for this delta; attach literal `covers_requirement` annotations to substantive discoverable Python unit/integration/browser tests. Run traceability check with the matching spec tree; never claim a pre-sync root pass covers new deltas.
- [ ] 3.3 Run only the focused labels/files/classes named above, run observability lint if server logging changes, then `uv run --locked python -m tools.contract_gate` and strict validation. Record commands/results and update the existing behavior documentation; no broad suites, CI shard commands, or local full evidence verification.
