## Purpose

The deterministic, offline-computable monster population for the wilderness/Virtual layer: bounded
authored regional habitats whose actual individuals are created once through the regional population
owner, thereafter evolve through its game-time recovery and explicitly bound ordinary-activity
contracts (including unobserved group wandering and journeys), and remain registered by wilderness
coordinate in the script's `itemcoordinates` while present. There is no coordinate-slot,
tier-example, capital-supply or room-entry refill path, and reads project only actual living
registrations.

## Requirements

### Requirement: A registered wilderness monster survives room recycling
An actual wilderness individual SHALL remain registered independently of transient rooms and reattach with its same persistent identity, current resources and home ownership on later activation.

#### Scenario: Re-activating a coordinate re-attaches the registered monster
- **WHEN** a coordinate has a registered monster, its room is vacated and recycled, and a character
  later enters the wilderness at that coordinate again
- **THEN** the registered `Monster` appears in the active room at that coordinate

#### Scenario: Read and re-entry do not refill
- **WHEN** a registered member is defeated or a habitat is empty before recovery due time
- **THEN** room preparation, startup reuse, view reads and re-entry create no immediate replacement

### Requirement: Runtime population uses authored regions without implicit fallback
Runtime ordinary population SHALL initialize bounded authored habitats once and thereafter evolve only through the regional owner's game-time recovery contract, with no tier-example fallback or capital supply guarantee.

#### Scenario: Fresh world and reuse
- **WHEN** fresh provisioning initializes habitats and the world then restarts or revisits
- **THEN** only the initial operation fills lawfully; subsequent reads/activation preserve initialized state and living IDs/resources

#### Scenario: Unconfigured and incompatible world
- **WHEN** ground has no ecology declaration or an existing world lacks required owner initialization state
- **THEN** unconfigured ground receives no automatic birth; incompatible state gives an explicit operator refusal without slot conversion, foreign deletion or hidden reset

#### Scenario: Offline delivery
- **WHEN** LLM and art services are disabled during real construction, hunt acceptance, combat, delay, recovery and reload
- **THEN** the deterministic loop completes using approved registered species and actual entities

### Requirement: Active encounters retain protected individuals and cells
Regional population settlement SHALL exclude active and historically protected encounter cells from births and preserve every persisted participant until the owning session settles.

#### Scenario: Session restoration before birth
- **WHEN** startup restores a recorded terminal round or clock catch-up crosses its active interval
- **THEN** population neither deletes/replaces its participants nor appends new enemies to its protected cell

#### Scenario: Finished protection
- **WHEN** an encounter has lawfully settled and its protection interval ended
- **THEN** only future due lawful regional births may use the cell; no immediate per-cell refill or participant resurrection occurs
