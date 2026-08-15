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
- Add the corresponding `test_rule_high_exposure_defense_penalty` unit test to
  `world/rules/tests/test_combat_modifiers.py`, satisfying the existing mechanical
  rule-id-to-test correspondence check, **plus a regression test exercising the row through real
  damage resolution** (`world/rules/combat.py::_adjusted_defense`), not only through
  `evaluate_combat_modifiers()` directly — see design.md D-2 for why this is required, not optional.

No other file changes. This is a pure data addition to an existing, already-generic table: the same
`evaluate_condition()` engine that already reads `arousal` and `climax_phase` thresholds reads
`exposure` identically, with no new condition primitive and no branching added to
`combat_modifiers.py`. The adjustment is a **flat** integer, matching `defense`'s only supported
shape (see design.md D-2 — an earlier draft of this proposal used a percentage, which is wrong: the
`defense` bundle key has no percentage-aware consumer anywhere in this codebase).

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
- `world/rules/tests/test_combat_modifiers.py` — one new test function.
- No production code changes: `world/rules/combat_modifiers.py` is untouched, since the row's
  condition shape (`field`/`gte`) and adjustment shape (`defense`) are both already handled by the
  existing evaluator and the existing damage-resolution consumer of the `defense` bundle key.
- Depends on nothing landed by this document set; it reads `entity.sexual.exposure`, which already
  exists on `SexualState` today. Independent of `pleasure-gauge` (B1), `sexual-counters` (B2), and
  every other proposal in the [sexual act system set](../../../docs/superpowers/specs/2026-08-15-sexual-act-system-overview-design.md).
