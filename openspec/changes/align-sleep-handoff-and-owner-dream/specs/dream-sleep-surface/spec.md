# Spec Delta

## MODIFIED Requirements

### Requirement: Optional collaboration follows one accepted sleep result
Optional dream entry SHALL be asked while the authenticated owner still sleeps and no companion is possessed, before recovery completes. Accepted zero-time entry SHALL qualify without claiming completed sleep. Other companions SHALL need no sleeping prerequisite. Rejected sleep SHALL open no dream. Any sleep type SHALL require explicit opt-in; forced sleep SHALL never auto-enter. Confirmation SHALL revalidate owner, control and accepted receipt.

#### Scenario: Fully restored entry
- **WHEN** until-recovered sleep has an already-met target
- **THEN** no elapsed sleep is invented and the reconciled awake owner has no dream offer; an accepted positive duration sleep can still offer while asleep

#### Scenario: Unsafe sleep
- **WHEN** the safety gate rejects voluntary sleep
- **THEN** no dream opens and nothing settles

#### Scenario: Ordinary sleep
- **WHEN** the player declines or closes the question
- **THEN** no dream opens and the same sleep remains available for recovery; the all-asleep owner continuation policy applies

#### Scenario: Interrupted result
- **WHEN** real interaction interrupts the same accepted sleep
- **THEN** only committed progress is retained and resumption never invents or repeats the interval

#### Scenario: Released sleeping owner
- **WHEN** owner sleep is followed by companion possession and explicit release while the owner remains asleep
- **THEN** the question appears for the owner even with awake companions present

#### Scenario: Confirmation rechecks current control
- **WHEN** the owner wakes, possession changes or the receipt becomes stale before a dream answer arrives
- **THEN** confirmation rejects without dream or time writes and returns the current authoritative view

### Requirement: Dream departure never settles sleep again
Dream exchanges SHALL add no independent time or restoration. Confirm, draft, awaken and failure departure SHALL resume or finish the same accepted owner sleep using only uncommitted clock intervals, then reconcile wake. Reconnect/cancel SHALL never open a second sleep or replay settlement. Receipt completion SHALL be durable and idempotent; physical interruptions SHALL remain truthful and actionable offline.

#### Scenario: Offline departure
- **WHEN** generation is unavailable and the player saves a draft and awakens
- **THEN** the same sleep continues safely to its owner target or a real interruption; no model call or independent dream-time charge occurs

#### Scenario: Reconnect and depart
- **WHEN** the client reconnects and ends the existing session
- **THEN** its exchange progress and receipt persist and only uncommitted sleep time can advance

#### Scenario: Duplicate departure
- **WHEN** confirm, awaken or retry is repeated after owner sleep completion
- **THEN** neither clock, restoration nor wake notifications repeat

### Requirement: Confirmed dream handoff returns to playable waking surfaces
Confirmation SHALL close dream interaction and acknowledge receipt distinct from arrangement. The same accepted sleep SHALL safely complete before ordinary owner actions are authorized. Dispatch and generation SHALL add no time or sleep settlement. Physical interruption SHALL expose status, lawful handoff and deterministic recovery without requiring generation; ordinary play SHALL remain available after wake while generation waits or fails.

#### Scenario: Confirmation is a receipt
- **WHEN** a player confirms a valid direction on either surface
- **THEN** the dream closes, feedback claims receipt rather than an existing NPC/quest, and the same sleep resumes before waking play

#### Scenario: Waiting while offline mechanics run
- **WHEN** model services are disabled after confirmation and safe owner recovery completes
- **THEN** deterministic movement/quests are available under normal gates without another sleep or generation charge

### Requirement: Dream collaboration consumes the committed elapsed result
Dream collaboration SHALL associate the authenticated owner's single accepted sleep receipt before recovery finishes and accumulate only actual committed intervals. Control-view transitions SHALL offer entry while the owner sleeps and no companion is possessed. Companion ownership SHALL never substitute for player ownership. Posture entry SHALL remain distinct from elapsed completion.

#### Scenario: Recovery then dream
- **WHEN** an accepted owner sleep has zero committed elapsed time and the no-possession view is entered
- **THEN** the question appears before recovery, with explicit opt-in required and no fictitious positive-elapsed receipt

#### Scenario: Companion cannot own player dream
- **WHEN** a controlled companion sleeps or a forged request names its identity
- **THEN** no player dream is created under that NPC; only a lawful released view of the sleeping authenticated owner can enter

#### Scenario: Possessing awake companion
- **WHEN** the owner sleeps while an awake companion is possessed
- **THEN** no dream entry is offered or accepted until possession is released

## ADDED Requirements

### Requirement: Explicit dream answers have browser and text parity
Text SHALL expose `dream enter` and `dream decline` for the current accepted owner-sleep question, with bare `dream` showing the pending question or associated state. Browser yes/no/close SHALL invoke the same guarded answer operation. Existing say/draft/confirm/awaken SHALL retain offline escape and bounded exchange behavior. Obsolete `sleep dream` SHALL be removed from callers and both command documents.

#### Scenario: Explicit answer parity
- **WHEN** text enter/decline or browser yes/no/close answers an equivalent current question
- **THEN** the same owner-bound result and continuation decision occur without a second sleep entry
