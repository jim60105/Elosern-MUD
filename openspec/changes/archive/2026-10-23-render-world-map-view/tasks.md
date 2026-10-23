# Tasks

Implementation budget: 8 hours total. Prerequisites are the exact `depends-on` lines in proposal.md.

## 1. Implement the bounded slice

- [x] 1.1 Implement WorldMapView consuming validated world panels with exactly ordered layers, opaque unlit selection, approximate dashed circles and resolution-aware trail rendering.
- [x] 1.2 Add inclusive LOD thresholds with screen-space >=16px text and collision hiding; emit semantic selections with multi-nation lit district details.
- [x] 1.3 Add 600 ms landmark-origin reveal and one live announcement only for newly lit districts observed open, respecting instant reduced/off motion and epoch/session resets.
- [x] 1.4 Add real WorldMapView stories for world country/continent/nearby, selected district/quest, unlit hatching, approximate markers and new-light/reduced-motion cases; update coverage/style ownership.

## 2. Focused behavioral verification

- [x] 2.1 Run only proposed `tests/world/world_map_view.test.js` with layer order, threshold boundaries, no unlit names, exact/approximate semantics and repeated-load/motion transition assertions.
- [x] 2.2 Use real-component Storybook play functions to assert nameless unlit districts, selection text, precision labels and 600ms-versus-reduced behavior; exercise the actual stories with agent-browser, capture and inspect country/continent/nearby views.
- [x] 2.3 Verify shared motion tokens and app-shell overrides in a normal production wrapper; the final drawer change owns the full live-client walk and one focused managed browser class.

- [x] 2.4 Add a discoverable Python executed-evidence wrapper in proposed `tests.test_map_client_contracts` that launches only this slice's selected JS assertions and fails on their assertion failure. Annotate wrapper test methods with tool-derived requirement IDs, never source-presence checks; run `uv run --locked python -m unittest tests.test_map_client_contracts.WorldViewContracts` for this slice. This top-level module is outside the Evennia shard manifest; any package/browser owners still require their own exact manifests.

## 3. Contracts and focused handoff

- [x] 3.1 Register any new/moved Evennia package test modules in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use synthetic fixtures except explicitly registered production data contracts.
- [x] 3.2 Copy the complete current implementation/tests/manifests/tooling into a disposable ordinary directory; merge prerequisite/current deltas into its copied main specs. Obtain canonical IDs with `tools.spec_traceability --repo-root <equivalent-root> list`, and retain literal intended `covers_requirement` annotations in implementation tests. Run `check` with that equivalent root and the copied contract gate from that directory before sync; the unsynced real-root gate is not an acceptance gate for new IDs.
- [x] 3.3 Run only the focused labels/files/classes named above and observability lint if logging changes; run strict validation and the equivalent-tree gate before handoff, then normal root `tools.spec_traceability check` and `tools.contract_gate` after sync. Record commands/results and existing-doc updates; no broad suites, CI shard commands or local full evidence verification.

## Verification record

- `npx vitest run web/webclient-app/tests/world/world_map_view.test.js`: 21 passed. The area map view, map viewport, motion token and motion reader files: 61 passed.
- The `tests.test_map_client_contracts.WorldViewContracts` wrapper: 4 passed.
- Focused Evennia labels: the four `web.webclient.tests.test_vue_showcase_*_evidence` modules (16 passed), plus `tests.test_evennia_test_optimization_contract` and `tests.test_webclient_frozen_contract` (18 passed). No test module was added or moved, so neither shard manifest changes.
- `node scripts/component-coverage.mjs`: 80 of 80 stories, with World/WorldMapView registered.
- Equivalent merged-spec tree: a disposable copy with the delta synced into `openspec/specs/webclient-world-map-view` and a fresh git index. In that tree, `tools.spec_traceability --repo-root <copy> check` reports 2,491 covered and 0 uncovered, and `tools.contract_gate` passes. `openspec validate render-world-map-view --strict` passes.
- Storybook with agent-browser: every World/WorldMapView story's play passes at 1451×790. The continent story was also captured at 1920×1080, where labels are 21.2 px at UI scale 1.32. The reveal was captured mid-spread by slowing the token. In those captures the ink spreads from the landmark, the hatching recedes and a gilt rim is clipped to the district. Stories render under `.elosern-root` with `app-shell.css` loaded, and no `.world-map` override exists there.
- No logging path changed. The root traceability check and contract gate run after main-spec sync, at archive.
