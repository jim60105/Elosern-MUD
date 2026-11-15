# landmark-rite-content Specification

## Purpose
Defines the authored landmark rite document: ritual archetypes, their options and scenes, the assignment of every map district to one archetype, and the validated immutable snapshot that game code reads.

## Requirements

### Requirement: The rite document loads into one validated immutable snapshot
The rite loader SHALL turn one rite document into an immutable snapshot of archetypes, options and scenes, and SHALL reject an invalid document with every fault reported together, each naming its field path and a stable code.

#### Scenario: Valid document
- **WHEN** a synthetic document with one archetype and two options within every bound is loaded
- **THEN** the snapshot exposes that archetype, its options in authored order and their scenes, and the snapshot cannot be mutated

#### Scenario: Bounds
- **WHEN** a document carries an out-of-range duration, an out-of-range shame or exposure step, an over-long text, an option count outside two to three, a malformed key or an unknown field
- **THEN** loading is rejected and each fault names its field path and its own code

#### Scenario: Duplicate identities
- **WHEN** two options of one archetype share a key, or two scenes anywhere in the document share a scene identifier
- **THEN** loading is rejected with the duplicate code for each

#### Scenario: Several faults at once
- **WHEN** one document contains three unrelated faults
- **THEN** a single rejection lists all three

### Requirement: Every district is assigned exactly one archetype
The rite loader SHALL accept a document only when every supplied district key is assigned to a declared archetype and every declared archetype is assigned to at least one district.

#### Scenario: Unassigned district
- **WHEN** a supplied district key is absent from the assignment
- **THEN** loading is rejected naming that district

#### Scenario: Unknown references
- **WHEN** the assignment names a district that was not supplied, or an archetype that is not declared
- **THEN** loading is rejected naming the offending key

#### Scenario: Unused archetype
- **WHEN** an archetype is declared and no district is assigned to it
- **THEN** loading is rejected naming that archetype

### Requirement: A rite scene needs narration and may omit the watch perspective
A rite scene SHALL contain at least one narration line and MAY open with narration. An option SHALL declare its watch perspective explicitly, either as a scene or as absent.

#### Scenario: Narration first
- **WHEN** a scene opens with a narration line followed by speech
- **THEN** it loads

#### Scenario: No narration
- **WHEN** a scene contains only speech lines
- **THEN** loading is rejected for that scene

#### Scenario: Explicit absence
- **WHEN** one option declares its watch perspective as absent and another omits the field entirely
- **THEN** the first loads with no watch scene and the second is rejected

### Requirement: Rite content is read only after it is installed
Reading the current rite snapshot SHALL raise a named not-loaded error until a snapshot is installed, and SHALL never load a document implicitly.

#### Scenario: Read before install
- **WHEN** the current snapshot is read in a process that installed none
- **THEN** the named not-loaded error is raised

#### Scenario: Scoped install
- **WHEN** a snapshot is installed for a scope and the scope ends
- **THEN** the value that was current before the scope is current again

### Requirement: The shipped rite document is adopted against the published districts
Adopting the shipped rite document SHALL validate it against the district keys of the published district world and install the resulting snapshot. A rejected or unreadable document SHALL raise, SHALL install nothing and SHALL leave any previously installed snapshot current.

#### Scenario: Valid document
- **WHEN** a valid synthetic document is adopted against a synthetic set of district keys
- **THEN** the returned snapshot is the current snapshot

#### Scenario: Invalid document
- **WHEN** a document that leaves one district unassigned is adopted while another snapshot is current
- **THEN** the rejection is raised and the other snapshot is still current

#### Scenario: Missing document
- **WHEN** adoption is pointed at a path that does not exist
- **THEN** it raises and no snapshot is installed

#### Scenario: Shipped document
- **WHEN** the shipped rite document is loaded against the district keys of the shipped district document
- **THEN** it loads and assigns exactly those districts

### Requirement: Adoption requires a registered art subject for every archetype
Adopting the rite document SHALL fail, installing nothing, when the art subject derived from any archetype key is not a registered scene archetype, and SHALL name each such archetype.

#### Scenario: Unregistered subject
- **WHEN** a valid synthetic document whose archetype has no registered art subject is adopted
- **THEN** adoption raises naming that archetype and no snapshot is installed

#### Scenario: Registered subject
- **WHEN** the same document is adopted while its derived subject is registered
- **THEN** the snapshot is installed
