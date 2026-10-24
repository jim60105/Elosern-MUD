# Tasks: rename-reserve-to-energy

Conventions: run Python tests with the Evennia test runner as `uv run --locked --env-file=<file> evennia test --settings test_settings.py --keepdb <label>`, where `<file>` is a scratch file containing the single line `MUD_TEST_SETTINGS=1`; run Vitest from the repo root as `npx --no-install vitest run <path>`; run the Node gate as `node --test <path>`. Replace only the exact strings listed. Do not touch code comments, docstrings, rulebook YAML comments, identifiers, `docs/development/`, `docs/superpowers/`, or `docs/design/`. Do not change any `covers_requirement(...)` string.

## 1. Server strings

- [ ] 1.1 In `world/rules/travel_cost.py`, change `DEPLETION_MESSAGE = "隊伍成員的精神儲備不足以支撐這趟旅行。"` to `DEPLETION_MESSAGE = "隊伍成員的精力不足以支撐這趟旅行。"`. In `world/rules/tests/test_movement.py`, in `test_a_non_distance_connector_refuses_exhaustion_before_arrival`, add `self.assertEqual(str(caught.exception), "隊伍成員的精力不足以支撐這趟旅行。")` right after the existing `caught.exception.reason` assertion. Verify: the label `world.rules.tests.test_movement` passes.
- [ ] 1.2 In `world/rules/possession.py` `handoff_candidate_label`, change `f"（精神儲備 {candidate.reserve_percent}%）"` to `f"（精力 {candidate.reserve_percent}%）"`. In `world/rules/tests/test_possession.py`, change `self.assertIn("精神儲備", offer)` to `self.assertIn("精力", offer)` and add `self.assertNotIn("精神儲備", offer)`. In `commands/tests/test_handoff_command.py`, change the three expected strings to `"1. 回到自己的身體（精力 100%）"`, `f"2. 接手 清醒同伴（精力 100%）"`, and `"接手 清醒同伴（精力 100%）（不在同一地點）"`. Verify: the labels `world.rules.tests.test_possession` and `commands.tests.test_handoff_command` pass.

- [ ] 1.3 In `world/rules/service_messages.py` `exam_started_message`, change `"雙方在開戰前與結束後都會恢復全部的體力、法力與精力。"` to `"雙方在開戰前與結束後都會恢復全部的體力、法力與耐力。"`. In `world/rules/tests/test_phase4_integration.py` (`test_register_to_promotion_loop`, around line 223), change the expected output to `"升階考核（E）開始。這是模擬戰，雙方在開戰前與結束後都會恢復全部的體力、法力與耐力。請選擇你的行動（cast <技能>[=<目標>]）。"`. Verify: `rg -n "法力與精力" world commands web tests docs` prints nothing and the label `world.rules.tests.test_phase4_integration` passes.

## 2. Client string

- [ ] 2.1 In `web/webclient-app/components/StatusPanel.vue`, change the fatigue row text `：精神儲備 {{ row.reserve_percent }}%` to `：精力 {{ row.reserve_percent }}%` (the rest of the line is unchanged). In `web/webclient-app/tests/data/status_panel.test.js`, change the two expectations to `"艾倫‧灰誓：精力 80%（測試充沛）"` and `"同行者：精力 2%（測試強制睡眠）"`. In `web/webclient-app/tests/app_client_sleep_handoff.test.js` and `web/static/webclient/js/tests/protocol_sleep_handoff.test.js`, replace every `精神儲備` in the fixture labels and expectations with `精力` (for example `"接手 同伴（精力 100%）"`, `"接手 沉睡者（精力 5%）"`). Verify: `npx --no-install vitest run web/webclient-app/tests/data/status_panel.test.js web/webclient-app/tests/app_client_sleep_handoff.test.js` and `node --test web/static/webclient/js/tests/protocol_sleep_handoff.test.js` pass.

## 3. Player documentation

- [ ] 3.1 In `docs/game/commands.md` and `docs/game/command-reference.md`, replace every `精神儲備` with `精力` (leave `精神恢復` as it is). Then replace the shorthand 滿儲備 in the two sleep descriptions: in `docs/game/commands.md` (line ~63) change `滿儲備不會把明確時長縮短；` to `即使精力全滿，也不會把明確時長縮短；`, and in `docs/game/command-reference.md` (line ~190, the `sleep` entry) change `滿儲備不會讓明確時長縮短，` to `即使精力全滿，也不會讓明確時長縮短，`. Change nothing else. In `tests/test_command_docs.py`, in `test_status_and_cast_entries_document_protected_physiology`, change `self.assertIn("精神儲備", status_description)` to `self.assertIn("精力", status_description)` and add `self.assertNotIn("精神儲備", status_description)`. Verify: `rg -n "精神儲備|滿儲備" docs/game` prints nothing, `rg -n "即使精力全滿" docs/game` prints exactly two lines, and the label `tests.test_command_docs` passes.

## 4. Integration checks

- [ ] 4.1 Run `rg -n "精神儲備" web/webclient-app/components web/webclient-app/tests web/static/webclient/js world/rules/travel_cost.py world/rules/possession.py world/rules/tests commands tests docs/game` and confirm it prints nothing; also run `rg -n "法力與精力|滿儲備" world commands web tests docs/game` and confirm it prints nothing. Then run `uv run --locked python -m tools.contract_gate` and `uv run --locked python -m tools.spec_traceability check`. Verify: no match and both commands pass.

## 5. Traceability (run during archive, right after the spec sync)

Run in the archive step after `openspec archive` syncs the `mental-reserve` delta into `openspec/specs/`, before the archive merge. Do not run during apply.

- [ ] 5.1 Run `uv run --locked python -m tools.spec_traceability list`, take the generated identifier of "Player-facing text names the reserve 精力", and add it (keeping the existing identifiers) to the `covers_requirement` of `test_a_non_distance_connector_refuses_exhaustion_before_arrival` (`world/rules/tests/test_movement.py`), `test_handoff_lists_fatigue_and_return_or_possess_meaning` (`commands/tests/test_handoff_command.py`), and `test_status_and_cast_entries_document_protected_physiology` (`tests/test_command_docs.py`). `test_register_to_promotion_loop` (`world/rules/tests/test_phase4_integration.py`, which asserts the exam sentence) has no decorator yet: add `from tools.spec_traceability import covers_requirement` to that file's imports (as `world/rules/tests/test_affinity_config.py` does) and put `@covers_requirement("<generated identifier>")` directly above that method. Verify: `uv run --locked python -m tools.spec_traceability check` and `uv run --locked python -m tools.contract_gate` pass.

## Workflow follow-up

- Archive the change after review; group 5 is part of the archive step.
