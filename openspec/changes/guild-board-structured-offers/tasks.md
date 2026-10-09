# Tasks

## 1. Shared quest facts and the offer-deadline seam

- [x] 1.1 Extract the category key map and shared one-item reward bound from `web/webclient/presentation/quest_log.py` into `web/webclient/presentation/quest_facts.py`, expose the existing world-owned `describe_reward_parts()` builder there, and import these facts back into `quest_log.py`. Register any new test module in `.github/evennia-shards.json`. Verify that `web.webclient.presentation.tests.test_quest_log_panel` still passes unchanged.
- [x] 1.2 Add `describe_offer_deadline()` to `world/quests/describe.py` with synthetic tests in `world/quests/tests/test_describe.py` (None, 24 → 接取後 1 日, 72 → 接取後 3 日, 36 → 接取後 36 小時). Verify with the focused label.

## 2. Read model and services v6

- [x] 2.1 Extend `BoardRowView` (category, objective parts, deadline line, rationale, flavor, structured reward; no reward summary) and `GuildSectionView` (`branch_label`, `rank_ladder`) in `world/rules/service_view.py`, and populate them in `_build_board()` and `_build_guild()` per design Decisions 1 to 4. Update `world/rules/tests/test_service_view/test_board_and_quest_rendering.py` with synthetic offers covering a species hunt, a deadline, no prose, and an item reward. Verify that `test_service_view_side_effects` still proves no mutation.
- [x] 2.2 Set `SERVICES_SCHEMA_VERSION = 6` in `web/webclient/presentation/services.py`, and update `_serialize_board_row`, `_serialize_guild`, and the validators (the exact board field set, the closed category set, nullable bounds, the reward shape and item cap, `branch_label` bound, and `rank_ladder` bound, uniqueness, and membership of every rank key in the section). Update `tests/test_services_panel/` (`_support.py`, `test_schema.py`, `test_schema_edges.py`, `test_presenter.py`) for every delta scenario. Add the twelve-maximal-row envelope case. Verify with the focused labels.
- [x] 2.3 Add a synthetic integration test: accept a board offer, then build both `services` and `quest_log`. It asserts that the board row's `reward` equals the new quest-log row's `reward` and that `branch_label` equals that row's issuer label. Verify with the focused label.

## 3. Client mirror and fixtures

- [ ] 3.1 Update `protocol/panels/services.js` (version 6, board row field set, `branch_label`, `rank_ladder`) and `constants.js`, reusing the quest-log reward and category validators. Update `protocol_services_b.test.js` and `protocol_fixtures.js` with drift rejections for `reward_summary`, an unknown category, and a ninth reward item. Verify with `node --test web/static/webclient/js/tests/protocol_services_b.test.js`, plus `uv run --locked python -m unittest tests.test_panel_schema_version_parity_contract` after updating that contract with the v6 version and the `rank_ladder` and reward-item bounds.
- [ ] 3.2 Rewrite the board rows and add `branch_label` and `rank_ladder` in `web/webclient-app/stories/fixtures/services_panels.js` (every `SERVICES_PANEL_*` export), using realistic content: real catalog offers across F, E, and D, rationale and flavor prose, one offer with a deadline, one with an item reward. Verify that the GuildCounter and ShopPanel stories render without console errors.

- [ ] 3.3 Update the hand-written `services` unavailable payload in `web/tests/browser/test_browser_services_quest_drawer.py` (`ServicesUnavailableJourney`) to schema version 6. The browser seeds (`web/tests/browser/seed/services_*.py`) build payloads through the real presenter and need no edit. Confirm this by running the board journeys in `test_browser_services_guild.py` (`test_board_list_to_accept`, `test_board_frame_refreshes_on_committed_update`) with `uv run --locked python -m web.tests.browser.unittest_driver`.

## 4. Interim counter board

- [ ] 4.1 Adapt the board section of `web/webclient-app/components/GuildCounter.vue`. If `quest-drawer-ui-primitives` has merged, the rank block already lives in `GuildRankCard.vue`; edit only the board markup. render the reward from `reward` under one label, with merit omitted at zero, and add `objective_note` and `deadline_line` lines. Update `web/webclient-app/tests/world/guild_counter.test.js` for both delta scenarios. Verify with `pnpm test -- tests/world/guild_counter.test.js`.

## 5. Integration acceptance

- [ ] 5.1 Run the focused Evennia labels (describe, service view, services panel), the Node protocol test, the schema-version parity contract, the counter Vitest file, `uv run --locked python -m tools.contract_gate`, and `openspec validate guild-board-structured-offers --strict`. In the live client (`agent-browser`), stand at the guild counter and confirm a board offer shows its note, deadline, and single-label reward.

## Workflow follow-up

- At archive sync, annotate the tests from 2.1 to 2.3 and 4.1 for the two new requirements using IDs from `tools.spec_traceability list`, and run `tools.spec_traceability check`.
- Do not apply, archive, or merge until the user asks.
