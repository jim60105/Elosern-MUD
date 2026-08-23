## Context

The quality-gate browser **creation** shard (shard 4) fails on `master` (CI run
`32628305589`, commit `82b8691`). All six creation tests fail in
`browser_helpers.focus_action_dock`, which waits 60 s for the `#action-dock` element to
become visible. In the captured store dump the session is `mode: 'creation'`, the
`creation` panel is available, but `context_actions` is unavailable and `suggestions` is
null.

Root cause (client): the Vue client renders `ActionDock` only when
`dockItems.length > 0 || !!store.view.suggestions`. In creation mode `dockItems` is empty
(the `context_actions` panel is unavailable by design) and there are no suggestions, so
the `v-if` is false and `#action-dock` is never mounted — the helper's 60 s wait times
out. The render condition was introduced by `a095192`; the `focus_action_dock` helper was
added later by `842c177` to stabilize a focus race, but did not restore the dock in
creation mode.

Deeper root cause (verified during implementation): shard 4 has been failing since the Vue
SPA flip (`166d33d`). The legacy webclient owned the creation keyboard journey in
`creation_dock.js` + `creation_menu.js` (router-driven root/presets/confirm menus and
confirmation screens); the Vue port never wired `creation_menu.js` into its store, and its
`CreationOverlay` drops the confirmation screens (its own unit tests assert direct
activation). The spec and the browser tests require the keyboard-only preset selection →
confirmation → activation journey and the destructive reset confirmation, so the flow must
be ported. A secondary CI defect: the shard step concatenates the per-process evidence
files with a bare `cat`, which aborts with `No such file or directory` when a failing
process never wrote its `.jsonl`.

## Goals / Non-Goals

**Goals:**
- Make browser shard 4 (creation) pass in CI.
- Restore the creation dock as the sole `#action-dock` owner in creation mode, torn down
  on exploration (the requirement the tests assert).
- Redesign the creation browser tests to be deterministic and robust under a loaded runner.
- Harden the shard step against a missing per-process evidence file.

**Non-Goals:**
- No backward-compatibility layers or data migrations (the project has zero released users).
- No changes to the deterministic creation service, the OOB `ui_action` protocol, or other
  browser shards (combat, exploration, services, etc.).
- Not a full local test-suite run; verification is scoped to the creation shard tests only.

## Decisions

### Decision 1 — Restore the action-dock in creation mode (client fix)

**Choice:** Add a mode-gated creation clause to the `ActionDock` render condition in
`AppClient.vue`:
```
v-if="dockItems.length > 0 || !!store.view.suggestions ||
      (store.view.mode === 'creation' && panelAvailable('creation'))"
```
**Rationale:** The spec (`webclient-character-creation-ui`) requires that "the creation
dock is the sole action-dock owner in creation mode and is torn down on exploration." The
client regressed by gating the dock on `context_actions`/`suggestions` only, so in
creation mode the dock (and its `#action-dock` element) disappeared. The clause is gated on
`mode === 'creation'` so a stale snapshot that still advertises the creation panel while the
shell has moved to exploration does not keep an empty creation dock.

**Teardown contract (review adjustment):** `ActionDock` is the single shared dock element
for exploration/combat/creation. On a successful activation the shell hands off to
exploration and `context_actions` becomes available, so the *same* `#action-dock` node stays
in the DOM with `data-mode` switching to `exploration`. The contract is therefore: in
creation mode there is exactly one dock with `data-mode="creation"`; after activation there
is no creation-mode dock (the shared dock re-renders as exploration when `context_actions`
is available). Tests must NOT assert the shared DOM node is fully removed.

**Alternatives considered:**
- *Test-only fix (wait for the `.creation-*` surface instead of `#action-dock`):* would
  let the tests pass without the dock, but then the spec assertion "the creation dock is
  the sole action-dock owner in creation mode" becomes untestable — the element must exist.
  Rejected: the client contract is authoritative.
- *Render the dock unconditionally (drop the v-if):* would show an empty dock in modes
  that should hide it. Rejected: other shards (shell, layout) rely on the dock being
  conditional.

### Decision 2 — Port the creation dock flow into the Vue SPA

**Choice:** Follow the established combat-menu pattern (`45a27fc`) to wire the preserved
`creation_menu.js` model into the Vue store, and add the confirmation screens to
`CreationOverlay`:

- Add `web/webclient-app/lib/creation_menu.js`, an ESM wrapper over the preserved
  `web/static/webclient/js/elosern/creation_menu.js` (never edited, exactly like
  `combat_menu.js`).
