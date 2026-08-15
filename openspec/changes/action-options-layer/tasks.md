## 1. Bounded-context serializer

- [ ] 1.1 Define the frozen `ActionOptionsContext` struct and the budget constants in
  `world/ai/action_options.py` (room_name ≤ 40, room_summary ≤ 300, narrative_tail ≤ 600,
  npc_entries ≤ 8 with persona digests ≤ 160, monster_entries ≤ 4 at ≤ 80, objective ≤ 120,
  affordances ≤ 16); module docstring follows the narrator's no-Evennia-import discipline.
- [ ] 1.2 Implement `build_options_context(...)` as a pure function over plain data (room,
  entities with stable positional order, objective, narrative tail, affordances tuple, and the
  caller-collected secret tokens) applying the fixed truncation policy: narrative tail dropped
  first, then persona-digest characters, then oldest NPC entries; `affordances`, `room_name`, and
  `room_summary` are never truncated.
- [ ] 1.3 Compose the `LEAK_BLOCKLIST` (numeric literals + hidden trait keys) as a separate output
  consumed by validation only; assert it is never serialized into the rendered prompt.
- [ ] 1.4 Tests: per-fixture truncation order (tail → digest → NPC count), budget boundaries and
  one-past-boundary, byte-identical determinism for identical inputs, blocklist-vs-prompt
  separation, and stable positional NPC order across two identical constructions.

## 2. Prompt assembly

- [ ] 2.1 Implement `build_action_options_prompt(context)`: system message via
  `render_prompt("action_options.system", ...)` (no prompt text as a Python constant) and the
  user message as the canonical serialization of the bounded context — affordance list with
  canonical `action_id` + typed params, NPC entries with positional `npc_index`, objective line,
  narrative tail.
- [ ] 2.2 Placeholder allowlist parity: a contract test asserting the `action_options.system`
  allowlist registered by the prompts change equals the serialized `ActionOptionsContext` fields
  (unknown placeholder fails loudly).
- [ ] 2.3 Tests: rendered user message contains the affordance list + index mapping and no
  blocklist tokens; parity assertion per 2.2.

## 3. Generation pipeline

- [ ] 3.1 Implement `register_action_options()` mirroring `register_npc_dialogue`: idempotent
  (second call no-op), atomic (partial failure uninstalls only this module's own hooks),
  installing the degrade fallback (`None`), the context-free semantic validators (CJK,
  placeholder, digit gates on labels/hints, reusing the narrator's validators), and registering
  the `action_options` output schema in `world/ai/schemas/registry.py`.
- [ ] 3.2 Implement the shared `_evaluate_enriched(parsed, *, fingerprint, affordances,
  npc_bindings) -> (OptionSet | None, list[str])` helper: resolve freeform `{npc_index}` to
  `params: {"npc_id": int}` against the bound NPC list (unknown index / duplicate target →
  binding error), then run the ladder entry point from the schema change (message-collecting
  variant if present, else named-error mapping) for the per-call retry loop and the strict final
  path.
- [ ] 3.3 Implement `generate_action_options(context, client)` wrapping
  `guardrail.guarded_call("action_options", client, descriptor)` with `schema_id="action_options"`
  and the per-call semantic validators (3.2) on the descriptor: profile gate before any prompt or
  transport work (disabled → `None`, stub never called), final strict re-validation of the
  accepted text into a frozen `OptionSet` (internal drift → bounded diagnostic + `None`).
- [ ] 3.4 FakeLLM suite: first-attempt success (order preserved; `fingerprint`/`status` absent in
  the recorded fixture), rejection → retry with the round's errors appended (assert the retry
  attempt consumes a fixture), exhaustion → `None` with call count `1 + max_retries`, timeout /
  HTTP / connection / malformed-body failures → `None` with exactly one call, disabled profile →
  stub never called, single/multiple `npc_index` binding, unknown index → retry.

## 4. Startup wiring

- [ ] 4.1 Add `_register_action_options_layer()` to `server/conf/at_server_startstop.py` following
  the boot-tolerant pattern of the other layers (foreign leftover registration logs a warning,
  never aborts startup), and call it from `at_server_start`.
- [ ] 4.2 Tests: double registration idempotency, partial-registration rollback leaves no
  half-installed hooks, and the guarded attempt at startup tolerates a conflicting registration.

## 5. Verification

- [ ] 5.1 Run the owned package tests:
  `uv run --locked evennia test --settings settings.py world.ai.tests.test_action_options_layer`
  plus `world.ai.tests.test_action_options_schema` (the consumed ladder entry point),
  `tests/test_ai_transport_contract.py` (module stays transport/state-writer-free), and
  `tests/test_command_docs.py` is unaffected (no command surface change).
- [ ] 5.2 `uv run --locked python -m tools.spec_traceability check` stays green; `git diff
  --check` clean; `openspec validate --change action-options-layer --strict` passes.