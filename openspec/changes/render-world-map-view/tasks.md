# Tasks

Implementation budget: 8 hours total. Prerequisites are the exact `depends-on` lines in proposal.md.

## 1. Implement the bounded slice

- [ ] 1.1 Implement WorldMapView consuming validated world panels with exactly ordered layers, opaque unlit selection, approximate dashed circles and resolution-aware trail rendering.
- [ ] 1.2 Add inclusive LOD thresholds with screen-space >=16px text and collision hiding; emit semantic selections with multi-nation lit district details.
- [ ] 1.3 Add 600 ms landmark-origin reveal and one live announcement only for newly lit districts observed open, respecting instant reduced/off motion and epoch/session resets.
- [ ] 1.4 Add real WorldMapView stories for world country/continent/nearby, selected district/quest, unlit hatching, approximate markers and new-light/reduced-motion cases; update coverage/style ownership.

## 2. Focused behavioral verification

- [ ] 2.1 Run only proposed `tests/world/world_map_view.test.js` with layer order, threshold boundaries, no unlit names, exact/approximate semantics and repeated-load/motion transition assertions.
- [ ] 2.2 Use real-component Storybook play functions to assert nameless unlit districts, selection text, precision labels and 600ms-versus-reduced behavior; exercise the actual stories with agent-browser, capture and inspect country/continent/nearby views.
- [ ] 2.3 Verify shared motion tokens and app-shell overrides in a normal production wrapper; the final drawer change owns the full live-client walk and one focused managed browser class.

## 3. Contracts and focused handoff

- [ ] 3.1 Register any new/moved Evennia package test modules in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use synthetic fixtures except explicitly registered production data contracts.
- [ ] 3.2 Obtain canonical requirement IDs through `tools.spec_traceability list` on the current tree and an equivalent merged-spec tree for this delta; attach literal `covers_requirement` annotations to substantive discoverable Python unit/integration/browser tests. Run traceability check with the matching spec tree; never claim a pre-sync root pass covers new deltas.
- [ ] 3.3 Run only the focused labels/files/classes named above, run observability lint if server logging changes, then `uv run --locked python -m tools.contract_gate` and strict validation. Record commands/results and update the existing behavior documentation; no broad suites, CI shard commands, or local full evidence verification.
