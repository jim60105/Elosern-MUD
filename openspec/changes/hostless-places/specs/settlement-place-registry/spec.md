## MODIFIED Requirements

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
