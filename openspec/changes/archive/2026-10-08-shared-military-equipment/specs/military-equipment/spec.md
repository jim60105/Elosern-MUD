## Purpose

Define register six shared military pairs with real effects, prices and finite commerce as observable deterministic behavior with explicit rejection and acceptance boundaries.

## ADDED Requirements

### Requirement: Six military pairs use shared registered effects and approved integer prices
The system SHALL register E-S mass-produced military sword/armor pairs using exactly the approved section 5 table reproduced in design.md. Players and NPCs SHALL use identical keys/modifiers, existing rarity budgets and normal slots. No rank purchase gate SHALL apply.

#### Scenario: Shared real equipment
- **WHEN** a synthetic player and NPC wear the same registered pair
- **THEN** resolver stat readers return the same equipment bonuses

#### Scenario: Authoring fails closed
- **WHEN** a modifier exceeds its selected rarity budget
- **THEN** loading rejects it without enlarging the budget

### Requirement: Military pairs participate in ordinary finite commerce
Weapons SHALL join common_arms and armor common_outfits with approved buy prices, existing resale rules, initial stock 2, maximum 4 and restock quantity 1 through ordinary clock commerce. Trade SHALL remain transactional.

#### Scenario: Finite purchase and restock
- **WHEN** a buyer exhausts stock then the configured restock boundary passes
- **THEN** an out-of-stock buy rejects without mutation and stock returns by one up to four

#### Scenario: Rollback
- **WHEN** a purchase persistence step fails
- **THEN** wallet inventory mirrors and stock equal their prior snapshots

