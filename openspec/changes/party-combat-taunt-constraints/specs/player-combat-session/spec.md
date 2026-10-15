# Spec Delta

## ADDED Requirements

### Requirement: Taunt selects one enemy and resolves competing declarations by initiative
Eligible allied Taunt SHALL select one living eligible enemy without a success roll, cost zero MP/SP and consume the selected action. Effects SHALL activate before ordinary actions and expire at round end. For multiple taunters of one enemy, the first in the already-computed initiative sequence SHALL win.

#### Scenario: Entry order has no priority
- **WHEN** two members Taunt one enemy and the slower member confirmed first
- **THEN** the earlier initiative member wins without rerolling initiative; both members consume their actions

#### Scenario: Winner loses eligibility
- **WHEN** the winning taunter becomes knocked out, defeated, absent or fled
- **THEN** later enemy decisions are unrestricted for the remainder of the round and no losing taunter takes over

