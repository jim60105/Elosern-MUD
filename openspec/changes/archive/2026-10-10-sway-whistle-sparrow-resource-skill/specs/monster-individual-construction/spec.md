# Spec Delta

## ADDED Requirements

### Requirement: 穗鳴雀 construction persists both approved contact kits
Formal construction of `sway_whistle_sparrow` SHALL atomically apply its approved complete profile, sole active `grain_shaking_peck`, empty passive kit and `instinctive` behavior binding. Reload SHALL retain identity, owned order, binding and depleted MP/SP. Existing live individuals SHALL NOT reset when registry content changes.

#### Scenario: Both literal rows use the production boundary
- **WHEN** `grain_pecker`, `flock_leader` are formally constructed
- **THEN** their HP/MP/SP/atk_phys/agility/defense/magic_power and grades equal 30/20/8/4/7/3/0 (F), 55/30/12/8/10/4/0 (E), with special ability before innate basic_attack/flee and no fabricated prerequisites

#### Scenario: Construction failure and reload
- **WHEN** kit/binding assignment fails, or a successfully constructed actor spends resources and reloads
- **THEN** failure leaves no partial individual/configuration, while reload preserves committed identity, order, profile and depleted resources

#### Scenario: Existing selectors and other rows are unchanged
- **WHEN** regional/site hunts match identities and all other variant records are compared
- **THEN** species/variant selector keys, ordinary classification and grades are unchanged; other complete rows, including both delivered crocodile rows and their kits, remain unchanged by this implementation
