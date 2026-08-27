## 1. Column sizing fix

- [ ] 1.1 In `web/webclient-app/components/DockMenu.vue`, change `paneGridStyle`'s computed to emit
      `max-content` as the track-sizing function when `paneKind.value` is `outlet` or `nav`, and keep
      `1fr` for every other pane kind — including `plain` (design.md Decision 1). Keep
      `repeat(${gridCols}, ...)` exactly as-is — only the sizing function changes.
- [ ] 1.2 Add `max-width: 220px; overflow-wrap: break-word;` to `.dock-menu__outlet-tile` and
      `max-width: 320px; overflow-wrap: break-word;` to `.dock-menu__nav-row` (design.md Decision 3).
- [ ] 1.3 Add a Vitest test rendering an outlet tile and a nav row with a long, generated destination
      name / joined affordance-label string (well past the cap), asserting the tile wraps within its
      `max-width` rather than overflowing the pane.
- [ ] 1.4 Add a Vitest unit test asserting `paneGridStyle`'s computed output: `max-content` for a mounted
      instance with `paneKind` resolving to `outlet`/`nav` and a non-null `gridCols`, `1fr` for
      `plain`/`affordance`/`cards`/`skills`/`targets`/`scales`/`confirm` with the same `gridCols`, and
      `{}` when `gridCols` is null/0.

## 2. Regression guard

- [ ] 2.1 `grep -rn` `getBoundingClientRect\|bounding_box` across `web/tests/browser/` and
      `web/webclient-app/tests/` for any test touching `dock-menu__outlet`, `dock-menu__nav`, or
      `dock-menu-item` to confirm none asserts a specific rendered pixel width that this change would
      alter; fix any hit found (none expected per design.md's research).
- [ ] 2.2 Run the full existing keyboard-navigation Playwright coverage for the `move`/`look`/`interact`
      menus unmodified: `test_browser_exploration.py` (the `ArrowRight` "second grid column" assertions)
      and the relevant `test_browser_contextual_hud.py` classes — confirm every assertion still passes
      with no test file edits needed (column count and item-to-cell mapping are unchanged).
- [ ] 2.3 Re-confirm live (do not skip, since this change's own research already found one such
      assumption wrong) that the `wait` sub-menu is unaffected: check `getComputedStyle` on
      `.dock-menu__plain` still reports `display: block` (or equivalent non-grid value) both before and
      after this change, and that the 等待/休息 frame's rendered layout is pixel-identical to before.

## 3. Spec and verification

- [ ] 3.1 Confirm `openspec validate fix-webclient-hud-dock-exploration-grid-width --strict` passes
      against the added requirement in `specs/webclient-contextual-hud/spec.md`.
- [ ] 3.2 Re-check the live client (`podman compose`, `http://localhost:4001/webclient/`) with
      `agent-browser`: open the 移動 frame on a multi-exit room, confirm tiles render at a content-sized
      width (not stretched to half the panel), confirm `ArrowRight`/`ArrowDown` still move focus between
      the same cells as before, and repeat for 查看/互動. Confirm 等待/休息 is visually unchanged.
