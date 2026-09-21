# settlement-place-registry Specification

## Purpose
Describe one service location — its room, its host and its goods — as a
single authored record, so adding a location to any settlement is a data
edit rather than a code edit across four files.

## Requirements

### Requirement: A place is the single authored record of one service location
The system SHALL support place records. One place SHALL carry everything
that distinguishes one service location: its stable key, the settlement it
belongs to, its kind, the Traditional Chinese name and description of its
interior room, the exterior coordinate the interior attaches to, the
doorway naming, its host's identity, the host's profession and that
profession's component identity kwargs, and the assortments the place
sells.

No part of a place SHALL be declared anywhere else. In particular a place's
host SHALL NOT also require a separate roster row, and a place's interior
SHALL NOT also require a code-side constant.

A place SHALL declare assortments if and only if it declares a shop
identity. A location that sells nothing and a location that sells something
but names no goods are both authoring errors and SHALL fail load.

A place's host SHALL be optional, and optional as one indivisible group:
the host name, title, race, subrace, sex, profession, service id and
component identity kwargs SHALL either all be authored or all be absent. A
partially authored host SHALL fail load naming the place and the fields
that break the set, because a location with a name but no profession, or a
profession but no name, is an unfinished record rather than a deliberate
empty room. A place that authors no host SHALL declare no assortments, no
additions and no exclusions: goods require a merchant to sell them.

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

### Requirement: A settlement declares its archetype and coordinate space
The system SHALL support settlement records carrying a stable key matching
the geographic anchor registry, an archetype drawn from a closed vocabulary
of the six settlement archetypes the world defines, and the map coordinate
space its places sit in.

A place SHALL name a settlement that exists; its exterior coordinate SHALL
be resolved within that settlement's coordinate space rather than being
declared with one.

The archetype vocabulary SHALL be distinct from the geographic anchor kind
vocabulary. Anchor kinds classify geography and include non-settlements;
archetypes classify how a settlement is built.

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

### Requirement: Shop identities and the service-host roster are derived from places
Shop identities SHALL be derived from the places that declare one, and the
service-host roster SHALL be derived from every place. Neither SHALL be
hand-authored.

A place SHALL carry the component identity kwargs its profession's blueprint
requires, whatever that profession is — a trading place supplies its shop
identity, a guild hall supplies its branch and dialogue identities. A flat
shop-only field SHALL NOT be used, because it cannot describe a
non-trading service location.

Blueprint coverage SHALL be enforced as it is for a hand-authored roster
row: every component's identity fields except the row-level service anchor
must be supplied, and a kwarg no component consumes SHALL be rejected.

The authored-name uniqueness rule SHALL continue to hold across shops,
guild branches and guild rank examiners, evaluated over the derived rows.

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
