# Spec Delta

Archive handoff: after syncing this delta, re-list canonical IDs and annotate every new or changed substantive requirement test. Existing requirement headings are intentionally unchanged; historical titles do not preserve superseded mode or dice behavior.

## MODIFIED Requirements

### Requirement: Damage-estimation surfaces mirror the live adjusted damage math
Overwhelm expected damage SHALL retain live adjusted attack and defense terms and its existing conservative shape. Reflex skill estimates SHALL read the actor own adjusted school attacking stat, including own buffs and modifier bundles, multiplied by primary damage coefficient and recipient count. Reflex SHALL omit defender terms and hit chance. Deliberation estimates and raw effective_power ranking SHALL remain unchanged.

#### Scenario: Overwhelm expected damage includes the bundle adjustments
- **WHEN** synthetic attacker and defender each receive a flat modifier bonus of 5
- **THEN** overwhelm uses adjusted attack and defense with those bonuses and its unchanged estimator shape

#### Scenario: Monster skill choice ranks physical attacks with their atk_phys bonus
- **WHEN** synthetic physical and magic candidates compete and the actor receives a relevant own attacking-stat modifier or buff
- **THEN** the affected school E includes that adjustment; the other school retains its own independent adjusted value

#### Scenario: Defender changes do not change reflex scores
- **WHEN** defender defense or agility changes while actor inputs, coefficients and living enemy count remain fixed
- **THEN** reflex E and probabilities remain unchanged, even though actual settlement can differ

#### Scenario: The power-ratio heuristic keeps ranking on raw stats
- **WHEN** effective_power ranks the same entities
- **THEN** it continues using its raw effective-stat contract

#### Scenario: Only the stat terms mirror live resolution
- **WHEN** overwhelm expected damage and reflex own-output estimation read adjusted attacking stats
- **THEN** overwhelm retains its existing conservative shape and adjusted defense; reflex uses exact A*c*R without a defender term or hit chance

#### Scenario: Numerical mechanism examples are synthetic
- **WHEN** these estimator arithmetic scenarios are exercised
- **THEN** fixed synthetic bonuses and coefficients supply independently known results without fixing shipped balance values
