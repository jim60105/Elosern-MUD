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

#### Scenario: One record carries a whole location
- **WHEN** a place loads
- **THEN** its interior/exterior/doorway, host identity, direct components and goods are authored there once

#### Scenario: A place may declare no host at all
- **WHEN** all host fields are absent
- **THEN** the location loads without a host roster row

#### Scenario: A host-less place may not sell
- **WHEN** a hostless place declares assortments/additions/exclusions
- **THEN** catalog validation names and rejects the place

#### Scenario: A dwelling that trades is still a dwelling
- **WHEN** a dwelling host has merchant capability
- **THEN** place kind remains dwelling rather than being inferred from trade

#### Scenario: Every shipped place's kind describes its location
- **WHEN** shipped place kinds are inspected
- **THEN** each retains its actual world location type

#### Scenario: Two places may share an exterior
- **WHEN** places share an exterior with distinct doorway names
- **THEN** each loads and receives its own doorway

#### Scenario: Two places sharing a doorway name fail load
- **WHEN** places share an exterior and doorway name
- **THEN** validation names both places and the collision

#### Scenario: One record supplies every distinguishing field
- **WHEN** place fields are enumerated
- **THEN** stable key, settlement/kind, localized room identity, exterior/doorway, host/profile, direct component configuration and assortments all come from that record

#### Scenario: No host roster row and no code-side interior constant
- **WHEN** a host/interior is authored
- **THEN** neither a separate roster declaration nor code-side interior constant is required

#### Scenario: A shop identity and assortments are interdependent
- **WHEN** goods lack merchant/shop identity or a trading declaration names no goods
- **THEN** the existing interdependence validation rejects the candidate

#### Scenario: The host group is indivisible
- **WHEN** a place declares a host
- **THEN** its required name/profile/race/subrace/sex identity is complete or wholly absent; zero declared capabilities remains valid

#### Scenario: Kind describes the location, never the host's capability
- **WHEN** kind is authored for a trading home
- **THEN** it describes the home, independently of merchant capability

#### Scenario: The kind vocabulary is closed and complete
- **WHEN** kinds are validated against existing lore vocabulary
- **THEN** unknown kinds reject without approximate substitutions or capability inference

#### Scenario: A shared exterior may carry distinct doorways
- **WHEN** two distinct places share an exterior
- **THEN** unique doorway names preserve both locations; a shared doorway name rejects

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
