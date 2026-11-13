# Proposal: text commands for the dream wish

## Batch: dream proposal co-editing

Stage 6 of 10 of `docs/superpowers/specs/2026-11-13-dream-proposal-coediting-design.md`
("Text Commands", "Player-Facing Wording").

- depends-on: dream-wish-stage-wire
- conflict: `commands/dream.py`, `docs/game/commands.md`,
  `docs/game/command-reference.md`, `tests/test_command_docs.py` are touched
  only by this change in the batch.
  `world/narrative/tests/test_dream_surface.py` is shared with the other
  server stages; apply in batch order.

## Why

The server now has thread choice, stages and a model-edited proposal, but the
text client can reach none of it: `dream` has no way to choose a thread or to
finalize, and it still prints one direction line instead of the proposal and
what changed.

## What Changes

- `dream thread [編號|new]` chooses the story the wish belongs to (no argument
  lists the choices); `dream finalize` stops the conversation and hands the
  wish over.
- Bare `dream` prints the whole wish, its thread and the last change report,
  naming removed items.
- A delivered `dream say` ends its output with a one-line change summary.
- `dream draft <text>` and `dream confirm <text>` keep their meaning (replace
  the summary) and, like the server rule, work only after finalize. The JSON
  form stays accepted after finalize.
- Usage text, command documents and the command-docs manifest follow.
- Text wording uses the design's vocabulary (願望, 訴說, 親自修改, 收著,
  許下).
- **Human-reviewed:** the Traditional Chinese wording of the command output
  and of the two documentation pages is reviewed by a person against the
  source design's "Player-Facing Wording" table. Tests establish structure
  and routing only.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `dream-sleep-surface`: adds the text-command requirement for thread choice,
  finalize and the change report.

## Impact

- Code: `commands/dream.py`, `tests/test_command_docs.py`,
  `docs/game/commands.md`, `docs/game/command-reference.md`,
  `world/narrative/tests/test_dream_surface.py`.
- No server rule changes: every command routes to the existing
  `server.dream_service.act`.
- Estimate: 4.5 hours (command and renderers 1.5 h, tests 1.5 h, documents and
  manifest 1 h, gates 0.5 h).
