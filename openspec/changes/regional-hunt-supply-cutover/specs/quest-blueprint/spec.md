# Spec Delta

## MODIFIED Requirements

### Requirement: Published regional species hunts are legally provisionable in their authored region
Published regional species hunts SHALL reference valid region/species/variant selectors and at least one lawful authored ecological or explicit supply source, without limiting total quantity to one cell's current or potential supply.

#### Scenario: Quantity spans encounters
- **WHEN** a valid source-backed hunt quantity exceeds one cell, site or wave quantity
- **THEN** publication accepts it without promising immediate targets or completion before its existing deadline

#### Scenario: No lawful source
- **WHEN** a selector names no permitted ecological or explicit authored source
- **THEN** publication rejects without promoting habitat prose, visual examples or unknown species to supply

#### Scenario: Current shortage
- **WHEN** a lawful source currently has zero living targets or blocked automatic headroom
- **THEN** the definition remains valid and acceptance does not invoke provisioning

