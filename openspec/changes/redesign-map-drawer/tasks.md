# Tasks

Implementation budget: 8 hours total. Prerequisites are the exact `depends-on` lines in proposal.md.

## 1. Implement the bounded slice

- [x] 1.1 Integrate MapDrawer and real area/world views into OverlayHost/AppClient with one header/close control, ARIA tabs, captions, per-tab epoch-scoped viewport memory and correct opening fits, resetting incompatible area selection/view on map_id or frame-key/unit changes.
- [x] 1.2 Wire exact map.view open/tab requests and once-per-committed-move active-scope refresh; preserve dispatch ordering, stale/epoch protection and no requests when closed/rejected.
- [x] 1.3 Implement real MapEdgePointers, floating control pill, quest dropdown, scale bar and selected-only detail drawer; use shared clamping, distance stacking and ＋n beyond three with keyboard/text access.
- [x] 1.4 Implement modal map shortcuts and Escape priority/focus restoration; forward only exact adjacent explore.move actions.
- [x] 1.5 After the minimap dependency, migrate all callers/tests/stories and delete obsolete MapOverlay, map_view.js, cellSize/rank compression/overlay-pitch paths without deleting still-used radial or movement helpers; apply the included inherited capability delta and map each existing assertion to the replacement requirement matching its role using the complete merged-tree canonical IDs; no retired aliases.
- [x] 1.6 Add real MapDrawer/MapEdgePointers stories covering all seven approved option-A scenarios plus fog, overflow and motion; update existing map/help/keyboard docs and component-story manifests.

## 2. Focused behavioral verification

- [x] 2.1 Run only affected `tests/overlays/map_overlay.test.js` replacement and new `tests/world/map_drawer.test.js`/pointer file, selecting individual files rather than pnpm test across the app; verify requests/commits/Escape/epoch resets, city→wilderness→interior and settlement→different-settlement frame resets, and no old imports.
- [x] 2.2 Use real Storybook play assertions for edge pointers, nameless unlit districts and 前往; use agent-browser during implementation to exercise/capture all approved scenario types and inspect labels, focus, drawer avoidance and reduced-motion reveal.
- [x] 2.3 Add one focused managed browser class (proposed `web.tests.browser.test_map_drawer.MapDrawerWalkTests`) and register its methods in browser-shards. Run that class only; use agent-browser in the live Altoria client to open map, cross gate, reach a real landmark and follow a commission pointer, saving inspected checkpoint captures.
- [x] 2.4 After main-spec sync run only the frozen/ownership contract labels required by AGENTS.md plus contract_gate; do not run complete browser, Evennia or evidence suites locally.

## 3. Contracts and focused handoff

- [x] 3.1 Register any new/moved Evennia package test modules in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use synthetic fixtures except explicitly registered production data contracts.
- [x] 3.2 Copy the complete current implementation/tests/manifests/tooling into a disposable ordinary directory; merge prerequisite/current deltas into its copied main specs. Obtain canonical IDs with `tools.spec_traceability --repo-root <equivalent-root> list`, and retain literal intended `covers_requirement` annotations in implementation tests. Run `check` with that equivalent root and the copied contract gate from that directory before sync; the unsynced real-root gate is not an acceptance gate for new IDs.
- [x] 3.3 Run only the focused labels/files/classes named above and observability lint if logging changes; run strict validation and the equivalent-tree gate before handoff, then normal root `tools.spec_traceability check` and `tools.contract_gate` after sync. Record commands/results and existing-doc updates; no broad suites, CI shard commands or local full evidence verification.

## Verification record

The implementation handoff completes the pre-sync portion of 2.4 and 3.3.
The archive owner must run the actual-root traceability and contract gates
after syncing the delta. This handoff does not sync main specs or archive.
The parent agent approved this predecessor handoff convention explicitly.

- The reported follow-current test used an invalid `townArea({current_node})`
  fixture, leaving the square marked current. It now uses the existing
  `townFromEastArea()` fixture, which updates visibility and adjacent actions
  together. The exact validator is unchanged. The test verifies retained
  400 m zoom and the new player's visible position.
- Preimplementation review identified deferred follow work crossing frames.
  Follow now runs in a post-render watcher, without a queued next-tick
  callback, and compares epoch plus complete area map/frame identity.
  Frame/epoch retirement regressions pass.
