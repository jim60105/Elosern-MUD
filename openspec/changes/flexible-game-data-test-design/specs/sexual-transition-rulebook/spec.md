# Spec Delta

## MODIFIED Requirements

### Requirement: The one rule targeting a vital gauge outside SexualState writes through change 3's entity.traits surface, never through SexualState
`sp_cost_on_climax` SHALL apply its cost by mutating `entity.traits.sp.current` directly ;  the
public writable property of change 3's `GaugeTrait` (`.value` is its read-only alias) ;  and SHALL
NOT reach through `entity.sexual` to do so. The delta
SHALL resolve to a negative integer in the authored range, applied as a
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

#### Scenario: Authored tuning is distinct from mechanism examples
- **WHEN** tests exercise exact numerical band, delta, duration, bias or multiplier examples in this requirement
- **THEN** scoped fixed synthetic rulebook rows provide those numbers and independently known outcomes; production rows receive valid-shape/reference/intentional-invariant checks without a copied expected balance table


### Requirement: pleasure-targeting rules write through the bounded_counter kind, and report their arousal-level crossing under the field name arousal
Every rule targeting `pleasure` SHALL apply its `delta` or `set` effect by mutating `entity.sexual.pleasure`'s bounded counter value, following the same `delta`/`set` resolution rules as `bounded_counter`'s `ordered_level` sibling. A `pleasure`-targeting rule's reported changed-field SHALL be `"arousal"`, computed by comparing the derived arousal ordinal before and after the mutation ;  not `"pleasure"`, and not by comparing raw pleasure numbers.

#### Scenario: A pleasure delta that crosses an arousal band reports as an arousal change
- **WHEN** `apply_event(entity, "stimulus_applied")` fires `arousal_up_on_stimulus`
  (`{field: pleasure, delta: "+8..+14"}`) on an entity whose `pleasure` starts at `10` (`平靜` band)
  and the resolved delta crosses into the `微興奮` band
- **THEN** `wetness_follows_arousal` fires within the same `apply_event()` call, because the pass's
  `_changed` map records `"arousal": "up"`, not `"pleasure": "up"`

#### Scenario: A pleasure delta that stays within one band reports no change
- **WHEN** a `pleasure`-targeting rule's resolved delta moves `pleasure` from `20` to `25`, both
  within the `微興奮` band (`15..34`)
- **THEN** no field-changed event fires for either `"arousal"` or `"pleasure"` from that mutation,
  and `wetness_follows_arousal` does not fire

#### Scenario: An absolute set to 100 reads back as 極限
- **WHEN** `apply_event(entity, "extreme_stimulus_applied")` fires `arousal_extreme_stimulus_to_max`
  (`{field: pleasure, set: 100}`)
- **THEN** `entity.sexual.pleasure.value` becomes `100` and `entity.sexual.arousal.level` becomes
  `"極限"` regardless of its level beforehand

#### Scenario: climax_gate still fires from a pleasure-driven arousal change
- **WHEN** `apply_event(entity, "extreme_stimulus_applied")` raises `pleasure` to `100` (and
  therefore derived `arousal` to `極限`) on an entity whose `climax_phase` is `"未達"`
- **THEN** `climax_gate` (`{field: arousal, equals: 極限}`, unmodified by this capability) fires
  within the same call and `entity.sexual.climax_phase.level` becomes `"接近"`, proving
  `arousal`-keyed `when` conditions continue to evaluate correctly against the derived view with no
  change to `climax_gate` itself

#### Scenario: Delta and set resolution follow the ordered_level sibling
- **WHEN** a `pleasure`-targeting rule uses `"+N..+M"` or a `set` value
- **THEN** the range resolves via an injectable RNG and `set` values are validated at load time

#### Scenario: Arousal listeners key on the observable level
- **WHEN** `field_changed: arousal` listeners (`wetness_follows_arousal`) evaluate
- **THEN** they key on the observable arousal level rather than the raw pleasure number

#### Scenario: A within-band pleasure change reports no change
- **WHEN** a pleasure change remains within one arousal band
- **THEN** it reports no change at all

#### Scenario: Authored tuning is distinct from mechanism examples
- **WHEN** tests exercise exact numerical band, delta, duration, bias or multiplier examples in this requirement
- **THEN** scoped fixed synthetic rulebook rows provide those numbers and independently known outcomes; production rows receive valid-shape/reference/intentional-invariant checks without a copied expected balance table

