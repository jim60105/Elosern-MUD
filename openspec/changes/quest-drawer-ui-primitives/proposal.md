# Proposal

## Why

The approved quest drawer redesign (`docs/superpowers/specs/2026-10-09-quest-drawer-redesign-design.md`, §3.2–§3.4, §3.7, §3.9; visual reference `docs/design/quest-drawer-redesign/`) is built from a few reusable pieces: icon-only tabs that work horizontally and vertically, a grade gem, a set of new line glyphs, and the existing rank block as its own component. Building and showcasing them first, as real components in the codebase with real Storybook stories, lets the two drawer changes compose them, and lets the visual language be reviewed in Storybook before any wiring.

## What Changes

- New `IconTabs.vue`: an icon-only tablist with `horizontal` and `vertical` orientations, roving tabindex, arrow/Home/End keys, a tooltip on hover and focus, count badges with a "hot" variant, and disabled (focusable, with a reason) and locked states. A slot accepts a custom icon such as a grade gem.
- New `GradeGem.vue`: the rotated-square grade seal in `sm`, `md`, and `lg`, with the F→S material ladder.
- New glyphs in `components/dock-icons.js`: quest book, guild counter, the three quest states, the five quest categories, track flag, copper, merit, item, deadline, and lock.
- New `GuildRankCard.vue`: the rank block extracted verbatim from `GuildCounter.vue` (crest, merit meter, met/short status, exam request). `GuildCounter.vue` now renders it. The only change is replacing two literal transition durations with `--motion-*` tokens, which fixes the `tests/motion_tokens.test.js` failure currently on `master`.
- Storybook stories for all three components under `web/webclient-app/stories/` (`Core/IconTabs`, `World/GradeGem`, `World/GuildRankCard`), registered in `component-manifest.json`. The rank-block variants move from the GuildCounter stories to GuildRankCard. The showcase evidence tests that pin the manifest key sets are updated.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This change adds unwired building blocks and a behavior-preserving extraction, so no spec-level behavior changes (`skip_specs: true`). The tab behaviors become contractual in `quest-drawer-book-tab`, where the drawer first uses them.

## Impact

New `web/webclient-app/components/IconTabs.vue`, `GradeGem.vue`, `GuildRankCard.vue`, and `grade-materials.js`; `components/dock-icons.js`; `components/GuildCounter.vue`; new stories and Vitest files; `stories/World/GuildCounter.stories.js`; `component-manifest.json`; `web/webclient/tests/test_vue_showcase_{evidence,world_evidence,data_evidence,action_evidence,overlays_evidence}.py` key sets; `tests/dock_icons.test.js`.

## Non-goals

No drawer wiring, no payload change, no change to the rank block's look or behavior beyond the motion-token fix, and no change to existing tab components elsewhere in the client.

## Batch:

```text
depends-on: (none)
code-conflicts: guild-board-structured-offers (GuildCounter.vue), quest-drawer-book-tab and quest-drawer-guild-board-tab (component-manifest.json, showcase evidence key sets)
```

Batch 1, in parallel with `quest-log-structured-rows`. It must merge before `quest-drawer-book-tab` and `quest-drawer-guild-board-tab`, which compose these components.

Archive strictly in this order: `quest-log-structured-rows` → `guild-board-structured-offers` → `quest-drawer-book-tab` → `quest-drawer-guild-board-tab`. `quest-drawer-ui-primitives` has no deltas and can archive any time after it merges. Any other order fails `openspec archive`: `quest-drawer-book-tab` REMOVES a requirement that `quest-log-structured-rows` MODIFIES, and `quest-drawer-guild-board-tab` adds to the capability that `quest-drawer-book-tab` creates and REMOVES a requirement that `guild-board-structured-offers` adds.

## Worker profile

**Visual.** Assign a worker with visual ability: one that can read screenshots, use `agent-browser`, and judge pixel parity against the `Design/QuestDrawerRedesign` prototype. The work is tab, gem, and glyph geometry matched to the prototype, plus side-by-side Storybook captures (task 4.2).

## Size and standalone delivery

About 6 hours: IconTabs with keyboard and tooltip behavior and tests (2.5h), GradeGem and glyphs (1h), the GuildRankCard extraction and story moves (1h), the manifest and showcase evidence updates (1h), and Storybook visual review against the prototype (0.5h). It is deployable alone: the live client behaves identically and the motion-token gate turns green.
