# Proposal: webclient-lore-codex-drawer

## Why

The `世界圖鑑` button sits inside the quest drawer and opens `LoreDrawer.vue`, which renders guild
quest prose rather than the codex — its own header comment admits the codex "has no OOB read model in
this payload, so the drawer never fabricates codex cards (a deliberate skip)". So the button is both
misplaced and non-functional.

Misplaced, because the codex is world knowledge, not a guild service: it has no dependency on quests
and no reason to be reachable only through the quest drawer. Non-functional, because there was no
read model — which `webclient-lore-codex-panel` now supplies.

## What Changes

- New `LoreCodexDrawer.vue` rendering the `lore_codex` panel, following the redesign draft's
  `dr-lore` aside: a header reading `圖鑑 · 僅已發現 · 8 類`, a category pill row carrying each
  category's discovered count, an entry list for the selected category, and an entry card — two
  levels of navigation, all local, with an "all" pill aggregating every discovered entry.
- The redesign draft's placeholder category names are superseded by the eight implemented categories:
  種族 / 國家 / 地域 / 魔物 / 元素 / 魔法 / 地點 / 公會.
- Empty categories render as zero-count pills; the panel discloses no registry size, so neither does
  the drawer. An entirely empty codex renders an honest empty state.
- `LoreDrawer.vue` is deleted. Its guild quest prose is duplicated by the quest book and is not
  carried over.
- New `.cmdutil` icon opening the codex drawer, making `.cmdutil` five icons: 技能系譜, 圖鑑, 稱號冊,
  設定, 說明. The four existing icons open overlays; this one opens a drawer, which the store's
  `openHudDrawer` already supports.
- The `世界圖鑑` button is removed from `QuestBoard.vue`.
- The glyph must be clearly distinguishable from the adjacent 稱號冊 icon: the title codex
  (`title_codex`, epithets) and the world codex (`lore_knowledge`, world knowledge) are separate
  systems sitting side by side.
- New test identifiers registered in the frozen contract audit §2.3.

## Capabilities

### New Capabilities

(None. The codex read model's contract is owned by `webclient-lore-codex-panel`; this change adds its
client surface, so its requirements belong to that capability.)

### Modified Capabilities

- `webclient-lore-codex-panel`: gains the client surface requirements — the drawer's composition and
  navigation, its non-disclosure rendering rules, and the command-line trigger. One of those
  requirements states that no control inside the quest drawer opens the codex, which is where the
  removal is pinned.

(`webclient-service-menus` needs no delta: no requirement anywhere describes the quest drawer's codex
button — it was an implementation detail of the reference-drawers task, so removing it changes no
requirement's behavior. `webclient-contextual-hud`'s reference-drawer requirements name the lore
drawer only as one of the drawers that must not exist while closed, which is unaffected.)

## Impact

- New `web/webclient-app/components/LoreCodexDrawer.vue`; `LoreDrawer.vue` and its story deleted.
- `web/webclient-app/components/CommandLine.vue`: the fifth `.cmdutil` icon and its emit.
- `web/webclient-app/AppClient.vue`: drawer body wiring and the command-line handler; the `lore`
  drawer name is already in the store's closed drawer-name set, so no store change is needed.
- `web/webclient-app/components/QuestBoard.vue`: the `世界圖鑑` button removed.
- New Storybook story; browser tests for the new trigger and drawer.
- `docs/development/webclient-vue-frozen-contract-audit.md` §2.3 gains the new identifiers.
- **Conflicts with `webclient-quest-drawer-split`** on `AppClient.vue`, `QuestBoard.vue`, and the
  audit document. Land this change FIRST, then the quest drawer split.
