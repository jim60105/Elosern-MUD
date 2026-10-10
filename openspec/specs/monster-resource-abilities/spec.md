# monster-resource-abilities Specification

## Purpose
Defines the approved crocodile resource ability and its complete authored-kit, combat, payment and persistence behavior through the common player/NPC/monster skill engine.

## Requirements

### Requirement: Crocodile bite is one authored shared-engine physical resource skill
Both crocodile variants SHALL own active tide_devouring_bite, labeled 吞潮咬擊, with no prerequisites/passive. It SHALL be selectable outside combat (`usable_out_of_combat=True`), with damage resolution requiring the existing battlefield gate, single enemy, close physical contact, water physical school, its authored coefficient and one strike. Nominal payment SHALL be the declared MP and SP costs. Taxonomy SHALL be elemental magic/water without granting player access or freeform scaling.

#### Scenario: Definition uses ordinary mechanics
- **WHEN** the production bite resolves for an eligible crocodile
- **THEN** damage reads physical attack with the normal formula, not magic_power; targeting uses existing physical close-contact/displacement rules

#### Scenario: Enemy component keeps shared selection rules
- **WHEN** a companion or invalid contact target is selected
- **THEN** the bite delivers no enemy-only damage/drain to it and ordinary targeting rejects invalid contact without introducing enemy-only faction constraints

#### Scenario: No acquired chain or scale is invented
- **WHEN** the two approved kits and player catalogs are inspected
- **THEN** basic_attack and flee remain; there is no new passive/prerequisite tree or freeform scale; the price remains valid under the existing cost-tier schema

#### Scenario: Content values remain tunable
- **WHEN** valid authored costs, coefficients, duration, modifier or drain amount change
- **THEN** integrity checks and representative consumer smoke remain green without duplicated numeric expectations; synthetic shared tests independently establish the retained mechanics

### Requirement: Successful bite drains MP and recovers only actual removal
The bite SHALL drain up to its declared amount of current target MP once if its damage strike hits and recover its declared share of actual MP removed capped at caster maximum. A miss SHALL drain/recover nothing. Critical damage SHALL NOT multiply the transfer. Zero target MP SHALL NOT cancel physical damage, and crossing defeat HP SHALL NOT suppress same-action transfer.

#### Scenario: Hit and miss evidence
- **WHEN** a deterministic bite hits and another misses
- **THEN** the hit damages and transfers up to the declared drain amount; the miss transfers none and still pays the declared MP/SP costs

#### Scenario: Partial and empty pools
- **WHEN** hit targets have 3 MP and 0 MP respectively
- **THEN** removal/recovery is at most 3 and exactly 0 respectively, with physical damage in both cases

#### Scenario: Critical and defeat crossing
- **WHEN** one hit is critical and another crosses the defeat threshold
- **THEN** ordinary damage applies while each transfer remains once and bounded by the declared drain amount; defeat settlement follows the complete action

#### Scenario: No healing or lasting magic loss
- **WHEN** bite outcomes settle
- **THEN** no HP recovery or permanent magic-power reduction occurs; no remote river-wide drain exists

#### Scenario: Content values remain tunable
- **WHEN** valid authored costs, coefficients, duration, modifier or drain amount change
- **THEN** integrity checks and representative consumer smoke remain green without duplicated numeric expectations; synthetic shared tests independently establish the retained mechanics

### Requirement: Affordability precedes effects and recovery precedes costs
The caster SHALL already afford both adjusted declared costs before any roll/effect. Damage, target drain and capped caster recovery SHALL precede MP/SP payment in the shared transaction. Canonical reactions SHALL remain in force and overflow SHALL be discarded. Tests SHALL cover this order once with fixed synthetic fixtures.

#### Scenario: Full cap loses nominal cost
- **WHEN** a synthetic caster starts at maximum MP 30, removes 10 target MP with full recovery share, and pays cost 10 MP plus 5 SP
- **THEN** caster MP ends at 20 and SP decreases by 5; a caster starting at 20 MP also ends at 20

