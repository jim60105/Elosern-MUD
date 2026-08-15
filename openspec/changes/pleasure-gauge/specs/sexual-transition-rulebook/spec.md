## MODIFIED Requirements

### Requirement: Ordered-level field rules write through the field's own live trait object, never through a second write path
Every rule targeting `wetness`, `shame`, or `exposure` SHALL apply its `delta` or `set` effect by
mutating the `OrderedLevelTrait` instance `entity.sexual.<field>` returns, never by constructing a
new trait or writing anywhere else. A `delta` of the form `"+N..+M"` SHALL resolve to a random
integer in `[N, M]` at apply time, using an injectable RNG so tests are deterministic. A `set` naming
a string absent from the field's own vocabulary SHALL raise, not silently no-op.

`arousal` is no longer covered by this requirement: no rule targets it via `then.field` (its four
former rules now target `pleasure`, a bounded counter, under the separate `bounded_counter` kind —
see `sexual-state-handler`'s pleasure-construction and pleasure-decay requirements for that field's
own contract).

#### Scenario: A fixed delta applies to the live trait
- **WHEN** `apply_event(entity, "stimulus_applied")` fires `wetness_follows_arousal`
- **THEN** `entity.sexual.wetness`'s ordinal increases by exactly `1`

#### Scenario: A random-range delta resolves deterministically under an injected RNG
- **WHEN** `apply_event(entity, "direct_stimulus_applied", rng=<fixed-value stub returning 2>)` fires
  `wetness_up_on_direct_stimulus` (`delta: "+1..+2"`)
- **THEN** `entity.sexual.wetness`'s ordinal increases by exactly `2`, matching the stub's fixed
  return value

#### Scenario: A set effect resolves an absolute vocabulary level
- **WHEN** `apply_event(entity, "climax_ends")` fires `wetness_max_on_climax`
- **THEN** `entity.sexual.wetness.level` becomes `"泛濫"` regardless of its level beforehand

#### Scenario: A set effect naming an unrecognized level raises
- **WHEN** `sexual.yaml` is loaded with a hypothetical malformed rule whose `then.set` value is not a
  member of the target field's vocabulary
- **THEN** applying that rule raises, naming the invalid level, rather than silently leaving the
  field unchanged

## ADDED Requirements

### Requirement: pleasure-targeting rules write through the bounded_counter kind, and report their arousal-level crossing under the field name arousal
Every rule targeting `pleasure` SHALL apply its `delta` or `set` effect by mutating
`entity.sexual.pleasure`'s bounded counter value, following the same `delta`/`set` resolution rules
as `bounded_counter`'s `ordered_level` sibling (`"+N..+M"` resolves via an injectable RNG; `set`
values are validated at load time). Because `field_changed: arousal` listeners
(`wetness_follows_arousal`) key on the observable arousal level rather than the raw pleasure number,
a `pleasure`-targeting rule's reported changed-field SHALL be `"arousal"`, computed by comparing the
derived arousal ordinal before and after the mutation — not `"pleasure"`, and not by comparing raw
pleasure numbers — so that a pleasure change remaining within one band reports no change at all.

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
