# affinity-ai Tasks

## 1. Dialogue schema and validators

- [x] 1.1 Extend `NPC_DIALOGUE_OUTPUT_SCHEMA` in `world/ai/npc_dialogue.py` so `adjust_relation`
      carries `delta`, a non-negative integer bounded 0–10 when present; keep the seven-kind
      whitelist unchanged. The schema bounds the value; exact single-field shape is the semantic
      validator's and applier's job (the schema has no `additionalProperties: false`).
- [x] 1.2 Add the per-kind semantic validator `_validate_relation_payload` (exactly one field
      `delta`, integer, 0–10, bool excluded) and register it in `_VALIDATORS`; keep registration
      atomic/idempotent per the existing `register_npc_dialogue` pattern.
- [x] 1.3 Add the per-call no-leak semantic validator factory
      `_make_no_affinity_leak_validator(value, cap)`: when an affinity context was injected, a
      reply whose speech contains the affinity value or the cap as a decimal integer substring
      (fullwidth digits folded via NFKC normalization) is a validation failure; the per-call
      validator travels with the request descriptor (`ChatRequestDescriptor.semantic_validators`)
      so the guardrail retries it within the budget without module-global state or
      cross-call contamination.
- [x] 1.4 Add schema and validator tests: valid `{"kind": "adjust_relation", "delta": 3}` passes;
      `delta` < 0, > 10, fractional, boolean, missing, or extra payload fields are rejected and
      retried; a speech echoing the value or cap is rejected and retried; a speech mentioning only
      the stage name passes; the rejected outputs never reach the engine.

## 2. Deterministic applier

- [x] 2.1 In `world/rules/npc_intents.py`, replace the `adjust_relation` forward-declared rejection
      with verification (exactly `delta`, integer, 0–10, bool excluded) and delegation to
      `apply_affinity_change(npc, player, "ai_dialogue", delta)` from `world/rules/affinity.py`.
- [x] 2.2 Extend `IntentOutcome` with a `delta_used: int | None` field; map the writer outcome by
      the actual applied amount: `delta_used > 0` → `applied=True` (even when the budget was also
      capped); `delta_used == 0` (fully blocked or rejected) → `applied=False` with reason, no
      state change; keep `offer_quest` and `reveal_lore` forward-declared.
- [x] 2.3 Add applier tests: full-amount delta reports applied with the amount; partial-budget
      delta reports applied with `delta_used=2`; zero-budget delta is discarded with the speech
      kept; malformed payload is discarded; a non-NPC target is rejected; no affinity write
      bypasses the writer (import-linter / boundary contract stays green).

## 3. Prompt injection

- [x] 3.1 Extend `build_npc_dialogue_prompt` with an optional `affinity_context` argument,
      serialized as `player.affinity = {"value": int, "cap": int, "stage": str}` through
      `_cap_value`; `None` omits the block; identical input stays byte-identical.
- [x] 3.2 Update `LLMNPC.at_talked_to` in `typeclasses/npcs.py` to read the NPC's own affinity
      context for the speaking player through the read-only relations handler — `has_record`
      gating, then the value/cap read accessor and `stage_for(player)`; never the writer; a
      recordless player yields no block.
- [x] 3.3 Add prompt and seam tests: the block carries the true value, cap, and stage; a recordless
      player yields no block; byte-identical determinism holds with and without the block; a talk
      through the seam leaves the stored affinity record unchanged; a corrupted `relations_data`
      record still lets the talk complete or degrade without crashing.
- [x] 3.4 Update the `npc_dialogue.system` template in `prompts/npc_dialogue.yaml` (data) to
      instruct choosing `adjust_relation` deltas from the supplied affinity values within 0–10 and
      treating the numeric value and cap as secrets never spoken aloud; verify with the project's
      prompt validator (`uv run --locked python -m world.prompts.validate`).

## 4. End-to-end and verification

- [x] 4.1 Add a `FakeLLMClient` replay test: an NPC dialogue reply carrying
      `{"kind": "adjust_relation", "delta": 5}` flows prompt → guarded call → applier → affinity
      record, with the speech presented; a leak-echo reply flows through retry and never presents
      the number.
- [x] 4.2 Add an offline test: with the `npc_dialogue` profile failing, the reply degrades to
      greeting/silence and no affinity changes.
- [x] 4.3 Annotate substantive new tests with `covers_requirement` using canonical IDs from
      `uv run --locked python -m tools.spec_traceability list`, including the renamed prompt
      requirement's new ID; update stale annotations that referenced the old requirement name.
- [x] 4.4 Run the touched test labels (`world.ai`, `world.rules` npc-intents/affinity,
      `typeclasses` npc/entity, prompt-library) and `tests/test_ai_transport_contract.py`;
      run `uv run --locked python -m compileall -q world typeclasses commands server` and keep
      `git diff --check` clean.
- [x] 4.5 Run `openspec validate affinity-ai --strict` and
      `uv run --locked python -m tools.spec_traceability check`; before handoff run the required
      test entry points with the same `OPENSPEC_TEST_EVIDENCE` path and the verifier's
      `verify --evidence` mode.
