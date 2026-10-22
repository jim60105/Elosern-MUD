# Tasks

Implementation budget: 7 hours total. Prerequisites are the exact `depends-on` lines in proposal.md.

## 1. Implement the bounded slice

- [ ] 1.1 Implement AreaMapView with metre settlement, radial room-graph and 15×15 wilderness branches, semantic known/visited/current presentation, scale-true dots/readout and gateway text.
- [ ] 1.2 Implement readable selection and adjacent-only 前往 emitting the existing move intent; expose controlled viewport state for the final host without adding an independent data requester.
- [ ] 1.3 Add real AreaMapView stories for city/current selection, wilderness, dungeon/interior fog and remote non-travel nodes; update story coverage ownership and matching app-shell styles.

## 2. Focused behavioral verification

- [ ] 2.1 Run only proposed `tests/world/area_map_view.test.js` through the webclient single-file Vitest command for geometry, fog, readout and exact movement intents.
- [ ] 2.2 Use Storybook play assertions for 前往, keyboard selection, full labels and remote inert travel; use agent-browser to exercise/capture the actual component stories and inspect 16px labels at desktop scale.
- [ ] 2.3 Run one affected managed area-map browser class/method once runtime integration is available in the final cutover; at this slice visually inspect production component geometry in the normal app wrapper rather than claiming prototype screenshots establish it.

## 3. Contracts and focused handoff

- [ ] 3.1 Register any new/moved Evennia package test modules in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use synthetic fixtures except explicitly registered production data contracts.
- [ ] 3.2 Obtain canonical requirement IDs through `tools.spec_traceability list` on the current tree and an equivalent merged-spec tree for this delta; attach literal `covers_requirement` annotations to substantive discoverable Python unit/integration/browser tests. Run traceability check with the matching spec tree; never claim a pre-sync root pass covers new deltas.
- [ ] 3.3 Run only the focused labels/files/classes named above, run observability lint if server logging changes, then `uv run --locked python -m tools.contract_gate` and strict validation. Record commands/results and update the existing behavior documentation; no broad suites, CI shard commands, or local full evidence verification.
