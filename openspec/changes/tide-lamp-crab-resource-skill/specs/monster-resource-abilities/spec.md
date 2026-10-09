# Spec Delta

## MODIFIED Requirements

### Requirement: Crocodile ecology documents implemented limits
Public crocodile ecology and author notes SHALL describe implemented contact MP pressure with no HP healing, remote drain or permanent magic loss. Assertions that crocodile mechanics/numbers remain deferred SHALL be removed. Delivered approved species SHALL use their authored kits and revised boundaries; still-deferred species are ridge_burrow_hare, rock_echo_goat, fog_mane_lynx.

#### Scenario: Public projection and notes agree
- **WHEN** the registry, bestiary and relevant author guidance are read
- **THEN** crocodile mechanics and limits agree without exposing private fields, inventing unapproved species abilities or claiming recalibrated grades

## ADDED Requirements

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
The `lamp_carapace_guard` mount SHALL last 20 world seconds, refresh without accumulating magnitude and apply `defense: 2` to its caster on each affordable resolved attempt. It SHALL have buff polarity and no DoT, ground/positional marker or action lock. Expiry/removal SHALL restore the control modifier result.

#### Scenario: Hit and miss separate delivery from payment
- **WHEN** deterministic hit and miss attempts resolve
- **THEN** both attempts mount caster guard once and both pay 10 MP/3 SP exactly once under unmodified costs

#### Scenario: Refresh and expiry
- **WHEN** the mount is reapplied before expiry then world time passes its refreshed lifetime
- **THEN** magnitude never accumulates and the modifier is absent after expiry

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
