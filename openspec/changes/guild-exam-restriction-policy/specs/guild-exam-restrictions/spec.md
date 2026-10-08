## Purpose

Define implement reducing-only exam accessories and shared skill/stat restriction consumers as observable deterministic behavior with explicit rejection and acceptance boundaries.

## ADDED Requirements

### Requirement: Guild accessories persist reversible execution and effect restrictions
Registered non-tradeable guild accessories SHALL occupy valid normal accessory slots and persist exam_id/host identity restriction state under rules-core ownership. Learned bases/ownership/proficiency SHALL remain intact. Every availability/action/passive/stat/gauge/initiative/equipment/hit/modifier/view consumer SHALL interpret one policy. Sealed actions SHALL reject before costs/effects; sealed passives SHALL contribute nothing. Purchase/sale/transfer/loot/reward SHALL be prohibited.

#### Scenario: Direct sealed action
- **WHEN** a restricted host directly submits heal
- **THEN** resolver rejects with pools/effects unchanged

#### Scenario: Sealed passive
- **WHEN** defense_instinct is learned and restricted
- **THEN** it contributes zero while ownership remains intact

#### Scenario: Accessory overflow
- **WHEN** kit has no available valid accessory slot
- **THEN** activation rejects before mutation

#### Scenario: Guild property
- **WHEN** a host attempts transfer or a loot/sale path selects the accessory
- **THEN** the item cannot leave guild ownership

### Requirement: Reduced neutral baselines precede penalties and preserve both agility consumers
E-B SHALL use section 4.2 ceilings and sword/body policy exactly, including permitted lower lineage and innate attack. Neutral baselines SHALL be reduced before transient negative modifiers; positive changes SHALL stay bounded and weaker hosts SHALL never be raised. Initiative agility SHALL be 8/11/14/17 and final neutral agility 8/12/16/20. Player/disguise SHALL NOT set host values.

#### Scenario: Hamstring remains consequential
- **WHEN** D pregear agility 11 gains gear 1 and hamstring subtracts 5
- **THEN** hit-resolution agility equals 7, not 12

#### Scenario: Stronger senior
- **WHEN** a qualified A/S normal host wears B restriction
- **THEN** effective values are reduced while normal bases and ownership remain unchanged

#### Scenario: Naturally weak setup
- **WHEN** a host cannot reach required reference without amplification
- **THEN** qualification/preflight rejects it

### Requirement: A and S examination kits retain real lineage effects
A/S SHALL use section 4.3 normal bases and respective military pair/full usable sword lineage, sealing unrelated utility for comparability. S SHALL retain current domain attack bonus above its pre-active 36 attack. No artificial 100/1000 amplification SHALL be introduced.
A/S SHALL permit body_enhancement_basic at its existing 1.2 multiplier to produce the reference pre-domain physical values A 30/25/29 and S 36/31/35, while sealing defense_instinct and unrelated utility effects.

#### Scenario: A and S real-kit pre-domain baselines
- **WHEN** their actual military pairs and permitted basic body enhancement apply before domain activation
- **THEN** A has attack/agility/defense 30/25/29 and S 36/31/35 without hidden stat amplification

#### Scenario: S domain
- **WHEN** true_sword_saint domain activates under S kit
- **THEN** its measured attack bonus remains and 36 does not cap it away

