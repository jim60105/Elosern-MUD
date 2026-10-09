# Tasks

## 1. Describe seams

- [x] 1.1 Add `describe_objective_parts()` to `world/quests/describe.py` and make `describe_objective()` compose `line` or `line（note）` from it. Extend `world/quests/tests/test_describe.py` with synthetic species-hunt and non-hunt objectives. Verify the line and note split, a null note for non-hunt objectives, and an unchanged composed string.
- [x] 1.2 Add `describe_reward_parts(reward)`, returning `{copper, merit, items: [{item_key, display_name, quantity}]}` in declared item order, and keep `describe_reward()` output unchanged. Verify with synthetic rewards (no items, several items, an unknown item key raising `QuestDescribeError`).
- [x] 1.3 Add a tagged data-contract test (first docstring line `Data-contract test: ...`, registered in `tools/test_data_freeze.json`). It asserts that `describe_objective()` and `describe_reward()` are byte-identical to the composed parts for every registered definition, guild offer, and private issuance, and that each carries at most one reward item (the envelope-tested cap). Verify with `uv run --locked python -m tools.test_data_lint check`.

## 2. quest_log v2 presenter and validator

- [x] 2.1 In `web/webclient/presentation/quest_log.py`, set `QUEST_LOG_SCHEMA_VERSION = 2` and add `QUEST_LOG_MAX_REWARD_ITEMS = 1` (the envelope-tested cap) and the `category` key map. Build the new row fields (`category`, `grade`, `objective_line` and `objective_note` from the parts seam, `rationale`, `flavor`, `reward`, `reward_claimed` via `parse_reward_claims()` on `quest_source`), drop `detail` and `reward_line`, and map `RewardClaimError` to `PanelUnavailableError`.
- [x] 2.2 Update `validate_quest_log()`: the exact field set, the closed `category` set, `grade` registry membership, the nullable bounds (design Decision 6), the `reward` object shape and item cap, the boolean `reward_claimed`, and settlement/reward null pairing. Extend `web/webclient/presentation/tests/test_quest_log_panel.py` with synthetic fixtures covering every scenario in the delta spec: field set, category and grade, the reward shape, a withdrawn issuance, claimed and unclaimed counter rows, an auto-settled row after completion, malformed claims degrading the panel, host independence, and a mismatched pair rejected. Verify with the focused Evennia test label.
- [x] 2.3 Add an envelope test: twelve rows, every prose field at its maximum, maximal reward items up to the tested cap, validating under `MAX_CANONICAL_JSON_BYTES`. Run it before section 3. The initial eight-item case failed at 99,754 bytes; lower `QUEST_LOG_MAX_REWARD_ITEMS` to one, then update the spec scenario and design Decision 4 to the new value.

## 3. Client protocol mirror

- [x] 3.1 Set `QUEST_LOG_SCHEMA_VERSION = 2` and add `QUEST_LOG_MAX_REWARD_ITEMS` and the prose bound constants in `web/static/webclient/js/elosern/protocol/constants.js`. Mirror the v2 row validator in `protocol/panels/quest_log.js` (grade checked by shape only, per design Decision 3).
- [x] 3.2 Update the quest-log cases in `web/static/webclient/js/tests/protocol_title_codex.test.js` and the shared protocol fixtures to v2. Add drift rejections for an extra `detail` field, an unknown category, `cap + 1` reward items, a non-boolean `reward_claimed`, and a mismatched commission pair. Verify with `node --test web/static/webclient/js/tests/protocol_title_codex.test.js`.
- [x] 3.3 Update `tests/test_quest_log_parity_contract.py` and `tests/test_panel_schema_version_parity_contract.py` for the v2 field set, bounds, and version. Verify with `uv run --locked python -m unittest tests.test_quest_log_parity_contract tests.test_panel_schema_version_parity_contract`.

## 4. Interim quest book and fixtures

- [x] 4.1 Rewrite `web/webclient-app/stories/fixtures/quest_log_panels.js` to v2 with realistic content: real catalog rationale and flavor prose, the full branch label `埃洛西恩冒險者公會 阿爾托利亞分會`, an item reward, a species-hunt note, a deadline, and a null-reward row. Keep every existing export name. Verify that the existing QuestLog stories render without console errors in Storybook.
- [x] 4.2 Adapt `web/webclient-app/components/QuestLog.vue`: render `flavor` (and `rationale` when present) in place of `detail`, format `reward` client-side with one 獎勵 label and no zero merit, render 第 `stage_index + 1` 階段, and render nothing for a null reward. Update `web/webclient-app/tests/world/quest_log.test.js` and verify with `pnpm test -- tests/world/quest_log.test.js`.

- [x] 4.3 Update the hand-written `quest_log` payloads in `web/tests/browser/test_browser_drawer_content.py` (`test_empty_quest_guidance_gives_way_to_the_unavailable_reason`) to schema version 2, keeping the interim `quest-log__*` test ids. Confirm that the Vitest suites consuming `QUEST_LOG_PANEL_*` fixtures (`tests/store/store_slices.test.js`, `tests/app_client_drawers.test.js`, `tests/drawer_content_polish.test.js`) and `tests/test_data_independence_webclient_presentation.py` pass unchanged. Run that browser class with `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_drawer_content.<Class>`.

## 5. Integration acceptance

- [x] 5.1 Sweep with `rg -n 'reward_line|"detail"' web tests world commands`, and grep for `quest_log` payloads with `schema_version` 1. Confirm that no producer, validator, fixture, or test still expects v1 (the `services` quest rows keep their own `detail`). Then run the focused Evennia labels for `world.quests.tests.test_describe` and `web.webclient.presentation.tests.test_quest_log_panel`, the Node protocol test, the two parity contracts, the quest-log Vitest file, `uv run --locked python -m tools.contract_gate`, and `openspec validate quest-log-structured-rows --strict`. Confirm in the live client (`agent-browser`) that the quest book renders a species hunt with its note and reward and shows no 獎勵：獎勵：.

Acceptance evidence: 74 focused Evennia tests, 14 Node tests, 9 parity tests, 63 focused Vitest tests, four presentation-independence tests, the three-method drawer browser class, contract gate, and strict change validation pass. All six existing QuestLog stories rendered with no browser errors. The built live client accepted the v2 species-hunt fixture through its actual `ui_update` receiver, showing its note, reward, and one reward label. The live fixture check tests rendering under `.elosern-root`; it does not claim a naturally accepted hunt in the seeded world. The browser class initially failed because the worktree had no built client bundle, then passed after `pnpm run build`. An accidentally broad Vitest invocation exposed the known GuildCounter motion-duration failures, which belong to `quest-drawer-ui-primitives` and remain unchanged.

## Workflow follow-up

Post-implementation duck found no blocking issues. Both non-blocking findings were adopted: the snapshot test now includes three populated tracker rows and twelve matching available counter rows, and the service delta explicitly permits exactly one client-owned reward label. The same reviewer then completed its critique against the supplied complete base diff and found no remaining findings; its initial missing-diff limitation is resolved.

- At archive sync, re-point `covers_requirement` annotations from the two renamed requirement IDs (`webclient-quest-log-panel::the-quest-log-panel-is-an-exact-read-only-version-1-presentation-panel`, `...::an-unresolvable-issuance-yields-no-reward-line-rather-than-a-fabricated-one`) to their new IDs from `tools.spec_traceability list`. Annotate the tests from 2.2 for the new claim-disclosure requirement, then run `tools.spec_traceability check`.
- Do not apply, archive, or merge until the user asks.
