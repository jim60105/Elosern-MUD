## 1. Reproduce and pin down the defect

- [x] 1.1 In `test_browser_art.py`, add a bounding-box overlap assertion between
      `[data-testid="scene-backdrop-placeholder"]` and `[data-testid="action-dock"]` at 1440×900 and
      1280×720, red against today's code (the placeholder currently overlaps the dock's tab-bar row).
      Verified: with the pre-fix offset the placeholder's bottom sits ~34px below the dock's top edge at
      both viewports (704 vs 670 at 1440×900; 549.6 vs 515.6 at 1280×720) — the assertion is red; after
      the token fix it is green.
- [x] 1.2 Confirm, by reading `HudFrame.vue:143,156,167,173-187` and `SceneBackdrop.vue:335-424`, the
      exact set of `calc(var(--dock-h) + Npx)` call sites that omit the 46px command-line height, so the
      fix touches all of them and no sibling call site is missed.
      Confirmed: exactly the five `SceneBackdrop.vue` caption rules and the `HudFrame.vue` feed rule consume
      `--dock-h` for a dock-relative `bottom`; the `max-height` rules (143/156) are top-anchored islands and
      already account for the command line; the dock's `bottom` and the command line's `height` literals were
      tokenized (task 2.3).

## 2. Introduce the shared offset token

- [x] 2.1 Add `--command-line-h: 46px` and `--stage-content-bottom: calc(var(--dock-h) +
      var(--command-line-h))` to `styles/tokens.css`, next to `--dock-h`, with short comments linking
      the token to the command line's own height (`HudFrame.vue`'s `[data-anchor="command-line"]` rule)
      and to the dock's real top edge.
- [x] 2.2 Update `SceneBackdrop.vue`'s five `bottom: calc(var(--dock-h) + Npx)` rules
      (`.scene-backdrop__placeholder`, `__generating`, `__scene-label`, `__scene-alt`,
      `__fullview-control`) to `bottom: calc(var(--stage-content-bottom) + Npx)`, keeping each rule's
      existing `N` buffer unchanged.
- [x] 2.3 Update `HudFrame.vue`'s `[data-anchor="feed"]` rule's `bottom` to use
      `--stage-content-bottom` instead of `--dock-h`, keeping the existing 60px buffer; additionally
      tokenized the dock's `bottom: 46px` and the command line's `height: 46px` to consume
      `--command-line-h` (computed layout unchanged).
- [x] 2.4 `HudFrame.vue:143,156`'s `max-height: calc(100% - var(--dock-h) - 110px)` rule bounds the
      top-anchored `hud-left`/`hud-right` islands (`top: 64px`, no `bottom` offset), not a
      dock-relative `bottom` position — its own `110px` already equals `--dock-h`'s companion 46px plus
      the anchor's own 64px top offset, so it independently accounts for the command line already. No
      change needed here; this task closes as a verification-only no-op.
- [x] 2.5 Expose the SceneBackdrop handle for the managed-browser pending-scene journey: add a
      `sceneBackdropRef` template ref to `AppClient.vue` (registered onto the bridge in `onMounted`) and a
      `backdrop: null` property on the `window.__elosernBridge` object in `main.js` (the bridge object is
      created *before* `app.mount()`, because AppClient's `onMounted` fires during mount). A plain property,
      not a getter — `app._instance` is dev-only in Vue's production build, so the registration approach
      works in every build. Tests then call `setPriorImage` deterministically.

## 3. Verify

- [x] 3.1 Turn the task 1.1 assertion green; extend it to also cover `__generating`,
      `__scene-label`/`__scene-alt`, and `__fullview-control` against both the dock and the command line,
      at both viewports.
      The captions are asserted in `ArtMissingSceneTest` (placeholder/label/alt/control + the narrative
      feed), and the pending generating-notice is asserted in `ArtPendingSceneTest` via the bridge hook
      (`setPriorImage` seeded with the fixture's valid PNG as a data URL). All green at both viewports.
- [x] 3.2 Re-run `test_browser_art.py` in full (the placeholder/missing/unavailable/pending branches) to
      confirm no behavioral regression — same testids, same text, same truthful-data branching, only the
      vertical position changes.
      Full file: 14 tests, OK in ~500s (within the 10-minute local budget).
- [x] 3.3 Re-run the existing narrative-caption non-overlap coverage (if any) now that the feed anchor's
      offset changed; if none exists, add a minimal one alongside this change's new assertions.
      Re-ran `test_browser_contextual_hud.py::test_command_line_never_overlaps_dock_caption_or_hud` — OK in
      ~35s; the new missing-scene test also asserts the narrative feed's bottom edge clears the dock's top
      edge at both viewports.
- [x] 3.4 Re-screenshot the client at 1440×900 and 1280×720 with art generation offline and visually
      confirm the placeholder/label captions now float cleanly above the dock with the intended small
      gap, not intruding into its tab-bar row.
      Screenshots captured (missing-scene state, art offline) at /tmp/opencode/scene_backdrop_1440x900.png
      and /tmp/opencode/scene_backdrop_1280x720.png; the geometric assertions in 3.1/1.1 confirm the
      captions float above the dock's top edge and the command line's top edge.

## 4. Close out

- [x] 4.1 `openspec validate fix-webclient-scene-backdrop-placeholder-overlap --strict`.
      Valid.
- [x] 4.2 Run the focused JS gates (`npm test`, the dependency-free Node gate) and the smallest browser
      class covering `test_browser_art.py`.
      `npm test` (363 tests, 52 files — all pass), the Node gate `node --test web/static/webclient/js/tests/*.test.js`
      (324 tests — all pass), plus `npm run build` / `npm run build-storybook` / `npm run showcase-coverage`
      (40/40 components covered). Smallest browser classes: `ArtMissingSceneTest` + `ArtPendingSceneTest`
      (the pending class green; the full `test_browser_art.py` file also re-run, 14 tests OK).
