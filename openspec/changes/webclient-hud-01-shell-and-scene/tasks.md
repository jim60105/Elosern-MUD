## 1. Freeze the preserved contract before any DOM moves

- [x] 1.1 Enumerate the identifiers this change must not move (`#action-dock` with its `data-mode`, `tabindex` and listbox composite role, `#elosern-action-live`, `#elosern-offline-overlay`, `#inputfield`, `#narrative-unread`, `data-testid="narrative-feed"`, `data-testid="command-drawer"`, `data-testid="action-dock"`, the `action-*` / `target-*` item keys) and record them in the change as the H1 preserved list
- [x] 1.2 Add a Vitest suite asserting every preserved identifier is present after the shell restructure, so a regression fails at the unit gate rather than in the browser suite
- [x] 1.3 Grep `web/tests/browser/` for the selectors this change relocates and list them in the change; they are re-mapped in group 8
- [x] 1.4 Add a mounted-`AppClient` integration test: in exploration / combat / creation, `#action-dock` is present and focusable, and the representative `action-*` / `target-*` item keys remain intact (slot re-homing must not break the listbox composite contract)

## 2. Stage tokens and the shell frame

- [x] 2.1 Add the per-mode stage gradients, the inset vignette, and the `menu-open` recession to `styles/tokens.css`, all expressed through the existing `--motion-*` tokens so the reduced-motion block already covers them
- [x] 2.2 Add the `[data-lowhp="true"]` and combat-pulse CSS hooks (state supplied by H2) and bind `elosern-combat-pulse` to the combat stage
- [x] 2.3 Rewrite `components/AppShell.vue`: replace the four-row grid and its `300px 1fr 300px` main row with a `position:relative; overflow:hidden` stage plus named anchors (`hud-left`, `hud-right`, `feed`, `dock`, `command-line`), sized from `--dock-h`
- [x] 2.4 Move the existing left/right panel slots into the `hud-left` / `hud-right` anchors unchanged — no panel's own markup or CSS is edited in this change
- [x] 2.5 Update `styles/app-shell.css` so the mount container carries the stage's height chain with no page-level scrollbar
- [x] 2.6 Define each anchor's bounded rectangle (the island stacks scroll internally; the right stack is bounded above the dock + caption reserved space) and verify at both 1440x900 and 1280x720 that no anchor's box intersects another's (browser acceptance in group 8)
- [x] 2.7 Host the visible command-line surface (the `CommandDrawer` entry control) in the `command-line` anchor — visible in exploration and combat, hidden in creation — so the H1 matrix's "command line: visible" requirement holds; H5 later upgrades the chrome to the always-visible field

## 3. Mode-gated visibility

- [x] 3.1 Implement the mode × surface matrix as CSS on `[data-elosern-mode]` using `display:none`, covering exploration / combat / creation for the narrative caption, the HUD island stack, the minimap anchor, the action dock, and the command line
- [x] 3.2 Move focus to `#action-dock` before a mode change removes the surface holding focus, reusing the existing focus-restore path rather than adding a second one
- [x] 3.3 Vitest: the minimap anchor is absent from the DOM in combat and present again in exploration; a focused element inside a hidden-by-mode surface loses focus to the dock, not to the body
- [x] 3.4 Vitest: no mode-hidden surface remains in the tab order
- [x] 3.5 Extract a side-effect-free `restoreDockFocus()` helper (the existing `dock.focus()` path, without the drawer-close side effects) and call it in the mode watcher's pre-update phase: if `document.activeElement` is inside an anchor the incoming mode will hide, focus the dock **before** the CSS hides the surface; test the feed, the HUD stacks, the `CommandDrawer`, and the `FullLogOverlay` cases

## 4. Scene backdrop

- [x] 4.1 Add `components/SceneBackdrop.vue` reading the committed `art` panel: `done` → cover-cropped image; pending with a prior image → prior image dimmed with the `目前場景圖片生成中` label; missing / failed / invalid / pending-without-prior / panel unavailable → mode gradient with the truthful placeholder label
- [x] 4.2 Render the scene label, alternative text and placeholder label as text on the stage, outside the bitmap, with a stable `data-testid` hook for the placeholder
- [x] 4.3 Mount `SceneBackdrop` as the lowest stage layer in `AppClient.vue`
- [x] 4.4 Storybook story with deterministic offline args for every scene status (done / pending-with-prior / pending-without-prior / missing / failed / unavailable) and both stage modes
- [x] 4.5 Vitest: no invented URL in any degraded state; the prior image is never presented as current; exactly one placeholder node in the degraded states
- [x] 4.6 Migrate the scene full-view contract onto the backdrop: the scene control opens the full-screen view on click or Enter and closes on Escape with focus restored (the MODIFIED `webclient-art-panel` keyboard-first requirement, now owned by the backdrop instead of the removed panel frame)
- [x] 4.7 Handle the `<img>` load-failure path: an error on the `done` URL degrades to the mode gradient + the single truthful placeholder, and the failed URL is remembered so it is not re-fetched before a reload (the `imageLoadFailed` behaviour migrated from `ArtPanel`)
- [x] 4.8 Reduce `ArtPanel` to its portrait-catalog section only (the scene frame is superseded by `SceneBackdrop`); the unmodified portrait requirements survive in the panel: catalog focus flow, the missing-image placeholder, the portrait's own full-view control, and literal rendering of HTML-like labels

