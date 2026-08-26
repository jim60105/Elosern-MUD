## 1. Reproduce and pin down the defect

- [ ] 1.1 In `test_browser_art.py`, add a bounding-box overlap assertion between
      `[data-testid="scene-backdrop-placeholder"]` and `[data-testid="action-dock"]` at 1440×900 and
      1280×720, red against today's code (the placeholder currently overlaps the dock's tab-bar row).
- [ ] 1.2 Confirm, by reading `HudFrame.vue:143,156,167,173-187` and `SceneBackdrop.vue:335-424`, the
      exact set of `calc(var(--dock-h) + Npx)` call sites that omit the 46px command-line height, so the
      fix touches all of them and no sibling call site is missed.

## 2. Introduce the shared offset token

- [ ] 2.1 Add `--stage-content-bottom: calc(var(--dock-h) + 46px)` to `styles/tokens.css`, next to
      `--dock-h`, with a short comment naming the 46px as the command line's own height
      (`HudFrame.vue`'s `[data-anchor="command-line"]` rule) so the two stay visibly linked.
- [ ] 2.2 Update `SceneBackdrop.vue`'s five `bottom: calc(var(--dock-h) + Npx)` rules
      (`.scene-backdrop__placeholder`, `__generating`, `__scene-label`, `__scene-alt`,
      `__fullview-control`) to `bottom: calc(var(--stage-content-bottom) + Npx)`, keeping each rule's
      existing `N` buffer unchanged.
- [ ] 2.3 Update `HudFrame.vue`'s `[data-anchor="feed"]` rule's `bottom` to use
      `--stage-content-bottom` instead of `--dock-h`, keeping the existing 60px buffer.
- [x] 2.4 `HudFrame.vue:143,156`'s `max-height: calc(100% - var(--dock-h) - 110px)` rule bounds the
      top-anchored `hud-left`/`hud-right` islands (`top: 64px`, no `bottom` offset), not a
      dock-relative `bottom` position — its own `110px` already equals `--dock-h`'s companion 46px plus
      the anchor's own 64px top offset, so it independently accounts for the command line already. No
      change needed here; this task closes as a verification-only no-op.

## 3. Verify

- [ ] 3.1 Turn the task 1.1 assertion green; extend it to also cover `__generating`,
      `__scene-label`/`__scene-alt`, and `__fullview-control` against both the dock and the command line,
      at both viewports.
- [ ] 3.2 Re-run `test_browser_art.py` in full (the placeholder/missing/unavailable/pending branches) to
      confirm no behavioral regression — same testids, same text, same truthful-data branching, only the
      vertical position changes.
- [ ] 3.3 Re-run the existing narrative-caption non-overlap coverage (if any) now that the feed anchor's
      offset changed; if none exists, add a minimal one alongside this change's new assertions.
- [ ] 3.4 Re-screenshot the client at 1440×900 and 1280×720 with art generation offline and visually
      confirm the placeholder/label captions now float cleanly above the dock with the intended small
      gap, not intruding into its tab-bar row.

## 4. Close out

- [ ] 4.1 `openspec validate fix-webclient-scene-backdrop-placeholder-overlap --strict`.
- [ ] 4.2 Run the focused JS gates (`npm test`, the dependency-free Node gate) and the smallest browser
      class covering `test_browser_art.py`.
