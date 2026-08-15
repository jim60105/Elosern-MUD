## 1. Vocabulary module

- [ ] 1.1 Define frozen `OptionSet` and `SuggestionCard` dataclasses in `world/ai/action_options.py`
  with the exact field set of the schema design doc §1 (`kind`, `action_code`, `label`, `params`,
  optional `hint`); `OptionSet.status` fixed to `"ready"`; `context_kind` closed to
  `"exploration"` in v1.
- [ ] 1.2 Implement `_reject_mutable_containers` at construction (mirror
  `world/ai/scenario_director.QuestBlueprint`) and test that nested list/dict params are rejected.
- [ ] 1.3 Define bounds constants `MIN_CARDS`/`MAX_CARDS` (3/5), `MAX_LABEL_LENGTH` (24),
  `MAX_HINT_LENGTH` (60), `MAX_PARAMS` (4), and the params value-shape rules (int ≤
  `MAX_SAFE_INTEGER`, str ≤ 32 chars); module docstring names these as the single source mirrored
  by `protocol.js` later.
- [ ] 1.4 Tests: construction rejection cases, `status`/`kind` closed enums, params shapes at
  boundary and one-past-boundary.

## 2. Validation ladder

- [ ] 2.1 Implement `validate_optionset(raw, *, fingerprint, affordances)` with the fixed 12-stage
  ladder (schema design doc §3), raising one named error per stage in the documented order.
- [ ] 2.2 Implement stages 6–8: reuse the narrator's `_validate_has_cjk` for the CJK check; the
  generic `{...}` placeholder gate (`re.compile(r"\{[^{}]+\}")`) and the ASCII-digit gate are
  implemented locally in this module (narrator's placeholder regex is token-specific and it has no
  digit gate).
- [ ] 2.3 Implement the fingerprint stage (opaque 8–64 chars, no whitespace) and the card-keys
  stage (exact keys `kind`, `action_code`, `label`, `params`, optional `hint`).
- [ ] 2.4 One `unittest` per rejection stage with minimal hostile fixtures covering all eleven
  rejection codes; assert first-failure-wins ordering.

## 3. Canonical match and enrichment

- [ ] 3.1 Implement stage-9 canonical replacement: resolve `action_code` to the unique current
  affordance entry and unconditionally replace params with its canonical payload (model params are
  curation hints, never equality-checked); the freeform branch checks
  `action_code == "explore.talk_freeform"` and `params == {"npc_id": int}` bound to a freeform
  affordance's target.
- [ ] 3.2 Implement the enrichment helper: inject `fingerprint`, `status: "ready"`, and the
  freeform `action_code` default (`"explore.talk_freeform"`); document that binding-only params are
  the single exception to the canonical-payload rule.
- [ ] 3.3 Tests: valid-now card passes with canonical replacement (including one omitting
  `params`); not-current affordance → `no_such_affordance`; unknown code →
  `unknown_action_code`; unknown target → `unknown_target`; freeform auto-`action_code`; validated
  card params byte-equal the fixture affordance's.

## 4. Leak gates

- [ ] 4.1 Implement the leak predicate on `label`/`hint` against the `leak_blocklist` keyword
  parameter (true-trait numbers, affinity numbers, disguised values, fabricated tokens) plus the
  hint length and placeholder gates at stage 10.
- [ ] 4.2 Tests: each leak category rejected with `leak_detected`; digit/placeholder gates on both
  fields; params never inspected (opaque id equal to a blocklist token passes).

## 5. JSON contract

- [ ] 5.1 Implement exact-field parsing for the `action_options` `response_format` JSON shape
  (known-action vs freeform forms per schema design doc §5), rejecting unknown keys and wrong
  shapes with named rejections; reuse the `web/webclient/presentation/protocol.py` parser pattern
  (no Evennia import at module time).
- [ ] 5.2 Tests: parsed sample payloads; unknown-key rejection; absent caller-side fields handled
  at enrichment; freeform `npc_index` fixture path documented as layer-owned.

## 6. Verification

- [ ] 6.1 Run the owned package tests:
  `uv run --locked evennia test --settings settings.py world.ai.tests.test_action_options_schema`
  plus `world.ai.tests.test_narrator` (reused validators untouched).
- [ ] 6.2 `uv run --locked python -m tools.spec_traceability check` stays green; `git diff --check`
  clean.