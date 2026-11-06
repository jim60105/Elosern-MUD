## ADDED Requirements

### Requirement: Reference export carries the monster spawn section
The reference export SHALL include a monster spawn section listing every authored ecology zone and manual monster site, with species and variant names resolved at export, each row naming its region by key only, and without reading live database state.

#### Scenario: Deterministic rows
- **WHEN** synthetic zones and sites are exported twice from registries given in different orders
- **THEN** the encoded output is byte-identical, zones and sites each sort by key, and pool rows and member rows keep their authored order

#### Scenario: Names resolve from the registries
- **WHEN** a synthetic zone and a synthetic site each name a composition whose member names a synthetic variant
- **THEN** each member row carries that variant's key and name and its species' key and name, and each zone and site row carries its region's key and no region name

#### Scenario: Site individual and recovery fields
- **WHEN** one synthetic site is one-shot with an individual name and another recovers after a delay with none
- **THEN** the first row carries the name and a null recovery value, and the second carries the delay and a null name

#### Scenario: Placement sources stay in the source closure
- **WHEN** the export is built
- **THEN** the source manifest lists the placement and species source files, so changing either one makes freshness report not current

### Requirement: Reference decoding refuses a malformed monster spawn section
Decoding SHALL accept only schema version 2 documents with a complete monster spawn section, and SHALL refuse the whole document through the existing reference-context error when the section is absent or malformed.

#### Scenario: Encode and decode round trip
- **WHEN** a document holding a synthetic section is encoded and decoded
- **THEN** the decoded section equals the original and encoding it again yields identical bytes

#### Scenario: Refused section shapes
- **WHEN** a section has an unknown or missing key, a rectangle that is not four integers, a rectangle with a minimum above its maximum, a zone with no rectangles, a nonpositive weight, a member minimum above its maximum, or a site kind outside the closed vocabulary
- **THEN** decoding refuses the whole document

#### Scenario: Prior schema version
- **WHEN** a document declares schema version 1, or omits the section
- **THEN** decoding refuses it and no compatibility conversion runs

#### Scenario: Site kind vocabulary parity
- **WHEN** the game's closed site kind vocabulary and the decoder's are compared
- **THEN** they hold the same members in the same order
