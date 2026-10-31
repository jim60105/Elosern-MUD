## MODIFIED Requirements

### Requirement: Compact status reports canonical true resources
Status SHALL use exact schema6 with canonical resources, actor, conditions, fatigue/asleep subjects, disguise and combat facts, plus nullable read-only wilderness travel_capacity; unrelated resource and possession ownership SHALL remain unchanged.

#### Scenario: Active disguise does not alter resources
- **WHEN** an actor has true HP 80/100, MP 40/60, SP 30/50 and display-only disguised values for any traits
- **THEN** the status payload reports 80/100, 40/60, and 30/50 and marks `disguise_active` true

#### Scenario: Missing gauge fails closed
- **WHEN** the active puppet lacks a valid required HP, MP, or SP gauge
- **THEN** the status panel is unavailable at schema version 6 and does not report zero for the missing resource

#### Scenario: A zero-maximum gauge is reported verbatim
- **WHEN** the active puppet's canonical storage carries a required gauge whose computed maximum is zero with stored current zero, as sanctioned zero-MP/SP monster data produces
- **THEN** the status panel stays available and reports that resource with current 0 and maximum 0, inventing nothing

#### Scenario: A negative computed maximum fails closed
- **WHEN** a required gauge's stored base/mod/mult compute to a negative maximum, or its stored current is nonzero while its maximum computes to zero
- **THEN** the status panel is unavailable at schema version 6 rather than reporting the corrupt gauge

#### Scenario: Status version cutover is exact
- **WHEN** equivalent available and unavailable status payloads are checked at versions 5 and 6
- **THEN** the registered version-6 forms are accepted and version-5 forms are rejected without replacing committed presentation

#### Scenario: Actor envelope fields are bounded
- **WHEN** an available version-6 status payload is validated
- **THEN** `actor` contains display `name` of 1..256 Unicode code points, opaque correlation `identity` of 1..64 ASCII characters, and nullable `location`, with the existing optional composed `full_title` contract unchanged
- **AND** a present location contains exactly a 1..256-code-point display `label` and 1..64-character opaque `identity`

#### Scenario: Condition and remaining envelope bounds
- **WHEN** an available version-6 status payload is validated
- **THEN** `conditions` contains at most 32 entries
- **AND** `disguise_active` is boolean and `combat` is null or the exact combat object

#### Scenario: Missing or malformed traits fail closed
- **WHEN** required canonical traits are missing or malformed
- **THEN** the common status-unavailable payload is produced rather than fabricated zero values

#### Scenario: Both status forms share registered version 3
- **WHEN** available and unavailable status forms are checked
- **THEN** both use the same registered version 6
- **AND** envelope protocol version and unrelated panel versions remain unchanged and status version 5 is not accepted as a compatibility form

#### Scenario: Required fatigue sleep facts
- **WHEN** current owner and present travellers include awake, voluntary and forced sleepers
- **THEN** each physiological identity has its own bounded fatigue row and asleep boolean, missing facts remain unavailable and reads materialize nothing

#### Scenario: Capacity shape is bounded and opaque
- **WHEN** wilderness capacity and neighbour duration quotes serialize, or the actor leaves wilderness
- **THEN** exact bounded stage counts, advisory pace state and exit_ref/seconds quotes expose no hidden target facts, withheld destination quotes are null, terminal admitted forced_sleep counts in severe, and travel_capacity is null outside wilderness
