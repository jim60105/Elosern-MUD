# Proposal: handbook-primitives

## Batch: handbook-codex-titles (change 1a of the design's four; split from change 1 after review because change 1 was larger than one workday)

- depends-on: none
- conflict: `handbook-titles-tab` and `handbook-codex-tab` consume and extend every component this change adds. Both must land after it.
- conflict: none with `lore-species-research` or `lore-codex-schema-v2` (disjoint files).

## Why

The approved design `docs/superpowers/specs/2026-11-09-handbook-codex-titles-design.md` (§5.1) requires both handbook tabs to share one detail column, one grouped tile wall, one emblem set and the quest detail's pinned action footer. The footer must be extracted from `QuestDetail.vue` rather than copied, and `ActionBar` is not used. Landing these shared parts first, with their own tests and stories, keeps each later change within one workday. It also proves the footer extraction leaves the quest window unchanged before anything else builds on it.

## What Changes

- Extract the pinned footer of `QuestDetail.vue` into `web/webclient-app/components/DetailFooter.vue`. `QuestDetail` renders through it with the same testids and the same focus behavior.
- Add `components/handbook/TileWall.vue`: a grouped listbox with one roving tab stop, reading-order arrow keys and non-selectable focusable items.
- Add `components/handbook/CodexEmblem.vue`, with stroke emblems for the title categories, epithet, ballot and unknown, stored in `components/dock-icons.js` as `emblem_<name>`.
- Add `components/handbook/CodexDetail.vue`: the shared detail column (hero band with emblem or medal, ribbon, title, subtitle, sections, stamp, and a `DetailFooter` pinned at the bottom).
- Add Storybook stories for the four components and register them in the component manifest.

## Capabilities

### New Capabilities

- none

### Modified Capabilities

- `webclient-window-primitives`: adds the `TileWall` roving-focus contract and the `DetailFooter` contract.

## Impact

- Client only: `components/QuestDetail.vue` and the new `components/DetailFooter.vue`, `components/handbook/{TileWall,CodexEmblem,CodexDetail}.vue` and `components/dock-icons.js`. Also stories, `component-manifest.json`, the showcase evidence lists and a new evidence bridge `web/webclient/tests/test_vue_handbook_evidence.py`.
- No visible change to any shipped surface. The new components are not mounted by the app until `handbook-titles-tab`.
- Human-reviewed: none. The footer must look identical to the current quest footer, which the existing quest-drawer browser tests and the review document of `handbook-titles-tab` cover.
