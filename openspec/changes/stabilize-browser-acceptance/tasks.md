## 1. Shared deterministic-state wait helper

- [x] 1.1 Confirm the existing `wait_for_store_state(page, predicate, dom_readiness=None,
  timeout=30000, interval_ms=250)` in `web/tests/browser/browser_helpers.py` matches the spec, and
  close the one gap the delta spec requires but the current implementation misses: `last_eval_error` is
  never assigned, so a non-navigation DOM-predicate JS/selector error currently escapes the polling loop
  instead of being surfaced in the timeout diagnostic. Fix: in the polling loop, wrap the
  `dom_readiness` predicate evaluation so a non-navigation error is recorded as `last_eval_error` and
  polling continues to the deadline (a recoverable navigation error stays `None`). The store view is read
  via `store_state_or_none` (navigation-tolerant); `dom_readiness` is a structured descriptor
  `{"selector", "predicate", "description"}` whose JS `predicate` is evaluated in the SAME loop under one
  monotonic deadline; a `None` store read is "not ready yet" (predicate not invoked on `None`); on timeout
  raise an `AssertionError` carrying `last_non_none_state`, `none_observed`, the last evaluation error, and
  — when a `dom_readiness` descriptor is supplied — the selector's connected/visible/enabled state and the
  `activeElement`.
- [x] 1.2 Convert the shared helpers `wait_for_shell_active` and `focus_action_dock` in
  `browser_helpers.py` from raw DOM waits to the store-state gate. Retarget `REQUIRED_SURFACES`
  from the stale legacy selectors (`.elosern-header` / `.elosern-narrative` / `.elosern-drawer`)
  to the Vue app's `data-testid` hooks (`.elosern-header` still renders; the narrative and drawer
  surfaces are now `data-testid="narrative-feed"` and `data-testid="command-drawer"`). For
  `focus_action_dock`: gate on the store state (connected + dock panel available), poll the
  `#action-dock` DOM readiness in the same bounded loop, call `locator.focus()` using the remaining
  deadline, then verify `document.activeElement` is the dock itself or a focusable descendant (or an
  explicitly allowed delegated-focus target).
- [x] 1.3 In every failing test file, retarget DOM-bound assertions from the stale legacy
  selectors to the Vue `data-testid` hooks (`narrative-feed`, `command-drawer`, `action-dock`,
  `art-panel`, `creation-overlay`), so assertions target the interface the Vue SPA actually renders.
- [x] 1.4 Add `document.activeElement` verification to `focus_creation_action_dock` in
  `browser_helpers.py`: after `locator.focus()`, verify `document.activeElement` is the `#action-dock`
  itself or a focusable descendant; on mismatch raise a diagnostic `AssertionError` naming the
  `activeElement`. This closes the creation-journey gap flagged by the reviewer (the creation dock focus
  currently focuses without confirming the focus actually landed).

## 2. Convert ALL raw DOM-visibility waits in `web/tests/browser/`

- [x] 2.1 `test_browser_exploration.py`: replace raw `page.wait_for_function` /
  `wait_for_selector` / `locator.click` gates (narrative text, `#action-dock` focus, cell clicks,
  disconnect waits) with `wait_for_store_state`, keeping short bounded DOM checks only for
  DOM-bound assertions.
- [x] 2.2 `test_browser_services.py`: convert the guild/shop/guild-board/exam journeys' raw waits
  (turn-in, buy/sell, reconnect) to the store-state gate.
- [x] 2.3 `test_browser_layout.py` and `test_browser_reconnect.py`: convert the layout-migration /
  protocol-mismatch / reconnect raw `wait_for_function` / `wait_for_selector` waits to the
  store-state gate.
- [x] 2.4 `test_browser_art.py`: convert the art-panel / combat-row raw DOM waits (`.art-panel`,
  `#combat-row-0`, portrait focus) to the store-state gate, keeping the spec-mandated `#combat-row-0`
  mount wait as a bounded DOM check.
- [x] 2.5 `test_vue_foundation.py` and `test_vue_transport_mount.py`: convert the Vue
  foundation/transport raw `wait_for_selector` / `wait_for_function` / `locator.click` gates (VUE_ROOT,
  command-drawer open/close, console log, Storybook render) to the store-state gate.
