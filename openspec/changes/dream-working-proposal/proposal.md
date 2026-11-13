# Proposal: the dream session keeps a working proposal

## Batch: dream proposal co-editing

Stage 3 of 8 of `docs/superpowers/specs/2026-11-13-dream-proposal-coediting-design.md`
("Working Proposal", "Thread choice", "Server Actions" rows `choose_thread`
and `say`, "Error Handling").

- depends-on: dream-collaborator-proposal-edits
- conflict: `server/dream_service.py`, `world/narrative/dream_surface.py`,
  `web/webclient/actions/dream_actions.py`,
  `web/static/webclient/js/elosern/command_echo.js` and
  `world/narrative/tests/test_dream_surface.py` are touched again by
  `dream-wish-stages`; apply in batch order.
- interim (removed by later stages of this batch): the panel wire stays at
  schema 3 and the browser panel is unchanged, so the browser cannot choose a
  thread yet and its sheet still labels the model-written summary with the
  old provenance text. `dream.choose_thread` echoes `dream thread …`, a text
  command that `dream-wish-text-commands` adds. Player-supplied directions are
  still accepted in every state; `dream-wish-stages` gates them.

## Why

Each `say` stores the player's raw message as the story direction, and the
model's edits (available since `dream-collaborator-proposal-edits`) are
applied to an empty proposal and thrown away. The session needs one
structured working proposal that the model reads and edits turn after turn,
and the thread the proposal belongs to has to be chosen before the first
message so the model can write for it.

## What Changes

- The dream surface association holds a structured working proposal, the last
  change report, the chosen thread and whether the thread is locked, in place
  of the single `direction` string and the `requirements` list.
- `say` no longer stores the message as the direction. It passes the working
  proposal and the chosen thread's label to the collaborator and, when the
  exchange settles, stores the edited proposal and its change report. A failed
  or stale response changes nothing.
- New action `choose_thread` (service and web action `dream.choose_thread`):
  allowed until the first `say` is accepted, then refused.
- A draft saved with no supplied direction, and the automatic draft on
  awakening, take the working proposal instead of the last message.
- **BREAKING** (internal): `dream_surface.store_direction` is removed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `dream-session-lifecycle`: adds the working proposal and the thread choice
  lock.

## Impact

- Code: `world/narrative/dream_surface.py`, `server/dream_service.py`,
  `web/webclient/actions/dream_actions.py`,
  `web/static/webclient/js/elosern/command_echo.js` with
  `web/static/webclient/js/tests/command_echo.test.js` and
  `command_echo_coverage_manifest.json`,
  `web/webclient/actions/tests/test_dispatcher/test_registry.py`,
  `world/narrative/tests/test_dream_surface.py`.
- No migration (the association is an Evennia Attribute), no panel schema
  change, no prompt change.
- Estimate: 7 hours (surface 1 h, service 1.5 h, web action and echo 1 h,
  tests 2.5 h, existing-test repair and gates 1 h).
