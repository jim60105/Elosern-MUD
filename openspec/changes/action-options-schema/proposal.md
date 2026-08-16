## Why

The AI suggestion surface (design set `2026-08-15-ai-action-options-*`) needs one frozen, well-bounded
card vocabulary that model output must satisfy deterministically. Without an immutable schema and a
fixed validation ladder, the LLM can fabricate inexecutable actions, leak hidden numbers through
labels, or produce payloads the dispatcher silently rejects — breaking the vocabulary-lock promise
that a suggestion card is always a currently-executable affordance.

## What Changes

- New `world/ai/action_options.py` module holding the frozen vocabulary: `OptionSet` and
  `SuggestionCard` (one wire shape: `kind`, `action_code`, `label`, `params`, optional `hint`),
  with `status: "ready"` as the only cached status.
- Exact bounds constants (card count, label/hint lengths, params keys and value shapes) as the
  single source mirrored later by `protocol.js`.
- A 12-stage validation ladder (`validate_optionset`) with fixed order and one named rejection code
  per stage, including the stage-9 canonical match against the affordance vocabulary and the
  freeform binding check.
- Caller-side enrichment helpers (inject `fingerprint`/`status`, default freeform `action_code` to
  `explore.talk_freeform`) — the `{npc_index}` → `{npc_id}` binding itself stays in
  `action-options-layer`.
- Leak gates on `label`/`hint` (true traits, affinity numbers, disguised values, hidden secrets,
  digits, template placeholders); `params` are exempt by construction.
- The LLM JSON output contract (inline `response_format` shape, exact-field parsing, unknown-key
  rejection) plus a full pure-test suite.

## Capabilities

### New Capabilities
- `ai-action-options-schema`: the immutable suggestion-card vocabulary, bounds, validation ladder,
  enrichment seam, leak gates, and JSON contract for the AI action-options surface.

## Impact

- **New module:** `world/ai/action_options.py` (pure, no Evennia imports at module time — mirrors
  `world/ai/narrator.py` import discipline).
- **Tests:** `world/ai/tests/test_action_options_schema.py` (pure `unittest.TestCase`, no DB).
- **Dependencies:** change 1 `action-options-affordance-contract` supplies the `Affordance` typing
  and fixtures; until it lands, tasks use fixtures matching the deterministic-actions design doc
  §1 shape (`action_id`, `label`, `params`, `freeform`, `navigation`).
- **Consumers (later changes):** `action-options-layer` (generation), `action-options-trigger-service`
  (cache/publish), `context-actions-suggestions` (client mirror parity).
- **No backward compatibility:** unreleased project, zero users — no migrations or compatibility
  layers.