# Design: Shared window primitives

## Context

See proposal.md. `QuestDrawer.vue` composes `HudDrawer.vue` (modal focus trap, Escape, motion), `IconTabs.vue` (first/second-level icon tabs with tooltips and keyboard), `QuestList.vue`/`QuestDetail.vue` (list/detail) and an action bar. The prototype CSS (`.pm-head`, `.pm-rail`, `.pm-body`, `.pm-actions`, `.pm-holdings`) defines the approved spacing, colours and glyph geometry. `component-manifest.json` is frozen and grows only through a governed wave.

## Goals / Non-Goals

**Goals:** five reusable, story-covered, keyboard-tested primitives matching the prototype; no behaviour invented beyond what the payloads carry.

**Non-Goals:** restyling the quest drawer or other windows (design §13), live wiring.

## Decisions

- **WindowFrame wraps HudDrawer** rather than duplicating its focus code; header extras are a named slot.
- **MemberRail** takes plain props (`members[]` with `id`, `name`, `portrait`, `knockedOut`, `unread`; `emptySlot`), emits `select(id)`; roving tabindex like `IconTabs`; the selected entry has `aria-current`.
- **HoldingsStrip** takes `rows` in the `item_holdings` row shape plus `combat` (counts only) and emits `give(memberId)`; it renders `delta.changes` with ▲/▼ shape prefixes so signs are never colour-only.
- **Styles** are ported from `prototype.css` into scoped SFC styles with tokens; no `.elosern-root` duplicate rules are introduced.
- **Manifest** titles: `Core/WindowFrame`, `Core/MemberRail`, `Core/ListDetail`, `Core/ActionBar`, `Data/HoldingsStrip`.

## Risks / Trade-offs

- [Primitives drift from the prototype] → Stories reproduce the prototype states and are reviewed side by side at both viewport sizes.

## Migration Plan

Additive; revert the implementation commit.

## Verification and documentation ownership

Vitest: rail arrow/Enter/Space/Home/End, knocked-out text, unread accessible name, 空位 entry; tabs reuse; action bar reason slot; holdings strip no-invention and combat counts-only; token-only sizes. Storybook build and showcase coverage. `web/webclient-app/AGENTS.md` gains a short primitives section.
