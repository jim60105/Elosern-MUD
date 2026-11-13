# Proposal: the dream collaborator returns proposal edits

## Batch: dream proposal co-editing

Stage 2 of 8 of `docs/superpowers/specs/2026-11-13-dream-proposal-coediting-design.md`
("Edit Contract", "Working Proposal", "Error Handling" row "Invalid edits").

- depends-on: dream-proposal-edit-applier
- conflict: `world/ai/dream.py`, `prompts/dream.yaml`,
  `world/ai/tests/test_dream_presentation.py` are touched only by this change
  in the batch. `world/narrative/dream_surface.py` (`store_response`) and
  `world/narrative/tests/test_dream_surface.py` are touched again by
  `dream-working-proposal`, `dream-wish-stages`, `dream-wish-stage-panel` and
  `dream-farewell-beat`; apply the batch in its stated order.

## Why

The dream collaborator returns scene, dialogue, phase and a whole requirement
list. It cannot change a proposal step by step, and it never sees one. The
model contract has to carry edit commands, and an invalid edit set has to fail
the response inside the existing validation retry instead of reaching the
session.

## What Changes

- The dream output schema drops `requirements` and gains an optional `edits`
  array of the commands defined by `dream-proposal-editing`.
- `generate_dream_exchange` accepts the current proposal and the chosen
  thread label, puts both in the prompt (the proposal with line numbers), and
  validates the returned edits by applying them; an edit set that does not
  apply invalidates the response and goes through the existing retry.
- Edit text passes the same forbidden-content validators as scene and dialogue.
- `DreamExchange` carries the resulting proposal and its change report
  instead of `requirements`.
- `prompts/dream.yaml` describes the new output contract.
- The session does not store a working proposal yet (`dream-working-proposal`
  does). Until then the service keeps calling with no proposal, so every turn
  edits an empty proposal and the surface shows the resulting requirement rows
  exactly where it showed the model's requirement list before.
- **Human-reviewed:** the wording of the system prompt in `prompts/dream.yaml`
  is model-facing copy. No test judges it; it is reviewed by a person against
  the source design's "Edit Contract" section.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `dream-explicit-presentation`: the collaborator's permitted context gains
  the current proposal and the chosen thread label; a new requirement states
  how returned proposal edits are validated.

## Impact

- Code: `world/ai/dream.py`, `prompts/dream.yaml`,
  `world/narrative/dream_surface.py` (`store_response`, one statement),
  `world/ai/tests/test_dream_presentation.py`,
  `world/narrative/tests/test_dream_surface.py` and
  `world/narrative/tests/test_dream_dispatch.py` (fixtures and the drift test).
- No migration, no panel wire change, no new dependency.
- Estimate: 7 hours (schema, validators and prompt builder 2.5 h, prompt text
  0.5 h, tests 3 h, fixture updates and gates 1 h).
