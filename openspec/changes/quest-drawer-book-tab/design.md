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
2. **`QuestDetail` renders a view model, not a row.** Its props are `detail` (hero, progress, conditions, letter, reward) and `actions` (a list of resolved descriptors plus a reason line). It emits `action` with the exact `{action_id, payload}`. Abandon arming is local state keyed by `quest_id` and reset when `detail.id` changes. This makes the component reusable for board offers.
3. **Tab and selection memory in the drawer, per session.** `QuestDrawer` keeps `{top, bookState, selectedByTab}` in a module-level reactive store that survives drawer close and reopen but not reload. The spec requires session memory only. Persisting to the client store would turn transient UI state into reconnect-sensitive state.
4. **Counter tab in this change.** When selected, the content area (no rail) renders the existing `GuildCounter` with its events forwarded. Disabled reasons come from the existing `questServicesUnavailable` / `questServicesPanel.reason` computeds, with the fixed clerk line otherwise. The current absence markers become tab reasons, so their `quest-drawer__counter-*` test ids move onto the reason text. Browser selectors are updated in the same change.
5. **Root test id kept.** `QuestDrawer` keeps `data-testid="quest-drawer"` on its root, so the shared browser drawer gates keep working. New ids follow `quest-drawer__*`. Row ids are `quest-drawer__row--<quest_id>`, and the action ids are `quest-drawer__track`, `__abandon`, `__abandon-confirm-yes`, `__abandon-confirm-no`, and `__turnin`.
6. **CSS ownership.** All styles are scoped in the new components and use tokens. The `.elosern-root .quest-log*` rules in `styles/app-shell.css` are deleted. The guild-counter rules stay until the next change. The drawer fills `HudDrawer`'s workspace with `height: 100%`, and the list and detail scroll independently.

## Risks / Trade-offs

- [Size: the largest change in the set] → the model and its tests come first. If time runs short, the visual parity review (task 5.2) is the only deferrable item, and it is recorded in tasks.md rather than silently dropped.
- [Browser test churn] → only journeys whose selectors or semantics changed are rewritten. Each touched class is run by its own short command, and new methods are registered in `.github/browser-shards.json`.
- [Session memory surprises] → covered by the remembered-tab fallback scenario. Memory never selects a disabled tab.
