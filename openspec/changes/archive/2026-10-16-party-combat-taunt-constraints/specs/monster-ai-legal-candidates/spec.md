# Spec Delta

## ADDED Requirements

### Requirement: Taunt constrains legal single-hostile target generation before estimation
For an active Taunt winner legal for an enemy single-target hostile action, candidate generation, estimation and final execution SHALL constrain that action to the winner. Hostility SHALL use the authoritative typed-effect classification. Existing range, recipient, seal and displacement restrictions SHALL remain authoritative. Effects SHALL NOT be silently redirected after selection.

#### Scenario: Non-damage harm and legal limits
- **WHEN** an enemy can choose a hostile debuff and the taunter is ordinarily legal for it
- **THEN** the candidate targets the taunter before utility scoring; if range or a mandatory seal restriction excludes that taunter, Taunt grants no exception

#### Scenario: Enemy alternatives
- **WHEN** a taunted enemy chooses an AREA action, self/allied benefit or flee
- **THEN** ordinary legal options remain available and Taunt does not force an attack or redirect area effects

#### Scenario: Suppressed winner
- **WHEN** the winner fell before the next enemy decision
- **THEN** candidate generation and estimation use ordinary legal target rules without promoting a losing declaration

