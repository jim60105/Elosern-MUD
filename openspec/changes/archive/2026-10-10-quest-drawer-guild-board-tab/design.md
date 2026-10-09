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

1. **Lock rule from data only.** A grade is locked when its ladder index is greater than the holder's rank index. When the holder has no rank (unregistered), the rail is not rendered (see Decision 4). The client never encodes F→S. The holder's rank is `services.player.guild_rank` alone. If the ladder lacks it (the services validator checks only `guild.rank` and the board ranks against the ladder, not `player.guild_rank`), every grade is treated as unlocked and none is marked as the holder's; the server still lists only eligible offers.
2. **Default grade.** The default is the highest ladder grade at or below the holder's rank whose offer count is non-zero, otherwise the holder's own grade. It is remembered per session like the other selections, together with its basis (the ladder and the holder's rank), and dropped when either changes so a promotion lands on a sensible tab. The grade shown first is pinned into memory, so a commit that empties it (the last offer accepted) does not move the tab. A locked grade carries the lock mark and no count, and is not dimmed, so it never reads as "no offers posted" or as hidden offers; it stays selectable.
3. **Offer view model.** `offerDetail(row, branchLabel)` produces the `QuestDetail` view model with `kind: 'offer'`: no progress, the condition pair (公會等級 X 級以上 with the rationale, plus the deadline or 無期限), the letter from `branchLabel` and `flavor`, and the reward with counter settlement. `offerActions(row)` returns the `accept` descriptor as primary, or its reason when disabled. The accept payload is exactly `{definition_key}`, as before.
4. **Registration card replaces the whole tab body.** When `guild.registration.registered` is false, the tab renders a centered card (title 未加入公會, short guidance, and the `register` descriptor as the primary button or its reason), and no rail, rank card, or board. This matches the server rule that an unregistered actor's board is empty, without showing an empty rail.
5. **Retire the legacy surface in one step.** Delete `GuildCounter.vue` and the `.elosern-root .guild-counter`, `__title`, `__row`, `__row-name`, `__row-objective`, and `__action` rules. `GuildRankCard` keeps its `guild-counter__rank*` / `__exam*` / `__merit*` class names and test ids, which those skin rules never styled (see its comment), so its look is unchanged. Visual parity in task 4.2 confirms this.
6. **Test-id continuity for browser journeys.** Board rows use `quest-drawer__row--<definition_key>`, and the accept and register buttons get `quest-drawer__accept` and `quest-drawer__register`. Journeys that used `guild-counter__register` and `guild-counter__accept` are rewritten. Rank-card ids are unchanged.

## Risks / Trade-offs

- [Browser seed lacks multi-grade offers] → if the services seed has only one grade, extend `web/tests/browser/seed/services_fixture.py` with a second-grade offer so the grade-switch journey is real.
- [Pinned manifest churn again] → follow the same key-set update pattern as the earlier two UI changes.

## Implementation notes

- **Disabled accept.** A disabled accept descriptor keeps its primary button with `aria-disabled="true"` (focusable, described by the reason line, inert on activation), matching the prototype's disabled button beside its reason.
- **Condition copy.** The acceptance condition reads `公會等級 X 級以上` (this design's wording) rather than the prototype's `X 級以上`.
- **Focus after a commit.** When a commit unmounts the focused control (the register button, or an accepted offer's detail), focus returns to the selected tab of the visible rail, so the drawer keeps keyboard ownership. Only focus that was inside the drawer before the update is rescued; a background commit never pulls focus in from elsewhere (post-implementation review).
- **Rank card inside the list tabpanel.** The rank card renders in `QuestList`'s `lead` slot, inside the element that carries the grade list's `role="tabpanel"`, so the card scrolls with the list column as in the prototype.
- **Browser seed not extended.** The services seed's holder is the lowest ladder rank, and the server lists only offers at or below the holder's rank, so a second offer grade cannot exist for that holder. Grade grouping and the default-grade rules are covered in Vitest; the browser journeys cover the default grade, accept, and a keyboard switch to a locked grade (derived from the seeded ladder).
- **Out-of-scope fix.** `protocol_services_a.test.js` (Node gate) was missing the v6 `branch_label` and `rank_ladder` fields that `guild-board-structured-offers` made required; they were added so the gate is green again.

## Visual review (task 4.2)

Storybook `World/QuestDrawer` GuildBoard, LockedGrade, DisabledAccept, and Unregistered were compared with `Design/QuestDrawerRedesign` GuildBoard at 1451×790, and the live client (services seed `guild_registered_board`) was captured at 1451×790 and 1920×1080 with keyboard focus and tooltips. The layout matches: grade rail with gems, counts, own-grade dot and lock marks, rank card atop the list column, the selected offer's detail, and the accept button pinned bottom-right. Intentional deviations:

- The first-level tabs sit in a strip under the HudDrawer header (as recorded for quest-drawer-book-tab), so the body is shorter than the prototype's.
- The rank card keeps its unchanged content, including the examination hint line the prototype omits.
- The accept label comes from the server descriptor (接取任務 / 接取), not the prototype's fixed 接取委託.
- The empty and locked lines use the shared `EmptyState` (headline type), larger than the prototype's muted paragraph.
- A vertical tab's tooltip overlaps the rank card, as it overlaps the list in the book tab.
- The live seed's synthetic ladder keys (`t_bronze`, `t_silver`) overflow `GradeGem`; real ladder keys are single letters (known issue, unchanged).
