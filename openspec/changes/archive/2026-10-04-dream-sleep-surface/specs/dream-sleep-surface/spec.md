## Purpose

Offers optional collaboration after exactly one accepted sleep settlement and keeps both browser and text clients able to awaken offline.

## ADDED Requirements

### Requirement: Optional collaboration follows one accepted sleep result

Sleeping SHALL offer explicit dream collaboration without forcing ordinary sleep, rest or wait into conversation. Existing sleep safety, duration and restoration rules SHALL settle once before opening the dream. Rejected sleep SHALL NOT open it. Zero-duration accepted sleep SHALL allow entry. Interrupted sleep SHALL use only its actual committed outcome.

#### Scenario: Fully restored entry
- **WHEN** a safe fully restored player chooses collaboration
- **THEN** accepted zero-duration sleep opens the session without invented clock advance

#### Scenario: Unsafe sleep
- **WHEN** the safety gate rejects sleep
- **THEN** no dream opens and nothing settles

#### Scenario: Ordinary sleep
- **WHEN** the player declines collaboration
- **THEN** sleep completes normally without conversation

#### Scenario: Interrupted result
- **WHEN** an existing sleep path commits less than requested
- **THEN** the dream uses only that outcome and never pretends the interval completed

### Requirement: Dream departure never settles sleep again

Exchanges SHALL NOT advance world time or change physical restoration. Every exit, confirmation, draft save, reconnect or failure SHALL preserve the original committed sleep and SHALL NOT run another settlement. Later entry SHALL distinguish a new explicit sleep from resuming the old session.

#### Scenario: Offline departure
- **WHEN** generation is unavailable after entry and the player saves a draft and awakens
- **THEN** sleep tick/gauges remain exactly post-entry and no model call is required

#### Scenario: Reconnect and depart
- **WHEN** the client reconnects and ends the existing session
- **THEN** original sleep is not replayed and six-exchange progress is retained

### Requirement: Public dream surface includes the approved presentation and deterministic escape

Both browser and text surfaces SHALL expose remaining exchanges, free text only below six, explicit confirm/draft choices and awakening on all failure states. Public entry SHALL include the approved explicit presentation capability rather than publishing a sanitized/incomplete session. Command documentation and contracts SHALL match the introduced syntax and availability.

#### Scenario: Six reached on either client
- **WHEN** the session completes its sixth exchange on browser or text client
- **THEN** free text closes and confirm/draft/awaken choices remain usable offline

