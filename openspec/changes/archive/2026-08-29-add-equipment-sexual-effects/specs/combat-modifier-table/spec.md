## ADDED Requirements

### Requirement: Condition contexts match on effective exposure

Both combat-modifier condition-context builders (the handler path and the
no-create path) SHALL fill the exposure condition field from the effective
(stored + equipment bias, clamped) ordinal, exposed as one shared immutable
level view with `gte`/`lte`/equality comparison parity across both paths.
Exposure-gated rules SHALL therefore fire on revealing equipment while
written state and stored values never change. The no-create builder SHALL
remain handler-free and write-free, and stored sexual levels SHALL be read
through one neutral shared reader that imports no rules modules.

#### Scenario: Revealing habit earns the exposure defense penalty with little written

- **WHEN** an actor with stored exposure 中等 wearing 修女聖袍 (bias +1,
  effective 高) is evaluated for combat modifiers
- **THEN** the shipped 露出 ≥ 高 defense adjustment is present in the merged
  bundle

#### Scenario: Penalty round-trips with the equipment

- **WHEN** the actor unequips 修女聖袍 mid-itinerary and modifiers are
  re-evaluated
- **THEN** the exposure defense adjustment is gone in both paths and the
  stored trait never moved

#### Scenario: Non-create preview agrees with live resolution

- **WHEN** the same actor's modifiers are evaluated through the no-create
  path and through the handler path
- **THEN** both bundles are identical, the exposure fields are the same
  view type, and all three comparison styles agree

#### Scenario: No equipment reproduces shipped matching

- **WHEN** an unequipped entity's contexts are built
- **THEN** exposure conditions match on the stored value exactly as before
