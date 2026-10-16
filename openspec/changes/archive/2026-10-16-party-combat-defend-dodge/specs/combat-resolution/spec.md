# Spec Delta

## MODIFIED Requirements

### Requirement: To-hit uses a recalibrated defender constant of 51, not the design doc's original 60
`world/rules/rulebook/combat.yaml` SHALL declare `to_hit.defender_constant: 51`. With no active
Dodge adjustment, a hit SHALL occur when `roll_d100() + attacker_effective_agility >=
defender_constant + defender_effective_agility`, where both agility values come from
`SkillHandler.effective_value("agility")` (change 5), adjusted by the entity's `agility`
percentage modifier from `evaluate_combat_modifiers()` (change 6), plus the attacker bundle's
`accuracy` modifier.

#### Scenario: Exact agility parity yields a 50% hit chance
- **WHEN** attacker and defender have identical effective agility (after modifiers) and 10,000
  `roll_d100()`-driven to-hit checks are run
- **THEN** the observed hit rate is within a small statistical tolerance of 50%, matching
  `(50 + 0) / 100` from design.md D-2's derivation

#### Scenario: A cross-race agility gap saturates to a guaranteed outcome
- **WHEN** a to-hit check is run with an attacker/defender effective-agility difference of 50 or more
  in either direction
- **THEN** the hit rate is exactly 0% (attacker's agility deficit) or exactly 100% (attacker's agility
  surplus), with no roll capable of changing the outcome

#### Scenario: A same-tier or adjacent-tier agility gap never fully saturates
- **WHEN** a to-hit check is run with an attacker/defender effective-agility difference within the
  range any two `STATIC_TIER_REGISTRY` entries for the same race produce (at most 30 points)
- **THEN** the resulting hit rate is strictly between 0% and 100%

#### Scenario: A natural roll of 100 does not override a saturated miss
- **WHEN** an attacker whose effective-agility deficit against the defender is 50 or more rolls the
  maximum possible value on `roll_d100()`
- **THEN** the action still misses — no natural-roll override exists that can defeat the deliberate,
  calibrated saturation from design.md D-2

#### Scenario: Dodge changes the threshold and the resulting solid-hit margin
- **WHEN** a defender declared Dodge for the active round
- **THEN** the shared hit margin subtracts the configured defender threshold bonus, initially 25; critical still requires a landed raw-100 hit

## ADDED Requirements

### Requirement: Defend and Dodge consume one zero-resource round-start action
Eligible allied Defend and Dodge declarations SHALL cost zero MP/SP, consume their selected action and activate before ordinary initiative actions after complete preflight. They SHALL have no cooldown, expire at round end and never stack across rounds. Enemies SHALL gain neither as a new basic action.

#### Scenario: Slow defending actor
- **WHEN** a slow ally declares Defend before a faster enemy acts
- **THEN** the reduction applies to eligible enemy direct damage before the ally ordinary initiative position and the ally receives no extra selected attack

#### Scenario: Expiry and rollback
- **WHEN** a round ends, reconnect occurs after completion or a round technically fails
- **THEN** no activated tactical effect leaks as a durable buff; failed-round state restores while the selected draft remains recoverable

### Requirement: Defend reduces eligible final scaled direct damage
Defend SHALL reduce eligible direct damage by the rulebook reduction, initially 35%, after normal mitigation, riders and authored magnitude. The reduced result SHALL be floored and the final hit floor reapplied. Damaging upkeep and explicitly defense-bypassing damage SHALL be exempt; zero or low defense alone SHALL NOT be exempt.

#### Scenario: Independent final reduction
- **WHEN** a successful direct strike has ordinary scaled damage 40 and Defend reduction is 0.35
- **THEN** final staged damage is 26 before existing downstream diversion and nonlethal projection

#### Scenario: Bypass and upkeep
- **WHEN** a defended actor receives explicit defense bypass or a damaging upkeep tick
- **THEN** no Defend reduction is applied; an ordinary hit against zero defense still receives Defend

### Requirement: Dodge affects only shared hit checks and their margins
Dodge SHALL add the rulebook threshold bonus, initially 25, to the defender-side hit threshold and resulting margin calculation. It SHALL NOT reduce landed damage, create new miss rolls, change initiative or improve retreat. Raw-roll critical requires landing. Per-target AREA hit checks SHALL apply Dodge separately.

#### Scenario: AREA and unchecked damage
- **WHEN** an AREA attack checks each recipient or a damage effect has no hit check
- **THEN** each actual recipient check uses its own Dodge adjustment and unchecked damage receives no invented roll

#### Scenario: Estimator agreement
- **WHEN** a monster estimates a hit against a Defend or Dodge declaration
- **THEN** its shared arithmetic matches settlement and does not grant extra enemy basic tactics

