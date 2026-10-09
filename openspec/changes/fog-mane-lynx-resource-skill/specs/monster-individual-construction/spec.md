# Spec Delta

## ADDED Requirements

### Requirement: 霧鬃山貓 construction persists both approved contact kits
Formal construction of `fog_mane_lynx` SHALL atomically apply its approved complete profile, sole active `mane_crosswind_pounce`, empty passive kit and `ambush_predator` behavior binding. Reload SHALL retain identity, owned order, binding and depleted MP/SP. Existing live individuals SHALL NOT reset when registry content changes.

#### Scenario: Both literal rows use the production boundary
- **WHEN** `wood_stalker`, `trail_hunter` are formally constructed
- **THEN** their HP/MP/SP/atk_phys/agility/defense/magic_power and grades equal 115/30/20/20/20/10/0 (D), 165/50/30/25/22/12/0 (C), with special ability before innate basic_attack/flee and no fabricated prerequisites

#### Scenario: Construction failure and reload
- **WHEN** kit/binding assignment fails, or a successfully constructed actor spends resources and reloads
- **THEN** failure leaves no partial individual/configuration, while reload preserves committed identity, order, profile and depleted resources

#### Scenario: Existing selectors and other rows are unchanged
- **WHEN** regional/site hunts match identities and all other variant records are compared
- **THEN** species/variant selector keys, ordinary classification and grades are unchanged; other complete rows, including both delivered crocodile rows and their kits, remain unchanged by this implementation
