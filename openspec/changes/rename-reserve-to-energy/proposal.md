# Proposal: rename-reserve-to-energy

## Why

Players read the long-term fatigue quantity as 精神儲備, a four-character technical term that crowds the status row and the handoff labels and reads like an internal resource name. The approved rest entry design (`docs/superpowers/specs/2026-10-24-rest-entry-redesign-design.md` §9, change 2) shortens the player-facing term to 精力 everywhere a player reads it.

## What Changes

- The status panel's fatigue row reads `<name>：精力 N%（<stage label>）` instead of `<name>：精神儲備 N%（…）`.
- The travel refusal for predicted pre-destination depletion reads `隊伍成員的精力不足以支撐這趟旅行。`.
- The sleep-handoff candidate suffix, shared by the text `handoff` listing and the browser roster, reads `（精力 N%）`.
- The player command documentation (`docs/game/commands.md`, `docs/game/command-reference.md`) uses 精力 for every occurrence of 精神儲備.
- The tests that assert these strings change with them.
- Unchanged: fatigue stage labels (精神充沛, 輕度疲勞, 中度疲勞, 重度疲勞, 強制睡眠, 沉睡), code identifiers, code and rulebook comments, and developer docs such as `docs/development/distance-based-travel.md`, which may keep 精神儲備.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mental-reserve`: adds one requirement that every player-facing surface naming a body's reserve calls it 精力 and never 精神儲備.

No existing requirement text in `openspec/specs/` contains 精神儲備, so no MODIFIED delta is needed.

## Impact

- Server: `world/rules/travel_cost.py` (`DEPLETION_MESSAGE`), `world/rules/possession.py` (`handoff_candidate_label`).
- Client: `web/webclient-app/components/StatusPanel.vue`.
- Docs: `docs/game/commands.md`, `docs/game/command-reference.md`.
- Tests: `tests/test_command_docs.py`, `world/rules/tests/test_possession.py`, `world/rules/tests/test_movement.py` (new message assertion), `commands/tests/test_handoff_command.py`, `web/webclient-app/tests/data/status_panel.test.js`, `web/webclient-app/tests/app_client_sleep_handoff.test.js`, `web/static/webclient/js/tests/protocol_sleep_handoff.test.js`.
- No payload shape, identifier, or persisted data changes.

## Batch:

depends-on: none

- Independent of `redesign-rest-entry`; that change's new tile text already reads 精力.
- Code-conflict note: both changes edit `docs/game/commands.md` and `docs/game/command-reference.md`, on different lines (this change: the 精神儲備 occurrences; the other: the web-client 等待 card sentences in the 等待 paragraph of `commands.md` and in the `wait` entry of `command-reference.md`). No other file is shared. Whichever lands second rebases with a textual merge only.
