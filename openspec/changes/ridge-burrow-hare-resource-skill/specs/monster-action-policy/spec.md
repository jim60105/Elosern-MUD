# Spec Delta

## ADDED Requirements

### Requirement: 築埂兔 contact kit uses existing first-owned policy and fallback
Both variants SHALL bind `instinctive` with first-owned skill selection, lowest-current-HP targets, no area preference and flee fraction 0.35. Affordable eligible `ridge_bracing_kick` SHALL precede basic_attack; insufficient MP or SP SHALL fall back to ordinary attack without utility planning. Existing initiative-time resolver and target gates SHALL remain authoritative.

#### Scenario: Preferred skill and either exhaustion axis
- **WHEN** real sessions resolve an affordable special attack then separately exhaust MP and SP
- **THEN** the special action resolves first and each exhausted case resolves basic_attack next, without changing any other archetype or tier default

#### Scenario: Flee retains priority at its inclusive threshold
- **WHEN** a variant reaches HP fraction 0.35 with living enemies
- **THEN** the existing flee request precedes attack selection and uses the normal disengage resolver, with no teleportation or special burrow escape

#### Scenario: Targets and late state changes remain shared
- **WHEN** all valid enemies are displaced or eligibility/affordability changes after initiative
- **THEN** ordinary positional selection and final resolver gates apply with no creature-specific branch or new decision dice
