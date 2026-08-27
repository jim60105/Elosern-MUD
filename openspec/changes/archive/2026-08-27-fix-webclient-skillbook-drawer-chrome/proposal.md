## Why

`docs/design/elosern-redesign/index.html`'s `#dr-skill` drawer head is one row: a star-shaped skill
glyph, "技能書", a subtitle ("主動 91 · 被動 23 · 最大 192"), and an X-icon close control — followed
by a full-width 主動/被動 segmented tab pair, a search field with a leading magnifying-glass icon, and
(at the very bottom, in the drawer's footer) the cast-syntax hint `施放入口：cast <技法>[@威力]=<代號>`.

Rendered against the same drawer today (`HudDrawer.vue` hosting `SkillBook.vue`, confirmed by opening
both the design draft and the live Storybook story side by side at 1440×900), the drawer shows:
**two stacked "技能書" headings** — `HudDrawer.vue`'s own `<h3 class="hud-drawer__title">` renders
"技能書" from `AppClient.vue`'s `drawerTitle`, and immediately below it `SkillBook.vue` renders its
own `<h3 class="skill-book__title">技能書 <span>主動 X · 被動 Y</span></h3>` — no icon anywhere, the
close control is a plain text button reading "關閉" (design: an icon-only X), the 主動/被動 tabs are two
small left-aligned pill buttons instead of a full-width segmented pair, the search field has no icon,
and there is no footer at all — `SkillBook.vue` never uses `HudDrawer`'s `foot` slot, so the cast-syntax
hint is simply absent.

None of this needs new data (the skill-count subtitle is already computable from `panel('character')`,
which `AppClient.vue` already holds); it is chrome and layout that never got wired to the icon table,
slot, and CSS the codebase already has. `web/webclient-app/components/dock-icons.js`'s `GLYPHS` table
already carries the exact `skills` star-glyph path the design draft's `#dr-skill` head icon uses
(`glyphPath('skills')` — confirmed identical `d` string to `index.html:887`'s `<svg class="ic">` path),
and `QuickWordChips.vue` already shows the established pattern for consuming it (import `glyphPath`,
render a plain inline `<svg><path :d="glyphPath(key)" .../></svg>`). `HudDrawer.vue` already supports a
`foot` slot (`<div v-if="$slots.foot"><slot name="foot" /></div>`) that no drawer has ever used.

## What Changes

- `HudDrawer.vue` gains an optional `icon` prop (a `dock-icons.js` glyph key); when set, a small
  `aria-hidden` SVG (the same `glyphPath()` pattern `QuickWordChips.vue` uses) renders before the
  title text inside `.hud-drawer__head`. Left unset (the other five drawers, unchanged in this
  change), the head renders exactly as it does today.
- `HudDrawer.vue`'s close button becomes an icon-only control: the design's X path
  (`M6 6l12 12M18 6 6 18`, rounded caps) is added to `dock-icons.js`'s `GLYPHS`/`STROKE_ATTRS` tables as
  a new `close` key, rendered in place of the visible "關閉" text, with `aria-label="關閉"` preserving
  the accessible name. This is a shared-chrome change — it affects all six `HudDrawer`-hosted panels
  identically, matching the design draft's own `.closebtn`, which is the same icon on every one of its
  seven drawers.
- `AppClient.vue` passes `icon="skills"` and a computed `subtitle` (`"主動 {n} · 被動 {m}"`, derived
  from `panel('character')`'s `actives`/`passives` row counts — the same counting `SkillBook.vue`
  already does internally) to the `HudDrawer` instance only when `store.view.hudDrawer === 'skill'`; the
  other five drawers pass no subtitle, unchanged.
- `SkillBook.vue` stops rendering its own `<h3 class="skill-book__title">` and count span — the title
  and the count now live once, in `HudDrawer`'s head, sourced from `AppClient.vue`'s computed subtitle.
- `SkillBook.vue`'s tabs (`.skill-book__tabs` / `.skill-book__tab`) become a full-width, evenly-split
  segmented control (`flex: 1` per tab), matching the design's two-up `主動`/`被動` pair.
- `SkillBook.vue`'s search field gains a leading magnifying-glass icon in a wrapper element, matching
  the design's `.searchbox` (icon + input, no shared-table entry needed — this glyph is used nowhere
  else in the app today, so it is a small inline SVG local to this component rather than a new
  `dock-icons.js` table entry).
- `AppClient.vue` provides the `HudDrawer`'s `foot` slot only for the skill drawer, rendering the
  design's static cast-syntax hint (`施放入口：cast <技法>[@威力]=<代號>`) — this is authored client
  copy describing the client's own `/cast` command syntax, not narrative/story content, and it carries
  no OOB data.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `webclient-contextual-hud`: the reference-drawer chrome requirement is amended so a drawer's close
  control is icon-only (with a preserved accessible name) and a drawer MAY declare a leading head icon,
  and so the skill-book drawer specifically carries its skill-count subtitle and a cast-syntax footer
  hint sourced from client-local presentation logic, not from a distinct OOB field.

## Impact

- `web/webclient-app/components/dock-icons.js`: new `close` glyph + stroke-attrs entry.
- `web/webclient-app/components/HudDrawer.vue`: new optional `icon` prop; close button becomes
  icon+`aria-label` instead of visible text; `.hud-drawer__close` CSS adjusted for an icon-sized button.
- `web/webclient-app/AppClient.vue`: `icon="skills"` + a new `skillBookSubtitle` computed passed to the
  skill drawer's `HudDrawer` instance; a `#foot` template added for the skill drawer only.
- `web/webclient-app/components/SkillBook.vue`: removes its own title/count heading; tabs become
  full-width; search field gains a leading icon.
- Tests: `web/webclient-app/tests/hud_drawer.test.js` (icon prop renders when set, absent otherwise;
  close button carries `aria-label="關閉"` and no visible text node); `web/webclient-app/tests/data/skill_book.test.js`
  (no more internal title/count assertions on `SkillBook` itself — those move to an `AppClient`-level or
  `HudDrawer`-level test asserting the composed subtitle); `web/tests/browser/test_browser_services.py:199`
  keeps passing unchanged (it asserts `.hud-drawer__title` is visible, not its text content, so the
  added icon is not a breaking change to that assertion).
- Player-facing command surface is unchanged (the footer hint documents the existing `/cast` syntax, it
  does not add or change a command), so `docs/game/commands.md` / `docs/game/command-reference.md` and
  `tests/test_command_docs.py` need no update.
- Spec-test traceability: the amended requirement keeps substantively matching tests (the updated
  `hud_drawer.test.js` cases); `tools.spec_traceability check` must stay green.
