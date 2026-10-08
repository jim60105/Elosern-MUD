# settlement-place-registry Specification

## Purpose
Describe one service location — its room, its host and its goods — as a
single authored record, so adding a location to any settlement is a data
edit rather than a code edit across four files.

## Requirements

### Requirement: A place is the single authored record of one service location
<!-- This block is written against the text `place-kind-vocabulary` leaves behind and MUST be
     archived after it. -->
The system SHALL support place records: one place SHALL carry everything
that distinguishes one service location — key, settlement, kind, interior,
doorway, host, and assortments — and no part of a place SHALL be declared
anywhere else.

#### Scenario: One record carries a whole location
- **WHEN** a place record is loaded
- **THEN** it alone supplies the interior's identity and description, the
  exterior it attaches to, the doorway naming, the host's identity and
  profession, and the goods — and no second file declares any of them

#### Scenario: Goods without a shop identity fail load
- **WHEN** a place declares assortments but no shop identity, or a shop
  identity but no assortments
- **THEN** catalog validation raises naming the place

#### Scenario: A place may declare no host at all
- **WHEN** a place record authors none of the host fields
- **THEN** it loads, and it contributes no service-host roster row

#### Scenario: A half-authored host fails load
- **WHEN** a place record authors a host name but no profession, or a
  profession but no host name
- **THEN** validation raises naming the place and the fields that break the
  all-or-nothing set

#### Scenario: A host-less place may not sell
- **WHEN** a place record authors no host and declares assortments,
  additions or exclusions
- **THEN** validation raises naming the place

#### Scenario: A dwelling that trades is still a dwelling
- **WHEN** a place whose room is a home and whose host carries a merchant
  capability is inspected
- **THEN** its kind names it a home rather than a shop

#### Scenario: Every shipped place's kind describes its location
- **WHEN** each shipped place's kind is compared against what its room is
- **THEN** each names the location type the world document gives it

#### Scenario: Two places may share an exterior
- **WHEN** two places declare the same exterior with different doorway names
- **THEN** both load, and synchronization gives that exterior one doorway
  per place

#### Scenario: Two places sharing a doorway name fail load
- **WHEN** two places declare the same exterior and the same doorway name
- **THEN** validation raises naming both places and the shared name

#### Scenario: One record supplies every distinguishing field
- **WHEN** a place's fields are enumerated
- **THEN** the record alone carries the stable key, the settlement it belongs to, its kind, the
  Traditional Chinese name and description of its interior room, the exterior coordinate the interior
  attaches to, the doorway naming, the host's identity, the host's profession and that profession's
  component identity kwargs, and the assortments the place sells

#### Scenario: No host roster row and no code-side interior constant
- **WHEN** a place's host and interior are authored
- **THEN** the host requires no separate roster row and the interior requires no code-side constant

#### Scenario: A shop identity and assortments are interdependent
- **WHEN** a place declares assortments if and only if it declares a shop identity, and a location
  that sells nothing or sells something but names no goods is authored
- **THEN** both are authoring errors and SHALL fail load

#### Scenario: The host group is indivisible
- **WHEN** a place authors its host — optional, but as one indivisible group: host name, title, race,
  subrace, sex, profession, service id and component identity kwargs
- **THEN** the fields SHALL either all be authored or all be absent, and a partially authored host
  SHALL fail load naming the place and the fields that break the set, because a location with a name
  but no profession, or a profession but no name, is an unfinished record rather than a deliberate
  empty room

#### Scenario: A host-less place declares no goods configuration
- **WHEN** a place authors no host
- **THEN** it SHALL declare no assortments, no additions and no exclusions, because goods require a
  merchant to sell them

#### Scenario: Kind describes the location, never the host's capability
- **WHEN** a place's kind is authored
- **THEN** it describes what the location is in the world, never what capability its host carries — a
  dwelling whose occupant happens to trade is a home, not a shop

#### Scenario: The kind vocabulary is closed and complete
- **WHEN** the kind vocabulary is compared against the location types the world document defines
- **THEN** it is closed and covers them, so no authored place is forced to pick a value that
  misdescribes it; a location type the vocabulary cannot name is a reason to extend the vocabulary,
  not to approximate

#### Scenario: A shared exterior may carry distinct doorways
- **WHEN** two places author doorways on one exterior — a craft alley with a forge and a tailor is
  one street with two doors
- **THEN** they MAY share the exterior but SHALL NOT share a doorway name, because two identical
  doorway names on one exterior produce a single exit where two were authored, silently losing a
  location rather than failing, so the collision SHALL be a load error naming both places

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
Shop identities SHALL be derived from the places that declare one, and the
service-host roster SHALL be derived from every place. Neither SHALL be
hand-authored. A place SHALL carry the component identity kwargs its
profession's blueprint requires, whatever that profession is.

#### Scenario: A trading place and a non-trading place both derive hosts
- **WHEN** the registry holds a place whose profession is a merchant and a
  place whose profession is guild staff
- **THEN** both derive complete roster rows, each carrying exactly the
  identity kwargs its own blueprint consumes

#### Scenario: A missing blueprint kwarg fails load
- **WHEN** a place's profession declares a component whose identity field
  the place does not supply
- **THEN** catalog validation raises naming the place, the profession and
  the missing field, without touching the database

#### Scenario: A duplicate authored name is rejected
- **WHEN** two derived rows, or a derived row and a guild registry row,
  carry the same authored name
- **THEN** load fails naming both holders

#### Scenario: Identity kwargs follow the profession, not a shop-only field
- **WHEN** a trading place and a guild hall author their hosts
- **THEN** the trading place supplies its shop identity and the guild hall supplies its branch and
  dialogue identities, and a flat shop-only field SHALL NOT be used because it cannot describe a
  non-trading service location

#### Scenario: Blueprint coverage is enforced like a hand-authored roster row
- **WHEN** a place's derived roster row is validated against its profession's blueprint
- **THEN** every component's identity fields except the row-level service anchor must be supplied,
  and a kwarg no component consumes SHALL be rejected

#### Scenario: Authored-name uniqueness spans the derived rows
- **WHEN** the authored-name uniqueness rule is evaluated over the derived rows
- **THEN** it continues to hold across shops, guild branches and guild rank examiners

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
