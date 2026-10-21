# Spec Delta

## ADDED Requirements

### Requirement: Monster decisions observe sleep inability without losing targets
Enemy observations and legal candidates SHALL represent sleeping opponents as present living unable-to-act targets under normal targeting rules. Sleep SHALL not imply death, absence, invulnerability or an automatic victory. AI and presentation SHALL write no fatigue state.

#### Scenario: Sleep-aware decision
- **WHEN** an enemy evaluates a mixed awake/sleeping allied roster
- **THEN** the sleeper remains a legal target with truthful inability-to-act observation; ordinary skill restrictions still apply

