# Tasks — webclient-frame-resolver-registry

## 1. Resolver core

- [x] 1.1 Create `web/webclient-app/stores/frame-resolvers.js` exporting `createFrameResolver(deps)` with the exploration-family table exactly as the delta spec defines it (`exploration.root|move|look|interact|wait|target|keywords|suggestions`, params per source, suggestions resolvable only in `generating|ready|degraded`), unknown-source and throw-to-marker degradation, and the `{unresolvable: true, reason}` marker preferring the panel's server-authored `reason.message`
- [x] 1.2 Bind each exploration resolver to the committed-state reads (`exploration`, `local_map.current_node`, `context_actions.suggestions`) through the existing `ExplorationMenu` builders unchanged — no label, row, or payload synthesis beyond what the builders already produce (root entries, back rows included)
- [x] 1.3 Wire the factory into `web/webclient-app/stores/elosern.js` against `reducer.getState()`; expose `resolveFrame` on `window.__elosernBridge` following the existing bridge pattern (test seam only)

## 2. Vitest suite (all three requirements)

- [x] 2.1 `web/webclient-app/tests/frame-resolvers.test.js` — committed-state-following and purity: resolve, swap in a newer committed fixture, re-resolve and assert the newer rows; double-resolve equality plus a deep snapshot diff proving no store/model mutation
- [x] 2.2 Table behavior: every exploration source resolves from a valid fixture with builder-identical rows (exit frame = two server exit rows + back row for a two-exit room fixture); unknown source, absent `identity`, `unavailable` suggestions envelope, and a throwing resolver all return the marker (with/without authored reason); a look/target fixture pins label/sub-line/action/payload/disabled-reason verbatim equality

## 3. Browser contract evidence (traceability)

- [x] 3.1 Add one browser test method to the existing exploration browser class (`web/tests/browser/test_browser_exploration.py`, one-class budget) driving the real three-exit south-gate fixture: resolve `exploration.move` through `__elosernBridge`, perform a real move, re-resolve, and assert the second menu names the new room's exits with no stale row; annotate with `covers_requirement` using IDs from `uv run --locked python -m tools.spec_traceability list`

## 4. Gates

- [x] 4.1 `npm test` green; `node --test web/static/webclient/js/tests/*.test.js` green (no router change expected); `uv run --locked python -m tools.spec_traceability check` green
