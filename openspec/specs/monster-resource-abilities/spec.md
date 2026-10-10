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
Public crocodile ecology and author notes SHALL describe implemented contact MP pressure with no HP healing, remote drain or permanent magic loss. Assertions that crocodile mechanics/numbers remain deferred SHALL be removed. Delivered approved species SHALL use their authored kits and revised boundaries; still-deferred species are ridge_burrow_hare, rock_echo_goat, fog_mane_lynx.

#### Scenario: Public projection and notes agree
- **WHEN** the registry, bestiary and relevant author guidance are read
- **THEN** crocodile mechanics and limits agree without exposing private fields, inventing unapproved species abilities or claiming recalibrated grades

### Requirement: 穗鳴雀 owns its approved contact resource ability
Both `sway_whistle_sparrow` variants SHALL own `grain_shaking_peck` (震穗啄擊) as a prerequisite-free, combat-only single-target physical ability with `wind` elemental-magic taxonomy and monster/species eligibility. Its sole damage strike SHALL use coefficient 0.8 and nominal payment 10 MP plus 2 SP. It SHALL have no passive, healing, transfer, environment gate or freeform scale.

#### Scenario: Exact ordered composition
- **WHEN** the approved ability is read
- **THEN** its ordered effects are `damage:wind:physical` and `buff_apply:grain_rattle`, with enemy damage and enemy buff requiring hit occurrence 0; damage reads physical attack, never magic power

#### Scenario: Shared identity containment
- **WHEN** a player, NPC or wrong-species monster corruptly owns the ability
- **THEN** invocation rejects before dice, costs, buffs or practice, and player catalog/lineage admission remains denied

#### Scenario: Contact and faction remain shared
- **WHEN** an invalid, dead or positional-displaced contact target is supplied, or a valid ally is selected
- **THEN** ordinary target gates reject invalid contact; ANY faction keeps candidate selection unrestricted but enemy components deliver nothing to allies

### Requirement: 穗鳴雀 timed modifier follows its authored recipient and lifetime
The `grain_rattle` mount SHALL last 10 world seconds, refresh without accumulating magnitude and apply `accuracy: -3` once to each selected enemy hit by its source strike. It SHALL have debuff polarity and no DoT, ground/positional marker or action lock. Expiry/removal SHALL restore the control modifier result.

#### Scenario: Hit and miss separate delivery from payment
- **WHEN** deterministic hit and miss attempts resolve
- **THEN** only the hit applies the target buff once, including an absorbed hit and both pay 10 MP/2 SP exactly once under unmodified costs

#### Scenario: Refresh and expiry
- **WHEN** the mount is reapplied before expiry then world time passes its refreshed lifetime
- **THEN** magnitude never accumulates and the modifier is absent after expiry

### Requirement: 穗鳴雀 payment and atomicity retain the shared transaction
Affordability SHALL precede dice/effects, with normal modifiers and effects-before-cost payment. Any failure SHALL restore all touched gauges, buffs and practice claims. Ecological fog, light, grain, soil or rock descriptions SHALL NOT change any combat result.

#### Scenario: Either insufficient resource rejects before effects
- **WHEN** MP is below 10 or SP below 2 under unmodified costs
- **THEN** the cast rejects before dice, HP loss, buff application, payment or practice

#### Scenario: Late failure restores the participants
- **WHEN** a late failure follows staged damage, buff and payment
- **THEN** actor/target HP, MP/SP, buffs and practice match their pre-action values and a retry has no stale claim

#### Scenario: Environment prose cannot act as a fact
- **WHEN** otherwise equal sessions use different scene prose, habitat labels or forged fog/light/rock request facts
- **THEN** the contact action and magnitude are identical and no ecological bonus or environment-dependent damage is produced

### Requirement: 穗鳴雀 public ecology reflects the completed contact kit
The registry public ecology and bestiary SHALL publish the same approved sentence edits in the proposed remaining-species design §4. Existing ecological conditions and untouched limits SHALL remain true, while current executable-deferral claims for this species SHALL be removed. Historical approval notes SHALL remain distinguishable from current implementation status.

