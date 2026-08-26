## 1. Z-index scale (tokens.css)

- [x] 1.1 In `web/webclient-app/styles/tokens.css`, add `--z-surface-modal: 3000;` and `--z-offline: 9000;`
      to the `:root` block (near `--dock-h`), with a one-line comment stating the invariant: every
      full-screen surface consumes `--z-surface-modal` (or a value derived from it); nothing but the
      offline overlay may exceed `--z-offline`.

## 2. Consume the scale (mechanical rename, no value changes)

- [x] 2.1 `web/webclient-app/components/HudDrawer.vue`: change `.hud-drawer-scrim`'s `z-index: 2900` to
      `z-index: calc(var(--z-surface-modal) - 100)` and `.hud-drawer`'s `z-index: 3000` to
      `z-index: var(--z-surface-modal)`.
- [x] 2.2 `web/webclient-app/components/ArtPanel.vue`: change `.art-panel__fullview`'s `z-index: 3000`
      to `z-index: var(--z-surface-modal)`.
- [x] 2.3 `web/webclient-app/components/SceneBackdrop.vue`: change `.scene-backdrop__fullview`'s
      `z-index: 3000` to `z-index: var(--z-surface-modal)`.
- [x] 2.4 `web/webclient-app/components/FullLogOverlay.vue`: change its root's `z-index: 3000` to
      `z-index: var(--z-surface-modal)`.
- [x] 2.5 Confirm (do not change) `web/webclient-app/components/OverlayHost.vue` stays at `z-index: 92`
      — out of scope per design.md D1 (drawer/overlay are mutually exclusive at the store level; folding
      it into the shared tier is unrelated risk this change doesn't need to take on).

## 3. Raise the offline overlay above the scale

- [x] 3.1 `web/webclient-app/components/AppShell.vue`: change `#elosern-offline-overlay`'s
      `z-index: 2000` to `z-index: var(--z-offline)`.

## 4. Tests

- [x] 4.1 Add a real-browser test to `web/tests/browser/test_browser_reconnect.py` (the file that
      already exercises `#elosern-offline-overlay`'s appearance/visibility on disconnect), decorated
      with `@covers_requirement("webclient-desktop-shell::connection-loss-locks-stale-controls")`
      (following the pattern already used by `test_offline_locking_no_retry_and_uncertain_notice` in
      that file). The test SHALL: open a reference drawer (or the full-log overlay — whichever is
      simplest to trigger deterministically from the logged-in page fixture), disconnect the transport
      via the existing `_disconnect_transport` helper, wait for the offline overlay to become visible,
      then assert via `page.evaluate` + `document.elementFromPoint(x, y)` (at a point known to lie
      inside both the open surface and the offline overlay, e.g. near viewport center) that the
      topmost element at that point is the offline overlay or one of its descendants, not the open
      surface. This is the test that actually proves the fix and the only place
      `tools/spec_traceability.py` can register coverage for the delta spec's two new scenarios (it
      discovers coverage exclusively via `@covers_requirement` on `test_*.py` files; a JS/Vitest test is
      invisible to it).
- [x] 4.2 Add a fast, source-level unit check (in `tests/preserved_contract.test.js` or a new focused
      test file under `tests/`) as a cheap first line of defense, NOT as the requirement's coverage of
      record: read the raw CSS from `AppShell.vue`, `HudDrawer.vue`, `ArtPanel.vue`, `SceneBackdrop.vue`,
      and `FullLogOverlay.vue`, and assert (a) `#elosern-offline-overlay`'s z-index declaration
      references `--z-offline`; (b) each of the four surfaces' modal z-index declaration references
      `--z-surface-modal` (directly or via the drawer scrim's `calc(...)`); and (c) in
      `styles/tokens.css`, the numeric value bound to `--z-offline` is strictly greater than the
      numeric value bound to `--z-surface-modal`. This cannot prove real paint order (jsdom has no
      layout/paint engine) — task 4.1's real-browser test is what proves the fix.
- [x] 4.3 Run the existing `tests/preserved_contract.test.js` and `tests/app.test.js` (or the project's
      full webclient-app unit suite) to confirm the DOM-ID contract and the offline-overlay
      `data-visible` toggle behavior are unaffected by the rename.

## 5. Documentation corrections

- [x] 5.1 In `docs/superpowers/specs/2026-08-02-webclient-ui-design.md` §5.1, remove ONLY the sentence
      "Players may resize the stage anchors." Do NOT remove the rest of that paragraph — "The saved
      layout configuration (the Vue layout store) includes a project layout version. When required
      component names or layout structure change, known old versions are migrated. An unrecognized
      version is reset to the approved default. The action dock, connection state, and command-line
      entry point cannot be removed by a stale localStorage layout." is still accurate: it is
      implemented by `web/static/webclient/js/elosern/layout_store.js` (loaded by `main.js` on every
      mount), tested by `web/tests/browser/test_browser_layout.py`
      (`test_known_layout_version_persists_across_reload`,
      `test_migration_registry_migrates_known_prior_version`), and required verbatim by this same
      capability's own binding "Browser persistence is versioned and presentation-only" requirement
      (`openspec/specs/webclient-desktop-shell/spec.md`). Only the anchor-resizing claim is stale; the
      version/migration/reset behavior is real and must stay documented. Reread the surviving sentences
      once the first is removed to confirm the paragraph still reads coherently on its own.
- [x] 5.2 In the same document's §5.3, reword "`/` opens and focuses the command drawer" to describe the
      shipped behavior accurately: the command line is a permanently-present field with no open/closed
      state; `/` moves focus into it (matching `webclient-desktop-shell`'s "Keyboard routing is
      menu-first and submission-safe" and "The command drawer preserves ordinary text control"
      requirements, and `AppShell.vue`'s `focusCommandField`/mode-watcher contract). Do not change any
      other sentence in §5.3.

## 6. Verification

- [x] 6.1 Run the full webclient-app test/lint suite (whatever this repo's standard command is, e.g.
      `npm test` / `npm run lint` under `web/webclient-app/`) and confirm green.
- [x] 6.2 Run `uv run --locked python -m tools.spec_traceability check` and confirm it passes. Note its
      actual scope precisely: the tool discovers coverage only through `@covers_requirement(...)` on
      Python `test_*.py` files, at requirement-heading granularity (not per-scenario), so a green run
      confirms the `webclient-desktop-shell::connection-loss-locks-stale-controls` requirement still has
      a covering test — it does not by itself prove the two new stacking-guarantee scenarios are
      exercised. That proof comes from task 4.1's real-browser test actually existing and passing;
      confirm task 4.1 is done and its test passes before relying on this check.
- [x] 6.3 Manually sanity-check in a running client (or via the existing Storybook stories for
      `HudDrawer`, `MapOverlay`/`SettingsOverlay`/`HelpOverlay`, and `FullLogOverlay`) that nothing looks
      visually different — the rename must be a no-op for every surface except the offline overlay.
