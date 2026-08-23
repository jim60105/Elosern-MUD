## Context

Elosern's managed browser acceptance suite (`web/tests/browser/`) proves, in a real Chromium
browser against an isolated, deterministic, managed Evennia server, that every gameplay surface
(character creation, exploration, services, combat, art, pointer parity, layout/reconnect)
works end to end. Each test boots its own managed runtime (temp SQLite, dynamic loopback
ports, deterministic account/character fixtures) and drives the UI with keyboard controls at
1440x900 and 1280x720. The suite is the sole quality-gate owner of `web/tests/browser/` and
writes requirement-coverage evidence into `OPENSPEC_TEST_EVIDENCE`.

On the `fix/browser-creation-ci` branch (CI run 32634654248) eleven browser shards fail, almost
entirely with Playwright `TimeoutError`. The root cause is that most waits in the failing test
files gate on **raw DOM visibility** (`page.wait_for_selector`, `page.wait_for_function`,
`locator.click`). Under a loaded CI runner — two parallel workspaces each starting an Evennia
server plus Chromium — the server publish + client render path slows down, and a single
raw-visibility wait (default 30s, or explicit 20/60s) exhausts its budget. The spec already
mandates: "Test waits SHALL gate on deterministic state — polling the committed store view and
the surface DOM with a bounded deadline — rather than on the raw `#action-dock` element becoming
visible, so the suite stays stable under a loaded CI runner." Only the creation surface has been
converted so far; the rest still uses raw waits. Separately, the top-level contract
`test_browser_method_labels_preserve_exact_ownership` fails because
`CombatReconnectBrowserTest.test_confirmed_action_disconnect_shows_no_uncertain_notice` is not
registered in any shard manifest entry.

## Goals / Non-Goals

**Goals:**
- Make the browser suite stable under a loaded CI runner by converting ALL raw DOM-visibility
  waits in `web/tests/browser/` (the failing files, the shared helpers, and the raw waits in the
  currently-passing files such as `test_browser_shell.py`, `test_browser_input_narrative.py`,
  and `test_browser_pointer.py`) to a shared bounded deterministic-state gate that polls the
  committed store view and, where the assertion is genuinely DOM-bound, the surface DOM within one
  bounded deadline.
- Keep the exact journeys and assertions identical — only the wait strategy changes.
- Register the unregistered discovered method in the shard manifest so the top-level ownership
  contract passes.

**Non-Goals:**
- Not re-architecting per-test managed-server isolation (keep per-test server, fresh ports, no
  shared process state, per the harness spec).
- Not adding new journeys, fixtures, remote/LLM/image requests, or changing the two desktop
  viewports.
- Not globally inflating every timeout constant to mask slowness.
- Not touching the evennia (non-browser) shards, which are already green.

## Decisions