- In `stores/elosern.js`, keep creation state (menu signature guard like combat), build
  `CreationMenu.buildMenus(panel)` when `mode === "creation"` and the panel is available,
  and reset the router to the stage-matching menu: a preset draft resumes the confirmation
  items, a custom/concept draft resumes an empty marker menu (the form owns its keys), and
  no draft starts at the root menu (預設角色 / 自訂角色 / 概念).
- Router events mirror the legacy `handleItem` and `onRouterEvent` of `creation_dock.js`:
  `openSubmenu` items push the matching menu; a preset card dispatches `creation.preset`
  with the exact payload and records the request id; `creation.activate` /
  `creation.reset` items dispatch exactly once; `cancel-` keys and Escape pop exactly one
  menu level (presets → root, confirm → the exact stage the confirmation was opened from,
  remembered as `returnStage`) without discarding the server draft.
- A new `lastActionResult` matching the pending save request id with `outcome ===
  "success"` opens the confirmation menu (`CreationMenu.activateConfirm`); rejection stays
  on the current view and surfaces through the existing `creation-form-message`.
- Expose the creation view stage (view name, confirm items, pending preset key) in the
  committed store view; `CreationOverlay` renders `.creation-confirm` and syncs its mode
  from that stage, so the destructive reset is always confirmed and pointer and keyboard
  share one flow.
- Update the Vue unit tests (`creation_overlay.test.js`) to assert the confirm-stage flow
  (activation only after confirmation; reset requires confirmation).

**Rationale:** The spec requires the keyboard-only journey and both confirmations; the
browser tests encode them; the legacy implementation is the reference. Porting on the
combat pattern keeps the router as the single focus owner (design D4) and keeps the
preserved model authoritative.

**Alternatives considered:**
- *Update the browser tests to the current pointer design (no confirm screens):* would
  contradict the spec's "keyboard-only ... confirmation" and "destructive reset
  confirmation" requirements. Rejected: the spec is the contract.
- *Reimplement the keyboard flow inside `CreationOverlay` (local state, bypassing the
  router):* would fork the single focus owner and break the router-current-menu contract
  the browser tests assert. Rejected: keep the store-owned router.

### Decision 3 — Redesign the creation browser tests (step-back analysis)

**Keep the shared helper generic; add a creation-specific gate (review adjustment):**
`focus_action_dock` is used by 31 call sites across the combat, pointer, shell, services,
exploration, art, options, input-narrative, choicepoints, and actions tests. It must keep
its generic non-creation semantics. Add a creation-only helper `focus_creation_action_dock`
that, in a single bounded polling loop (reusing the `evaluate_tolerating_navigation` /
`store_state_or_none` pattern so a reconnect window is treated as "not ready yet"), waits
until ALL of the following hold before focusing: the committed store view reports
`mode === 'creation'`, `connected`, not `mutationsLocked`; the creation surface
(`[data-testid="creation-overlay"]`) is mounted; and there is exactly one `#action-dock`
element with `data-mode="creation"` that is visible. The combined gate (not a separate
`wait_for_creation_surface` then a separate dock assertion) avoids a Vue mount race between
the surface and the dock. The base-class `_focus_dock` in `test_browser_creation.py` is
shared by all creation journeys (shard 3 and 5 included), so the change is scoped to the
whole creation file and verified with a Python compile check plus the shard 4 run.

**Also fix the existing browser-side JS syntax errors (review adjustment):** many
`page.evaluate`/`wait_for_function` JS strings in `test_browser_creation.py` carry a stray
`)` (e.g. `document.querySelector('...')).focus()`), which are invalid JavaScript. These are
currently masked by the shared dock timeout; once the dock mounts, several journeys would
throw a browser SyntaxError (the likely source of the `errors=1`). Fix every unbalanced JS
string in shard 4 and add an explicit task to run the shard 4 creation journeys to catch the
regressions.

**What the tests are for:** the managed localhost Playwright creation tests verify the
character-creation journey end-to-end in a real Chromium against a real Evennia server.
They drive keyboard-only creation flows (preset selection → confirmation → activation →
exploration hand-off, the custom form, reconnect at saved stages, viewport checks at
1440x900 and 1280x720), are fully deterministic (no live LLM, Stable Diffusion, or other
network services), and assert the exact `creation.*` OOB mutations that cross the wire.

**The governing requirement** (`webclient-character-creation-ui::creation-browser-acceptance-is-keyboard-only-and-desktop-bounded`):
the suite SHALL exercise these journeys with deterministic fixtures, make no remote/LLM/
image request, assert the creation dock is the sole `#action-dock` owner in creation mode
and is torn down on exploration, and assert no persona/import field is rendered.

