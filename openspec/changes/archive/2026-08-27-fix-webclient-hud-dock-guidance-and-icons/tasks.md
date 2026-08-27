## 1. Shortcut legend: single visible instance, accurate wording

- [x] 1.1 In `web/webclient-app/components/ActionDock.vue`, add a `.visually-hidden` rule (the same
      absolute-position/1×1px/`clip: rect(0 0 0 0)` definition already duplicated independently in
      `DockMenuItem.vue` and `DockMenu.vue`) to `ActionDock.vue`'s **own** `<style scoped>` block —
      Vue's scoped CSS does not cross component boundaries, so reusing the class name alone without a
      local rule is a no-op. Apply the class to `.action-dock__description` and add
      `aria-hidden="true"` so the hidden copy is also removed from the accessibility narration order
      (the delta spec requires this; the Playwright `inner_text()` gate keeps working, since
      `aria-hidden` does not affect `textContent`/`innerText`).
- [x] 1.2 Reword the shared legend string in both `ActionDock.vue`'s `.action-dock__description` and
      `DockTabBar.vue`'s `.dock-tab-bar__hint` from `"...Esc 返回・/ 開啟指令"` to
      `"...Esc 返回・/ 聚焦指令列"` — keep the two strings byte-identical to each other and change
      nothing before the `/` clause.
- [x] 1.3 Update all four literal-text assertions in `web/webclient-app/tests/action/action_dock.test.js`
      (lines 76, 83, 193, 198) to the new wording.
- [x] 1.4 Update the Playwright keyword-substring assertion in `web/tests/browser/test_browser_shell.py`
      (~line 755: replace the `"/ 開啟指令"` keyword with `"/ 聚焦指令列"`).
- [x] 1.5 Add a Vitest assertion (in `action_dock.test.js` or a new focused spec) that
      `.action-dock__description` is not actually visible — assert its rendered state (computed
      `position`/`width`/`height`/`overflow`, and `clip` where jsdom computes it), not merely that it
      carries the `visually-hidden` class name. The test **must mount with `rootItems`** (e.g. the
      exploration root keys) so the tab bar and its `.dock-tab-bar__hint` actually render, and assert
      the hint is present and not clipped, while the hidden description's `aria-hidden` attribute is
      `"true"`.

## 2. Dock and combat-root tab glyphs matched to the redesign

- [x] 2.1 In `web/webclient-app/components/dock-icons.js`, replace the `d` path values for `move`,
      `look`, `interact`, `suggestions`, `attack`, `skills`, `items`, `defend`, `flee`, and `forfeit`
      with the exact strings in design.md's mapping table (copied from
      `docs/design/elosern-redesign/index.html`), including `look`'s combined eye+pupil compound path
      and `forfeit`'s y-shifted coordinates.
- [x] 2.2 In `web/webclient-app/components/dock-icons.js`, add a `STROKE_ATTRS` map plus a
      `glyphAttrs(key)` export mirroring the reference's selective attributes: `move` carries
      `stroke-linecap`+`stroke-linejoin` round, `interact` carries `stroke-linejoin` round only,
      `attack`/`flee` carry `stroke-linecap` round only, and every other key (`look`, `suggestions`,
      `skills`, `items`, `defend`, `forfeit`, and the untouched keys) carries none. In
      `web/webclient-app/components/DockTabBar.vue`, bind them on the tab icon `<path>` via
      `v-bind="glyphAttrs(tab.key)"`; merge the same per-key attributes into `glyphSvg`'s `path`
      child too. The tab icon's `stroke-width` is set to the reference's `1.9` (the client previously
      used `1.8`, which rendered the glyphs slightly thinner than the binding reference).
- [x] 2.3 `grep -rn` each of the ten *old* `d` string values across `web/webclient-app/tests/` and
      `web/tests/browser/` to confirm no test snapshots or asserts a literal path string; fix any hit
      found (design.md flags this as unconfirmed-clean, not assumed-clean).
- [x] 2.4 Add a new Vitest unit test file for `dock-icons.js` (none currently exists) asserting
      `glyphPath(key)` returns the new literal string for each of the ten replaced keys, that
      `glyphAttrs(key)` returns the reference's selective stroke attributes per key (`move`: cap+join,
      `interact`: join only, `attack`/`flee`: cap only, all other keys: none), and that at least one
      untouched key (e.g. `character`) still returns its prior `d` value.
- [x] 2.5 Visually verify the new glyphs render correctly at 16×16 in the `Action/ActionDock` and
      `Action/DockTabBar` Storybook stories (exploration and combat variants) — confirm no clipped or
      malformed path (particularly `look`'s compound path) and confirm the rounded caps/joins render.

## 3. Dock panel background and shadow matched to the redesign

- [x] 3.1 In `web/webclient-app/components/ActionDock.vue`'s `.action-dock` rule, replace
      `background: linear-gradient(180deg, var(--panel-hi), var(--panel))` with
      `background: linear-gradient(0deg, #0c0a0e, #141019 70%, var(--panel))`, and
      `box-shadow: 0 -12px 40px -20px rgba(0, 0, 0, 0.9)` with `box-shadow: 0 -14px 34px -24px #000`.
      Leave `border-top`, `border-radius`, and every other declaration unchanged.
- [x] 3.2 Visually verify the new background/shadow in the `Action/ActionDock` Storybook story and
      against the live client (task 4.3) — confirm the panel reads as a darker, shadow-receding band
      rather than a lighter violet-tinted card.

## 4. Spec and verification

- [x] 4.1 Confirm `openspec validate fix-webclient-hud-dock-guidance-and-icons --strict` passes against
      the delta spec in `specs/webclient-contextual-hud/spec.md`.
- [x] 4.2 Run the focused test slice: `npm test -- action_dock` (Vitest) and the `test_browser_shell.py`
      shell-chrome test class (Playwright/managed browser), plus the new `dock-icons` unit test.
- [x] 4.3 Re-check the live client (`podman compose`, `http://localhost:4001/webclient/`) with
      `agent-browser`: confirm the shortcut legend now prints once with the reworded `/` clause, the
      move/look/interact tab icons visually match `docs/design/elosern-redesign/index.html`, and the
      dock panel's background/shadow match the reference.
