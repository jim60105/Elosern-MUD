# Spec Delta

## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: A registered wilderness monster survives room recycling
An actual wilderness individual SHALL remain registered independently of transient rooms and reattach with its same persistent identity, current resources and home ownership on later activation.

#### Scenario: Re-activating a coordinate re-attaches the registered monster
- **WHEN** a coordinate has a registered monster, its room is vacated and recycled, and a character
  later enters the wilderness at that coordinate again
- **THEN** the registered `Monster` appears in the active room at that coordinate

#### Scenario: Read and re-entry do not refill
- **WHEN** a registered member is defeated or a habitat is empty before recovery due time
- **THEN** room preparation, startup reuse, view reads and re-entry create no immediate replacement

## REMOVED Requirements

### Requirement: population_for_coordinates is a pure, deterministic function over the bounded map
**Reason**: Coordinate-slot generation, tier examples and guaranteed capital-local supply conflict with bounded delayed regional populations.

**Migration**: Cut every caller to the regional population owner and actual-live view; incompatible development state uses explicit operator procedures, with no slot alias, reader or automatic reset.

### Requirement: A hunting band around the capital's north gate always hosts a low-tier monster
**Reason**: Coordinate-slot generation, tier examples and guaranteed capital-local supply conflict with bounded delayed regional populations.

**Migration**: Cut every caller to the regional population owner and actual-live view; incompatible development state uses explicit operator procedures, with no slot alias, reader or automatic reset.

### Requirement: ensure_population idempotently places and respawns monsters at a coordinate
**Reason**: Coordinate-slot generation, tier examples and guaranteed capital-local supply conflict with bounded delayed regional populations.

**Migration**: Cut every caller to the regional population owner and actual-live view; incompatible development state uses explicit operator procedures, with no slot alias, reader or automatic reset.

### Requirement: Population reconciliation never destroys an active-session participant
**Reason**: Conformance reconciliation is deleted; participant retention and historical-cell birth protection become the live owner contract.

**Migration**: Cut all callers and substantively matching test annotations to the replacement contract using tool-generated canonical IDs; retain no legacy behavior, alias or data migration.

