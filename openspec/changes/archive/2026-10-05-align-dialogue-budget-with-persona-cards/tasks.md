# Tasks: align-dialogue-budget-with-persona-cards

## 1. Budget profile

- [x] 1.1 Raise the `npc_dialogue` budget profile in `build_dialogue_context`
  to `context_window=16384`, `character_anchor` hard bound 5200, and an
  explicit `turn_frames` hard bound of 15366, with a comment tying the sizing
  to the persona-card bounds
- [x] 1.2 Replace the `min(system + turn_frames, budget)` final aggregate cap
  with the profile `max_input_budget` alone, keeping the existing
  oldest-first reduction ladder and mandatory-reject semantics unchanged

## 2. Tests

- [x] 2.1 Add the regression test
  `test_full_persona_card_pair_stays_inside_the_input_budget` in
  `world/narrative/tests/test_dialogue_epochs.py` covering the delta
  requirement (full-bound NPC card + player public persona builds without
  degradation); verified red before the fix (same
  `ContextBudgetExceededError` as the field failure) and green after
- [x] 2.2 De-pin the fixed `3078` budget assertion in
  `test_movement_preserves_prefix_and_original_frame_bytes` to the
  `total_rendered_tokens <= max_input_budget` invariant
- [x] 2.3 Run the focused suites green: `world.narrative.tests.test_dialogue_epochs`,
  `world.narrative.tests.test_dialogue_memory`,
  `world.narrative.tests.test_correspondence_memory`,
  `world.narrative.tests.test_narrative_context`,
  `world.ai.tests.test_npc_dialogue_prompts`,
  `typeclasses.tests.test_npc_dialogue`

## 3. Documentation and gates

- [x] 3.1 Update `docs/development/dialogue-epoch-calibration.md`: npc_dialogue
  row 16384/15366 and the persona-card sizing rationale
- [x] 3.2 Run `uv run --locked python -m tools.contract_gate`
  (traceability/lints/manifests/contracts) green and
  `python -m compileall -q world` plus `git diff --check` clean
