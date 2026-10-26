# settlement-place-registry Specification

## Purpose
Describe one service location — its room, its host and its goods — as a
single authored record, so adding a location to any settlement is a data
edit rather than a code edit across four files.

## Requirements

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

### Requirement: A settlement declares its archetype and coordinate space
The system SHALL support settlement records carrying a stable key matching
the geographic anchor registry, an archetype drawn from a closed vocabulary
of the six settlement archetypes the world defines, and the map coordinate
space its places sit in. A place SHALL name a settlement that exists.

#### Scenario: A place in an unknown settlement fails load
- **WHEN** a place names a settlement key absent from the settlement
  registry
- **THEN** catalog validation raises naming the place and the missing
  settlement

#### Scenario: Two settlements' places resolve in their own coordinate spaces
- **WHEN** two settlements each declare a place at the same exterior
  coordinate
- **THEN** each interior attaches to its own settlement's exterior room, and
  neither attaches to the other's

#### Scenario: Exterior coordinates resolve inside the settlement's space
- **WHEN** a place's exterior coordinate is resolved
- **THEN** it is resolved within that settlement's coordinate space rather than being declared with
  one

#### Scenario: Archetypes are not anchor kinds
- **WHEN** the archetype vocabulary is compared with the geographic anchor kind vocabulary
- **THEN** they are distinct: anchor kinds classify geography and include non-settlements; archetypes
  classify how a settlement is built

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

#### Scenario: Authored-name uniqueness spans the derived rows
- **WHEN** derived host identities validate
- **THEN** existing authored-name uniqueness remains across shop, guild and persistent-adventurer sources

### Requirement: A place's host profile reference is validated
A place record SHALL be able to name its host's authored NPC profile by profile key. Place-registry validation SHALL reject a place that names a host profile key which does not resolve in the NPC profile registry, and SHALL reject a hostless place that names any host profile key, naming the place and the key in both cases. A host profile key SHALL count as host material, so a hostless place carrying one is never treated as hostless.

#### Scenario: An unresolved profile key fails load
- **WHEN** a synthetic hosted place names a host profile key absent from the profile registry
- **THEN** place-registry validation raises naming the place and the key

#### Scenario: A hostless place cannot name a host profile
- **WHEN** a synthetic hostless place names a host profile key
- **THEN** place-registry validation raises naming the place, and the place is not treated as hostless

### Requirement: Every host-authoring place names its host's NPC profile
The host profile key SHALL be part of a place's all-or-nothing host group: a place that authors a host SHALL name a host profile key that resolves in the NPC profile registry, and a hostless place SHALL name none. A hosted place without a profile key SHALL fail load as a partially authored host, naming the place and the missing field; no generic or placeholder profile SHALL be substituted.

#### Scenario: A hosted place without a profile fails load
- **WHEN** a synthetic place authors a complete host but no host profile key
- **THEN** place-registry validation raises naming the place and listing the host profile key as missing

#### Scenario: Every shipped hosted place names a resolvable profile
- **WHEN** the shipped place registry is validated
- **THEN** every place that authors a host names a host profile key that resolves to a valid profile
