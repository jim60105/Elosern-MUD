## 1. Client: restore the action-dock in creation mode

- [x] 1.1 In `web/webclient-app/AppClient.vue`, add a mode-gated creation clause to the
      `ActionDock` render condition:
      `v-if="dockItems.length > 0 || !!store.view.suggestions || (store.view.mode === 'creation' && panelAvailable('creation'))"`.
      The `:mode` prop already passes `store.view.mode`, so the dock renders with
      `data-mode="creation"` in creation mode. On exploration the shared dock re-renders as
      `data-mode="exploration"` when `context_actions` is available (the node may persist,
      not be fully removed).

## 2. Port the creation dock flow into the Vue SPA (true root cause)

The Vue SPA flip (`166d33d`) never ported the legacy creation dock
(`web/static/webclient/js/plugins/creation_dock.js` + `creation_menu.js`): the keyboard
router has no creation menu and the overlay has no confirmation screens. Shard 4 has been
failing since the flip. Port the flow following the combat-menu pattern (`45a27fc`).

- [x] 2.1 Add `web/webclient-app/lib/creation_menu.js`: an ESM wrapper over the preserved
      `web/static/webclient/js/elosern/creation_menu.js` (mirror the `combat_menu.js`
      wrapper; the UMD source and its Node gate are never edited).
- [x] 2.2 In `web/webclient-app/stores/elosern.js`, wire the creation menus into the
      keyboard router:
      - Maintain creation state (panel signature guard like combat): menus, view
        (root/presets/confirm/custom), pending save request id + preset key, confirm items.
      - When `mode === "creation"` and the creation panel is available, build
        `CreationMenu.buildMenus(panel)` and reset the router to the menu matching the
        stage: preset draft -> confirm items; custom/concept draft -> empty marker menu;
        else root menu.
      - Handle router events (mirror the legacy `handleItem`): `openSubmenu` presets/custom
        push the matching menu; an item with `presetKey` dispatches `creation.preset`
        (recording the request id); `creation.activate` / `creation.reset` items dispatch
        the exact OOB action; `cancel-` keys pop back to the previous view; escape pops one
        menu level (presets -> root, confirm -> presets/custom) without discarding the
        server draft.
      - On a new `lastActionResult` matching the pending save request id with
        `outcome === "success"`, open the confirmation menu (`CreationMenu.activateConfirm`);
        rejection/error stays on the current view and surfaces via `creation-form-message`.
      - Expose the creation view state (`view`, confirm items, pending preset key) in the
        committed store view so the overlay can render it.
- [x] 2.3 In `web/webclient-app/components/CreationOverlay.vue`, add the confirmation
      screens and keyboard flow:
      - Render `.creation-confirm` (title + 確認/返回 rows) when the store view reports the
        confirm stage; the router's confirm menu drives it (Enter confirms, Escape returns).
      - The destructive reset flow opens a confirmation first (no direct `creation.reset`
        dispatch); activate is gated on the confirm stage after a successful save.
      - Sync the overlay's mode from the store creation view (root/presets -> preset,
        custom -> custom, concept -> concept) so keyboard and pointer share one flow.
- [x] 2.4 Update the Vue unit tests (`web/webclient-app/tests/overlays/creation_overlay.test.js`)
      to assert the confirm-stage flow (activate only after confirmation, reset requires
      confirmation), matching the spec.

## 3. Redesign the creation browser tests (deterministic, bounded waits)

- [x] 3.1 In `web/tests/browser/browser_helpers.py`, ADD a creation-only helper
      `focus_creation_action_dock(page, timeout=30000)` that, in a single bounded polling
      loop (using the existing `evaluate_tolerating_navigation` / `store_state_or_none`
      pattern so a reconnect window is "not ready yet"), waits until ALL of the following hold:
      the committed store view reports `mode === 'creation'`, `connected`, not
      `mutationsLocked`; the creation surface DOM (`[data-testid="creation-overlay"]`) is
      mounted; and there is exactly one `#action-dock` element with `data-mode="creation"`
      that is visible. Then focuses it. Keep the shared `focus_action_dock` generic (31
      non-creation call sites must not regress).
- [x] 3.2 Update `web/tests/browser/test_browser_creation.py`: change the base-class
      `_focus_dock` (line ~171) to call `focus_creation_action_dock(page)` instead of
      `focus_action_dock(page)`. Note: this base helper is shared by ALL creation journeys
      (shard 3 `CustomCreationJourneys` / `ConceptCreationJourneys` and shard 5
      `ViewportCreationJourney` / `ReconnectPresetCreationJourney`), so the change is scoped
      to the creation file as a whole — verify with a Python compile check and the shard 4
      browser run.
- [x] 3.3 Fix the pre-existing stray-`)` JS strings in `test_browser_creation.py`
      (e.g. `document.querySelector('...')).focus()`), which are invalid JavaScript and the
      likely source of the CI `errors=1` once the dock mounts.

## 4. Harden the CI shard step

- [x] 4.1 In `.github/workflows/quality-gate.yml`, rewrite the "Run browser shard" step so
      that:
      - Both background processes are waited on with `wait "$pid" || status=$?` (no early
        exit under `set -e`); only after both `wait`s complete are evidence/coverage files
        read (no write race).
      - Coverage and per-process evidence files are copied/merged only when they exist
        (`test -f` guard, warning when missing on a failed run).
      - If either process failed, the step exits with the real test status (status1 takes
        precedence, else status2) rather than a `cat`/`cp` error.
      - Only when BOTH processes succeeded does a missing coverage or evidence file become a
        clear infrastructure error (`exit 1`).
- [x] 4.2 Add `if: always()` to the "Upload coverage and evidence artifacts" step so the
      coverage/evidence artifacts are retained for diagnosis on failure, and change
      `if-no-files-found` from `error` to `warn` so a missing-file error does not mask the
      real test failure.

## 5. Verify (CI-based, specific tests only — not the full local suite)

- [x] 5.1 Node unit tests: `node --test web/static/webclient/js/tests/*.test.js` plus the
      vitest overlay/action suites that cover the changed store and overlay.
- [x] 5.2 Python compile check: `uv run --locked python -m compileall -q web/tests/browser`
      (catches syntax issues introduced by the JS-string and helper edits without running the
      full suite).
- [x] 5.3 Run only the browser creation-shard tests locally (shard 4: `PresetCreationJourneys`,
      `ResetAndDraftJourneys`, `CreationDispatchJourneys`, `PointerCreationJourneys`,
      `ReconnectCreationJourney`), confirming they pass (Chromium + real Evennia server).
- [x] 5.4 Confirm the browser creation shard (shard 4) is green in CI.
