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

- [ ] 2.4 Add a discoverable Python executed-evidence wrapper in proposed `tests.test_map_client_contracts` that launches only this slice's selected JS assertions and fails on their assertion failure. Annotate wrapper test methods with tool-derived requirement IDs, never source-presence checks; run `uv run --locked python -m unittest tests.test_map_client_contracts.WorldViewContracts` for this slice. This top-level module is outside the Evennia shard manifest; any package/browser owners still require their own exact manifests.

## 3. Contracts and focused handoff

- [ ] 3.1 Register any new/moved Evennia package test modules in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use synthetic fixtures except explicitly registered production data contracts.
- [ ] 3.2 Copy the complete current implementation/tests/manifests/tooling into a disposable ordinary directory; merge prerequisite/current deltas into its copied main specs. Obtain canonical IDs with `tools.spec_traceability --repo-root <equivalent-root> list`, and retain literal intended `covers_requirement` annotations in implementation tests. Run `check` with that equivalent root and the copied contract gate from that directory before sync; the unsynced real-root gate is not an acceptance gate for new IDs.
- [ ] 3.3 Run only the focused labels/files/classes named above and observability lint if logging changes; run strict validation and the equivalent-tree gate before handoff, then normal root `tools.spec_traceability check` and `tools.contract_gate` after sync. Record commands/results and existing-doc updates; no broad suites, CI shard commands or local full evidence verification.
