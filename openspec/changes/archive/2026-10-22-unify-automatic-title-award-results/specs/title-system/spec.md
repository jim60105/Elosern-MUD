# Spec Delta

## ADDED Requirements

### Requirement: Automatic built-in-title awards report occurrence-linked grants
All automatic built-in-title awards SHALL use one deterministic award contract reporting the source occurrence, recipient identity and newly granted title identity. Grant conditions and benefits SHALL remain unchanged. Generated-epithet acceptance SHALL remain separate.

#### Scenario: Several grants retain attribution
- **WHEN** one occurrence grants several built-in titles to two recipients
- **THEN** each new grant carries its source, recipient and title identity, including an automatically authored starter epithet

#### Scenario: Existing ownership is not a new grant
- **WHEN** a new occurrence tries to grant an already-owned title
- **THEN** that title contributes no award result

#### Scenario: Future producer uses the contract
- **WHEN** a synthetic future event grants a synthetic built-in title
- **THEN** it produces the same result contract without nomination-specific event classifications

#### Scenario: Consent is separate
- **WHEN** a player accepts a generated epithet
- **THEN** no automatic built-in-title award result is emitted

### Requirement: Award evidence finalizes atomically and survives replay
Title writes, automatic award results and source evidence SHALL share the source settlement transaction. Award results SHALL be finalized before immutable event persistence. Replaying a committed occurrence SHALL retain its original grant results and SHALL NOT replace them with an empty replay result.

#### Scenario: Rollback after writes
- **WHEN** a fault follows gameplay, title, award and narrative writes before outer commit
- **THEN** all durable and cached gameplay/title state and related records return to their prior values

#### Scenario: Replay keeps suppression evidence
- **WHEN** the same committed source settles again after its title is already owned
- **THEN** one source remains and its original nonempty award results are returned unchanged

