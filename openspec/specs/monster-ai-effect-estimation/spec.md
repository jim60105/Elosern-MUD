# monster-ai-effect-estimation Specification

## Purpose
Estimate supported attack health effects with settlement arithmetic and conservative outcome models. This capability defines observable behavior at the monster decision boundary.

## Requirements

### Requirement: Damage estimates use settlement arithmetic without settlement
Estimates SHALL reuse scalar base damage, potency, scale, mitigation, strike count and cost rules. They SHALL analytically average supported d100 ranges with the actual hit-gate topology and SHALL NOT roll dice, invoke effect handlers, pay costs, install buffs or emit events.

#### Scenario: Shared hit multi strike
- **WHEN** a skill has several strikes sharing one hit gate
- **THEN** the estimate uses that gate once and matches independently calculated outcome ranges without assuming independent hits

#### Scenario: Ordered capped damage
- **WHEN** later effects affect an already damaged recipient
- **THEN** their projected loss is capped by remaining projected HP and never counted against the original HP twice

### Requirement: Uncertain effects have conservative explicit limits
Unsupported harmful outcomes SHALL exclude a candidate. Unknown harmless benefits SHALL contribute zero with diagnostics. Uncertain beneficial conditionals SHALL be omitted. Known shielding/diversion limits SHALL reduce estimates; finishing credit SHALL require a supported outcome model or guaranteed-on-hit lower bound. A supported buff or control mount SHALL be valued by its marginal modifier difference over one next action opportunity; unvaluable modifiers SHALL be reported, not invented.

#### Scenario: Approximate reactions
- **WHEN** reactions, diversion or multi-strike interactions cannot be exactly modeled
- **THEN** the trace labels conservative limits and cannot claim a certain knockout because average damage exceeds current HP

#### Scenario: Conditional recovery
- **WHEN** a hit-dependent drain can miss or requested damage exceeds remaining HP
- **THEN** failed prerequisites contribute no recovery; recovery never exceeds projected actual loss

#### Scenario: Marginal mount
- **WHEN** a supported mount would be reapplied, has expired, is outweighed by an effect its recipient already holds, is capped by the merge, or lands on a recipient with no action opportunity before expiry
- **THEN** its marginal value is zero with the limitation recorded, and an unvaluable modifier contributes nothing instead of an invented amount

### Requirement: Health and resource features are bounded and signed
Features SHALL be in 0..1 with explicit benefit/harm direction. Enemy damage and allied healing SHALL be positive; ally damage and enemy healing SHALL be negative. Projected effects SHALL be capped by capacity; zero denominators SHALL contribute zero. A control feature SHALL also be bounded in 0..1 with benefit direction, summed from the beneficial marginal value of supported mounts. Non-finite features SHALL be typed invalid states.

#### Scenario: Feature normalization
- **WHEN** eligible live faction maximum HP sums are computed
- **THEN** damage and recovery normalize by the affected faction sum bounded below by one; waste is excess nominal effect divided by total absolute nominal health magnitude

#### Scenario: Finishing and cost
- **WHEN** a candidate charges one or more MP, HP, nutrition or arousal pools
- **THEN** finishing is supported hostile knockout likelihood divided by live enemy count; cost is the mean charged fraction of current spendable pools using scale and proficiency

#### Scenario: Control normalization
- **WHEN** a supported mount changes a recipient's action opportunities, offensive impact, prevented incoming health or resource economy
- **THEN** the change is the difference between that recipient's modifier bundle now and with the mount applied, normalized by the faction's own baseline opportunities or by the faction capacity the change helps or threatens
