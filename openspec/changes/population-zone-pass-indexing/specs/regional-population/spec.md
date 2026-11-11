## ADDED Requirements

### Requirement: Boundary zone passes read shared population facts once per pass
A boundary zone pass over many ecology zones SHALL decode the per-zone state record once and scan presence facts once for the whole pass. Each zone SHALL receive the same counts and state fields that its single-zone read gives. Recovery settlement SHALL visit only the zones whose recovery is due at the boundary tick.

#### Scenario: Note pass over many zones
- **WHEN** one settled boundary notes six initialized zones from one presence mapping
- **THEN** the state record is decoded once, the presence mapping is iterated once, and every zone's recovery-due and settled-through fields equal the result of noting that zone alone

#### Scenario: Batch counts equal single-zone counts
- **WHEN** zone counts are measured for several zones from one presence mapping
- **THEN** the presence mapping is iterated once and each zone's local, home-owned and per-cell measures equal its single-zone measure

#### Scenario: Recovery visits due zones only
- **WHEN** a boundary tick finds two of six initialized zones with a recovery due at or before that tick
- **THEN** recovery settlement runs for exactly those two zones in zone-key order, and the other four zone records are unchanged

#### Scenario: Forecast zone note
- **WHEN** a forecast projection notes its zones at one projected tick
- **THEN** its presence facts are scanned once for all zones and each zone's projected recovery-due tick equals the single-zone rule
