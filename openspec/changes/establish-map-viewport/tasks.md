# Tasks

Implementation budget: 5 hours total. Prerequisites are the exact `depends-on` lines in proposal.md.

## 1. Implement the bounded slice

- [ ] 1.1 Implement pure `lib/map_viewport.js` functions for uniform projection/inversion, pixel pan, pointer-anchored continuous zoom and explicit metre/km units.
- [ ] 1.2 Implement aspect-aware whole-map fit, scope stop selection/recentre, and rectangle/edge clamping that excludes detail width; document API for the two real map-view consumers.
- [ ] 1.3 Keep the current overlay path functioning until final cutover; do not add compatibility exports or duplicate a second component implementation.

## 2. Focused behavioral verification

- [ ] 2.1 Add proposed `web/webclient-app/tests/world/map_viewport.test.js` for independently known projection/inversion, unequal gaps, anchored zoom, pan, scope stops, aspect fit and open/closed drawer clamping; run only this Vitest file.
- [ ] 2.2 Record that real-component Storybook/agent-browser visual evidence belongs to the consuming area/world/drawer changes, not a fake visual component in this pure geometry slice.

## 3. Contracts and focused handoff

- [ ] 3.1 Register any new/moved Evennia package test modules in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use synthetic fixtures except explicitly registered production data contracts.
- [ ] 3.2 Obtain canonical requirement IDs through `tools.spec_traceability list` on the current tree and an equivalent merged-spec tree for this delta; attach literal `covers_requirement` annotations to substantive discoverable Python unit/integration/browser tests. Run traceability check with the matching spec tree; never claim a pre-sync root pass covers new deltas.
- [ ] 3.3 Run only the focused labels/files/classes named above, run observability lint if server logging changes, then `uv run --locked python -m tools.contract_gate` and strict validation. Record commands/results and update the existing behavior documentation; no broad suites, CI shard commands, or local full evidence verification.
