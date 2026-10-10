# Spec Delta

## MODIFIED Requirements

### Requirement: Authored crocodile behavior uses the existing first-owned strategy
The crocodile kit SHALL bind a reusable existing-vocabulary profile using first-owned skill choice, lowest-current-HP targets, no area preference and the authored flee fraction. The bite SHALL precede innate attack. Ineligible or MP/SP-unaffordable bites SHALL fall back to an available ordinary attack.

#### Scenario: Resource exhaustion is ordinary fallback
- **WHEN** formal crocodile combat exhausts either payable bite resource
- **THEN** the next policy action resolves an ordinary attack without a new utility planner

#### Scenario: Current combat boundaries remain authoritative
- **WHEN** targets move, die or are knocked out before resolution or the crocodile reaches its flee threshold
- **THEN** existing close-range/displacement, living-target, knockout and flee rules apply; other profiles and target choices remain unchanged

### Requirement: 穗鳴雀 contact kit uses existing first-owned policy and fallback
Both variants SHALL bind `instinctive` with first-owned skill selection, lowest-current-HP targets, no area preference and the authored flee fraction. Affordable eligible `grain_shaking_peck` SHALL precede basic_attack; insufficient MP or SP SHALL fall back to ordinary attack without utility planning. Existing initiative-time resolver and target gates SHALL remain authoritative.

#### Scenario: Preferred skill and either exhaustion axis
- **WHEN** real sessions resolve an affordable special attack then separately exhaust MP and SP
- **THEN** the special action resolves first and each exhausted case resolves basic_attack next, without changing any other archetype or tier default

#### Scenario: Flee retains priority at its inclusive threshold
- **WHEN** a variant reaches its configured inclusive HP-fraction boundary with living enemies
- **THEN** the existing flee request precedes attack selection and uses the normal disengage resolver, with no teleportation or special burrow escape

#### Scenario: Targets and late state changes remain shared
- **WHEN** all valid enemies are displaced or eligibility/affordability changes after initiative
- **THEN** ordinary positional selection and final resolver gates apply with no creature-specific branch or new decision dice

### Requirement: 潮燈蟹 contact kit uses existing first-owned policy and fallback
Both variants SHALL bind `instinctive` with first-owned skill selection, lowest-current-HP targets, no area preference and the authored flee fraction. Affordable eligible `lamp_carapace_claw` SHALL precede basic_attack; insufficient MP or SP SHALL fall back to ordinary attack without utility planning. Existing initiative-time resolver and target gates SHALL remain authoritative.

#### Scenario: Preferred skill and either exhaustion axis
- **WHEN** real sessions resolve an affordable special attack then separately exhaust MP and SP
- **THEN** the special action resolves first and each exhausted case resolves basic_attack next, without changing any other archetype or tier default

#### Scenario: Flee retains priority at its inclusive threshold
- **WHEN** a variant reaches its configured inclusive HP-fraction boundary with living enemies
- **THEN** the existing flee request precedes attack selection and uses the normal disengage resolver, with no teleportation or special burrow escape

#### Scenario: Targets and late state changes remain shared
- **WHEN** all valid enemies are displaced or eligibility/affordability changes after initiative
- **THEN** ordinary positional selection and final resolver gates apply with no creature-specific branch or new decision dice
