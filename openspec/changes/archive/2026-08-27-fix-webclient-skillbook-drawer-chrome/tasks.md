## 1. Extend the shared glyph table

- [x] 1.1 In `web/webclient-app/components/dock-icons.js`, add `close: "M6 6l12 12M18 6 6 18"` to `GLYPHS` and `close: { "stroke-linecap": "round" }` to `STROKE_ATTRS` (matching `docs/design/elosern-redesign/index.html`'s `.closebtn` path exactly)

## 2. `HudDrawer.vue`: icon prop + icon-only close control

- [x] 2.1 Import `glyphPath` from `./dock-icons.js`
- [x] 2.2 Add an `icon: { type: String, default: null }` prop
- [x] 2.3 In `.hud-drawer__head`, render a leading `<svg class="hud-drawer__icon" aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none"><path :d="glyphPath(icon)" stroke="currentColor" stroke-width="1.8" v-bind="glyphAttrs(icon)" /></svg>` when `icon` is set and `glyphPath(icon)` resolves, before `.hud-drawer__title` — follow `DockTabBar.vue:133`'s `v-bind="glyphAttrs(...)"` pattern, not `QuickWordChips.vue`'s bare `:d`-only usage, so a glyph's per-key stroke attributes actually apply
- [x] 2.4 Replace the close button's visible "關閉" text with an icon (`glyphPath('close')`, `v-bind="glyphAttrs('close')"`, `aria-hidden="true"`) and add `aria-label="關閉"` to the `<button>` so the accessible name is unchanged
- [x] 2.5 Add `.hud-drawer__icon` CSS: `width: 20px; height: 20px; color: var(--gold-400);` (matching `docs/design/elosern-redesign/index.html:409-410`'s `.dhead .ic`) so the head icon renders gold, not inherited text color
- [x] 2.6 Adjust `.hud-drawer__close`'s CSS (padding/min-size) so the icon-only button keeps at least its current click/tap target size

## 3. `AppClient.vue`: wire the skill drawer's icon, subtitle, and footer

- [x] 3.1 Add a `skillCounts` (or reuse-named) computed that counts `actives`/`passives` rows from `panel('character')` the same way `SkillBook.vue`'s `skillCount()` does today
- [x] 3.2 Add a `skillBookSubtitle` computed: `` `主動 ${activeCount} · 被動 ${passiveCount}` `` when the skill drawer is open and the character panel is available, else `""`
- [x] 3.3 On the `HudDrawer` instance, pass `:icon="store.view.hudDrawer === 'skill' ? 'skills' : null"` and `:subtitle="store.view.hudDrawer === 'skill' ? skillBookSubtitle : ''"` (the other five drawers keep receiving no icon / no subtitle, unchanged)
- [x] 3.4 Add a `<template #foot>` block, rendered only when `store.view.hudDrawer === 'skill'`, containing the static cast-syntax hint text `施放入口：cast <技法>[@威力]=<代號>`, styled with the existing `.hud-drawer__foot` chrome (no new CSS needed there)

## 4. `SkillBook.vue`: drop the duplicate title, widen the tabs, add the search icon

- [x] 4.1 Remove the `<h3 class="skill-book__title">` block and its `.skill-book__title`/`.skill-book__counts` CSS rules (the count now lives in `HudDrawer`'s subtitle, computed in `AppClient.vue`)
- [x] 4.2 Change `.skill-book__tabs` to a flex row where each `.skill-book__tab` takes `flex: 1` and is center-text, so the two tabs evenly split the drawer's width (matching the design's full-width segmented pair)
- [x] 4.3 Wrap the search input in a `.skill-book__search-wrap` container that carries the border/background `.skill-book__search` has today (so the field reads as one single-bordered control, not double-boxed); add a small inline magnifying-glass SVG (`<circle cx="11" cy="11" r="6"/><path d="M20 20l-4-4" stroke-linecap="round"/>`, matching `index.html:891`) as a leading icon inside the wrapper; the `<input>` itself keeps its `placeholder`, `v-model`, and `data-testid` unchanged, but its own border/background rules move to the wrapper

## 5. Tests

- [x] 5.1 Update `web/webclient-app/tests/hud_drawer.test.js`: add a case asserting the `icon` prop renders the glyph path when set and renders nothing when unset; add a case asserting the close button has `aria-label="關閉"` and no visible text node
- [x] 5.2 Update `web/webclient-app/tests/data/skill_book.test.js`: remove any assertion on `SkillBook`'s own title/count markup (now gone); keep/extend the tab and search assertions against the new markup (`data-testid` values are unchanged, only surrounding structure/CSS changed)
- [x] 5.3 Add an `AppClient`-level or a small dedicated test asserting the skill drawer's composed `HudDrawer` receives `icon="skills"` and the correct `主動 {n} · 被動 {m}` subtitle string for a given `panel('character')` fixture, and that the footer renders the cast-syntax hint only for the skill drawer
- [x] 5.4 Run `web/tests/browser/test_browser_services.py`'s `GuildBoardJourneys`/related drawer test (the one asserting `.hud-drawer__title` visibility at line ~199) to confirm it still passes unchanged

## 6. Stories

- [x] 6.1 Confirm `web/webclient-app/stories/Data/SkillBook.stories.js`'s existing stories still render correctly with the title/count markup removed (they render `SkillBook` standalone, outside `HudDrawer`, so no story-level regression is expected — verify by rendering, not by assumption)
- [x] 6.2 Extend the existing `web/webclient-app/stories/Core/HudDrawer.stories.js` with a variant showing the `icon` + `subtitle` + `foot` slot combination the skill drawer now uses, so the composed chrome is visible in the offline showcase too

## 7. Spec sync and gates

- [x] 7.1 Confirm `openspec/changes/fix-webclient-skillbook-drawer-chrome/specs/webclient-contextual-hud/spec.md`'s MODIFIED requirement matches the implemented behavior exactly
- [x] 7.2 Run `openspec validate fix-webclient-skillbook-drawer-chrome --strict`
- [x] 7.3 Run `npm test` (Vitest) for the affected component/story tests
- [x] 7.4 Run the affected `web/tests/browser/` suite slice (services + contextual-hud + reconnect files, which reference `hud-drawer`)
- [x] 7.5 Run `tools.spec_traceability check` to confirm the amended requirement's new scenarios have matching tests
