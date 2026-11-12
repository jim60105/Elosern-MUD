## MODIFIED Requirements

### Requirement: @art requeue accepts one validated full subject key and forces regeneration under the lock
`commands/art.py::CmdArtRequeue` (`@art requeue <full-subject-key>`) SHALL parse and validate exactly
one full subject key through the subject parser. An invalid key SHALL be rejected with a named error
and no record change. A key whose subject kind declares a gallery — character, species-keyed monster and scene alike —
SHALL request one gallery generation through the shared seam and SHALL NOT reset or create a classic
record.

#### Scenario: A validated key forces regeneration
- **WHEN** staff runs `@art requeue scene:<archetype>` for a registered synthetic archetype that holds one card
- **THEN** one gallery generation is requested, no classic record is reset or created, and the existing
  card stays until the new card replaces it under the declared maximum

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


### Requirement: Players have no access to any art control
No `@art` subcommand SHALL be available to ordinary players. Player-triggered generation SHALL exist
only through the gallery management actions, for subjects admitted to the acting player.

#### Scenario: All subcommands require staff
- **WHEN** every `@art` subcommand's access is exercised with a non-staff caller
- **THEN** each is denied and no queue, store, or worker operation runs

