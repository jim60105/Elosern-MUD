# Design

## Context

`quest-drawer-book-tab` delivers `QuestDrawer` with the book tab and a counter tab that hosts the legacy `GuildCounter`. Its model already resolves book detail and actions. `QuestDetail` renders a view model plus resolved actions, and `QuestList` renders rows. `guild-board-structured-offers` ships board rows with category, objective parts, deadline, prose, structured reward, `branch_label`, and `rank_ladder`. `GuildRankCard` exists from `quest-drawer-ui-primitives`. The holder's rank comes from `services.player.guild_rank`.

## Goals / Non-Goals

**Goals:**
- Board offers and held quests share one list component and one detail component, distinguished only by the view model and actions.
- No client-side rank rule beyond reading the ladder and the holder's rank.

**Non-Goals:**
- No preview of offers above the holder's rank. The server does not list them, and locked tabs explain why.

## Decisions

1. **Lock rule from data only.** A grade is locked when its ladder index is greater than the holder's rank index. When the holder has no rank (unregistered), the rail is not rendered (see Decision 4). The client never encodes F→S. If the ladder lacks the holder's rank (a producer bug), every grade is treated as unlocked, and the services validator already rejects such a payload.
2. **Default grade.** The default is the highest ladder grade at or below the holder's rank whose offer count is non-zero, otherwise the holder's own grade. It is remembered per session like the other selections, and dropped when the ladder or rank changes so a promotion lands on a sensible tab.
3. **Offer view model.** `offerDetail(row, branchLabel)` produces the `QuestDetail` view model with `kind: 'offer'`: no progress, the condition pair (公會等級 X 級以上 with the rationale, plus the deadline or 無期限), the letter from `branchLabel` and `flavor`, and the reward with counter settlement. `offerActions(row)` returns the `accept` descriptor as primary, or its reason when disabled. The accept payload is exactly `{definition_key}`, as before.
4. **Registration card replaces the whole tab body.** When `guild.registration.registered` is false, the tab renders a centered card (title 未加入公會, short guidance, and the `register` descriptor as the primary button or its reason), and no rail, rank card, or board. This matches the server rule that an unregistered actor's board is empty, without showing an empty rail.
5. **Retire the legacy surface in one step.** Delete `GuildCounter.vue` and the `.elosern-root .guild-counter`, `__title`, `__row`, `__row-name`, `__row-objective`, and `__action` rules. `GuildRankCard` keeps its `guild-counter__rank*` / `__exam*` / `__merit*` class names and test ids, which those skin rules never styled (see its comment), so its look is unchanged. Visual parity in task 4.2 confirms this.
6. **Test-id continuity for browser journeys.** Board rows use `quest-drawer__row--<definition_key>`, and the accept and register buttons get `quest-drawer__accept` and `quest-drawer__register`. Journeys that used `guild-counter__register` and `guild-counter__accept` are rewritten. Rank-card ids are unchanged.

## Risks / Trade-offs

- [Browser seed lacks multi-grade offers] → if the services seed has only one grade, extend `web/tests/browser/seed/services_fixture.py` with a second-grade offer so the grade-switch journey is real.
- [Pinned manifest churn again] → follow the same key-set update pattern as the earlier two UI changes.
