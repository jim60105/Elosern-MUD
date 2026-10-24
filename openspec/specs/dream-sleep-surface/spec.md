# dream-sleep-surface Specification

## Purpose
Offers owner-only optional collaboration while one accepted sleep receipt still holds a real sleeping posture, before recovery completes, and keeps both browser and text clients able to awaken offline.

## Requirements

### Requirement: Optional collaboration follows one accepted sleep result

Optional dream entry SHALL be asked while the authenticated owner still sleeps and no companion is possessed, before recovery completes. Accepted zero-time entry SHALL qualify without claiming completed sleep. Other companions SHALL need no sleeping prerequisite. Rejected sleep SHALL open no dream. Any sleep type SHALL require explicit opt-in; forced sleep SHALL never auto-enter. Confirmation SHALL revalidate owner, control and accepted receipt.

#### Scenario: Fully restored entry
- **WHEN** until-recovered sleep has an already-met target
- **THEN** no elapsed sleep is invented and the reconciled awake owner has no dream offer; an accepted positive duration sleep can still offer while asleep

#### Scenario: Unsafe sleep
- **WHEN** the safety gate rejects sleep
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

Exchanges and ordinary draft saves SHALL add no time/restoration; draft save SHALL keep the dream open. Explicit confirm/awaken departure, including after draft preservation or generation failure, SHALL continue the same accepted owner sleep using only uncommitted intervals, then reconcile wake. Reconnect/cancel SHALL never open a second sleep or replay settlement. Physical interruptions SHALL remain actionable offline; completion SHALL be durable and idempotent.

#### Scenario: Offline departure
- **WHEN** generation is unavailable after entry and the player saves a draft and awakens
- **THEN** the same sleep continues safely to its owner target or a real interruption; no model call or independent dream-time charge occurs

#### Scenario: Reconnect and depart
- **WHEN** the client reconnects and ends the existing session
- **THEN** original sleep is not replayed and six-exchange progress is retained

### Requirement: Public dream surface includes the approved presentation and deterministic escape

Both browser and text surfaces SHALL expose remaining exchanges, free text only below six, explicit confirm/draft choices and awakening on all failure states. Public entry SHALL include the approved explicit presentation capability rather than publishing a sanitized/incomplete session. Command documentation and contracts SHALL match the introduced syntax and availability.

#### Scenario: Six reached on either client
- **WHEN** the session completes its sixth exchange on browser or text client
- **THEN** free text closes and confirm/draft/awaken choices remain usable offline

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

### Requirement: Explicit dream answers have browser and text parity
Text SHALL expose `dream enter` and `dream decline` for the current accepted owner-sleep question, with bare `dream` showing the pending question or associated state. Browser yes/no/close SHALL invoke the same guarded answer operation. Existing say/draft/confirm/awaken SHALL retain offline escape and bounded exchange behavior. Obsolete `sleep dream` SHALL be removed from callers and both command documents.

#### Scenario: Explicit answer parity
- **WHEN** text enter/decline or browser yes/no/close answers an equivalent current question
- **THEN** the same owner-bound result and continuation decision occur without a second sleep entry
