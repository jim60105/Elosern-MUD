# Tasks

Implementation budget: 5 hours total. Prerequisites are the exact `depends-on` lines in proposal.md.

## 1. Implement the bounded slice

- [ ] 1.1 Implement pure `lib/map_viewport.js` functions for uniform projection/inversion, pixel pan, pointer-anchored continuous zoom and explicit metre/km units.
- [ ] 1.2 Implement aspect-aware whole-map fit, scope stop selection/recentre, and rectangle/edge clamping that excludes detail width; document API for the two real map-view consumers.
- [ ] 1.3 Keep the current overlay path functioning until final cutover; do not add compatibility exports or duplicate a second component implementation.

## 2. Focused behavioral verification

- [ ] 2.1 Add proposed `web/webclient-app/tests/world/map_viewport.test.js` for independently known projection/inversion, unequal gaps, anchored zoom, pan, scope stops, aspect fit and open/closed drawer clamping; run only this Vitest file.
- [ ] 2.2 Record that real-component Storybook/agent-browser visual evidence belongs to the consuming area/world/drawer changes, not a fake visual component in this pure geometry slice.

- [ ] 2.3 Add a discoverable Python executed-evidence wrapper in proposed `tests.test_map_client_contracts` that launches only this slice's selected JS assertions and fails on their assertion failure. Annotate wrapper test methods with tool-derived requirement IDs, never source-presence checks; run `uv run --locked python -m unittest tests.test_map_client_contracts.ViewportContracts` for this slice. This top-level module is outside the Evennia shard manifest; any package/browser owners still require their own exact manifests.

## 3. Contracts and focused handoff

- [ ] 3.1 Register any new/moved Evennia package test modules in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use synthetic fixtures except explicitly registered production data contracts.
- [ ] 3.2 Copy the complete current implementation/tests/manifests/tooling into a disposable ordinary directory; merge prerequisite/current deltas into its copied main specs. Obtain canonical IDs with `tools.spec_traceability --repo-root <equivalent-root> list`, and retain literal intended `covers_requirement` annotations in implementation tests. Run `check` with that equivalent root and the copied contract gate from that directory before sync; the unsynced real-root gate is not an acceptance gate for new IDs.
- [ ] 3.3 Run only the focused labels/files/classes named above and observability lint if logging changes; run strict validation and the equivalent-tree gate before handoff, then normal root `tools.spec_traceability check` and `tools.contract_gate` after sync. Record commands/results and existing-doc updates; no broad suites, CI shard commands or local full evidence verification.
