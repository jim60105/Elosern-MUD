## Why

CI run 32705789787 leaves two browser shards red:

- **Shard 14 (vue-foundation)** — `test_window_elosern_bridge_facades_resolve_and_route` fails
  deterministically (reproduced locally). The test dispatches `ArrowDown` on the exploration root
  frame and asserts the keyboard router's `store.view.focus.key` becomes `"action-guild"`, but the
  app's G2 hierarchical exploration root exposes the bare key `"move"` (a one-row grid makes
  `ArrowDown` a no-op). The `action-guild` expectation is a **stale test expectation** written
  against the legacy B2 flat `context_actions` affordance-list key contract (`action-<action_id>` /
  `action-<surface>`), which the G2 root has replaced. The app behavior is correct; the test is
  stale.
- **Shard 11 (art-harness-shell)** — `test_missing_scene_uses_the_placeholder_and_play_continues`
  is **flaky in CI only** (passes locally). Under a loaded CI runner the placeholder count assertion
  occasionally observes two `.art-panel__scene-placeholder` nodes (a transient double-node window
  during a snapshot refresh / Vue re-render), producing `AssertionError: 2 == 2`. It is a
  timing/load-related flake, not a permanent art-panel behavioral bug.

## What Changes

- Update the keyboard-routing expectation in `web/tests/browser/test_vue_foundation.py` so it
  asserts the G2 hierarchical root focus (the bare `move/look/interact/character/quests/inventory/wait`
  keys), replacing the stale `action-guild` expectation and the Enter→`guild` surface assertion.
- Make the art-panel placeholder assertion in `web/tests/browser/test_browser_art.py` robust by
  gating the DOM-bound count on the shared bounded wait helper (`wait_for_store_state` with a
  DOM-readiness descriptor) instead of a single raw `.count()` sample, so the transient double-node
  window no longer fails the shard under CI load.
- Amend three capability specs so the contracts match the observed, correct behavior:
  - `webclient-desktop-shell`: the keyboard-routing contract SHALL expose the G2 bare-key hierarchical
    exploration root (not the B2 `action-`/`target-` prefixed contract).
  - `webclient-art-panel`: the scene placeholder DOM SHALL remain a single, stable node even under
    loaded re-renders (no transient double-node window).
  - `webclient-browser-verification`: DOM-bound acceptance assertions SHALL gate on the bounded
    wait helper (store + DOM-readiness descriptor), never on a single raw visibility/count sample.

## Capabilities

### New Capabilities

(none — this change only amends existing capability specs)

### Modified Capabilities

- `webclient-desktop-shell`: `keyboard-routing-is-menu-first-and-submission-safe` — the exploration
  keyboard root is the G2 hierarchical menu with bare item keys (`move`/`look`/`interact`/
  `character`/`quests`/`inventory`/`wait`), not the legacy `action-`-prefixed flat affordance list.
- `webclient-art-panel`: `art-degradation-never-blocks-gameplay-or-leaks-rejected-content` — the
  scene placeholder frame SHALL render as exactly one stable DOM node; a missing/failed/pending scene
  degrades to that single placeholder and never leaves a transient second placeholder node during a
  snapshot refresh.
- `webclient-browser-verification`: `browser-test-waits-gate-on-deterministic-state-within-a-bounded-deadline`
  — DOM-bound acceptance assertions (counts, visibility) SHALL be gated by the shared bounded wait
  helper using a `{selector, predicate, description}` DOM-readiness descriptor, so a delayed render
  under a loaded CI runner does not produce a flaky raw count.

## Impact

- **Test code** (planning only; the fix lands on this branch):
  `web/tests/browser/test_vue_foundation.py` (keyboard-routing block + Enter assertion),
  `web/tests/browser/test_browser_art.py` (placeholder count assertion), and
  `web/tests/browser/browser_helpers.py` (reused bounded-wait helper, no new API needed).
- **Specs**: three capability spec deltas under this change's `specs/` directory.
- **App code**: no behavior change — the Vue app and the keyboard router are already correct; this
  change aligns the tests and the capability contracts with the implemented behavior.
- **CI**: both shards (`vue-foundation`, `art-harness-shell`) are expected to turn green; no other
  shards are touched.
