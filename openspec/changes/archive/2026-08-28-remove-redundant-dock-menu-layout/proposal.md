# Remove the redundant dock pane layout wrapper

## Why

The redesign (`docs/design/elosern-redesign/index.html`) has no generic layout
wrapper inside a dock pane: `.dock .pane` hosts the row region directly
(lines 311-335); the mock's only split element is the skill pane's own
`.skwrap` grid, which is a content pair container, not an anonymous shell.
The implementation stacks two nested flex containers instead:
`AppClient.vue`'s `.dock-pane-host` (already `display:flex; gap:12px`,
`AppClient.vue:906-912`, the real split owner between the dock menu and the
combat `SkillDetailPane`) and, redundantly inside it, `DockMenu.vue`'s root
`div.dock-menu-layout` (`DockMenu.vue:243`), which for every non-detail frame
wraps exactly one child and adds nothing. The managed browser test even asserts
the wrapper's existence (`web/tests/browser/test_browser_combat.py:776`). The
wrapper is 多餘: the host that owns the split already exists one level up.

## What Changes

- `DockMenu.vue` renders no wrapper at all: its root becomes a fragment of the
  `.dock-menu` listbox plus the optional `aside.dock-detail` (existing
  `exploration-detail` / `combat-detail` testids preserved). Both mount
  attributes are declared props/emits only (verified at `AppClient.vue:725-740`
  and `809-819`), so fragment roots carry no fallthrough cost.
- Split layout stays exclusively in the hosts that already exist:
  `.dock-pane-host` keeps `display:flex` (it already pairs DockMenu with
  `SkillDetailPane`), so the listbox, DockMenu's own detail aside, and
  `SkillDetailPane` are sibling flex children; `.dock-menu` takes
  `flex:1; min-width:0` and `.dock-detail` keeps its `flex:0 0 220px` track.
  The drawer host gets one explicit modifier (`hud-drawer__body--dock`, a
  wrapping flex row that pins the third child — the hosted surface — to its own
  full-width line) applied when a dock frame is hosted, so the drawer-hosted
  split pair remains side-by-side without squishing the surface and without any
  new component-level wrapper.
- `.dock-menu-layout` and its CSS are deleted. Managed assertions become:
  in split frames `.dock-menu` and the visible detail pane share
  `.dock-pane-host` as their direct parent (zero `.dock-menu-layout`); in the
  outlet frame `.dock-menu` is `.dock-pane-host`'s only child filling it.
- The direct-child assertion for a non-split (outlet) frame moves to the
  exploration browser journey, where outlet frames actually occur; the combat
  test keeps only the split-pair assertion.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-desktop-shell` (ADDED requirement only): the dock's row region and
  detail panes are direct children of their host — no anonymous layout
  container may sit between host and either child; the host owns the pairing.

## Impact

- Code: `web/webclient-app/components/DockMenu.vue` (fragment root + scoped
  CSS), `web/webclient-app/AppClient.vue` (drawer-body modifier class when
  `drawerHostsServiceFrame`) threaded through a new `bodyClass` prop on
  `web/webclient-app/components/HudDrawer.vue` (the open drawer root is a
  fragment, so the modifier cannot ride fallthrough), verify `ActionDock.vue`
  pane styles never assumed the removed child chain.
- Tests: `web/webclient-app/tests/action/dock_menu.test.js`,
  `web/webclient-app/tests/action/dock_menu_outlet.test.js` (root becomes the
  listbox; detail becomes a sibling of the root fragment), managed
  `web/tests/browser/test_browser_combat.py:770-780` (split-pair assertion
  replacing `.dock-menu-layout`), an outlet direct-child assertion added to the
  exploration journey (`web/tests/browser/test_browser_exploration.py`).
- Docs: `docs/development/webclient-vue-frozen-contract-audit.md:410` drops
  `.dock-menu-layout` from the REMAP-TO-TESTID row.
- Showcase: `stories/Action/DockMenu.stories.js` args unchanged; mounting a
  fragment component in Vitest/Storybook needs `attrs`/parent-free checks
  verified; no story-title changes (frozen manifest untouched).
- Traceability: the new requirement's literal ID only exists after its delta is
  synced into `openspec/specs/` — tasks sequence the sync step before the
  `covers_requirement` annotation (IDs are never taken from an active delta).
- No payload, protocol, or command-surface change; no backward compatibility
  work (unreleased project).