- [x] 2.6 `test_browser_options_surface.py` and `test_browser_choicepoints.py`: convert the
  options-surface / choicepoints raw waits to the store-state gate.
- [x] 2.7 `test_browser_combat_rejection.py`: convert the combat-rejection raw waits (tampered
  target, stale forfeit, reconnect resume) to the store-state gate.
- [x] 2.8 The currently-passing files with raw waits — `test_browser_shell.py`,
  `test_browser_input_narrative.py`, `test_browser_pointer.py` — convert their raw DOM-visibility
  waits to the store-state gate so no residual raw-wait population remains.
- [x] 2.9 `test_browser_actions.py`, `test_browser_local_map.py`, and `test_browser_session_lifecycle.py`:
  convert the remaining raw DOM-visibility waits (e.g. `test_browser_actions.py` disconnected/offline
  overlay waits, `test_browser_local_map.py` `wait_for_selector` on `[data-testid='local-map__title']`
  / `.local-map__lattice`, `test_browser_session_lifecycle.py` session waits) to the store-state gate.
  Preserve pure store-result and pure assertion waits; only readiness waits that need both the store
  state and surface DOM readiness get converted.
- [x] 2.10 `test_browser_creation.py`: convert the creation-journey raw DOM-visibility waits (the
  `#action-dock` / `creation-overlay` readiness) to the store-state gate, and retarget DOM-bound
  assertions to the `creation-overlay` / `action-dock` `data-testid` hooks so the creation journey targets
  the Vue interface (closes the creation-scope gap flagged by the reviewer).

## 5. Helper behavior test

- [x] 5.1 Add a focused Playwright test for `wait_for_store_state` itself, covering: recovers after a
  `None` (mid-reload) read, the store predicate is never invoked on `None`, the store gate and the
  DOM-readiness descriptor must both hold, and the timeout `AssertionError` carries the last state, the
  `none_observed` flag, the last evaluation error, and (when a descriptor is present) the selector's
  connected/visible/enabled state + `activeElement`.

## 3. Register the missing shard-manifest method

- [x] 3.1 Verify the discovered method
  `web.tests.browser.test_browser_combat_rejection.CombatReconnectBrowserTest.test_confirmed_action_disconnect_shows_no_uncertain_notice`
  is registered under shard 3 `combat-rejection` in `.github/browser-shards.json` — it already is (line
  46), so confirm exactly-one-process ownership and do NOT append it a second time. If a shard-3 process
  list approaches the shard budget, move one equally-independent class to a shard with headroom, keeping each
  discovered method in exactly one process list.

## 4. Verify (CI-based, specific tests only — not the full local suite)

- [x] 4.1 Locally run the specific failing browser test classes/files for each affected shard
  (one class or file within the 10-minute budget) and confirm the store-state gate removes the
  `TimeoutError` failures.
- [x] 4.2 Run the top-level ownership contract test
  `tests.test_evennia_test_optimization_contract.TestOwnershipContractTests.test_browser_method_labels_preserve_exact_ownership`
  and confirm it passes after the manifest registration.
- [x] 4.3 Run a representative smoke set that covers the currently-passing shards that share the
  converted helpers — a combat-dock smoke (shard 1), a pointer-dock smoke (shard 9), and a
  login-shell smoke — to guard against shared-helper regressions, each within the 10-minute budget.
  Confirmed green: `test_browser_combat.CombatMenuBrowserTest.test_focus_stays_on_action_dock_in_combat`
  (shard 1), `test_browser_pointer.PointerAcceptanceTest.test_pointer_exploration_root_and_submenu_submission`
  (shard 9), and `test_browser_shell.ShellAcceptanceTest.test_surfaces_visible_at_1440x900` (login-shell).
- [ ] 4.4 Push the branch and confirm the affected browser shards (3, 5, 6, 7, 8, 10, 11, 12, 13,
  14, 15) and the passing shards that share the converted helpers (1, 2, 9) are green in CI,
  without running the full local suite.
