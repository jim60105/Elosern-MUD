## MODIFIED Requirements

### Requirement: Each displayed stat matches its named authoritative computation

For every displayed stat, the panel's `effective` SHALL equal the shipped authoritative computation named for it under identical inputs: attack/defense via the merged-bundle flat/pct with skill mults and single final rounding; agility identical plus the ≥ 0 floor (initiative's raw-agility exception is explicitly out of parity scope); `magic_power` via the shipped skill effective-value arithmetic's rounding form; gauge maximum via the shipped gauge reader form. Behavior tests SHALL pin each stat against ITS named computation; consumer-specific post-effective floors (to-hit, heal) are documented non-contradictions, not parity targets.

#### Scenario: Panel defense equals the defense used in resolution

- **WHEN** an actor with skill mults, a matched condition rule, and worn gear has both a panel breakdown and a live defense evaluation from the same fixed inputs
- **THEN** both show the identical defense value

#### Scenario: Heavy-gear agility displays floored

- **WHEN** modifiers drive raw adjusted agility below zero
- **THEN** the panel shows agility 0, matching the consumer-side floor

#### Scenario: Gauge ceiling layers include the equipment cap

- **WHEN** an actor wearing the `hp +15` plate requests the HP breakdown
- **THEN** the maximum decomposes over the stored base plus an equipment flat layer of 15 and the panel maximum equals the heal-clamp ceiling
