## MODIFIED Requirements

### Requirement: Buff definitions configure a subset of rate of change, clamped bounds, and decay rate
— never a combat-stat multiplier
`world/rules/rulebook/buffs.yaml` SHALL define each buff's tunable parameters (duration, tick interval,
stacking policy, and a `modifiers` mapping using at most the keys `rate`, `bounds`, and `decay`) with rate choosing either a fixed delta or a validated recovery profile (never both), per
design doc §6.4's exhaustive list of what a buff may modify. A buff definition SHALL NOT configure a
combat-stat multiplier (`atk_phys`/`agility`/`defense` scaling) — that remains change 5's
`SkillHandler.effective_value()` territory. A buff MAY declare an empty `modifiers` mapping when its
sole purpose is being detectable as present (a marker buff).

#### Scenario: A rate-of-change buff definition is well-formed
- **WHEN** `buffs.yaml`'s `poisoned` definition is inspected
- **THEN** its `modifiers` mapping contains a `rate` key naming a target field and a per-tick delta, and
  contains neither `bounds` nor a combat-stat-multiplier key

#### Scenario: A marker-only buff definition has an empty modifiers mapping
- **WHEN** `buffs.yaml`'s `paralysis` and `fear` definitions are inspected
- **THEN** each has an empty `modifiers` mapping, and each is still loadable and applyable via
  `BuffHandler`

#### Scenario: No buff definition configures a combat-stat multiplier
- **WHEN** every entry in `buffs.yaml` is inspected
- **THEN** none contains a `modifiers` key resembling a multiplicative combat-stat scale (e.g.
  `atk_phys_multiplier`); combat-facing consequences of a buff's presence are expressed exclusively
  through `combat_modifiers.yaml`'s separate table, never through a buff definition's own `modifiers`

## REMOVED Requirements

### Requirement: Every buff key in buffs.yaml has exactly one corresponding unit test
**Reason**: A test-name-to-authored-key correspondence enforces data mirroring rather than behavioral evidence and conflicts with the requested behavior-only verification.
**Migration**: Remove the correspondence checker, retain useful existing behavioral tests, and cover distinct rate, timing, refresh, immunity and expiration mechanics with synthetic fixtures. Do not add a light exception or weaken aggregate coverage.

## ADDED Requirements

### Requirement: Recovery profiles restore living recipients with explicit snapshot and live inputs
A timed recovery profile SHALL combine a validated base amount, optional live recipient-state adjustment and persisted caster-side modifiers. Caster inputs SHALL be captured on application and recipient effective state SHALL be read at each tick. Recovery SHALL floor the resulting nonnegative value, clamp to each living HP gap, and never revive a dead target. Malformed profiles SHALL be rejected before application.

#### Scenario: Live recipient and captured caster inputs differ
- **WHEN** recipient exposure changes after application and the caster later changes equipment or is deleted
- **THEN** the next tick reflects new recipient exposure but the original caster modifier and does not require the caster object

#### Scenario: No revival or overflow
- **WHEN** a tick addresses a dead recipient or a living recipient near maximum HP
- **THEN** dead HP is unchanged and living HP never exceeds its maximum

### Requirement: Finite recovery ticks and refresh are deterministic across elapsed-time partitions
A configured three-tick recovery SHALL tick at 10, 20 and 30 elapsed world seconds, never at application or after expiration. Advances within the clock's settlement-quanta budget SHALL produce the same ticks whether taken at once or in equivalent segments; an advance beyond that budget SHALL never fabricate ticks. Reapplication SHALL replace source snapshots and restart duration and tick remainder without stacking. Removal SHALL stop future ticks; persistence reload SHALL not replay completed ticks.

#### Scenario: Final tick precedes expiration
- **WHEN** world time advances 30 seconds at once or in three equal segments
- **THEN** exactly three recovery ticks occur with no application-time tick and no fourth tick at 40 seconds

#### Scenario: Refresh and reload preserve schedule
- **WHEN** a partially elapsed profile is refreshed and refetched
- **THEN** only the new three-tick schedule runs using the new source snapshots

#### Scenario: Removal cancels recovery
- **WHEN** the buff is removed before its next due tick
- **THEN** no later tick restores HP

### Requirement: Buff verification establishes mechanics rather than catalog correspondence
Distinct buff mechanics SHALL have substantive behavior tests using synthetic definitions. Assertions SHALL establish state changes, timing, refresh, expiry or immunity rather than require test function names or duplicate each authored buff key. Timed defense riders SHALL be verified through actual damage changes and expiration, not declaration equality.

#### Scenario: Synthetic timed defense affects combat
- **WHEN** a synthetic refreshable defense marker is applied and then expires
- **THEN** computed incoming damage is reduced while active and returns to its prior value after expiration without stacking on refresh
