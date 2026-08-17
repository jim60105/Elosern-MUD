## 1. Bounded-context serializer

- [x] 1.1 Define the frozen `ActionOptionsContext` struct and the budget constants in
  `world/ai/action_options.py` (room_name ≤ 40, room_summary ≤ 300, narrative_tail ≤ 600,
  npc_entries ≤ 8 with persona digests ≤ 160, monster_entries ≤ 4 at ≤ 80, objective ≤ 120,
  affordances ≤ 16); module docstring follows the narrator's no-Evennia-import discipline.
- [x] 1.2 Implement `build_options_context(...)` as a pure function over plain data (room,
  entities with stable positional order, objective, narrative tail, affordances tuple, and the
  caller-collected secret tokens) applying the fixed truncation policy: narrative tail dropped
  first, then persona-digest characters, then oldest NPC entries; `affordances`, `room_name`, and
  `room_summary` are never truncated. A call-site value exceeding one of the never-truncated caps
  raises a named `ActionOptionsInputError`; the entry point catches it, logs bounded, and resolves
  `None` (no out-of-bounds data ever emitted).
- [x] 1.3 Compose the `LEAK_BLOCKLIST` (numeric literals + hidden trait keys) as a separate output
  consumed by validation only; assert it is never serialized into the rendered prompt.
- [x] 1.4 Tests: per-fixture truncation order (tail → digest → NPC count), budget boundaries and
  one-past-boundary, named input error for over-budget non-truncatable values (entry point
  resolves `None`), byte-identical determinism for identical inputs, blocklist-vs-prompt
  separation, and stable positional NPC order across two identical constructions.

## 2. Prompt assembly

- [x] 2.1 Implement `build_action_options_prompt(context)`: system message via
  `render_prompt("action_options.system", ...)` and user message via
  `render_prompt("action_options.user", ...)` (no prompt text as a Python constant; the user
  message substitutes exactly the seven `ActionOptionsContext` fields, pre-serializing the
  structured ones — affordance list with canonical `action_id` + typed params, NPC entries with
  positional `npc_index`, objective line, narrative tail).
- [x] 2.2 Placeholder allowlist parity: a contract test asserting each prompt-library key's
  allowlist matches what this module renders with — the user key's allowlist equals the seven
  serialized `ActionOptionsContext` fields, the system key's is empty (unknown placeholder fails
  loudly).
- [x] 2.3 Tests: rendered user message contains the affordance list + index mapping and no
  blocklist tokens; parity assertion per 2.2.

## 3. Generation pipeline

- [x] 3.1 Implement `register_action_options()` mirroring `register_npc_dialogue`: idempotent
  (second call no-op), atomic (partial failure uninstalls only this module's own hooks),
  installing the degrade fallback (`None`) — no semantic validators (D-2; the ladder owns every
  text gate with generic patterns — narrator's token-specific regex and missing digit gate are
  not reusable) — and registering the `action_options` output schema in
  `world/ai/schemas/registry.py` validating the **raw model wire shape** (optional `params` on
  `known_action`, `npc_index` on `freeform`; never caller-injected `fingerprint`/`status`/
  `action_code`/`params`).
- [x] 3.2 Implement the shared total `_evaluate_enriched(parsed, *, fingerprint, affordances,
  npc_bindings, leak_blocklist) -> (OptionSet | None, list[str])` helper: resolve freeform
  `{npc_index}` to `params: {"npc_id": int}` against the bound NPC list (unknown index / duplicate
  target → binding error), run the schema change's `validate_optionset(raw, *, fingerprint,
  affordances, leak_blocklist)` raise-only ladder entry point, map each caught rejection to
  `"stage N: <code>"`, and reject sets passing the ladder with fewer than `MIN_CARDS` (3) as the
  layer's generation-rule failure (D-4a). The helper never raises; every parsing/enrichment/
  binding/ladder exception becomes a named error in the round's list.
- [x] 3.3 Implement `generate_action_options(context, client, *, fingerprint)` wrapping
  `guardrail.guarded_call("action_options", client, descriptor)` with `schema_id="action_options"`
  and the per-call semantic validator closure (3.2, capturing this call's fingerprint/affordances/
  bindings/blocklist) on the descriptor: profile gate before any prompt or transport work
  (disabled → `None`, stub never called), `ActionOptionsInputError` from the builder caught →
  bounded diagnostic + `None`, final strict re-validation of the accepted text through the same
  helper into a frozen `OptionSet` (defensive internal-error guard → bounded diagnostic + `None`).
- [x] 3.4 FakeLLM suite (callable matchers on `len(descriptor.messages)` — e.g. `== 2` then
  `== 3` with the last message asserted to contain round-1 errors — following the
  `test_npc_dialogue.py` retry-fixture pattern): first-attempt success (order preserved;
  `fingerprint`/`status` absent in the recorded raw fixture), generation-floor rejection (0, 2
  cards) → retry → exhaustion → `None`, 6-card ladder rejection → retry, binding rejection
  (unknown index, duplicate target) → retry with the binding error appended, leak-blocklist
  rejection (blocklist literal on a label/hint) → retry, exhaustion → `None` with call count
  `1 + max_retries`, timeout / HTTP / connection / malformed-body failures → `None` with exactly
  one call, disabled profile → stub never called, ladder-exception round maps to `"stage N: <code>"`
  without escaping, accepted 3-card and 5-card sets resolve (no retry, floor satisfied).

## 4. Startup wiring

- [x] 4.1 Add `_register_action_options_layer()` to `server/conf/at_server_startstop.py` following
  the boot-tolerant pattern of the other layers (foreign leftover registration logs a warning,
  never aborts startup), extended per D-7: `UnknownLayerError` (the `action_options` `LAYER_NAMES`
  slot arrives with the prompts change) and `DuplicateSchemaError`/`GuardrailRegistrationError`
  log a bounded warning and skip — a branch landing this wiring before its prerequisites must
  never abort startup; call it from `at_server_start`.
- [x] 4.2 Tests: double registration idempotency, partial-registration rollback leaves no
  half-installed hooks, the guarded attempt at startup tolerates a conflicting registration, and
  registration with the profile slot / schema entry point missing warns-and-skips (aborting
  startup on prerequisite absence is a regression).

## 5. Verification

- [x] 5.1 Run the owned package tests:
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py
  world.ai.tests.test_action_options_layer`
  plus `world.ai.tests.test_action_options_schema` (the consumed ladder entry point and its
  3–5-ladder boundary), `tests/test_ai_transport_contract.py` (module stays transport/state-
  writer-free), and `tests/test_command_docs.py` is unaffected (no command surface change).
- [x] 5.2 Trace the seven requirements to tests: bounded-context (1.4), prompt assembly (2.2/2.3),
  freeform binding (3.2/3.4), validation retry incl. generation floor (3.4), registration
  (4.2), proposal-only boundary (5.1 transport contract), generation outcome (3.4).
  `uv run --locked python -m tools.spec_traceability check` stays green; `git diff
  --check` clean; `openspec validate --changes action-options-layer --strict` passes.