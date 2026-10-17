# Proposal: Shared window primitives

## Why

Design §9 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: the party window and the shop reuse the quest drawer frame through shared primitives (`WindowFrame`, `MemberRail`, `ListDetail`, `ActionBar`, `HoldingsStrip`, with `IconTabs` reused unchanged), and the prototype's new glyphs join `dock-icons.js`. The approved visual source is `docs/design/party-member-management/prototype.css` and `glyphs.js`.

## What Changes

- New Vue SFCs in `web/webclient-app/components/`: `WindowFrame.vue` (seal, title, `IconTabs`, header extras, close; wraps `HudDrawer`'s focus/motion contract), `MemberRail.vue`, `ListDetail.vue`, `ActionBar.vue`, `HoldingsStrip.vue`, each with a Storybook story at 1451×790 and 1920×1080, deterministic offline args in the party v3 / item_holdings shapes, and Vitest keyboard tests.
- New glyphs (member, status, potion, sword, hammer, bow, shield, armor, staff, amulet, ration, scroll, herb, holy, ice, wind, buff, debuff, slot_empty, plus, minus, give, knocked_out) added to `dock-icons.js` from the prototype's `glyphs.js`.
- The governed-wave requirement of `webclient-component-showcase` names this series; the manifest gains the five primitives.
- No live wiring yet (the window shell is the next change).

## Capabilities

### New Capabilities

- `webclient-window-primitives`: behaviour contracts of the five primitives and their sizing/motion rules.

### Modified Capabilities

- `webclient-component-showcase`: the governed redesign wave requirement admits this series' additions and deletions.

## Impact

- New components and stories under `web/webclient-app/components/` and `web/webclient-app/stories/Core|Data/`, `component-manifest.json`, `components/dock-icons.js`, Vitest files under `web/webclient-app/tests/`.
- Gates: `pnpm test` (touched files), `pnpm run build-storybook`, `pnpm run showcase-coverage`.

## Effort

**7 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **21 of 31**.

- depends-on: party-panel-v3-view-member
- depends-on: item-holdings-panel
- depends-on: lineage-panel-v2-graphs

### Code and spec conflicts within the new batch

- Every later client change composes these primitives (D) and appends manifest titles in `component-manifest.json` (F; ordered, append/remove only).
- `webclient-component-showcase`: later client changes re-modify other showcase requirements (S; distinct requirements).
- `dock-icons.js`: `webclient-main-navigation-hotkeys` may reuse glyph keys (D).

### Active change coordination

No active OpenSpec change. `IconTabs`, `GradeGem` and `GuildRankCard` already exist and are reused unchanged.
