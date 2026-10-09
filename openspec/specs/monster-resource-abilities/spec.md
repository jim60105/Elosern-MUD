# monster-resource-abilities Specification

## Purpose
Defines the approved crocodile resource ability and its complete authored-kit, combat, payment and persistence behavior through the common player/NPC/monster skill engine.

## Requirements

### Requirement: Crocodile bite is one authored shared-engine physical resource skill
Both crocodile variants SHALL own active tide_devouring_bite, labeled 吞潮咬擊, with no prerequisites/passive. It SHALL be combat-only, single enemy, close physical contact, water physical school, coefficient 1.0 and one strike. Nominal payment SHALL be 10 MP and 5 SP. Taxonomy SHALL be elemental magic/water without granting player access or freeform scaling.

#### Scenario: Definition uses ordinary mechanics
- **WHEN** the production bite resolves for an eligible crocodile
- **THEN** damage reads physical attack with the normal formula, not magic_power; targeting uses existing physical close-contact/displacement rules

#### Scenario: Enemy component keeps shared selection rules
- **WHEN** a companion or invalid contact target is selected
- **THEN** the bite delivers no enemy-only damage/drain to it and ordinary targeting rejects invalid contact without introducing enemy-only faction constraints

#### Scenario: No acquired chain or scale is invented
- **WHEN** the two approved kits and player catalogs are inspected
- **THEN** basic_attack and flee remain; there is no new passive/prerequisite tree or freeform scale; the 10-MP price retains the existing single-target apprentice band

### Requirement: Successful bite drains MP and recovers only actual removal
The bite SHALL drain up to 10 current target MP once if its damage strike hits and recover 100% of actual MP removed capped at caster maximum. A miss SHALL drain/recover nothing. Critical damage SHALL NOT multiply the transfer. Zero target MP SHALL NOT cancel physical damage, and crossing defeat HP SHALL NOT suppress same-action transfer.

#### Scenario: Hit and miss evidence
- **WHEN** a deterministic bite hits and another misses
- **THEN** the hit damages and transfers up to 10 MP; the miss transfers none and still pays 10 MP/5 SP

#### Scenario: Partial and empty pools
- **WHEN** hit targets have 3 MP and 0 MP respectively
- **THEN** removal/recovery is at most 3 and exactly 0 respectively, with physical damage in both cases

#### Scenario: Critical and defeat crossing
- **WHEN** one hit is critical and another crosses the defeat threshold
- **THEN** ordinary damage applies while each transfer remains once and at most 10; defeat settlement follows the complete action

#### Scenario: No healing or lasting magic loss
- **WHEN** bite outcomes settle
- **THEN** no HP recovery or permanent magic-power reduction occurs; no remote river-wide drain exists

### Requirement: Affordability precedes effects and recovery precedes costs
The caster SHALL already afford both nominal costs after existing modifiers before any roll/effect. Damage, target drain and capped caster recovery SHALL precede MP/SP payment in the shared transaction. Existing canonical transfer/cost reactions SHALL remain in force; overflow SHALL be discarded.

#### Scenario: Full cap loses nominal cost
- **WHEN** a bank_lurker starts at 30 MP and removes 10 MP
- **THEN** recovery clamps at 30 before payment, so it ends at 20 MP and spends 5 SP

#### Scenario: Room under the cap follows current order
- **WHEN** a bank_lurker starts at 20 MP and removes 10 MP
- **THEN** it recovers to 30 then pays to 20; requested recovery cannot exceed actual removal

#### Scenario: Drain cannot finance an action
- **WHEN** the actor starts below 10 MP or below 5 SP and target MP is plentiful
- **THEN** resolution rejects before dice, damage, drain, recovery or practice

#### Scenario: Canonical modifiers still apply
- **WHEN** an existing resource modifier or MP reaction participates
- **THEN** the shared APIs apply it without reordering existing skills or storing discarded recovery

### Requirement: Production crocodile delivery includes real combat and persistence evidence
Delivery SHALL formally construct both approved variants and exercise resolver-backed combat sessions through hit, miss and resource exhaustion followed by ordinary attack. Evidence SHALL observe victim HP, both MP pools and caster SP, construction/action rollback and reload. Runtime smoke SHALL use no live generative or image service.

#### Scenario: Complete production loop
- **WHEN** both variants enter real resolver-backed sessions after production construction
- **THEN** their exact approved profiles, usable kits and profile bindings participate; depletion changes policy to ordinary attack and reload preserves current values

#### Scenario: Atomicity covers both participants
- **WHEN** failure is injected after staged damage/transfer or during kit/profile construction
- **THEN** no partial participant state or ownership/configuration remains; rolled-back practice claims are released

#### Scenario: Second species proves shared reuse
- **WHEN** a synthetic second species owns an eligible synthetic damage/transfer ability
- **THEN** it executes through identical dependency/transfer APIs without a species-specific branch

### Requirement: Crocodile ecology documents implemented limits
Public crocodile ecology and author notes SHALL describe implemented contact MP pressure with no HP healing, remote drain or permanent magic loss. Assertions that crocodile mechanics/numbers remain deferred SHALL be removed. Other five species SHALL retain their deferred abilities and boundaries.

#### Scenario: Public projection and notes agree
- **WHEN** the registry, bestiary and relevant author guidance are read
- **THEN** crocodile mechanics and limits agree without exposing private fields, inventing other species abilities or claiming recalibrated grades
