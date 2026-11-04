# Spec Delta

## ADDED Requirements

### Requirement: Combat state preserves individual identity across repeated labels
Interactive combat SHALL keep participant, selection, action, effect, AI and outcome state distinct by persistent individual identity across renames and restoration.

#### Scenario: Independent selected recipient
- **WHEN** A, A and B are admitted and a saved action selects the second A before rename and reload
- **THEN** the same second A receives the effect; the first A keeps its independent HP, resources and state

#### Scenario: Independent removal and credit
- **WHEN** one same-label A flees or is defeated and its defeat event is delivered twice
- **THEN** only that ID leaves eligibility and each applicable quest counts its defeat once; the other A remains independent

#### Scenario: Invalid duplicate identity
- **WHEN** one entity is supplied twice
- **THEN** admission rejects before any session or resource write

#### Scenario: Atomic identity state
- **WHEN** a later round write fails after a real recipient mutation
- **THEN** durable reload and in-process participant, observation and draft state equal the pre-round state

