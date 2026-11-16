## MODIFIED Requirements

### Requirement: Startup recovery rescans explicit unique portrait policies
Startup SHALL recover explicit named portrait policies through the shared automatic gallery guard, including official-default suppression. Invalid ages SHALL reject deterministically with a bounded diagnostic and no persisted rejection marker. Repeated attempts on unchanged invalid data SHALL reject identically.

#### Scenario: A named policy with an empty gallery is recovered at startup
- **WHEN** an eligible character has an explicit named portrait policy, an empty gallery, no in-flight job and no satisfying official default after a restart
- **THEN** exactly one gallery generation is requested and no gameplay is rolled back

#### Scenario: A subject that already has a card is not regenerated
- **WHEN** recovery runs for a character whose gallery already holds a card, or whose generation is already in flight
- **THEN** nothing is requested and the gallery is unchanged

#### Scenario: An ineligible recovered subject is skipped deterministically
- **WHEN** a character with an explicit named policy fails the canonical-age check during recovery
- **THEN** no record is created, a named diagnostic is logged, and the same policy is not retried by a
  later recovery pass without re-running the gate

#### Scenario: The gallery satisfies recovery
- **WHEN** recovery evaluates a subject whose gallery already holds at least one card, or whose
  gallery generation is already in flight
- **THEN** the subject is left alone — the gallery satisfies the recovery

#### Scenario: A recovery request is one unbound auto-generated card
- **WHEN** recovery proceeds for a subject, which happens only for an empty gallery with no
  in-flight job and no satisfying official default after declared eligibility checks
- **THEN** the requested image is one unbound auto-generated card, never a classic asset record

### Requirement: Successful player creation and validated import schedule an eligible unique portrait through transaction.on_commit
Creation and validated import SHALL establish named portrait policy transactionally. Unless creation explicitly skips generation, they SHALL schedule the guarded gallery callback through transaction.on_commit; actual enqueue SHALL require eligibility and unsatisfied gallery/job/official state. Rejected or rolled-back transactions SHALL emit no callback or job.

#### Scenario: A committed creation schedules exactly one portrait ensure
- **WHEN** player creation commits successfully with generation not explicitly skipped
- **THEN** the character carries an explicit named policy with a stable key and exactly one
  post-commit portrait ensure is scheduled

#### Scenario: A rolled-back creation emits no job
- **WHEN** a creation attempt fails and its transaction rolls back
- **THEN** no portrait policy is persisted and no post-commit portrait job is emitted

#### Scenario: A validated import schedules per eligible record
- **WHEN** an all-or-nothing import batch commits with validated named records carrying canonical ages
- **THEN** each imported named NPC carries an explicit named policy and one post-commit ensure is
  scheduled per record

#### Scenario: A rejected import batch emits no job
- **WHEN** an import batch fails validation and is rejected as a whole
- **THEN** no imported character carries a portrait policy and no post-commit job is emitted

### Requirement: Every player-activation path finalizes the portrait lifecycle
Every successful activation transport SHALL establish the same named portrait policy and apply the same explicit skip flag and guarded post-commit generation behavior. Official-satisfied, carded, in-flight or ineligible subjects SHALL enqueue nothing; skipped creation SHALL schedule nothing.

#### Scenario: Web activation assigns the portrait policy
- **WHEN** a character is activated through the Web creation flow
- **THEN** it has named policy with stable key str(pk); a callback is scheduled only when not explicitly skipped, and enqueue is subject to the shared guard

#### Scenario: Telnet and Web activation produce identical portrait state
- **WHEN** characters activate through Telnet and Web with equivalent skip, eligibility, gallery, job and official-reference inputs
- **THEN** both carry the same policy shape and guarded scheduling/enqueue outcome, including no request for skipped or satisfied subjects

#### Scenario: Rolled-back activation leaves no portrait state
- **WHEN** the activation transaction fails after the policy would have been assigned
- **THEN** no `portrait_policy` and no portrait job remain on the character
