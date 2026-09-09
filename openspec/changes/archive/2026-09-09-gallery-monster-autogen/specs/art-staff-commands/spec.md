## MODIFIED Requirements

### Requirement: @art retry re-enqueues failed records
`commands/art.py::CmdArtRetry` (`@art retry`) SHALL re-enqueue every `failed` classic subject record
of a kind that declares NO gallery to `pending` under the queue lock and SHALL, in the same pass,
re-drive every subject whose `GalleryRecord` carries a recorded generation error through the gallery
request seam. It SHALL report both counts.

The classic arm SHALL skip every subject kind whose capability declaration carries a gallery: such a
kind's failures are retried exclusively through the gallery arm, so a legacy classic monster record is
never reset, re-enqueued, or newly produced by any retry pass. Because a character subject no longer
owns a classic asset record, `queue.failed_keys()` can no longer yield one; the command SHALL NOT
carry a classic-character re-enqueue branch, and the gallery arm SHALL be the only character retry
path.

A gallery re-drive SHALL go through the same validated request seam an automatic path uses, so every
precondition that seam enforces still applies and a subject that no longer qualifies is skipped with
no record change rather than failing the whole command.

When the seam declines an erroring subject because its gallery is no longer empty — a seed card
arrived, or an operator kept an image — the recorded error SHALL be cleared rather than left standing.
The subject has art and its automatic guard will suppress every future request, so nothing else would
ever clear that code and it would otherwise remain permanently on the status surface. A subject
declined for any other reason SHALL keep its recorded error.

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
