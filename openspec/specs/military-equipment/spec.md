# military-equipment Specification

## Purpose
Define register six shared military pairs with real effects, prices and finite commerce as observable deterministic behavior with explicit rejection and acceptance boundaries.

## Requirements

### Requirement: Six military pairs use shared registered effects and approved integer prices
The six existing E-S military sword/armor pairs SHALL remain registered for shared player/NPC use, using identical keys/modifiers, ordinary slots and existing rarity budgets with no rank purchase gate. Prices and adjustment magnitudes SHALL be mutable authoring data; tests SHALL NOT duplicate the historical section 5 numerical table.

#### Scenario: Shared real equipment
- **WHEN** a player and NPC equip the same pair through normal equipment APIs
- **THEN** both receive the declared effects through shared consumers, with independently tested synthetic equipment arithmetic and no holder-specific path

#### Scenario: Authoring fails closed
- **WHEN** an equipment row names a missing identity, buff, price band or violates the established rarity budget
- **THEN** normal validation rejects it before use

### Requirement: Military pairs participate in ordinary finite commerce
Weapons SHALL remain in common_arms and armor in common_outfits through ordinary finite-stock commerce and clock restocking. Buy prices and initial/max/restock quantities SHALL come from valid authored declarations and existing resale rules. Trade SHALL remain transactional.

#### Scenario: Finite purchase and restock
- **WHEN** stock is exhausted and a configured restock boundary passes
- **THEN** purchases reject while empty and restock adds at most the declared quantity up to the declared maximum; fixed synthetic fixtures independently verify arithmetic, wallet/inventory/stock atomicity and resale

#### Scenario: Rollback
- **WHEN** a purchase persistence step fails after a relevant write
- **THEN** wallet, inventory mirrors and stock equal their prior snapshots after reload

