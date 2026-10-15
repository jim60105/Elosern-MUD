# Spec Delta

## ADDED Requirements

### Requirement: Controllable companion item requests use that actors complete item rules
A commanded companion SHALL use its own usable inventory, equipment context and shared item-effect preflight. SELF SHALL bind that actor; successful consumption SHALL remove one item and matching mirror from that actor. Every existing scope, effectiveness rule and disabled reason SHALL apply without a shared party bag.

#### Scenario: Local stock and mirrors
- **WHEN** a companion holds a usable item absent from the commander inventory
- **THEN** its choice is available for that companion and a valid resolved use consumes only its item and contained mirror

#### Scenario: Ineffective or forged item
- **WHEN** a client names an item the selected member lacks or no effect can change any allowed recipient
- **THEN** preflight rejects without consuming an item, resources, round or time

#### Scenario: Full effect and targeting semantics
- **WHEN** a companion chooses an item with mixed effects or nonself recipients
- **THEN** ordinary effect target resolution and per-effect ineffective skipping apply with the selected actor as owner