**Decision 1: One shared bounded deterministic-state wait helper with an optional DOM-readiness
predicate under a single monotonic deadline.**
Add `wait_for_store_state(page, predicate, dom_predicate=None, timeout=30000, interval_ms=250)`
to `browser_helpers.py`. It runs a Python-side bounded polling loop that reads the committed store
view via the existing `store_state_or_none` (which already tolerates a one-shot recovery reload
via `evaluate_tolerating_navigation`). A caller passes a small predicate over the store view
(e.g. `connected`, `mode`, `revision`, a panel's `available`). An optional `dom_predicate` is
evaluated in the SAME polling loop under one monotonic deadline, so the store gate and the
DOM-readiness gate share a single bounded window (no two-stage race, no double timeout budget).
`None` store states (mid-reload) are logged and polling continues (the store predicate is not
invoked on `None`); on timeout the helper raises an `AssertionError` carrying
`last_non_none_state`, `none_observed`, and the last evaluation error, plus (when a
`dom_predicate` is present) the relevant selector's connected/visible/enabled state and the
`activeElement`.

*Alternative considered:* keep per-call `page.wait_for_function` with longer explicit timeouts.
*Rejected:* that only delays the same slowness and still couples to a single raw render. The
bounded store-poll decouples the wait from render latency.

**Decision 2: Convert ALL raw DOM-visibility waits in `web/tests/browser/`, file by file.**
The scope is the whole managed browser tree, not just the currently-failing files, so the change
fully satisfies the "every test wait SHALL gate on deterministic state" requirement and does not
leave a residual population of raw waits that would still time out under load. Convert the
failing files (`test_browser_exploration.py`, `test_browser_services.py`, `test_browser_layout.py`,
`test_browser_reconnect.py`, `test_browser_art.py`, `test_vue_foundation.py`,
`test_vue_transport_mount.py`, `test_browser_options_surface.py`, `test_browser_choicepoints.py`,
`test_browser_combat_rejection.py`) AND the currently-passing files with raw waits
(`test_browser_shell.py`, `test_browser_input_narrative.py`, `test_browser_pointer.py`), plus the
shared helpers `wait_for_shell_active` and `focus_action_dock` in `browser_helpers.py`.

For `focus_action_dock` (a DOM focus operation) do NOT gate on the store predicate alone: gate on
the store state (connected + the dock panel available), then within the SAME bounded loop poll the
`#action-dock` DOM readiness (visible + focusable) via the optional `dom_predicate`, call
`locator.focus()`, and verify `document.activeElement` is the dock or its internal delegated focus
target. This avoids re-introducing the `null.focus()` failure mode.

*Alternative considered:* a global Playwright `default_timeout` increase. *Rejected:* it hides
slowness instead of decoupling the wait from render latency.

**Decision 3: Correlate action-result waits on a fresh revision/epoch.**
Where a journey waits for the result of a submitted action, record the pre-action epoch/revision
and require the store view to show the post-action revision (and the relevant panel/semantic
change) rather than only a loose `phase == "active"` or an already-satisfied value, so the wait
cannot succeed on a stale snapshot.

*Alternative considered:* a loose store predicate that may be true before the action is applied.
*Rejected:* it can pass on a stale snapshot and misattribute later failures.

**Decision 4: Register the missing method in the shard manifest.**
Add `web.tests.browser.test_browser_combat_rejection.CombatReconnectBrowserTest.test_confirmed_action_disconnect_shows_no_uncertain_notice`
to shard 3 `combat-rejection`'s `files_a` (or `files_b`), so every discovered method is in
exactly one process list. This is a one-line manifest fix that unblocks the top-level gate.

*Alternative considered:* remove the method. *Rejected:* it is a real behavior test; the
ownership contract requires it to be owned by a shard, not deleted.

## Risks / Trade-offs

- [Risk] A store-poll that only checks the store view may miss a DOM-specific assertion that
  the spec requires. → Mitigation: the helper's optional `dom_predicate` is evaluated in the same
  polling loop under one monotonic deadline, so the store gate and the DOM-readiness gate share a
  single bounded window (no two-stage race or double timeout budget).
- [Risk] `None` store state (mid-reload) — the polling loop treats a `None` read as "not ready
  yet," logs it, and continues; it does not invoke the store predicate on `None`. On timeout the
  error carries `last_non_none_state`, `none_observed`, and the last evaluation error so a reload
  that never completes is diagnosable.
- [Risk] Converting the shared helpers (`wait_for_shell_active`, `focus_action_dock`) changes
  timing for every journey that calls them, including the currently-passing shards (combat 1/2,
  pointer 9). → Mitigation: after the conversion, run a representative smoke set that covers the
  passing shards that use these helpers (a combat-dock smoke, a pointer-dock smoke, and a
  login-shell smoke), each within the 10-minute budget, and confirm all affected shards (both the
  originally-failing ones and the passing ones that share the helpers) are green in CI.
- [Risk] Adding the missing method to shard 3's process list changes that shard's worst-case run
  time (the method itself carries 30–60s waits plus a real reconnect). → Mitigation: run the full
  shard-3 process list under CI-equivalent parallel conditions and record the duration; if it
  approaches the shard budget, move one equally-independent class to a shard with headroom, while
  keeping each discovered method in exactly one process list.
- [Risk] The per-test managed-server boot is itself slow and still a load contributor. →
  Mitigation: out of scope here; the wait-gate change removes the dominant timeout source. A
  server-sharing change is a separate, later proposal.
- [Risk] A predicate that is too strict may time out if the store view field name is wrong. →
  Mitigation: predicates are written against the real committed store view field names, and the
  helper raises a descriptive `AssertionError` with the last observed state on timeout.

## Migration Plan

No data migration (0 released users). Deploy by merging the branch. Rollback by reverting the
branch. The manifest registration and wait conversions are additive/behavior-preserving, so
rollback restores the previous raw-wait behavior.

## Open Questions

- None blocking. Whether to later share the managed server across a shard (reducing per-test boot
  cost) is a follow-up proposal, not part of this change.
