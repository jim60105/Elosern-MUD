# Design

## Context

The approved prototype (`docs/design/quest-drawer-redesign/QuestDrawerPrototype.vue`) inlines every piece: the top tabs, the rail, the gems, the glyph paths, and a compact copy of the rank card. Production components must come from shared units. `components/dock-icons.js` is the client's single glyph table (24×24 stroke paths, `aria-hidden` beside text). The rank block lives inside `GuildCounter.vue` together with its `.elosern-root` skin rules in `styles/app-shell.css`. Storybook renders game stories under `.elosern-root` (`.storybook/preview.js`). The component-coverage manifest is frozen and pinned by the showcase evidence tests.

## Goals / Non-Goals

**Goals:**
- One tab primitive serves both the horizontal first level and the vertical second level, so focus, tooltip, and badge behavior is identical.
- Pixel parity with the prototype for the tab, gem, and glyph visuals.

**Non-Goals:**
- No generic tooltip system for the rest of the client. The tooltip is internal to `IconTabs` until another consumer needs it.

## Decisions

1. **`IconTabs` API.** Props: `tabs` (`[{ key, label, glyph?, count?, hot?, disabled?, reason?, locked?, dim?, mark? }]`), `modelValue`, `orientation` (`horizontal` | `vertical`), `ariaLabel`. It emits `update:modelValue`, and a scoped `icon` slot receives the tab. Each tab is a `button` with `role="tab"`, `aria-selected`, `aria-label` = `label`, and `aria-controls` when the consumer passes a panel id. Disabled tabs use `aria-disabled="true"` rather than native `disabled`, so they stay focusable and their reason is reachable. Clicking or pressing Enter on a disabled tab does nothing. The reason is wired with `aria-describedby` to visually hidden text. Selection follows activation, not focus: arrow keys move focus, and Enter or Space selects. With six or seven tabs, automatic activation would re-render the list on every keystroke.
2. **Tooltip placement by orientation.** Vertical tabs show the tooltip to the right, horizontal tabs below. The tooltip shows on `:hover` and `:focus-visible`, never steals pointer events, and shows `label` plus ` · reason` when the tab is disabled. A pure-CSS `::after` approach is enough. The prototype's `data-tip` rules show the exact geometry.
3. **Badges.** The badge renders only when `count > 0`. It is ink and gold by default; `hot` is seal-red with a glow. The tab's accessible name includes the count (`label（count）`) so the badge is never color-only.
4. **Locked and dim.** `dim` lowers icon opacity (an empty category). `locked` adds the lock glyph corner mark and a dimmer icon. Both stay selectable, because the consumer shows an explanatory empty state. `mark` draws the small gold "this is yours" dot.
5. **`GradeGem` materials as data.** The F→S material ladder lives in `components/grade-materials.js` as a map from grade key to CSS custom properties (`--gem-hi`, `--gem-lo`, `--gem-rim`, `--gem-ink`, `--gem-inner`), with values copied from the prototype. Unknown keys get the iron (F) material. The component is decorative (`aria-hidden`) unless `label` is passed. The letter always renders, so meaning never depends on material.
6. **Verbatim extraction.** `GuildRankCard.vue` receives the services `guild.rank` object as `rank` and emits `exam_request` with the same `{action_id, payload: {target_rank}}`. It keeps every `guild-counter__*` class name and data-testid, so existing tests, the `.elosern-root .guild-counter__*` skin, and browser selectors keep matching. Only the root wrapper moves. A class rename now would churn browser tests twice: the old surface is deleted in `quest-drawer-guild-board-tab`.
7. **Glyph naming.** New keys are prefixed by role (`quest_book`, `guild_counter`, `quest_in_progress`, `quest_completed`, `quest_failed`, `cat_gather`, `cat_defeat`, `cat_escort`, `cat_explore`, `cat_emergency`, `track_flag`, `reward_copper`, `reward_merit`, `reward_item`, `deadline`, `lock`), with the prototype's path data and attrs. `cat_gather` is new; the prototype had no gather path, so it is drawn to match the set's stroke weight.

## Risks / Trade-offs

- [Manifest pinning churn] → the new titles are added to `PREVIOUS_MANIFEST_KEYS` / family constants exactly the way `World/LettersPanel` joined, keeping the frozen-set assertions meaningful.
- [Visual drift from the prototype] → task 4.1 compares the Storybook screenshots side by side with the `Design/QuestDrawerRedesign` stories at 1451×790 and 1920×1080.
