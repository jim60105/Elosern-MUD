## Context

The AI action-options design set defines a proactive suggestions surface: an LLM curates 3–5
action cards per situation, gated by a strict validation ladder (`2026-08-15-ai-action-options-schema-design.md`).
The vocabulary-lock invariant requires AI output to be byte-for-byte executable: cards must match a
currently-valid affordance, params must come from the canonical builders, and nothing hidden may
leak through card text. This change builds the pure schema layer — `world/ai/action_options.py` —
that the generative layer (`action-options-layer`), the trigger service, and the v3 client mirror
all consume. The `Affordance` typing and fixtures come from change 1
(`action-options-affordance-contract`); this change is implemented after it.

## Goals / Non-Goals

**Goals:**
- One frozen vocabulary (`OptionSet`/`SuggestionCard`) with a single wire shape and exact bounds,
  safe to hand across the `world/ai` boundary.
- A deterministic 12-stage validation ladder with one named rejection code per stage; any
  rejection maps to degrade at the caller.
- The stage-9 canonical match (vocabulary lock) and the freeform binding-only exception.
- Leak gates (true traits, affinity numbers, disguised values, hidden tokens, digits,
  placeholders) on `label`/`hint` only.
- Enrichment helpers for caller-side field injection and the freeform `action_code` constant.
- A pure-test suite (no DB, no network) over every stage and bound.

**Non-Goals:**
- The `{npc_index}` → `{npc_id}` binding resolution and prompt construction (`action-options-layer`).
- The context builder and `LEAK_BLOCKLIST` composition (pipeline design doc §2) — this change
  only applies a caller-supplied blocklist.
- The `ACTION_CODE_ALLOWLIST` vocabulary (change 1 owns it); this module consumes affordances.
- Client-side mirror/parity (change `context-actions-suggestions`).

## Decisions

- **One module, one wire shape.** All vocabulary, bounds, ladder, enrichment, and leak helpers live
  in `world/ai/action_options.py`, mirroring the `world/ai/narrator.py` import discipline: no
  Evennia imports at module time, no module-level logger binding, pure functions plus frozen
  structs. Cards carry `action_code` explicitly so dispatchers never infer it.
- **Ladder stage order is frozen** (stages 0–11 per the schema design doc §3); the first failing
  stage wins and maps to degrade. Stage numbering is public contract — the pipeline reuses it for
  retry messages.
- **Stage-9 canonical replacement, not equality.** Model-typed `params` for `known_action` cards
  are curation hints — the JSON contract permits omitting them entirely, and the ladder never
  checks them for equality. Stage 9 resolves `action_code` to the unique current affordance and
  unconditionally replaces params with its canonical payload; the vocabulary-lock guarantee holds
  on the validated *result* (`(action_code, params) == (action_id, params)` of one affordance).
  This resolves the round-three contradiction between "exact match" and "replacement" (rubber-duck
  round 4).
- **Card label gates are local, not narrator imports.** Only the CJK check reuses
  `world/ai/narrator.py::_validate_has_cjk`. The generic `{...}` placeholder gate and the digit
  gate are implemented in this module because narrator's `_TEMPLATE_PLACEHOLDER_RE` is
  token-specific (`{actor}|{target}|{data[...]}`) and narrator has no digit gate — amends the
  schema design doc's stage 6–8 reuse line.
- **Leak blocklist is an explicit parameter.** `validate_optionset` takes
  `leak_blocklist: frozenset[str] = frozenset()`; the context builder (pipeline change) supplies
  it. An empty default keeps the function pure and total — no implicit reads of game state.
- **Freeform binding-only params are the single exception** to the validator-normalized rule
  (round-three review): `validate_talk_freeform_payload` requires `speech`, so no validator can
  produce `{"npc_id"}`. The ladder therefore validates the binding shape only, and the full
  dispatcher validator runs on the client-composed payload.
- **Leak gates read a caller-supplied `LEAK_BLOCKLIST`** (numeric literals + hidden trait keys).
  The gates apply to `label`/`hint`; `params` are exempt by construction — canonical copies after
  stage 9.
- **Stage 6–8 reuse the narrator's exact validators** (`_validate_has_cjk`,
  `_validate_no_template_placeholder`, digit gate) so label rules cannot drift between layers.
- **Enrichment stays thin.** It injects `fingerprint`, `status: "ready"`, and the freeform
  `action_code` default. The `npc_index` binding belongs to the layer change because it needs the
  prompt's bound-NPC list; fixtures here feed resolved `{"npc_id": int}`.
- **Parsing pattern.** Exact-field parsing mirrors `web/webclient/presentation/protocol.py`:
  unknown keys reject; no silent coercion. `response_format` schema_id is `action_options`
  (registered in `world/ai/schemas/registry.py` — registration itself lands with the layer
  change; this change defines the shape and the parser contract tests for it).

## Risks / Trade-offs

- **Affordance freshness:** stage 9 is only as correct as the `affordances` argument the caller
  passes; a stale caller could pass a stale list. Mitigated by design: the fingerprint includes an
  eligibility digest (trigger-service change), and the deterministic builders re-derive the list
  per render.
- **Freeform exception surface:** the binding-only params break the "validator-produced" rule for
  exactly one action. Documented as the single exception in the module docstring and asserted by a
  dedicated test, so a future second exception must be a deliberate decision.
- **Label digit gate:** hints/labels cannot contain ASCII digits at all (e.g. "3 個敵人" is
  rejected; numerals must be rendered as Chinese characters). This is a deliberate narrator
  alignment, carried as an open question for `hint` (schema design doc §7).