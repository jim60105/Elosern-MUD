## Why

`docs/design/elosern-redesign/index.html`'s `#dr-skill` skill rows carry a distinct visual language the
live `SkillBook.vue` does not: a category summary states its skill count and a `›` chevron that rotates
open (`details.cat>summary .cnt` / `.tw`), a small square colour dot precedes an elemental group's name
(`.grp .dot`, 7×7px, `border-radius:2px`), MP/SP costs are colour-coded by resource
(`.srow .cost{color:var(--vit-mp)}`, `.cost.sp{color:var(--vit-sp)}`) while a free cast reads in muted
grey (`.cost.free{color:var(--paper-500)}`), the `combat` OOC pill has an exact bordered-pill treatment
(`font-size:9px;color:var(--ok);border:1px solid rgba(112,150,122,.5);border-radius:4px;padding:0 4px`),
a passive/proficiency badge (`.prf`) reads in muted mono type, and a one-line legend above the list
explains the grouping/OOC/hidden-content conventions before the first category. `SkillBook.vue` today
renders none of this: categories show only their label (no count, no chevron), groups show only a
plain-text label (no dot), every cost cell shares one grey style regardless of resource or free-ness,
there is no legend, and (per the companion `fix-webclient-skillbook-descriptor-data` change, which adds
the underlying `usable_out_of_combat`/enriched-cost data this proposal's styling consumes) the `combat`
pill exists but with only placeholder styling.

This is the last visual gap between the live 技能書 and the design draft once the drawer chrome
(`fix-webclient-skillbook-drawer-chrome`) and the descriptor data
(`fix-webclient-skillbook-descriptor-data`) land: everything left is CSS and small template additions
against data both companion changes already establish. Every colour used below is an existing
`tokens.css` custom property — no new token is introduced, and (see Design) the element-dot colours are
seeded only for the three elements the design draft actually samples, so nothing is invented for the
five elements it never shows.

## What Changes

- `SkillBook.vue`'s category `<summary>` gains a trailing skill count (`{n}`, the category's own
  flattened skill count — already computed today, just not rendered) and a `›` chevron
  (`data-testid="skill-book__category-chevron"`) that rotates 90° when the `<details>` is open, via a
  CSS `transition: transform` on `details[open] > summary` — matching the design's own mechanism (no JS
  state needed, `<details>`'s native `open` attribute already drives it).
- `SkillBook.vue`'s group label gains a small square colour dot (`data-testid="skill-book__group-dot"`)
  when the row's `category` is `elemental_magic` and its `group` key is one of the three the design
  draft samples (`fire` → `var(--seal-500)`, `water` → `var(--vit-mp)`, `wind` → `var(--warn)` — all
  three already exact byte-matches of the draft's inline hex, confirmed against `tokens.css`), or when
  `category` is `sexual_act` (uniformly `var(--seal-500)`, matching every one of the draft's sexual-act
  line groups). A group whose element the draft never sampled (earth/lightning/ice/light/dark) renders
  its label with no dot — nothing invented for a colour the design never specified.
- `SkillBook.vue`'s cost cell colour-codes by resource: an `mp`-only cost reads `var(--vit-mp)`, an
  `sp`-only or mixed cost reads `var(--vit-sp)` (matching the draft's `.cost.sp` override, which wins
  when a row spends `sp` at all), and a free cast (`{}` or absent) reads `var(--paper-500)` — matching
  the draft's `.srow .cost` / `.cost.sp` / `.cost.free` rules exactly.
- `SkillBook.vue`'s `combat` OOC pill (added with placeholder styling by
  `fix-webclient-skillbook-descriptor-data`) is restyled to the draft's exact `.srow .ooc` rule:
  `font-size:9px; letter-spacing:.04em; color:var(--ok); border:1px solid rgba(112,150,122,.5);
  border-radius:4px; padding:0 4px; margin-left:8px`.
- `SkillBook.vue`'s passive tab rows gain a trailing `被動` badge (`data-testid="skill-book__passive-badge"`,
  styled per the draft's `.prf` rule: muted mono type) — this is a static, client-known label (the tab
  itself is already "被動"), not new payload data.
- `SkillBook.vue` gains a one-line legend (`data-testid="skill-book__legend"`) above the active-tab
  category list, matching the draft's exact markup (`index.html:892`:
  `依分類分群；<span style="color:var(--ok)">戰鬥外</span> 表示非戰鬥亦可施放；未解鎖之性愛行為「藏而不列」。`)
  — a plain `color: var(--ok)` inline span around the Chinese phrase `戰鬥外`, **not** the bordered
  `.ooc` pill (that pill reads the English word "combat" and sits next to each skill row, per
  `index.html:895`; it is a different UI element from the legend's plain-colored word). Client-authored
  UI copy describing the list's own grouping/OOC/hidden-content conventions, not narrative or story
  content. Rendered only on the active tab (the draft shows it only above `#sk-active`).

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `webclient-component-showcase`: the "status, character, and skill surfaces present truthful,
  non-color-only state" requirement is amended so the skill book's category summaries, group labels,
  cost cells, and OOC pill are described as never conveying their meaning by colour alone (each pairs a
  colour with a text/shape cue: the count digit, the resource-unit suffix already in the cost text, the
  pill's own text and border, the badge's own text), and so an unsampled element's group renders with no
  invented dot colour.

## Impact

- `web/webclient-app/components/SkillBook.vue`: template additions (chevron, dot, legend, passive
  badge) and CSS additions/edits (cost colour-coding, `.ooc` pill exact styling, chevron rotation); no
  script-logic change beyond a small `groupDotColor(row)` / `costColorClass(row)` helper.
- `web/webclient-app/stories/fixtures.js`: `SKILLS_SLICE_SAMPLE` gains at least one `sp`-costing row and
  keeps its existing `water`/`fire` groups so the dot-colour and cost-colour-coding stories are provable
  offline.
- Tests: `web/webclient-app/tests/data/skill_book.test.js` (chevron rotates with `open`, dot renders only
  for the three sampled elements and for `sexual_act`, cost colour class matches resource, OOC pill
  carries the exact draft styling, passive badge renders on the passive tab, legend renders only on the
  active tab).
- Player-facing command surface is unchanged, so `docs/game/commands.md` /
  `docs/game/command-reference.md` and `tests/test_command_docs.py` need no update.
- Spec-test traceability: the amended requirement keeps a substantively matching test (the extended
  `skill_book.test.js` cases); `tools.spec_traceability check` must stay green.
- **Depends on** `fix-webclient-skillbook-descriptor-data` (the `usable_out_of_combat`/cost/target data
  and the OOC pill's existence) landing first; this change only restyles what that change already
  renders. Independent of `fix-webclient-skillbook-drawer-chrome` (no shared file — that change owns
  `HudDrawer.vue`/the drawer head; this one owns only `SkillBook.vue`'s internal row/category markup).
