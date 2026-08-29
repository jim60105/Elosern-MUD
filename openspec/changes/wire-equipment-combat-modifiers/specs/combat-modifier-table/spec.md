## ADDED Requirements

### Requirement: Worn equipment merges into the merged bundle of both evaluation paths

The deterministic core SHALL expose one pure equipment-adjustment accessor
that reads the fail-closed normalized equipment mapping and folds each worn
item's rulebook combat values into a single adjustment bundle. Both
`evaluate_combat_modifiers()` and the no-create preview variant SHALL append
that bundle after rule-table matching, so to-hit, damage, estimation,
preview, cost, and resist consumers share one effective bundle. Malformed
equipment storage SHALL yield an empty bundle: resolution SHALL proceed on
base stats while mutation stays blocked by the existing preflight. The
accessor and both evaluation paths SHALL NOT write any entity state.

#### Scenario: Worn gear lands in combat resolution

- **WHEN** an actor wearing an item granting `atk_phys +5` strikes under a
  fixed seed
- **THEN** the damage magnitude reflects the merged bundle including the
  equipment contribution, identical to what the preview path predicted

#### Scenario: Malformed equipment storage falls back to base stats

- **WHEN** equipment storage is malformed and a combat resolution evaluates
  the actor
- **THEN** the evaluation returns the rule-table bundle unchanged (no
  equipment contribution, no error raised) while every equipment mutation
  still fails preflight

#### Scenario: Preview and revalidation agree on equipment costs

- **WHEN** an actor wearing an `mp_cost −10%` accessory previews a cast and
  then resolves it without state change between the two reads
- **THEN** both paths apply the identical adjusted cost

### Requirement: Adjusted agility never resolves negative

Every consumer path that derives a modifier-adjusted effective agility for
to-hit, overwhelm estimation, resist scoring, or the flee contest SHALL
clamp the adjusted value at 0 after percentage modifiers (skill multipliers,
rules, and equipment) are applied. Initiative order keeps its documented
raw-agility exception unchanged.

#### Scenario: Heavy gear cannot invert the to-hit inequality

- **WHEN** a defender's equipment and rules drive raw modifier-adjusted
  agility below zero
- **THEN** the to-hit formula consumes agility 0, and the required roll is
  identical to the one computed for a defender with base agility 0

#### Scenario: Negative agility cannot speed a flee attempt

- **WHEN** a fleeing actor's modifiers drive raw adjusted agility below zero
- **THEN** the flee contest scores the actor with agility 0
