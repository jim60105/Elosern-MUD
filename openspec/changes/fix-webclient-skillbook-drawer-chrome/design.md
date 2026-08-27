## Context

`HudDrawer.vue` is the single shared chrome for all six reference drawers (skill, inventory, shop,
quest, lore, status), mounted by `AppClient.vue` with `:title="drawerTitle"` and no `subtitle`/`icon`
today. `SkillBook.vue` is the only one of the six panel components that renders its own redundant
`<h3>` title inside the drawer body — `InventoryPanel.vue`, `ShopPanel.vue`, `QuestBoard.vue`,
`LoreDrawer.vue`, and `CharacterStatusDrawer.vue` do not (confirmed: `grep -rn
"skill-book__title\|skill-book__counts"` matches only inside `SkillBook.vue` itself and one existing
test, `web/webclient-app/tests/data/skill_book.test.js:38`, which asserts the `skill-book__counts`
text — that assertion is removed by tasks.md §5.2; no other component matches).

`DockTabBar.vue:133` already shows the complete glyph-rendering pattern this design follows:
`v-bind="glyphAttrs(tab.key)"` bound onto the `<path>` alongside `:d="glyphPath(tab.key)"`, so a glyph's
per-key stroke attributes (e.g. the new `close` key's `stroke-linecap: round`) actually apply.
`QuickWordChips.vue`'s simpler `:d`-only usage (no `glyphAttrs`) is the wrong precedent to follow for
the close icon specifically, since the design's close glyph needs its rounded caps to render
correctly.

`dock-icons.js` already exports `GLYPHS`, `glyphAttrs`, `glyphPath`, and `glyphSvg`. `glyphPath(key)` is
the pattern already consumed directly in a template (`QuickWordChips.vue`: `import { glyphPath } from
"./dock-icons.js"`, then a hand-written `<svg><path :d="glyphPath(key)" stroke="currentColor"
stroke-width="1.8" /></svg>`). `glyphSvg(key, size)` is a different, heavier helper that returns a
render-object tree including a wrapping `<circle>` stroke ring around the glyph — appropriate for a
circular icon-button context, not for a plain inline head icon the design draws with no ring. This
design follows `QuickWordChips.vue`'s `glyphPath()` pattern, not `glyphSvg()`.

## Goals / Non-Goals

**Goals:**
- Collapse the double "技能書" heading into one, sourced from `HudDrawer`'s own head.
- Give the skill drawer the design's icon + subtitle + icon-only close control + full-width tabs +
  search icon + footer cast-hint, reusing existing shared infrastructure (`dock-icons.js`, the `foot`
  slot) rather than inventing new mechanisms.
- Keep the close-control and icon changes to `HudDrawer.vue` **backward compatible with the other five
  drawers** — an unset `icon` prop renders nothing new, and the close-control change is the one
  genuinely shared, uniform improvement (matching the design draft's own `.closebtn`, which is
  identical across every one of its seven drawers, not just `#dr-skill`).

**Non-Goals:**
- No icon assignment for the other five drawers (inventory/shop/quest/lore/status). Sourcing and
  verifying five more glyph mappings against the design draft is out of this change's one-workday
  budget and out of the user's stated "skill-book" focus; `icon` stays unset for them, which is a no-op
  on `HudDrawer`'s existing rendering.
- No change to drawer open/close mechanics, focus trap, Escape handling, or the scrim — the "one modal
  contract" requirement's behavioral scenarios (focus trap, single-drawer, reduced-motion) are untouched;
  only the close control's *presentation* (icon vs. text) changes, not its behavior.
- The search field's border/background move to the new `.skill-book__search-wrap` container so the
  field reads as one single-bordered control (matching the draft's `.searchbox`), not a bordered input
  nested inside a bordered wrapper; only the input's `data-testid`, `placeholder`, and `v-model` binding
  are unchanged, not its box styling.
- No new `dock-icons.js` table entry for the search-field icon. It is used nowhere else in the app
  (unlike `skills`, which is already shared by the dock tab, the quick-word chip, and now the drawer
  head), so a local inline SVG in `SkillBook.vue` is proportionate; adding a shared-table entry for a
  single consumer would be premature generalization.
- No row/category-level visual changes (colour dots, count+chevron summaries, free-cost styling, the
  legend caption, the OOC pill's final styling). Those are `fix-webclient-skillbook-row-visual-language`
  (a separate, independently-schedulable change) — bundling chrome and row-level visuals here would
  exceed the one-workday budget.

## Decisions

- **`icon` is a prop on `HudDrawer`, not a new wrapper component.** The six drawers already share one
  component; adding one optional prop keeps that sharing intact and costs the other five drawers
  nothing (unset prop → unchanged render), versus a skill-specific drawer variant that would fork the
  shared focus-trap/scrim/slide logic `webclient-contextual-hud`'s "one modal contract" requirement
  already pins down for all six.
- **Glyph rendering follows `DockTabBar.vue`'s `v-bind="glyphAttrs(key)"` pattern, not
  `QuickWordChips.vue`'s bare `:d` usage.** Both the head icon and the close icon bind
  `v-bind="glyphAttrs(icon)"` / `v-bind="glyphAttrs('close')"` on their `<path>` alongside `:d`, so the
  new `close` key's `stroke-linecap: round` (design draft: `M6 6l12 12M18 6 6 18`,
  `stroke-linecap="round"`) actually renders rounded, matching the reference exactly instead of
  silently falling back to square caps.
- **`.hud-drawer__icon` gets its own explicit size/color CSS, matching the draft's `.dhead .ic`
  (`docs/design/elosern-redesign/index.html:409-410`: `width:20px;height:20px;color:var(--gold-400)`).**
  Left to inherited `currentColor` it would render in the title's paper-toned color, not the draft's
  gold accent — a visible fidelity gap in a change whose entire purpose is chrome fidelity.
- **The close control keeps its accessible name as `aria-label`, not visible text.** The design's own
  `.closebtn` is icon-only with `aria-label="關閉"` implied by context (no visible text node in its
  markup); `HudDrawer.vue`'s current button already has the exact string "關閉" as its only content, so
  moving that string to `aria-label` while swapping the content for the icon preserves the exact same
  accessible name — screen-reader behavior is unchanged, only the visual presentation changes. Confirmed
  no existing test asserts the button's visible text (`grep -n "關閉" web/webclient-app/tests/hud_drawer.test.js`
  found no match), so this is a safe, low-blast-radius swap.
- **The skill-count subtitle is computed in `AppClient.vue`, not inside `HudDrawer.vue` or re-added to
  `SkillBook.vue`.** `AppClient.vue` already calls `panel('character')` to build the `:skills` prop it
  passes to `SkillBook`; counting `actives`/`passives` rows there (the same counting logic
  `SkillBook.vue`'s own `skillCount()` performs today, moved up one level) keeps `HudDrawer` a dumb
  presentational shell (no panel-shape knowledge) and keeps `SkillBook.vue` focused on rendering the
  list rather than the chrome around it — the same separation the drawer/panel split already
  establishes for every other drawer (e.g. `ShopPanel` never computes its own drawer title).
- **The footer hint is static client copy, not OOB data.** `施放入口：cast <技法>[@威力]=<代號>`
  describes the client's own already-existing `/cast` command syntax (unchanged by this proposal); it
  is authored the same way `HelpOverlay`'s control reference is authored (per
  `webclient-component-showcase`'s existing rule that the help overlay "SHALL therefore render the
  client's own control reference, which the client authoritatively knows, and no authored game-help
  content") — knowledge the client has about itself, not narrative or story content.

## Risks / Trade-offs

- **Changing a shared component's close control affects all six drawers at once.** → This is the one
  deliberately shared part of the change (the design draft itself is uniform here); every existing
  `hud_drawer.test.js` interaction test (open/close/focus-restore) is re-run unchanged since the
  control's *behavior* (click → close, Escape → close, focus returns) is untouched, only its markup.
- **`.hud-drawer__close`'s CSS (padding, min width) was sized for a two-character text label** and needs
  adjusting for an icon-sized square button so the click/tap target does not shrink below the existing
  size — verified during implementation against the existing `min` touch-target expectations the
  contextual-hud spec's accessibility scenarios imply.
- **A future drawer added without an `icon` prop silently renders with no head icon** — this is the
  correct default (matching today's five other drawers), not a gap; the requirement text says a head
  icon MAY be present, not that every drawer needs one.

## Migration Plan

Not applicable — 0 released users, purely a view-layer chrome change with no persisted state or OOB
schema involved.

## Open Questions

None outstanding.
