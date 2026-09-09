## MODIFIED Requirements

### Requirement: @art requeue accepts one validated full subject key and forces regeneration under the lock
`commands/art.py::CmdArtRequeue` (`@art requeue <full-subject-key>`) SHALL parse and validate exactly
one full subject key through the subject parser. An invalid key SHALL be rejected with a named error
and no record change. A key whose subject kind declares NO gallery — a scene key — SHALL reset the
classic record to `pending` under the queue lock, preserve the prior valid output, and SHALL be the
only way an ordinary-lifecycle pass can force regeneration of that record.

A key whose subject kind declares a gallery — character and generic monster alike — SHALL instead
issue exactly one gallery generation request for that subject through the shared request seam,
appending a new card on success. Requeue is the staff force path: it SHALL deliberately bypass the
automatic-generation idempotency guard, so a subject that already holds cards still gets one new
generation. For a kind whose declared card maximum the new card would exceed, the append SHALL respect
that maximum exactly as any other append does — for the monster kind, replacing its single card. For a
kind with no declared maximum, the existing cards SHALL be untouched. Neither path SHALL create a
classic asset record for a gallery-bearing subject.

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
- **WHEN** staff runs `@art requeue portrait:monster:<tier>` for a tier that already holds its one card
- **THEN** one gallery generation is requested, no classic asset record is created, and the settled card replaces the existing one under the declared maximum

#### Scenario: A monster requeue never resets a classic record
- **WHEN** staff runs `@art requeue portrait:monster:<tier>` for a tier that still has a pre-existing classic asset record
- **THEN** a gallery generation is requested and that classic record's status is unchanged
