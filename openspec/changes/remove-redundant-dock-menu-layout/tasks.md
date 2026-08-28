# Tasks — remove-redundant-dock-menu-layout

## 1. DockMenu fragment root

- [ ] 1.1 In `DockMenu.vue`, make the template a fragment: the `.dock-menu`
  listbox subtree (unchanged internally) and the existing
  `aside.dock-detail` under the unchanged display condition; delete the
  `.dock-menu-layout` element and its scoped CSS; move `flex:1; min-width:0`
  onto `.dock-menu`; keep `.dock-detail`'s `flex:0 0 220px`.
- [ ] 1.2 In `AppClient.vue`, add the `hud-drawer__body--dock` flex-row
  modifier on the drawer body only when `drawerHostsServiceFrame`
  (`display:flex; align-items:flex-start; gap: var(--sp-3)`); leave
  `.dock-pane-host` CSS untouched.
- [ ] 1.3 Verify both hosts render list + detail side by side for split frames
  (including the `focusedSkill` state where `SkillDetailPane` is the detail)
  and that non-split frames make `.dock-menu` the host's only dock-menu child.

## 2. Tests with the behavior

- [ ] 2.1 Update `web/webclient-app/tests/action/dock_menu.test.js` and
  `web/webclient-app/tests/action/dock_menu_outlet.test.js` for the fragment
  root (no `w.element` root assumptions; detail asserted as the listbox's
  fragment sibling); run both files with `npm test`.
- [ ] 2.2 Migrate `web/tests/browser/test_browser_combat.py:776` from
  `.dock-menu-layout` to: `.dock-menu-layout` count 0, and `.dock-menu` +
  visible detail testid share the `.dock-pane-host` parent; add the
  outlet-frame direct-child assertion to the move-frame step of
  `web/tests/browser/test_browser_exploration.py` (where outlet frames occur);
  run both classes locally within budget.

## 3. Contract bookkeeping and showcase

- [ ] 3.1 Remove `.dock-menu-layout` from the REMAP-TO-TESTID row of
  `docs/development/webclient-vue-frozen-contract-audit.md:410` (retired; no
  replacement selector).
- [ ] 3.2 Confirm `stories/Action/DockMenu.stories.js` renders split and
  non-split states with no title change; `npm run showcase-coverage` green.

## 4. Traceability (after the behavior lands)

- [ ] 4.1 Sync the delta into the main spec
  (`openspec-sync-specs` flow for `webclient-desktop-shell`), then obtain the
  new requirement's literal ID from
  `uv run --locked python -m tools.spec_traceability list` and annotate the
  split-pair assertion in `test_browser_combat.py` (and the outlet assertion if
  it is the substantive cover) with `covers_requirement`. Never annotate from
  the active-delta text before syncing; there is no waiver path.
- [ ] 4.2 `uv run --locked python -m tools.spec_traceability check`;
  `openspec validate remove-redundant-dock-menu-layout --strict`;
  `git diff --check` clean.
