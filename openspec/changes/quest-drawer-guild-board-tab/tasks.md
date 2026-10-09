# Tasks

## 1. Board model

- [x] 1.1 Add `offersByGrade()`, `gradeLocked()`, `defaultGrade()`, `offerDetail()`, and `offerActions()` to `web/webclient-app/components/quest-drawer-model.js` per design Decisions 1 to 3. Extend `tests/world/quest_drawer_model.test.js` to cover ladder-ordered grouping, the lock rule including a missing holder rank, the default grade with and without eligible offers, the offer view model (condition, deadline fallback, branch letter, reward, no progress), and the accept action enabled, disabled with reason, and with its exact payload. Verify with `pnpm test -- tests/world/quest_drawer_model.test.js`.

## 2. Counter tab composition

- [x] 2.1 In `QuestDrawer.vue`, replace the hosted `GuildCounter` with the grade rail (`IconTabs` vertical with `GradeGem` in the icon slot, counts, `mark`, `dim`, `locked`), `GuildRankCard` atop `QuestList`, and `QuestDetail` for the selected offer. Add the registration card (design Decision 4) and the locked and empty grade lines. Extend `tests/world/quest_drawer.test.js` for every scenario in the four added requirements and the modified counter-business requirement. Verify with `pnpm test`.
- [x] 2.2 Add board variants to `stories/World/QuestDrawer.stories.js` (grade board with a selected offer, a locked grade, an empty eligible grade, a disabled accept, an unregistered holder, top rank) and to `QuestList` and `QuestDetail` stories (an offer list and an offer detail). Verify that they render without console errors in Storybook.

## 3. Retire the legacy counter

- [x] 3.1 Delete `components/GuildCounter.vue`, `stories/World/GuildCounter.stories.js`, and `tests/world/guild_counter.test.js`, and remove the `.elosern-root .guild-counter*` rules from `styles/app-shell.css` (design Decision 5). Remove `World/GuildCounter` from `component-manifest.json`, update the showcase evidence key sets, and re-point `web/webclient/tests/test_vue_hud_drawer_evidence.py` (and any `test_node_suite_evidence.py` method naming `guild_counter.test.js`) to the drawer and rank-card Vitest files. Verify with `node scripts/component-coverage.mjs`, `uv run --locked pytest -q web/webclient/tests/test_vue_showcase_*evidence.py web/webclient/tests/test_vue_hud_drawer_evidence.py`, and `pnpm test -- tests/motion_tokens.test.js`.

## 4. Browser journeys and visual parity

- [x] 4.1 Rewrite the counter journeys for the grade-tabbed board: in `test_browser_services_guild.py`, register and idempotent re-register through the registration card, the reference viewport keeping controls visible, board list to accept via grade tab, list, detail, and accept, and the board refreshing on a committed update; the examination appointment journeys keep working from the rank card. Update `test_browser_pointer.py` (register selector), and extend `web/tests/browser/seed/services_fixture.py` with a second-grade offer if needed. Register new or renamed methods in `.github/browser-shards.json`, and run each touched class with `uv run --locked python -m web.tests.browser.unittest_driver <module>.<Class>`.
- [x] 4.2 With `agent-browser`, capture the live counter tab (grade rail, rank card, offer detail, a locked grade, the registration card, tooltips, and keyboard focus) at 1451×790 and 1920×1080, and compare it with the `GuildBoard` story of `Design/QuestDrawerRedesign`. Fix deviations, or record intentional ones in this change's design.md.

## 5. Integration acceptance

- [x] 5.1 Run `pnpm test`, `node scripts/component-coverage.mjs`, the touched browser classes, `tests.test_evennia_test_optimization_contract` and `tests.test_webclient_frozen_contract` (documented `--env-file` form), `uv run --locked python -m tools.contract_gate`, and `openspec validate quest-drawer-guild-board-tab --strict`. Confirm that no file under `web/webclient-app` still references `GuildCounter.vue` or `QuestLog.vue`.

## Workflow follow-up

- At archive sync, re-point annotations of the removed `webclient-service-menus` requirement per its migration note.
- At archive sync, annotate the Python evidence carriers (the browser tests from 4.1 and the Vitest evidence runners from 3.1) with the four new `webclient-quest-drawer` requirement IDs, and run `tools.spec_traceability check`.
- After this change is archived, the user may decide whether `docs/design/quest-drawer-redesign/` stays as historical reference or is retired together with its Storybook glob. This set does not decide that.
- Do not apply, archive, or merge until the user asks.
