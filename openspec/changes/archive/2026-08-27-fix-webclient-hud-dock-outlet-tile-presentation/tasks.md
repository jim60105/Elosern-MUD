## 1. Outlet tile: correct field hierarchy (enabled-aware)

- [x] 1.1 In `web/webclient-app/components/DockMenu.vue`'s outlet-tile template, replace the separate
      `<b>{{ row.item.label }}</b>` + `<small v-if="destinationLabel(row.item)">...</small>` pair with a
      single `<b>` whose content is
      `(row.item.enabled && row.item.direction && destinationLabel(row.item)) || row.item.label` — the
      destination name only when the row is enabled, canonical, and the destination is known; the exit's
      own label (which already carries the `（無法通行）` suffix when disabled) in every other case
      (disabled, non-canonical, or unknown destination). Add a code comment explaining why a disabled row
      is excluded from the destination-name substitution (it is the row's only carrier of the disabled
      marker).
- [x] 1.2 Add/extend a Vitest test (e.g. in `web/webclient-app/tests/components/dock_panes.test.js` or a
      new `dock_menu_outlet.test.js`) covering all four branches: enabled canonical exit + known
      destination (renders destination name), enabled canonical exit + unknown destination (renders the
      exit's own label), **disabled canonical exit + known destination (renders the exit's own label with
      its `（無法通行）` suffix, NOT the destination name)**, and non-canonical exit (renders its own
      label regardless of any `destination` field).

## 2. Outlet tile: single focus indicator

- [x] 2.1 Delete the `.dock-menu__outlet-tile--focused::before` rule (the `"▶"` caret) from
      `DockMenu.vue`'s `<style scoped>` block. Do not add a replacement glyph.
- [x] 2.2 Add/extend a test asserting a focused outlet tile renders no `::before` content distinct from
      an unfocused one (or asserts computed `content: none`), while the background/border-color focus
      styling still differs between focused and unfocused tiles.

## 3. Outlet pane: no companion detail aside, disabled reason moves onto the tile

- [x] 3.1 In `DockMenu.vue`, extend the `dock-detail` aside's `v-if` guard to exclude
      `paneKind === 'outlet'` (the aside's internal `paneKind` computed value), so it never renders for
      the move frame.
- [x] 3.2 In the same outlet-tile template, add `:aria-describedby="!row.item.enabled && row.reason ? row.rowId + '-reason' : null"`
      and a `visually-hidden` `<span v-if="!row.item.enabled && row.reason" :id="row.rowId + '-reason'">{{ row.reason }}</span>`
      — the same pattern `DockMenuItem.vue` already uses — so the server-authored disabled explanation
      stays reachable by assistive technology once the aside no longer renders it.
- [x] 3.3 Add/extend tests asserting: (a) no `[data-testid="dock-detail"]` (or the aside's own testid)
      renders while the outlet pane is active with a focused row, (b) the outlet grid's rendered width
      equals the pane's full available width (no 220px reserved), and (c) a disabled outlet row (using
      the existing `_move_row(..., enabled=False)` Playwright helper / an equivalent Vitest fixture)
      carries an `aria-describedby` pointing at a hidden element containing its `disabled_reason.message`.

## 4. Spec and verification

- [x] 4.1 `grep -rn` `dock-menu__outlet` and the literal string `"east"`/`"north"` (or any other
      currently-asserted raw exit label) across `web/webclient-app/tests/` and `web/tests/browser/` to
      confirm no test snapshots the old two-field layout or the removed caret; fix any hit found. While
      here, tighten `web/tests/browser/test_browser_contextual_hud.py:1017`'s
      `assertIn("南", first_text, ...)` (a substring match that would pass by coincidence against the new
      destination-name text "南大道") to a whole-token check or an explicit assertion that the raw exit
      label is absent.
- [x] 4.2 Confirm `openspec validate fix-webclient-hud-dock-outlet-tile-presentation --strict` passes
      against the delta spec in `specs/webclient-contextual-hud/spec.md`.
- [x] 4.3 Run the focused test slice: the new/extended Vitest specs from sections 1–3, plus the existing
      `web/tests/browser/test_browser_shell.py` and `test_browser_contextual_hud.py` classes touching the
      action dock.
- [x] 4.4 Re-check the live client (`podman compose`, `http://localhost:4001/webclient/`) with
      `agent-browser`: open the 移動 frame on a room with 3+ exits, confirm each enabled tile shows one
      glyph, the destination name as its headline, no detail aside, and the focused tile shows no
      duplicate arrow symbol; separately verify (via a disabled exit, or by inspecting the accessibility
      tree) that a disabled tile still shows its `（無法通行）` label and carries its accessible reason.
