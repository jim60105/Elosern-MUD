# Design

## Context

`world/rules/service_view.py` builds the guild section. `_build_board()` turns each listed `GuildQuestOffer` into a `BoardRowView` with `objective_summary=describe_objective(...)` and `reward_summary=describe_reward(offer)`. `_build_guild()` already knows the registration's `branch_key`. `web/webclient/presentation/services.py` serializes and validates the section, and `protocol/panels/services.js` mirrors it, checking `schema_version !== 5`.

`quest-log-structured-rows` adds `describe_objective_parts()`, `describe_reward_parts()`, the category key map, and `QUEST_LOG_MAX_REWARD_ITEMS`. This change reuses all four.

## Goals / Non-Goals

**Goals:**
- One reward shape and one category vocabulary across `quest_log` and the board.
- Board facts come from the same seams as the quest book, so a quest accepted from the board shows the same facts in the book.

**Non-Goals:**
- No change to `quests` rows: the redesign reads them only for the abandon and turn-in descriptors.

## Decisions

1. **Share, don't copy, the quest-log helpers.** Move the category key map and reward-item bound to a small module both presenters import (`web/webclient/presentation/quest_facts.py`), and expose the existing `describe_reward_parts()` builder through that module. The builder already lives in `world/quests/describe.py`; the read model continues using that world-owned seam directly. Retain the canonical one-item bound, with `QUEST_LOG_MAX_REWARD_ITEMS` re-exported under the shared name. The redesign document's §4.1 eight-item text is stale: the merged dependency lowered the bound to one after its maximal envelope exceeded 65,536 bytes. Test rejection of both a second item and the delta's ninth item without widening the quest-log contract.
2. **Offer deadline seam in `describe.py`.** `describe_offer_deadline(hours: int | None) -> str | None` returns 接取後 N 日 when `hours % 24 == 0`, otherwise 接取後 N 小時. It sits beside `describe_deadline()` so all deadline prose lives in one module. The board renders from the definition's authored `deadline_hours`, never from a record.
3. **`branch_label` on the section, not per row.** Every offer on one board shares the issuing branch, so one field on the `guild` section avoids twelve copies. It resolves through `GUILD_BRANCH_REGISTRY[branch_key].display_name_zh`, the same lookup the quest log's `_issuer_label()` uses for `guild:` issuers. Always use the local `GuildStaff` component's `branch_key`, including for registered actors visiting another branch: listing and acceptance use that local issuing branch rather than the registration's branch. Cover cross-branch acceptance in the board/book equality test.
4. **`rank_ladder` from the registry order.** `[key for key, _ in sorted(GUILD_RANK_REGISTRY.items(), key=order)]`, bounded at 16 keys of at most `MAX_RANK_KEY` characters, and validated for uniqueness. The redesigned board tab needs the full ordered ladder to show every grade tab and to lock grades above the actor's rank. Hardcoding F→S in the client would duplicate authored data that the server already owns.
5. **Prose bounds match the quest log.** `objective_note` uses `MAX_SUMMARY_CODE_POINTS` (the board summary bound), `deadline_line` uses `MAX_DEADLINE_LINE_CODE_POINTS`, and `rationale` and `flavor` use `MAX_DEFINITION_PROSE_LENGTH`. The services envelope test is extended to twelve maximal board rows on top of the existing maximal sections. If it overflows, the response is to lower the board's per-row prose with a recorded spec change, never to truncate silently.
6. **Interim counter rendering.** `GuildCounter.vue` renders the board reward from `reward`, adds `objective_note` and `deadline_line` lines, and leaves the rest as is. The redesign replaces the board UI in `quest-drawer-guild-board-tab`.

## Risks / Trade-offs

- [Envelope growth: twelve board rows with two 240-character prose fields each] → the extended envelope test runs first. Real board sizes are small, but the bound must hold at the cap.
- [Branch label disagreement between board and book] → a scenario-level test accepts a board offer and compares `branch_label` with the new quest-log row's issuer label.
