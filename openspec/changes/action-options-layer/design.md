# Design: action-options-layer

## Context

This change is the generative half of the AI Action Options feature family
([overview](docs/superpowers/specs/2026-08-15-ai-action-options-overview-design.md)). The
vocabulary and validation ladder arrive with `action-options-schema`; the prompt YAML, the
`action_options` profile slot, and the prompt-library registration arrive with
`action-options-prompts`; the canonical affordance tuple comes from `action-options-affordance-contract`.
This change builds `world/ai/action_options.py`: the bounded-context serializer, the prompt
assembly, and the guarded generation pipeline that resolves `OptionSet | None`.

The repository already owns every mechanism this layer needs, and the design goal is to consume
those mechanisms without inventing parallel ones:

- `world/ai/guardrail.py::guarded_call` — validation → retry-with-appended-errors (budget
  `1 + max_retries`) → layer degrade fallback; transport failures degrade immediately without
  entering the retry loop; per-call semantic validators ride on the request descriptor.
- `world/ai/profiles.py` — frozen per-layer profiles with an `enabled` gate (`get_profile`).
- `world/ai/schemas/registry.py` — registered output schemas resolved by `schema_id`.
- `world/prompts/loader.py::render_prompt` + `world/prompts/registry.py` placeholder allowlist —
  the prompt library is the sole source of prompt text.
- Layer registration pattern: `register_npc_dialogue()` / `register_character_creation()` with
  atomic rollback, wired at `server/conf/at_server_startstop.py` (boot-tolerant).
- `world/ai/fake_client.py::FakeLLMClient` — replay double with scripted transport failures.

Constraints: the module is proposal-only (no state writes, no live transport, no socket, no
module-level Evennia imports/loggers — the transport-contract test covers it). No backward
compatibility: the project has zero released users.

## Goals / Non-Goals

**Goals:**

- `generate_action_options(context, client) -> defer.Deferred` resolving to a frozen `OptionSet`
  (`status: "ready"` only) or `None` under every failure mode (disabled profile, transport
  failure, retry exhaustion, internal error), with no partial success.
- `build_options_context(...)` — deterministic, public-only, bounded context serialization with
  the fixed truncation policy (narrative tail → persona digest → NPC count; `affordances`,
  `room_name`, `room_summary` never truncated) and a `LEAK_BLOCKLIST` consumed by validation only.
- Prompt assembly through `render_prompt("action_options.system", ...)` with placeholder-allowlist
  parity asserted by a contract test; the user message serializes the bounded context including
  the affordance list (canonical ids + params) and stable `npc_index` references.
- Validation-retry-degrade semantics per the pipeline design: validation/ladder rejections retry
  within `1 + max_retries` with the round's errors appended; transport failures resolve `None`
  immediately (no retry loop — the trigger service memoizes); exhaustion resolves `None`.
- Idempotent, atomic, boot-tolerant guardrail registration (fallback + semantic validators +
  output schema) wired at server startup.

**Non-Goals:**

- The `OptionSet`/`SuggestionCard` vocabulary, the enrichment entry point internals, the ladder
  stages, and the leak-gate predicates themselves (`action-options-schema`). This change only
  *consumes* the ladder and performs the caller-side injections the ladder's stage 0 requires.
- The `action_options.yaml` text, the placeholder allowlist entry, the `LAYER_NAMES` slot, and
  the `LLM_PROFILES` setting values (`action-options-prompts`).
- Fingerprint derivation, caches, session state, coordinator push, and dismissal
  (`action-options-trigger-service`); hook call sites (`action-options-trigger-hooks`).
- Any panel, protocol, or webclient surface (later changes in the family).

## Decisions

### D-1: Reuse `guardrail.guarded_call` instead of a hand-rolled loop

`generate_action_options` wraps `guarded_call("action_options", client, descriptor)` with the
layer's registered degrade fallback returning `None`. The guardrail already implements the exact
contract the pipeline design requires: validation failures append `"Validation failed: ..."`
and retry within the budget, transport failures degrade immediately, and a disabled profile
degrades without transport work.

*Alternative rejected:* a bespoke retry loop calling `client.get_response` directly. It would
duplicate the budget semantics, the transport-vs-validation distinction, and the error-message
appending — three behaviors the repository already pins down in `world/ai/guardrail.py` and its
main spec.

### D-2: Two-tier validator placement (registered + per-call)

- **Layer-registered semantic validators** — context-free text gates reused from the narrator:
  CJK presence, template-placeholder absence, and the no-digit gate, applied to labels and hints.
  These are stateless, so they belong in the registered set.
- **Per-call semantic validators** — carried on the request descriptor's
  `semantic_validators` (the guardrail already runs these after the registered ones): one
  closure bound to the call's `fingerprint`, `affordances`, and NPC bindings, which runs the
  enrichment + full ladder (canonical match replacing model-typed params, freeform binding,
  count bounds, leak gates) and returns the aggregated error messages for the retry loop.

*Alternative rejected:* registering context-dependent validators at the layer level. Registered
validators cannot see per-call state, so the canonical-match and binding checks would be
impossible there. *Alternative rejected:* validating only after `guarded_call` resolves, with no
in-loop ladder checks — that would make ladder failures undetectable inside the retry budget,
contradicting the pipeline design's retry semantics.

### D-3: One shared enrichment-and-ladder helper for both paths

