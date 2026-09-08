## MODIFIED Requirements

### Requirement: @art requeue accepts one validated full subject key and forces regeneration under the lock
`commands/art.py::CmdArtRequeue` (`@art requeue <full-subject-key>`) SHALL parse and validate exactly
one full subject key through the subject parser. An invalid key SHALL be rejected with a named error
and no record change. A valid key SHALL reset the record to `pending` under the queue lock, preserve
the prior valid output, and SHALL be the only way an ordinary-lifecycle pass can force regeneration. A valid CHARACTER subject
key SHALL instead issue one gallery generation request for that subject — appending a new card on
success and never replacing an existing one — because a character subject no longer owns a
fixed-identity asset record; a monster subject's gallery request SHALL respect the one-card cap.
Neither path SHALL create a classic asset record for a character subject.

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
