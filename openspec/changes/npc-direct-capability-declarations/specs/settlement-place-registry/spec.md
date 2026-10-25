# Spec Delta

## MODIFIED Requirements

### Requirement: A place is the single authored record of one service location
Each place SHALL own its geometry, naming, optional complete host identity and direct capability declarations, and assortments. Hostless places SHALL remain valid without host/capability/goods fields. A host SHALL allow zero capabilities without implying a profession.

#### Scenario: One source record
- **WHEN** a hosted location is authored
- **THEN** geometry, identity, direct components and goods are declared there once

#### Scenario: Goods without a shop identity fail load
- **WHEN** goods exist without a valid merchant/shop configuration
- **THEN** the complete candidate rejects naming the place

#### Scenario: A half-authored host fails load
- **WHEN** some required identity/profile fields are missing
- **THEN** validation names the incomplete host; zero components is valid for a complete host

#### Scenario: A host-less place declares no goods configuration
- **WHEN** a hostless place declares host/capability/goods configuration
- **THEN** it is rejected while ordinary plazas/interiors still synchronize

### Requirement: Shop identities and the service-host roster are derived from places
Shop identities and roster rows SHALL derive from explicit place component declarations. Required configuration SHALL be complete, unknown/dead kwargs rejected, and canonical host provenance unique. Per-component person/place bindings SHALL be independent of place kind or component ordering.

#### Scenario: A trading place and a non-trading place both derive hosts
- **WHEN** a merchant and guild hall declare direct components
- **THEN** each yields its own validated host plan and complete component kwargs

#### Scenario: A missing blueprint kwarg fails load
- **WHEN** a direct capability omits a required identifier
- **THEN** the whole candidate rejects naming place/type/field

#### Scenario: A duplicate authored name is rejected
- **WHEN** two authored host names violate the existing uniqueness contract
- **THEN** the existing named rejection remains before writes

#### Scenario: Identity kwargs follow the profession, not a shop-only field
- **WHEN** a multi-capability host is declared
- **THEN** each component carries its own kwargs with no flat override map

#### Scenario: Blueprint coverage is enforced like a hand-authored roster row
- **WHEN** an authored component contains unused or unknown kwargs
- **THEN** validation rejects it without consulting a blueprint