#### Scenario: Revised prose and private boundaries
- **WHEN** public ecology, bestiary and author guides are read after implementation
- **THEN** they disclose environment-independent contact behavior, retain the design's unchanged limits, remove only this species' current deferral and expose no author-private origin or conjecture

### Requirement: 潮燈蟹 owns its approved contact resource ability
Both `tide_lamp_crab` variants SHALL own `lamp_carapace_claw` (燈甲螯擊) as a prerequisite-free, combat-only single-target physical ability with `light` elemental-magic taxonomy and monster/species eligibility. Its sole damage strike SHALL use coefficient 1.0 and nominal payment 10 MP plus 3 SP. It SHALL have no passive, healing, transfer, environment gate or freeform scale.

#### Scenario: Exact ordered composition
- **WHEN** the approved ability is read
- **THEN** its ordered effects are `damage:light:physical` and `self_buff_apply:lamp_carapace_guard`, with enemy damage and self guard independent of hit; damage reads physical attack, never magic power

#### Scenario: Shared identity containment
- **WHEN** a player, NPC or wrong-species monster corruptly owns the ability
- **THEN** invocation rejects before dice, costs, buffs or practice, and player catalog/lineage admission remains denied

#### Scenario: Contact and faction remain shared
- **WHEN** an invalid, dead or positional-displaced contact target is supplied, or a valid ally is selected
- **THEN** ordinary target gates reject invalid contact; ANY faction keeps candidate selection unrestricted but enemy components deliver nothing to allies

### Requirement: 潮燈蟹 timed modifier follows its authored recipient and lifetime
The `lamp_carapace_guard` mount SHALL last 20 world seconds, refresh without accumulating magnitude and apply `defense: 2` to its caster on each affordable resolved attempt with a valid selected contact target, including a miss. Rejected or no-target requests SHALL grant nothing. It SHALL have buff polarity and no DoT, ground/positional marker or action lock. Expiry/removal SHALL restore the control modifier result.

#### Scenario: Hit and miss separate delivery from payment
- **WHEN** deterministic hit and miss attempts against a valid selected enemy resolve
- **THEN** both attempts mount caster guard once and both pay 10 MP/3 SP exactly once under unmodified costs

#### Scenario: Refresh and expiry
- **WHEN** the mount is reapplied before expiry then world time passes its refreshed lifetime
- **THEN** magnitude never accumulates and the modifier is absent after expiry

#### Scenario: Missing or invalid contact cannot grant guard
- **WHEN** the SINGLE request has no selected target or its target fails ordinary contact validation
- **THEN** the ordinary target gate rejects before guard, damage, resource payment or practice

### Requirement: 潮燈蟹 payment and atomicity retain the shared transaction
Affordability SHALL precede dice/effects, with normal modifiers and effects-before-cost payment. Any failure SHALL restore all touched gauges, buffs and practice claims. Ecological fog, light, grain, soil or rock descriptions SHALL NOT change any combat result.

#### Scenario: Either insufficient resource rejects before effects
- **WHEN** MP is below 10 or SP below 3 under unmodified costs
- **THEN** the cast rejects before dice, HP loss, buff application, payment or practice

#### Scenario: Late failure restores the participants
- **WHEN** a late failure follows staged damage, buff and payment
- **THEN** actor/target HP, MP/SP, buffs and practice match their pre-action values and a retry has no stale claim

#### Scenario: Environment prose cannot act as a fact
- **WHEN** otherwise equal sessions use different scene prose, habitat labels or forged fog/light/rock request facts
- **THEN** the contact action and magnitude are identical and no ecological bonus or environment-dependent damage is produced

### Requirement: 潮燈蟹 public ecology reflects the completed contact kit
The registry public ecology and bestiary SHALL publish the same approved sentence edits in the proposed remaining-species design §5. Existing ecological conditions and untouched limits SHALL remain true, while current executable-deferral claims for this species SHALL be removed. Historical approval notes SHALL remain distinguishable from current implementation status.

#### Scenario: Revised prose and private boundaries
- **WHEN** public ecology, bestiary and author guides are read after implementation
- **THEN** they disclose environment-independent contact behavior, retain the design's unchanged limits, remove only this species' current deferral and expose no author-private origin or conjecture
