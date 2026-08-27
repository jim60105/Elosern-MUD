## 1. Column sizing fix

- [x] 1.1 In `web/webclient-app/components/DockMenu.vue`, change `paneGridStyle`'s computed to emit
      `minmax(0, max-content)` as the track-sizing function when `paneKind.value` is `outlet` or `nav`,
      and keep `1fr` for every other pane kind — including `plain` (design.md Decision 1). Keep
      `repeat(${gridCols}, ...)` exactly as-is — only the sizing function changes; the `0` minimum lets
      the fixed columns compress on a narrow pane instead of overflowing it.
- [x] 1.2 Add `max-width: 220px; min-width: 0; overflow-wrap: break-word;` to `.dock-menu__outlet-tile`
      and `max-width: 320px; min-width: 0; overflow-wrap: break-word;` to `.dock-menu__nav-row`, and
      add a new `min-width: 0; overflow-wrap: break-word;` rule on `.dock-menu__nav-text` (design.md
      Decision 3), so long server-authored strings wrap inside the capped tile/row and the nav row's text
      block cannot break through the 320px cap via its automatic min-content size.
- [x] 1.3 Add a Vitest test rendering an outlet tile and a nav row with a long, generated destination
      name / joined affordance-label string (well past the cap), asserting the long label renders inside
      the tile/row and the loaded CSS rule carries the `max-width` / `min-width: 0` /
      `overflow-wrap: break-word` safety net (asserted through the rule's `style.cssText`, since jsdom
      leaves the camelCase accessors unpopulated).
- [x] 1.4 Add a Vitest unit test asserting the rendered pane element's inline
      `grid-template-columns` per pane kind (the script-setup computed is closed, so no `wrapper.vm`):
      `repeat(2, minmax(0, max-content))` for `outlet`/`nav` with a non-null `gridCols`, `repeat(2, 1fr)`
      for `plain`/`affordance`/`cards`/`skills`/`targets`/`scales`/`confirm` with the same `gridCols`,
      and no inline grid template when `gridCols` is null/0 (the plain pane's computed `display` stays
      `block` — the task 2.3 re-confirmation, asserted in the same test).

## 2. Regression guard

- [x] 2.1 `grep -rn` `getBoundingClientRect\|bounding_box` across `web/tests/browser/` and
      `web/webclient-app/tests/` for any test touching `dock-menu__outlet`, `dock-menu__nav`, or
      `dock-menu-item` to confirm none asserts a specific rendered pixel width that this change would
      alter; fix any hit found (none expected per design.md's research).
- [x] 2.2 Run the existing keyboard-navigation Playwright coverage for the `move`/`look`/`interact`
      menus unmodified — the `ArrowRight` "second grid column" assertions in
      `test_browser_exploration.py` (`test_keyboard_move_charges_time_and_refreshes_map`,
      `test_look_at_guard_shows_the_affinity_stage_line`,
      `test_freeform_dialogue_degrades_offline_through_the_command_line`,
      `test_cancelled_freeform_dialogue_cannot_capture_a_later_command`,
      `test_unsafe_skip_rejects_before_any_clock_advance`,
      `test_safe_wait_until_dawn_advances_the_clock`) and the `ArrowRight` assertions in
      `test_browser_contextual_hud.py` (`test_combat_skills_bounded_master_detail`,
      `test_destructive_combat_confirmation_two_step_panel`) — confirm every assertion still passes with
      no test-file edits (column count and item-to-cell mapping are unchanged).
- [x] 2.3 Re-confirm (do not skip, since this change's own research already found one such assumption
      wrong) that the `wait` sub-menu is unaffected: the Vitest task 1.4 test asserts
      `getComputedStyle(.dock-menu__plain).display === "block"`, and the new narrow-viewport browser test
      re-confirms the 等待/休息 frame stays a non-grid block container after this change.
- [x] 2.4 Add the narrow-viewport regression test
      `test_outlet_and_nav_tiles_stay_within_the_pane_at_a_narrow_viewport` to
      `web/tests/browser/test_browser_exploration.py` (the minimum supported 1280x720 viewport): assert
      the outlet tiles and nav rows stay within the pane's bounding box (no horizontal overflow), that
      `ArrowRight` still moves focus to the second grid column, and that the wait/rest pane's computed
      `display` remains `block`. Register the new test in `.github/browser-shards.json` so the
      `test_browser_method_labels_preserve_exact_ownership` contract keeps passing.

## 3. Spec and verification

- [x] 3.1 Confirm `openspec validate fix-webclient-hud-dock-exploration-grid-width --strict` passes
      against the added requirement in `specs/webclient-contextual-hud/spec.md`.
- [x] 3.2 Re-check the live client (`podman compose`, `http://localhost:4001/webclient/`) with
      `agent-browser`: open the 移動 frame on a multi-exit room, confirm tiles render at a content-sized
      width (not stretched to half the panel), confirm `ArrowRight`/`ArrowDown` still move focus between
      the same cells as before, and repeat for 查看/互動. Confirm 等待/休息 is visually unchanged.
