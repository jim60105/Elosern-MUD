## MODIFIED Requirements

### Requirement: Startup recovery rescans explicit unique portrait policies
`art_sync_all()` SHALL also scan living characters that carry an explicit `{"mode": "named",
"stable_key": ...}` portrait policy and ensure each subject, recovering an enqueue that failed after an
earlier gameplay commit. A subject whose canonical ages fail the age check SHALL be skipped with a named
diagnostic and never retried by a later recovery pass for the same policy.

The recovery SHALL be satisfied by the subject's GALLERY: a subject whose gallery already holds at
least one card, or whose gallery generation is already in flight, SHALL be left alone, and only a
subject with an empty gallery and no in-flight job SHALL be requested. The requested image SHALL be
one unbound auto-generated card, never a classic asset record.

#### Scenario: A named policy with an empty gallery is recovered at startup
- **WHEN** a character has an explicit named portrait policy, an empty gallery, and no in-flight job after a restart
- **THEN** exactly one gallery generation is requested and no gameplay is rolled back

#### Scenario: A subject that already has a card is not regenerated
- **WHEN** recovery runs for a character whose gallery already holds a card, or whose generation is already in flight
- **THEN** nothing is requested and the gallery is unchanged

#### Scenario: A named policy without a record is recovered at startup
- **WHEN** a character has an explicit named portrait policy but no asset record exists after a
  restart
- **THEN** the subject record is ensured and the record is created without any gameplay rollback

#### Scenario: An ineligible recovered subject is skipped deterministically
- **WHEN** a character with an explicit named policy fails the canonical-age check during recovery
- **THEN** no record is created, a named diagnostic is logged, and the same policy is not retried by a
  later recovery pass without re-running the gate

