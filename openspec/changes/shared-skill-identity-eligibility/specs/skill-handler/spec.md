# Spec Delta

## ADDED Requirements

### Requirement: Identity-ineligible owned and conferred passive effects are inert
Passive queries SHALL apply identity qualification to directly owned and conferred skill effects before computing any trait or rule contribution. Reads SHALL create no handlers or persistent state, and unrestricted shared skills SHALL retain their existing behavior.

#### Scenario: Misconfigured passive has no influence
- **WHEN** an entity has an identity-ineligible owned or conferred multiplier/rule-table passive
- **THEN** effective traits and rule-table values equal the control without that passive

#### Scenario: Eligible reuse remains unchanged
- **WHEN** eligible character and monster owners read an unrestricted synthetic passive
- **THEN** both retain its existing effect and no persistent state changes

