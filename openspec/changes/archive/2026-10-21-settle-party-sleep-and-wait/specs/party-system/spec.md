# Spec Delta

## ADDED Requirements

### Requirement: Any present forced sleeper makes party travel stationary
Any present effective party member in forced sleep SHALL block all travel before effects/time/location changes, including ordinary exits, settlement exits, wilderness steps and cross-layer gates. Possessing an awake member SHALL grant no carrying, split-party movement or sleeper teleport. Lawful local interactions and fighting SHALL remain available.

#### Scenario: Every exit family
- **WHEN** an awake possessed companion tries each exit family with a forced-sleeping member present
- **THEN** each refuses with a stable sleeping-party reason, identical source locations and unchanged tick/reserves

#### Scenario: Local play
- **WHEN** an awake member interacts or fights locally while a companion is forced asleep
- **THEN** ordinary lawful local actions remain available; no sleeping body is relocated

