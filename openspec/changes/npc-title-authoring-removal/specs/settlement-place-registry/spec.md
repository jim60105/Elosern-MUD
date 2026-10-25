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

#### Scenario: One record carries a whole location
- **WHEN** a place loads
- **THEN** its interior/exterior/doorway, title-free host identity, direct components and goods are authored there once

#### Scenario: A place may declare no host at all
- **WHEN** all host fields are absent
- **THEN** the location loads without a host roster row

#### Scenario: A host-less place may not sell
- **WHEN** a hostless place declares assortments/additions/exclusions
- **THEN** catalog validation names and rejects it

#### Scenario: A dwelling that trades is still a dwelling
- **WHEN** a dwelling host carries merchant capability
- **THEN** place kind remains dwelling

#### Scenario: Every shipped place's kind describes its location
- **WHEN** shipped kinds are inspected
- **THEN** each retains its actual world location type

#### Scenario: Two places may share an exterior
- **WHEN** shared exterior places have distinct doorway names
- **THEN** both load with their separate doorways

#### Scenario: Two places sharing a doorway name fail load
- **WHEN** places share exterior and doorway name
- **THEN** validation names both places and the collision

#### Scenario: One record supplies every distinguishing field
- **WHEN** place fields are enumerated
- **THEN** stable key, settlement/kind, localized room, exterior/doorway, title-free host/profile, direct components and assortments come from that record

#### Scenario: No host roster row and no code-side interior constant
- **WHEN** a place host/interior is authored
- **THEN** separate roster declarations and interior code constants remain unnecessary

#### Scenario: A shop identity and assortments are interdependent
- **WHEN** goods lack merchant/shop identity or a trading declaration names no goods
- **THEN** existing interdependence validation rejects the candidate

#### Scenario: The host group is indivisible
- **WHEN** a host is declared
- **THEN** required name/profile/race/subrace/sex identity is complete or absent, titles are absent and zero capabilities is valid

#### Scenario: Kind describes the location, never the host's capability
- **WHEN** a home host trades
- **THEN** kind still describes a home

#### Scenario: The kind vocabulary is closed and complete
- **WHEN** kinds are validated
- **THEN** unknown kinds reject without approximation or service inference

#### Scenario: A shared exterior may carry distinct doorways
- **WHEN** distinct places share an exterior
- **THEN** distinct doorway names preserve both locations and collisions reject
