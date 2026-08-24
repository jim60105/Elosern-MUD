## Why

The managed browser acceptance shards (`browser (3/5/6/7/8/10/11/12/13/14/15)`) have been
failing on the `fix/browser-creation-ci` branch (CI run 32634654248), almost entirely with
Playwright `TimeoutError`.

The underlying cause is the frontend rewrite: the WebClient shell was replaced by the Vue SPA
(Vue C4 flip). The managed browser tests were written against the old GoldenLayout/jQuery shell
and still wait on now-stale legacy selectors (e.g. `.elosern-narrative`, `.elosern-drawer` in
the shared `wait_for_shell_active` gate) that the Vue app no longer renders under those exact
classes. So every journey times out waiting for an interface that no longer exists, regardless
of CI load. The existing spec already mandates that test waits SHALL gate on deterministic
state (the committed store view + surface DOM) with a bounded deadline "rather than on the raw
`#action-dock` element becoming visible," but only the creation surface has been converted; the
rest of the suite still waits on legacy DOM. A top-level contract test
(`test_browser_method_labels_preserve_exact_ownership`) also fails because one discovered browser
test method is not registered in any shard manifest entry.

## What Changes

- Introduce a shared bounded, deterministic-state wait helper in `web/tests/browser/browser_helpers.py`
  that polls the committed store view (and, where needed, the surface DOM) within a single bounded
  monotonic deadline. It accepts an optional DOM-readiness predicate evaluated in the same polling
  loop, tolerates `None` store reads (mid-reload), and on timeout raises a diagnostic
  `AssertionError` carrying the last observed store state, DOM facts, and the `activeElement`.
- Convert ALL raw DOM-visibility waits in `web/tests/browser/` (the failing test files, the
  currently-passing files with raw waits, and the shared helpers `wait_for_shell_active` /
  `focus_action_dock`) to the deterministic-state gate, so a slow server publish or a delayed
  client render no longer burns the whole timeout budget on a single raw-visibility wait. Focus
  operations verify `document.activeElement` after focusing.
- Retarget the DOM-bound assertions from the stale legacy selectors (`.elosern-narrative`,
  `.elosern-drawer`, etc.) to the Vue app's `data-testid` hooks (`narrative-feed`,
  `command-drawer`, `action-dock`, `art-panel`, `creation-overlay`), so waits and assertions
  target the interface the Vue SPA actually renders.
- Register the unregistered discovered method
  `test_browser_combat_rejection.CombatReconnectBrowserTest.test_confirmed_action_disconnect_shows_no_uncertain_notice`
  into `.github/browser-shards.json` (shard 3 `combat-rejection`) so the top-level ownership
  contract passes.
- Keep every journey's asserted behavior identical; only the wait strategy changes (no change
  to which journeys are exercised, no new fixtures, no new remote/LLM/image requests).

## Capabilities

### New Capabilities
<!-- None. -->

### Modified Capabilities
- `webclient-browser-verification`: Add/modify the requirement that governs how the whole
  managed browser suite gates its waits. Generalize the creation-surface clause ("gate on
  deterministic state — polling the committed store view and the surface DOM with a bounded
  deadline — rather than on raw `#action-dock` visibility") to ALL browser acceptance journeys,
  and add the top-level contract that every discovered browser test method is registered in
  exactly one shard manifest entry.

## Impact

- Code: `web/tests/browser/browser_helpers.py` (new shared wait helper), and the failing
  test files under `web/tests/browser/` (wait conversions).
- CI: `.github/browser-shards.json` (register the missing method); no change to the shard
  process composition otherwise.
- Spec: `openspec/specs/webclient-browser-verification/spec.md` (deterministic-wait gate +
  shard-ownership contract).
- Verification: run the specific failing browser test classes/methods locally (one class or file
  within the 10-minute budget), plus a representative smoke set covering the passing shards that
  share the converted helpers (combat 1/2, pointer 9, login-shell) to guard against
  shared-helper regressions. Not the full local suite.
