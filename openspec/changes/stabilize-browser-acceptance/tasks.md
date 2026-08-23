## 1. Shared deterministic-state wait helper

- [ ] 1.1 Add `wait_for_store_state(page, predicate, dom_predicate=None, timeout=30000,
  interval_ms=250)` to `web/tests/browser/browser_helpers.py`: a bounded Python-side polling loop
  that reads the committed store view via `store_state_or_none` (navigation-tolerant). The optional
  `dom_predicate` is evaluated in the SAME loop under one monotonic deadline (store gate + DOM
  readiness share one bounded window). A `None` store read is logged and polling continues (the
  store predicate is not invoked on `None`). On timeout, raise an `AssertionError` carrying
  `last_non_none_state`, `none_observed`, the last evaluation error, and — when a `dom_predicate`
  is supplied — the selector's connected/visible/enabled state and the `activeElement`.
- [ ] 1.2 Convert the shared helpers `wait_for_shell_active` and `focus_action_dock` in
  `browser_helpers.py` from raw DOM waits to the store-state gate. For `focus_action_dock`: gate on
  the store state (connected + dock panel available), poll the `#action-dock` DOM readiness in the
  same bounded loop, call `locator.focus()`, then verify `document.activeElement` is the dock or
  its delegated focus target.

## 2. Convert ALL raw DOM-visibility waits in `web/tests/browser/`

- [ ] 2.1 `test_browser_exploration.py`: replace raw `page.wait_for_function` /
  `wait_for_selector` / `locator.click` gates (narrative text, `#action-dock` focus, cell clicks,
  disconnect waits) with `wait_for_store_state`, keeping short bounded DOM checks only for
  DOM-bound assertions.
- [ ] 2.2 `test_browser_services.py`: convert the guild/shop/guild-board/exam journeys' raw waits
  (turn-in, buy/sell, reconnect) to the store-state gate.
- [ ] 2.3 `test_browser_layout.py` and `test_browser_reconnect.py`: convert the layout-migration /
  protocol-mismatch / reconnect raw `wait_for_function` / `wait_for_selector` waits to the
  store-state gate.
- [ ] 2.4 `test_browser_art.py`: convert the art-panel / combat-row raw DOM waits (`.art-panel`,
  `#combat-row-0`, portrait focus) to the store-state gate, keeping the spec-mandated `#combat-row-0`
  mount wait as a bounded DOM check.
- [ ] 2.5 `test_vue_foundation.py` and `test_vue_transport_mount.py`: convert the Vue
  foundation/transport raw `wait_for_selector` / `wait_for_function` / `locator.click` gates (VUE_ROOT,
  command-drawer open/close, console log, Storybook render) to the store-state gate.
- [ ] 2.6 `test_browser_options_surface.py` and `test_browser_choicepoints.py`: convert the
  options-surface / choicepoints raw waits to the store-state gate.
- [ ] 2.7 `test_browser_combat_rejection.py`: convert the combat-rejection raw waits (tampered
  target, stale forfeit, reconnect resume) to the store-state gate.
- [ ] 2.8 The currently-passing files with raw waits — `test_browser_shell.py`,
  `test_browser_input_narrative.py`, `test_browser_pointer.py` — convert their raw DOM-visibility
  waits to the store-state gate so no residual raw-wait population remains.

## 3. Register the missing shard-manifest method

- [ ] 3.1 Add `web.tests.browser.test_browser_combat_rejection.CombatReconnectBrowserTest.test_confirmed_action_disconnect_shows_no_uncertain_notice`
  to `.github/browser-shards.json` under shard 3 `combat-rejection` (append to `files_a` or
  `files_b`). After adding, run the full shard-3 process list under CI-equivalent parallel
  conditions and record the duration; if it approaches the shard budget, move one
  equally-independent class to a shard with headroom, keeping each discovered method in exactly
  one process list.

## 4. Verify (CI-based, specific tests only — not the full local suite)

- [ ] 4.1 Locally run the specific failing browser test classes/files for each affected shard
  (one class or file within the 10-minute budget) and confirm the store-state gate removes the
  `TimeoutError` failures.
- [ ] 4.2 Run the top-level ownership contract test
  `tests.test_evennia_test_optimization_contract.TestOwnershipContractTests.test_browser_method_labels_preserve_exact_ownership`
  and confirm it passes after the manifest registration.
- [ ] 4.3 Run a representative smoke set that covers the currently-passing shards that share the
  converted helpers — a combat-dock smoke (shard 1/2), a pointer-dock smoke (shard 9), and a
  login-shell smoke — to guard against shared-helper regressions, each within the 10-minute budget.
- [ ] 4.4 Push the branch and confirm the affected browser shards (3, 5, 6, 7, 8, 10, 11, 12, 13,
  14, 15) and the passing shards that share the converted helpers (1, 2, 9) are green in CI,
  without running the full local suite.