## 5. Narrative caption and the full log

- [x] 5.1 Bound `components/NarrativeFeed.vue` to the caption geometry (`width:min(880px,90vw)`, bounded height, panel chrome with backdrop blur) and keep `#narrative-unread`, its live region and its jump-to-latest behaviour unchanged
- [x] 5.2 Add the caption's labelled full-log control
- [x] 5.3 Add `components/FullLogOverlay.vue`: the complete retained narrative rendered through the existing `narrative-renderer.js` (no second markup path), scrollable, focus-trapped, Escape-closing, restoring focus to the opener
- [x] 5.4 Mount `FullLogOverlay` from `AppClient.vue` and wire the caption control to it
- [x] 5.5 Storybook stories for the caption card (short / overflowing / with unread) and the full-log overlay
- [x] 5.6 Vitest: the caption never grows past its bounded height; the overlay renders the same line count as the store's retained narrative; Escape restores focus to the opener
- [x] 5.7 Drive the stage's `menu-open` recession from a single reactive open-surface registry — the `CommandDrawer`, the `FullLogOverlay`, and the `CreationOverlay` (H4's drawers will plug in later); the recessed mark clears only when no open surface remains
- [x] 5.8 On a mode transition into creation, close any open `FullLogOverlay` (a non-creation surface must not persist into creation) and route focus to the action dock through the group-3 rescue path

## 6. Brand and top-meta

- [x] 6.1 Split `components/TopBar.vue` into the top-left brand element (game name, preserving the `webclient-login-gate` brand surface) and the top-right meta pill (location · world date/time · connection state with the ok-green dot plus label)
- [x] 6.2 Anchor both on the stage; the wallet is deliberately not added here (it belongs to H2's island stack)
- [x] 6.3 Storybook story and Vitest for connected / offline / missing-location states

## 7. Manifest and showcase gate

- [x] 7.1 Add `Core/SceneBackdrop`, `Core/HudFrame`, `Core/FullLogOverlay` to `component-manifest.json`
- [x] 7.2 Run `npm run build-storybook` and `npm run showcase-coverage`; both must pass with the extended set
- [x] 7.3 Extend `tests/overlays/deferred_surfaces_absent.test.js` to assert the stage reserves no anchor for a companion strip, a toast queue, or a persistent objective tracker

## 8. Browser acceptance and re-map

- [x] 8.1 Re-map `test_browser_layout.py` off the column-structure walk onto the stage anchors' `data-testid` hooks, and delete the stale GoldenLayout-shaped `LayoutStore.createStore(...).load().config` component walk it still performs
- [x] 8.2 Re-map `test_browser_shell.py` and `test_browser_art.py` off `.art-panel__scene-frame` / `.art-panel__scene-placeholder` onto the backdrop's `data-testid` hooks, keeping the bounded-wait gate on the placeholder count
- [x] 8.3 Add a browser assertion that no stage anchor's box intersects another's at **both** 1440x900 and 1280x720
- [x] 8.4 Add a browser assertion that the minimap anchor is absent in combat and present in exploration
- [x] 8.5 Add a browser assertion that the full log opens from the caption in one action and closes on Escape with focus restored
- [x] 8.6 Re-run the offline-degradation regression: bundle blocked → text playable; art unavailable → gradient stage, gameplay unblocked

## 9. Gates and handoff

- [x] 9.1 `npm test`, `npm run build`, `npm run build-storybook`, `npm run showcase-coverage` green
- [x] 9.2 `node --test web/static/webclient/js/tests/*.test.js` green (unchanged logic, asserted not broken)
- [x] 9.3 `uv run --locked python -m tools.spec_traceability check` green; new requirements carry `@covers_requirement` annotations
- [x] 9.4 `openspec validate webclient-hud-01-shell-and-scene --strict` passes
- [x] 9.5 Rebuild `web/static/webclient/app/dist` and verify the running client at both supported viewports
- [x] 9.6 Flip the roadmap's H1 Status cell to `Done`
