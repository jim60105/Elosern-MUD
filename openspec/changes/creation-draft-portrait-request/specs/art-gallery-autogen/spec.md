# Spec Delta

## MODIFIED Requirements

### Requirement: Portrait-character enqueue validates canonical age attributes immediately before enqueue
`world/art/subjects.py` SHALL expose `character_ages(entity)` that reads `age` and `apparent_age`
from the character's canonical attributes and raises a named `ArtSubjectError` diagnostic identifying
the failing field when either value is missing or non-integer. `world/art/service.py` SHALL run this check immediately before enqueue, except an owned pending-character request with a validated draft-portrait input SHALL validate submitted apparent age instead, without writing canonical ages.

#### Scenario: A valid integer record reaches the worker fixture
- **WHEN** a character with `age = 22` and `apparent_age = 22` and an explicit named portrait policy is
  enqueued
- **THEN** the age check passes and a fixture worker receives a job whose description contains the
  character's canonical identity

#### Scenario: A zero age is a valid canonical value
- **WHEN** a character with `age = 0` and `apparent_age = 0` and an explicit named portrait policy is
  enqueued
- **THEN** the age check passes, as zero lies within the canonical 0..10000 age range

#### Scenario: A missing age rejects with a named diagnostic
- **WHEN** a character's `age` or `apparent_age` attribute is absent
- **THEN** a named `ArtSubjectError` is raised with the failing field identified, no queue record is
  created, no prompt text is produced, and the worker fixture is never invoked

#### Scenario: A non-integer age rejects with a named diagnostic
- **WHEN** a character's `age` or `apparent_age` attribute is a string or otherwise non-integer
- **THEN** a named `ArtSubjectError` is raised with the failing field identified, no queue record is
  created, no prompt text is produced, and the worker fixture is never invoked

#### Scenario: The enqueue check supplements the schema validation
- **WHEN** the enqueue-time age check runs for a `portrait:character` subject
- **THEN** it runs in addition to the schema/creation validation that already checked the same
  fields

#### Scenario: A rejection is logged for staff review
- **WHEN** the enqueue-time age check rejects a subject
- **THEN** the rejection is logged with the named diagnostic for staff review

#### Scenario: The draft-value exception is pending-only
- **WHEN** a character without canonical ages requests a portrait
- **THEN** only an owned pending-character request with the validated draft-portrait input can enqueue; an activated request or ordinary lifecycle request still rejects before render/write

### Requirement: Startup recovery rescans explicit unique portrait policies
Startup SHALL recover activated characters’ explicit named portrait policies through the shared automatic gallery guard, including official-default suppression. Invalid canonical ages SHALL reject deterministically with a bounded diagnostic and no persisted rejection marker. Repeated attempts on unchanged invalid data SHALL reject identically.

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
- **THEN** the requested image is one unbound auto-generated card, through the per-image gallery seam

#### Scenario: Pending policies do not trigger automatic recovery
- **WHEN** startup encounters a creation-pending character with an early named policy, with or without canonical ages
- **THEN** it enqueues no automatic portrait for that character, preserves any existing draft job/card for its normal settlement/reconnect path, and does not create an automatic replacement after reset
