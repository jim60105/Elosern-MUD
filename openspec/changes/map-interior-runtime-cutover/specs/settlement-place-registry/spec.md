# Spec Delta

## MODIFIED Requirements

### Requirement: A place is the single authored record of one service location
Each place SHALL own non-map kind, qualified room reference, optional complete host identity/direct capabilities and assortments, while room identity/prose/topology belong solely to interior documents. Hostless and zero-capability hosts SHALL remain valid under existing non-map validation rules.

#### Scenario: One source record
- **WHEN** a hosted location is authored with a valid qualified interior-room reference
- **THEN** the qualified room join, non-map identity, direct components and goods are declared in the service record once; geometry/naming/topology live in the interior document

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
- **THEN** its qualified room reference, host identity, direct components and goods are authored in the place; room/exterior/doorway data are authored once in the interior document

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
- **WHEN** interior relationships share an exterior with distinct doorway names
- **THEN** each loads and receives its own doorway

#### Scenario: Two places sharing a doorway name fail load
- **WHEN** interior relationships share an exterior and doorway name
- **THEN** validation names both places and the collision

#### Scenario: One record supplies every distinguishing field
- **WHEN** place fields are enumerated
- **THEN** stable key, settlement/kind, qualified room reference, host/profile, direct components and assortments come from the service record; localized room identity and exterior/doorway declarations come only from the interior document

#### Scenario: No host roster row and no code-side interior constant
- **WHEN** a host/interior is authored
- **THEN** no separate host roster declaration or code-side interior constant is required; topology is declared in its map document

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
- **WHEN** two distinct interior relationships share an exterior
- **THEN** unique doorway names preserve both locations; a shared doorway name rejects

### Requirement: A settlement declares its archetype and coordinate space
A non-map settlement record SHALL retain its authored archetype and resolve its map association through the map snapshot; service places SHALL target qualified rooms without duplicating coordinate space or exterior geometry.

#### Scenario: Two settlement spaces
- **WHEN** two settlements have equal local coordinates but distinct qualified room references
- **THEN** each service resolves its own room with no place-authored coordinate fallback

#### Scenario: Unknown settlement
- **WHEN** a non-map service settlement or qualified room is absent
- **THEN** static validation rejects before persistence while archetype and geographic kind remain distinct

