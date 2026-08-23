## Why

The quality-gate browser **creation** shard (shard 4) has been failing on `master` since the
Vue SPA flip (`166d33d`): all six creation tests time out in `focus_action_dock` (a 60 s
wait for `#action-dock` to become visible). Two compounding root causes:

1. **The Vue port lost the creation dock flow.** The legacy webclient owned the creation
   keyboard journey in `creation_dock.js` + `creation_menu.js` (router-driven root/presets/
   confirm menus, confirmation screens, destructive-reset confirmation). The Vue SPA port
   never wired `creation_menu.js` into its store, and its overlay drops the confirmation
   screens (its own unit tests assert direct activation). The spec
   (`webclient-character-creation-ui`) requires keyboard-only preset selection →
   confirmation → activation and the destructive reset confirmation, and the browser tests
   assert them — so the creation shard cannot go green without porting that flow.
2. **The client never renders the creation dock.** In creation mode the `context_actions`
   panel is unavailable and no `suggestions` are present, so the Vue `ActionDock` `v-if`
   (`dockItems.length > 0 || !!suggestions`) is false and `#action-dock` is never rendered —
   the tests then wait a full minute and fail.

This change restores the creation dock as the sole `#action-dock` owner in creation mode,
ports the creation dock flow (keyboard menus + confirmation screens) into the Vue SPA
following the established combat-menu pattern, redesigns the creation browser tests to poll
deterministic state instead of gating on raw element visibility, fixes the pre-existing
browser-side JS syntax errors, and hardens the CI shard step against missing evidence files.

## What Changes

- **Web client (`web/webclient-app/AppClient.vue`):** render `ActionDock` in creation mode via
  a mode-gated clause (`store.view.mode === 'creation' && panelAvailable('creation')`), so
  `#action-dock` renders with `data-mode="creation"` in creation mode. The shared dock node
  persists on exploration (its `data-mode` switches to `exploration` when `context_actions`
  becomes available); the creation dock is the sole `#action-dock` owner in creation mode.
- **Creation dock port (`web/webclient-app/`):** add an ESM wrapper
  (`lib/creation_menu.js`) over the preserved `creation_menu.js` model and wire it into the
  Vue store following the combat-menu pattern (`45a27fc`): build the creation root/presets/
  confirm menus into the keyboard router when in creation mode, handle router submits
  (preset card → `creation.preset` with request-id correlation; activate/reset items →
  exact OOB dispatch; cancel/escape → one menu level, draft preserved), open the
  confirmation menu only after a successful save result, and expose the creation view stage
  in the committed store view. `CreationOverlay` gains the confirmation screens
  (`.creation-confirm`) and syncs its mode with the store-driven stage, so the destructive
  reset is always confirmed. The Vue unit tests are updated to assert the confirm-stage flow.
- **Browser creation tests (step-back redesign):** the managed Playwright creation tests
  exist to verify the character-creation journey end-to-end in a real Chromium against a
  real Evennia server, deterministically (no LLM / image services). Keep the shared
  `focus_action_dock` helper generic (31 non-creation call sites must not regress) and add a
  creation-only `focus_creation_action_dock` that, in a single bounded polling loop, waits
  until the creation surface is mounted, the store is in creation mode and unlocked, and
  exactly one visible `#action-dock` with `data-mode="creation"` exists, then focuses it.
  Also fix the pre-existing stray-`)` JS strings in the shard 4 creation journeys (the likely
  source of the CI `errors=1`). This keeps the suite satisfying the "keyboard-only and
  desktop-bounded" requirement robustly under a loaded CI runner.
- **CI robustness (`.github/workflows/quality-gate.yml`):** the browser-shard step waits on
  both background processes (`wait "$pid" || status=$?`), then copies/merges only the
  coverage and per-process evidence files that exist (warning when missing on a failed run);
  if either process failed the step exits with the real test status (status1 takes precedence,
  else status2); only when both processes succeeded does a missing coverage or evidence file
  become a clear infrastructure error. The artifact upload step uses `if: always()` and
  `if-no-files-found: warn` so coverage/evidence are retained for diagnosis on failure.

## Capabilities

### New Capabilities

(none.)

### Modified Capabilities

- `webclient-character-creation-ui`: the requirement "Creation browser acceptance is
  keyboard-only and desktop-bounded" is refined to mandate deterministic polling of
  store / creation-surface DOM state and bounded waits (no raw element-visibility gate),
  and to keep asserting the creation dock is the sole `#action-dock` owner in creation
  mode and re-renders on exploration.

## Impact

- `web/webclient-app/AppClient.vue` — the `ActionDock` render condition gains a
  mode-gated `creation` clause; the overlay receives the store-driven creation view stage.
- `web/webclient-app/lib/creation_menu.js` — new ESM wrapper over the preserved model.
- `web/webclient-app/stores/elosern.js` — creation menus wired into the keyboard router,
  save-result → confirmation handling, creation view stage exposed in the committed view.
- `web/webclient-app/components/CreationOverlay.vue` — confirmation screens
  (`.creation-confirm`), confirmed reset, mode sync with the store-driven stage.
- `web/webclient-app/tests/overlays/creation_overlay.test.js` — updated to the
  confirm-stage flow.
- `web/tests/browser/browser_helpers.py` — adds the creation-only
  `focus_creation_action_dock` helper (the shared `focus_action_dock` stays generic).
- `web/tests/browser/test_browser_creation.py` — the creation journeys are redesigned around
  the deterministic, bounded waits, and the pre-existing stray-`)` JS strings are fixed.
- `.github/workflows/quality-gate.yml` — the browser-shard step's evidence concatenation is
  made tolerant of a missing per-process evidence file; the artifact upload uses `if: always()`.
- Expected result: browser shard 4 (creation) goes green in CI.
- Verification is scoped to the creation shard tests only (not the full local suite), per
  the CI-based fix policy.
