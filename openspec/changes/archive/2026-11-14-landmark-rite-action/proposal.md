# Proposal

## Why

`landmark-rite-settlement` can settle a rite but nothing reaches it. Players need two entry points that share that one settlement: the registered browser action `explore.landmark_rite` and the text command `儀式`. With both in place and the shipped content adopted (`landmark-rite-content`, `landmark-rite-content-completion`), rites become performable and recorded while districts still light from visits, so the game stays fully playable.

## What Changes

- New registered action `explore.landmark_rite` with the exact payload `{option, member_id}`. The server resolves the district, archetype, cost and scene itself and ignores nothing: any other field is rejected. The action carries the dispatcher's request identity so a duplicate request replays the committed result.
- The action's success result carries the delivered scene as an authored-scene delivery, for the panel and stage changes to adopt.
- New text command `rite` (alias `儀式`): with no argument it lists the guardian, the options and which were experienced; with an option it performs it with the controlled character; with an option and a companion name it performs it with that companion. The complete scene is emitted at once, then one completion line.
- Player command documentation for the new command.

## Capabilities

### New Capabilities

- `landmark-rite-command`: the browser action and the text command, their inputs, outputs and refusals.

### Modified Capabilities

None. The command reference gains the new command under the existing `game-command-docs` drift contract.

## Impact

- New: `web/webclient/actions/rite_actions.py`, `commands/rite.py`, `web/webclient/actions/tests/test_rite_actions.py`, `commands/tests/test_rite_command.py`.
- Edits: `web/webclient/actions/registry.py`, `web/webclient/actions/dispatcher.py` (`_REQUEST_IDENTITY_ACTIONS`), `web/webclient/actions/tests/test_dispatcher/test_registry.py` (the listed action identifiers), `web/static/webclient/js/elosern/command_echo.js`, `web/static/webclient/js/tests/command_echo_coverage_manifest.json`, `web/static/webclient/js/tests/command_echo.test.js`, `commands/default_cmdsets.py`, `docs/game/commands.md`, `docs/game/command-reference.md`, `docs/development/webclient-synchronization.md`, `.github/evennia-shards.json`.
- No browser surface dispatches the action yet (`landmark-rite-stage`).

## Batch:

- depends-on: landmark-rite-content-completion
- depends-on: landmark-rite-settlement
- conflicts: `landmark-rite-panel` edits `web/webclient/actions/rite_actions.py`; it runs after this change.
