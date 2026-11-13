# Proposal: the dream panel publishes the wish stages

## Batch: dream proposal co-editing

Stage 5 of 10 of `docs/superpowers/specs/2026-11-13-dream-proposal-coediting-design.md`
("Stages", "Server Actions" row `finalize`, "Browser Surface" stage flags).

- depends-on: dream-wish-stages
- conflict: `web/webclient/presentation/dream.py`,
  `web/static/webclient/js/elosern/protocol/panels/dream.js`,
  `web/static/webclient/js/elosern/protocol/constants.js`,
  `web/static/webclient/js/tests/protocol_dream.test.js`,
  `web/webclient-app/tests/dream.test.js`,
  `stories/World/DreamPanel.stories.js` and
  `web/webclient/actions/dream_actions.py`, `command_echo.js` (shared with
  `dream-wish-change-report`, which bumps the schema again and removes the
  schema-3 keys) and `world/narrative/tests/test_dream_surface.py` (shared
  with the other server stages). `openspec/specs/webclient-dream-stage`
  requirement "The dream is a full-stage AVG scene over its official artwork"
  is modified here and again by `dream-wish-stage-panel`. Apply in batch
  order.
- interim (ended by `dream-wish-stage-panel`): the browser panel and the text
  command still behave as before, so the old panel is rejected by the new
  schema until it is replaced, and the text client cannot reach `finalize`
  until `dream-wish-text-commands`.

## Why

The session records a stage and refuses every action the stage forbids, but
nothing tells the browser about it: the panel state still publishes the
schema-3 shape, and `dream.finalize` exists only as a service action. The
player needs the stage, the working proposal, the change report, the chosen
thread and the stage flags — and a wire the client validates exactly.

## What Changes

- `dream_state` adds `stage`, `proposal`, `changes`, `thread_id`,
  `can_choose_thread`, `can_finalize`, `can_edit` and `drafted`, and
  `can_confirm` follows the stage. The schema-3 keys stay until
  `dream-wish-change-report` removes them.
- Panel schema 4 on both sides: the server presenter and the client
  validator declare the same version and validate the new fields, their
  bounds and their stage invariants.
- New web action `dream.finalize` with its own validator, registration,
  command echo entry and registry enumeration; the production action roster
  in `webclient-action-dispatch` gains it and both roster scenarios are
  restated.
- An envelope test builds the largest legal dream state and pins it under the
  65,536-byte canonical JSON limit, so the aggregate proposal and report
  budgets cannot be raised without failing.
- **BREAKING** (wire): schema-3 dream payloads are rejected.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-dream-stage`: the dream panel wire carries the stage fields.
- `webclient-action-dispatch`: the production action roster gains
  `dream.finalize`.

## Impact

- Code: `world/narrative/dream_surface.py` (`dream_state`),
  `web/webclient/presentation/dream.py`,
  `web/static/webclient/js/elosern/protocol/panels/dream.js`,
  `protocol/constants.js`, `web/static/webclient/js/tests/protocol_dream.test.js`,
  `web/webclient/actions/dream_actions.py`,
  `web/static/webclient/js/elosern/command_echo.js`,
  `web/webclient/actions/tests/test_dispatcher/test_registry.py`,
  `web/webclient/presentation/tests/test_dream_artwork.py`,
  `web/webclient-app/tests/dream.test.js` and
  `stories/World/DreamPanel.stories.js` (fixtures only, no component or
  assertion change), rebuilt `dist`.
- No migration, no prompt change, no server-rule change.
- Estimate: 4.5 hours (read model 1 h, validator 1.5 h, action and echo 0.5 h,
  tests and fixtures 1 h, gates 0.5 h).
