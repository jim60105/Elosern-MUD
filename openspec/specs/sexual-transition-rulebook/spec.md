# sexual-transition-rulebook Specification

## Purpose
TBD - created by archiving change sexual-transition-rules. Update Purpose after archive.
## Requirements
### Requirement: sexual.yaml loads through change 6's shared rule loader with no second parser
`world/rules/rulebook/sexual.yaml` SHALL be a YAML list of `{id, when, then}` entries loadable by
change 6's `world.rules.rulebook.schema.load_rules()`, with no rule-loading or condition-matching
logic duplicated anywhere in `world/rules/sexual_transitions.py`. Every entry SHALL carry a unique,
non-empty `id`.

#### Scenario: sexual.yaml loads successfully via load_rules()
- **WHEN** `load_rules(Path("world/rules/rulebook/sexual.yaml"))` is called
- **THEN** it returns one `Rule` per entry, each exposing `id`, `when`, and `then`, with no error

#### Scenario: sexual_transitions.py contains no second condition matcher
- **WHEN** `world/rules/sexual_transitions.py` is inspected
- **THEN** it imports `evaluate_condition` from `world.rules.rulebook.schema` and contains no
  function that independently re-implements matching against `event`, `field`, `field_changed`, or
  `buff_active`

### Requirement: apply_event() is the single entry point, evaluating every rule to a fixed point
`world/rules/sexual_transitions.py` SHALL expose `apply_event(entity, event, **event_context)`,
running every loaded rule against an immutable pass-start snapshot of `entity.sexual` plus the
given event name and non-reserved payload. Payload SHALL NOT override authoritative state, `event`,
or `_changed`. It SHALL re-evaluate rules across successive passes so that one rule's
effect can satisfy a second rule's condition within the same call, continuing until a pass produces
no field change, and SHALL evaluate any `event`-keyed condition only on the first pass. Exhausting
a positive `max_passes` SHALL raise `RuleConvergenceError`; a non-positive limit SHALL be rejected.

#### Scenario: A chained effect fires within one apply_event() call
- **WHEN** `apply_event(entity, "extreme_stimulus_applied")` is called on an entity whose `arousal`
  is below `極限`
- **THEN** `arousal_extreme_stimulus_to_max` raises `arousal` to `極限` and, within the same call,
  `climax_gate` fires and `entity.sexual.climax_phase.level` becomes `"接近"`, with no second call to
  `apply_event()` required

#### Scenario: An event-conditioned rule fires exactly once per call, not once per pass
- **WHEN** `apply_event(entity, "stimulus_applied")` is called and triggers a multi-pass cascade
- **THEN** `arousal_up_on_stimulus` (the only rule conditioned on the `stimulus_applied` event
  itself) applies its delta exactly once, regardless of how many further passes the cascade takes

#### Scenario: A field-changed-conditioned rule fires exactly once per underlying change
- **WHEN** `apply_event(entity, "stimulus_applied")` raises `arousal` by one level, triggering
  `wetness_follows_arousal`
- **THEN** `wetness` receives its `+1` delta exactly once, not once per remaining fixed-point pass
  while `arousal` remains at its new level without changing further

#### Scenario: The loop terminates when no field changes
- **WHEN** `apply_event()` is called and a pass produces zero field changes
- **THEN** the loop stops and `apply_event()` returns without requiring a fixed iteration count to be
  reached

#### Scenario: Pass evaluation is independent of YAML order
- **WHEN** a stimulus raises `arousal` to `極限` from a pass-start phase of `未達`
- **THEN** `climax_gate` observes the raised arousal on the next pass and moves only to `接近`;
  the original stimulus event is no longer present, so the phase does not also advance to `進行中`

#### Scenario: Event payload cannot forge authoritative state
- **WHEN** event context supplies `arousal`, `_changed`, or another reserved mechanical key
- **THEN** `apply_event()` raises before applying any rule

#### Scenario: A rule cycle fails loudly
- **WHEN** synthetic rules continue producing changes through `max_passes`
- **THEN** `apply_event()` raises `RuleConvergenceError` rather than returning partial settlement