- `pnpm exec vitest run web/webclient-app/tests/world/map_drawer.test.js
  web/webclient-app/tests/world/map_edge_pointers.test.js`: 50 tests passed.
  Includes request commit ordering, rejected/closed paths, keyboard/Escape,
  current markers, removal checks and both required frame-transition paths.
- `uv run --locked python -m unittest
  tests.test_map_client_contracts.MapDrawerContracts
  tests.test_map_client_contracts.MapEdgePointerContracts`: 8 passed,
  executing those same focused JS files through the evidence wrappers.
- `uv run --locked python -m web.tests.browser.unittest_driver
  web.tests.browser.test_map_drawer.MapDrawerWalkTests`: 2 passed in 53.447 s.
  The managed class uses synthetic minimap fixtures. Its unanchored synthetic
  settlement intentionally receives the server's unavailable world response;
  real continental geometry is verified in the separate live journey.
- Real Storybook plays completed without console errors for all seven
  approved option-A scenarios, Dungeon, Interior, OverflowPointers,
  LegendEscape and ReducedMotionReveal, plus both MapEdgePointers stories.
  Agent-browser exercised them at 1451×790. Inspected captures are
  `/tmp/map-drawer-final-<scenario>.png`. City selection forwards the exact
  exit; overflow opens all six commissions and focuses the first row;
  legend Escape restores toggle focus; reduced reveal announces discovery
  without ink. A visual overlap between top-edge commission chips was fixed
  by spacing them by their width; real play assertions now reject overlap.
- The isolated shipped-catalog live client was exercised through
  agent-browser under `.elosern-root`. Opened at Altoria's south gate,
  crossed to `wild:elosern:860:1077`, returned and walked South Avenue,
  Avenue North and Central Plaza through actual adjacent 前往 controls.
  Reaching `grid:capital_altoria:3500:2850` lit 王都河谷, changing 0/120
  to 1/120 known districts. Entered the real guild, registered and accepted
  `eastern_plains_ridge_burrow_hare:1` using ordinary player commands.
  Outside the guild its eastern pointer selected and centred the real
  commission's approximate destination, preserving the server's 50 km
  precision and showing no remote movement control.
- Inspected live captures are `/tmp/map-drawer-live-altoria.png`,
  `/tmp/map-drawer-live-gate.png`, `/tmp/map-drawer-live-landmark.png`,
  `/tmp/map-drawer-live-commission-pointer.png` and
  `/tmp/map-drawer-live-commission-detail.png`. Header, labels and floating
  chrome remain readable; the selected detail keeps its own right-hand
  column and the pill stays to its left. No conflicting app-shell map
  overrides remain.
- The complete equivalent ordinary directory is
  `/tmp/map-drawer-equivalent-8yv3c_lr`, initialized as a standalone git
  repository for the test-data lint, without a branch/worktree relationship
  to the feature. Prerequisite specs are already in the base; both current
  deltas were merged into its copied main specs. Canonical IDs were obtained
  with `tools.spec_traceability list --json-output`; the assertion-role
  matrix is in `docs/development/metric-local-maps.md`.
- Equivalent `tools.spec_traceability check`: 2495 requirements,
  11132 associations, 2495 covered, zero uncovered/errors.
  The copied `tools.contract_gate` passed traceability, observability,
  test-data, manifests and all 18 frozen/ownership contracts.
  The stale deleted edge-name test was removed from active test-data debt;
  its historical seed baseline remains unchanged.
- `openspec validate redesign-map-drawer --strict`: passed. No production
  logging path changed. No broad test suite or CI evidence verification ran.
- Postimplementation review found two blocking pointer-capacity defects:
  occupied-endpoint fallback on a full edge, and missing cross-edge corner
  collision accounting. Both are fixed by conservative shared rectangles,
  nearest-free-edge placement and accessible overflow folding that reserves
  a real spot for ＋n. The review's exact saturated-top and adjacent-corner
  reproductions are now focused passing tests. Relevant real Storybook
  plays were repeated with no console errors, including overflow-chip
  collision and drawer-avoidance assertions, and captures inspected.
  The reviewer could inspect current source/specs but could not obtain the
  full Git diff through its tools; this is recorded as a review limitation,
  not a complete-diff approval.
- Existing map protocol, metric-map, frozen-hook, player command and
  frontend-agent docs were updated. The builder-oriented text `地圖`
  command and its reference entry are intentionally unchanged.
