## 1. Vocabulary module

- [x] 1.1 Define frozen `OptionSet` and `SuggestionCard` dataclasses in `world/ai/action_options.py`
  with the exact field set of the schema design doc §1 (`kind`, `action_code`, `label`, `params`,
  optional `hint`); `OptionSet.status` fixed to `"ready"`; `context_kind` closed to
  `"exploration"` in v1.
- [x] 1.2 Implement `_reject_mutable_containers` at construction (mirror
  `world/ai/scenario_director.QuestBlueprint`) and test that nested list/dict params are rejected.
- [x] 1.3 Define bounds constants `MIN_CARDS`/`MAX_CARDS` (3/5), `MAX_LABEL_LENGTH` (24),
  `MAX_HINT_LENGTH` (60), `MAX_PARAMS` (4), the trigger-service bounds
  `MAX_OPTIONSET_CACHE_ENTRIES` (16) and `NEGATIVE_MEMO_TTL` (30), and the params value-shape
  rules (int ≤ `MAX_SAFE_INTEGER`, str ≤ 32 chars, or the exact boolean room-survey marker
  `{"room": true}`); module docstring names these as the single source mirrored by `protocol.js`
  later.
- [x] 1.4 Tests: construction rejection cases, `status`/`kind` closed enums, params shapes at
  boundary and one-past-boundary.

## 2. Validation ladder

- [x] 2.1 Implement `validate_optionset(raw, *, fingerprint, affordances, leak_blocklist=frozenset())`
  with the fixed 12-stage ladder (schema design doc §3), raising one named error per stage in the
  documented order.
- [x] 2.2 Implement stages 6–8: reuse the narrator's `_validate_has_cjk` for the CJK check; the
  generic `{...}` placeholder gate (`re.compile(r"\{[^{}]+\}")`) and the ASCII-digit gate are
  implemented locally in this module (narrator's placeholder regex is token-specific and it has no
  digit gate).
- [x] 2.3 Implement the fingerprint stage (opaque 8–64 chars, no whitespace) and the card-keys
  stage (exact keys `kind`, `action_code`, `label`, `params`, optional `hint`).
- [x] 2.4 One `unittest` per rejection stage with minimal hostile fixtures covering all twelve
  rejection codes (`schema_violation`, `card_count_out_of_range`, `empty_label`, `label_too_long`,
  `non_cjk_label`, `placeholder_label`, `digit_in_label`, `unknown_action_code`,
  `no_such_affordance`, `unknown_target`, `hint_too_long`, `leak_detected`); assert
  first-failure-wins ordering.

## 3. Canonical match and enrichment

- [x] 3.1 Implement stage-9 canonical replacement: resolve `action_code` to the unique current
  affordance entry and unconditionally replace params with its canonical payload (model params are
  curation hints, never equality-checked); the freeform branch checks
  `action_code == "explore.talk_freeform"` and `params == {"npc_id": int}` bound to a freeform
  affordance's target.
- [x] 3.2 Implement the enrichment helper: inject `fingerprint`, `status: "ready"`, and the
  freeform `action_code` default (`"explore.talk_freeform"`); document that binding-only params are
  the single exception to the canonical-payload rule.
- [x] 3.3 Tests: valid-now card passes with canonical replacement (including one omitting
  `params`); not-current affordance → `no_such_affordance`; unknown code →
  `unknown_action_code`; unknown target → `unknown_target`; freeform auto-`action_code`; validated
  card params byte-equal the fixture affordance's.

## 4. Leak gates

- [x] 4.1 Implement the leak predicate on `label`/`hint` against the `leak_blocklist` keyword
  parameter (true-trait numbers, affinity numbers, disguised values, fabricated tokens) plus the
  hint length and placeholder gates at stage 10.
- [x] 4.2 Tests: each leak category rejected with `leak_detected`; digit/placeholder gates on both
  fields; params never inspected (opaque id equal to a blocklist token passes).

## 5. JSON contract

- [x] 5.1 Implement exact-field parsing for the `action_options` `response_format` JSON shape
  (known-action vs freeform forms per schema design doc §5), rejecting unknown keys and wrong
  shapes with named rejections; reuse the `web/webclient/presentation/protocol.py` parser pattern
  (no Evennia import at module time).
- [x] 5.2 Tests: parsed sample payloads; unknown-key rejection; absent caller-side fields handled
  at enrichment; freeform `npc_index` fixture path documented as layer-owned.

## 6. Verification

- [x] 6.1 Run the owned package tests:
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py
  world.ai.tests.test_action_options_schema`
  plus `world.ai.tests.test_narrator` (reused validators untouched).
- [x] 6.2 `uv run --locked python -m tools.spec_traceability check` stays green; `git diff --check`
  clean.
- [x] 6.3 Sync the delta spec into `openspec/specs/ai-action-options-schema/spec.md`, annotate the
  owning tests with `covers_requirement` from `tools.spec_traceability`, and keep the check green
  (per the slice workflow, mirroring change 1 task 7.1).