### Requirement: Ordered-level field rules write through the field's own live trait object, never through a second write path
Every rule targeting `arousal`, `wetness`, `shame`, or `exposure` SHALL apply its `delta` or `set`
effect by mutating the `OrderedLevelTrait` instance `entity.sexual.<field>` returns, never by
constructing a new trait or writing anywhere else. A `delta` of the form `"+N..+M"` SHALL resolve to
a random integer in `[N, M]` at apply time, using an injectable RNG so tests are deterministic. A
`set` naming a string absent from the field's own vocabulary SHALL raise, not silently no-op.

#### Scenario: A fixed delta applies to the live trait
- **WHEN** `apply_event(entity, "sustained_stimulus_applied")` fires `arousal_up_on_sustained_
  stimulus`
- **THEN** `entity.sexual.arousal`'s ordinal increases by exactly `1`

#### Scenario: A random-range delta resolves deterministically under an injected RNG
- **WHEN** `apply_event(entity, "stimulus_applied", rng=<fixed-value stub returning 2>)` fires
  `arousal_up_on_stimulus` (`delta: "+1..+2"`)
- **THEN** `entity.sexual.arousal`'s ordinal increases by exactly `2`, matching the stub's fixed
  return value

#### Scenario: A set effect resolves an absolute vocabulary level
- **WHEN** `apply_event(entity, "extreme_stimulus_applied")` fires `arousal_extreme_stimulus_to_max`
- **THEN** `entity.sexual.arousal.level` becomes `"極限"` regardless of its level beforehand

#### Scenario: A set effect naming an unrecognized level raises
- **WHEN** `sexual.yaml` is loaded with a hypothetical malformed rule whose `then.set` value is not a
  member of the target field's vocabulary
- **THEN** applying that rule raises, naming the invalid level, rather than silently leaving the
  field unchanged

### Requirement: Every climax_phase-targeting rule routes exclusively through change 7's _apply_climax_phase_set()
No rule's effect SHALL write `entity.sexual.climax_phase`'s underlying value directly. Every
`climax_phase`-targeting `then` clause SHALL be applied by calling
`world.rules.sexual_state._apply_climax_phase_set(entity, target_level)`, and SHALL inherit that
function's no-op behavior for any transition outside its valid cycle.

#### Scenario: A valid climax_phase transition applies through the guard
- **WHEN** `apply_event(entity, "stimulus_applied")` is called on an entity whose `climax_phase` is
  currently `"接近"`
- **THEN** `climax_phase_critical_point_to_in_progress` fires and `entity.sexual.climax_phase.level`
  becomes `"進行中"`, applied via `_apply_climax_phase_set`

#### Scenario: A rule whose condition would imply an invalid climax_phase transition no-ops instead of applying
- **WHEN** `climax_gate`'s condition (`arousal` at `極限`) is satisfied on an entity whose
  `climax_phase` is already at `"進行中"` (not a valid source for the `接近` target)
- **THEN** `entity.sexual.climax_phase.level` remains `"進行中"`, unchanged, because
  `_apply_climax_phase_set` no-ops the invalid edge

#### Scenario: Generic climax gating does not use race-specific afterglow re-entry
- **WHEN** `arousal` is `極限`, `climax_phase` is `餘韻`, and any event is applied
- **THEN** `climax_gate` no-ops because its effect requires `from: 未達`

#### Scenario: No source line in sexual_transitions.py writes climax_phase outside the guard
- **WHEN** `world/rules/sexual_transitions.py` is inspected
- **THEN** the only reference to `climax_phase`'s underlying value is the one call site invoking
  `_apply_climax_phase_set`; no line assigns to `.climax_phase.value` or reaches into
  `entity.sexual._traits` directly

### Requirement: sensitivity rules target the body part supplied by the triggering event, not a fixed part named in the rule
`sensitivity`-targeting rules SHALL read the body part to mutate from the event's own context
(`event_context["part"]`), applying their `delta` to `entity.sexual.sensitivity[part]`. A
`sensitivity`-targeting rule whose triggering call supplies no `part` SHALL raise rather than
silently applying to an arbitrary or default part.

