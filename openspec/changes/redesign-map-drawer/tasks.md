# Tasks

Implementation budget: 8 hours total. Prerequisites are the exact `depends-on` lines in proposal.md.

## 1. Implement the bounded slice

- [ ] 1.1 Integrate MapDrawer and real area/world views into OverlayHost/AppClient with one header/close control, ARIA tabs, captions, per-tab epoch-scoped viewport memory and correct opening fits, resetting incompatible area selection/view on map_id or frame-key/unit changes.
- [ ] 1.2 Wire exact map.view open/tab requests and once-per-committed-move active-scope refresh; preserve dispatch ordering, stale/epoch protection and no requests when closed/rejected.
- [ ] 1.3 Implement real MapEdgePointers, floating control pill, quest dropdown, scale bar and selected-only detail drawer; use shared clamping, distance stacking and ＋n beyond three with keyboard/text access.
- [ ] 1.4 Implement modal map shortcuts and Escape priority/focus restoration; forward only exact adjacent explore.move actions.
- [ ] 1.5 After the minimap dependency, migrate all callers/tests/stories and delete obsolete MapOverlay, map_view.js, cellSize/rank compression/overlay-pitch paths without deleting still-used radial or movement helpers; apply the included inherited capability delta and map each existing assertion to the replacement requirement matching its role using the complete merged-tree canonical IDs; no retired aliases.
- [ ] 1.6 Add real MapDrawer/MapEdgePointers stories covering all seven approved option-A scenarios plus fog, overflow and motion; update existing map/help/keyboard docs and component-story manifests.

## 2. Focused behavioral verification

- [ ] 2.1 Run only affected `tests/overlays/map_overlay.test.js` replacement and new `tests/world/map_drawer.test.js`/pointer file, selecting individual files rather than pnpm test across the app; verify requests/commits/Escape/epoch resets, city→wilderness→interior and settlement→different-settlement frame resets, and no old imports.
- [ ] 2.2 Use real Storybook play assertions for edge pointers, nameless unlit districts and 前往; use agent-browser during implementation to exercise/capture all approved scenario types and inspect labels, focus, drawer avoidance and reduced-motion reveal.
- [ ] 2.3 Add one focused managed browser class (proposed `web.tests.browser.test_map_drawer.MapDrawerWalkTests`) and register its methods in browser-shards. Run that class only; use agent-browser in the live Altoria client to open map, cross gate, reach a real landmark and follow a commission pointer, saving inspected checkpoint captures.
- [ ] 2.4 After main-spec sync run only the frozen/ownership contract labels required by AGENTS.md plus contract_gate; do not run complete browser, Evennia or evidence suites locally.

## 3. Contracts and focused handoff

- [ ] 3.1 Register any new/moved Evennia package test modules in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use synthetic fixtures except explicitly registered production data contracts.
- [ ] 3.2 Copy the complete current implementation/tests/manifests/tooling into a disposable ordinary directory; merge prerequisite/current deltas into its copied main specs. Obtain canonical IDs with `tools.spec_traceability --repo-root <equivalent-root> list`, and retain literal intended `covers_requirement` annotations in implementation tests. Run `check` with that equivalent root and the copied contract gate from that directory before sync; the unsynced real-root gate is not an acceptance gate for new IDs.
- [ ] 3.3 Run only the focused labels/files/classes named above and observability lint if logging changes; run strict validation and the equivalent-tree gate before handoff, then normal root `tools.spec_traceability check` and `tools.contract_gate` after sync. Record commands/results and existing-doc updates; no broad suites, CI shard commands or local full evidence verification.
