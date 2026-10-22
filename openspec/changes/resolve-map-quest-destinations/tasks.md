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
- [ ] 3.2 Copy the complete current implementation/tests/manifests/tooling into a disposable ordinary directory; merge prerequisite/current deltas into its copied main specs. Obtain canonical IDs with `tools.spec_traceability --repo-root <equivalent-root> list`, and retain literal intended `covers_requirement` annotations in implementation tests. Run `check` with that equivalent root and the copied contract gate from that directory before sync; the unsynced real-root gate is not an acceptance gate for new IDs.
- [ ] 3.3 Run only the focused labels/files/classes named above and observability lint if logging changes; run strict validation and the equivalent-tree gate before handoff, then normal root `tools.spec_traceability check` and `tools.contract_gate` after sync. Record commands/results and existing-doc updates; no broad suites, CI shard commands or local full evidence verification.
