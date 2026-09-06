# Tasks: webclient-lore-codex-drawer

## 1. LoreCodexDrawer.vue

- [ ] 1.1 New `web/webclient-app/components/LoreCodexDrawer.vue` taking the committed `lore_codex`
  panel. Render the registry-owned unavailable reason and no codex content when the panel is
  unavailable.
- [ ] 1.2 Category strip: one control per shipped category showing its label and its discovered
  count, plus an aggregate control covering every discovered entry. Zero-count categories render as
  zero-count controls. Show no registry total, denominator, percentage, or placeholder entry.
- [ ] 1.3 Entry list for the selected category; entry card rendering the panel's card fields in the
  panel's order, unmodified.
- [ ] 1.4 Two-level navigation entirely local: selecting a category or an entry dispatches nothing
  and fetches nothing.
- [ ] 1.5 Empty-codex state when every category ships empty.
- [ ] 1.6 Layout follows the redesign draft's `dr-lore` aside
  (`docs/design/elosern-redesign/index.html`): header `圖鑑 · 僅已發現 · 8 類`, pill row, entry rows,
  card. The draft's placeholder category names are superseded by the eight implemented categories.
- [ ] 1.7 Stable `data-testid` on the surface, each category control, each entry row, and the card.

## 2. Command-line trigger

- [ ] 2.1 Add the fifth `.cmdutil` icon in `web/webclient-app/components/CommandLine.vue` with an
  accessible label, emitting a drawer-open request. Order: 技能系譜, 圖鑑, 稱號冊, 設定, 說明.
- [ ] 2.2 Choose a glyph clearly distinct from the adjacent 稱號冊 glyph — the two open different
  systems and sit side by side.
- [ ] 2.3 `AppClient.vue` handles the emit by calling the store's single open-drawer entry point for
  the `lore` drawer name, which is already in the store's closed drawer-name set. No store change.

## 3. Removals

- [ ] 3.1 Delete `web/webclient-app/components/LoreDrawer.vue` and its story; its guild quest prose is
  duplicated by the quest book and is not carried over.
- [ ] 3.2 Remove the `世界圖鑑` button and its `open_lore` emit from
  `web/webclient-app/components/QuestBoard.vue`, and the corresponding handler in `AppClient.vue`.
- [ ] 3.3 Wire the drawer body for `hudDrawer === "lore"` to the new component; keep the drawer title
  and the frameless-drawer classification unchanged.

## 4. Stories and tests

- [ ] 4.1 New Storybook story covering: populated codex, single-category selection, entry card, empty
  codex, unavailable panel.
- [ ] 4.2 Component tests: local navigation dispatches nothing; a zero-count category shows zero and
  no total; the card matches the panel's field order; the empty and unavailable states render their
  own messages.
- [ ] 4.3 Browser tests: the utility-strip control opens the codex drawer and closes any open drawer
  or overlay; the quest drawer contains no codex control; the two utility-strip codex controls carry
  distinct labels and glyphs.

## 5. Contract registration

- [ ] 5.1 Register every new `data-testid` in
  `docs/development/webclient-vue-frozen-contract-audit.md` §2.3, and remove the retired
  `lore-drawer__*` and `quest-board__open-lore` identifiers in the same edit.
- [ ] 5.2 Keep `tests/test_webclient_frozen_contract.py` green.

## 6. Sequencing

- [ ] 6.1 This change conflicts with `webclient-quest-drawer-split` on `AppClient.vue`,
  `QuestBoard.vue`, and the frozen contract audit document. Land THIS change first; the quest drawer
  split then deletes `QuestBoard.vue` outright.
