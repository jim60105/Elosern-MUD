## Purpose

The adult portrait gate: every `portrait:character` subject re-checks canonical validated `age >= 18`
and `apparent_age >= 18` immediately before enqueue, in addition to the creation/import validation
that already enforced the same invariant. Missing, malformed, or underage values reject with a named
diagnostic and produce no queue record, no prompt, and no worker call. Permanent underage regression
tests cover both fields on every lifecycle path.

## ADDED Requirements

### Requirement: Every character-portrait enqueue re-checks both adult age fields immediately before enqueue
`world/art/adult.py` SHALL expose `portrait_eligibility(entity)` that reads `age` and `apparent_age`
from the character's canonical attributes and raises a named `PortraitRejected` diagnostic when either
value is missing, non-integer, or less than 18. `world/art/service.py` SHALL run this gate for every
`portrait:character` subject immediately before any queue record is written, in addition to the
schema/creation validation that already checked the same fields. A rejection SHALL produce no queue
record and no prompt text, SHALL never reach a worker fixture, and SHALL be logged with the named
diagnostic for staff review.

#### Scenario: A valid adult record reaches the worker fixture with an adult description
- **WHEN** a character with `age = 22` and `apparent_age = 22` and an explicit named portrait policy is
  enqueued
- **THEN** the gate passes and a fixture worker receives a job whose description contains the
  character's adult identity

#### Scenario: age = 17 is rejected before the queue and the worker
- **WHEN** a character with `age = 17` and `apparent_age = 22` and an explicit named portrait policy is
  enqueued
- **THEN** a named `PortraitRejected` is raised, no queue record exists, no prompt text is produced,
  and the worker fixture is never invoked

#### Scenario: apparent_age = 17 is rejected before the queue and the worker
- **WHEN** a character with `age = 22` and `apparent_age = 17` and an explicit named portrait policy is
  enqueued
- **THEN** a named `PortraitRejected` is raised, no queue record exists, no prompt text is produced,
  and the worker fixture is never invoked

#### Scenario: Missing or malformed age values reject with a named diagnostic
- **WHEN** a character's `age` or `apparent_age` attribute is absent, a string, or otherwise non-integer
- **THEN** a named `PortraitRejected` is raised with the failing field identified, and no queue record
  is created

### Requirement: The gate runs on every lifecycle path and rejects deterministically without a persisted marker
`world/art/service.py` SHALL apply the gate at schedule time and again before the queue write for
every lifecycle path that can produce a `portrait:character` subject — player creation, validated
import, named-NPC spawn, and startup recovery. Because the gate is a pure function of the canonical
age attributes, every attempt against the same underage data SHALL reject with the same named
diagnostic; no separate persisted rejection marker is required, and no attempt SHALL be retried
periodically (attempts occur only on lifecycle events). A subject that failed the gate SHALL be
eligible again once its canonical age data is corrected, at which point the next lifecycle attempt
passes.

#### Scenario: An underage player creation never enqueues
- **WHEN** a player character whose creation record carries `age = 17` is activated
- **THEN** the creation succeeds (art is presentation) but no portrait record is created and no worker
  call occurs

#### Scenario: An underage import batch item never enqueues
- **WHEN** an import batch contains a record with `apparent_age = 17` and an explicit named portrait
  policy
- **THEN** the import is rejected by the schema gate before any portrait scheduling, and no queue
  record is created

#### Scenario: A forged underage spawn never reaches the worker
- **WHEN** a spawn path is forced to schedule a portrait subject for a character whose canonical age
  data is underage or missing
- **THEN** the gate rejects before any record write and the worker fixture receives nothing

#### Scenario: An ineligible recovered subject is skipped deterministically
- **WHEN** a character with an explicit named policy fails the adult gate during recovery
- **THEN** no record is created, a named diagnostic is logged, and a later recovery pass for the same
  underage data rejects identically without creating a record

### Requirement: Rejected prompt content never reaches the presenter or browser
The presenter-facing surface SHALL never contain a rejected prompt or an underage identity. A
`portrait:character` subject that failed the gate SHALL resolve only to the unavailable placeholder
with its explanatory label and alternative text.

#### Scenario: The presenter surface is free of rejected content
- **WHEN** a gate-rejected character is queried through the read-only presenter primitives
- **THEN** the result is the unavailable placeholder with a label and safe alternative text, and no
  prompt text or underage identity appears in the payload