#### Scenario: Room under the cap follows current order
- **WHEN** the same fixed synthetic caster starts at MP 20 under cap 30 and removes 10 target MP
- **THEN** recovery reaches 30 before MP payment 10 leaves 20, without credit exceeding actual removal

#### Scenario: Drain cannot finance an action
- **WHEN** either resource is below its adjusted declared cost despite plentiful target MP
- **THEN** resolution rejects before dice, effects or practice

#### Scenario: Canonical modifiers still apply
- **WHEN** existing resource modifiers or MP reactions participate
- **THEN** shared APIs apply them without reordering existing skills or storing discarded recovery

#### Scenario: Content values remain tunable
- **WHEN** valid authored costs, coefficients, duration, modifier or drain amount change
- **THEN** integrity checks and representative consumer smoke remain green without duplicated numeric expectations; synthetic shared tests independently establish the retained mechanics

### Requirement: Production crocodile delivery includes real combat and persistence evidence
Delivery SHALL validate both variants generically and retain a representative formally constructed resolver-backed session smoke observing victim HP, both MP pools, caster SP, ordinary fallback and reload. Shared synthetic engine suites SHALL cover hit/miss vectors and construction/action rollback rather than duplicate an exhaustive suite per variant. Runtime smoke SHALL use no live generative or image service.

#### Scenario: Complete production loop
- **WHEN** both variants enter real resolver-backed sessions after production construction
- **THEN** their current authored profiles, usable kits and profile bindings participate; depletion changes policy to ordinary attack and reload preserves current values

#### Scenario: Atomicity covers both participants
- **WHEN** failure is injected after staged damage/transfer or during kit/profile construction
- **THEN** no partial participant state or ownership/configuration remains; rolled-back practice claims are released

#### Scenario: Second species proves shared reuse
- **WHEN** a synthetic second species owns an eligible synthetic damage/transfer ability
- **THEN** it executes through identical dependency/transfer APIs without a species-specific branch

#### Scenario: Content values remain tunable
- **WHEN** valid authored costs, coefficients, duration, modifier or drain amount change
- **THEN** integrity checks and representative consumer smoke remain green without duplicated numeric expectations; synthetic shared tests independently establish the retained mechanics

### Requirement: Crocodile ecology documents implemented limits
Public crocodile ecology and author notes SHALL describe implemented contact MP pressure with no HP healing, remote drain or permanent magic loss. Assertions that crocodile mechanics/numbers remain deferred SHALL be removed. Delivered approved species SHALL use their authored kits and revised boundaries; still-deferred species are ridge_burrow_hare, rock_echo_goat, fog_mane_lynx.

#### Scenario: Public projection and notes agree
- **WHEN** the registry, bestiary and relevant author guidance are read
- **THEN** crocodile mechanics and limits agree without exposing private fields, inventing unapproved species abilities or claiming recalibrated grades

### Requirement: 穗鳴雀 owns its approved contact resource ability
Both `sway_whistle_sparrow` variants SHALL own `grain_shaking_peck` (震穗啄擊) as a prerequisite-free single-target physical ability selectable outside combat (`usable_out_of_combat=True`) with `wind` elemental-magic taxonomy and monster/species eligibility, whose damage resolution requires the existing battlefield gate. Its sole strike SHALL use its authored coefficient and the declared MP and SP costs. It SHALL have no passive, healing, transfer, environment gate or freeform scale.

#### Scenario: Exact ordered composition
- **WHEN** the approved ability is read
- **THEN** its ordered effects are `damage:wind:physical` and `buff_apply:grain_rattle`, with enemy damage and enemy buff requiring hit occurrence 0; damage reads physical attack, never magic power

#### Scenario: Shared identity containment
- **WHEN** a player, NPC or wrong-species monster corruptly owns the ability
- **THEN** invocation rejects before dice, costs, buffs or practice, and player catalog/lineage admission remains denied

#### Scenario: Contact and faction remain shared
- **WHEN** an invalid, dead or positional-displaced contact target is supplied, or a valid ally is selected
- **THEN** ordinary target gates reject invalid contact; ANY faction keeps candidate selection unrestricted but enemy components deliver nothing to allies