#### Scenario: A frequent-stimulation event raises the named part's sensitivity
- **WHEN** `apply_event(entity, "frequent_stimulation", part="乳房")` is called
- **THEN** `entity.sexual.sensitivity["乳房"]`'s ordinal increases by the rule's configured delta,
  and no other part's sensitivity changes

#### Scenario: The same rule applies generically to any part named by the event
- **WHEN** `apply_event(entity, "frequent_stimulation", part="私處")` is called instead
- **THEN** `entity.sexual.sensitivity["私處"]` increases identically, using the same rule and the
  same `id`, proving the rule is part-agnostic rather than duplicated per body part

#### Scenario: A missing part raises rather than silently applying nowhere
- **WHEN** `apply_event(entity, "frequent_stimulation")` is called with no `part` keyword
- **THEN** it raises, rather than silently no-op'ing or defaulting to an arbitrary body part

### Requirement: climax_today increments through SexualState.record_climax(), never through SexualState's private handler
The rule targeting `climax_today` SHALL increment it by calling `entity.sexual.record_climax()` —
change 7's sanctioned mutator for this field — and SHALL NOT read or write
`entity.sexual._traits.climax_today` (or any other private attribute) directly.

#### Scenario: A climax event increments climax_today by exactly one
- **WHEN** `apply_event(entity, "climax_ends")` is called on an entity whose `climax_today` is `2`
- **THEN** `entity.sexual.climax_today` becomes `3`

#### Scenario: The increment path never touches SexualState's private TraitHandler
- **WHEN** `world/rules/sexual_transitions.py` is inspected
- **THEN** no line references `entity.sexual._traits` or any other leading-underscore attribute of
  `SexualState`; the `climax_today` mutation goes exclusively through a call to
  `entity.sexual.record_climax()`

### Requirement: The one rule targeting a vital gauge outside SexualState writes through change 3's entity.traits surface, never through SexualState
`sp_cost_on_climax` SHALL apply its cost by mutating `entity.traits.sp.current` directly — the
public writable property of change 3's `GaugeTrait` (`.value` is its read-only alias) — and SHALL
NOT reach through `entity.sexual` to do so. The delta
SHALL resolve to a negative integer in the source's documented `20`–`30` range, applied as a
subtraction.

#### Scenario: A climax event costs stamina in the documented range
- **WHEN** `apply_event(entity, "climax_ends", rng=<fixed-value stub returning -25>)` is called
- **THEN** `entity.traits.sp.value` decreases by exactly `25`, and no `SexualState` field is touched
  by this specific rule's effect

#### Scenario: The stamina cost never reaches through entity.sexual
- **WHEN** `world/rules/sexual_transitions.py` is inspected
- **THEN** the `vital_gauge`-kind branch of `_apply_then()` references `entity.traits.<field>.current`
  only, with no reference to `entity.sexual` anywhere in that branch

#### Scenario: The stamina cost respects the gauge's own floor
- **WHEN** `apply_event(entity, "climax_ends")` fires on an entity whose `sp` is below the rule's
  delta magnitude
- **THEN** `entity.traits.sp.value` stops at its own configured floor (change 3's `TraitHandler`
  bound), rather than this rule producing a negative stamina value

### Requirement: virgin and experience_types rules are irreversible and append-only end-to-end through apply_event()
Firing `virginity_once`'s triggering event SHALL flip `entity.sexual.virgin` to `False` permanently;
no subsequent call to `apply_event()`, with any event, SHALL be able to set it back to `True`.
Firing any `experience_types`-adding rule's triggering event SHALL add exactly the one documented
type string to `entity.sexual.experience_types`; the resulting set SHALL never lose a previously
present entry, regardless of how many further events fire.

#### Scenario: virgin cannot be reversed by any later event
- **WHEN** `apply_event(entity, "first_vaginal_penetration")` is called, and afterward
  `apply_event(entity, "first_vaginal_penetration")` is called again
- **THEN** `entity.sexual.virgin` is `False` after the first call and remains `False` after the
  second, with no error

