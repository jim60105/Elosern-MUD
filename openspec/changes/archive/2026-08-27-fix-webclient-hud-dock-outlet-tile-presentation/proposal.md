## Why

Comparing the shipped move/exit list (the dock's "outlet" pane, opened from the 移動 tab) against
`docs/design/elosern-redesign/index.html`'s `.outlet` grid found three concrete defects, reproduced live
against the running client (`podman compose`, `http://localhost:4001/webclient/`) with a browser at
1440x900:

1. **The tile's bold text is the wrong field, so canonical exits show redundant, low-information
   content.** `DockMenu.vue`'s outlet template renders, per tile: a leading direction-glyph span (e.g.
   `→` for east), then `<b>{{ row.item.label }}</b>` (the exit's own raw server label — for this game's
   compass exits that label is literally the direction word, e.g. `"east"`), then a `<small>` destination
   name (e.g. `"冒險者公會外"`) only when the destination is in the committed local-map lattice. For a
   canonical exit this means the direction is shown **twice** — once as the glyph, once spelled out as
   the bold headline — while the actually useful information (where the exit leads) is relegated to a
   barely-legible 10.5px subtitle. `webclient-contextual-hud`'s own "Dock panes render a per-kind
   vocabulary" requirement already says a move row renders "the exit's direction as a leading glyph
   **together with the destination's display name**" — two pieces of information, not three — and does
   not call for the raw exit label to render as a separate headline once a glyph already carries its
   meaning. The redesign's own tiles (`index.html:766-770`, e.g. `<b>北</b>北岸大道`) render exactly the
   two pieces the requirement names: a compact glyph/short-form, then the destination name as the
   tile's actual readable content — never a third repetition of the direction word.

2. **The focused tile shows two arrow-like symbols at once.** `.dock-menu__outlet-tile--focused::before`
   independently injects a `"▶"` caret (`DockMenu.vue`, the same pattern `DockMenuItem.vue` uses for
   plain text-only cells), which renders *before* the tile's own persistent direction-glyph span. On a
   focused canonical exit this produces two arrow-shaped glyphs stacked at the start of the tile (`▶`
   then `→`), confirmed in the live client. `DockMenuItem.vue`'s identical `::before` pattern is correct
   for its own case — those cells carry no other icon, so the caret is the only non-color focus
   indicator — but the outlet tile already carries a permanent, non-color direction glyph, so stacking a
   second one on focus is pure visual noise with no added information.

3. **A generic "detail" side panel renders for the outlet pane and adds nothing.** `DockMenu.vue`'s
   `dock-detail` aside (`showDetail` defaults to `true` and is suppressed only via an explicit
   `hideGenericDetail` prop, which the exploration frame does not pass) renders a fixed 220px-wide column
   next to every pane with a focused row, showing the focused item's own `label`, an optional
   `cost_text`/`description` (both absent for exit rows), and a static `"Enter → 開啟"` action hint. For
   the outlet pane this panel repeats the just-clicked exit's own label and adds only the literal string
   `"Enter → 開啟"` — no new information a player couldn't already infer. It also consumes a fixed 220px
   of the dock's 1180px-max width, which is the direct cause of the outlet grid rendering far fewer,
   far wider tiles than the reference: measured live, the outlet grid's own container shrinks from
   ~1140px to ~908px once the aside is subtracted. `docs/design/elosern-redesign/index.html`'s `.outlet`
   grid has no companion side panel at all — exit tiles are self-explanatory; clicking or pressing Enter
   needs no additional prompt.

All three are presentation/template fixes inside `DockMenu.vue`, a component already built and wired by
the completed `webclient-hud-03-action-dock` wave. None of them touches the router, the store, the OOB
action dispatch, or any preserved DOM contract identifier (`#action-dock`, `data-item-key`,
`data-testid="dock-menu"`, etc.). A separate, independently-sized change addresses why the outlet grid
renders only two *equal-width* columns instead of a responsive multi-column grid even after this
panel-width fix (`fix-webclient-hud-dock-outlet-grid-geometry` — a `gridCols` value shared with the
keyboard router, out of this change's presentation-only scope).

## What Changes

- In `DockMenu.vue`'s outlet-tile template, swap which field is the tile's primary bold text: render the
  destination's display name (`destinationLabel(row.item)`) as the `<b>` headline, and drop the separate
  rendering of the exit's raw `row.item.label` for an **enabled, canonical** exit — the glyph alone
  carries the direction. For a non-canonical exit (no `direction`, e.g. a named door), a disabled exit
  (whose label already carries the server's `（無法通行）` suffix), or a canonical exit whose destination
  is not yet in the committed local-map lattice, the headline stays `row.item.label` verbatim — never a
  blank tile, and never a silently-dropped disabled marker.
- Preserve the disabled exit's server-authored explanation (`row.reason`) as an accessible-only note on
  the tile itself (`aria-describedby` + a visually-hidden span, the same pattern `DockMenuItem.vue`
  already uses), since removing the generic detail aside below removes the only other surface that
  rendered it.
- Remove `.dock-menu__outlet-tile--focused::before`'s `"▶"` caret. The tile's existing direction glyph
  (always rendered, not focus-conditional) plus the focused-state background/border fill already
  distinguish the focused tile without stacking a second glyph; a non-canonical exit tile (no direction
  glyph) still shows its headline text plus the same background/border fill, so no tile loses its
  non-color focus indicator.
- Suppress the generic `dock-detail` aside for the outlet pane kind: `DockMenu.vue`'s own internal
  `paneKind` classification (already computed in this file) extends the aside's existing `v-if` guard so
  it never renders while `paneKind === 'outlet'`, the same intent `hideGenericDetail` already serves for
  combat (suppressing the generic aside in favor of a pane-specific surface) but resolved internally
  since `paneKind` is not exposed to the parent. The outlet grid then receives the pane's full width.
- **BREAKING**: none. No prop, event, DOM id, `data-testid`, dispatch, or protocol contract changes;
  `outletRows`, `destinationLabel()`, and the exploration menu's server-derived item shape are unchanged.
  The visible tile content, the new `aria-describedby` note, and the aside's presence are the only
  observable differences.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-contextual-hud`: the "Dock panes render a per-kind vocabulary from backed fields only"
  requirement's move-row clause is tightened to state the destination's display name is the row's primary
  rendered text only when the row is enabled (a disabled row's own label, carrying its `（無法通行）`
  suffix, is never replaced), that a move row carries no other side panel or companion surface, and that
  a disabled move row's server-authored explanation stays accessible even without that panel.

## Impact

- **Code**: `web/webclient-app/components/DockMenu.vue` (outlet-tile template markup, the
  `--focused::before` rule removal, the `hideGenericDetail`/pane-kind guard for the outlet pane).
- **Tests**: `web/webclient-app/tests/components/dock_panes.test.js` or a new focused Vitest spec for the
  outlet tile's rendered headline/subtitle field mapping; a Storybook visual check
  (`Action/ActionDock` or a dedicated `DockMenu` outlet story) confirming the wider, glyph-only-focus
  tiles and the absent detail aside; a managed-browser (Playwright) re-check that the move frame's
  rendered tile count and width look correct at 1440x900 and 1280x720.
- **Docs**: none.
- **No protocol, read-model, dispatch, keyboard-router, or component-inventory changes.**