#### Scenario: Content values remain tunable
- **WHEN** valid authored costs, coefficients, duration, modifier or drain amount change
- **THEN** integrity checks and representative consumer smoke remain green without duplicated numeric expectations; synthetic shared tests independently establish the retained mechanics

### Requirement: 穗鳴雀 timed modifier follows its authored recipient and lifetime
The `grain_rattle` mount SHALL last its authored duration in world seconds, refresh without accumulating magnitude and apply its authored negative accuracy adjustment once to each selected enemy hit by its source strike. It SHALL have debuff polarity and no DoT, ground/positional marker or action lock. Expiry/removal SHALL restore the control modifier result.

#### Scenario: Hit and miss separate delivery from payment
- **WHEN** deterministic hit and miss attempts resolve
- **THEN** only the hit applies the target buff once, including an absorbed hit and both pay the declared MP/SP costs exactly once under unmodified costs

#### Scenario: Refresh and expiry
- **WHEN** the mount is reapplied before expiry then world time passes its refreshed lifetime
- **THEN** magnitude never accumulates and the modifier is absent after expiry

#### Scenario: Content values remain tunable
- **WHEN** valid authored costs, coefficients, duration, modifier or drain amount change
- **THEN** integrity checks and representative consumer smoke remain green without duplicated numeric expectations; synthetic shared tests independently establish the retained mechanics

### Requirement: 穗鳴雀 payment and atomicity retain the shared transaction
Affordability SHALL precede dice/effects, with normal modifiers and effects-before-cost payment. Any failure SHALL restore all touched gauges, buffs and practice claims. Ecological fog, light, grain, soil or rock descriptions SHALL NOT change any combat result.

#### Scenario: Either insufficient resource rejects before effects
- **WHEN** either current resource is below its adjusted declared cost under unmodified costs
- **THEN** the cast rejects before dice, HP loss, buff application, payment or practice

#### Scenario: Late failure restores the participants
- **WHEN** a late failure follows staged damage, buff and payment
- **THEN** actor/target HP, MP/SP, buffs and practice match their pre-action values and a retry has no stale claim

#### Scenario: Environment prose cannot act as a fact
- **WHEN** otherwise equal sessions use different scene prose, habitat labels or forged fog/light/rock request facts
- **THEN** the contact action and magnitude are identical and no ecological bonus or environment-dependent damage is produced

#### Scenario: Content values remain tunable
- **WHEN** valid authored costs, coefficients, duration, modifier or drain amount change
- **THEN** integrity checks and representative consumer smoke remain green without duplicated numeric expectations; synthetic shared tests independently establish the retained mechanics

### Requirement: 穗鳴雀 public ecology reflects the completed contact kit
The registry public ecology and bestiary SHALL publish the same approved sentence edits in the proposed remaining-species design §4. Existing ecological conditions and untouched limits SHALL remain true, while current executable-deferral claims for this species SHALL be removed. Historical approval notes SHALL remain distinguishable from current implementation status.

#### Scenario: Revised prose and private boundaries
- **WHEN** public ecology, bestiary and author guides are read after implementation
- **THEN** they disclose environment-independent contact behavior, retain the design's unchanged limits, remove only this species' current deferral and expose no author-private origin or conjecture

### Requirement: 潮燈蟹 owns its approved contact resource ability
Both `tide_lamp_crab` variants SHALL own `lamp_carapace_claw` (燈甲螯擊) as a prerequisite-free single-target physical ability selectable outside combat (`usable_out_of_combat=True`) with `light` elemental-magic taxonomy and monster/species eligibility, whose damage resolution requires the existing battlefield gate. Its sole strike SHALL use its authored coefficient and the declared MP and SP costs. It SHALL have no passive, healing, transfer, environment gate or freeform scale.

#### Scenario: Exact ordered composition
- **WHEN** the approved ability is read
- **THEN** its ordered effects are `damage:light:physical` and `self_buff_apply:lamp_carapace_guard`, with enemy damage and self guard independent of hit; damage reads physical attack, never magic power

