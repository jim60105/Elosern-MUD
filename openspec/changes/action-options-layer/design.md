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

- `generate_action_options(context, client, *, fingerprint) -> defer.Deferred` resolving to a
  frozen `OptionSet` (`status: "ready"` only) or `None` under every failure mode (disabled
  profile, transport failure, retry exhaustion, internal error), with no partial success.
- `build_options_context(...)` — deterministic, public-only, bounded context serialization with
  the fixed truncation policy (narrative tail → persona digest → NPC count; `affordances`,
  `room_name`, `room_summary` never truncated), named input errors for over-budget
  non-truncatable values, and a `LEAK_BLOCKLIST` consumed by validation only.
- Prompt assembly through the prompt library's two `action_options` keys
  (`render_prompt("action_options.system" | "action_options.user", ...)`) with placeholder-
  allowlist parity asserted by a contract test; the user message carries exactly the seven
  context fields, including the affordance list (canonical ids + params) and stable `npc_index`
  references.
- Validation-retry-degrade semantics per the pipeline design: validation/ladder rejections —
  including the 3–5 generation floor (D-4a) — retry within `1 + max_retries` with the round's
  errors appended; transport failures resolve `None` immediately (no retry loop — the trigger
  service memoizes); exhaustion resolves `None`.
- Idempotent, atomic, boot-tolerant guardrail registration (degrade fallback + raw-shape output
  schema only, skippable pre-prerequisite) wired at server startup.

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

### D-2: Validation lives in a single per-call closure; the layer registers no text gates

The ladder (schema change) already owns every text gate — stages 6–8 (CJK, generic `{...}`
placeholder, ASCII-digit) are implemented inside the schema module with *generic* patterns; the
narrator's placeholder regex is token-specific (`{actor}|{target}|{data[...]}`) and narrator has
no digit gate, so those helpers are **not** reusable (schema change spec, stage 6–8 amendment).
The layer therefore registers **no semantic validators**: the sole per-call validator carried on
the request descriptor's `semantic_validators` is one closure bound to the call's `fingerprint`,
`affordances`, `npc_bindings`, and `leak_blocklist`, which runs enrichment + the full ladder and
returns aggregated error messages for the retry loop.

*Alternative rejected:* layer-registered semantic validators duplicating the ladder's gates. They
would run before the ladder closure on the raw model shape, double-enforce gates the ladder owns,
and diverge from the schema module's gate definitions. *Alternative rejected:* validating only
after `guarded_call` resolves — that would make ladder failures invisible to the retry budget.

### D-3: One total enrichment-and-ladder helper for both paths

A single private `_evaluate_enriched(parsed, *, fingerprint, affordances, npc_bindings,
leak_blocklist) -> (OptionSet | None, list[str])` is used by (a) the per-call validator to
produce retry messages and (b) the final resolution step, which parses the accepted text again
and demands the strict `OptionSet`. The helper is a **total function** (review round three): every
parsing, enrichment, binding, and ladder exception is converted into a named error message
(`"stage N: <code>"` for ladder rejections — the schema ladder raises one named error per stage)
and returned in the error list; it never raises into `guarded_call`, which would errback the
Deferred instead of retrying. Because both paths run the identical helper on the same input, an
accepted text cannot fail the final strict path; if it ever does (a defensive internal-error
guard, not a client-side drift scenario — `guarded_call` pins the accepted text), the layer logs
a bounded diagnostic and resolves `None`.

### D-4: Caller-side enrichment contract with the schema change

