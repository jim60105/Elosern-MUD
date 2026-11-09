# Proposal: handbook-titles-tab

## Batch: handbook-codex-titles (change 1 of 4)

- depends-on: none
- conflict: `handbook-codex-tab` modifies the same `webclient-quest-drawer` and `webclient-desktop-shell` requirements again, and edits `QuestDrawer.vue`, `quest-drawer-memory.js`, `nav-tools.js`, `stores/elosern/hud.js` and `AppClient.vue`. It is written against this change's archived text and must land after this change.
- conflict: none with `lore-species-research` or `lore-codex-schema-v2` (server-only; disjoint files).

## Why

The approved design `docs/superpowers/specs/2026-11-09-handbook-codex-titles-design.md` (D1, D2, D8, D9, D10) folds the title book into the quest window, renamed 手帳. Today the title book is a separate overlay (`TitleCodexPanel.vue`) with its own markup, while the quest window already has the rail, list and detail columns plus the pinned action footer that the title book needs. This change is the first of four in the design's §3 Delivery. It has no server dependency because the `title_codex` v1 payload stays unchanged.

## What Changes

- The quest window (`QuestDrawer`, hotkey J) is renamed 手帳 (window title and primary navigation label). It gains a `titles` first-level tab after 任務簿 and 公會櫃檯.
- New `components/handbook/TitleCodexTab.vue`. Its rail lists the six fixed-title categories, a divider, 異名, and 提名 (提名 is present only while a ballot is pending). Fixed titles render as a medal wall (`CodexMedalGrid.vue` over a shared roving-focus `TileWall.vue`). Epithets and nominees render as `QuestList` rows. The detail is a shared `CodexDetail.vue`.
- The quest detail's pinned action footer is extracted from `QuestDetail.vue` into a shared `components/DetailFooter.vue`. Both `QuestDetail` and `CodexDetail` use it. `ActionBar` is not used.
- Equip, the two-step epithet removal and the ballot answers go out through that footer as the existing `title.equip`, `title.remove`, `title.accept` and `title.decline` intents. While removal is armed, any close attempt (Escape, ✕, scrim) cancels it through the drawer's `closeGuard`.
- The 稱號冊 tool shortcut opens the handbook on its `titles` tab through the existing `routeRequest` mechanism, carried by the store's `serviceReadRequest` slot with a new `handbook` slot value.
- In combat the handbook is reachable only through the tool shortcut and shows only the `titles` tab (the 圖鑑 tab joins in `handbook-codex-tab`).
- New `components/handbook/CodexEmblem.vue` stroke emblems for the title categories, epithet and ballot. Codex category emblems are added later by `handbook-codex-tab`.
- **BREAKING (internal, pre-release):** `TitleCodexPanel.vue`, its story and its vitest suite are removed, along with the `codex` overlay name and the `OverlayHost` `codex` branch.

## Capabilities

### New Capabilities

- none

### Modified Capabilities

- `webclient-quest-drawer`: the first-level tab set becomes 任務簿/公會櫃檯/稱號 outside combat and 稱號 alone in combat. A tab route request is added. New requirements cover the titles tab rail, equip, two-step removal with close-guard cancellation, ballot answers, honest degradation and reference-viewport geometry.
- `title-system`: the "codex OOB payload and WebClient window" requirement now names the handbook titles tab instead of the big-window overlay. The payload is unchanged.
- `webclient-desktop-shell`: the tool-group requirement now states that 稱號冊 opens the handbook on its titles tab instead of the title-codex overlay.

## Impact

- Client only: `web/webclient-app/components/QuestDrawer.vue`, `QuestDetail.vue`, new `DetailFooter.vue`, new `components/handbook/` (`TitleCodexTab.vue`, `CodexMedalGrid.vue`, `TileWall.vue`, `CodexDetail.vue`, `CodexEmblem.vue`, `title-codex-model.js`), `quest-drawer-memory.js`, `nav-tools.js`, `nav-primary.js`, `DesktopNavigation.vue`, `composables/use-drawers.js`, `stores/elosern/hud.js`, `AppClient.vue`. The removed `TitleCodexPanel.vue` and its story and test are deleted.
- Tests: new vitest suites, the rewritten browser test `web/tests/browser/test_browser_title_codex.py` plus a live-client geometry journey (shard manifest `.github/browser-shards.json`), the Storybook component manifest and the showcase evidence lists, and the frozen-contract audit (`docs/development/webclient-vue-frozen-contract-audit.md`).
- Docs: `docs/game/commands.md` (the top-bar paragraph: 手帳 label and the 稱號冊 shortcut).
- No server, protocol or payload change. `title_codex` v1 and its validators are untouched.
- Human-reviewed: the visual-fidelity and copy review listed in `design.md` § "Review document (human-reviewed)". No automated requirement covers it.
