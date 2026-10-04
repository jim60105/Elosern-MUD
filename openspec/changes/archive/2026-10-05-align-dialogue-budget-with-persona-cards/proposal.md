# Proposal: align-dialogue-budget-with-persona-cards

## Why

The `npc_dialogue` rendered-budget profile was sized for the generic 4096-token
default window, which cannot hold the mandatory dialogue content of a
fully-authored character: the persona-injected character anchor (a valid
compact NPC card is bounded at 2000 rendered code points, ~4000
`token_est_v3` tokens) plus the speaking player's public persona inside the
mandatory current frame exceed the old 3078-token input budget with zero
history. Every dialogue turn with such a pair failed with
`ContextBudgetExceededError` and degraded to the authored greeting, making
free LLM conversation unusable for shipped cards (observed live with the
2000-code-point card pair 悠花/悠奈).

## What Changes

- Raise the `npc_dialogue` budget profile in `world/narrative/dialogue.py`:
  context window 16384 (max input 15366), `character_anchor` hard bound
  1800 → 5200, and an explicit `turn_frames` hard bound equal to the max
  input (the mandatory current frame lives inside that section; a smaller
  bound could reject after the aggregate reduction loop had already
  converged).
- Remove the secondary `min(system + turn_frames, budget)` aggregate cap in
  the final rejection check: it could sink below the mandatory system +
  current-frame content, rejecting prompts no deterministic reduction step
  can relieve. The profile max input becomes the single aggregate bound;
  the existing oldest-first reduction order (replay frames, chat memory,
  cognition, epoch summary) is unchanged and still rejects rather than drop
  mandatory content.
- Contractualize the sizing rule: the dialogue profile budgets SHALL admit
  the mandatory persona-card floor (see delta spec), so a future window
  shrink or bound tightening that reintroduces the degradation is caught by
  the spec and its covering test.
- Update `docs/development/dialogue-epoch-calibration.md` budget table, and
  replace the pinned `3078` test assertion with the
  `total_rendered_tokens <= max_input_budget` invariant.

No player-facing command surface changes; no persistence or schema changes.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `dialogue-epochs`: adds the requirement that the `npc_dialogue` rendered
  profile budget admits the mandatory persona-card floor and that section
  hard bounds can never reject content the aggregate bound already admits.

## Impact

- Affected code: `world/narrative/dialogue.py` (budget profile + final
  rejection bound), `world/narrative/tests/test_dialogue_epochs.py`
  (de-pinned assertion + regression test),
  `docs/development/dialogue-epoch-calibration.md`.
- Snapshot provenance: captured `budget_accounting.context_window` values
  for new dialogue snapshots change from 4096 to 16384 (accounting data
  only; readers use the stored `max_input_budget`).
- Related existing requirements untouched: `narrative-context::rendered-context-obeys-profile-budgets`
  (mechanism unchanged), `persona-dialogue-injection` requirements (the fix
  makes its no-truncation card injection actually reachable for full cards).
