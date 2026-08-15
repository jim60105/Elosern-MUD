## Why

`exposure` (露出) is one of five `SexualState` ordered-level fields, and its offensive payoff — a
distraction debuff on enemies who can see an exposed actor — is delivered entirely by act effects in
the upcoming sexual act catalog. Nothing currently prices the *defensive* cost of exposing oneself in
combat. `combat_modifiers.yaml` already couples two other sexual-state fields (`arousal`,
`climax_phase`) to combat in the same table as poison and paralysis, but has no row reading
`exposure`. Without one, the forthcoming 羞恥線 (shame line) of the sexual act catalog has no combat
cost to balance its combat benefit, and a raised `exposure` is otherwise mechanically inert outside
its own shame feedback loop.

## What Changes

- Add one new row to `world/rules/rulebook/combat_modifiers.yaml`:
  `high_exposure_defense_penalty` — `{field: exposure, gte: 高}` → `{defense: -15}`.
- Extend the three condition-context builders that feed `matched_combat_modifiers()` to expose the
  `exposure` field. This is required, not optional: all three currently expose only `arousal` and
  `climax_phase`, and `evaluate_condition()` treats a `field` condition as unsatisfied when the
  field is absent from the context — a `{field: exposure, gte: 高}` row cannot match without it.
  The change is one tuple entry and one context assignment per builder plus the `EXPOSURE_LEVELS`
  import: `_build_context` in `world/rules/combat_modifiers.py` (resolution),
  `build_no_create_condition_context` in `world/rules/combat_modifiers.py` (preview/revalidation),
  and `_sexual_condition_context` in `world/rules/status_query.py` (player-visible status
  conditions; restoring the surface here is required by the shipped
  `webclient-status-presentation` matched-modifier contract and by D-5's now-reachable label — see
  design.md D-4). No change to `evaluate_condition()`, `_merge_adjustments()`, or the
  adjustment-bundle vocabulary.
- Add one Traditional Chinese display entry to `world/rules/rulebook/status_display.yaml`
  (`high_exposure_defense_penalty`, warning severity). This is required by an import-time gate:
  `world/rules/status_display.py` fails closed unless every `combat_modifiers.yaml` rule ID and
  every buff key has exactly one display entry (see design.md D-5).
- Add the corresponding `test_rule_high_exposure_defense_penalty` unit test to
  `world/rules/tests/test_combat_modifiers.py`, satisfying the existing mechanical
  rule-id-to-test correspondence check, **plus a regression test exercising the row through real
  damage resolution** (`world/rules/combat.py::_adjusted_defense`), not only through
  `evaluate_combat_modifiers()` directly — see design.md D-2 for why this is required, not optional.

Everything else is a pure data addition to an existing, already-generic table: the same
`evaluate_condition()` engine that already reads `arousal` and `climax_phase` thresholds reads
`exposure` identically once it is present in the context, with no new condition primitive. The
adjustment is a **flat** integer, matching `defense`'s only supported shape (see design.md D-2 — an
earlier draft of this proposal used a percentage, which is wrong: the `defense` bundle key has no
percentage-aware consumer anywhere in this codebase).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `combat-modifier-table`: adds one new, narrowly-scoped requirement pinning the
  `high_exposure_defense_penalty` row's existence and exact adjustment. No existing requirement's
  text changes — every shipped requirement in this capability already covers a new row in general
  terms (see design.md D-1) — this is an `ADDED Requirement`, not a `MODIFIED` one.

## Impact

- `world/rules/rulebook/combat_modifiers.yaml` — one new row.
- `world/rules/combat_modifiers.py` — two context-builder entries and one import, exposing
  `exposure` to the shared condition engine (required for the row to match at all; see "What
  Changes").
- `world/rules/status_query.py` — one context-builder entry and one import, exposing `exposure` to
  the status read model's matched-condition surface (see design.md D-4).
- `world/rules/rulebook/status_display.yaml` — one Traditional Chinese display entry (required by
  `status_display.py`'s import-time coverage gate; see design.md D-5).
- `world/rules/tests/test_combat_modifiers.py` and `world/rules/tests/test_status_query.py` — new
  test functions.
- Depends on nothing landed by this document set; it reads `entity.sexual.exposure`, which already
  exists on `SexualState` today. Independent of `pleasure-gauge` (B1), `sexual-counters` (B2), and
  every other proposal in the [sexual act system set](../../../docs/superpowers/specs/2026-08-15-sexual-act-system-overview-design.md).