**Current design weakness:** `focus_action_dock` gates on the raw `#action-dock` element
becoming visible with a fixed 60 s timeout. Under a loaded CI runner the element may be
slow to mount, or the runner may be slow, so the fixed visibility wait times out. The
redesign keeps the test's *intent* (focus the dock before keyboard driving) but replaces
the brittle element-visibility gate with **bounded polling of deterministic state**:
- Poll the committed store view (via the `__elosernBridge` hook) and the creation-surface
  DOM (`.creation-*` elements) with a bounded deadline, then focus the dock only once the
  creation surface is confirmed mounted.
- Keep waits bounded (e.g., 30 s) and make failures diagnosable (include a store snapshot
  on timeout), matching the existing `store_state_or_none` / `wait_for_presentation_settled`
  pattern already used by the sibling browser tests.

**Why this satisfies the requirement:** the tests still prove the creation dock owns the
action-dock in creation mode (now that the client renders it) and prove the desktop-bounded
keyboard journeys, while the deterministic polling keeps them stable on a loaded runner —
no live services, no flaky raw-visibility gate.

### Decision 4 — Harden the CI shard step (status + evidence/coverage + artifact upload)

**Choice:** in `.github/workflows/quality-gate.yml`, the "Run browser shard" step:
1. Waits on both background processes with `wait "$pid" || status=$?` so a non-zero status
   does not abort the step under `set -e`; only after BOTH `wait`s complete are files read
   (no write race with the still-running processes).
2. Copies/merges only the coverage and per-process evidence files that exist (a `test -f`
   guard, warning when missing on a failed run).
3. If either process FAILED, the step exits with the real test status — status1 takes
   precedence, else status2 (not a `cat`/`cp` error). Only when BOTH processes SUCCEEDED does
   a missing coverage or evidence file become a clear infrastructure error (exit 1), so a
   missing file on a successful run is not silently swallowed.

**Rationale:** the shard step should report the real test failure, not mask it behind a
missing-file `cat`/`cp` error, while still surfacing an evidence/coverage-infrastructure
problem when the run succeeded.

**Artifact upload (review adjustment):** set the browser shard's artifact-upload step to
`if: always()` so the coverage/evidence artifacts are retained even when the test step fails,
and change `if-no-files-found` from `error` to `warn` so a missing-file error does not mask
the real test failure (the "Run" step already reports the real status).

## Risks / Trade-offs

- [Risk] Adding the `creation` clause renders an (possibly empty) `DockMenu` frame in
  creation mode → Mitigation: the dock's guidance line always renders; the `CreationOverlay`
  carries the preset cards and custom form, so an empty menu frame is acceptable and matches
  the "sole owner" contract.
- [Risk] Redesigning the creation test waits could shift which assertions run in CI →
  Mitigation: only the creation-shard tests change; verify by running just the shard 4
  creation tests locally (per the CI-based fix policy), not the full suite.
- [Risk] Changing the shared `focus_action_dock` would regress the other 30 non-creation call
   sites → Mitigation: keep `focus_action_dock`'s generic behavior; add a creation-only
   `focus_creation_action_dock` used solely by the creation journeys.
- [Risk] Once the dock mounts, the pre-existing stray-`)` JS strings in the creation tests
  throw a browser SyntaxError (the likely `errors=1`) → Mitigation: fix every unbalanced JS
  string in shard 4 and run the shard 4 creation journeys to confirm.
- [Known pre-existing, out of scope] The shard-3/5 creation journeys
  (`CustomCreationJourneys`, `ConceptCreationJourneys`, `ViewportCreationJourney`) still fail
  at deeper Vue-port gaps the remap missed: the overlay fields carry `data-testid` but no
  `id` (the Tab-focus assertions read `document.activeElement.id`), the legacy
  `.creation-control` class is absent, and the concept field is a separate mode tab rather
  than a custom-form sub-state. These were failing (dock timeout) before this change and are
  owned by other failing shards; this change scopes to shard 4 (all 12 creation-shard tests
  verified green locally).
- [Trade-off] Bounded 30 s deterministic polling vs a 60 s raw visibility wait — bounded
  polling is more deterministic and yields a diagnosable store snapshot on failure.

## Migration Plan

No data migration (zero released users). The client, test, and CI changes land as one
change. Rollback is a single `git revert`. Verify by running the creation-shard tests
locally (Chromium + real Evennia server), then confirm CI shard 4 is green.

## Open Questions

- None blocking. The `suggestions` clause is kept for the non-creation modes that rely on
  it; only the creation clause is added.
