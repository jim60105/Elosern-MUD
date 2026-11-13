# Proposal: conversing and finalized stages for the dream session

## Batch: dream proposal co-editing

Stage 4 of 10 of `docs/superpowers/specs/2026-11-13-dream-proposal-coediting-design.md`
("Stages", "Server Actions", "Error Handling").

- depends-on: dream-working-proposal
- conflict: `server/dream_service.py`, `world/narrative/dream_surface.py`,
  `world/narrative/tests/test_dream_surface.py` are touched again by
  `dream-wish-stage-wire`, `dream-wish-text-commands` and
  `dream-farewell-beat`; `world/narrative/dream_session.py` (lifecycle and
  migration) is touched only here in the batch. Apply in batch order.
- interim (ended by the next two stages): the browser panel still receives
  schema 3 and the text command is unchanged, so neither offers `finalize`
  yet. A confirmation or a hand-written draft before the sixth exchange is
  refused with a reason; after the sixth exchange both work.
  `dream-wish-stage-wire` publishes the stage and `dream.finalize`.

## Why

The session now keeps a model-edited working proposal, but the player can
still overwrite it at any moment and confirm without ever taking it over. The
design gives each session two stages with one rule: manual editing is allowed
exactly when free text is closed.

## What Changes

- `DreamSession` records a stage, `conversing` or `finalized` (one new field,
  one additive schema migration). No data migration: the batch ships with a
  reset database, so no in-progress wish is carried across.
- New service action `finalize`: refused while a response is pending; closes
  free text for this dream and saves the working proposal as the session
  draft. The sixth settled exchange finalizes the same way.
- While conversing: supplied direction content and `confirm` are refused
  without a write; `draft` saves the working proposal; thread choice is still
  open. Once finalized: `draft` and `confirm` take the submitted form as the
  new working proposal, `confirm` saves and confirms that saved version in
  one transaction, and thread choice is refused. The thread stays locked; a
  thread that is no longer offered may be released to a new story.
- A JSON form that omits `thread_id` keeps the locked thread instead of
  reading as a new story.
- A session resumed on a later sleep returns to conversing when exchanges
  remain.
- **BREAKING**: `confirm` before `finalize` is refused.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `dream-session-lifecycle`: the stage requirement; convergence and exit
  choices follow the stage.
- `dream-authoring`: a confirmation saves the submitted finalized proposal as
  the shown version and confirms exactly that version.

## Impact

- Code: `world/narrative/models.py`,
  `world/narrative/migrations/0013_dream_session_stage.py` (new),
  `world/narrative/dream_session.py`, `world/narrative/dream_surface.py`,
  `server/dream_service.py`, and the tests named in design.md.
- No wire change, no action change, no fixture change; the read model, panel
  schema 4 and `dream.finalize` belong to `dream-wish-stage-wire`.
- `world/narrative/authoring.py` is not changed: the store's requirement
  version checks stay as they are.
- Estimate: 6 hours (model, migration and lifecycle 1.5 h, service gating
  and confirm flow 2 h, tests 1.5 h, existing-test repair and gates 1 h).
