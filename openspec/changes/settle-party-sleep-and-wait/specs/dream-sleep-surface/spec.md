# Spec Delta

## MODIFIED Requirements

### Requirement: Optional collaboration follows one accepted sleep result

Sleeping SHALL offer explicit dream collaboration without forcing ordinary sleep, rest or wait into conversation. Existing sleep safety, duration and restoration rules SHALL settle once before opening the dream. Rejected sleep SHALL NOT open it. Entry SHALL require a real positive elapsed accepted voluntary sleep result; posture entry or zero-duration recovery SHALL NOT open a dream. Forced sleep SHALL never open one automatically. Interrupted sleep SHALL use only its actual committed outcome.

#### Scenario: Fully restored entry
- **WHEN** a safe fully restored player chooses collaboration without elapsed sleep
- **THEN** no dream opens and no clock advance is invented

#### Scenario: Unsafe sleep
- **WHEN** the safety gate rejects sleep
- **THEN** no dream opens and nothing settles

#### Scenario: Ordinary sleep
- **WHEN** the player declines collaboration
- **THEN** sleep completes normally without conversation

#### Scenario: Interrupted result
- **WHEN** an existing sleep path commits less than requested
- **THEN** the dream uses only that outcome and never pretends the interval completed

## ADDED Requirements

### Requirement: Dream collaboration consumes the committed elapsed result
Dream collaboration SHALL use the real accepted voluntary-sleep receipt, including interruptions. Entry, later discussion and departure SHALL never repeat mental or ordinary restoration. Handoff SHALL be offered at posture entry before any requested elapsed sleep and before any dream offer.

#### Scenario: Recovery then dream
- **WHEN** the player explicitly continues sleep and a real elapsed result commits
- **THEN** only then may optional collaboration use that receipt once; offline generation failure leaves deterministic recovery and waking controls available

