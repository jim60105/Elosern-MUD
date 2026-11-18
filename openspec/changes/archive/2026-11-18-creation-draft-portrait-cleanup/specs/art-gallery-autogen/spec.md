# Spec Delta

## MODIFIED Requirements

### Requirement: Player creation may skip the automatic portrait
`world/rules/character_creation.py::finalize_player_portrait` SHALL accept an explicit skip flag,
defaulting to generating. It SHALL establish the explicit named `portrait_policy` on every path,
including the skipped one. A skipped creation
SHALL enqueue nothing. It SHALL preserve a custom activation's already committed draft portrait,
while a preset activation still discards creation-owned draft art before its normal portrait
source (draft portrait lifecycle). The flag SHALL
be read inside the activation transaction like
the rest of the finalization, so a rollback adds no portrait state and preserves previously committed draft portrait state.

#### Scenario: A skipped creation starts with an empty gallery
- **WHEN** a character is activated with the skip flag set
- **THEN** it carries the named portrait policy, a previously empty gallery stays empty, no job is enqueued, and it resolves through the standard chain's terminal fallback seam rather than owning any portrait state of its own

#### Scenario: The default path still generates
- **WHEN** a character is activated without the skip flag, without a satisfying official default and without an existing card or in-flight job
- **THEN** exactly one post-commit gallery generation is scheduled

#### Scenario: A rolled-back skipped activation leaves nothing
- **WHEN** an activation with the skip flag set rolls back
- **THEN** no newly established portrait policy or gallery state remains; previously committed draft portrait state is unchanged

#### Scenario: The empty gallery resolves through the terminal fallback seam
- **WHEN** a skipped character's empty gallery is presented
- **THEN** it resolves through the standard chain's terminal fallback seam (inert until the
  gallery-fallback capability fills it — today the honest outcome is the truthful placeholder, owned
  by ``gallery-builtin-fallbacks``)
- **AND** establishing the policy on every path keeps the character eligible for a later request

### Requirement: Successful player creation and validated import schedule an eligible unique portrait through transaction.on_commit
Creation and validated import SHALL establish named portrait policy transactionally. Unless creation explicitly skips generation, they SHALL schedule the guarded gallery callback through transaction.on_commit; actual enqueue SHALL require eligibility and unsatisfied gallery/job/official state. Rejected or rolled-back transactions SHALL emit no callback or job.

#### Scenario: A committed creation schedules exactly one guarded gallery request
- **WHEN** player creation commits successfully with generation not explicitly skipped
- **THEN** the character carries an explicit named policy with a stable key and exactly one
  post-commit guarded gallery request is scheduled

#### Scenario: A rolled-back creation emits no job
- **WHEN** a creation attempt fails and its transaction rolls back
- **THEN** no activation-created portrait policy is persisted and no post-commit portrait job is emitted; previously committed draft portrait state is preserved

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
- **THEN** both carry the same policy shape and the same guarded scheduling/enqueue outcome, including no request for skipped or satisfied subjects

#### Scenario: Rolled-back activation leaves no portrait state
- **WHEN** the activation transaction fails after the policy would have been assigned
- **THEN** no activation-added `portrait_policy` or portrait job remains on the character; previously committed creation portrait policy, receipt, cards and jobs are unchanged

#### Scenario: Draft art satisfies the custom activation guard
- **WHEN** a custom activation has a creation-generated card or an existing creation job on its named subject
- **THEN** finalization reuses the same policy and the shared idempotency guard enqueues no duplicate
