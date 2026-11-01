## MODIFIED Requirements

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
