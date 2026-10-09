# Design

## Context

`AppClient.vue` renders the quest drawer inline when `store.view.hudDrawer === 'quest'`: `<QuestLog>`, then `<GuildCounter>` or one of two absence markers, gated by `questGuildAvailable` and `questServicesUnavailable` from the app composable. `HudDrawer.vue` owns the frame, title, focus trap, and close. The browser base (`web/tests/browser/test_browser_services_base.py`) waits on `[data-testid="quest-drawer"]`.

After `quest-log-structured-rows`, each `quest_log` row carries category, grade, objective parts, prose, structured reward, and `reward_claimed`. After `quest-drawer-ui-primitives`, `IconTabs`, `GradeGem`, `GuildRankCard`, and the glyphs exist. The approved prototype (`docs/design/quest-drawer-redesign/QuestDrawerPrototype.vue`) is the visual source of truth for the grid, row, hero, ribbon, stamp, pips, letter, reward cells, and action bar.

## Goals / Non-Goals

**Goals:**
- All decision logic in a pure, unit-tested model; components only render.
- Live-client geometry and Storybook look the same as the prototype.

**Non-Goals:**
- No board-row normalizer yet; `quest-drawer-guild-board-tab` adds it to the same model.

## Decisions

1. **Model owns every decision.** `quest-drawer-model.js` exports pure functions: `rowsByState(questLog)`, `stateCounts(...)`, `turninHot(questLog, services)`, `counterRowsById(services)`, `bookDetail(row)` (the view model with one-based stage, pip-or-bar choice at 12, and omitted sections), and `bookActions(row, counterRow)` (the action-bar resolution in the spec's order). Components receive view models. This keeps the merge and honesty rules testable without mounting, and lets the board tab add `offerDetail()` and `offerActions()` beside them.
2. **`QuestDetail` renders a view model, not a row.** Its props are `detail` (hero, progress, conditions, letter, reward) and `actions` (the resolved track, abandon, and turn-in descriptors plus a reason line). It emits `action` with the exact `{action_id, payload}`. Abandon arming is local state keyed by `quest_id` and reset when `detail.id` changes or the abandon descriptor goes away. The armed line names the quest (`放棄「<name>」後任務會判定失敗，且無法回復。`), as `webclient-contextual-hud` requires of every drawer abandon confirmation. Arming moves focus to 取消, and cancelling returns it to the abandon control. This makes the component reusable for board offers. `QuestDrawer` forwards every `action` (and every `GuildCounter` intent) as one `action` event, and `AppClient` routes it to `onQuestAction`, which already dispatches `intent.action_id` with `intent.payload` whatever the intent kind.
3. **Tab and selection memory in the drawer, per session.** `QuestDrawer` keeps `{scope, top, bookState, selectedByTab}` in a module-level reactive store (`quest-drawer-memory.js`) that survives drawer close and reopen but not reload. The spec requires session memory only. Persisting to the client store would turn transient UI state into reconnect-sensitive state. `AppClient` passes `memoryScope` (`<generation>|<epoch>` from `store.view`); when it differs from the stored scope, the memory resets before use. This keeps the `webclient-contextual-hud` rule that a transport loss or epoch reset discards every local selection inside a drawer. The memory holds only keys: the effective tab, state, and row are computed, so a remembered key that is disabled or gone falls back without being overwritten. Tests reset it through the exported `resetQuestDrawerMemory()`.
4. **Counter tab in this change.** When selected, the content area (no rail) renders the existing `GuildCounter` with its events forwarded. The model's `counterTab(services)` owns the enabled flag and the disabled reason: the services panel's own `reason.message` when it is unavailable, otherwise the fixed clerk line 需在公會職員面前才能辦理. The `questGuildAvailable` / `questServicesUnavailable` / `questServicesPanel` computeds in `use-drawers.js` lose their only consumer and are removed. The current absence markers become tab reasons, so their `quest-drawer__counter-*` test ids move onto the reason text: `IconTabs` gains an optional per-tab `reasonAttrs` object bound onto its visually hidden reason element, which carries `data-testid` and `data-reason-code`. Browser selectors are updated in the same change, and every counter-side journey selects the counter tab first, because the drawer always lands on the book.
5. **Root test id kept.** `QuestDrawer` keeps `data-testid="quest-drawer"` on its root, so the shared browser drawer gates keep working. New ids follow `quest-drawer__*`. Row ids are `quest-drawer__row--<quest_id>`, and the action ids are `quest-drawer__track`, `__abandon`, `__abandon-confirm-yes`, `__abandon-confirm-no`, and `__turnin`.
6. **CSS ownership.** All styles are scoped in the new components and use tokens. The `.elosern-root .quest-log*` and `.elosern-root .quest-drawer` rules in `styles/app-shell.css` are deleted. The guild-counter rules stay until the next change. `AppClient` passes `HudDrawer`'s existing `bodyFlush` prop for the quest drawer, so the drawer fills the workspace with no body padding or body scroll, and the list and detail scroll independently. `HudDrawer` itself is unchanged.
7. **Header strip inside the drawer chrome.** `HudDrawer`'s `DrawerHeader` already draws the seal glyph, the 任務 title, and the close control, and the frame is a non-goal. The first-level tabs therefore sit on their own strip directly under that header, on the prototype's header rule, instead of sharing the title row. This is the one intentional layout deviation from the prototype.
8. **Listbox keyboard model.** The list uses the same activation model as `IconTabs`: a roving tab stop on the selected row, ArrowUp/ArrowDown/Home/End move focus without wraparound, and Enter, Space, or a click selects. Selection never follows focus alone, so the detail does not re-animate on every arrow press.
9. **Server prose stays verbatim.** `deadline_line` already reads `期限：…`, and the book renders it unchanged under the 期限 label, so it stays byte-identical to the tracker and the counter (`webclient-quest-log-panel`). Fixed client lines (無期限, the two deadline sentences, 委託人沒有留下說明。, the settlement notes, and the action-bar reasons) are stable copy, never derived from prose.
10. **Empty guidance.** An empty state tab renders the shared `EmptyState` (glyph `quests`, headline 這裡還沒有任務。, and a per-state guidance line) inside the list column, which satisfies the `webclient-contextual-hud` rule that the empty quest book uses the shared guidance card.

## Risks / Trade-offs

- [Size: the largest change in the set] → the model and its tests come first. If time runs short, the visual parity review (task 5.2) is the only deferrable item, and it is recorded in tasks.md rather than silently dropped.
- [Browser test churn] → only journeys whose selectors or semantics changed are rewritten. Each touched class is run by its own short command, and new methods are registered in `.github/browser-shards.json`.
- [Session memory surprises] → covered by the remembered-tab fallback scenario. Memory never selects a disabled tab.

## Visual review (task 5.2)

Reviewed with `agent-browser` against `Design/QuestDrawerRedesign`, in Storybook (`World/QuestDrawer` inside the real `HudDrawer` chrome) and in the live client (an isolated services server, `guild_active_quest`), at 1451×790 and 1920×1080. The rail (68px), the list and detail grid, the list rows, hero, ribbon, stamp, pips, conditions pair, letter, reward cells, and the pinned action bar match the prototype's geometry and colors at both viewports, and the live client renders identically to Storybook (no `.elosern-root` rule reaches the new components). Keyboard focus rings show on every tab, row, and button; the disabled counter tab is focusable and its tooltip carries the reason; tracking flips to 追蹤中 only after the commit lands.

Recorded deviations:

- The first-level tabs sit on their own strip under `HudDrawer`'s header instead of sharing the title row (Decision 7), so the body is about 52px shorter than the prototype's at the same viewport.
- The first-level tooltip opens downward over the rail's top edge; the strip is raised (`z-index: 2`) so the tooltip is never clipped by the body.
- The browser fixture's synthetic rank ladder uses keys such as `t_bronze`, which `GradeGem` prints verbatim and which overflow the gem. The shipped ladder is single letters (F–S), so this only shows in browser fixtures; a long-key treatment belongs to `GradeGem` and is out of scope here.