A single private `_evaluate_enriched(parsed, *, fingerprint, affordances, npc_bindings) ->
(tuple[OptionSet | None, list[str]])` is used by (a) the per-call validator to produce retry
messages and (b) the final resolution step, which parses the accepted text again and demands the
strict `OptionSet`. Because both paths run the identical helper on the same input, an accepted
text cannot fail the final strict path; if it ever does (a non-deterministic state change between
trips), the layer logs a bounded diagnostic and resolves `None`.

### D-4: Caller-side enrichment contract with the schema change

The ladder's stage 0 requires the caller to inject `fingerprint` and `status: "ready"`; the
schema's LLM contract requires freeform `{npc_index}` resolution before validation. The schema
change's enrichment helper injects the caller-scoped fields and the freeform `action_code`
default (its tasks 3.2); this change owns the **binding resolution**: it resolves each freeform
card's `npc_index` against the prompt's bound NPC list (the positional order fixed by the
context builder) into `params: {"npc_id": int}` and passes the enriched card set through the
ladder; an out-of-range index or a target bound twice rejects the card with a binding error that
enters the retry loop. The schema change owns the ladder entry point; this change consumes
whichever form it ships — a message-collecting variant preferred for the retry loop, with a
fallback of mapping the named per-stage errors to messages (pinned by an integration test in
this change's suite, see Risks).

### D-5: Pure context-builder input contract

`build_options_context(...)` is a pure function over plain data: the deterministic call site
(the trigger service, change 5) hands in room name/summary, bounded narrative tail, present NPC
entries (identity, display name, dialogue key, persona digest, public tier), monster entries,
the public objective line, the canonical affordance tuple, and the caller-collected secret
tokens (numeric literals + hidden trait keys of its view). The builder composes the
`ActionOptionsContext` frozen struct and the `LEAK_BLOCKLIST`; the blocklist is an output for
validation consumption and is never serialized into the prompt. The builder cannot read traits
itself — it must stay Evennia-import-free.

### D-6: Prompt shape

- System message: `render_prompt("action_options.system", ...)` with exactly the allowlisted
  placeholders registered for the key by the prompts change. No prompt text as a Python
  constant.
- User message: the canonical serialization of the bounded context — room, entities with their
  positional `npc_index`, the objective line, the narrative tail, and the affordance list with
  each entry's canonical `action_id` and typed params (the same list the ladder's stage 9
  matches against). The model selects and curates; the ladder verifies.

### D-7: Registration wiring

`register_action_options()` mirrors `register_npc_dialogue()`: idempotent (second call no-op),
atomic (partial failure uninstalls only this module's own hooks), installing the degrade
fallback (`None`), the context-free semantic validators (D-2), and registering the
`action_options` output schema in `world/ai/schemas/registry.py`. `server/conf/at_server_startstop.py`
gains `_register_action_options_layer()` following the boot-tolerant pattern of the other
layers (a foreign leftover registration logs a warning instead of aborting startup).

## Risks / Trade-offs

- **[R1] The schema change ships only the raise-on-first-error ladder entry.** → The retry loop
  needs aggregated messages. Mitigation: the integration contract is pinned here — consume the
  message-collecting variant if present; otherwise wrap the named per-stage errors
  (`"stage N: <code>"`) into the retry text. Either way only the message producer differs; the
  retry/degrade behavior in this change's specs is unchanged.
- **[R2] Wording overlap with the schema change's "enrichment".** → Scope ruling (D-4): the
  ladder entry point and stage-0 validation are schema-owned; the caller-side injection
  (fingerprint/status, `npc_index` → `action_code`/`params`) is layer-owned. The integration
  test exercises both halves together.
- **[R3] The model may repeat the same binding/ladder failure across retries.** → The bounded
  budget terminates; exhaustion resolves `None`; the service memoizes transport failures but
  validation exhaustion simply degrades to rule cards (correct product behavior — never show
  unvalidated output).
- **[R4] Accepted text re-validated after `guarded_call` must not drift.** → Single shared
  `_evaluate_enriched` (D-3); the strict path is the same helper, so drift is structurally
  impossible. Remaining risk is state mutation between trips → bounded diagnostic + `None`.
- **[R5] Startup registration conflicts with other layers.** → Boot-tolerant registration per
  the existing pattern; correctness preserved because the layer gate (profile
  enabled/disables + degrade-fallback identity) still fails loudly on a foreign registration.
- **[R6] Truncation hides content from the model.** → Fixed, tested order guarantees the most
  decision-relevant inputs (affordances, room identity) survive any budget pressure.

## Migration Plan

Pure additive change: one new module, one new startup registration call, one new test suite.
The `action_options` profile slot and prompt file are prerequisites from the prompts change; the
ladder entry point and output schema from the schema change; until they land, the layer's own
tests register/consume thin local stand-ins in test fixtures only (no production code depends on
unlanded modules — the generation entry point is not called by anything until the trigger
service lands). No data migration, no settings migration beyond the prompts change's profile
values. Rollback is a revert of this change plus its dependency changes; nothing persists.

## Open Questions

- The exact entry-point name/shape the schema change exposes for "ladder validation with error
  messages" — this change's integration test pins whatever ships (R1).
- Whether the trigger service passes the secret-token set explicitly or derives it inside
  `build_options_context` — resolved at the trigger-service design (change 5); the pure builder
  contract (D-5) supports both.