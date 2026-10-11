# Spec Delta

## MODIFIED Requirements

### Requirement: @art requeue accepts one validated full subject key and forces regeneration under the lock
`commands/art.py::CmdArtRequeue` (`@art requeue <full-subject-key>`) SHALL parse and validate exactly
one full subject key through the subject parser. An invalid key SHALL be rejected with a named error
and no record change. A key whose subject kind declares NO gallery — a scene key — SHALL reset the
classic record to `pending` under the queue lock, preserve the prior valid output, and SHALL be the
only way an ordinary-lifecycle pass can force regeneration of that record.

#### Scenario: A validated key forces regeneration
- **WHEN** staff runs `@art requeue scene:forest_path`
- **THEN** the scene record becomes `pending`, its prior valid output is preserved, and a regeneration
  is queued under the queue lock

#### Scenario: An invalid key is rejected with no record change
- **WHEN** staff runs `@art requeue` with a malformed or unknown full subject key
- **THEN** a named error is returned and no record is changed

#### Scenario: A character key requeue adds a gallery card
- **WHEN** staff runs `@art requeue portrait:character:<stable-key>` for a subject that already holds cards
- **THEN** one gallery generation is requested, no classic asset record is created, and the existing cards are untouched until the new card is appended

#### Scenario: A monster key requeue requests a gallery card honouring the cap
- **WHEN** staff runs `@art requeue portrait:monster:<visual-key>` for a visual species that already holds its one card
- **THEN** one gallery generation is requested, no classic asset record is created, and the settled card replaces the existing one under the declared maximum

#### Scenario: A monster requeue never resets a classic record
- **WHEN** staff runs `@art requeue portrait:monster:<visual-key>` for a visual species that still has a pre-existing classic asset record
- **THEN** a gallery generation is requested and that classic record's status is unchanged

#### Scenario: A gallery-bearing key issues one request through the shared seam
- **WHEN** the requeue key's subject kind declares a gallery — character and species-keyed monster alike
- **THEN** the command SHALL instead issue exactly one gallery generation request for that subject
  through the shared request seam, appending a new card on success

#### Scenario: Requeue deliberately bypasses the idempotency guard
- **WHEN** requeue targets a subject that already holds cards
- **THEN** because requeue is the staff force path, it SHALL deliberately bypass the
  automatic-generation idempotency guard, so the subject still gets one new generation

#### Scenario: The append respects the declared card maximum
- **WHEN** the new card would exceed the kind's declared card maximum
- **THEN** the append SHALL respect that maximum exactly as any other append does — for the monster
  kind, replacing its single card

#### Scenario: A kind with no declared maximum keeps its existing cards
- **WHEN** the kind declares no card maximum
- **THEN** the existing cards SHALL be untouched

#### Scenario: Neither path creates a classic record for a gallery-bearing subject
- **WHEN** either requeue path runs for a gallery-bearing subject
- **THEN** neither path SHALL create a classic asset record for that subject

#### Scenario: Retired monster tiers never requeue
- **WHEN** staff supplies any threat-tier key as a monster requeue subject
- **THEN** a named invalid-subject error is returned with no generation, record reset or conversion


### Requirement: @art retry re-enqueues failed records
`commands/art.py::CmdArtRetry` (`@art retry`) SHALL re-enqueue every `failed` classic subject record
of a kind that declares NO gallery to `pending` under the queue lock and SHALL, in the same pass,
re-drive every subject whose `GalleryRecord` carries a recorded generation error through the gallery
request seam. It SHALL report both counts.

#### Scenario: Failed records are re-enqueued
- **WHEN** staff runs `@art retry` with failed classic (scene) records present
- **THEN** each failed record becomes `pending` and the command reports the re-enqueued count

#### Scenario: A legacy failed monster classic record is never reactivated
- **WHEN** staff runs `@art retry` with a `failed` classic monster record present
- **THEN** that record stays `failed` with its stored state untouched, it is not counted in the re-enqueued total, and no classic generation is queued for it

#### Scenario: A failed gallery generation is retried without a restart
- **WHEN** a character subject's gallery carries a recorded generation error and staff runs `@art retry`
- **THEN** exactly one gallery generation is requested for that subject and the command reports it

#### Scenario: An ineligible erroring subject is skipped, not fatal
- **WHEN** a subject carrying a recorded gallery error no longer satisfies the request seam's preconditions
- **THEN** that subject is skipped with no record change, the remaining subjects are still retried, and the command reports the count it actually requested

#### Scenario: A moot error on a subject that now has art is cleared
- **WHEN** a subject carrying a recorded gallery error has since gained a card and staff runs `@art retry`
- **THEN** no generation is requested for it, its recorded error is cleared, and it no longer appears as erroring on the status surface

#### Scenario: A healthy gallery is left alone
- **WHEN** staff runs `@art retry` and every gallery record carries no error
- **THEN** no gallery generation is requested and the command reports zero gallery retries

#### Scenario: The classic arm skips every gallery-bearing subject kind
- **WHEN** the classic retry arm encounters a subject kind whose capability declaration carries a
  gallery
- **THEN** it SHALL skip that kind: such a kind's failures are retried exclusively through the
  gallery arm, so a legacy classic monster record is never reset, re-enqueued, or newly produced by
  any retry pass

#### Scenario: No classic-character re-enqueue branch exists
- **WHEN** the retry command's classic arm is inspected
- **THEN** because a character subject no longer owns a classic asset record,
  `queue.failed_keys()` can no longer yield one; the command SHALL NOT carry a classic-character
  re-enqueue branch, and the gallery arm SHALL be the only character retry path

#### Scenario: A gallery re-drive goes through the validated request seam
- **WHEN** the gallery arm re-drives a subject
- **THEN** the re-drive SHALL go through the same validated request seam an automatic path uses, so
  every precondition that seam enforces still applies and a subject that no longer qualifies is
  skipped with no record change rather than failing the whole command

#### Scenario: A declined erroring subject with art now has its error cleared
- **WHEN** the seam declines an erroring subject because its gallery is no longer empty — a seed
  card arrived, or an operator kept an image
- **THEN** the recorded error SHALL be cleared rather than left standing: the subject has art and
  its automatic guard will suppress every future request, so nothing else would ever clear that
  code and it would otherwise remain permanently on the status surface

#### Scenario: A subject declined for any other reason keeps its error
- **WHEN** the seam declines an erroring subject for any reason other than a now-non-empty gallery
- **THEN** that subject SHALL keep its recorded error

#### Scenario: Retired tier jobs and gallery errors never retry
- **WHEN** a retry pass encounters tier-keyed monster records or errors
- **THEN** it cannot reactivate or convert them; valid scene, character and species retries retain their normal behavior