#### Scenario: experience_types strictly grows across a sequence of events
- **WHEN** `apply_event(entity, "masturbation_climax")` is called, then
  `apply_event(entity, "first_vaginal_penetration")` is called, then
  `apply_event(entity, "masturbation_climax")` is called a second time
- **THEN** `entity.sexual.experience_types` contains both `"自慰"` and `"陰道性交"` after all three
  calls, and never shrinks or loses either entry at any point in the sequence

### Requirement: Every rule ID has exactly one matching test, structurally enforced
For every `Rule.id` loaded from `sexual.yaml`, a test function named `test_rule_<id>` SHALL exist in
`world/rules/tests/test_sexual_transitions.py`; no `test_rule_<id>` function SHALL exist for an `id`
`sexual.yaml` does not define. A rule SHALL NOT be addable to `sexual.yaml` without this check
failing until its matching test is also added.

#### Scenario: Every loaded rule id has a matching test function
- **WHEN** `test_every_rule_id_has_a_test()` is run
- **THEN** it passes, because every `id` in `sexual.yaml` has a corresponding `test_rule_<id>`
  function in the test module, and every `test_rule_<id>` function corresponds to a real `id`

#### Scenario: An added rule with no matching test fails the structural check
- **WHEN** a new rule is added to `sexual.yaml` with no corresponding `test_rule_<new_id>` function
  added to the test module
- **THEN** `test_every_rule_id_has_a_test()` fails, naming the rule id with no matching test

### Requirement: FIELD_KINDS covers exactly the fields targeted by sexual.yaml, structurally enforced
`FIELD_KINDS`' key set SHALL equal exactly the set of `then.field` values appearing anywhere in
`sexual.yaml` — no rule targets a field absent from `FIELD_KINDS`, and no `FIELD_KINDS` entry is
untargeted by any rule.

#### Scenario: FIELD_KINDS matches sexual.yaml's targeted fields exactly
- **WHEN** `test_field_kinds_covers_every_targetable_field()` is run
- **THEN** it passes, because `FIELD_KINDS`'s keys and the set of fields named in `sexual.yaml`'s
  `then` clauses are identical sets

#### Scenario: A rule targeting an unrecognized field fails the coverage check
- **WHEN** a hypothetical rule is added whose `then.field` is not a key of `FIELD_KINDS`
- **THEN** `test_field_kinds_covers_every_targetable_field()` fails, naming the unrecognized field

### Requirement: Race-specific behavior and narrative-only fields have no row in sexual.yaml
`sexual.yaml` SHALL contain no rule expressing a race-specific behavior (elf rapid post-climax
recovery, elf sensitivity floors, elf 餘韻→接近 rapid re-entry) and no rule targeting a narrative-only
field (身體感受, 興奮要素, 被注視感受, 最後性活動, or the top-level 基本資訊.狀態 enum), per change
7's design doc D-7.

#### Scenario: No rule references a race condition
- **WHEN** `sexual.yaml` is inspected
- **THEN** no rule's `when` or `then` references race, species, or any elf-specific behavior

#### Scenario: No rule targets a narrative-only field
- **WHEN** `sexual.yaml` is inspected
- **THEN** no rule's `then.field` names 身體感受, 興奮要素, 被注視感受, 最後性活動, or 基本資訊.狀態

### Requirement: The stamina action-efficiency threshold has no row in sexual.yaml and is named for change 6
`sexual.yaml` SHALL contain no rule expressing `variable_rule.md`'s `疲勞狀態` action-efficiency
threshold (`≤30點時所有行動效率降低`) — a standing-condition modifier belongs in change 6's
`combat_modifiers.yaml`, alongside the existing arousal-threshold and poison rows, not in this
event-triggered transition table.

#### Scenario: No rule models the stamina action-efficiency threshold
- **WHEN** `sexual.yaml` is inspected
- **THEN** no rule's `when` references an `sp`-threshold condition producing an action-efficiency
  modifier bundle, and this change's design documentation names change 6's `combat_modifiers.yaml`
  as the owner of that future row rather than leaving it unrecorded

