## MODIFIED Requirements

### Requirement: Damaging rate buffs persist a validated effect-source identity in the buff cache
`_handle_buff_apply` SHALL persist the resolving actor's dbref as `source_pk` in the buff cache whenever the applied definition's `rate` modifier damages a gauge (target `hp` or `mp` with a negative delta). The value SHALL be derived from the actor inside the handler; a caller-supplied `source_pk` in `buff_kwargs` SHALL NOT override it, and an actor without a resolvable positive-int dbref SHALL reject the action before commit. Buff instances created outside the handler (for example direct `_add_buff` calls) MAY lack `source_pk`, in which case their rate ticks are unattributed. An mp-target damaging rate tick SHALL carry this persisted attribution into the canonical MP-change writer so a depletion crossing it causes dispatches with the grant-time source skill and source tier; the hp-target dispatch path SHALL remain behaviorally unchanged.

#### Scenario: Applying fire_scorch stores the caster's dbref
- **WHEN** `_handle_buff_apply` resolves `buff:fire_scorch` for a target in combat
- **THEN** the target's buff cache entry carries `source_pk` equal to the caster's dbref, readable on the buff instance

#### Scenario: Caller-supplied source identity cannot spoof attribution
- **WHEN** a `buff_kwargs` value supplies `source_pk` naming a different entity than the actor
- **THEN** the cached `source_pk` is the actor's dbref, never the supplied value

#### Scenario: An actor without a resolvable dbref rejects the damaging buff application
- **WHEN** `_handle_buff_apply` stages a damaging buff for an actor with no positive-int pk
- **THEN** the action rejects before commit and no buff is added

#### Scenario: Reapplying a damaging buff replaces the source with the new caster
- **WHEN** the same damaging buff key is re-applied by a different caster before expiry
- **THEN** the buff cache's `source_pk` is the newest caster's dbref, and a refresh that omits `source_pk` retains the previously cached value rather than erasing attribution

#### Scenario: An mp-target drain ticks with grant-time attribution
- **WHEN** a synthetic mp-target negative-delta buff applied by a source-bearing cast later ticks the holder's MP to zero
- **THEN** the depletion crossing is attributed to the persisted grant-time source skill and tier, not to the tick moment
