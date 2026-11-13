# Proposal: pure applier for dream proposal edits

## Batch: dream proposal co-editing

Stage 1 of 8 of `docs/superpowers/specs/2026-11-13-dream-proposal-coediting-design.md`
("Edit Contract", "Module boundary").

- depends-on: none
- conflict: none. This change adds one new module and one new test module and
  edits `.github/evennia-shards.json` (one appended line).

Order of the batch: `dream-proposal-edit-applier` →
`dream-collaborator-proposal-edits` → `dream-working-proposal` →
`dream-wish-stages` → `dream-wish-text-commands` → `dream-wish-stage-panel` →
`dream-wish-change-report` → `dream-farewell-beat`.

## Why

Dream collaboration is going to let the model edit a structured proposal step
by step. Every later stage needs one deterministic place that applies a set of
edit commands to a proposal and reports what changed. Building it first, with
no database and no session, lets every later stage depend on a tested contract.

## What Changes

- New pure module `world/narrative/dream_proposal.py`: the canonical proposal
  shape, the three edit commands (`str_replace`, `insert`, `create`) over seven
  fixed paths, all-or-nothing application, normalization, bounds, a closed set
  of error codes, the per-field change report and the numbered-line rendering a
  prompt will use.
- New test module `world/narrative/tests/test_dream_proposal.py`.
- Nothing calls the module yet. No player-visible behaviour changes.

## Capabilities

### New Capabilities

- `dream-proposal-editing`: how edit commands change a dream proposal, what
  makes an edit set invalid, and how the change report is computed.

### Modified Capabilities

None.

## Impact

- Code: `world/narrative/dream_proposal.py` (new),
  `world/narrative/tests/test_dream_proposal.py` (new),
  `.github/evennia-shards.json`.
- No migration, no wire change, no prompt change, no dependency.
- Estimate: 5 hours (module 2 h, tests 2.5 h, gates 0.5 h).
