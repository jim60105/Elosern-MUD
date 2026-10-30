## MODIFIED Requirements

### Requirement: Compact status reports canonical true resources
Status SHALL use exact schema5 with canonical true resources, actor, conditions, fatigue subjects, disguise and combat facts; each fatigue subject SHALL include canonical asleep state without changing resource ownership under possession.

#### Scenario: Active disguise does not alter resources
- **WHEN** an actor has true HP 80/100, MP 40/60, SP 30/50 and display-only disguised values for any traits
- **THEN** the status payload reports 80/100, 40/60, and 30/50 and marks `disguise_active` true

#### Scenario: Missing gauge fails closed
- **WHEN** the active puppet lacks a valid required HP, MP, or SP gauge
- **THEN** the status panel is unavailable at schema version 5 and does not report zero for the missing resource

#### Scenario: A zero-maximum gauge is reported verbatim
- **WHEN** the active puppet's canonical storage carries a required gauge whose computed maximum is zero with stored current zero, as sanctioned zero-MP/SP monster data produces
- **THEN** the status panel stays available and reports that resource with current 0 and maximum 0, inventing nothing

#### Scenario: A negative computed maximum fails closed
- **WHEN** a required gauge's stored base/mod/mult compute to a negative maximum, or its stored current is nonzero while its maximum computes to zero
- **THEN** the status panel is unavailable at schema version 5 rather than reporting the corrupt gauge

#### Scenario: Status version cutover is exact
- **WHEN** equivalent available and unavailable status payloads are checked at versions 4 and 5
- **THEN** the registered version-5 forms are accepted and version-4 forms are rejected without replacing committed presentation

#### Scenario: Actor envelope fields are bounded
- **WHEN** an available version-5 status payload is validated
- **THEN** `actor` contains display `name` of 1..256 Unicode code points, opaque correlation `identity` of 1..64 ASCII characters, and nullable `location`, with the existing optional composed `full_title` contract unchanged
- **AND** a present location contains exactly a 1..256-code-point display `label` and 1..64-character opaque `identity`

#### Scenario: Condition and remaining envelope bounds
- **WHEN** an available version-5 status payload is validated
- **THEN** `conditions` contains at most 32 entries
- **AND** `disguise_active` is boolean and `combat` is null or the exact combat object

#### Scenario: Missing or malformed traits fail closed
- **WHEN** required canonical traits are missing or malformed
- **THEN** the common status-unavailable payload is produced rather than fabricated zero values

#### Scenario: Both status forms share registered version 3
- **WHEN** available and unavailable status forms are checked
- **THEN** both use the same registered version 5
- **AND** envelope protocol version and unrelated panel versions remain unchanged and status version 4 is not accepted as a compatibility form

#### Scenario: Required fatigue sleep facts
- **WHEN** current owner and present travellers include awake, voluntary and forced sleepers
- **THEN** each physiological identity has its own bounded fatigue row and asleep boolean, missing facts remain unavailable and reads materialize nothing

### Requirement: Fatigue presentation identifies its physiological subject
Read-only fatigue presentation SHALL identify each present physiological subject by its own committed identity, reserve percent, exact stage, canonical asleep boolean and restriction while preserving unrelated owner-keyed possession resources.

#### Scenario: Possessed body differs from owner
- **WHEN** the owner is awake at 80% and the controlled companion is forced asleep at 2%
- **THEN** presentation identifies each subject and exposes the companion's sleep restriction; no owner gauge is relabelled as companion truth

#### Scenario: No independent countdown
- **WHEN** a forced sleeper is displayed twice without accepted time
- **THEN** reserve and posture stay unchanged and no fabricated expiry or wake is promised

#### Scenario: Present party rows stay body-keyed
- **WHEN** the controlled body changes through possession while present companions differ in posture
- **THEN** each body retains its own fatigue/sleep row and no owner gauge becomes controlled-body physiology
