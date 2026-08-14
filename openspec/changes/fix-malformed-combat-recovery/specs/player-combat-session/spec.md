## MODIFIED Requirements

### Requirement: Startup restores valid sessions and terminates invalid references safely
The deterministic startup sequence SHALL reconstruct valid persisted sessions and skip-safety
registration through `restore_persisted_sessions()`. A persisted record that cannot be strictly parsed
SHALL be cleared or quarantined without settling world time or participant effects derived from its
untrusted fields, and SHALL leave the player unblocked for ordinary hostile engagement. Missing,
deleted, moved, duplicated, or malformed
participants in a well-formed record SHALL produce a diagnostic and deterministic session termination
without leaving the player blocked.

#### Scenario: Reload preserves an active battle
- **WHEN** the server reloads with a valid session whose participants remain in its room
- **THEN** the next player combat action resumes the recorded round count and battlefield membership

#### Scenario: Deleted enemy does not strand the player
- **WHEN** startup finds that every recorded enemy dbref is missing
- **THEN** it closes the session with a diagnostic and clears skip-safety state

#### Scenario: Malformed persisted record is cleared at startup
- **WHEN** `active_combat` holds a value that strict parsing rejects (for example `{"not": "a valid record"}`)
- **THEN** startup clears the durable record and the actor's transient combat context and battlefield
  registration without advancing world time and without settling any participant effects

#### Scenario: Hostile engagement succeeds after malformed-record recovery
- **WHEN** startup cleared a malformed persisted record and the player then engages a valid co-located
  living monster
- **THEN** a fresh hostile session is created and the player can act in it

## ADDED Requirements

### Requirement: Malformed session payloads fail closed without unhandled conversion errors
`read_session` SHALL raise `CombatSessionError` with the `malformed_session` reason for any
`active_combat` payload that fails raw conversion or strict parsing, including `TypeError`/`ValueError`
conversion-shape failures, and SHALL NOT leak an unhandled conversion exception. `is_in_active_session`
SHALL return false, and hostile engagement or forfeit SHALL reject with the normalized
`malformed_session` reason while such a payload remains persisted.

#### Scenario: Non-dict payloads normalize to a malformed-session rejection
- **WHEN** `active_combat` holds a non-dict value whose conversion raises `TypeError` or `ValueError`
  (for example an integer or a string)
- **THEN** `read_session` raises `CombatSessionError` with the `malformed_session` reason and
  `is_in_active_session` returns false

#### Scenario: Engagement and forfeit reject a persisted malformed payload without unhandled exceptions
- **WHEN** the player attempts to engage or forfeit while a malformed payload is still persisted
- **THEN** the operation rejects with the normalized `malformed_session` reason and no unhandled
  `TypeError` or `ValueError` escapes
