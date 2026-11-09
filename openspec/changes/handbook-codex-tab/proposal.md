# Proposal: handbook-codex-tab

## Batch: handbook-codex-titles (change 4 of 4)

- depends-on: lore-codex-schema-v2
- depends-on: handbook-titles-tab
- conflict: `handbook-titles-tab` introduces the handbook dispatcher, `handbook-tabs.js`, `openHandbook`, `TileWall.vue`, `CodexDetail.vue`, `CodexEmblem.vue` and `DetailFooter.vue`, and this change extends all of them. This change's `webclient-quest-drawer` and `webclient-desktop-shell` deltas are written against that change's archived text. The design's §3 lists only "4 depends on 3", but the codex tab cannot exist without the handbook shell, so the dependency on change 1 is added here as a sequencing fact. No design decision changes.
- conflict: `lore-codex-schema-v2` supplies the v2 payload and the interim v2 read in `LoreCodexDrawer.vue`, which this change deletes.
- conflict: `lore-species-research`: indirect only (through change 3).

## Why

The approved design `docs/superpowers/specs/2026-11-09-handbook-codex-titles-design.md` (D1, D2, D3, D4, D6, D7, D10, §5) replaces the world-codex drawer with an MHW hunter's-notes tab inside the handbook. It shows a grouped tile wall with silhouette placeholders, a hero image per entry, and a two-stage monster research state. The server side (`lore_codex` v2) is delivered by `lore-codex-schema-v2`. This change is the client surface that consumes it, and it removes the drawer.

## What Changes

- New handbook first-level tab `codex` (圖鑑), placed before `titles`. In combat the tabs are 圖鑑 and 稱號 only.
- New `components/handbook/LoreCodexTab.vue`. Its rail (`IconTabs` with labels) holds the eight categories with discovered-count badges. Beside it are `CodexTileGrid.vue` (grouped tiles over the shared `TileWall`) and the shared `CodexDetail.vue`, extended with hero art, a stage stamp, a two-step research track and locked-field boxes.
- New pure model `components/handbook/lore-codex-model.js` (payload → rail, groups, tiles, detail) and a v2 field-label map that replaces `lib/codex_field_label.js`.
- Codex category emblems are added to `CodexEmblem.vue`. The hero renders the slot's art descriptor through the shared `useArtwork` attempt lifecycle and falls back to the emblem.
- Stage marks: a defeated tile has a filled diamond, a sighted tile a hollow diamond with desaturated art, and a placeholder is a hatched tile marked ？. A legend pinned to the bottom edge of the monster wall uses fixed `12px × --ui-scale` marks (approved fix `08406a57`).
- The 圖鑑 tool opens the handbook on its codex tab through the same route request as 稱號冊.
- Session memory gains the codex category and the per-category selection.
- **BREAKING (internal, pre-release):** `LoreCodexDrawer.vue`, its story, its vitest suite, `lib/codex_field_label.js` and the `lore` HudDrawer branch and drawer name are removed.

## Capabilities

### New Capabilities

- none

### Modified Capabilities

- `webclient-lore-codex-panel`: the three drawer requirements are removed. New requirements cover the codex tab's tile wall, stage marks and legend, locked-field boxes, hero-art fallback, honest degradation and reference-viewport geometry.
- `webclient-quest-drawer`: the first-level tab set gains the codex tab, in and out of combat.
- `webclient-desktop-shell`: 圖鑑 opens the handbook codex tab instead of the `lore` drawer.
- `webclient-contextual-hud`: the "no art column" rule no longer applies to the codex, whose hero shows only the entry's own art or emblem, and the empty-codex guidance sits beside the placeholder wall.

## Impact

- Client only: new `components/handbook/LoreCodexTab.vue`, `CodexTileGrid.vue`, `CodexArt.vue`, `lore-codex-model.js`. Edited: `CodexDetail.vue`, `CodexEmblem.vue`, `components/dock-icons.js`, `handbook-tabs.js`, `QuestDrawer.vue`, `quest-drawer-memory.js`, `nav-tools.js`, `stores/elosern/hud.js`, `composables/use-drawers.js`, `AppClient.vue`. Deleted: `LoreCodexDrawer.vue`, `lib/codex_field_label.js` and their stories and tests.
- Tests: new vitest suites, an evidence bridge, a live-client browser journey with geometry at 1451×790 and 2560×1440 (registered in `.github/browser-shards.json`), updated codex browser tests, the component manifest and showcase evidence lists, and the frozen-contract audit.
- Docs: `docs/game/commands.md` (top-bar paragraph).
- No server or protocol change.
- Human-reviewed: the visual-fidelity and copy review in `design.md` § "Review document (human-reviewed)".
