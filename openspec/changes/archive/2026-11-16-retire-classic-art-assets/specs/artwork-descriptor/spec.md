## MODIFIED Requirements

### Requirement: Descriptors preserve independent artwork facts
Each canonical descriptor SHALL carry stable subject identity, source revision, independent generation state, ordered real-image or known-fault attempts, and a permitted terminal fallback. Candidates SHALL carry canonical resource identity/version, bounded same-origin URL, origin and applicable geometry. Faults SHALL name the failed source and bounded reason without a URL.

#### Scenario: Official image does not complete generation
- **WHEN** an official candidate is available while generation is pending or failed
- **THEN** its origin is official and the original generation state remains unchanged

#### Scenario: Known faults preserve precedence
- **WHEN** a preferred source is broken and a later source is usable
- **THEN** the descriptor puts the known fault at that preferred position before the later candidate

#### Scenario: Resolution reads without writing
- **WHEN** the same descriptor is built repeatedly
- **THEN** no queue, gallery, room, character, asset status, file or narrative state changes

#### Scenario: Generation state derives only from gallery state
- **WHEN** a subject has official artwork and a live job, recorded gallery error or stored card
- **THEN** state is pending for a live job, else failed for recorded error, else done for a card, else missing; official artwork never completes it
