# Design — remove-redundant-dock-menu-layout

## Context

Mount chain today: `.action-dock__pane` (scroll, `ActionDock.vue:165`) →
`div.dock-pane-host` (`AppClient.vue:724`, `display:flex; gap:12px;
align-items:flex-start`, `AppClient.vue:906-912`) → `DockMenu` (root
`div.dock-menu-layout`, another flex row, `DockMenu.vue:243,518-524`) →
`div.dock-menu[role=listbox]` + optional `aside.dock-detail`
(`DockMenu.vue:248-513`, detail `flex:0 0 220px`, line 892). The combat
skill-specific detail is a sibling of DockMenu **under `.dock-pane-host`**
already: `SkillDetailPane` (`AppClient.vue:741-751`), while DockMenu's generic
detail is suppressed via `:hide-generic-detail` (line 737). Both detail
elements carry the same `combat-detail`/`exploration-detail` testids
(`SkillDetailPane.vue:44`). The second host is the drawer body
(`AppClient.vue:809-819`, `drawerHostsServiceFrame`). The mount sites bind only
declared props/emits — verified — so a fragment root has no attribute
fallthrough to lose.

## Goals / Non-goals

- Goals: zero anonymous layout containers inside `DockMenu`; the host that
  already owns the split (`.dock-pane-host`) keeps owning it; drawer-hosted
  pairs stay side by side; preserved hooks (`dock-menu`, `dock-item`,
  `exploration-detail`, `combat-detail`, listbox composite, scroll/keyboard
  contracts) untouched.
- Non-goals: restyling `.dock-detail`/`SkillDetailPane`, changing the 220px
  track, touching `DockMenuItem.vue`.

## Decisions

### D1 — Fragment root; the host owns the split (no new wrapper anywhere)

`DockMenu.vue`'s template root becomes a fragment: `.dock-menu` (always) and
`aside.dock-detail` (current condition: `paneKind !== 'outlet' && ((showDetail
&& focusedRow && !hideGenericDetail) || detailMessage)`).
`.dock-menu-layout`'s CSS is deleted; `flex:1; min-width:0` moves onto
`.dock-menu`. Consequences per host:

- Action dock: `.dock-pane-host` (flex row) pairs `.dock-menu` with
  `SkillDetailPane` exactly as today, and now pairs it with `.dock-detail`
  too (same flex row, same gap). No new AppClient CSS.
- Drawer host: `.hud-drawer__body` gains a modifier class
  `hud-drawer__body--dock` (`display:flex; flex-wrap:wrap; align-items:flex-start;
  gap:var(--sp-3)`) applied by AppClient only when `drawerHostsServiceFrame`
  (an existing computed) via a new `bodyClass` prop on `HudDrawer` — the
  modifier cannot ride attribute fallthrough because the open drawer root is a
  fragment (scrim + panel). The drawer body also holds the surface component
  (Shop/Quest/InventoryPanel) as a third direct child, so the rule wraps and
  pins the non-`.dock-menu`/non-`.dock-detail` child to a full-width row
  (`.hud-drawer__body--dock > :not(.dock-menu):not(.dock-detail) { flex: 1 1
  100%; min-width: 0 }`): the surface keeps its own line (the pre-change
  stacked reading, never squished beside the rows) while `.dock-menu` and
  `.dock-detail` wrap onto the next line side by side. Block layout would
  otherwise stack the list/detail pair vertically; the modifier is one
  host-side declaration, not a component wrapper.

Rejected: a conditional split wrapper inside DockMenu — the mock's `.skwrap`
counterpart is the skill content pair, and here the pair owner is the host:
in the combat skill frame the detail (`SkillDetailPane`) is not even rendered
by DockMenu, so a DockMenu-owned split container can never hold that pair;
keeping any wrapper would leave two nested split containers again.

### D2 — Scope attribute note

Scoped-CSS hashing applies to fragment roots normally; `.dock-menu`/
`.dock-detail` styles move to unscoped-safe selectors already present in
`DockMenu.vue` (scoped still works on fragment children). Vitest mounting a
multi-root component: `wrapper.get/find` still work; root-element assertions
(`w.element`) must be rewritten to `w.findAll('.dock-menu')`-style queries.

### D3 — Contract bookkeeping

Delete `.dock-menu-layout` everywhere: managed skill-frame assertion becomes
`.dock-menu` and `[data-testid="combat-detail"]` share the
`.dock-pane-host` parent and `.dock-menu-layout` count is 0; outlet
direct-child assertion goes to the exploration journey where outlet frames are
reachable (`test_browser_exploration.py` move-frame step); the audit table
(`docs/development/webclient-vue-frozen-contract-audit.md:410`) drops the class
with no replacement (it is retired, not remapped).

## Risks / trade-offs

- `.dock-detail` now relies on `.dock-pane-host`'s flex context; the drawer
  modifier replicates the needed properties. The third direct child (the hosted
  service surface) is pinned to a full-width wrapped row so it is never squeezed
  beside the dock rows — a bare flex-row body (the initial draft) would have put
  the surface, the 220px detail, and the rows on one line inside the ~560px
  drawer and overflowed it, so the modifier wraps instead.
- Multi-root changes focus-order assumptions in `dock_menu*.test.js` root
  queries — mechanical rewrites.
- Managed shard changes are CI-verified; locally only the two touched browser
  classes run (each within budget).
