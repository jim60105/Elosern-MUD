# dream-sleep-surface Specification

## Purpose
Offers owner-only optional collaboration while one accepted sleep receipt still holds a real sleeping posture, before recovery completes, and keeps both browser and text clients able to awaken offline.

## Requirements

### Requirement: Optional collaboration follows one accepted sleep result
Optional dream entry SHALL require explicit opt-in while the authenticated owner sleeps without possession. An eligible voluntary sleep-entry `dream: true` SHALL record enter atomically with entry, without a question. Forced sleep SHALL never enter a dream. Rejected entry or failed owner/control/receipt revalidation SHALL write nothing. Ordinary false/absent flags SHALL record no answer; camp false SHALL record decline for a sleeping owner.

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
- **WHEN** unanswered owner sleep is followed by companion possession and explicit release while the owner remains asleep
- **THEN** the question appears for the owner even with awake companions present

#### Scenario: Confirmation rechecks current control
- **WHEN** the owner wakes, possession changes or the receipt becomes stale before a dream answer arrives
- **THEN** confirmation rejects without dream or time writes and returns the current authoritative view

#### Scenario: Atomic entry opt-in
- **WHEN** the authenticated owner is selected for new voluntary sleep, no companion is possessed and true is submitted
- **THEN** entry and guarded enter commit together, the dream opens without a question, and elapsed time stays zero

#### Scenario: Consent ineligible or stale
- **WHEN** true is submitted for forced sleep, an excluded owner, companion possession, unauthenticated owner, or receipt/control changes during revalidation
- **THEN** the entire requested entry rejects without posture, receipt, decision, dream or time writes

#### Scenario: False and absent differ from camp decline
- **WHEN** equivalent owner sleeps are started with ordinary false, ordinary absent, or camp false
- **THEN** the ordinary requests record no answer and retain the question policy, while camp records explicit decline and exposes no later question

#### Scenario: No sleeping owner receipt
- **WHEN** camp recovery leaves an already-recovered owner awake while a companion sleeps
- **THEN** no owner receipt or answer is fabricated and no owner-sleep question appears

### Requirement: Dream departure never settles sleep again
Exchanges and ordinary draft saves SHALL add no time/restoration; draft save SHALL keep the dream open. Explicit confirm/awaken departure, including after draft preservation or generation failure, SHALL continue the same accepted owner sleep using only uncommitted intervals, then reconcile wake. Reconnect/cancel SHALL never open a second sleep or replay settlement. Physical interruptions SHALL remain actionable offline; completion SHALL be durable and idempotent.

#### Scenario: Offline departure
- **WHEN** generation is unavailable and the player saves a draft and awakens
- **THEN** the same sleep continues safely to its owner target or a real interruption; no model call or independent dream-time charge occurs

#### Scenario: Reconnect and depart
- **WHEN** the client reconnects and ends the existing session
- **THEN** its exchange progress and receipt persist and only uncommitted sleep time can advance

#### Scenario: Duplicate departure
- **WHEN** confirm, awaken or retry is repeated after owner sleep completion
- **THEN** neither clock, restoration nor wake notifications repeat

#### Scenario: Save and keep dreaming
- **WHEN** the player invokes ordinary draft save through text, the keepsake row or edit sheet
- **THEN** the draft persists while session remains open, owner remains asleep at the same tick and no recovery continuation is created

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
Dream collaboration SHALL bind one authenticated owner receipt before recovery and accumulate only committed intervals. Control transitions SHALL offer unanswered sleeping-owner entry without possession. An entry-time answer or camp decline SHALL suppress that receipt's question. Companion ownership SHALL never substitute for owner identity; posture entry SHALL remain distinct from elapsed completion.

#### Scenario: Recovery then dream
- **WHEN** an accepted owner sleep has zero committed elapsed time and the no-possession view is entered
- **THEN** an unanswered receipt shows the question before recovery, with explicit opt-in required and no fictitious positive-elapsed receipt

#### Scenario: Companion cannot own player dream
- **WHEN** a controlled companion sleeps or a forged request names its identity
- **THEN** no player dream is created under that NPC; only a lawful released view of the sleeping authenticated owner can enter

#### Scenario: Possessing awake companion
- **WHEN** the owner sleeps while an awake companion is possessed
- **THEN** no dream entry is offered or accepted until possession is released

### Requirement: Explicit dream answers have browser and text parity
Text `sleep [all] <mode> dream` and browser entry-time opt-in SHALL invoke the same guarded answer as `dream enter`. `dream enter`, `dream decline` and bare `dream` SHALL remain available for unanswered sleeps; browser yes/no/close SHALL share those operations. Existing say/draft/confirm/awaken SHALL retain offline escape. The standalone obsolete `sleep dream` form SHALL remain invalid; both command documents SHALL describe the explicit-mode form.

#### Scenario: Explicit answer parity
- **WHEN** text enter/decline or browser yes/no/close answers an equivalent current question
- **THEN** the same owner-bound result and continuation decision occur without a second sleep entry

### Requirement: Text dream commands reach thread choice, finalize and the change report

The text dream command SHALL offer thread choice and finalize through the same guarded operations as the browser actions. Bare `dream` SHALL show the whole current proposal, the thread it belongs to and the last change report, naming removed items. A delivered `dream say` SHALL end its output with a one-line change summary. Hints SHALL list only the operations the current stage allows. Command documentation SHALL match the syntax and availability.

#### Scenario: Thread choice by number or new
- **WHEN** the owner types the thread command with the number of an offered thread, and later with the new-story word, before any message
- **THEN** each invokes the shared thread-choice operation with that thread or with none, and the stored choice follows

#### Scenario: Thread command without argument lists choices
- **WHEN** the owner types the thread command with no argument
- **THEN** the output lists the new-story option and each offered thread with its number, and nothing is written

#### Scenario: Unknown thread argument
- **WHEN** the argument is neither an offered number, an offered thread identity nor the new-story word
- **THEN** a local refusal is shown and the shared operation is not invoked

#### Scenario: Finalize command
- **WHEN** the owner types the finalize command while conversing with no response pending
- **THEN** the shared finalize operation runs and the next state output offers draft and confirmation and no longer offers free text

#### Scenario: Bare dream shows the proposal and removed items
- **WHEN** the last settled exchange added one list item and removed another, and the owner types bare `dream`
- **THEN** the output contains every non-empty proposal field, the thread line, and a change report that names both the added and the removed item

#### Scenario: Say ends with the change summary
- **WHEN** a `dream say` is delivered, once with edits and once with none
- **THEN** the last output line is the one-line change summary, which names the changes in the first case and states that nothing changed in the second

#### Scenario: Summary replacement only after finalize
- **WHEN** the owner types the draft command with text while conversing, and again after finalize
- **THEN** the first is refused with the server's reason and the second replaces only the summary, keeping lists, requirement rows and thread

#### Scenario: Documentation parity
- **WHEN** the command documentation contract is checked
- **THEN** the documented dream syntax equals the mounted command's usage, including the thread and finalize forms