#### Scenario: Shared identity containment
- **WHEN** a player, NPC or wrong-species monster corruptly owns the ability
- **THEN** invocation rejects before dice, costs, buffs or practice, and player catalog/lineage admission remains denied

#### Scenario: Contact and faction remain shared
- **WHEN** an invalid, dead or positional-displaced contact target is supplied, or a valid ally is selected
- **THEN** ordinary target gates reject invalid contact; ANY faction keeps candidate selection unrestricted but enemy components deliver nothing to allies

#### Scenario: Content values remain tunable
- **WHEN** valid authored costs, coefficients, duration, modifier or drain amount change
- **THEN** integrity checks and representative consumer smoke remain green without duplicated numeric expectations; synthetic shared tests independently establish the retained mechanics

### Requirement: 潮燈蟹 timed modifier follows its authored recipient and lifetime
The `lamp_carapace_guard` mount SHALL last its authored duration in world seconds, refresh without accumulating magnitude and apply its authored positive defense adjustment to its caster on each affordable resolved attempt with a valid selected contact target, including a miss. Rejected or no-target requests SHALL grant nothing. It SHALL have buff polarity and no DoT, ground/positional marker or action lock. Expiry/removal SHALL restore the control modifier result.

#### Scenario: Hit and miss separate delivery from payment
- **WHEN** deterministic hit and miss attempts against a valid selected enemy resolve
- **THEN** both attempts mount caster guard once and both pay the declared MP/SP costs exactly once under unmodified costs

#### Scenario: Refresh and expiry
- **WHEN** the mount is reapplied before expiry then world time passes its refreshed lifetime
- **THEN** magnitude never accumulates and the modifier is absent after expiry

#### Scenario: Missing or invalid contact cannot grant guard
- **WHEN** the SINGLE request has no selected target or its target fails ordinary contact validation
- **THEN** the ordinary target gate rejects before guard, damage, resource payment or practice

#### Scenario: Content values remain tunable
- **WHEN** valid authored costs, coefficients, duration, modifier or drain amount change
- **THEN** integrity checks and representative consumer smoke remain green without duplicated numeric expectations; synthetic shared tests independently establish the retained mechanics

### Requirement: 潮燈蟹 payment and atomicity retain the shared transaction
Affordability SHALL precede dice/effects, with normal modifiers and effects-before-cost payment. Any failure SHALL restore all touched gauges, buffs and practice claims. Ecological fog, light, grain, soil or rock descriptions SHALL NOT change any combat result.

#### Scenario: Either insufficient resource rejects before effects
- **WHEN** either current resource is below its adjusted declared cost under unmodified costs
- **THEN** the cast rejects before dice, HP loss, buff application, payment or practice

#### Scenario: Late failure restores the participants
- **WHEN** a late failure follows staged damage, buff and payment
- **THEN** actor/target HP, MP/SP, buffs and practice match their pre-action values and a retry has no stale claim

#### Scenario: Environment prose cannot act as a fact
- **WHEN** otherwise equal sessions use different scene prose, habitat labels or forged fog/light/rock request facts
- **THEN** the contact action and magnitude are identical and no ecological bonus or environment-dependent damage is produced

#### Scenario: Content values remain tunable
- **WHEN** valid authored costs, coefficients, duration, modifier or drain amount change
- **THEN** integrity checks and representative consumer smoke remain green without duplicated numeric expectations; synthetic shared tests independently establish the retained mechanics

### Requirement: 潮燈蟹 public ecology reflects the completed contact kit
The registry public ecology and bestiary SHALL publish the same approved sentence edits in the proposed remaining-species design §5. Existing ecological conditions and untouched limits SHALL remain true, while current executable-deferral claims for this species SHALL be removed. Historical approval notes SHALL remain distinguishable from current implementation status.

#### Scenario: Revised prose and private boundaries
- **WHEN** public ecology, bestiary and author guides are read after implementation
- **THEN** they disclose environment-independent contact behavior, retain the design's unchanged limits, remove only this species' current deferral and expose no author-private origin or conjecture