The ladder's stage 0 requires the caller to inject `fingerprint` and `status: "ready"`; the
schema's LLM contract requires freeform `{npc_index}` resolution before validation. The schema
change's enrichment helper injects the caller-scoped fields and the freeform `action_code`
default (its spec: "the `{npc_index}` → `{npc_id}` binding resolution is owned by
`action-options-layer`"); this change owns the **binding resolution**: it resolves each freeform
card's `npc_index` against the prompt's bound NPC list (the positional order fixed by the context
builder) into `params: {"npc_id": int}`; an out-of-range index or a target bound twice rejects
the card with a binding error that enters the retry loop. **Data flow (review round three):**
`fingerprint` is an explicit call argument of `generate_action_options(context, client, *,
fingerprint)` (the trigger service computes it); `leak_blocklist` is composed by
`build_options_context` and travels on the context into `_evaluate_enriched`; both reach the
ladder entry point `validate_optionset(raw, *, fingerprint, affordances, leak_blocklist)`.
Neither value is ever rendered into the prompt, and the per-call closure captures only that
call's immutable copies.

### D-4a: The generation rule — a 3–5 floor the ladder does not enforce

The schema ladder's stage 4 accepts 0–5 cards and its spec explicitly delegates the 3–5 minimum
to this change ("the 3–5 minimum is a *generation* rule owned by `action-options-layer`"). The
layer therefore enforces the floor **after** ladder success: a set with fewer than `MIN_CARDS`
(3) is a generation failure entering the same retry loop with a named message; exhaustion
resolves `None` (rule cards). The 6-card rejection stays the ladder's (stage 4).

### D-5: Pure context-builder input contract

`build_options_context(...)` is a pure function over plain data: the deterministic call site
(the trigger service, change 5) hands in room name/summary, bounded narrative tail, present NPC
entries (identity, display name, dialogue key, persona digest, public tier), monster entries,
the public objective line, the canonical affordance tuple, and the caller-collected secret
tokens (numeric literals + hidden trait keys of its view). The builder composes the
`ActionOptionsContext` frozen struct (carrying the `LEAK_BLOCKLIST`) and the stable positional
NPC order; the blocklist is an output for validation consumption and is never serialized into
the prompt. The builder cannot read traits itself — it must stay Evennia-import-free. **Over-budget
non-truncatable inputs (review round three):** because `affordances`, `room_name`, and
`room_summary` are both hard-capped and never truncated, a call-site value exceeding a cap is a
named input error raised by the builder (`ActionOptionsInputError`), which the entry point
catches, logs, and resolves `None` — the contract never silently emits out-of-bounds data.

### D-6: Prompt shape — both keys render through the prompt library

- System message: `render_prompt("action_options.system", ...)` — the prompts change registers
  this key with an **empty** allowlist (static role/hard-rule direction, no context tokens).
- User message: `render_prompt("action_options.user", ...)` — the prompts change registers its
  allowlist as exactly the seven `ActionOptionsContext` fields (`room_name`, `room_summary`,
  `npc_entries`, `monster_entries`, `objective`, `narrative_tail`, `affordances`). The builder
  pre-serializes the structured fields (NPC entries, monster entries, affordance list) into
  deterministic JSON strings and supplies the substitution dict; the hard rules live in the YAML
  text, never in Python. No prompt text as a Python constant, and the parity contract test covers
  both keys.

### D-7: Registration wiring

`register_action_options()` mirrors `register_npc_dialogue()`: idempotent (second call no-op),
atomic (partial failure uninstalls only this module's own hooks), installing the degrade
fallback (`None`) and registering the `action_options` output schema in
`world/ai/schemas/registry.py` (no semantic validators — D-2; the registered schema validates the
**raw model wire shape**: `known_action` cards with optional `params`, `freeform` cards carrying
`npc_index` — never the caller-injected `fingerprint`/`status`/`action_code`/`params`, per the
schema change's exact-field parsing contract). `server/conf/at_server_startstop.py` gains
`_register_action_options_layer()` following the boot-tolerant pattern of the other layers,
with one addition (review round three): it also catches `UnknownLayerError` and logs
"skipped — action_options slot pending" — the `LAYER_NAMES` slot arrives with the prompts change,
and a branch that lands this change's wiring first must never abort startup; the same warning-
and-skip applies to `GuardrailRegistrationError`/`DuplicateSchemaError` as with the other
layers. The prompts and schema changes are landing prerequisites for this change's regression
suite.

## Risks / Trade-offs

- **[R1] The schema ladder raises one named error per stage, not message lists.** → The
  per-call closure maps each caught rejection to `"stage N: <code>"` (D-3); the retry/degrade
  behavior in this change's specs is unaffected.
- **[R2] Wording overlap with the schema change's "enrichment".** → Scope ruling (D-4): the
  ladder entry point, enrichment helper, and stage-0 validation are schema-owned; the caller-side
  `npc_index` → `npc_id` binding resolution is layer-owned. The schema spec states the same
  boundary, and the integration test exercises both halves together.
- **[R3] The model may repeat the same binding/ladder/count failure across retries.** → The
  bounded budget terminates; exhaustion resolves `None`; validation exhaustion degrades to rule
  cards (correct product behavior — never show unvalidated output).
- **[R4] Accepted text re-validated after `guarded_call` must not drift.** → Single total
  `_evaluate_enriched` (D-3); the strict path is the same helper, so drift is structurally
  impossible; the residual branch is a defensive bounded-log + `None`.
- **[R5] Startup ordering: the `LAYER_NAMES` slot lands with the prompts change.** → The startup
  wrapper catches `UnknownLayerError` with warning-and-skip (D-7); the branch-safe behavior is
  itself wired before any deployment order is assumed.
- **[R6] Truncation hides content from the model.** → Fixed, tested order guarantees the most
  decision-relevant inputs (affordances, room identity) survive any budget pressure; over-budget
  non-truncatable inputs fail named and degrade instead of silently overflowing (D-5).
- **[R7] A raw wire shape that accidentally requires caller-injected fields would make every
  accepted response unenrichable.** → Pinned cross-change contract (D-7): the registered output
  schema validates the model's raw shape only (`params` optional on known-action cards, `npc_index`
  on freeform); the integration test proves an accepted raw payload enriches and validates.

## Review Fixes

### D-9 (rubber-duck review): profile-gate ordering and named-input hardening

- **Disabled profile resolves `None` even when the layer is unregistered.** The entry point
  originally checked registration before the profile gate, so the allowed startup-skip path
  (prerequisites missing, registration skipped) turned a disabled-profile call into a failed
  Deferred instead of `None`. The gate now runs before `_require_registered()`: a disabled
  profile resolves `None` with no transport work and no registration requirement; an *enabled*
  profile on an unregistered layer still fails loudly (regression test added).
- **Context construction is uniformly named-error safe.** The entry dataclasses now validate
  their own field types (a `persona_digest=None` can no longer reach a `len()` `TypeError`),
  the affordance shape check reads through `getattr` so a garbage entry raises
  `ActionOptionsInputError` instead of `AttributeError`, and the builder materializes
  sequences before slicing so any iterable input is handled (tests added).
- **Rejected: making the guardrail import lazy at module time.** The review flagged that
  `from world.ai import guardrail` transitively imports `evennia.logger` at module import
  time. This matches the repository-wide pattern the design doc itself cites — `narrator.py`
  imports guardrail at module level (as do npc_dialogue/character_creation/scene_flavor) —
  the transport-contract test (the enforcement for the proposal-only requirement) is green,
  and no code path imports this module before `evennia._init()` (settings.py imports only
  `world.ai.profiles`; the startup wrapper imports the layer inside `at_server_start`). The
  module's own direct Evennia use stays lazy (`_log_bounded_diagnostic`).

### D-8: The shipped user-prompt examples taught a `kind` field the raw contract forbids

The schema change's JSON contract (§5) — pinned by the exact-field parser and its main spec —
requires raw cards **without** `kind`: known_action cards carry `{action_code, label, params?,
hint?}`, freeform cards carry `{npc_index, label, hint?}`; `kind` is derived at enrichment.
The prompts change's `prompts/action_options.yaml` user-key example formats showed
`{"kind": "known_action", ...}` / `{"kind": "freeform", ...}`, which a faithful model would emit
and the parser would reject every time (`schema_violation` → retry → exhaust → degrade — the
suggestion surface would never come online). This change fixes the two example formats in
`prompts/action_options.yaml` to the raw wire shape (no `kind`); no placeholder, key, or allowlist
changes. The main `ai-action-options-prompts` requirement ("exactly the documented JSON schema
output") is thereby honored, and the layer's parse-then-bind-then-enrich tests exercise the fixed
contract end to end.

## Migration Plan

Pure additive change: one new module, one new startup registration call, one new test suite.
The `action_options` profile slot and prompt file are prerequisites from the prompts change; the
ladder entry point and output schema from the schema change; until they land, the layer's own
tests register/consume thin local stand-ins in test fixtures only (no production code depends on
unlanded modules — the generation entry point is not called by anything until the trigger
service lands). No data migration, no settings migration beyond the prompts change's profile
values. Rollback is a revert of this change plus its dependency changes; nothing persists.

## Open Questions

- Whether the trigger service passes the secret-token set explicitly or derives it inside
  `build_options_context` — resolved at the trigger-service design (change 5); the pure builder
  contract (D-5) supports both.
- Whether the trigger service binds `fingerprint` per situation or per transition-in — the
  service memoizes transport failures, so it chooses the scope; the layer treats it as an opaque
  value it carries through (D-3/D-4).