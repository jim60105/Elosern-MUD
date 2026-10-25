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

#### Scenario: Host authoring has no title
- **WHEN** a current place/roster identity is declared
- **THEN** it has a validated name and profile and no title/host_title field
