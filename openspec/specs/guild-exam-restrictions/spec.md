# guild-exam-restrictions Specification

## Purpose
Define implement reducing-only exam accessories and shared skill/stat restriction consumers as observable deterministic behavior with explicit rejection and acceptance boundaries.

## Requirements

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
E-B examinations SHALL apply the authored rank ceilings and sword/body restriction policy, retaining permitted lower lineage and innate attack. Neutral baselines SHALL be reduced before transient negative modifiers; positive changes SHALL stay bounded and weaker hosts SHALL never be raised. Initiative and hit-resolution agility SHALL read their respective declared restrictions. Candidate/disguise SHALL NOT set host values.

#### Scenario: Hamstring remains consequential
- **WHEN** a synthetic restriction fixture sets pregear agility 11, gear +1 and a hamstring -5
- **THEN** hit-resolution agility is 7; independently exercised initiative and damage consumers read their intended restricted state

#### Scenario: Normal state restoration
- **WHEN** a real examination completes or rolls back
- **THEN** persistent normal bases and gear match the pre-exam snapshot

#### Scenario: Stronger senior
- **WHEN** a qualified A/S normal host wears B restriction
- **THEN** effective values are reduced while normal bases and ownership remain unchanged

#### Scenario: Naturally weak setup
- **WHEN** a host cannot reach its required authored reference without amplification
- **THEN** qualification/preflight rejects before mutation rather than admitting or raising the host

### Requirement: A and S examination kits retain real lineage effects
A/S SHALL use their authored normal bases and military pair/full usable sword lineage, sealing unrelated utility for comparability. Existing permitted basic body enhancement SHALL apply through its normal passive path. S domain attack SHALL remain above its pre-active reference when the domain grants a positive bonus. No artificial extreme-body amplification SHALL be introduced; reference effective-stat magnitudes SHALL be mutable authoring data.

#### Scenario: A and S real-kit pre-domain baselines
- **WHEN** a qualified A or S host runs its real permitted lineage under examination restrictions
- **THEN** normal effects reach the consumers and S domain bonus survives, without a duplicated 30/25/29 or 36/31/35 table or cap that suppresses the bonus

#### Scenario: S domain
- **WHEN** true_sword_saint domain activates under the real S examination kit
- **THEN** its measured positive attack bonus survives above the actual pre-domain baseline

