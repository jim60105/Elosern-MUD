# Proposal: conversing and finalized stages for the dream session

## Batch: dream proposal co-editing

Stage 4 of 8 of `docs/superpowers/specs/2026-11-13-dream-proposal-coediting-design.md`
("Stages", "Server Actions", "Error Handling", the panel-state paragraph).

- depends-on: dream-working-proposal
- conflict: `server/dream_service.py`, `world/narrative/dream_surface.py`,
  `world/narrative/tests/test_dream_surface.py`,
  `web/webclient/actions/dream_actions.py`, `command_echo.js` (shared with
  `dream-working-proposal`); `web/webclient/presentation/dream.py`,
  `protocol/panels/dream.js`, `protocol/constants.js`,
  `web/static/webclient/js/tests/protocol_dream.test.js`,
  `web/webclient-app/tests/dream.test.js`,
  `stories/World/DreamPanel.stories.js` (shared with
  `dream-wish-stage-panel`, which bumps the panel schema again and removes the
  schema-3 keys this change keeps). `openspec/specs/webclient-dream-stage`
  requirement "The dream is a full-stage AVG scene over its official artwork"
  is modified here and again by `dream-wish-stage-panel`.
- interim (ended by the next two stages): the browser panel and the text
  command are unchanged, so neither offers `finalize` yet. With them, a
  confirmation or a hand-written draft before the sixth exchange is refused
  with a reason; after the sixth exchange both work. `dream.finalize` echoes
  `dream finalize`, added by `dream-wish-text-commands`.

## Why

The session now keeps a model-edited working proposal, but the player can
still overwrite it at any moment and confirm without ever taking it over. The
design gives each session two stages with one rule: manual editing is allowed
exactly when free text is closed.

## What Changes

- `DreamSession` records a stage, `conversing` or `finalized` (one new field,
  one schema migration).
- New action `finalize` (service and web action `dream.finalize`): refused
  while a response is pending; closes free text for this dream and saves the
  working proposal as the session draft. The sixth settled exchange finalizes
  the same way.
- While conversing: supplied direction content and `confirm` are refused
  without a write; `draft` saves the working proposal.
- Once finalized: `draft` and `confirm` take the submitted form as the new
  working proposal. `confirm` saves it and confirms that saved version in one
  transaction. The thread stays locked; a thread that is no longer offered
  may be released to a new story.
- A session resumed on a later sleep returns to conversing when exchanges
  remain.
- Panel schema 4: adds `stage`, `proposal`, `changes`, `thread_id`,
  `can_choose_thread`, `can_finalize`, `can_edit`, `drafted`. The schema-3
  keys stay until `dream-wish-stage-panel` removes them.
- **BREAKING**: `confirm` before `finalize` is refused.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `dream-session-lifecycle`: the stage requirement; convergence and exit
  choices follow the stage.
- `dream-authoring`: a confirmation saves the submitted finalized proposal as
  the shown version and confirms exactly that version.
- `webclient-dream-stage`: the dream panel wire carries the stage fields.

## Impact

- Code: `world/narrative/models.py`,
  `world/narrative/migrations/0013_dream_session_stage.py` (new),
  `world/narrative/dream_session.py`, `world/narrative/dream_surface.py`,
  `server/dream_service.py`, `web/webclient/presentation/dream.py`,
  `web/webclient/actions/dream_actions.py`,
  `web/static/webclient/js/elosern/protocol/panels/dream.js`,
  `protocol/constants.js`, `command_echo.js`, and the tests and fixtures
  named in design.md.
- `world/narrative/authoring.py` is not changed: the store's requirement
  version checks stay as they are.
- Estimate: 8.5 hours (model, migration and lifecycle 1.5 h, service 1.5 h,
  read model, wire and validators 2 h, web action and echo 0.5 h, tests 2 h,
  existing-test repair and gates 1 h).
